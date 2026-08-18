#!/usr/bin/env python3
"""
Client OperaCRM optimisé pour l'application photo validator
Basé sur le script corrigé avec tous les champs nécessaires
"""

import requests
import json
import os
from typing import Dict, List, Optional, Any

class OperaCRMClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8070"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session_id = None
        
        # Configuration depuis les variables d'environnement ou valeurs par défaut
        self.db = os.getenv('OPERACRM_DB', 'odoo_restore')
        self.login = os.getenv('OPERACRM_LOGIN', 'frederic@faucouneau.fr')
        self.password = os.getenv('OPERACRM_PASSWORD', 'ONc8VxiDFnSgCuwSkArqur3Sj1WFZhov')
    
    # Champs complets pour les œuvres d'art
    ARTWORK_FIELDS = [
        # Champs de base
        "id", "name", "default_code", "description",
        
        # Informations artiste
        "ArtistName", "res_artist_id", "LArtist",
        
        # Informations œuvre
        "Category", "artwork_year", "Medium", "artwork_signed",
        
        # Dimensions (en cm et inches)
        "SizeH", "SizeL", "SizeP",
        "SizeIncH", "SizeIncL", "SizeIncP",
        
        # Prix dans différentes devises
        "PriceRef", "CurrencyRef", "artwork_price_combined",
        "PriceEUREnt", "PriceUSDEnt", "PriceGBPEnt", "PriceCHFEnt",
        
        # Localisation et statut
        "Location", "SubLocation", "Status", "CustomsStatus",
        
        # Provenance et historique
        "artwork_provenance", "artwork_exhibited", "ConsignmentFrom",
        "ConsignmentDateIn", "ConsignmentDateOut", "PurchaseDate",
        
        # Images
        "image_url", "image_1920", "image_1024", "image_512",
        "detail_1_image", "detail_2_image",
        
        # Métadonnées
        "create_date", "write_date", "__last_update",
        "IdName", "Type", "Region"
    ]
    
    def authenticate(self) -> bool:
        """Authentification auprès d'OperaCRM"""
        url = f"{self.base_url}/web/session/authenticate"
        
        payload = {
            "jsonrpc": "2.0",
            "params": {
                "db": self.db,
                "login": self.login,
                "password": self.password
            }
        }
        
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = self.session.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            if 'error' in result:
                print(f"Erreur d'authentification: {result['error']}")
                return False
            
            if 'session_id' in self.session.cookies:
                self.session_id = self.session.cookies['session_id']
                return True
            else:
                return False
                
        except Exception as e:
            print(f"Erreur d'authentification: {e}")
            return False
    
    def ensure_authenticated(self) -> bool:
        """S'assurer que la session est active"""
        if not self.session_id:
            return self.authenticate()
        return True
    
    def search_by_id_name(self, id_name: str) -> Optional[Dict[str, Any]]:
        """Rechercher une œuvre par IdName (ex: CANORA-53600)"""
        if not self.ensure_authenticated():
            return None
        
        url = f"{self.base_url}/web/dataset/call_kw"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "product.template",
                "method": "search_read",
                "args": [[('IdName', '=', id_name)]],
                "kwargs": {
                    "fields": self.ARTWORK_FIELDS
                }
            }
        }
        
        result = self._execute_call(url, payload)
        return result[0] if result and len(result) > 0 else None
    
    def search_by_artist(self, artist_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Rechercher des œuvres par nom d'artiste"""
        if not self.ensure_authenticated():
            return []
        
        url = f"{self.base_url}/web/dataset/call_kw"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "product.template",
                "method": "search_read",
                "args": [[('ArtistName', 'ilike', artist_name)]],
                "kwargs": {
                    "fields": self.ARTWORK_FIELDS,
                    "limit": limit
                }
            }
        }
        
        return self._execute_call(url, payload) or []
    
    def search_by_title(self, title: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Rechercher des œuvres par titre"""
        if not self.ensure_authenticated():
            return []
        
        url = f"{self.base_url}/web/dataset/call_kw"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "product.template",
                "method": "search_read",
                "args": [[('name', 'ilike', title)]],
                "kwargs": {
                    "fields": self.ARTWORK_FIELDS,
                    "limit": limit
                }
            }
        }
        
        return self._execute_call(url, payload) or []
    
    def search_by_category(self, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Rechercher des œuvres par catégorie"""
        if not self.ensure_authenticated():
            return []
        
        url = f"{self.base_url}/web/dataset/call_kw"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "product.template",
                "method": "search_read",
                "args": [[('Category', 'ilike', category)]],
                "kwargs": {
                    "fields": self.ARTWORK_FIELDS,
                    "limit": limit
                }
            }
        }
        
        return self._execute_call(url, payload) or []
    
    def global_search(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Recherche globale dans tous les champs pertinents"""
        if not self.ensure_authenticated():
            return []
        
        url = f"{self.base_url}/web/dataset/call_kw"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "product.template",
                "method": "search_read",
                "args": [['|', '|', '|', '|', 
                         ('ArtistName', 'ilike', query),
                         ('name', 'ilike', query),
                         ('IdName', 'ilike', query),
                         ('Category', 'ilike', query),
                         ('description', 'ilike', query)]],
                "kwargs": {
                    "fields": self.ARTWORK_FIELDS,
                    "limit": limit
                }
            }
        }
        
        return self._execute_call(url, payload) or []
    
    def _execute_call(self, url: str, payload: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """Méthode utilitaire pour exécuter un appel API"""
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = self.session.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            if 'error' in result:
                print(f"Erreur API: {result['error']}")
                return None
            
            return result.get('result', [])
            
        except Exception as e:
            print(f"Erreur lors de l'appel API: {e}")
            return None
    
    def format_artwork_for_frontend(self, artwork: Dict[str, Any]) -> Dict[str, Any]:
        """Formater les données d'œuvre pour le frontend"""
        if not artwork:
            return {}
        
        # Construire les URLs d'images
        image_urls = []
        
        # Ajouter les différentes images disponibles
        for img_field in ['image_1920', 'image_1024', 'image_512', 'detail_1_image', 'detail_2_image']:
            if artwork.get(img_field):
                # Construire l'URL de l'image (en supposant qu'il y ait un endpoint pour cela)
                img_url = f"{self.base_url}/web/image/product.template/{artwork.get('id')}/{img_field}"
                image_urls.append(img_url)
        
        # Si une URL d'image directe est disponible
        if artwork.get('image_url'):
            image_urls.append(artwork['image_url'])
        
        return {
            'id': artwork.get('id'),
            'IdName': artwork.get('IdName', ''),
            'title': artwork.get('name', ''),
            'artist': artwork.get('ArtistName', ''),
            'year': artwork.get('artwork_year', ''),
            'category': artwork.get('Category', ''),
            'medium': artwork.get('Medium', ''),
            'description': artwork.get('description', ''),
            'dimensions': self._format_dimensions(artwork),
            'price_estimate': self._format_price(artwork),
            'location': artwork.get('Location', ''),
            'status': artwork.get('Status', ''),
            'signed': artwork.get('artwork_signed', ''),
            'provenance': artwork.get('artwork_provenance', ''),
            'exhibited': artwork.get('artwork_exhibited', ''),
            'main_picture_hd': image_urls[0] if image_urls else None,
            'all_image_urls': image_urls,
            'image_count': len(image_urls),
            'created_date': artwork.get('create_date', ''),
            'updated_date': artwork.get('write_date', '')
        }
    
    def _format_dimensions(self, artwork: Dict[str, Any]) -> str:
        """Formater les dimensions"""
        h = artwork.get('SizeH')
        l = artwork.get('SizeL')
        p = artwork.get('SizeP')
        
        h_in = artwork.get('SizeIncH')
        l_in = artwork.get('SizeIncL')
        
        dimensions = []
        
        if h and l:
            if p and p > 0:
                dimensions.append(f"{h} × {l} × {p} cm")
            else:
                dimensions.append(f"{h} × {l} cm")
        
        if h_in and l_in:
            dimensions.append(f"({h_in} × {l_in} in)")
        
        return " ".join(dimensions) if dimensions else ""
    
    def _format_price(self, artwork: Dict[str, Any]) -> str:
        """Formater le prix"""
        price = artwork.get('artwork_price_combined') or artwork.get('PriceRef')
        currency = artwork.get('CurrencyRef', 'EUR')
        
        if price:
            return f"{price:,.0f} {currency}"
        
        return ""

# Instance globale du client
operacrm_client = OperaCRMClient()

# Fonctions utilitaires pour l'API Flask
def search_artwork_by_id(id_name: str) -> Dict[str, Any]:
    """Rechercher une œuvre par ID pour l'API Flask"""
    try:
        artwork = operacrm_client.search_by_id_name(id_name)
        if artwork:
            return {
                'success': True,
                'artwork': operacrm_client.format_artwork_for_frontend(artwork)
            }
        else:
            return {
                'success': False,
                'message': 'Artwork not found'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def search_artworks(query: str, search_type: str = 'all', limit: int = 20) -> Dict[str, Any]:
    """Rechercher des œuvres pour l'API Flask"""
    try:
        if search_type == 'artist':
            results = operacrm_client.search_by_artist(query, limit)
        elif search_type == 'artwork_id':
            # Pour un ID spécifique, on fait une recherche exacte
            single_result = operacrm_client.search_by_id_name(query)
            results = [single_result] if single_result else []
        elif search_type == 'title':
            results = operacrm_client.search_by_title(query, limit)
        elif search_type == 'category':
            results = operacrm_client.search_by_category(query, limit)
        else:  # search_type == 'all'
            results = operacrm_client.global_search(query, limit)
        
        formatted_results = [
            operacrm_client.format_artwork_for_frontend(artwork) 
            for artwork in results
        ]
        
        return {
            'success': True,
            'artworks': formatted_results,
            'total': len(formatted_results)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'artworks': [],
            'total': 0
        }