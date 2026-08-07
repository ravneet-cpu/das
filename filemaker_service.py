#!/usr/bin/env python3
"""
FileMaker service for photo validator
Handles FileMaker database operations for artwork image management
"""

import requests
from requests.auth import HTTPBasicAuth
import os
import re
import urllib3
import time

# Disable SSL warnings for FileMaker self-signed certificate
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class FileMakerService:
    def __init__(self):
        self.server = '178.248.210.53'
        self.database = 'OperaGallery'
        self.layout = 'Artworks'
        self.username = 'DataApiAccess'
        self.password = 'JPMEJU1JPMEJU1'
        self.token = None
        self.session = None
        self.token_timestamp = None
        # # self.server = '178.248.210.53'
        # self.server = '172.29.0.2:9443'
        # # self.server = 'host.docker.internal:8443'
        # self.database = 'OperaGallery'
        # self.layout = 'Artworks'
        # self.username = 'DataApiAccess'
        # self.password = 'JPMEJU1JPMEJU1'
        # self.token = None
        # self.session = None
        # self.token_timestamp = None
        
    FIELD_MAPPING = {
        "main_picture_hd": "MAINFM",
        "main_web_picture": "UHDPictureUrl",
        "image_url": "UHDPictureUrl",
        "thumbnail_url": "ThumbnailCrm",
        "detail_1_url": "DET300",
        "detail_2_url": "DET2300",
        "other_url": "BACK300",         # Default back view
        "perspective_url": "FRONT300",  # Default front view
        "left_url": "LEFT300",
        "right_url": "FRONTRIGHT300",
        "frame_url": "FRAME300",
        "insitu_url": "INSITU300",
        "other_views_url": "OTHER300"
    }   
    def connect(self):
        """Establish connection to FileMaker"""
        try:
            self.session = requests.Session()
            self.session.verify = False
            self.session.auth = HTTPBasicAuth(self.username, self.password)
            
            # Get authentication token
            auth_url = f'https://{self.server}/fmi/data/vLatest/databases/{self.database}/sessions'
            auth_response = self.session.post(auth_url, json={}, timeout=30)
            
            if auth_response.status_code == 200:
                self.token = auth_response.json().get('response', {}).get('token')
                self.token_timestamp = time.time() 
                
                # Switch to Bearer token authentication
                self.session.auth = None
                self.session.headers.update({
                    'Authorization': f'Bearer {self.token}',
                    'Content-Type': 'application/json'
                })
                return True
            else:
                print(f"FileMaker authentication failed: {auth_response.status_code}")
                return False
                
        except Exception as e:
            print(f"FileMaker connection error: {e}")
            return False
    
    def disconnect(self):
        """Close FileMaker session"""
        if self.token and self.session:
            try:
                self.session.delete(f'https://{self.server}/fmi/data/vLatest/databases/{self.database}/sessions/{self.token}')
            except:
                pass
            self.token = None
            self.session = None
    
    def is_token_expired(self):
        """
        FileMaker token ~15 min valid hota hai
        Hum 14 min baad hi expire maan lete hain (safe buffer)
        """
        if not self.token_timestamp:
            return True
        return (time.time() - self.token_timestamp) > 840  # 14 minutes
    
    def ensure_connected(self):
        """
        Ensure FileMaker session is alive
        Reconnect if token missing or expired
        """
        if not self.session or not self.token or self.is_token_expired():
            print("[FILEMAKER] Token expired or missing, reconnecting...")
            return self.connect()
        return True


    def update_artwork(self, record_id, field_updates):
        """🔄 Mettre à jour les champs d'images d'une œuvre"""
        update_url = f"https://{self.server}/fmi/data/vLatest/databases/{self.database}/layouts/{self.layout}/records/{record_id}"
        
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        update_data = {
            "fieldData": field_updates
        }
        
        try:
            response = self.session.patch(update_url, json=update_data, headers=headers, timeout=30)
            print("response for update artwork")
            print(response.text)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Erreur update: {e}")
            return False
        
    def create_artwork(self, artwork_id, target_field, final_filename):
        """🔄 Mettre à jour les champs d'images d'une œuvre"""
        update_url = f"https://{self.server}/fmi/data/vLatest/databases/{self.database}/layouts/{self.layout}/records"
        
        headers = {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }
        
        update_data = {
            "fieldData": {target_field: final_filename}
        }
        print(update_data)
        print(artwork_id)
        fm_id = None
        try:
            response = self.session.post(update_url, json=update_data, headers=headers, timeout=30)
            print(response.text)
            is_success = response.status_code == 200
            fm_id = response.json().get('response', {}).get('recordId')
        except Exception as e:
            print(f"❌ Erreur update: {e}")
            is_success = False
        
        if fm_id:
            update_artwork = self.update_artwork(fm_id, {"IdName": artwork_id})
            print(update_artwork)
        return is_success
    
    def find_artwork_by_id(self, artwork_id):
        """Find artwork by IdName in FileMaker"""
        print(f"[FILEMAKER DEBUG] Searching for artwork: {artwork_id}")
        if not self.session or not self.token:
            print(f"[FILEMAKER DEBUG] No session, connecting...")
            if not self.connect():
                print(f"[FILEMAKER DEBUG] Connection failed!")
                return None
        
        try:
            search_url = f'https://{self.server}/fmi/data/vLatest/databases/{self.database}/layouts/{self.layout}/_find'
            
            search_data = {
                'query': [{
                    'IdName': artwork_id
                }]
            }
            
            response = self.session.post(search_url, json=search_data, timeout=30)
            print(f"[FILEMAKER DEBUG] Response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json().get('response', {})
                records = data.get('data', [])
                print(f"[FILEMAKER DEBUG] Found {len(records)} records")
                
                if records:
                    print(f"[FILEMAKER DEBUG] Artwork found: {records[0].get('fieldData', {}).get('IdName')}")
                    return records[0]  # Return first matching record
            elif response.status_code == 404:
                print(f"[FILEMAKER DEBUG] Artwork not found (404)")
                return None  # No artwork found
            else:
                print(f"FileMaker search error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Error searching FileMaker: {e}")
            return None
        
        return None

    def get_field_value(self, artwork_id, field_name):
        """Get the current value of a specific field for an artwork"""
        if not self.ensure_connected():
            return None
        record = self.find_artwork_by_id(artwork_id)
        if not record:
            return None
        return record.get('fieldData', {}).get(field_name) or None

    def update_mainfm_test_field(self, artwork_id, image_url):
        """Update MAINFMTest field for an artwork"""
        # if not self.session or not self.token:
        #     if not self.connect():
        #         return False
        if not self.ensure_connected():
            print("[FILEMAKER DEBUG] Connection failed!")
            return None
        
        try:
            # First find the artwork to get its record ID
            artwork = self.find_artwork_by_id(artwork_id)
            if not artwork:
                print(f"Artwork {artwork_id} not found in FileMaker")
                return False
            
            record_id = artwork.get('recordId')
            if not record_id:
                print(f"No recordId found for artwork {artwork_id}")
                return False
            
            # Update the MAINFMTest field
            update_url = f'https://{self.server}/fmi/data/vLatest/databases/{self.database}/layouts/{self.layout}/records/{record_id}'
            
            update_data = {
                'fieldData': {
                    'MAINFMTest': image_url
                }
            }
            
            response = self.session.patch(update_url, json=update_data, timeout=30)
            
            if response.status_code == 200:
                print(f"Successfully updated MAINFMTest for {artwork_id}: {image_url}")
                return True
            else:
                print(f"FileMaker update error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error updating FileMaker: {e}")
            return False
        
        return False
    
    def get_field_name_for_classification(self, classification):
        """Map photo classification to FileMaker field name"""
        classification_map = {
            'MAIN': 'MAINFM',
            'DET': 'DET300', 
            'OTHER': 'OTHER300',
            'BACK': 'BACK300',
            'INSITU': 'INSITU300',
            'FRONT': 'FRONT300',
            'FRAME': 'FRAME300',
            'LEFT': 'LEFT300',
            'FRONTRIGHT': 'FRONTRIGHT300',
            'PERS': 'PERS300'
        }
        return classification_map.get(classification.upper(), 'OTHER300')
    
    def update_specialized_field(self, artwork_id, field_name, image_url):
        """Update a specialized image field (MAIN300, DET300, etc.) for an artwork"""
        # if not self.session or not self.token:
        #     if not self.connect():
        #         return False
        if not self.ensure_connected():
            return False
        
        try:
            # First find the artwork to get its record ID
            artwork = self.find_artwork_by_id(artwork_id)
            if not artwork:
                print(f"Artwork {artwork_id} not found in FileMaker")
                return False
            
            record_id = artwork.get('recordId')
            if not record_id:
                print(f"No recordId found for artwork {artwork_id}")
                return False
            
            # Update the specialized field
            update_url = f'https://{self.server}/fmi/data/vLatest/databases/{self.database}/layouts/{self.layout}/records/{record_id}'
            
            update_data = {
                'fieldData': {
                    field_name: image_url
                }
            }
            
            response = self.session.patch(update_url, json=update_data, timeout=30)
            
            if response.status_code == 200:
                print(f"Successfully updated {field_name} for {artwork_id}: {image_url}")
                return True
            else:
                print(f"FileMaker update error for {field_name}: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Response text: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error updating {field_name} in FileMaker: {e}")
            return False
        
        return False
    
    def update_multiple_fields(self, artwork_id, field_updates):
        """Update multiple fields for an artwork (auto mapping from OperaCRM → FileMaker fields)"""
        # if not self.session or not self.token:
        #     if not self.connect():
        #         return False
        if not self.ensure_connected():
            return False
        
        try:
            # First find the artwork to get its record ID
            artwork = self.find_artwork_by_id(artwork_id)
            if not artwork:
                print(f"Artwork {artwork_id} not found in FileMaker")
                return False
            print("\n📋 AVAILABLE FIELDS FROM FILEMAKER:")
            print(list(artwork.get('fieldData', {}).keys()))
            print("------------------------------------------------\n")
            record_id = artwork.get('recordId')
            if not record_id:
                print(f"No recordId found for artwork {artwork_id}")
                return False
            
            mapped_fields = {}
            for odoo_field, value in field_updates.items():
                if not value:
                    continue  # skip empty URLs
                fm_field = self.FIELD_MAPPING.get(odoo_field, odoo_field)
                mapped_fields[fm_field] = value
                print(f"🔗 Mapping: {odoo_field} → {fm_field}")

            if not mapped_fields:
                print("⚠️ No valid fields to update after mapping")
                return False
            
            # Update multiple fields
            update_url = f'https://{self.server}/fmi/data/vLatest/databases/{self.database}/layouts/{self.layout}/records/{record_id}'
            
            update_data = {
                'fieldData': mapped_fields
            }
            
            response = self.session.patch(update_url, json=update_data, timeout=30)
            print(f"FileMaker update response: {response.text}")
            if response.status_code == 200:
                # updated_fields = ', '.join(field_updates.keys())
                # print(f"Successfully updated fields [{updated_fields}] for {artwork_id}")
                print(f"✅ Successfully updated fields for {artwork_id}: {list(mapped_fields.keys())}")
                return True
            else:
                print(f"FileMaker update error for multiple fields: {response.status_code}")
                try:
                    error_data = response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Response text: {response.text}")
                return False
                
        except Exception as e:
            print(f"Error updating multiple fields in FileMaker: {e}")
            return False
        
        return False
    
    def get_artwork_image_fields(self, artwork_id):
        """Get all image-related fields for an artwork"""
        artwork = self.find_artwork_by_id(artwork_id)
        if not artwork:
            return None
        
        field_data = artwork.get('fieldData', {})
        
        image_fields = {
            # 'MAIN300': field_data.get('MAIN300', ''),
            # 'BACK300': field_data.get('BACK300', ''),
            # 'OTHER300': field_data.get('OTHER300', ''),
            # 'DET300': field_data.get('DET300', ''),
            # 'MAINFM': field_data.get('MAINFM', ''),
            # 'MAINFMTest': field_data.get('MAINFMTest', ''),
            # 'CertificateFMUrl': field_data.get('CertificateFMUrl', ''),
            # 'CertificateWording': field_data.get('CertificateWording', '')
                'MAINFM': field_data.get('MAINFM', ''),
                'MAIN300': field_data.get('MAIN300', ''),
                'DET300': field_data.get('DET300', ''),
                'BACK300': field_data.get('BACK300', ''),
                'FRONT300': field_data.get('FRONT300', ''),
                'LEFT300': field_data.get('LEFT300', ''),
                'FRONTRIGHT300': field_data.get('FRONTRIGHT300', ''),
                'FRAME300': field_data.get('FRAME300', ''),
                'INSITU300': field_data.get('INSITU300', ''),
                'OTHER300': field_data.get('OTHER300', ''),
                'PERS300': field_data.get('PERS300', ''),
                'MAINFMTest': field_data.get('MAINFMTest', ''),
                'CertificateFMUrl': field_data.get('CertificateFMUrl', ''),
                'CertificateWording': field_data.get('CertificateWording', '')
        }
        
        # Parse multi-line URL fields
        for field in ['MAIN300', 'BACK300', 'OTHER300', 'DET300']:
            if image_fields[field]:
                image_fields[field] = [url.strip() for url in image_fields[field].split('\n') if url.strip()]
            else:
                image_fields[field] = []
        
        return image_fields

def extract_artwork_id_from_filename(filename):
    """Extract artwork ID from filename (e.g., PICAPA-666, BUFFBE-123)"""
    import re
    
    # Look for pattern like ART-12345 or [ART-12345]
    patterns = [
        r'\[([A-Z]+-\d+)\]',  # [PICAPA-666]
        r'([A-Z]+-\d+)',      # PICAPA-666
    ]
    
    for pattern in patterns:
        match = re.search(pattern, filename)
        if match:
            return match.group(1)
    
    return None

# Global FileMaker service instance
filemaker_service = FileMakerService()
