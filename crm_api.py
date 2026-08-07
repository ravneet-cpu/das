#!/usr/bin/env python3
"""
API CRM pour partager le cache Redis avec des systèmes externes
"""

from flask import Blueprint, request, jsonify
from filemaker_cache_service import cache_service
from operagallery_service import cached_search_operacrm_artworks
import json

# Blueprint pour l'API CRM
crm_api_bp = Blueprint('crm_api', __name__)

@crm_api_bp.route('/api/crm/artworks/search/<artist_name>', methods=['GET'])
def crm_search_artworks(artist_name):
    """
    API pour CRM : Rechercher des œuvres d'art (avec cache)
    Usage: GET /api/crm/artworks/search/Picasso
    """
    try:
        # Utiliser le cache existant
        results = cached_search_operacrm_artworks(artist_name, 'artist', limit=None)
        
        if results:
            # Format adapté pour CRM
            crm_results = []
            for artwork in results:
                crm_artwork = {
                    'id': artwork.get('id_name', ''),
                    'artist': artwork.get('artist_name', ''),
                    'title': artwork.get('artwork_name', ''),
                    'year': artwork.get('year', ''),
                    'medium': artwork.get('medium', ''),
                    'dimensions': artwork.get('size', ''),
                    'location': artwork.get('location', ''),
                    'image_url': artwork.get('mainfm', ''),
                    'record_id': artwork.get('record_id', ''),
                    'source': 'OperaGallery',
                    'cached': True
                }
                crm_results.append(crm_artwork)
            
            return jsonify({
                'success': True,
                'artist': artist_name,
                'total': len(crm_results),
                'artworks': crm_results,
                'cached': True,
                'cache_expiry': '24 hours'
            })
        else:
            return jsonify({
                'success': True,
                'artist': artist_name,
                'total': 0,
                'artworks': [],
                'message': f'No artworks found for {artist_name}'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Search failed: {str(e)}'
        }), 500

@crm_api_bp.route('/api/crm/cache/stats', methods=['GET'])
def crm_cache_stats():
    """
    API pour CRM : Statistiques du cache
    Usage: GET /api/crm/cache/stats
    """
    try:
        if not cache_service.cache_enabled:
            return jsonify({
                'success': False,
                'error': 'Cache not available'
            }), 503
        
        # Obtenir les clés du cache
        search_keys = cache_service.redis_client.keys("fm_cache:search:*")
        
        stats = {
            'cache_enabled': True,
            'total_cached_searches': len(search_keys),
            'cache_type': 'Redis',
            'cache_duration': '24 hours',
            'sample_cached_artists': []
        }
        
        # Extraire quelques noms d'artistes en cache
        for key in search_keys[:10]:
            # Extraire le nom d'artiste de la clé
            parts = key.split(':')
            if len(parts) >= 3:
                artist_query = parts[-1]
                stats['sample_cached_artists'].append(artist_query)
        
        return jsonify({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Stats failed: {str(e)}'
        }), 500

@crm_api_bp.route('/api/crm/artworks/by-id/<artwork_id>', methods=['GET'])
def crm_get_artwork_by_id(artwork_id):
    """
    API pour CRM : Récupérer une œuvre par ID
    Usage: GET /api/crm/artworks/by-id/PICAPA-666
    """
    try:
        from operagallery_integration import get_operagallery_artwork_images
        
        # Rechercher l'artwork par ID
        # TODO: Implémenter cache pour les requêtes par ID
        artwork = get_operagallery_artwork_images(artwork_id)
        
        if artwork:
            return jsonify({
                'success': True,
                'artwork_id': artwork_id,
                'artwork': artwork
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Artwork {artwork_id} not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Lookup failed: {str(e)}'
        }), 500

@crm_api_bp.route('/api/crm/famous-artists', methods=['GET'])
def crm_get_famous_artists():
    """
    API pour CRM : Liste des artistes célèbres pré-configurés
    Usage: GET /api/crm/famous-artists
    """
    try:
        from artist_indexer import FAMOUS_ARTISTS
        
        return jsonify({
            'success': True,
            'total': len(FAMOUS_ARTISTS),
            'famous_artists': FAMOUS_ARTISTS,
            'cache_status': 'All artists cached for 24h after first search'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Failed to get famous artists: {str(e)}'
        }), 500