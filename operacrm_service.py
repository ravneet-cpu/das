#!/usr/bin/env python3
"""
Integrated OperaCRM service for photo validator application
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from search_operacrm_corrected import OperaCRMClient
from flask import Blueprint, request, jsonify, Response
from auth import verify_token
import re
import requests
from image_quality_checker import ImageQualityChecker
from filemaker_cache_service import cache_search, cache_metadata, cache_medium, cache_service

# Create the blueprint
operacrm_bp = Blueprint('operacrm', __name__)

# Global OperaCRM client instance
client = OperaCRMClient()

# Global quality checker instance
quality_checker = ImageQualityChecker()

# ============================================================================
# CACHED FILEMAKER API FUNCTIONS
# ============================================================================

@cache_search
def cached_search_by_artist(artist_name, limit=200):
    """Cached version of artist search"""
    try:
        return client.search_by_artist(artist_name, limit)
    except Exception as e:
        print(f"[CACHE] Search by artist error: {e}")
        return None

@cache_search
def cached_search_by_artwork_name(artwork_name, limit=200):
    """Cached version of artwork name search"""
    try:
        return client.search_by_artwork_name(artwork_name, limit)
    except Exception as e:
        print(f"[CACHE] Search by artwork name error: {e}")
        return None

@cache_search
def cached_search_by_category(category, limit=200):
    """Cached version of category search"""
    try:
        return client.search_by_category(category, limit)
    except Exception as e:
        print(f"[CACHE] Search by category error: {e}")
        return None

@cache_medium
def cached_search_by_idname(id_name):
    """Cached version of ID name search"""
    try:
        return client.search_by_idname(id_name)
    except Exception as e:
        print(f"[CACHE] Search by ID name error: {e}")
        return None

@cache_medium
def cached_search_by_id(artwork_id):
    """Cached version of search by ID"""
    try:
        return client.search_by_id(artwork_id)
    except Exception as e:
        print(f"[CACHE] Search by ID error: {e}")
        return None

# ============================================================================
# CACHE MANAGEMENT ENDPOINTS
# ============================================================================

@operacrm_bp.route('/api/cache/status', methods=['GET'])
def get_cache_status():
    """Get cache statistics"""
    try:
        # Verify authentication
        user = verify_flask_auth()
        if not user or user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        stats = cache_service.get_cache_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@operacrm_bp.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    """Clear all FileMaker cache (admin only)"""
    try:
        # Verify authentication
        user = verify_flask_auth()
        if not user or user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        cleared_count = cache_service.clear_all_cache()
        return jsonify({
            'success': True,
            'cleared_entries': cleared_count,
            'message': f'Cleared {cleared_count} cache entries'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@operacrm_bp.route('/api/cache/invalidate/<pattern>', methods=['POST'])
def invalidate_cache_pattern(pattern):
    """Invalidate cache entries matching pattern (admin only)"""
    try:
        # Verify authentication
        user = verify_flask_auth()
        if not user or user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        
        cache_service.invalidate_pattern(pattern)
        return jsonify({
            'success': True,
            'message': f'Invalidated cache pattern: {pattern}'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def verify_flask_auth():
    """Verify Flask authentication"""
    token = request.headers.get('Authorization')
    if not token or not token.startswith('Bearer '):
        return None
    
    token = token.split(' ')[1]
    payload = verify_token(token)
    return payload

def ensure_authenticated():
    """Ensure client is authenticated with automatic retry"""
    max_retries = 3
    
    for attempt in range(max_retries):
        if not client.session_id:
            print(f"🔐 Authenticating with OperaCRM (attempt {attempt + 1}/{max_retries})...")
            success = client.authenticate("odoo_15", "surafelwubshet7@gmail.com", "Surafell")
            if success:
                print("✅ OperaCRM authentication successful")
                return True
            else:
                print(f"❌ OperaCRM authentication failed (attempt {attempt + 1})")
                if attempt < max_retries - 1:
                    import time
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

# Cache to avoid reanalyzing the same images
_quality_cache = {}

# List of photos marked for later processing (in memory for now)
_marked_photos = set()

def analyze_operacrm_image_quality(artwork_id, image_field='image_1920'):
    """Analyze OperaCRM image quality with cache"""
    # Check cache first
    cache_key = f"{artwork_id}_{image_field}"
    if cache_key in _quality_cache:
        return _quality_cache[cache_key]
    
    try:
        # Retrieve artwork data
        results = client.search_by_id(artwork_id)
        if not results or len(results) == 0:
            return {'error': 'Artwork not found', 'quality_level': 'error', 'color_code': 'gray'}
        
        artwork = results[0]
        image_data = artwork.get(image_field)
        
        if not image_data or not isinstance(image_data, str):
            return {'error': 'No image data', 'quality_level': 'error', 'color_code': 'gray'}
        
        # Decode and analyze base64 image
        import base64
        import tempfile
        import os
        
        try:
            # Decode base64
            image_bytes = base64.b64decode(image_data)
            
            # Save temporarily for analysis
            with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
                temp_file.write(image_bytes)
                temp_path = temp_file.name
            
            # Analyze quality
            quality_analysis = quality_checker.analyze_image_quality(temp_path)
            
            # Clean up temporary file
            os.unlink(temp_path)
            
            # Cache the result
            _quality_cache[cache_key] = quality_analysis
            
            return quality_analysis
            
        except Exception as e:
            error_result = {'error': f'Error analyzing image: {str(e)}', 'quality_level': 'error', 'color_code': 'gray'}
            _quality_cache[cache_key] = error_result
            return error_result
            
    except Exception as e:
        error_result = {'error': f'Error retrieving artwork: {str(e)}', 'quality_level': 'error', 'color_code': 'gray'}
        _quality_cache[cache_key] = error_result
        return error_result

def get_quick_quality_estimate(artwork):
    """Quick quality estimation based on OperaCRM metadata"""
    try:
        # Check if there is an image
        has_image = artwork.get('image_1920') or artwork.get('image_1024') or artwork.get('image_512')
        if not has_image:
            return {
                'error': 'No image data',
                'quality_level': 'no_image',
                'color_code': 'gray',
                'print_quality_a5': 'No image available',
                'estimated': True
            }
        
        # Estimation based on base64 data size (approximation)
        image_data_size = 0
        if artwork.get('image_1920'):
            image_data_size = len(str(artwork.get('image_1920')))
        elif artwork.get('image_1024'):
            image_data_size = len(str(artwork.get('image_1024')))
        elif artwork.get('image_512'):
            image_data_size = len(str(artwork.get('image_512')))
        
        # Rough quality estimation based on data size
        if image_data_size > 1000000:  # > 1MB base64 ≈ high quality image
            quality_level = 'excellent'
            color_code = 'green'
            description = 'Probably excellent quality (estimated)'
            estimated_dpi = '300+'
        elif image_data_size > 500000:  # > 500KB base64 ≈ good quality
            quality_level = 'good'
            color_code = 'lightgreen'
            description = 'Probably good quality (estimated)'
            estimated_dpi = '200+'
        elif image_data_size > 200000:  # > 200KB base64 ≈ acceptable quality
            quality_level = 'acceptable'
            color_code = 'orange'
            description = 'Probably acceptable quality (estimated)'
            estimated_dpi = '150+'
        else:
            quality_level = 'poor'
            color_code = 'red'
            description = 'Probably insufficient quality (estimated)'
            estimated_dpi = '<150'
        
        return {
            'quality_level': quality_level,
            'color_code': color_code,
            'print_quality_a5': description,
            'equivalent_dpi_a5': estimated_dpi,
            'file_size_mb': round(image_data_size * 0.75 / 1024 / 1024, 2),  # Approximation
            'estimated': True,
            'data_size_bytes': image_data_size
        }
        
    except Exception as e:
        return {
            'error': f'Error estimating quality: {str(e)}',
            'quality_level': 'error',
            'color_code': 'gray',
            'estimated': True
        }

def format_artwork_for_frontend(artwork):
    """Convert OperaCRM data for frontend"""
    if not artwork:
        return None
    
    # Build image URLs
    image_urls = []
    
    # If artwork has a direct image URL
    if artwork.get('image_url'):
        image_urls.append(artwork['image_url'])
    
    # Build URLs for images via our proxy
    artwork_id = artwork.get('id')
    
    if artwork_id:
        # Prioritize lighter images for performance
        for img_field in ['image_512', 'image_1024', 'image_1920']:
            # OperaCRM returns base64 binary data in these fields
            img_data = artwork.get(img_field)
            if img_data and isinstance(img_data, str) and len(img_data) > 100:
                # This is base64 binary data, use our proxy
                img_url = f"/api/operacrm/image/{artwork_id}/{img_field}"
                image_urls.append(img_url)
                # Take only the first valid image for performance
                break
    
    # Quick analysis based on metadata (no image download)
    quality_analysis = None
    if artwork_id:
        quality_analysis = get_quick_quality_estimate(artwork)
    
    # Format dimensions
    dimensions = ""
    size_h = artwork.get('SizeH')
    size_l = artwork.get('SizeL')
    size_inc_h = artwork.get('SizeIncH')
    size_inc_l = artwork.get('SizeIncL')
    
    if size_h and size_l:
        dimensions = f"{size_h} × {size_l} cm"
        if size_inc_h and size_inc_l:
            dimensions += f" ({size_inc_h} × {size_inc_l} in)"
    
    # Format price
    price_estimate = ""
    price = artwork.get('artwork_price_combined') or artwork.get('PriceRef')
    currency = artwork.get('CurrencyRef', 'EUR')
    if price:
        price_estimate = f"{price:,.0f} {currency}"
    
    return {
        'id': artwork.get('id'),
        'IdName': artwork.get('IdName', ''),
        'title': artwork.get('name', ''),
        'artist': artwork.get('ArtistName', ''),
        'year': artwork.get('artwork_year', ''),
        'category': artwork.get('Category', ''),
        'medium': artwork.get('Medium', ''),
        'description': artwork.get('description', ''),
        'dimensions': dimensions,
        'price_estimate': price_estimate,
        'location': artwork.get('Location', ''),
        'status': artwork.get('Status', ''),
        'signed': artwork.get('artwork_signed', ''),
        'provenance': artwork.get('artwork_provenance', ''),
        'exhibited': artwork.get('artwork_exhibited', ''),
        'main_picture_hd': image_urls[0] if image_urls else None,
        'all_image_urls': image_urls,
        'image_count': len(image_urls),
        'created_date': artwork.get('create_date', ''),
        'updated_date': artwork.get('write_date', ''),
        'quality_analysis': quality_analysis,
        'marked_for_processing': str(artwork.get('id')) in _marked_photos
    }

# DISABLED: Using OperaGallery instead
# @operacrm_bp.route('/api/artworks/search', methods=['POST'])
def search_artworks_disabled():
    """Endpoint to search for artworks"""
    try:
        import sys
        print(f"[DEBUG SEARCH] Starting search request", file=sys.stderr, flush=True)
        
        if not ensure_authenticated():
            print(f"[DEBUG SEARCH] Authentication failed", file=sys.stderr, flush=True)
            return jsonify({
                'success': False,
                'error': 'Failed to authenticate with OperaCRM',
                'artworks': [],
                'total': 0
            }), 500
        
        print(f"[DEBUG SEARCH] Authentication successful, session_id: {client.session_id[:10]}...", file=sys.stderr, flush=True)
        
        data = request.get_json()
        query = data.get('query', '').strip()
        search_type = data.get('searchType', 'all')
        limit = data.get('limit', 1000)  # No limit restriction
        quality_filter = data.get('qualityFilter', 'all')  # all, excellent, good, acceptable, poor
        stock_filter = data.get('stockFilter', 'all')  # all, in_stock, in_transit, available
        gallery_filter = data.get('galleryFilter', 'all')  # all, specific gallery
        
        print(f"[DEBUG SEARCH] Query: '{query}', Type: {search_type}, Limit: {limit}, Gallery: {gallery_filter}", file=sys.stderr, flush=True)
        
        results = []
        
        # Use cached search functions for better performance
        print(f"[CACHE] Using cached search for query: '{query}', type: {search_type}", file=sys.stderr, flush=True)
        
        # If gallery filter is specified but no query, search by location only
        if gallery_filter != 'all' and (not query or query == ''):
            print(f"[DEBUG SEARCH] Gallery-only search for location: {gallery_filter}", file=sys.stderr, flush=True)
            # Use broad search to get artworks and then filter by location
            # Search using ALL alphabet letters to get comprehensive results for gallery
            letters = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z']
            all_results = []
            for letter in letters:
                letter_results = cached_search_by_artist(letter, 200)  # Use cached search
                if letter_results:
                    all_results.extend(letter_results)
                    print(f"[DEBUG SEARCH] Letter '{letter}': found {len(letter_results)} artworks, total so far: {len(all_results)}", file=sys.stderr, flush=True)
                # No limit - get ALL artworks to ensure we don't miss any
            results = all_results
            print(f"[DEBUG SEARCH] Total artworks found across all letters: {len(results)}", file=sys.stderr, flush=True)
        elif search_type == 'artist':
            print(f"[DEBUG SEARCH] Searching by artist: {query}", file=sys.stderr, flush=True)
            results = cached_search_by_artist(query, limit)  # Use cached search
        elif search_type == 'artwork_id':
            # Search by specific ID
            if query:
                print(f"[DEBUG SEARCH] Searching by IdName: {query}", file=sys.stderr, flush=True)
                results = cached_search_by_idname(query)  # Use cached search
                if results and not isinstance(results, list):
                    results = [results]  # Convert single result to list
                elif not results:
                    results = []
        elif search_type == 'title':
            print(f"[DEBUG SEARCH] Searching by title: {query}", file=sys.stderr, flush=True)
            results = cached_search_by_artwork_name(query, limit)  # Use cached search
        elif search_type == 'category':
            print(f"[DEBUG SEARCH] Searching by category: {query}", file=sys.stderr, flush=True)
            results = cached_search_by_category(query, limit)  # Use cached search
        elif search_type == 'medium':
            print(f"[DEBUG SEARCH] Searching by medium: {query}", file=sys.stderr, flush=True)
            # Note: search_by_medium doesn't exist in client, fallback to artist search for now
            results = cached_search_by_artist(query, limit)  # Use cached search
        else:  # search_type == 'all'
            # Global search - try both artist and artwork name
            if query:
                print(f"[DEBUG SEARCH] Global search (artwork name OR artist): {query}", file=sys.stderr, flush=True)
                # Try artist search first, then artwork name search
                artist_results = cached_search_by_artist(query, limit) or []
                artwork_results = cached_search_by_artwork_name(query, limit) or []
                # Combine and remove duplicates by ID
                all_results = artist_results + artwork_results
                seen_ids = set()
                results = []
                for artwork in all_results:
                    artwork_id = artwork.get('id')
                    if artwork_id not in seen_ids:
                        seen_ids.add(artwork_id)
                        results.append(artwork)
            else:
                # No query specified, perform a broad search
                print(f"[DEBUG SEARCH] No query specified, performing broad search", file=sys.stderr, flush=True)
                results = cached_search_by_artist('A', limit)  # Use cached search
        
        # Debug logging
        print(f"[DEBUG SEARCH] Raw results from OperaCRM: {len(results) if results else 0}", file=sys.stderr, flush=True)
        if results and len(results) > 0:
            print(f"[DEBUG SEARCH] First result sample: {results[0].get('IdName', 'NO_ID')} - {results[0].get('name', 'NO_NAME')}", file=sys.stderr, flush=True)
        
        # Convert for frontend
        formatted_results = []
        if results:  # Check if results is not None
            print(f"[DEBUG SEARCH] Processing {len(results)} artworks for gallery filter '{gallery_filter}'", file=sys.stderr, flush=True)
            for i, artwork in enumerate(results):
                formatted = format_artwork_for_frontend(artwork)
                if formatted:
                    # Apply quality filter
                    quality_ok = True
                    if quality_filter != 'all':
                        quality_analysis = formatted.get('quality_analysis')
                        if quality_analysis and quality_analysis.get('quality_level') == quality_filter:
                            quality_ok = True
                        elif quality_filter == 'no_image' and (not quality_analysis or quality_analysis.get('error')):
                            quality_ok = True
                        else:
                            quality_ok = False
                    
                    # Apply stock filter
                    stock_ok = True
                    if stock_filter != 'all':
                        status = formatted.get('status', '').lower()
                        if stock_filter == 'in_stock':
                            stock_ok = 'stock' in status or 'disponible' in status
                        elif stock_filter == 'in_transit':
                            stock_ok = 'transit' in status or 'transport' in status or 'expédition' in status
                        elif stock_filter == 'available':
                            # Available = in stock OR in transit (not for sale, sold, etc.)
                            stock_ok = ('stock' in status or 'disponible' in status or 
                                       'transit' in status or 'transport' in status or 'expédition' in status) and \
                                       ('vente' not in status and 'vendu' not in status and 'sold' not in status)
                    
                    # Apply gallery filter
                    gallery_ok = True
                    if gallery_filter != 'all':
                        location = formatted.get('location', '').strip()
                        gallery_ok = location == gallery_filter
                        if i < 10:  # Only log first 10 for debugging
                            print(f"[DEBUG GALLERY] Artwork {i}: location='{location}', filter='{gallery_filter}', match={gallery_ok}", file=sys.stderr, flush=True)
                    
                    # Add to results only if all filters pass
                    if quality_ok and stock_ok and gallery_ok:
                        formatted_results.append(formatted)
                    elif gallery_filter != 'all':
                        # Debug why artworks are filtered out in gallery-only searches
                        if not quality_ok:
                            print(f"[DEBUG FILTER] Artwork {formatted.get('id', 'unknown')} filtered out by quality: {quality_filter}", file=sys.stderr, flush=True)
                        if not stock_ok:
                            print(f"[DEBUG FILTER] Artwork {formatted.get('id', 'unknown')} filtered out by stock: {stock_filter}", file=sys.stderr, flush=True)
                        if not gallery_ok:
                            print(f"[DEBUG FILTER] Artwork {formatted.get('id', 'unknown')} filtered out by gallery: location='{formatted.get('location', '')}' vs filter='{gallery_filter}'", file=sys.stderr, flush=True)
        
        print(f"[DEBUG SEARCH] Formatted results for frontend: {len(formatted_results)}", file=sys.stderr, flush=True)
        
        return jsonify({
            'success': True,
            'artworks': formatted_results,
            'total': len(formatted_results)
        })
        
    except Exception as e:
        print(f"[DEBUG SEARCH] Error: {str(e)}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': f'Search error: {str(e)}',
            'artworks': [],
            'total': 0
        }), 500

@operacrm_bp.route('/api/artworks/categories', methods=['GET'])
def get_artwork_categories():
    """Get all available artwork categories from OperaCRM"""
    try:
        if not ensure_authenticated():
            return jsonify({
                'success': False,
                'error': 'Failed to authenticate with OperaCRM'
            }), 500
        
        # Note: get_all_categories method doesn't exist in client, need to implement
        categories = []  # Fallback for now
        
        return jsonify({
            'success': True,
            'categories': categories or [],
            'count': len(categories) if categories else 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error retrieving categories: {str(e)}',
            'categories': [],
            'count': 0
        }), 500

@operacrm_bp.route('/api/artworks/mediums', methods=['GET'])
def get_artwork_mediums():
    """Get all available artwork mediums from OperaCRM"""
    try:
        if not ensure_authenticated():
            return jsonify({
                'success': False,
                'error': 'Failed to authenticate with OperaCRM'
            }), 500
        
        # Note: get_all_mediums method doesn't exist in client, need to implement
        mediums = []  # Fallback for now
        
        return jsonify({
            'success': True,
            'mediums': mediums or [],
            'count': len(mediums) if mediums else 0
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error retrieving mediums: {str(e)}',
            'mediums': [],
            'count': 0
        }), 500

@operacrm_bp.route('/api/artworks/by-id/<artwork_id>', methods=['GET'])
def get_artwork_by_id(artwork_id):
    """Get an artwork by its ID"""
    try:
        if not ensure_authenticated():
            return jsonify({
                'success': False,
                'error': 'Failed to authenticate with OperaCRM'
            }), 500
        
        results = cached_search_by_idname(artwork_id.strip())  # Use cached version
        
        if results and len(results) > 0:
            artwork = results[0]  # Take the first result
            formatted = format_artwork_for_frontend(artwork)
            return jsonify({
                'success': True,
                'artwork': formatted
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Artwork not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error retrieving artwork: {str(e)}'
        }), 500


@operacrm_bp.route('/api/photos/validate-upload', methods=['POST'])
def validate_photo_upload():
    """Validate photo upload with quality verification and metadata"""
    try:
        if not ensure_authenticated():
            return jsonify({
                'success': False,
                'error': 'Failed to authenticate with OperaCRM'
            }), 500
        
        # Check if a file was uploaded
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Empty filename'
            }), 400
        
        # Temporarily save file for analysis
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Analyze quality de l'image
            quality_analysis = quality_checker.analyze_image_quality(temp_path)
            
            # Extract artwork ID from filename
            filename = file.filename
            id_match = re.search(r'([A-Z]+-\d+)', filename.upper())
            extracted_id = id_match.group(1) if id_match else None
            
            response_data = {
                'filename': filename,
                'artwork_id': extracted_id,
                'artwork_found': False,
                'artwork_metadata': None,
                'duplicate_warning': None,
                'quality_analysis': quality_analysis
            }
            
            if extracted_id:
                # Search for artwork in OperaCRM using cached version
                results = cached_search_by_idname(extracted_id)
                
                if results and len(results) > 0:
                    artwork = results[0]
                    formatted_artwork = format_artwork_for_frontend(artwork)
                    response_data['artwork_found'] = True
                    response_data['artwork_metadata'] = formatted_artwork
                    
                    # Check if there are existing images
                    has_existing_images = formatted_artwork.get('image_count', 0) > 0
                    if has_existing_images:
                        response_data['duplicate_warning'] = {
                            'type': 'potential_duplicate',
                            'message': f"This artwork ({extracted_id}) already has {formatted_artwork['image_count']} image(s) in OperaCRM.",
                            'existing_images': formatted_artwork.get('all_image_urls', [])
                        }
                    
                    # Determine if upload should be accepted
                    should_accept, reason = quality_checker.should_accept_upload(
                        quality_analysis.get('quality_level', 'error'),
                        has_existing_images
                    )
                    
                    response_data['upload_recommendation'] = {
                        'should_accept': should_accept,
                        'reason': reason,
                        'quality_level': quality_analysis.get('quality_level', 'error'),
                        'color_code': quality_analysis.get('color_code', 'gray')
                    }
            
            return jsonify({
                'success': True,
                'data': response_data
            })
            
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_path)
            except:
                pass
                
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error validating upload: {str(e)}'
        }), 500

@operacrm_bp.route('/api/photos/validate-metadata', methods=['POST'])
def validate_photo_metadata():
    """Validate and enrich photo metadata"""
    try:
        if not ensure_authenticated():
            return jsonify({
                'success': False,
                'error': 'Failed to authenticate with OperaCRM'
            }), 500
        
        data = request.get_json()
        photo_id = data.get('photoId')
        filename = data.get('filename', photo_id)
        
        # Extract artwork ID from filename
        id_match = re.search(r'([A-Z]+-\d+)', filename.upper())
        extracted_id = id_match.group(1) if id_match else None
        
        response_data = {
            'photo_id': photo_id,
            'filename': filename,
            'artwork_id': extracted_id,
            'artwork_found': False,
            'artwork_metadata': None,
            'duplicate_warning': None
        }
        
        if extracted_id:
            # Search for artwork in OperaCRM using cached version
            results = cached_search_by_idname(extracted_id)
            
            if results and len(results) > 0:
                artwork = results[0]  # Take the first result
                formatted_artwork = format_artwork_for_frontend(artwork)
                response_data['artwork_found'] = True
                response_data['artwork_metadata'] = formatted_artwork
                
                # Check if there are existing images
                if formatted_artwork.get('image_count', 0) > 0:
                    response_data['duplicate_warning'] = {
                        'type': 'potential_duplicate',
                        'message': f"This artwork ({extracted_id}) already has {formatted_artwork['image_count']} image(s) in OperaCRM.",
                        'existing_images': formatted_artwork.get('all_image_urls', [])
                    }
        
        return jsonify({
            'success': True,
            'data': response_data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error validating metadata: {str(e)}'
        }), 500

@operacrm_bp.route('/api/operacrm/image/<int:artwork_id>/<image_field>')
def proxy_operacrm_image(artwork_id, image_field):
    """Proxy to serve OperaCRM images (base64 or direct URL)"""
    try:
        if not ensure_authenticated():
            return jsonify({'error': 'OperaCRM authentication failed'}), 500
        
        # Retrieve artwork to access image data
        results = client.search_by_id(artwork_id)
        if not results or len(results) == 0:
            return jsonify({'error': 'Artwork not found'}), 404
            
        artwork = results[0]
        image_data = artwork.get(image_field)
        
        import sys
        print(f"[DEBUG PROXY] Artwork {artwork_id}, field {image_field}, data length: {len(image_data) if image_data else 0}", flush=True)
        sys.stdout.flush()
        
        if not image_data:
            return jsonify({'error': 'Image field empty'}), 404
            
        # Use base64 data from OperaCRM API (the real images)
        # Direct OperaCRM URLs always return the same generic image
        if isinstance(image_data, str) and len(image_data) > 100:
            # This is base64 data
            import base64
            import io
            
            try:
                # Decode base64
                image_bytes = base64.b64decode(image_data)
                
                # Detect image type
                mimetype = 'image/jpeg'
                if image_bytes.startswith(b'\x89PNG'):
                    mimetype = 'image/png'
                elif image_bytes.startswith(b'GIF'):
                    mimetype = 'image/gif'
                
                return Response(
                    image_bytes,
                    mimetype=mimetype,
                    headers={
                        'Cache-Control': 'public, max-age=86400',
                        'Access-Control-Allow-Origin': '*',
                        'X-Content-Type-Options': 'nosniff'
                    }
                )
            except Exception as e:
                return jsonify({'error': f'Error decoding base64: {str(e)}'}), 500
        else:
            return jsonify({'error': 'No valid image data'}), 404
            
    except Exception as e:
        return jsonify({'error': f'Error proxying image: {str(e)}'}), 500

@operacrm_bp.route('/api/admin/quality-config', methods=['GET'])
def get_quality_config():
    """Retrieve image quality configuration"""
    try:
        # TODO: Add admin verification
        config = quality_checker.get_config()
        return jsonify({
            'success': True,
            'config': config
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error getting config: {str(e)}'
        }), 500

@operacrm_bp.route('/api/admin/quality-config', methods=['POST'])
def update_quality_config():
    """Update image quality configuration"""
    try:
        # TODO: Add admin verification
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No configuration data provided'
            }), 400
        
        quality_checker.update_config(data)
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated successfully'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error updating config: {str(e)}'
        }), 500

@operacrm_bp.route('/api/artworks/<int:artwork_id>/analyze-quality', methods=['GET'])
def analyze_artwork_quality(artwork_id):
    """Analyze image quality of a specific artwork"""
    try:
        if not ensure_authenticated():
            return jsonify({
                'success': False,
                'error': 'Failed to authenticate with OperaCRM'
            }), 500
        
        image_field = request.args.get('image_field', 'image_1920')
        quality_analysis = analyze_operacrm_image_quality(artwork_id, image_field)
        
        return jsonify({
            'success': True,
            'artwork_id': artwork_id,
            'image_field': image_field,
            'quality_analysis': quality_analysis
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error analyzing quality: {str(e)}'
        }), 500

@operacrm_bp.route('/api/artworks/quality-report', methods=['POST'])
def generate_quality_report():
    """Generate quality report for a list of artworks"""
    try:
        if not ensure_authenticated():
            return jsonify({
                'success': False,
                'error': 'Failed to authenticate with OperaCRM'
            }), 500
        
        data = request.get_json()
        artwork_ids = data.get('artwork_ids', [])
        
        if not artwork_ids:
            return jsonify({
                'success': False,
                'error': 'No artwork IDs provided'
            }), 400
        
        quality_report = {
            'total_analyzed': 0,
            'quality_distribution': {
                'excellent': 0,
                'good': 0,
                'acceptable': 0,
                'poor': 0,
                'no_image': 0,
                'error': 0
            },
            'artworks': []
        }
        
        for artwork_id in artwork_ids[:100]:  # Limit to 100 to avoid timeout
            try:
                quality_analysis = analyze_operacrm_image_quality(artwork_id)
                quality_level = quality_analysis.get('quality_level', 'error')
                
                if quality_level in quality_report['quality_distribution']:
                    quality_report['quality_distribution'][quality_level] += 1
                else:
                    quality_report['quality_distribution']['error'] += 1
                
                quality_report['artworks'].append({
                    'artwork_id': artwork_id,
                    'quality_level': quality_level,
                    'color_code': quality_analysis.get('color_code', 'gray'),
                    'equivalent_dpi_a5': quality_analysis.get('equivalent_dpi_a5'),
                    'dimensions': quality_analysis.get('dimensions'),
                    'print_quality_a5': quality_analysis.get('print_quality_a5')
                })
                
                quality_report['total_analyzed'] += 1
                
            except Exception as e:
                quality_report['quality_distribution']['error'] += 1
                quality_report['artworks'].append({
                    'artwork_id': artwork_id,
                    'quality_level': 'error',
                    'color_code': 'gray',
                    'error': str(e)
                })
        
        return jsonify({
            'success': True,
            'report': quality_report
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error generating report: {str(e)}'
        }), 500

@operacrm_bp.route('/api/artworks/<int:artwork_id>/mark-for-processing', methods=['POST'])
def mark_artwork_for_processing(artwork_id):
    """Mark artwork for later processing"""
    try:
        _marked_photos.add(str(artwork_id))
        return jsonify({
            'success': True,
            'message': f'Artwork {artwork_id} marked for processing',
            'marked': True
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error marking artwork: {str(e)}'
        }), 500

@operacrm_bp.route('/api/artworks/<int:artwork_id>/unmark-for-processing', methods=['POST'])
def unmark_artwork_for_processing(artwork_id):
    """Unmark artwork for later processing"""
    try:
        _marked_photos.discard(str(artwork_id))
        return jsonify({
            'success': True,
            'message': f'Artwork {artwork_id} unmarked for processing',
            'marked': False
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error unmarking artwork: {str(e)}'
        }), 500

@operacrm_bp.route('/api/artworks/marked-for-processing', methods=['GET'])
def get_marked_artworks():
    """Retrieve list of artworks marked for processing"""
    try:
        return jsonify({
            'success': True,
            'marked_artwork_ids': list(_marked_photos),
            'count': len(_marked_photos)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Error getting marked artworks: {str(e)}'
        }), 500