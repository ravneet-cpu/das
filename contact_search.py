#!/usr/bin/env python3
"""
Contact Search Engine — Customers & Prospects
Searches across res.partner, crm.prospect and res.partner.addresses
Links via LEntity = Id_with_c
"""

import xmlrpc.client
import logging
from flask import Blueprint, request, jsonify
from functools import lru_cache
import time

log = logging.getLogger(__name__)

contact_search_bp = Blueprint('contact_search', __name__)

# --- Odoo config ---
DB   = "odoo_15"
UID  = 34
PASS = "Surafell"
URL  = "https://operacrm.com"

PARTNER_FIELDS = [
    'id', 'name', 'email', 'phone', 'mobile',
    'street', 'city', 'zip', 'country_id',
    'Id_with_c', 'IdEntity', 'ref',
    'total_sold_price_global_eur',
]

PROSPECT_FIELDS = [
    'id', 'name', 'FirstName', 'LastName',
    'Email1', 'Email2', 'Phone1', 'Phone2',
    'BirthDate', 'Id_with_c', 'IdEntity',
]

ADDRESS_FIELDS = [
    'id', 'LEntity', 'FirstName', 'LastName', 'AddrName',
    'Street1', 'Street2', 'City', 'State', 'ZipCode', 'Country',
    'Phone1', 'Phone2', 'Email', 'Email1',
    'Category', 'is_main', 'customer_id', 'prospect_id',
]


def get_models():
    return xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")


def build_domain(query, fields):
    """Build an OR domain for ilike search across multiple fields."""
    if len(fields) == 1:
        return [[fields[0], 'ilike', query]]
    parts = []
    for i, f in enumerate(fields):
        if i < len(fields) - 1:
            parts.append('|')
        parts.append([f, 'ilike', query])
    return parts


def search_partners(models, query, limit=30):
    """Search res.partner by name, email, phone, city."""
    domain = build_domain(query, ['name', 'email', 'phone', 'city', 'Id_with_c'])
    try:
        return models.execute_kw(DB, UID, PASS, 'res.partner', 'search_read',
            [domain], {'fields': PARTNER_FIELDS, 'limit': limit, 'order': 'name asc'})
    except Exception as e:
        log.error(f"search_partners error: {e}")
        return []


def search_prospects(models, query, limit=30):
    """Search crm.prospect by name, email, phone."""
    domain = build_domain(query, ['name', 'Email1', 'Phone1', 'Id_with_c'])
    try:
        return models.execute_kw(DB, UID, PASS, 'crm.prospect', 'search_read',
            [domain], {'fields': PROSPECT_FIELDS, 'limit': limit, 'order': 'name asc'})
    except Exception as e:
        log.error(f"search_prospects error: {e}")
        return []


def search_addresses(models, query, limit=50):
    """Search addresses by city, country, street, name."""
    domain = build_domain(query, [
        'FirstName', 'LastName', 'City', 'Country',
        'Street1', 'ZipCode', 'Email', 'Phone1'
    ])
    try:
        return models.execute_kw(DB, UID, PASS, 'res.partner.addresses', 'search_read',
            [domain], {'fields': ADDRESS_FIELDS, 'limit': limit})
    except Exception as e:
        log.error(f"search_addresses error: {e}")
        return []


def get_addresses_for_entities(models, lentity_list, limit=200):
    """Fetch all addresses for a list of LEntity codes."""
    if not lentity_list:
        return []
    try:
        return models.execute_kw(DB, UID, PASS, 'res.partner.addresses', 'search_read',
            [[['LEntity', 'in', lentity_list]]],
            {'fields': ADDRESS_FIELDS, 'limit': limit})
    except Exception as e:
        log.error(f"get_addresses_for_entities error: {e}")
        return []


def get_entities_by_lentity(models, lentity_list):
    """Find partners and prospects matching a list of LEntity codes."""
    if not lentity_list:
        return [], []
    try:
        partners = models.execute_kw(DB, UID, PASS, 'res.partner', 'search_read',
            [[['Id_with_c', 'in', lentity_list]]],
            {'fields': PARTNER_FIELDS, 'limit': 50})
    except Exception:
        partners = []
    try:
        prospects = models.execute_kw(DB, UID, PASS, 'crm.prospect', 'search_read',
            [[['Id_with_c', 'in', lentity_list]]],
            {'fields': PROSPECT_FIELDS, 'limit': 50})
    except Exception:
        prospects = []
    return partners, prospects


def format_partner(p, addresses):
    """Format a res.partner record for the API response."""
    country = p.get('country_id')
    return {
        'type': 'customer',
        'id': p['id'],
        'entity_code': p.get('Id_with_c', ''),
        'name': p.get('name', ''),
        'email': p.get('email') or '',
        'phone': p.get('phone') or p.get('mobile') or '',
        'city': p.get('city') or '',
        'country': country[1] if isinstance(country, list) else '',
        'street': p.get('street') or '',
        'zip': p.get('zip') or '',
        'ref': p.get('ref') or '',
        'total_sales': p.get('total_sold_price_global_eur') or 0,
        'addresses': addresses,
    }


def format_prospect(p, addresses):
    """Format a crm.prospect record for the API response."""
    return {
        'type': 'prospect',
        'id': p['id'],
        'entity_code': p.get('Id_with_c', ''),
        'name': p.get('name', ''),
        'first_name': p.get('FirstName') or '',
        'last_name': p.get('LastName') or '',
        'email': p.get('Email1') or p.get('Email2') or '',
        'phone': p.get('Phone1') or p.get('Phone2') or '',
        'addresses': addresses,
    }


def format_address(a):
    """Format an address record."""
    return {
        'id': a['id'],
        'name': ' '.join(filter(None, [a.get('FirstName') or '', a.get('LastName') or ''])).strip()
               or a.get('AddrName') or '',
        'street': ' '.join(filter(None, [a.get('Street1') or '', a.get('Street2') or ''])).strip(),
        'city': a.get('City') or '',
        'state': a.get('State') or '',
        'zip': a.get('ZipCode') or '',
        'country': a.get('Country') or '',
        'phone': a.get('Phone1') or a.get('Phone2') or '',
        'email': a.get('Email') or a.get('Email1') or '',
        'category': a.get('Category') or '',
        'is_main': a.get('is_main', False),
    }


def merge_results(partners, prospects, all_addresses_by_lentity,
                  found_partner_ids, found_prospect_ids):
    """
    Build unified results list.
    - partners/prospects: already fetched records
    - all_addresses_by_lentity: dict {lentity: [address, ...]}
    - found_*_ids: sets of IDs already included (to avoid duplicates)
    """
    results = []

    for p in partners:
        if p['id'] in found_partner_ids:
            continue
        found_partner_ids.add(p['id'])
        lentity = p.get('Id_with_c', '')
        addrs = [format_address(a) for a in all_addresses_by_lentity.get(lentity, [])]
        results.append(format_partner(p, addrs))

    for p in prospects:
        if p['id'] in found_prospect_ids:
            continue
        found_prospect_ids.add(p['id'])
        lentity = p.get('Id_with_c', '')
        addrs = [format_address(a) for a in all_addresses_by_lentity.get(lentity, [])]
        results.append(format_prospect(p, addrs))

    return results


# ─────────────────────────────────────────────
# FLASK ROUTES
# ─────────────────────────────────────────────

@contact_search_bp.route('/api/contacts/search', methods=['GET'])
def search_contacts():
    """
    Unified contact search across customers and prospects.

    GET /api/contacts/search?q=Smith&type=all&limit=20

    Params:
      q     : search query (required, min 2 chars)
      type  : 'all' | 'customer' | 'prospect' (default: 'all')
      limit : max results per type (default: 20, max: 50)
    """
    query = request.args.get('q', '').strip()
    search_type = request.args.get('type', 'all')
    try:
        limit = min(int(request.args.get('limit', 20)), 50)
    except ValueError:
        limit = 20

    if len(query) < 2:
        return jsonify({'success': False, 'error': 'Query must be at least 2 characters'}), 400

    t0 = time.time()
    models = get_models()

    partners   = []
    prospects  = []
    addr_hits  = []

    # --- Direct searches ---
    if search_type in ('all', 'customer'):
        partners = search_partners(models, query, limit)

    if search_type in ('all', 'prospect'):
        prospects = search_prospects(models, query, limit)

    # --- Address search (only for 'all' type or when few direct results) ---
    if search_type == 'all' or (len(partners) + len(prospects) < 5):
        addr_hits = search_addresses(models, query, limit * 2)

        if addr_hits:
            lentity_from_addrs = list({a['LEntity'] for a in addr_hits if a.get('LEntity')})
            extra_partners, extra_prospects = get_entities_by_lentity(models, lentity_from_addrs)
            # Will be merged below (dedup by id)
            partners  = partners  + extra_partners
            prospects = prospects + extra_prospects

    # --- Collect all LEntity codes to fetch addresses ---
    all_lentities = list({
        *[p.get('Id_with_c', '') for p in partners  if p.get('Id_with_c')],
        *[p.get('Id_with_c', '') for p in prospects if p.get('Id_with_c')],
    })
    all_addresses = get_addresses_for_entities(models, all_lentities)

    # Build lookup: lentity → [addresses]
    addr_by_lentity = {}
    for a in all_addresses:
        le = a.get('LEntity', '')
        addr_by_lentity.setdefault(le, []).append(a)

    # Merge, dedup
    results = merge_results(
        partners, prospects, addr_by_lentity,
        found_partner_ids=set(),
        found_prospect_ids=set(),
    )

    elapsed = round(time.time() - t0, 2)

    return jsonify({
        'success': True,
        'query': query,
        'type': search_type,
        'total': len(results),
        'elapsed_s': elapsed,
        'results': results,
    })


@contact_search_bp.route('/api/contacts/<entity_code>', methods=['GET'])
def get_contact_by_code(entity_code):
    """
    Get a single contact by entity code (e.g. C6362).

    GET /api/contacts/C6362
    """
    models = get_models()

    # Try partner first
    partners = []
    prospects = []
    try:
        partners = models.execute_kw(DB, UID, PASS, 'res.partner', 'search_read',
            [[['Id_with_c', '=', entity_code]]], {'fields': PARTNER_FIELDS, 'limit': 1})
    except Exception:
        pass

    if not partners:
        try:
            prospects = models.execute_kw(DB, UID, PASS, 'crm.prospect', 'search_read',
                [[['Id_with_c', '=', entity_code]]], {'fields': PROSPECT_FIELDS, 'limit': 1})
        except Exception:
            pass

    if not partners and not prospects:
        return jsonify({'success': False, 'error': f'Contact {entity_code} not found'}), 404

    # Fetch all addresses for this entity
    addresses_raw = []
    try:
        addresses_raw = models.execute_kw(DB, UID, PASS, 'res.partner.addresses', 'search_read',
            [[['LEntity', '=', entity_code]]], {'fields': ADDRESS_FIELDS, 'limit': 50})
    except Exception:
        pass

    addrs = [format_address(a) for a in addresses_raw]

    if partners:
        contact = format_partner(partners[0], addrs)
    else:
        contact = format_prospect(prospects[0], addrs)

    return jsonify({'success': True, 'contact': contact})


@contact_search_bp.route('/api/contacts/stats', methods=['GET'])
def contact_stats():
    """Return counts of customers, prospects and addresses."""
    models = get_models()
    try:
        n_partners  = models.execute_kw(DB, UID, PASS, 'res.partner',  'search_count', [[['Id_with_c', '!=', False]]])
        n_prospects = models.execute_kw(DB, UID, PASS, 'crm.prospect', 'search_count', [[]])
        n_addresses = models.execute_kw(DB, UID, PASS, 'res.partner.addresses', 'search_count', [[]])
        return jsonify({
            'success': True,
            'customers': n_partners,
            'prospects': n_prospects,
            'addresses': n_addresses,
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
