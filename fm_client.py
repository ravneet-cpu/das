#!/usr/bin/env python3
"""
fm_client.py — Shared FileMaker Data API client for all Mediactive sync scripts.

==============================================================================
WHY THIS FILE EXISTS: THE JUNE 2026 INCIDENT
==============================================================================

In June 2026, the FileMaker Data API (FM server at 178.248.210.53) crashed and
had to be restarted after a synchronisation run sent ~44 000 _find requests to
the Artworks layout starting at 04:00.  Investigation revealed THREE systemic
bugs present in every sync script:

  BUG 1 — No 952 handling
    FM returns error code 952 ("Invalid FileMaker Data API token") when a
    session token has expired or become invalid mid-run.  No script caught
    this: every subsequent API call silently failed, producing thousands of
    empty/error responses that were still looped over, hammering the server.

  BUG 2 — No logout
    The FM Data API requires an explicit DELETE /sessions/{token} call to
    release a session slot.  No script ever called it.  Over many runs this
    exhausted the FM session pool, causing the server to reject new logins
    from any client.

  BUG 3 — No timeout
    No script passed a `timeout` parameter to requests.  When the FM server
    became unresponsive (socket still open, no data), scripts blocked
    indefinitely on the socket read.  Because they also held flock() locks,
    ALL subsequent cron invocations queued behind them — the entire sync
    pipeline was silently frozen for days before anyone noticed.

This shared client fixes all three bugs in one place so that individual sync
scripts never have to think about them again.

==============================================================================
USAGE
==============================================================================

    from fm_client import FileMakerClient, FMError, FMNotFound
    from fm_client import FM_ARTWORKS_LAYOUT, FM_GALLERIES_LAYOUT

    with FileMakerClient() as fm:
        records = fm.get_records(FM_GALLERIES_LAYOUT, limit=100, offset=1)
        found   = fm.find(FM_ARTWORKS_LAYOUT, [{'IdName': 'BOM-12345'}], limit=1)
        fm.patch(FM_ARTWORKS_LAYOUT, record_id, {'MAINFM': 'https://...'})

The `with` block guarantees that DELETE /sessions is called even if an
exception is raised inside the block (fixes Bug 2).
==============================================================================
"""

import logging
import time
from typing import Optional, Union
from requests.auth import HTTPBasicAuth
import requests
import urllib3

# Suppress the SSL certificate warning that arises because the FM server uses
# a self-signed certificate and we pass verify=False.  The FM server is on a
# private IP (178.248.210.53) and Mediactive does not provide a CA bundle, so
# certificate verification is deliberately disabled.  This suppression keeps
# log output clean — the security trade-off is intentional and accepted.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==============================================================================
# FM CONNECTION CONSTANTS
# These credentials belong to Mediactive, who operates the FileMaker server.
# They are kept here (rather than in environment variables) because this package
# is distributed exclusively to Mediactive and there is no multi-tenant concern.
# ==============================================================================

FM_SERVER   = '178.248.210.53'   # Private IP of the Mediactive FileMaker server
FM_USERNAME = 'DataApiAccess'    # FM Data API user account (read/write, no admin)
FM_PASSWORD = 'JPMEJU1JPMEJU1'  # Password for the DataApiAccess account
FM_DATABASE = 'OperaGallery'    # FM database name (the main CRM database)

# ==============================================================================
# LAYOUT NAME CONSTANTS
# Import these in sync scripts instead of writing layout names as bare strings.
# Centralising them here means a layout rename only requires one edit.
# ==============================================================================

FM_ARTWORKS_LAYOUT       = 'Artworks'            # Main artwork catalogue
FM_GALLERIES_LAYOUT      = 'CRMRecordGalleries'  # Gallery / venue records
FM_ARTISTS_LAYOUT        = 'CRMRecordArtists'    # Artist records
FM_CUSTOMERS_LAYOUT      = 'CRMRecordCustomers'  # Customer / contact records
FM_ORDERS_LAYOUT         = 'CRMRecordOrders'     # Sales orders
FM_LINE_ITEMS_LAYOUT     = 'CRMRecordOrderItems' # Individual order line items
FM_USERS_LAYOUT          = 'CRMRecordUsers'      # FM user accounts

# ==============================================================================
# CLIENT TUNING CONSTANTS
# These values were chosen after the June 2026 incident to make the client
# robust against a slow or temporarily unresponsive FM server.
# ==============================================================================

DEFAULT_TIMEOUT = 60
# Maximum seconds to wait for ANY single HTTP response from the FM server.
# Before this fix, no timeout was set anywhere: if FM accepted the TCP connection
# but stopped sending data (e.g. during a heavy _find on the Artworks layout),
# the requests library would block forever.  Scripts held flock() locks while
# blocked, so every subsequent cron run queued behind them — the whole pipeline
# froze silently.
# 60 s was chosen as a balance: long enough for a legitimate slow _find (the
# Artworks layout with related fields can take 30-50 s), short enough to unblock
# a hung script within one minute rather than hours.

LOGIN_TIMEOUT = 30
# Shorter timeout used exclusively for POST /sessions (login) and
# DELETE /sessions (logout).  These are simple, cheap operations on the FM
# server; if they take more than 30 s the server is effectively down and there
# is no point waiting longer.  Using a shorter value here lets the script fail
# fast and release its flock() lock sooner.

MAX_RETRIES = 3
# Number of attempts for each FM API call before giving up.
# Retry logic covers two cases:
#   - Transient network errors (TCP reset, brief DNS hiccup, etc.)
#   - FM HTTP 5xx responses (FM server temporarily overloaded)
# Three attempts means we tolerate up to two failures per call.  More retries
# would delay scripts too long on a genuinely dead server; fewer would make
# the client too sensitive to momentary blips.

BACKOFF_BASE = 2.0
# Base for the exponential back-off between retries (seconds).
# Wait time = BACKOFF_BASE ** attempt_number:
#   attempt 1 → 2.0 s
#   attempt 2 → 4.0 s
#   attempt 3 → 8.0 s  (not reached because MAX_RETRIES=3 raises on attempt 3)
# Exponential back-off reduces the thundering-herd effect: if FM is struggling,
# a flood of immediate retries from multiple scripts would make it worse.

RATE_MIN_INTERVAL = 0.05
# Minimum number of seconds between consecutive outgoing HTTP requests.
# 0.05 s = 20 requests per second maximum.
# The June 2026 incident traced part of the FM overload to update_mainfm.py
# issuing ~44 000 _find calls on the Artworks layout with no pacing at all.
# This floor ensures that even a tight loop never exceeds 20 req/s, which is
# well within FM's documented Data API limits and leaves headroom for other
# concurrent scripts.  For scripts processing large volumes, callers can pass
# a higher rate_interval to FileMakerClient() (e.g. 0.15 for ~6 req/s).


# ==============================================================================
# EXCEPTIONS
# ==============================================================================

class FMError(Exception):
    """
    Base exception for all FileMaker Data API errors.

    Raised for non-retryable conditions: authentication failure, field not on
    layout, unexpected HTTP status, etc.

    Attributes:
        status_code (int | None): HTTP status code returned by FM, if any.
        fm_code (str | None): FM-specific error code from the JSON response
                              'messages' array (e.g. '102', '401', '952').
    """
    def __init__(self, message: str, status_code: Optional[int] = None, fm_code: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.fm_code = fm_code


class FMNotFound(FMError):
    """
    Raised by find() when the FM server returns error code 401 ("No records match
    the request").

    This is a subclass of FMError so callers that do not care about the
    distinction can catch FMError, while callers that need to distinguish
    "found nothing" from "real error" can catch FMNotFound specifically.

    Example:
        try:
            records = fm.find(FM_ARTWORKS_LAYOUT, [{'IdName': ref}])
        except FMNotFound:
            pass  # artwork not yet in FM — skip
        except FMError as e:
            logger.error('FM error: %s', e)
    """
    pass


# ==============================================================================
# PRIVATE HELPERS
# ==============================================================================

def _fm_messages(resp: requests.Response) -> list:
    """
    Extract the 'messages' list from an FM JSON response.

    FM always returns a JSON body of the form:
        {"response": {...}, "messages": [{"code": "0", "message": "OK"}]}

    Returns an empty list if the body is not valid JSON or 'messages' is absent.
    Never raises — used in error-path code where we do not want a secondary
    exception to mask the original problem.
    """
    try:
        return resp.json().get('messages', [])
    except Exception:
        return []


def _first_fm_code(resp: requests.Response) -> Optional[str]:
    """
    Return the FM error code from the first message in the response, or None.

    Used to populate FMError.fm_code so that callers can inspect the exact FM
    error without parsing the response themselves.
    """
    msgs = _fm_messages(resp)
    return str(msgs[0]['code']) if msgs else None


def _is_code(resp: requests.Response, code: str) -> bool:
    """
    Return True if any message in the FM response carries the given error code.

    Checks all messages (not just the first) because FM occasionally returns
    multiple messages for a single request.

    Args:
        resp: The requests.Response object from the FM API call.
        code: FM error code to look for, as a string (e.g. '401', '952').
    """
    return any(str(m.get('code')) == code for m in _fm_messages(resp))


# ==============================================================================
# MAIN CLIENT
# ==============================================================================

class FileMakerClient:
    """
    FileMaker Data API client with guaranteed session lifecycle.

    Handles authentication, rate limiting, timeout enforcement, retry/back-off,
    and automatic re-login on FM error 952 — the three systemic bugs from the
    June 2026 incident, fixed once for all scripts.

    ALWAYS use as a context manager so that logout is guaranteed:

        with FileMakerClient() as fm:
            records = fm.get_records(FM_GALLERIES_LAYOUT, limit=100, offset=1)

    For scripts that process large volumes and should run more slowly, pass a
    custom rate_interval (minimum seconds between requests):

        with FileMakerClient(rate_interval=0.15) as fm:  # ~6 req/s
            ...

    For scripts that need a custom logger (e.g. one that writes to a per-script
    log file), pass it explicitly:

        with FileMakerClient(logger=my_logger) as fm:
            ...
    """

    def __init__(
        self,
        server: str = FM_SERVER,
        username: str = FM_USERNAME,
        password: str = FM_PASSWORD,
        database: str = FM_DATABASE,
        timeout: int = DEFAULT_TIMEOUT,
        rate_interval: float = RATE_MIN_INTERVAL,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialise the client. Does NOT log in yet — login happens in __enter__.

        Args:
            server:        FM server hostname or IP address.
            username:      FM Data API username.
            password:      FM Data API password.
            database:      FM database name.
            timeout:       Per-request timeout in seconds (default DEFAULT_TIMEOUT=60).
            rate_interval: Minimum seconds between consecutive requests
                           (default RATE_MIN_INTERVAL=0.05, i.e. max 20 req/s).
            logger:        Optional logger instance.  If None, uses the module-level
                           logger (logging.getLogger(__name__)).
        """
        self.server        = server
        self.username      = username
        self.password      = password
        self.database      = database
        self.timeout       = timeout
        self.rate_interval = rate_interval
        self.token: Optional[str] = None                        # Set by _login(), cleared by _logout()
        self.log = logger or logging.getLogger(__name__)
        self._base = f'https://{server}/fmi/data/vLatest/databases/{database}'  # API root URL
        self._last_req_at: float = 0.0                       # Monotonic timestamp of last request (rate limiting)

    # ── Context manager ──────────────────────────────────────────────────────

    def __enter__(self) -> 'FileMakerClient':
        """
        Log in to the FM Data API and return self.

        Called automatically by `with FileMakerClient() as fm:`.

        Returns:
            self — the authenticated client ready for API calls.

        Raises:
            FMError: if login fails (network error or bad credentials).
        """
        self._login()
        return self

    def __exit__(self, *_) -> None:
        """
        Log out from the FM Data API, always — even if an exception occurred.

        Called automatically at the end of the `with` block.  The *_ absorbs
        exc_type, exc_val, exc_tb so that any exception propagates normally after
        logout.  This is the fix for Bug 2 (no logout → session pool exhaustion).
        """
        self._logout()

    # ── Authentication ───────────────────────────────────────────────────────

    def _login(self) -> None:
        """
        POST /sessions — obtain a session token from the FM Data API.

        Sends HTTP Basic Auth credentials; FM responds with a bearer token that
        must be included in the Authorization header of every subsequent request.

        Uses LOGIN_TIMEOUT (30 s) rather than DEFAULT_TIMEOUT because login is a
        lightweight operation and a slow response indicates the server is down.

        Sets self.token on success.

        Raises:
            FMError: on network error or if FM returns a non-200 status.
        """
        url = f'{self._base}/sessions'
        try:
            resp = requests.post(
                url,
                auth=HTTPBasicAuth(self.username, self.password),
                json={},          # FM requires a JSON body (even if empty) for POST /sessions
                verify=False,     # Self-signed certificate — see urllib3.disable_warnings above
                timeout=LOGIN_TIMEOUT,
            )
        except requests.exceptions.RequestException as e:
            raise FMError(f'FM login network error: {e}')
        if resp.status_code != 200:
            raise FMError(
                f'FM login failed: HTTP {resp.status_code} — {resp.text[:200]}',
                status_code=resp.status_code,
            )
        self.token = resp.json()['response']['token']
        self.log.info('FM login OK (token %s…)', self.token[:12])

    def _logout(self) -> None:
        """
        DELETE /sessions/{token} — release the FM session slot.

        This is the fix for Bug 2: the FM server has a finite session pool; if
        sessions are never closed they accumulate until FM refuses new logins.

        Errors are logged as warnings but never re-raised so that they do not
        mask the original exception that triggered __exit__.

        Clears self.token in the `finally` block so that any accidental calls
        after logout cannot reuse a dead token.
        """
        if not self.token:
            return   # Already logged out or never logged in — nothing to do
        url = f'{self._base}/sessions/{self.token}'
        try:
            requests.delete(
                url,
                headers={'Content-Type': 'application/json'},
                verify=False,
                timeout=LOGIN_TIMEOUT,
            )
            self.log.info('FM logout OK')
        except Exception as e:
            # Non-fatal: if the server is already unreachable, the session will
            # eventually time out on the FM side.  More important to not crash here.
            self.log.warning('FM logout error (non-fatal): %s', e)
        finally:
            # Always clear the token — even if DELETE failed, this token is done
            self.token = None

    def _relogin(self) -> None:
        """
        Handle FM error 952 ("Invalid FileMaker Data API token") by refreshing
        the session token.

        This is the fix for Bug 1: before this client, receiving a 952 mid-run
        caused every remaining API call to fail silently (invalid token) while
        the script kept looping, hammering the server with thousands of doomed
        requests.

        Steps:
          1. Attempt to DELETE the stale session (best-effort, ignored on error).
          2. Call _login() to obtain a fresh token.

        After _relogin(), _request() retries the original call once with the new
        token.  If FM returns 952 again after the retry, _request() raises FMError
        rather than looping indefinitely.

        Raises:
            FMError: if the fresh login attempt fails.
        """
        self.log.warning('FM 952 detected — re-logging in')
        old = self.token
        self.token = None
        # Attempt to release the stale session — FM may reject it (it's already
        # invalid), but trying keeps the session pool as clean as possible.
        if old:
            url = f'{self._base}/sessions/{old}'
            try:
                requests.delete(url, headers={'Content-Type': 'application/json'},
                                verify=False, timeout=10)
            except Exception:
                pass   # Ignore — the session is stale anyway
        self._login()

    # ── Low-level HTTP request ───────────────────────────────────────────────

    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Execute a single HTTP request against the FM Data API with full resilience:

          - Rate limiting: enforces at least RATE_MIN_INTERVAL between requests
            (fix for the Artworks _find flood that triggered the June 2026 crash).
          - Timeout: every request respects self.timeout = DEFAULT_TIMEOUT = 60 s
            (fix for Bug 3 — scripts previously hung indefinitely on dead sockets).
          - Retry + back-off: up to MAX_RETRIES=3 attempts on network errors and
            FM HTTP 5xx responses, with waits of 2 s, 4 s before the final try.
          - 952 auto-recovery: on FM error 952, calls _relogin() and retries the
            request exactly once outside the normal retry counter (fix for Bug 1).

        Args:
            method: HTTP verb ('GET', 'POST', 'PATCH', 'DELETE').
            url:    Full URL for the FM API endpoint.
            **kwargs: Passed through to requests.request() (e.g. json=, params=).
                      'timeout' defaults to self.timeout; 'verify' is always False.

        Returns:
            requests.Response from the FM server.

        Raises:
            FMError: after MAX_RETRIES failures, or on persistent 952 after re-login.
        """
        # Apply defaults — callers never need to specify these
        kwargs.setdefault('timeout', self.timeout)
        kwargs['verify'] = False   # Always; FM uses a self-signed certificate

        def _do() -> requests.Response:
            """Rate-limit then fire the request."""
            self._wait_rate()
            return requests.request(method, url, headers=self._headers(), **kwargs)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = _do()
            except requests.exceptions.RequestException as e:
                # Network-level failure (connection refused, timeout, SSL error, etc.)
                if attempt == MAX_RETRIES:
                    raise FMError(f'FM network error after {MAX_RETRIES} tries on {url}: {e}')
                wait = BACKOFF_BASE ** attempt
                self.log.warning('FM network error (attempt %d/%d), retry in %.1fs: %s',
                                 attempt, MAX_RETRIES, wait, e)
                time.sleep(wait)
                continue

            # ── FM error 952: expired/invalid token ──────────────────────────
            # Re-login and retry ONCE.  This single retry is NOT counted against
            # MAX_RETRIES because 952 is a session-management issue, not a load
            # issue — the server is healthy but our token is stale.
            if _is_code(resp, '952'):
                self._relogin()
                try:
                    resp = _do()
                except requests.exceptions.RequestException as e:
                    raise FMError(f'FM network error after 952 re-login: {e}')
                # If FM still returns 952 after a fresh login, something is wrong
                # at the server level — abort rather than loop.
                if _is_code(resp, '952'):
                    raise FMError('FM 952 persists after re-login — aborting',
                                  status_code=resp.status_code, fm_code='952')

            # ── FM HTTP 5xx: server-side error, transient ─────────────────────
            # Back off and retry, but only if we have attempts left.
            if resp.status_code >= 500 and attempt < MAX_RETRIES:
                wait = BACKOFF_BASE ** attempt
                self.log.warning('FM HTTP %d (attempt %d/%d), retry in %.1fs',
                                 resp.status_code, attempt, MAX_RETRIES, wait)
                time.sleep(wait)
                continue

            # All other responses (200, 4xx, etc.) are returned to the caller
            # which decides whether to raise or handle them.
            return resp

        # Reached only if every attempt ended in a 5xx (network errors raise inline)
        raise FMError(f'FM request failed after {MAX_RETRIES} attempts')

    def _wait_rate(self) -> None:
        """
        Enforce the minimum interval between consecutive requests.

        Computes how long since the last request was sent and sleeps for the
        remainder of rate_interval if needed.  Uses time.monotonic() to avoid
        issues with system clock adjustments.

        After sleeping (or if no sleep was needed), records the current monotonic
        time so the next call can measure the gap correctly.
        """
        wait = self.rate_interval - (time.monotonic() - self._last_req_at)
        if wait > 0:
            time.sleep(wait)
        self._last_req_at = time.monotonic()

    def _headers(self) -> dict:
        """
        Build the HTTP headers required for authenticated FM Data API requests.

        Returns:
            dict with 'Authorization' (Bearer token) and 'Content-Type'.
            Must be called after _login() so that self.token is set.
        """
        return {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}

    # ── Public API ───────────────────────────────────────────────────────────

    def get_records(self, layout: str, limit: int = 100, offset: int = 1) -> list:
        """
        Fetch a page of records from a FM layout.

        Wraps GET /layouts/{layout}/records with pagination parameters.

        Args:
            layout: FM layout name (use the FM_*_LAYOUT constants).
            limit:  Maximum number of records to return (FM default is 100).
            offset: 1-based record offset for pagination.  Pass offset=1 for the
                    first page, offset=limit+1 for the second page, etc.

        Returns:
            List of FM record dicts, each with keys 'fieldData', 'recordId',
            'modId', and 'portalData'.  Returns an empty list when FM responds
            with error code 101 ("No records remain") — this is the normal
            pagination termination signal, not an error.

        Raises:
            FMError: on unexpected HTTP status or FM error other than 101.

        Example:
            offset = 1
            while True:
                page = fm.get_records(FM_GALLERIES_LAYOUT, limit=100, offset=offset)
                if not page:
                    break
                for rec in page:
                    process(rec)
                offset += 100
        """
        url = f'{self._base}/layouts/{layout}/records'
        resp = self._request('GET', url, params={'_limit': limit, '_offset': offset})
        if resp.status_code != 200:
            if _is_code(resp, '101'):
                return []  # Normal end-of-data signal — not an error
            raise FMError(
                f'get_records({layout}) offset={offset}: HTTP {resp.status_code}',
                status_code=resp.status_code, fm_code=_first_fm_code(resp),
            )
        return resp.json()['response']['data']

    def find(self, layout: str, query: list, limit: int = 1000,
             sort: Optional[list] = None) -> list:
        """
        Search for records in a FM layout using the Data API _find endpoint.

        Wraps POST /layouts/{layout}/_find with a FileMaker query payload.

        Args:
            layout: FM layout name (use the FM_*_LAYOUT constants).
            query:  List of query dicts, each mapping field names to search
                    values.  Multiple dicts in the list are ORed together.
                    Example: [{'IdName': 'BOM-12345'}]
                    Example (OR): [{'Status': 'Active'}, {'Status': 'Pending'}]
                    To omit records matching a criterion, prefix the dict with
                    'omit': True.
            limit:  Maximum records to return (default 1000).
            sort:   Optional list of sort dicts, e.g.:
                    [{'fieldName': 'IdName', 'sortOrder': 'ascend'}]

        Returns:
            List of FM record dicts (same structure as get_records).

        Raises:
            FMNotFound: if FM returns error code 401 (no matching records).
                        Callers that expect this should catch FMNotFound explicitly.
            FMError:    on any other FM error or unexpected HTTP status.

        Example:
            try:
                rows = fm.find(FM_ARTWORKS_LAYOUT, [{'IdName': ref}], limit=1)
                fm_record = rows[0]
            except FMNotFound:
                logger.info('Artwork %s not in FM — skipping', ref)
        """
        url = f'{self._base}/layouts/{layout}/_find'
        payload: dict = {'query': query, 'limit': str(limit)}
        if sort:
            payload['sort'] = sort
        resp = self._request('POST', url, json=payload)
        if resp.status_code != 200:
            if _is_code(resp, '401'):
                # FM code 401 = "No records match the request" — raised as
                # FMNotFound so callers can distinguish "empty result" from
                # "API error" without parsing the response themselves.
                raise FMNotFound(
                    f'find({layout}): no records matching {query}',
                    status_code=resp.status_code, fm_code='401',
                )
            raise FMError(
                f'find({layout}): HTTP {resp.status_code}',
                status_code=resp.status_code, fm_code=_first_fm_code(resp),
            )
        return resp.json()['response']['data']

    def get_record(self, layout: str, record_id) -> dict:
        """
        Fetch a single FM record by its internal recordId.

        Wraps GET /layouts/{layout}/records/{record_id}.

        Note: record_id is the FM internal record identifier (an integer),
        NOT the business-facing IdEntity (Cxxxx) or IdName (BOM-xxxxx).
        Use find() if you only have the business key.

        Args:
            layout:    FM layout name.
            record_id: FM internal record ID (int or str).

        Returns:
            Single FM record dict with keys 'fieldData', 'recordId', 'modId',
            and 'portalData'.

        Raises:
            FMError: if the record is not found, or on any HTTP/FM error.
        """
        url = f'{self._base}/layouts/{layout}/records/{record_id}'
        resp = self._request('GET', url)
        if resp.status_code != 200:
            raise FMError(
                f'get_record({layout}/{record_id}): HTTP {resp.status_code}',
                status_code=resp.status_code, fm_code=_first_fm_code(resp),
            )
        data = resp.json().get('response', {}).get('data', [])
        if not data:
            raise FMError(f'get_record({layout}/{record_id}): empty response')
        return data[0]

    def patch(self, layout: str, record_id, field_data: dict) -> dict:
        """
        Update fields on an existing FM record.

        Wraps PATCH /layouts/{layout}/records/{record_id}.

        Args:
            layout:     FM layout name.
            record_id:  FM internal record ID (int or str).
            field_data: Dict mapping FM field names to new values.
                        Example: {'MAINFM': 'https://...', 'SyncStatus': 'OK'}
                        Only the fields listed here are updated; others are left
                        unchanged (PATCH semantics, not PUT/replace).

        Returns:
            Full FM response dict (usually {'response': {}, 'messages': [...]}).
            Most callers discard this; it is returned for completeness.

        Raises:
            FMError: on FM error or unexpected HTTP status.
                     Check e.fm_code == '102' for "field not on layout" errors,
                     which indicate a mismatch between the field_data dict and the
                     fields available on the target layout.

        Example:
            fm.patch(FM_ARTWORKS_LAYOUT, rec['recordId'], {'SyncedAt': today_str})
        """
        url = f'{self._base}/layouts/{layout}/records/{record_id}'
        resp = self._request('PATCH', url, json={'fieldData': field_data})
        if resp.status_code != 200:
            raise FMError(
                f'patch({layout}/{record_id}): HTTP {resp.status_code}',
                status_code=resp.status_code, fm_code=_first_fm_code(resp),
            )
        return resp.json()
