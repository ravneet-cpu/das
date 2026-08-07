#!/usr/bin/env python3
"""
Script corrigé pour rechercher des œuvres dans OperaCRM avec les bons champs
Usage: python3 search_operacrm_corrected.py [options]
"""

import requests
import json
import sys
import argparse

class OperaCRMClient:
    def __init__(self, base_url="https://operacrm.com"):
        self.base_url = base_url
        self.session = requests.Session()
        self.session_id = None
    
    # Champs corrigés basés sur l'analyse de l'API
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
    
    def authenticate(self, db, login, password):
        """Authentification auprès d'OperaCRM"""
        url = f"{self.base_url}/web/session/authenticate"
        
        payload = {
            "jsonrpc": "2.0",
            "params": {
                "db": db,
                "login": login,
                "password": password
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
                
        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"Erreur de décodage JSON: {e}")
            return False
    
    def search_by_artist(self, artist_name, limit=200):
        """Rechercher des œuvres par nom d'artiste (recherche optimisée)"""
        if not self.session_id:
            print("Pas de session active.")
            return None
        
        url = f"{self.base_url}/web/dataset/call_kw"
        
        # Recherche prioritaire dans ArtistName, puis dans name et description
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "product.template",
                "method": "search_read",
                "args": [['|', '|', ('ArtistName', 'ilike', artist_name), 
                         ('name', 'ilike', artist_name), ('description', 'ilike', artist_name)]],
                "kwargs": {
                    "fields": self.ARTWORK_FIELDS,
                    "limit": limit
                }
            }
        }
        
        return self._execute_search(url, payload)
    
    def update_artwork_record(self, artwork_id, data_dict):
        if not self.session_id:
            print("Pas de session active.")
            return None
    
        print("creating with data:", data_dict)
        url = f"{self.base_url}/web/dataset/call_kw"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "product.template",
                "method": "write",
                "args": [[artwork_id], data_dict],
                "kwargs": {}
            }
        }
        try:
            response = requests.post(
                url, 
                json=payload,
                cookies={'session_id': self.session_id}
            )
            
            result = response.json()
            
            if 'error' in result:
                print(f"Erreur Odoo: {result['error']}")
                return None
            
            if 'result' in result:
                return result['result']  # Returns the ID of created record
            
        except Exception as e:
            print(f"Erreur lors de la création: {e}")
            return None

    def create(self, model, data_dict):
        """Generic create method for any Odoo model"""
        if not self.session_id:
            print("No active session for Odoo create()")
            return None

        url = f"{self.base_url}/web/dataset/call_kw"

        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": model,
                "method": "create",
                "args": [data_dict],
                "kwargs": {}
            }
        }

        try:
            response = requests.post(
                url,
                json=payload,
                cookies={"session_id": self.session_id}
            )
            result = response.json()

            if "error" in result:
                print("[ODOO CREATE ERROR]", result["error"])
                return None

            return result.get("result")

        except Exception as e:
            print("[ODOO CREATE EXCEPTION]", e)
            return None

    
    def create_artwork_record(self, artwork_id, final_filename):
        """Créer un enregistrement d'œuvre d'art avec gestion d'erreurs"""
        if not self.session_id:
            print("Pas de session active.")
            return None
        
        image_url = f'https://images.operagallery.com/FM/{final_filename}'
        data_dict = {
            "IdName": artwork_id,
            "image_url": image_url,
            "name": final_filename,
        }
        print("creating with data:", data_dict)
        url = f"{self.base_url}/web/dataset/call_kw"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "product.template",
                "method": "create",
                "args": [data_dict],
                "kwargs": {}
            }
        }
        try:
            response = requests.post(
                url, 
                json=payload,
                cookies={'session_id': self.session_id}
            )
            print(response.text)
            
            result = response.json()
            
            if 'error' in result:
                print(f"Erreur Odoo: {result['error']}")
                return None
            
            if 'result' in result:
                return result['result']  # Returns the ID of created record
            
        except Exception as e:
            print(f"Erreur lors de la création: {e}")
            return None

    def search_by_artwork_name(self, artwork_name, limit=200):
        """Rechercher des œuvres par nom d'œuvre"""
        if not self.session_id:
            print("Pas de session active.")
            return None
        
        url = f"{self.base_url}/web/dataset/call_kw"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "product.template",
                "method": "search_read",
                "args": [[('name', 'ilike', artwork_name)]],
                "kwargs": {
                    "fields": self.ARTWORK_FIELDS,
                    "limit": limit
                }
            }
        }
        
        return self._execute_search(url, payload)
    
    def search_by_id(self, artwork_id):
        """Rechercher une œuvre par ID"""
        if not self.session_id:
            print("Pas de session active.")
            return None
        
        url = f"{self.base_url}/web/dataset/call_kw"
        
        payload = {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {
                "model": "product.template",
                "method": "search_read",
                "args": [[('id', '=', artwork_id)]],
                "kwargs": {
                    "fields": self.ARTWORK_FIELDS
                }
            }
        }
        
        return self._execute_search(url, payload)
    
    def search_by_idname(self, id_name):
        """Rechercher une œuvre par IdName (ex: CANORA-53600)"""
        if not self.session_id:
            print("Pas de session active.")
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
        
        return self._execute_search(url, payload)
    
    def search_by_category(self, category, limit=200):
        """Rechercher des œuvres par catégorie"""
        if not self.session_id:
            print("Pas de session active.")
            return None
        
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
        
        return self._execute_search(url, payload)
    
    def _execute_search(self, url, payload):
        """Méthode utilitaire pour exécuter une recherche"""
        headers = {'Content-Type': 'application/json'}
        
        try:
            response = self.session.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            if 'error' in result:
                print(f"Erreur lors de la recherche: {result['error']}")
                return None
            
            return result.get('result', [])
            
        except requests.exceptions.RequestException as e:
            print(f"Erreur de connexion: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"Erreur de décodage JSON: {e}")
            return None

def display_results(results, search_type=""):
    """Afficher les résultats de recherche avec tous les détails"""
    if not results:
        print("Aucune œuvre trouvée.")
        return
    
    print(f"\n{len(results)} œuvre(s) trouvée(s) {search_type}:")
    print("=" * 80)
    
    for artwork in results:
        print(f"ID: {artwork.get('id')}")
        print(f"Nom: {artwork.get('name')}")
        print(f"Code ID: {artwork.get('IdName', 'N/A')}")
        print(f"Artiste: {artwork.get('ArtistName', 'N/A')}")
        print(f"Catégorie: {artwork.get('Category', 'N/A')}")
        print(f"Année: {artwork.get('artwork_year', 'N/A')}")
        print(f"Medium: {artwork.get('Medium', 'N/A')}")
        
        # Dimensions
        size_h = artwork.get('SizeH')
        size_l = artwork.get('SizeL')
        size_inc_h = artwork.get('SizeIncH')
        size_inc_l = artwork.get('SizeIncL')
        
        if size_h and size_l:
            print(f"Dimensions: {size_h} x {size_l} cm", end="")
            if size_inc_h and size_inc_l:
                print(f" ({size_inc_h} x {size_inc_l} in)")
            else:
                print()
        
        # Prix
        price = artwork.get('artwork_price_combined') or artwork.get('PriceRef')
        currency = artwork.get('CurrencyRef', 'EUR')
        if price:
            print(f"Prix: {price:,.2f} {currency}")
        
        # Localisation
        location = artwork.get('Location')
        sublocation = artwork.get('SubLocation')
        if location:
            print(f"Localisation: {location}", end="")
            if sublocation:
                print(f" - {sublocation}")
            else:
                print()
        
        print(f"Statut: {artwork.get('Status', 'N/A')}")
        
        # Images
        has_images = []
        if artwork.get('image_url'):
            has_images.append("URL")
        if artwork.get('image_1920'):
            has_images.append("1920px")
        if artwork.get('detail_1_image'):
            has_images.append("Détail 1")
        if artwork.get('detail_2_image'):
            has_images.append("Détail 2")
        
        if has_images:
            print(f"Images disponibles: {', '.join(has_images)}")
        
        # Description courte
        if artwork.get('description'):
            desc = str(artwork.get('description', ''))[:150]
            print(f"Description: {desc}{'...' if len(str(artwork.get('description', ''))) > 150 else ''}")
        
        print("-" * 40)




def main():
    parser = argparse.ArgumentParser(description='Rechercher des œuvres dans OperaCRM (version corrigée)')
    parser.add_argument('--artist', '-a', help='Rechercher par nom d\'artiste')
    parser.add_argument('--artwork', '-w', help='Rechercher par nom d\'œuvre')
    parser.add_argument('--id', '-i', type=int, help='Rechercher par ID')
    parser.add_argument('--idname', '-n', help='Rechercher par ID Name (ex: CANORA-53600)')
    parser.add_argument('--category', '-c', help='Rechercher par catégorie')
    parser.add_argument('--limit', '-l', type=int, default=10, help='Nombre maximum de résultats (défaut: 10)')
    
    args = parser.parse_args()
    
    # Paramètres de connexion
    db = "odoo_15"
    login = "surafelwubshet7@gmail.com"
    password = "Surafell"
    
    print("=== Connexion à OperaCRM (Version Corrigée) ===")
    
    # Créer le client
    client = OperaCRMClient()
    
    # Tenter l'authentification
    if not client.authenticate(db, login, password):
        print("Échec de l'authentification")
        return
    
    print("Connexion réussie!")
    
    # Effectuer la recherche selon les arguments
    if args.artist:
        print(f"\nRecherche d'œuvres de l'artiste: {args.artist}")
        results = client.search_by_artist(args.artist, args.limit)
        display_results(results, f"pour l'artiste '{args.artist}'")
    
    elif args.artwork:
        print(f"\nRecherche d'œuvres avec le nom: {args.artwork}")
        results = client.search_by_artwork_name(args.artwork, args.limit)
        display_results(results, f"avec le nom '{args.artwork}'")
    
    elif args.id:
        print(f"\nRecherche de l'œuvre ID: {args.id}")
        results = client.search_by_id(args.id)
        display_results(results, f"avec l'ID {args.id}")
    
    elif args.idname:
        print(f"\nRecherche de l'œuvre ID Name: {args.idname}")
        results = client.search_by_idname(args.idname)
        display_results(results, f"avec l'ID Name '{args.idname}'")
    
    elif args.category:
        print(f"\nRecherche d'œuvres dans la catégorie: {args.category}")
        results = client.search_by_category(args.category, args.limit)
        display_results(results, f"dans la catégorie '{args.category}'")
    
    else:
        print("\nAucune recherche spécifiée. Exemples d'utilisation:")
        print("python3 search_operacrm_corrected.py --artist 'Picasso'")
        print("python3 search_operacrm_corrected.py --artwork 'Altar'")
        print("python3 search_operacrm_corrected.py --id 137376")
        print("python3 search_operacrm_corrected.py --idname 'CANORA-53600'")
        print("python3 search_operacrm_corrected.py --category 'Painting'")
        print("python3 search_operacrm_corrected.py --artist 'Canogar' --limit 5")

if __name__ == "__main__":
    main()
