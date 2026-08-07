#!/usr/bin/env python3
"""
Intégration OperaGallery pour Photo Validator
Connecte le search de photo validator à la base OperaGallery et retourne les images
"""

import requests
import json
import re
import csv
import os
from requests.auth import HTTPBasicAuth
import urllib3
from urllib.parse import quote

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cache global pour les URLs MAINFM
_mainfm_urls = None

# Cache global pour les champs d'images depuis CSV
_image_fields_cache = None

def load_mainfm_urls():
    """Charger les URLs MAINFM depuis le fichier CSV"""
    global _mainfm_urls
    if _mainfm_urls is not None:
        return _mainfm_urls
    
    # ⚡ OPTIMISATION: Désactiver temporairement pour tests de performance
    _mainfm_urls = {}
    return _mainfm_urls
    
    _mainfm_urls = {}
    # Essayer plusieurs chemins possibles
    csv_paths = [
        '/app/list-url-id.csv',  # Chemin dans le container
        'list-url-id.csv',       # Répertoire courant (ajouté au Dockerfile)
        '../list-url-id.csv',    # Depuis frontend/
        '/home/projet/photo-validator/list-url-id.csv'  # Chemin absolu
    ]
    
    csv_path = None
    for path in csv_paths:
        if os.path.exists(path):
            csv_path = path
            break
    
    try:
        if csv_path and os.path.exists(csv_path):
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 5 and row[0] and row[4]:
                        url = row[0].strip()
                        artwork_id = row[4].strip()
                        if url.startswith('https://') and artwork_id:
                            _mainfm_urls[artwork_id] = url
            print(f"[MAINFM] Loaded {len(_mainfm_urls)} URLs from CSV")
        else:
            print(f"[MAINFM] CSV file not found: {csv_path}")
    except Exception as e:
        print(f"[MAINFM] Error loading CSV: {e}")
        _mainfm_urls = {}
    
    return _mainfm_urls

def load_image_fields_from_csv():
    """Charger les champs d'images depuis images_catalog.csv"""
    global _image_fields_cache
    if _image_fields_cache is not None:
        return _image_fields_cache
    
    # ⚡ OPTIMISATION: Désactiver temporairement pour tests de performance
    _image_fields_cache = {}
    return _image_fields_cache
    
    _image_fields_cache = {}
    
    # Mapping des types CSV vers les champs FileMaker
    TYPE_TO_FIELD_MAPPING = {
        'MAIN': 'MAIN300',
        'OTHER': 'OTHER300', 
        'DET': 'DET300',
        'INSITU': 'INSITU300',
        'BACK': 'BACK300',
        'FRONT': 'FRONT300',
        'FRAME': 'FRAME300',
        'LEFT': 'LEFT300',
        'FRONTRIGHT': 'FRONTRIGHT300',
        'PERS': 'PERS300'
    }
    
    # Essayer plusieurs chemins possibles pour images_catalog.csv
    csv_paths = [
        '/app/images_catalog.csv',  # Chemin dans le container
        'images_catalog.csv',       # Répertoire courant
        '../images_catalog.csv',    # Depuis frontend/
        '/home/projet/photo-validator/images_catalog.csv'  # Chemin absolu
    ]
    
    csv_path = None
    for path in csv_paths:
        if os.path.exists(path):
            csv_path = path
            break
    
    try:
        if csv_path and os.path.exists(csv_path):
            print(f"[IMAGE-FIELDS] Loading from CSV: {csv_path}")
            
            from collections import defaultdict
            
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                
                # Structure: {artwork_id: {field_name: [urls]}}
                temp_data = defaultdict(lambda: defaultdict(list))
                
                for row in reader:
                    artwork_id = row['id'].strip()
                    image_type = row['type'].strip()
                    image_url = row['localisation'].strip()
                    
                    if artwork_id and image_type and image_url:
                        # Mapper le type vers le nom de champ FileMaker
                        field_name = TYPE_TO_FIELD_MAPPING.get(image_type)
                        if field_name:
                            temp_data[artwork_id][field_name].append(image_url)
                
                # Convertir en format final avec URLs jointes par \n
                for artwork_id, fields in temp_data.items():
                    _image_fields_cache[artwork_id] = {}
                    for field_name, urls in fields.items():
                        if len(urls) == 1:
                            _image_fields_cache[artwork_id][field_name] = urls[0]
                        else:
                            _image_fields_cache[artwork_id][field_name] = '\n'.join(urls)
                
            print(f"[IMAGE-FIELDS] Loaded image fields for {len(_image_fields_cache)} artworks")
            
            # Debug: montrer quelques exemples
                
        else:
            print(f"[IMAGE-FIELDS] CSV file not found: {csv_path}")
    except Exception as e:
        print(f"[IMAGE-FIELDS] Error loading CSV: {e}")
        _image_fields_cache = {}
    
    return _image_fields_cache

class OperaGalleryClient:
    def __init__(self):
        self.server = "178.248.210.53"
        self.username = "DataApiAccess"
        self.password = "JPMEJU1JPMEJU1"
        self.token = None
        self.session = None
    
    def authenticate(self):
        """Créer une session FileMaker et obtenir un token"""
        self.session = requests.Session()
        self.session.verify = False
        self.session.auth = HTTPBasicAuth(self.username, self.password)
        
        try:
            session_url = f"https://{self.server}/fmi/data/vLatest/databases/OperaGallery/sessions"
            response = self.session.post(session_url, json={}, timeout=60)
            
            if response.status_code == 200:
                self.token = response.json()['response']['token']
                return True
            else:
                print(f"Échec authentification: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Erreur authentification: {e}")
            return False
    
    def get_headers(self):
        """Obtenir les headers avec token Bearer"""
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
    

    def _translate_search_terms(self, query):
        """Traduire les termes français vers anglais pour la recherche"""
        translations = {
            'femme': 'woman',
            'homme': 'man', 
            'chat': 'cat',
            'chien': 'dog',
            'fleur': 'flower',
            'fleurs': 'flowers',
            'maison': 'house',
            'enfant': 'child',
            'enfants': 'children',
            'nature': 'nature',
            'mort': 'death',
            'vie': 'life',
            'amour': 'love',
            'guerre': 'war',
            'paix': 'peace',
            'nu': 'nude',
            'portrait': 'portrait',
            'paysage': 'landscape',
            'mer': 'sea',
            'montagne': 'mountain',
            'arbre': 'tree',
            'arbres': 'trees',
            'soleil': 'sun',
            'lune': 'moon',
            'étoile': 'star',
            'étoiles': 'stars',
            'rouge': 'red',
            'bleu': 'blue',
            'vert': 'green',
            'jaune': 'yellow',
            'noir': 'black',
            'blanc': 'white'
        }
        
        # Séparer les mots et traduire individuellement
        words = query.lower().split()
        translated_words = []
        
        for word in words:
            # Enlever la ponctuation
            clean_word = word.strip('.,!?;:')
            if clean_word in translations:
                translated_words.append(translations[clean_word])
                print(f"[TRANSLATE] '{clean_word}' → '{translations[clean_word]}'")
            else:
                translated_words.append(word)  # Garder le mot original
        
        translated_query = ' '.join(translated_words)
        
        if translated_query != query.lower():
            print(f"[TRANSLATE] Requête traduite: '{query}' → '{translated_query}'")
            return translated_query
        
        return query

    def search_artworks(self, query, limit=500, max_retries=2):
        """
        Rechercher des œuvres d'art dans OperaGallery
        Supporte la recherche par artiste, nom d'œuvre, etc.
        Inclut une logique de retry pour gérer les timeouts
        Traduction automatique français → anglais
        """
        print(f"[SEARCH] 🎯 Début search_artworks: query='{query}', limit={limit}")
        
        if not self.token:
            print(f"[SEARCH] Pas de token, tentative authentification...")
            if not self.authenticate():
                print(f"[SEARCH] ❌ Échec authentification")
                return None
            print(f"[SEARCH] ✅ Authentification réussie, token: {self.token[:20]}...")
        
        # TRADUCTION DÉSACTIVÉE
        original_query = query
        # query = self._translate_search_terms(query)  # DÉSACTIVÉ
        
        find_url = f"https://{self.server}/fmi/data/vLatest/databases/OperaGallery/layouts/CRMSearchArtworks/_find"
        print(f"[SEARCH] URL: {find_url}")
        
        # 🎯 RECHERCHE OperaCRM : Utiliser IdNameIndexed2 pour trouver les IDs artwork
        find_payload = {
            "query": [{"IdNameIndexed2": f"*{query}*"}],
            "limit": str(limit)
        }
        print(f"[SEARCH] Payload exactement comme test manuel: {find_payload}")
        
        # Retry logic pour gérer les timeouts
        for attempt in range(max_retries):
            try:
                print(f"[SEARCH] Tentative {attempt + 1}/{max_retries} pour '{query}'")
                print(f"[SEARCH] Headers: {self.get_headers()}")
                print(f"[SEARCH] Payload: {find_payload}")
                
                # Timeout normal pour le cache
                timeout = 45 if attempt < 1 else 90
                
                response = requests.post(find_url, headers=self.get_headers(), 
                                       json=find_payload, verify=False, timeout=timeout)
                
                if response.status_code == 200:
                    data = response.json()
                    if 'response' in data and 'data' in data['response']:
                        # Étape 1 : Résultats de recherche dans CRMSearchArtworks
                        search_results = data['response']['data']
                        print(f"[SEARCH] Étape 1: {len(search_results)} résultats trouvés dans CRMSearchArtworks")
                        
                        # 🔧 TEMPORAIRE: Retourner les résultats basiques sans enrichissement pour debug
                        basic_results = []
                        for record in search_results:
                            field_data = record.get('fieldData', {})
                            basic_results.append({
                                'record_id': record.get('recordId'),
                                'artist_name': field_data.get('ArtistName3', ''),
                                'artwork_name': field_data.get('Name', ''),
                                'year': field_data.get('Year', ''),
                                'crm_search_content': field_data.get('CrmSearchArtwork', ''),
                                'MAINFM': '',  # Vide pour l'instant
                                'mainfm': '',
                                'images': {'primary_image': None, 'mainfm_url': None}
                            })
                        print(f"[SEARCH] Retour de {len(basic_results)} résultats basiques")
                        return basic_results
                        
                        # Étape 2 : Enrichir chaque résultat avec les données du layout Artworks (DÉSACTIVÉ)
                        # enriched_results = self.enrich_with_artwork_details(search_results)
                        # print(f"[SEARCH] Étape 2: {len(enriched_results)} résultats enrichis depuis Artworks")
                        # return enriched_results
                elif response.status_code == 404:
                    print(f"[SEARCH] Aucun résultat trouvé pour '{query}'")
                    return []  # Aucun résultat trouvé
                else:
                    print(f"[SEARCH] Erreur HTTP {response.status_code} (tentative {attempt + 1})")
                    print(f"[SEARCH] Response text: {response.text[:500]}")
                    if attempt == max_retries - 1:  # Dernière tentative
                        return None
                    
            except requests.exceptions.Timeout as e:
                print(f"[SEARCH] Timeout tentative {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:  # Dernière tentative
                    print(f"[SEARCH] Échec définitif après {max_retries} tentatives")
                    return None
                    
                # Attendre un peu avant de réessayer
                import time
                time.sleep(2)
                
            except Exception as e:
                print(f"[SEARCH] Erreur tentative {attempt + 1}/{max_retries}: {e}")
                if attempt == max_retries - 1:  # Dernière tentative
                    return None
                    
                # Attendre un peu avant de réessayer
                import time
                time.sleep(1)
        
        return None
    
    def enrich_with_artwork_details(self, search_results):
        """Enrichir les résultats de recherche avec les détails du layout Artworks"""
        enriched_results = []
        
        for search_record in search_results:
            try:
                # Extraire l'ID de l'œuvre depuis CRMSearchArtworks
                search_data = search_record.get('fieldData', {})
                record_id = search_record.get('recordId', '')
                # Dans CRMSearchArtworks, on n'a pas IdName, on utilise le recordId
                artwork_id = record_id
                
                if not artwork_id:
                    print(f"[ENRICH-ARTWORK] Pas d'ID trouvé, skip")
                    continue
                
                # Chercher les détails dans le layout Artworks
                artwork_details = self.get_artwork_from_artworks_layout(artwork_id)
                
                if artwork_details:
                    enriched_results.append(artwork_details)
                    print(f"[ENRICH-ARTWORK] ✅ {artwork_id}: Détails récupérés")
                else:
                    print(f"[ENRICH-ARTWORK] ❌ {artwork_id}: Pas trouvé dans Artworks")
                    
            except Exception as e:
                print(f"[ENRICH-ARTWORK] Erreur: {e}")
                
        return enriched_results
    
    def get_artwork_from_artworks_layout(self, artwork_id):
        """Récupérer les détails d'une œuvre depuis le layout Artworks"""
        try:
            # Récupérer directement par record ID
            artworks_url = f"https://{self.server}/fmi/data/vLatest/databases/OperaGallery/layouts/Artworks/records/{artwork_id}"
            
            response = requests.get(artworks_url, headers=self.get_headers(), verify=False, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'response' in data and 'data' in data['response']:
                    # Traiter le résultat avec process_artwork_results
                    artwork_record = data['response']['data']
                    processed = self.process_artwork_results([artwork_record])  # Wrap dans une liste
                    return processed[0] if processed else None
                    
        except Exception as e:
            print(f"[ARTWORK-DETAIL] Erreur pour {artwork_id}: {e}")
            
        return None
    
    def process_artwork_results(self, records):
        """Traiter les résultats et extraire les informations d'images"""
        processed_results = []
        
        for record in records:
            if 'fieldData' not in record:
                continue
                
            field_data = record['fieldData']
            record_id = record.get('recordId')
            
            # Extraire les informations de base
            id_name = field_data.get('IdName', '')
            
            # ⚡ OPTIMISATION: Bypass CSV loading pour performance
            final_mainfm = field_data.get('MAINFM', '')
            csv_image_fields = {}
            
            # Préparer les champs d'images (priorité: FileMaker > CSV)
            image_fields = {
                'MAIN300': field_data.get('MAIN300', '') or csv_image_fields.get('MAIN300', ''),
                'OTHER300': field_data.get('OTHER300', '') or csv_image_fields.get('OTHER300', ''),
                'DET300': field_data.get('DET300', '') or csv_image_fields.get('DET300', ''),
                'INSITU300': field_data.get('INSITU300', '') or csv_image_fields.get('INSITU300', ''),
                'BACK300': field_data.get('BACK300', '') or csv_image_fields.get('BACK300', ''),
                'FRONT300': field_data.get('FRONT300', '') or csv_image_fields.get('FRONT300', ''),
                'FRAME300': field_data.get('FRAME300', '') or csv_image_fields.get('FRAME300', ''),
                'LEFT300': field_data.get('LEFT300', '') or csv_image_fields.get('LEFT300', ''),
                'FRONTRIGHT300': field_data.get('FRONTRIGHT300', '') or csv_image_fields.get('FRONTRIGHT300', ''),
                'PERS300': field_data.get('PERS300', '') or csv_image_fields.get('PERS300', '')
            }
            
            # Debug logging pour les nouveaux champs
            non_empty_fields = {k: v for k, v in image_fields.items() if v.strip()}
            if id_name and non_empty_fields:
                print(f"[NEW-IMAGE-FIELDS] {id_name}: {len(non_empty_fields)} champs avec images: {list(non_empty_fields.keys())}")
                # Afficher le détail pour debug
                for field_name, urls in non_empty_fields.items():
                    url_count = len(urls.split('\n')) if '\n' in urls else 1
                    print(f"  -> {field_name}: {url_count} URL(s)")
            elif id_name:
                print(f"[NEW-IMAGE-FIELDS] {id_name}: AUCUN champ d'image trouvé (FM: 0, CSV: {len(csv_image_fields)})")
            
            # Debug logging original
            if id_name:
                print(f"[ARTWORK-PROCESSING] {id_name}: MAINFM={bool(final_mainfm)}, Picture={bool(field_data.get('Picture', ''))}")
            
            artwork_info = {
                "record_id": record_id,
                "artist_name": field_data.get('Artists::TotalNameArtist', field_data.get('ArtistName3', '')),
                "artwork_name": field_data.get('Name', ''),
                "year": field_data.get('Artworkyear', ''),
                "id_name": id_name,
                "medium": field_data.get('Medium', ''),
                "size": field_data.get('SizeArtwork', ''),
                "location": field_data.get('Location', ''),
                "status": field_data.get('Status', ''),
                "mainfm": final_mainfm,  # URL de l'image principale MAINFM
                "MAINFM": final_mainfm,  # 🔧 MAJUSCULES pour API compatibility
                # 🔧 AJOUTER LE CHAMP PICTURE POUR LE FALLBACK
                "Picture": field_data.get('Picture', ''),
                "images": self.extract_image_urls(field_data, record_id),
                # 🎯 AJOUTER LES NOUVEAUX CHAMPS D'IMAGES
                "MAIN300": image_fields['MAIN300'],
                "OTHER300": image_fields['OTHER300'],
                "DET300": image_fields['DET300'],
                "INSITU300": image_fields['INSITU300'],
                "BACK300": image_fields['BACK300'],
                "FRONT300": image_fields['FRONT300'],
                "FRAME300": image_fields['FRAME300'],
                "LEFT300": image_fields['LEFT300'],
                "FRONTRIGHT300": image_fields['FRONTRIGHT300'],
                "PERS300": image_fields['PERS300']
            }
            
            processed_results.append(artwork_info)
        
        return processed_results
    
    def extract_image_urls(self, field_data, record_id):
        """Extraire UNIQUEMENT les URLs MAINFM"""
        images = {
            "web_urls": [],
            "hd_urls": [],
            "container_fields": [],
            "thumbnail_url": None,
            "primary_image": None,
            "mainfm_url": None
        }
        
        # UTILISER UNIQUEMENT LES URLs MAINFM depuis le CSV
        id_name = field_data.get('IdName', '')
        if id_name:
            mainfm_urls = load_mainfm_urls()
            mainfm_url = mainfm_urls.get(id_name, '')
            if mainfm_url:
                images["primary_image"] = mainfm_url
                images["mainfm_url"] = mainfm_url
        
        # Plus aucune autre logique d'images - MAINFM uniquement
        return images
    
    # Méthode parse_hd_urls supprimée - MAINFM uniquement
    
    def get_artwork_by_id(self, artwork_id):
        """Récupérer une œuvre spécifique par son ID"""
        if not self.token:
            if not self.authenticate():
                return None
        
        try:
            # Rechercher dans OperaCRM avec IdNameIndexed2
            find_url = f"https://{self.server}/fmi/data/vLatest/databases/OperaGallery/layouts/CRMSearchArtworks/_find"
            find_payload = {
                "query": [{"IdNameIndexed2": f"*{artwork_id}*"}]
            }
            
            response = requests.post(find_url, headers=self.get_headers(), 
                                   json=find_payload, verify=False, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if 'response' in data and 'data' in data['response']:
                    results = self.process_artwork_results(data['response']['data'])
                    return results[0] if results else None
            
            return None
            
        except Exception as e:
            print(f"Erreur récupération artwork {artwork_id}: {e}")
            return None
    
    def close_session(self):
        """Fermer la session FileMaker"""
        if self.token:
            try:
                delete_url = f"https://{self.server}/fmi/data/vLatest/databases/OperaGallery/sessions/{self.token}"
                requests.delete(delete_url, headers=self.get_headers(), verify=False, timeout=5)
            except:
                pass
            self.token = None


def search_operagallery_artworks(query, limit=10000):
    """
    Fonction principale pour rechercher des œuvres d'art dans OperaGallery
    Compatible avec l'API photo-validator existante
    Recherche en 2 étapes : CRMSearchArtworks puis enrichissement via Artworks
    """
    print(f"🔥🔥🔥 [SEARCH-STANDALONE] NOUVELLE VERSION - Début recherche: '{query}' (limit: {limit}) 🔥🔥🔥")
    
    # Utiliser la classe OperaGalleryClient avec la logique 2-étapes
    client = OperaGalleryClient()
    if not client.authenticate():
        print(f"[SEARCH-STANDALONE] ❌ Échec authentification")
        return None
    
    try:
        print(f"[SEARCH-STANDALONE] Appel client.search_artworks('{query}', {limit})")
        results = client.search_artworks(query, limit)
        print(f"[SEARCH-STANDALONE] ✅ Résultats: {len(results) if results else 0}")
        return results
    except Exception as e:
        import traceback
        print(f"[SEARCH-STANDALONE] ❌ Erreur: {e}")
        print(f"[SEARCH-STANDALONE] Traceback:")
        traceback.print_exc()
        return None
    finally:
        client.close_session()

# ANCIENNE VERSION AVEC TRADUCTION (DÉSACTIVÉE)
def search_operagallery_artworks_OLD(query, limit=10000):
    """
    ANCIENNE VERSION avec traduction - gardée pour référence
    """
    # ⭐ TRADUCTION BIDIRECTIONNELLE FRANÇAIS ↔ ANGLAIS
    fr_to_en = {
        'femme': 'woman',
        'homme': 'man', 
        'chat': 'cat',
        'chien': 'dog',
        'fleur': 'flower',
        'fleurs': 'flowers',
        'enfant': 'child',
        'enfants': 'children',
        'nu': 'nude',
        'portrait': 'portrait',
        'paysage': 'landscape',
        'nature': 'nature',
        'mer': 'sea',
        'montagne': 'mountain',
        'arbre': 'tree',
        'arbres': 'trees',
        'maison': 'house',
        'ville': 'city',
        'soleil': 'sun',
        'lune': 'moon',
        'étoile': 'star',
        'étoiles': 'stars',
        'nuit': 'night',
        'jour': 'day',
        'matin': 'morning',
        'soir': 'evening',
        'amour': 'love',
        'mort': 'death',
        'vie': 'life',
        'guerre': 'war',
        'paix': 'peace',
        'fête': 'party',
        'danse': 'dance',
        'musique': 'music',
        'rouge': 'red',
        'bleu': 'blue',
        'vert': 'green',
        'jaune': 'yellow',
        'noir': 'black',
        'blanc': 'white',
        'rose': 'pink',
        'violet': 'purple',
        'orange': 'orange',
        'gris': 'gray',
        'marron': 'brown'
    }
    
    # Traduction inverse anglais → français
    en_to_fr = {v: k for k, v in fr_to_en.items()}
    
    # Ajouter des termes supplémentaires anglais → français
    en_to_fr.update({
        'woman': 'femme',
        'man': 'homme',
        'cat': 'chat',
        'dog': 'chien',
        'flower': 'fleur',
        'flowers': 'fleurs',
        'child': 'enfant',
        'children': 'enfants',
        'nude': 'nu',
        'portrait': 'portrait',
        'landscape': 'paysage',
        'still': 'nature',
        'sea': 'mer',
        'mountain': 'montagne',
        'tree': 'arbre',
        'trees': 'arbres',
        'house': 'maison',
        'city': 'ville',
        'sun': 'soleil',
        'moon': 'lune',
        'star': 'étoile',
        'stars': 'étoiles',
        'night': 'nuit',
        'day': 'jour',
        'morning': 'matin',
        'evening': 'soir',
        'love': 'amour',
        'death': 'mort',
        'life': 'vie',
        'war': 'guerre',
        'peace': 'paix',
        'party': 'fête',
        'dance': 'danse',
        'music': 'musique'
    })
    
    original_query = query
    words = query.lower().split()
    
    # ⚡ PERFORMANCE : Recherche simple sans traduction
    search_queries = [query]
    
    print(f"[TRANSLATE] Recherche avec {len(search_queries)} variantes: {search_queries}")
    
    # Faire les recherches avec toutes les variantes et combiner les résultats
    all_results = []
    seen_ids = set()
    
    for search_query in search_queries:
        client = OperaGalleryClient()
        try:
            results = client.search_artworks(search_query, limit, max_retries=3)
            if results:
                print(f"[SEARCH] '{search_query}': {len(results)} résultats")
                for result in results:
                    # ⚡ FIX: Utiliser record_id si id_name est vide
                    id_name = result.get('id_name', '')
                    record_id = result.get('record_id', '')
                    result_id = id_name if id_name.strip() else f"record_{record_id}"
                    
                    if result_id not in seen_ids:
                        all_results.append(result)
                        seen_ids.add(result_id)
        finally:
            client.close_session()
    
    print(f"[SEARCH] Total combiné: {len(all_results)} résultats uniques")
    return all_results[:limit] if limit else all_results


def get_operagallery_artwork_images(artwork_id):
    """
    Récupérer les images d'une œuvre spécifique
    Compatible avec l'API photo-validator existante
    """
    client = OperaGalleryClient()
    
    try:
        artwork = client.get_artwork_by_id(artwork_id)
        if artwork:
            return artwork.get('images', {})
        return None
    finally:
        client.close_session()


if __name__ == "__main__":
    # Test de recherche Picasso
    print("🎯 TEST RECHERCHE PICASSO DANS OPERAGALLERY")
    print("=" * 60)
    
    results = search_operagallery_artworks("Picasso", limit=10)
    
    if results:
        print(f"✅ Trouvé {len(results)} œuvres de Picasso")
        
        for i, artwork in enumerate(results[:3]):
            print(f"\n--- Œuvre #{i+1} ---")
            print(f"Artiste: {artwork['artist_name']}")
            print(f"Œuvre: {artwork['artwork_name']}")
            print(f"Année: {artwork['year']}")
            print(f"ID: {artwork['id_name']}")
            
            images = artwork['images']
            if images['primary_image']:
                print(f"Image principale: {images['primary_image']}")
            if images['hd_urls']:
                print(f"Images HD: {len(images['hd_urls'])} disponibles")
            
    else:
        print("❌ Aucun résultat trouvé")