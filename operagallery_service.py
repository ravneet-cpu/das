#!/usr/bin/env python3
"""
OperaCRM service for photo validator application
Integration with real OperaCRM (Odoo system)
"""

import sys
import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_operacrm_corrected import OperaCRMClient
from flask import Blueprint, request, jsonify, Response
from auth import verify_token
import re
import requests
import time
import json
import os
from image_quality_checker import ImageQualityChecker
from requests.auth import HTTPBasicAuth
import urllib3

# Supprimer les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from filemaker_cache_service import cache_search, cache_metadata, cache_medium

# Create the blueprint
operacrm_bp = Blueprint('operacrm', __name__)

FM_SERVER = '178.248.210.53'
FM_USERNAME = 'DataApiAccess'
FM_PASSWORD = 'JPMEJU1JPMEJU1'
FM_DATABASE = 'OperaGallery'
FM_LAYOUT = 'CRMSearchArtworks'

# Global OperaCRM client instance
client = OperaCRMClient()

# Cache for authentication
_auth_time = 0

def ensure_authenticated():
    """Ensure client is authenticated with automatic retry"""
    global _auth_time
    
    # Re-authenticate every 30 minutes
    if client.session_id and (time.time() - _auth_time) < 1800:
        return True
    
    max_retries = 3
    
    for attempt in range(max_retries):
        if not client.session_id:
            print(f"🔐 Authenticating with OperaCRM (attempt {attempt + 1}/{max_retries})...")
            success = client.authenticate("odoo_15", "surafelwubshet7@gmail.com", "Surafell")
            if success:
                print("✅ OperaCRM authentication successful")
                _auth_time = time.time()
                return True
            else:
                print(f"❌ OperaCRM authentication failed (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    time.sleep(2)  # Wait 2 seconds before retry
                client.session_id = None  # Reset session
        else:
            # Test if existing session is still valid
            try:
                test_results = client.search_by_artist("TEST_CONNECTIVITY", 1)
                if test_results is not None:
                    return True
                else:
                    print("🔄 Session expired, re-authenticating...")
                    client.session_id = None
            except:
                print("🔄 Session test failed, re-authenticating...")
                client.session_id = None
    
    print("❌ All authentication attempts failed")
    return False

def get_operacrm_artwork_by_id(id_name):
    """Get artwork data from OperaCRM by IdName"""
    if not ensure_authenticated():
        return None
    
    try:
        results = client.search_by_idname(id_name)
        if results and len(results) > 0:
            return results[0]
        return None
    except Exception as e:
        print(f"[OPERACRM] Error for {id_name}: {e}")
        return None

# Global quality checker instance
quality_checker = ImageQualityChecker()

def verify_flask_auth():
    """Verify Flask authentication"""
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return None
    
    token = token.split(' ')[1]
    payload = verify_token(token)
    return payload

# ============================================================================
# LOCAL CATALOGUE SEARCH (no FileMaker / no Odoo)
# ----------------------------------------------------------------------------
# FileMaker is down and the Odoo (OperaCRM) credentials are dead, which is what
# caused the "Authentication required / Search failed" errors on global search.
# The photo-validator already ships two local image catalogues that map every
# artwork ID to its public image URLs. We search those directly so global search
# works from the exact same data the rest of the app displays.
#   - images_catalog.csv : localisation(url), filename, id, type(MAIN/BACK/DET…)
#   - list-url-id.csv    : url,,,,id   (extra FM/A5 renders keyed by id)
# ============================================================================
import csv as _csv

# Candidate locations: container (/app), local dev (script dir + parent)
_CATALOG_FILES = ['images_catalog.csv', 'list-url-id.csv']
_CATALOG_DIRS = [
    os.path.dirname(os.path.abspath(__file__)),
    '/app',
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
]

_CATALOG = None          # {artwork_id: {'images': {type: [urls]}, 'text': str}}
_CATALOG_IDS = None      # ordered list of ids for stable results

def _find_catalog_file(name):
    for d in _CATALOG_DIRS:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None

def _add_catalog_entry(catalog, aid, url, filename, img_type):
    aid = (aid or '').strip().upper()
    url = (url or '').strip()
    if not aid or not url or not url.lower().startswith('http'):
        return
    img_type = (img_type or 'MAIN').strip().upper() or 'MAIN'
    entry = catalog.setdefault(aid, {'images': {}, 'text': ''})
    urls = entry['images'].setdefault(img_type, [])
    if url not in urls:
        urls.append(url)
    # Build a lowercase searchable blob from id + filenames
    if filename:
        entry['text'] += ' ' + filename.lower()

def _load_catalog():
    """Load + index the local image catalogues once (in-memory)."""
    global _CATALOG, _CATALOG_IDS
    if _CATALOG is not None:
        return _CATALOG
    catalog = {}

    # images_catalog.csv -> header: localisation,filename,id,type
    p = _find_catalog_file('images_catalog.csv')
    if p:
        try:
            with open(p, newline='', encoding='utf-8', errors='replace') as f:
                reader = _csv.DictReader(f)
                for row in reader:
                    _add_catalog_entry(
                        catalog,
                        row.get('id'),
                        row.get('localisation'),
                        row.get('filename'),
                        row.get('type'),
                    )
            print(f"[LOCAL-SEARCH] Loaded images_catalog.csv from {p}")
        except Exception as e:
            print(f"[LOCAL-SEARCH] Failed reading {p}: {e}")

    # list-url-id.csv -> no header, columns: url,,,,id
    p = _find_catalog_file('list-url-id.csv')
    if p:
        try:
            with open(p, newline='', encoding='utf-8', errors='replace') as f:
                for parts in _csv.reader(f):
                    if len(parts) < 5:
                        continue
                    url = parts[0]
                    aid = parts[4]
                    if not aid or not url:
                        continue
                    fname = url.rsplit('/', 1)[-1]
                    _add_catalog_entry(catalog, aid, url, fname, 'MAIN')
        except Exception as e:
            print(f"[LOCAL-SEARCH] Failed reading {p}: {e}")

    # Make the id itself part of the searchable text, and record the artist
    # prefix (leading letters of the ID, e.g. CHAGMA in CHAGMA-46538) so an
    # artist-name query like "Chagall" can match works that only carry the code.
    for aid, entry in catalog.items():
        entry['text'] = (aid.lower() + entry['text'])
        m = re.match(r'^([A-Za-z]+)', aid)
        entry['prefix'] = (m.group(1).lower() if m else '')

    # ── Index validated artwork IDs from the database ──────────────────────
    # Many artworks are validated in photo-validator but never exported to the
    # CSV catalogues. Add them so they appear in search results.
    _db_paths = [os.path.join(d, 'data', 'photo_validator.db') for d in _CATALOG_DIRS]
    _db_paths += [os.path.join(d, 'photo_validator.db') for d in _CATALOG_DIRS]
    _db_added_ids = set()
    for _dbp in _db_paths:
        if os.path.exists(_dbp):
            try:
                import sqlite3 as _sqlite3
                _conn = _sqlite3.connect(_dbp)
                _conn.row_factory = _sqlite3.Row
                _rows = _conn.execute(
                    "SELECT DISTINCT artwork_id, photo_id, classification FROM photo_validations "
                    "WHERE artwork_id IS NOT NULL AND artwork_id != '' AND status = 'validated'"
                ).fetchall()
                _conn.close()
                _added = 0
                for _row in _rows:
                    _aid = (_row['artwork_id'] or '').strip().upper()
                    _pid = (_row['photo_id'] or '').strip()
                    _cls = (_row['classification'] or '').strip()
                    if not _aid:
                        continue
                    if _aid not in catalog:
                        catalog[_aid] = {'images': {}, 'text': _aid.lower(), 'cls_labels': {}}
                        _added += 1
                        _db_added_ids.add(_aid)
                    # Add filename text for searchability
                    if _pid:
                        _fname = _pid.rsplit('/', 1)[-1]
                        catalog[_aid]['text'] += ' ' + _fname.lower()
                        # Derive artwork title from first meaningful filename
                        _entry = catalog[_aid]
                        _derived = _derive_title_from_photo(_fname, _aid)
                        _existing = _entry.get('_title', '')
                        # Prefer longer, more descriptive titles (skip short artifact-only ones)
                        if _derived and (not _existing or len(_derived) > len(_existing)):
                            _entry['_title'] = _derived
                    # Store classification label per photo_id for later image matching
                    if _cls and _pid:
                        _entry = catalog[_aid]
                        if 'cls_labels' not in _entry:
                            _entry['cls_labels'] = {}
                        _entry['cls_labels'][_pid.rsplit('/', 1)[-1]] = _cls
                if _added:
                    print(f"[LOCAL-SEARCH] Indexed {_added} additional artwork IDs from {_dbp}")
                break  # only use first found DB
            except Exception as _e:
                print(f"[LOCAL-SEARCH] DB lookup failed for {_dbp}: {_e}")

    # ── Link local photos for DB-only artworks ────────────────────────────
    # Look for photos by artwork ID prefix (fast: artwork-driven, not file-scan).
    if _db_added_ids:
        _photo_dirs = ['/app/photos/FM', '/app/photos/300', '/app/photos/A5']
        _linked = 0
        # Cache directory listings per dir (scanned once)
        _dir_cache = {}
        for _pdir in _photo_dirs:
            if not os.path.isdir(_pdir):
                continue
            try:
                _files = [f for f in os.listdir(_pdir) if os.path.isfile(os.path.join(_pdir, f))]
                _dir_cache[_pdir] = _files
            except Exception:
                _dir_cache[_pdir] = []
        for _aid in _db_added_ids:
            _upper = _aid.upper()
            for _pdir in _photo_dirs:
                _files = _dir_cache.get(_pdir, [])
                for _fname in _files:
                    if _fname.upper().startswith(_upper + '_') or _fname.upper().startswith(_upper + '.'):
                        _ptype = os.path.basename(_pdir)
                        _url = f'https://images.operagallery.com/{_ptype}/{_fname}'
                        img_key = 'MAIN' if _ptype == 'FM' else _ptype.upper()
                        entry = catalog[_aid]
                        entry['images'].setdefault(img_key, [])
                        if _url not in entry['images'][img_key]:
                            entry['images'][img_key].append(_url)
                            _linked += 1
        if _linked:
            print(f"[LOCAL-SEARCH] Linked {_linked} local photos for DB-only artworks")

    # Compute prefix + text for any entries added from DB (CSV ones done above)
    for aid in _db_added_ids:
        entry = catalog.get(aid)
        if entry:
            m = re.match(r'^([A-Za-z]+)', aid)
            entry['prefix'] = (m.group(1).lower() if m else '')

    _CATALOG = catalog
    _CATALOG_IDS = sorted(catalog.keys())
    print(f"[LOCAL-SEARCH] Catalogue ready: {len(_CATALOG)} artworks indexed")
    return _CATALOG

# Preferred order when picking the primary image / listing the gallery
_IMG_TYPE_ORDER = ['MAIN', 'FRONT', 'OTHER', 'DET', 'INSITU', 'BACK',
                   'LEFT', 'FRONTRIGHT', 'FRAME', 'PERS']

def _derive_title_from_photo(fname, aid):
    """Extract human-readable title from a photo filename like PICAPA-55498_Tete_dhomme_1965_MAIN.jpg"""
    base = fname.rsplit('.', 1)[0]
    # remove the id prefix
    base = re.sub(r'^' + re.escape(aid) + r'[_\- ]?', '', base, flags=re.I)
    # remove known classification suffixes
    for _sfx in ['_MAIN', '_FRAME', '_BACK', '_FRONT', '_LEFT', '_RIGHT', '_PERS',
                 '_INSITU', '_SIGN', '_DET1', '_DET2', '_SCALE', '_OTHERS',
                 '_MAIN_HR', '_MAIN_LR', '_FRAMED', '_UNFRAMED', '_RENDER',
                 '_BLUR', '_SCALE', '_INSTALL', '_WEB300', '_A5', '_HR', '_LR',
                 '_BACKFRAME', '_FRONTRIGHT', '_SIGNATURE', '_thumb', '_INSITU_RENDER']:
        base = re.sub(re.escape(_sfx) + r'$', '', base, flags=re.I)
    # cleanup
    base = re.sub(r'[_\-]+', ' ', base).strip()
    base = base.replace('  ', ' ')
    return base

def _derive_title(entry, aid):
    """Best-effort human title from the first filename (ID + extension stripped)."""
    # Use DB-derived title if available
    if entry.get('_title'):
        return entry['_title']
    for t in _IMG_TYPE_ORDER + list(entry['images'].keys()):
        for url in entry['images'].get(t, []):
            fname = url.rsplit('/', 1)[-1]
            base = fname.rsplit('.', 1)[0]
            # remove the id prefix and separators
            base = re.sub(r'^' + re.escape(aid) + r'[_\- ]?', '', base, flags=re.I)
            base = re.sub(r'[_\-]+', ' ', base).strip()
            if base:
                return base
    return ''

def _ordered_image_fields(entry):
    """Return image_fields (type -> newline-joined urls) in a sensible order."""
    fields = {}
    keys = [t for t in _IMG_TYPE_ORDER if t in entry['images']]
    keys += [t for t in entry['images'] if t not in keys]
    for t in keys:
        urls = entry['images'][t]
        if urls:
            fields[t] = '\n'.join(urls)
    return fields

def _primary_image(entry):
    for t in _IMG_TYPE_ORDER:
        if entry['images'].get(t):
            return entry['images'][t][0]
    for t, urls in entry['images'].items():
        if urls:
            return urls[0]
    return None

def _all_image_urls(entry):
    """Flat, de-duplicated list of every image URL for an artwork (ordered)."""
    urls = []
    keys = [t for t in _IMG_TYPE_ORDER if t in entry['images']]
    keys += [t for t in entry['images'] if t not in keys]
    for t in keys:
        for u in entry['images'][t]:
            if u not in urls and 'storage.googleapis.com' not in u:
                urls.append(u)
    return urls

def _build_image_labels(entry, all_urls):
    """Build URL → human-readable label mapping from DB cls_labels."""
    _cls_map = entry.get('cls_labels', {})
    if not _cls_map:
        return {}
    _lower_map = {k.lower(): v for k, v in _cls_map.items()}
    labels = {}
    for url in all_urls:
        fname = url.rsplit('/', 1)[-1]
        fname_lower = fname.lower()
        label = _lower_map.get(fname_lower, '')
        if not label:
            fname_noext = fname.rsplit('.', 1)[0].lower()
            for k_lower, v in _lower_map.items():
                k_noext = k_lower.rsplit('.', 1)[0] if '.' in k_lower else k_lower
                if fname_noext.startswith(k_noext) or k_noext in fname_noext:
                    label = v
                    break
        labels[url] = label or fname_noext
    return labels

def _build_artwork(aid, entry, detailed=False):
    """Shape one artwork the way the frontend expects."""
    main = _primary_image(entry)
    img_count = sum(len(u) for u in entry['images'].values())
    # Derive artist display name from prefix when real name unavailable
    prefix = entry.get('prefix', '')
    artist_display = prefix.title() if prefix else ''
    art = {
        'id': aid,
        'IdName': aid,
        'name': aid,
        'title': _derive_title(entry, aid),
        'artist': artist_display,
        'artist_name': artist_display,
        'year': '',
        'category': '',
        'medium': '',
        'dimensions': '',
        'location': '',
        'description': '',
        'main_picture_hd': main,
        'main_picture': main,
        'image_count': img_count,
        'all_image_urls': _all_image_urls(entry),
        'source': 'LocalCatalogue',
        'status': 'Validated' if img_count > 0 else '',
        'image_labels': _build_image_labels(entry, _all_image_urls(entry)),
    }
    if detailed:
        art['image_fields'] = _ordered_image_fields(entry)
    return art

def _db_fallback_artworks(query=None, limit=200):
    """Fresh DB lookup for recently validated/rejected artworks not yet in cache
    PLUS Odoo fallback for artworks that exist only in Odoo (not validated in DAS)."""
    results = []
    # 1) Local DB
    _db_paths = [os.path.join(d, 'data', 'photo_validator.db') for d in _CATALOG_DIRS]
    _db_paths += [os.path.join(d, 'photo_validator.db') for d in _CATALOG_DIRS]
    for _dbp in _db_paths:
        if os.path.exists(_dbp):
            try:
                import sqlite3 as _sqlite3
                _conn = _sqlite3.connect(_dbp)
                _conn.row_factory = _sqlite3.Row
                if query:
                    like = f'%{query.upper()}%'
                    _rows = _conn.execute(
                        'SELECT DISTINCT artwork_id FROM photo_validations '
                        'WHERE artwork_id IS NOT NULL AND artwork_id != "" '
                        'AND artwork_id LIKE ? LIMIT ?', (like, limit)
                    ).fetchall()
                else:
                    _rows = _conn.execute(
                        'SELECT DISTINCT artwork_id FROM photo_validations '
                        'WHERE artwork_id IS NOT NULL AND artwork_id != "" '
                        'LIMIT ?', (limit,)
                    ).fetchall()
                _conn.close()
                results.extend(r['artwork_id'].strip().upper() for r in _rows if r['artwork_id'])
                break
            except Exception:
                pass
    # 2) Odoo fallback (cached, auth cached, only for ID-like queries)
    if query and not results and re.search(r'\d', query):
        _now = time.time()
        _odoo_cache_key = f'odoo_{query.lower()}_{limit}'
        # Module-level Odoo cache with 5min TTL
        if not hasattr(_db_fallback_artworks, '_odoo_cache'):
            _db_fallback_artworks._odoo_cache = {}
            _db_fallback_artworks._odoo_uid = None
            _db_fallback_artworks._odoo_uid_ts = 0
        _cache = _db_fallback_artworks._odoo_cache
        if _odoo_cache_key in _cache:
            _cached = _cache[_odoo_cache_key]
            if _now - _cached[0] < 300:  # 5min TTL
                return _cached[1]
        try:
            import xmlrpc.client as _xc
            _odoo_url = 'https://operacrm.com'
            _odoo_db = 'odoo_15'
            _odoo_user = 'surafelwubshet7@gmail.com'
            _odoo_pass = 'Surafell'
            # Reuse auth for 25 min
            _uid = _db_fallback_artworks._odoo_uid
            if not _uid or _now - _db_fallback_artworks._odoo_uid_ts > 1500:
                _common = _xc.ServerProxy(f'{_odoo_url}/xmlrpc/2/common')
                _uid = _common.authenticate(_odoo_db, _odoo_user, _odoo_pass, {})
                _db_fallback_artworks._odoo_uid = _uid
                _db_fallback_artworks._odoo_uid_ts = _now
            _models = _xc.ServerProxy(f'{_odoo_url}/xmlrpc/2/object')
            _img_fields = ['main_super_picture_hd', 'main_web_picture', 'frame_picture',
                          'back_pictures', 'perspective_url', 'detail_1_url', 'detail_2_url',
                          'in_situ_hr', 'other_url', 'signatures_pictures']
            _recs = _models.execute_kw(_odoo_db, _uid, _odoo_pass,
                'product.template', 'search_read',
                [[['IdName', 'ilike', f'%{query}%']]],
                {'fields': ['IdName'] + _img_fields, 'limit': limit})
            for _r in (_recs or []):
                _idn = _r.get('IdName', '')
                if _idn:
                    _idn = _idn.strip().upper()
                    results.append(_idn)
                    # Build catalog entry with Odoo images so thumbnails show
                    _imgs = {}
                    for _fld in _img_fields:
                        _val = _r.get(_fld)
                        if _val and isinstance(_val, str) and _val.startswith('http') and 'storage.googleapis.com' not in _val:
                            _imgs.setdefault('MAIN', []).append(_val)
                    if _idn not in _CATALOG:
                        m = re.match(r'^([A-Za-z]+)', _idn)
                        _CATALOG[_idn] = {
                            'images': _imgs,
                            'text': _idn.lower(),
                            'prefix': (m.group(1).lower() if m else ''),
                            '_title': ''
                        }
                    elif _imgs and not _CATALOG[_idn].get('images'):
                        _CATALOG[_idn]['images'] = _imgs
            _cache[_odoo_cache_key] = (_now, results)  # cache for 5min
        except Exception:
            pass
    return results

def local_artwork_by_id(artwork_id):
    """Exact/loose lookup of a single artwork by ID from the local catalogue."""
    catalog = _load_catalog()
    aid = (artwork_id or '').strip().upper()
    if not aid:
        return None
    if aid in catalog:
        return _build_artwork(aid, catalog[aid], detailed=True)
    # loose: allow ARTIST-123 vs ARTIST123 and partial id
    norm = aid.replace('-', '')
    for cid, entry in catalog.items():
        if cid.replace('-', '') == norm:
            return _build_artwork(cid, entry, detailed=True)
    # last resort: prefix / contains match, return first
    for cid in _CATALOG_IDS:
        if aid in cid:
            return _build_artwork(cid, catalog[cid], detailed=True)
    # DB fallback: check for recently validated/rejected artwork not in cache
    db_ids = _db_fallback_artworks(aid, limit=1)
    if db_ids:
        _db_aid = db_ids[0]
        # Use enriched catalog entry if available, else create lightweight one
        entry = catalog.get(_db_aid)
        if not entry:
            m = re.match(r'^([A-Za-z]+)', _db_aid)
            entry = {'images': {}, 'text': _db_aid.lower(),
                     'prefix': (m.group(1).lower() if m else ''), '_title': ''}
        return _build_artwork(_db_aid, entry, detailed=True)
    return None

def local_search_artworks(query, limit=200):
    """Global text search over the local catalogue (id + filenames)."""
    catalog = _load_catalog()
    q = (query or '').strip().lower()
    if not q:
        return []
    terms = [t for t in q.split() if t]
    # Terms long enough to match an artist code by its first 4 letters
    # (OperaGallery codes are lastname-first, e.g. CHAG… = Chagall, PICA… = Picasso).
    artist_terms = [t for t in terms if len(t) >= 4]
    # Rank artist-code / ID matches (what the user actually means by e.g.
    # "Picasso" -> PICAPA-*) ABOVE free-text title matches (e.g. a Denzan work
    # titled "... after Picasso"). Otherwise title noise buries the real hits.
    primary, secondary = [], []
    for aid in _CATALOG_IDS:
        entry = catalog[aid]
        blob = entry['text']
        prefix4 = entry.get('prefix', '')[:4]
        artist_match = bool(prefix4) and any(t[:4] == prefix4 for t in artist_terms)
        id_match = any(t in aid.lower() for t in terms)
        text_match = all(term in blob for term in terms)
        if artist_match or id_match:
            primary.append(aid)
            if limit and len(primary) >= limit:
                break
        elif text_match:
            secondary.append(aid)
    ordered = primary + secondary
    # DB fallback: add newly validated/rejected artworks not yet in cache
    db_fallback = _db_fallback_artworks(query, limit or 200)
    for _db_aid in db_fallback:
        if _db_aid not in ordered:
            ordered.append(_db_aid)
        if _db_aid not in catalog:
            # Create a lightweight entry for this new artwork
            m = re.match(r'^([A-Za-z]+)', _db_aid)
            catalog[_db_aid] = {'images': {}, 'text': _db_aid.lower(),
                                'prefix': (m.group(1).lower() if m else ''), '_title': ''}
    if limit:
        ordered = ordered[:limit]
    return [_build_artwork(aid, catalog[aid], detailed=False) for aid in ordered]

# ============================================================================
# CACHED OPERAGALLERY API FUNCTIONS
# ============================================================================

@cache_search
def cached_search_operacrm_artworks(query, search_type='all', limit=None):
    """Cached version of OperaCRM search"""
    try:
        if not ensure_authenticated():
            print(f"[CACHE] OperaCRM authentication failed")
            return None
        
        print(f"🎯 [OPERACRM] Searching '{query}' (type: {search_type})")
        
        if search_type == 'artist':
            return client.search_by_artist(query, limit or 200)
        elif search_type == 'title' or search_type == 'artwork_name':
            return client.search_by_artwork_name(query, limit or 200)
        elif search_type == 'category':
            return client.search_by_category(query, limit or 200)
        elif search_type == 'artwork_id':
            result = client.search_by_idname(query)
            return [result] if result else []
        else:  # search_type == 'all'
            # Combined search: artist + artwork name
            artist_results = client.search_by_artist(query, limit or 100)
            artwork_results = client.search_by_artwork_name(query, limit or 100)
            
            # Combine and remove duplicates by ID
            all_results = (artist_results or []) + (artwork_results or [])
            seen_ids = set()
            unique_results = []
            for artwork in all_results:
                artwork_id = artwork.get('id')
                if artwork_id not in seen_ids:
                    seen_ids.add(artwork_id)
                    unique_results.append(artwork)
            
            return unique_results
            
    except Exception as e:
        print(f"[CACHE] OperaCRM search error: {e}")
        return None

@cache_medium
def cached_get_operacrm_artwork_by_id(artwork_id):
    """Cached version of OperaCRM artwork by ID"""
    try:
        return get_operacrm_artwork_by_id(artwork_id)
    except Exception as e:
        print(f"[CACHE] OperaCRM artwork error: {e}")
        return None

def format_operacrm_artwork(artwork):
    """Format OperaCRM artwork data for frontend"""
    try:
        if not artwork or not isinstance(artwork, dict):
            return None
        
        # Extract basic info
        artwork_id = artwork.get('idname', artwork.get('IdName', ''))
        name = artwork.get('name', artwork.get('Name', ''))
        artist_name = artwork.get('artist_name', artwork.get('ArtistName', ''))
        category = artwork.get('category_name', artwork.get('Category', ''))
        medium = artwork.get('medium', artwork.get('Medium', ''))
        year = artwork.get('year', artwork.get('Year', ''))
        location = artwork.get('location_name', artwork.get('Location', ''))
        price = artwork.get('price', artwork.get('Price', 0))
        currency = artwork.get('currency', artwork.get('Currency', 'EUR'))
        
        # Format dimensions
        dimensions = ''
        width = artwork.get('width', artwork.get('Width', 0))
        height = artwork.get('height', artwork.get('Height', 0))
        if width and height:
            dimensions = f'{width} x {height} cm'
        
        formatted = {
            'id': artwork.get('id', artwork.get('ID', '')),
            'idname': artwork_id,
            'name': name,
            'artist_name': artist_name,
            'category': category,
            'medium': medium,
            'year': year,
            'dimensions': dimensions,
            'location': location,
            'price': price,
            'currency': currency,
            'status': artwork.get('status', artwork.get('Status', ''))
        }
        
        return formatted
        
    except Exception as e:
        print(f"Error formatting artwork: {e}")
        return None

@operacrm_bp.route('/api/operacrm/search', methods=['GET'])
def search_operacrm():
    """Search for artworks in OperaCRM (simple GET endpoint)"""
    try:
        query = request.args.get('q', '')
        limit = int(request.args.get('limit', 10))
        search_type = request.args.get('type', 'all')
        
        if not query:
            return jsonify({'results': []})
        
        # Use OperaCRM search function
        results = cached_search_operacrm_artworks(query, search_type, limit)
        
        # Format results for frontend
        formatted_results = []
        if results:
            for artwork in results:
                formatted_artwork = format_operacrm_artwork(artwork)
                if formatted_artwork:
                    formatted_results.append(formatted_artwork)
        
        return jsonify({
            'results': formatted_results,
            'total': len(formatted_results)
        })
        
    except Exception as e:
        print(f"OperaCRM search error: {e}")
        return jsonify({'error': str(e)}), 500

@operacrm_bp.route('/api/artworks/search', methods=['POST'])
@operacrm_bp.route('/api/artworks/search-new', methods=['POST'])
def search_artworks():
    """
    Rechercher des œuvres d'art dans OperaGallery (FileMaker)
    """
    print(f"🌟🌟🌟 [ENDPOINT-HIT] /api/artworks/search appelé ! Headers: {dict(request.headers)} 🌟🌟🌟")
    
    # Verify authentication
    auth_result = verify_flask_auth()
    print(f"[SEARCH] Auth result: {auth_result}")
    
    if not auth_result:
        print("[SEARCH] Authentication failed")
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        data = request.get_json()
        print(f"[SEARCH] Received data: {data}")
        
        if not data:
            print("[SEARCH] No JSON data received")
            return jsonify({'error': 'Invalid request data'}), 400
        
        query = data.get('query', '').strip()
        search_type = data.get('searchType', 'all')
        limit = data.get('limit', 200)  # Limite normale restaurée
        if limit is not None:
            limit = int(limit)
        
        if not query:
            print("[SEARCH] No search parameters provided, returning empty results")
            return jsonify({
                'success': True,
                'artworks': [],
                'total': 0,
                'query': '',
                'source': 'OperaGallery',
                'search_type': search_type
            })
        
        print(f"[SEARCH] Searching OperaGallery with query: '{query}', limit: {limit if limit else 'UNLIMITED'}")
        
        # ⭐ TRACKER TOUTES LES RECHERCHES
        try:
            from artist_indexer import artist_indexer as indexer
            # Enregistrer cette recherche dans les stats
            if query in indexer.search_requests:
                indexer.search_requests[query] += 1
            else:
                indexer.search_requests[query] = 1
            print(f"[SEARCH-TRACKING] ✅ Recherche trackée: '{query}' ({indexer.search_requests[query]}x)")
        except Exception as e:
            print(f"[SEARCH-TRACKING] ❌ Erreur tracking: {e}")
        
        # 🔥 BYPASS COMPLET - STRATÉGIE HYBRIDE INTELLIGENTE
        # Respect the requested search type so "global" stays broad and
        # doesn't get downgraded to an artist-only search for single words.
        if search_type == 'artist':
            search_mode = 'artist'
            print(f"🎨 [BYPASS] Recherche ARTISTE optimisée (Méthode 2) pour '{query}'")
        elif search_type == 'artwork_id':
            search_mode = 'artwork_id'
            print(f"🆔 [BYPASS] Recherche ID ciblée pour '{query}'")
        elif search_type == 'title':
            search_mode = 'title'
            print(f"🎨 [BYPASS] Recherche TITRE ciblée pour '{query}'")
        else:
            search_mode = 'all'
            print(f"🔍 [BYPASS] Recherche GLOBALE standard (Méthode 1) pour '{query}'")

        # ── Local-catalogue routing (no FileMaker / no Odoo) ──────────────────
        # FM is down and the Odoo creds are dead, which produced the auth errors
        # on global search. Serve results straight from the local image
        # catalogues (images_catalog.csv + list-url-id.csv) — the same data the
        # rest of photo-validator already displays. Search is driven by the
        # artwork ID (and filename text) that photo-validator already has.
        import re as _re
        _q = (query or '').strip()
        _looks_like_id = bool(_re.match(r'^[A-Za-z]+-?\d+', _q))
        if search_type in ('id', 'artwork_id') or search_mode == 'artwork_id' or _looks_like_id:
            try:
                _art = local_artwork_by_id(_q)
                if _art:
                    return jsonify({'success': True, 'artwork': _art,
                                    'artworks': [_art], 'total': 1, 'query': query,
                                    'source': 'LocalCatalogue', 'search_type': 'artwork_id'})
                # No exact ID match → fall through to text search
            except Exception as _e:
                print(f"[SEARCH] Local by-id search failed: {_e}")
                return jsonify({'error': f'Search failed: {_e}'}), 500

        # Text search (also serves as fallback for failed ID lookups)
        try:
            _arts = local_search_artworks(query, limit or 200) or []
            return jsonify({'success': True, 'artworks': _arts,
                            'total': len(_arts), 'query': query,
                            'source': 'LocalCatalogue', 'search_type': search_mode})
        except Exception as _e:
            print(f"[SEARCH] Local search failed: {_e}")
            return jsonify({'error': f'Search failed: {_e}'}), 500

        try:
            # ── FileMakerClient replaces raw requests calls ───────────────────
            # Fixed June 2026 bugs: guaranteed logout (context manager), 952
            # auto-relogin, mandatory timeouts, and exponential-backoff retries.
            from fm_client import FileMakerClient, FMNotFound

            # Build search plan: (label, layout, query_list, using_artist_layout)
            if search_mode == 'artist':
                searches = [
                    ('artist', 'CrmRecordArtworks', [{'ArtistName3': f'*{query}*'}], True)
                ]
            elif search_mode == 'artwork_id':
                normalized_query = query.strip().upper()
                searches = [
                    ('artwork_id', 'CrmRecordArtworks', [{'IdNameIndexed2': f'*{normalized_query}*'}], True)
                ]
            elif search_mode == 'title':
                searches = [
                    ('title', 'CrmRecordArtworks', [{'Name': f'*{query}*'}], True)
                ]
            else:
                normalized_query = query.strip().upper()
                # Global search should cover the broad indexed field first, then
                # explicitly try title, artwork ID and artist name to catch misses.
                searches = [
                    ('global_index',    'CRMSearchArtworks', [{'CrmSearchArtwork':  f'*{query}*'}],            False),
                    ('title_fallback',  'CrmRecordArtworks', [{'Name':              f'*{query}*'}],            True),
                    ('id_fallback',     'CrmRecordArtworks', [{'IdNameIndexed2':    f'*{normalized_query}*'}], True),
                    ('artist_fallback', 'CrmRecordArtworks', [{'ArtistName3':       f'*{query}*'}],            True),
                ]

            search_results = []
            seen_record_ids = set()

            # One FM session for all searches + enrichment — closed automatically
            # by __exit__ even if an exception is raised mid-loop.
            with FileMakerClient() as fm:
                for label, layout, query_list, using_artist_layout in searches:
                    print(f"🔥 [BYPASS] Recherche {label} avec query: {query_list}")
                    try:
                        current_results = fm.find(layout, query_list, limit=limit if limit else 200)
                    except FMNotFound:
                        print(f"🔥 [BYPASS] Aucun résultat pour {label}")
                        current_results = []

                    print(f"🔥 [BYPASS] ✅ {len(current_results)} résultats trouvés pour {label}")
                    for record in current_results:
                        record_id = str(record.get('recordId', 'unknown'))
                        if record_id in seen_record_ids:
                            continue
                        seen_record_ids.add(record_id)
                        record['_using_artist_layout'] = using_artist_layout
                        search_results.append(record)

                    if limit and len(search_results) >= limit:
                        search_results = search_results[:limit]
                        break

                if search_results:
                    print(f"🔥 [BYPASS] ✅ {len(search_results)} résultats uniques retenus")

                    # Traitement adapté selon le layout utilisé
                    formatted_results = []
                    for record in search_results:
                        field_data = record.get('fieldData', {})
                        record_id = record.get('recordId', 'unknown')
                        using_artist_layout = record.get('_using_artist_layout', False)

                        if using_artist_layout:
                            # 🎨 TRAITEMENT ARTISTE: Données directes + enrichissement minimal
                            enriched_data = {
                                'medium': field_data.get('Medium', ''),
                                'dimensions': f"{field_data.get('SizeH', '')}x{field_data.get('SizeL', '')}x{field_data.get('SizeP', '')}".replace('xx', ''),
                                'location': field_data.get('Region', ''),
                                'status': field_data.get('Status', ''),
                                'price': field_data.get('PriceRef', ''),
                                'currency': field_data.get('CurrencyRef', ''),
                                'category': field_data.get('Category', ''),
                                'id_name': field_data.get('IdNameIndexed2', str(record_id)),
                                'mainfm_url': '',
                                'certificate_url': '',
                                'certificate_wording': '',
                                'description': ''
                            }

                            # Enrichissement minimal pour images et certificats uniquement
                            try:
                                artwork_record = fm.get_record('Artworks', record_id)
                                artwork_fields = artwork_record.get('fieldData', {})
                                enriched_data['mainfm_url'] = artwork_fields.get('MAINFM', '')
                                enriched_data['certificate_url'] = artwork_fields.get('CertificateFMUrl', '')
                                enriched_data['certificate_wording'] = artwork_fields.get('CertificateWording', '')
                                enriched_data['description'] = artwork_fields.get('DescriptionEn', '')
                                print(f"🎨 [ARTIST-ENRICH] {record_id}: MAINFM={bool(enriched_data['mainfm_url'])}, Cert={bool(enriched_data['certificate_url'])}, Prix={enriched_data['price']} {enriched_data['currency']}")
                            except Exception as e:
                                print(f"🎨 [ARTIST-ENRICH] Erreur pour {record_id}: {e}")

                        else:
                            # 🔍 TRAITEMENT GLOBAL: Enrichissement complet (méthode originale)
                            enriched_data = {}
                            try:
                                artwork_record = fm.get_record('Artworks', record_id)
                                artwork_fields = artwork_record.get('fieldData', {})
                                enriched_data = {
                                    'mainfm_url': artwork_fields.get('MAINFM', ''),
                                    'medium': artwork_fields.get('Medium', ''),
                                    'dimensions': artwork_fields.get('SizeArtwork', ''),
                                    'location': artwork_fields.get('Location', ''),
                                    'status': artwork_fields.get('Status', ''),
                                    'description': artwork_fields.get('DescriptionEn', ''),
                                    'certificate_url': artwork_fields.get('CertificateFMUrl', ''),
                                    'certificate_wording': artwork_fields.get('CertificateWording', ''),
                                    'id_name': artwork_fields.get('IdName', str(record_id)),
                                    'price': '',
                                    'currency': '',
                                    'category': 'Artwork'
                                }
                                print(f"🔍 [GLOBAL-ENRICH] {record_id}: MAINFM={bool(enriched_data['mainfm_url'])}, Cert={bool(enriched_data['certificate_url'])}")
                            except Exception as e:
                                print(f"🔍 [GLOBAL-ENRICH] Erreur pour {record_id}: {e}")

                        formatted_artwork = {
                            'id': str(record_id),
                            'IdName': enriched_data.get('id_name', str(record_id)),
                            'title': field_data.get('Name', ''),
                            'artist': field_data.get('ArtistName3', ''),
                            'year': field_data.get('Year', '') or field_data.get('Artworkyear', ''),
                            'category': enriched_data.get('category', 'Artwork'),
                            'medium': enriched_data.get('medium', ''),
                            'description': enriched_data.get('description', ''),
                            'dimensions': enriched_data.get('dimensions', ''),
                            'location': enriched_data.get('location', ''),
                            'status': enriched_data.get('status', ''),
                            'main_picture_hd': enriched_data.get('mainfm_url', ''),
                            'mainfm_url': enriched_data.get('mainfm_url', ''),
                            'image_count': 1 if enriched_data.get('mainfm_url') else 0,
                            'record_id': record_id,
                            'source': f'FileMaker-{"Artist" if using_artist_layout else "Global"}-Hybrid'
                        }

                        # Ajouter prix si disponible (recherche artiste uniquement)
                        if using_artist_layout and enriched_data.get('price'):
                            formatted_artwork['price'] = enriched_data['price']
                            formatted_artwork['currency'] = enriched_data.get('currency', '')

                        # Ajouter certificats si disponibles
                        if enriched_data.get('certificate_url'):
                            formatted_artwork['certificate_url'] = enriched_data['certificate_url']
                            formatted_artwork['filemakerData'] = {
                                'CertificateFMUrl': enriched_data['certificate_url']
                            }
                            if enriched_data.get('certificate_wording'):
                                formatted_artwork['certificate_wording'] = enriched_data['certificate_wording']
                                formatted_artwork['filemakerData']['CertificateWording'] = enriched_data['certificate_wording']

                        formatted_results.append(formatted_artwork)

                    # FM session closed automatically by context manager __exit__
                    return jsonify({
                        'success': True,
                        'artworks': formatted_results,
                        'count': len(formatted_results),
                        'debug_info': f'Direct FileMaker search: {len(formatted_results)} results'
                    })
                else:
                    print(f"🔥 [BYPASS] Aucun résultat direct trouvé pour '{query}'")

        except Exception as e:
            import traceback
            print(f"🔥 [BYPASS] Erreur: {e}")
            print(f"🔥 [BYPASS] Traceback complet:")
            traceback.print_exc()
            print(f"🔥 [BYPASS] Fallback vers ancien système")
        
        # Fallback ancien système si le nouveau échoue
        results = []
        max_retries = 2  # Réduit encore
        
        for attempt in range(max_retries):
            try:
                print(f"🚀 [SEARCH] Tentative {attempt + 1}/{max_retries} pour '{query}' (ANCIEN SYSTÈME)")
                
                results = cached_search_operacrm_artworks(query, search_type=search_type, limit=limit)
                print(f"[SEARCH] Succès: {len(results) if results else 0} résultats trouvés")
                break
                
            except Exception as e:
                print(f"[SEARCH] Tentative {attempt + 1} échouée: {str(e)}")
                if attempt == max_retries - 1:
                    print(f"[SEARCH] Toutes les tentatives ont échoué")
                    results = []
                else:
                    import time
                    time.sleep(1)
        
        print(f"[SEARCH] OperaGallery search returned {len(results) if results else 0} results")
        
        # DEBUG: Analyser pourquoi il n'y a pas de résultats
        if not results:
            print(f"[SEARCH] DEBUG: Aucun résultat pour '{query}' - vérifier si le nom est dans le proxy ou si l'API fonctionne")
        
        # Traitement des résultats
        formatted_results = []
        if results:
            print(f"[SEARCH] Starting to format {len(results)} results")
            
            for artwork in results:
                try:
                    # Obtenir toutes les URLs d'images depuis les nouveaux champs
                    images = artwork.get('images', {})
                    # 🔧 CORRECTION: Utiliser MAINFM (majuscules) et fallback vers Picture et nouveaux champs
                    mainfm_url = (images.get('primary_image') or 
                                 images.get('mainfm_url') or 
                                 artwork.get('MAINFM', '') or 
                                 artwork.get('Picture', '') or
                                 artwork.get('MAIN300', '') or
                                 artwork.get('OTHER300', '') or
                                 artwork.get('DET300', ''))
                    
                    # DEBUG: Vérifier les valeurs réelles dans les champs ID
                    debug_id_values = {
                        'IdName': artwork.get('IdName', 'MISSING'),
                        'id_name': artwork.get('id_name', 'MISSING'), 
                        'id': artwork.get('id', 'MISSING'),
                        'record_id': artwork.get('record_id', 'MISSING')
                    }
                    print(f"[DEBUG-ID] Valeurs ID réelles: {debug_id_values}")
                    
                    # Extraire l'ID de la meilleure source possible
                    artwork_id = (artwork.get('id_name') or 
                                 artwork.get('IdName') or 
                                 artwork.get('record_id') or 
                                 artwork.get('id') or 
                                 'unknown')
                    
                    print(f"[DEBUG-ID] ID final utilisé: '{artwork_id}'")
                    
                    if not mainfm_url:
                        print(f"[DEBUG-IMG] {artwork_id}: AUCUNE image trouvée - MAINFM='{artwork.get('MAINFM', 'MISSING')}', Picture='{artwork.get('Picture', 'MISSING')}'")
                    else:
                        print(f"[DEBUG-IMG] {artwork_id}: Image trouvée - {mainfm_url[:100]}...")
                    
                    # 🎯 NOUVEAUX CHAMPS D'IMAGES (MAIN300, OTHER300, etc.)
                    image_fields = {
                        'MAIN300': artwork.get('MAIN300', ''),
                        'OTHER300': artwork.get('OTHER300', ''),
                        'DET300': artwork.get('DET300', ''),
                        'INSITU300': artwork.get('INSITU300', ''),
                        'BACK300': artwork.get('BACK300', ''),
                        'FRONT300': artwork.get('FRONT300', ''),
                        'FRAME300': artwork.get('FRAME300', ''),
                        'LEFT300': artwork.get('LEFT300', ''),
                        'FRONTRIGHT300': artwork.get('FRONTRIGHT300', ''),
                        'PERS300': artwork.get('PERS300', '')
                    }
                    
                    # Compter les images disponibles
                    total_images = sum(1 for url in image_fields.values() if url.strip())
                    if mainfm_url:
                        total_images += 1
                    
                    formatted_artwork = {
                        'id': str(artwork.get('record_id', artwork.get('id', 'unknown'))),
                        'IdName': artwork.get('id_name', artwork.get('IdName', '')),
                        'title': artwork.get('artwork_name', artwork.get('title', artwork.get('name', ''))),
                        'artist': artwork.get('artist_name', artwork.get('artist', '')),
                        'year': artwork.get('year', artwork.get('DateYear', '')),
                        'category': artwork.get('category', artwork.get('Category', 'Artwork')),
                        'medium': artwork.get('medium', artwork.get('Medium', '')),
                        'description': artwork.get('description', artwork.get('DescriptionEn', '')),
                        'dimensions': artwork.get('size', artwork.get('dimensions', '')),
                        'price_estimate': f"{artwork.get('PriceEUR', '')} EUR" if artwork.get('PriceEUR') else '',
                        'location': artwork.get('location', artwork.get('GalleryLocation', '')),
                        'status': artwork.get('status', artwork.get('Status', '')),
                        'main_picture_hd': mainfm_url,  # Utiliser directement l'URL MAINFM
                        'image_count': total_images,
                        'created_date': artwork.get('created_date', ''),
                        'updated_date': artwork.get('updated_date', ''),
                        'record_id': artwork.get('record_id', artwork.get('id', 'unknown')),
                        'mainfm_url': mainfm_url,
                        'source': 'OperaGallery',
                        # 🎯 NOUVEAUX CHAMPS D'IMAGES
                        'image_fields': image_fields
                    }
                    
                    # 🎯 ENRICHISSEMENT FileMaker direct pour MAINFM et certificats
                    # OPTIMISATION: Seulement pour les 10 premiers résultats pour éviter les timeouts
                    # NOUVEAU: Enrichir même si il y a déjà une image (pour les certificats)
                    # NOUVEAU: Accepter aussi les IDs numériques (record_id) du layout CRMSearchArtworks
                    should_enrich = (
                        artwork_id != 'unknown' and 
                        len(artwork_id) > 2 and  # Réduire de 3 à 2 pour les IDs numériques
                        (('-' in artwork_id) or artwork_id.isdigit()) and  # Accepter format PICAPA-123 OU IDs numériques
                        len(formatted_results) < 10  # LIMITE: seulement 10 premiers
                    )
                    
                    if should_enrich:
                        try:
                            print(f"[ENRICH] 🔍 Tentative enrichissement FileMaker pour ID: '{artwork_id}' (#{len(formatted_results)+1}/10)")
                            fm_data = get_filemaker_data_direct(artwork_id)
                            if fm_data:
                                fm_mainfm_url = fm_data.get('MAINFM', '')
                                certificate_url = fm_data.get('CertificateFMUrl', '')
                                certificate_wording = fm_data.get('CertificateWording', '')
                                
                                # Enrichir l'image seulement si pas déjà présente
                                if fm_mainfm_url and not mainfm_url:
                                    formatted_artwork['main_picture_hd'] = fm_mainfm_url
                                    formatted_artwork['mainfm_url'] = fm_mainfm_url
                                    formatted_artwork['image_count'] = 1
                                    print(f"[ENRICH] ✅ {artwork_id}: MAINFM récupéré - {fm_mainfm_url[:60]}...")
                                
                                if certificate_url:
                                    formatted_artwork['certificate_url'] = certificate_url
                                    # Ajouter aussi dans filemakerData pour l'affichage frontend
                                    if 'filemakerData' not in formatted_artwork:
                                        formatted_artwork['filemakerData'] = {}
                                    formatted_artwork['filemakerData']['CertificateFMUrl'] = certificate_url
                                    print(f"[ENRICH] ✅ {artwork_id}: Certificat récupéré - URL: {certificate_url[:50]}...")
                                    print(f"[ENRICH] 📋 filemakerData créé pour {artwork_id}: {formatted_artwork['filemakerData']}")
                                    
                                if certificate_wording:
                                    formatted_artwork['certificate_wording'] = certificate_wording
                                    # Ajouter aussi dans filemakerData pour l'affichage frontend
                                    if 'filemakerData' not in formatted_artwork:
                                        formatted_artwork['filemakerData'] = {}
                                    formatted_artwork['filemakerData']['CertificateWording'] = certificate_wording
                                    print(f"[ENRICH] 📜 {artwork_id}: Certificate wording ajouté ({len(certificate_wording)} chars)")
                                    
                        except Exception as enrich_error:
                            print(f"[ENRICH] ❌ Erreur pour {artwork_id}: {enrich_error}")
                    
                    formatted_results.append(formatted_artwork)
                    
                except Exception as format_error:
                    print(f"[SEARCH] Error formatting artwork: {str(format_error)}")
                    continue
        
        return jsonify({
            'success': True,
            'artworks': formatted_results,
            'total': len(formatted_results),
            'query': query,
            'source': 'OperaGallery',
            'search_type': search_type
        })
        
    except Exception as e:
        print(f"[SEARCH] Global error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500


def capture_real_data(artist):
    """Capturer les vraies données d'un artiste pour le fallback (debug)"""
    try:
        # Faire une vraie recherche
        results = cached_search_operagallery_artworks(artist, limit=10)
        
        if results:
            # Formater pour le fallback  
            fallback_data = []
            for artwork in results[:5]:  # Prendre les 5 premiers
                images = artwork.get('images', {})
                # 🔧 CORRECTION: Utiliser MAINFM (majuscules) et fallback vers Picture
                mainfm_url = images.get('primary_image') or images.get('mainfm_url') or artwork.get('MAINFM', '') or artwork.get('Picture', '')
                
                fallback_data.append({
                    "record_id": artwork.get('record_id', 'unknown'),
                    "artist_name": artwork.get('artist_name', ''),
                    "artwork_name": artwork.get('artwork_name', ''),
                    "year": artwork.get('year', ''),
                    "id_name": artwork.get('id_name', ''),
                    "medium": artwork.get('medium', ''),
                    "size": artwork.get('size', ''),
                    "location": artwork.get('location', ''),
                    "status": artwork.get('status', ''),
                    "mainfm": mainfm_url,
                    "images": {
                        "primary_image": mainfm_url,
                        "mainfm_url": mainfm_url
                    }
                })
            
            return jsonify({
                'success': True,
                'artist': artist,
                'fallback_data': fallback_data,
                'count': len(fallback_data)
            })
        else:
            return jsonify({
                'success': False,
                'error': f'No results found for {artist}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to capture data: {str(e)}'
        }), 500

@operacrm_bp.route('/api/admin/artist-indexing/status', methods=['GET'])
def get_indexing_status():
    """Statut de l'indexation automatique (Admin)"""
    auth_result = verify_flask_auth()
    if not auth_result or auth_result.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        from artist_indexer import artist_indexer as indexer
        
        status = {
            'active': indexer.indexing_active,
            'last_index_times': {
                artist: time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp.timestamp()))
                for artist, timestamp in indexer.last_index_time.items()
            },
            'interval_minutes': indexer.index_interval // 60,
            'total_artists': len(indexer.last_index_time)
        }
        
        return jsonify({
            'success': True,
            'status': status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get status: {str(e)}'
        }), 500

@operacrm_bp.route('/api/admin/artist-indexing/test', methods=['GET'])
def test_famous_artists():
    """Test simple pour vérifier les artistes célèbres"""
    try:
        from artist_indexer import FAMOUS_ARTISTS
        return jsonify({
            'success': True,
            'total': len(FAMOUS_ARTISTS),
            'artists': FAMOUS_ARTISTS,
            'sample': FAMOUS_ARTISTS[:10]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@operacrm_bp.route('/api/admin/artist-indexing/artists', methods=['GET'])
def get_indexed_artists():
    """Liste des artistes indexés et informations sur le système de cache quotidien (Admin)"""
    auth_result = verify_flask_auth()
    if not auth_result or auth_result.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        from artist_indexer import artist_indexer as indexer, FAMOUS_ARTISTS
        from filemaker_cache_service import cache_service
        
        # Debug: vérifier l'import
        print(f"[DEBUG] FAMOUS_ARTISTS imported: {len(FAMOUS_ARTISTS)} artists")
        print(f"[DEBUG] First 5 artists: {FAMOUS_ARTISTS[:5]}")
        
        # Obtenir les stats du système de cache quotidien
        stats = indexer.get_indexing_stats()
        print(f"[DEBUG] Indexer stats: {stats}")
        print(f"[DEBUG] Search requests: {indexer.search_requests}")
        print(f"[DEBUG] Total searches: {sum(indexer.search_requests.values())}")
        
        # Informations sur le système de cache quotidien
        daily_cache_info = {
            'name': 'Daily Cache System',
            'last_indexed': 'Updates daily at 4AM',
            'artwork_count': 0,
            'has_cache': True
        }
        
        # Compter les recherches récentes dans le cache
        total_searches = stats.get('total_searches', 0)
        unique_searches = stats.get('unique_searches', 0)
        
        result = {
            'success': True,
            'artists': [daily_cache_info],  # Un seul "artiste" représentant le système
            'daily_cache_stats': {
                'system_active': True,
                'cache_duration': '24 hours',
                'next_refresh': '4:00 AM daily',
                'total_famous_artists': len(FAMOUS_ARTISTS),
                'unique_famous_artists': len(set([name.lower() for name in FAMOUS_ARTISTS])),
                'total_searches': total_searches,
                'unique_searches': unique_searches,
                'search_requests': stats.get('search_requests', {}),
                'famous_artists_list': FAMOUS_ARTISTS  # Liste complète des 145 artistes
            }
        }
        
        print(f"[DEBUG] API Response keys: {result.keys()}")
        print(f"[DEBUG] daily_cache_stats keys: {result['daily_cache_stats'].keys()}")
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get artists: {str(e)}'
        }), 500

@operacrm_bp.route('/api/admin/artist-indexing/add', methods=['POST'])
def add_artist_to_index():
    """Ajouter un artiste à indexer (Admin)"""
    auth_result = verify_flask_auth()
    if not auth_result or auth_result.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        artist_name = data.get('artist_name', '').strip()
        
        if not artist_name:
            return jsonify({'error': 'Artist name is required'}), 400
        
        from artist_indexer import artist_indexer as indexer
        
        # Indexer immédiatement l'artiste
        artworks_count = indexer.index_artist_now(artist_name)
        
        return jsonify({
            'success': True,
            'message': f'Artist {artist_name} indexed successfully',
            'artworks_count': artworks_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to add artist: {str(e)}'
        }), 500

@operacrm_bp.route('/api/admin/artist-indexing/remove', methods=['POST'])
def remove_artist_from_index():
    """Supprimer un artiste de l'index (Admin)"""
    auth_result = verify_flask_auth()
    if not auth_result or auth_result.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        data = request.get_json()
        artist_name = data.get('artist_name', '').strip()
        
        if not artist_name:
            return jsonify({'error': 'Artist name is required'}), 400
        
        from artist_indexer import artist_indexer as indexer
        from filemaker_cache_service import cache_service
        
        # Supprimer de la liste des artistes indexés
        if artist_name in indexer.last_index_time:
            del indexer.last_index_time[artist_name]
        
        # Supprimer du cache
        if cache_service.cache_enabled:
            cache_key = f"operagallery_search:{artist_name}"
            cache_service.redis_client.delete(cache_key)
        
        return jsonify({
            'success': True,
            'message': f'Artist {artist_name} removed from index'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to remove artist: {str(e)}'
        }), 500

@operacrm_bp.route('/api/admin/artist-indexing/start', methods=['POST'])
def start_indexing():
    """Redémarrer l'indexation automatique (Admin)"""
    auth_result = verify_flask_auth()
    if not auth_result or auth_result.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        from artist_indexer import artist_indexer as indexer
        
        # Redémarrer l'indexation
        indexer.indexing_active = True
        
        return jsonify({
            'success': True,
            'message': 'Indexing restarted successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to start indexing: {str(e)}'
        }), 500

@operacrm_bp.route('/api/admin/artist-indexing/clear-cache', methods=['POST'])
def clear_search_cache():
    """Vider le cache de recherche (Admin)"""
    auth_result = verify_flask_auth()
    if not auth_result or auth_result.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        from filemaker_cache_service import cache_service
        
        if cache_service.cache_enabled:
            # Vider seulement le cache de recherche (search)
            search_keys = [k for k in cache_service.redis_client.keys("fm_cache:search:*")]
            if search_keys:
                cache_service.redis_client.delete(*search_keys)
                count = len(search_keys)
                return jsonify({
                    'success': True,
                    'message': f'Cache vidé avec succès: {count} entrées supprimées',
                    'cleared_entries': count
                })
            else:
                return jsonify({
                    'success': True,
                    'message': 'Aucune entrée de cache à supprimer',
                    'cleared_entries': 0
                })
        else:
            return jsonify({
                'success': False,
                'error': 'Redis cache not available'
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to clear cache: {str(e)}'
        }), 500

@operacrm_bp.route('/api/admin/artist-indexing/index/<artist_name>', methods=['POST'])
def index_specific_artist(artist_name):
    """Réindexer un artiste spécifique (Admin)"""
    auth_result = verify_flask_auth()
    if not auth_result or auth_result.get('role') != 'admin':
        return jsonify({'error': 'Admin access required'}), 403
    
    try:
        from artist_indexer import artist_indexer as indexer
        
        # Indexer immédiatement l'artiste
        artworks_count = indexer.index_artist_now(artist_name)
        
        return jsonify({
            'success': True,
            'message': f'Artist {artist_name} reindexed successfully',
            'artworks_count': artworks_count
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to reindex artist: {str(e)}'
        }), 500
