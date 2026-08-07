#!/usr/bin/env python3
"""
OperaGallery service for photo validator application
Remplace OperaCRM par OperaGallery pour la recherche d'œuvres d'art
"""

import sys
import os
# sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from operagallery_integration import OperaGalleryClient, search_operagallery_artworks, get_operagallery_artwork_images
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
operagallery_bp = Blueprint('operagallery', __name__)

# Configuration FileMaker
FM_SERVER = '178.248.210.53'
FM_USERNAME = 'DataApiAccess'
FM_PASSWORD = 'JPMEJU1JPMEJU1'
FM_DATABASE = 'OperaGallery'
FM_LAYOUT = 'CRMSearchArtworks'

# Cache des tokens FileMaker
_fm_token = None
_fm_token_time = 0

def get_filemaker_token():
    """Obtenir un token FileMaker (avec cache)"""
    global _fm_token, _fm_token_time
    
    # Token valide pour 15 minutes, on renouvelle après 10 minutes
    if _fm_token and (time.time() - _fm_token_time) < 600:
        return _fm_token
    
    auth_url = f"https://{FM_SERVER}/fmi/data/vLatest/databases/{FM_DATABASE}/sessions"
    
    try:
        response = requests.post(
            auth_url,
            auth=HTTPBasicAuth(FM_USERNAME, FM_PASSWORD),
            json={},
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            _fm_token = data['response']['token']
            _fm_token_time = time.time()
            return _fm_token
        else:
            print(f"[FM-AUTH] Erreur {response.status_code}")
            return None
            
    except Exception as e:
        print(f"[FM-AUTH] Erreur: {e}")
        return None

def get_filemaker_data_direct(id_name):
    """Récupérer MAINFM et certificats directement depuis FileMaker"""
    token = get_filemaker_token()
    if not token:
        return None
    
    find_url = f"https://{FM_SERVER}/fmi/data/vLatest/databases/{FM_DATABASE}/layouts/{FM_LAYOUT}/_find"
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Chercher par CrmSearchArtwork (champ indexé)
    payload = {
        "query": [{"CrmSearchArtwork": id_name}],
        "limit": 1
    }
    
    try:
        response = requests.post(
            find_url,
            headers=headers,
            json=payload,
            verify=False,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            records = data.get('response', {}).get('data', [])
            
            if records:
                field_data = records[0].get('fieldData', {})
                return {
                    'MAINFM': field_data.get('MAINFM', ''),
                    'CertificateFMUrl': field_data.get('CertificateFMUrl', ''),
                    'CertificateWording': field_data.get('CertificateWording', '')
                }
        else:
            print(f"[FM-DIRECT] Erreur {response.status_code} pour {id_name}")
            
    except Exception as e:
        print(f"[FM-DIRECT] Erreur pour {id_name}: {e}")
    
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
# CACHED OPERAGALLERY API FUNCTIONS
# ============================================================================

# @cache_search  # CACHE TEMPORAIREMENT DÉSACTIVÉ POUR TESTS
def cached_search_operagallery_artworks(query, limit=None):
    """Cached version of OperaGallery search - CACHE DÉSACTIVÉ POUR TESTS"""
    try:
        print(f"🎯 [CACHE-DISABLED] Appel direct search_operagallery_artworks pour '{query}'")
        # Pas de limite par défaut - récupère TOUT
        actual_limit = limit if limit is not None else 10000  # Très grande limite
        return search_operagallery_artworks(query, actual_limit)
    except Exception as e:
        print(f"[CACHE] OperaGallery search error: {e}")
        return None

@cache_medium
def cached_get_operagallery_artwork_images(artwork_id):
    """Cached version of OperaGallery artwork images"""
    try:
        return get_operagallery_artwork_images(artwork_id)
    except Exception as e:
        print(f"[CACHE] OperaGallery images error: {e}")
        return None

@operagallery_bp.route('/api/artworks/search', methods=['POST'])
@operagallery_bp.route('/api/artworks/search-new', methods=['POST'])
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
        
        # 🔥 BYPASS COMPLET - UTILISER RECHERCHE DIRECTE SIMPLIFIÉE
        print(f"🔥 [BYPASS] Recherche FileMaker directe simplifiée pour '{query}'")
        
        try:
            import requests
            from requests.auth import HTTPBasicAuth
            import urllib3
            urllib3.disable_warnings()
            
            # Authentification directe
            auth_url = f"https://{FM_SERVER}/fmi/data/vLatest/databases/{FM_DATABASE}/sessions"
            auth_response = requests.post(auth_url, auth=HTTPBasicAuth(FM_USERNAME, FM_PASSWORD), json={}, verify=False, timeout=30)
            
            if auth_response.status_code == 200:
                token = auth_response.json()['response']['token']
                print(f"🔥 [BYPASS] ✅ Authentification réussie")
                
                # Recherche simplifiée avec le bon champ
                find_url = f"https://{FM_SERVER}/fmi/data/vLatest/databases/{FM_DATABASE}/layouts/CRMSearchArtworks/_find"
                headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
                payload = {
                    "query": [{"CrmSearchArtwork": f"*{query}*"}],
                    "limit": str(limit if limit else 200)
                }
                
                print(f"🔥 [BYPASS] Recherche avec payload: {payload}")
                search_response = requests.post(find_url, headers=headers, json=payload, verify=False, timeout=30)
                
                if search_response.status_code == 200:
                    data = search_response.json()
                    search_results = data.get('response', {}).get('data', [])
                    print(f"🔥 [BYPASS] ✅ {len(search_results)} résultats trouvés")
                    
                    # Convertir au format attendu et enrichir avec layout Artworks
                    formatted_results = []
                    for record in search_results:
                        field_data = record.get('fieldData', {})
                        record_id = record.get('recordId', 'unknown')
                        
                        # Enrichir avec les données du layout Artworks
                        enriched_data = {}
                        try:
                            artwork_url = f"https://{FM_SERVER}/fmi/data/vLatest/databases/{FM_DATABASE}/layouts/Artworks/records/{record_id}"
                            artwork_response = requests.get(artwork_url, headers=headers, verify=False, timeout=30)
                            
                            if artwork_response.status_code == 200:
                                artwork_data = artwork_response.json()
                                # 'data' est toujours une liste, même pour un record spécifique
                                data_list = artwork_data.get('response', {}).get('data', [])
                                if data_list:
                                    artwork_record = data_list[0]  # Premier (et seul) élément
                                    artwork_fields = artwork_record.get('fieldData', {})
                                else:
                                    artwork_fields = {}
                                enriched_data = {
                                    'mainfm_url': artwork_fields.get('MAINFM', ''),
                                    'medium': artwork_fields.get('Medium', ''),
                                    'dimensions': artwork_fields.get('SizeArtwork', ''),
                                    'location': artwork_fields.get('Location', ''),
                                    'status': artwork_fields.get('Status', ''),
                                    'description': artwork_fields.get('DescriptionEn', ''),
                                    'certificate_url': artwork_fields.get('CertificateFMUrl', ''),
                                    'certificate_wording': artwork_fields.get('CertificateWording', ''),
                                    'id_name': artwork_fields.get('IdName', str(record_id))
                                }
                                print(f"🔥 [ENRICH] {record_id}: MAINFM={bool(enriched_data['mainfm_url'])}, Cert={bool(enriched_data['certificate_url'])}")
                        except Exception as e:
                            print(f"🔥 [ENRICH] Erreur pour {record_id}: {e}")
                        
                        formatted_artwork = {
                            'id': str(record_id),
                            'IdName': enriched_data.get('id_name', str(record_id)),
                            'title': field_data.get('Name', ''),
                            'artist': field_data.get('ArtistName3', ''),
                            'year': field_data.get('Year', ''),
                            'category': 'Artwork',
                            'medium': enriched_data.get('medium', ''),
                            'description': enriched_data.get('description', ''),
                            'dimensions': enriched_data.get('dimensions', ''),
                            'location': enriched_data.get('location', ''),
                            'status': enriched_data.get('status', ''),
                            'main_picture_hd': enriched_data.get('mainfm_url', ''),
                            'mainfm_url': enriched_data.get('mainfm_url', ''),
                            'image_count': 1 if enriched_data.get('mainfm_url') else 0,
                            'record_id': record_id,
                            'source': 'FileMaker-Direct-Enriched'
                        }
                        
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
                    
                    # Fermer la session
                    delete_url = f"https://{FM_SERVER}/fmi/data/vLatest/databases/{FM_DATABASE}/sessions/{token}"
                    requests.delete(delete_url, headers=headers, verify=False, timeout=5)
                    
                    return jsonify({
                        'success': True,
                        'artworks': formatted_results,
                        'count': len(formatted_results),
                        'debug_info': f'Direct FileMaker search: {len(formatted_results)} results'
                    })
                else:
                    print(f"🔥 [BYPASS] Erreur recherche: {search_response.status_code} - {search_response.text[:200]}")
            else:
                print(f"🔥 [BYPASS] Échec authentification: {auth_response.status_code}")
                
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
                
                results = cached_search_operagallery_artworks(query, limit)
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

@operagallery_bp.route('/api/admin/artist-indexing/status', methods=['GET'])
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

@operagallery_bp.route('/api/admin/artist-indexing/test', methods=['GET'])
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

@operagallery_bp.route('/api/admin/artist-indexing/artists', methods=['GET'])
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

@operagallery_bp.route('/api/admin/artist-indexing/add', methods=['POST'])
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

@operagallery_bp.route('/api/admin/artist-indexing/remove', methods=['POST'])
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

@operagallery_bp.route('/api/admin/artist-indexing/start', methods=['POST'])
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

@operagallery_bp.route('/api/admin/artist-indexing/clear-cache', methods=['POST'])
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

@operagallery_bp.route('/api/admin/artist-indexing/index/<artist_name>', methods=['POST'])
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