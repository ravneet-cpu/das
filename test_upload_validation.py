#!/usr/bin/env python3
"""
Script de test pour vérifier que les validations d'extensions de fichiers fonctionnent correctement.
"""

import tempfile
import os
import requests
import json

def test_file_extension_validation():
    """Test que les extensions non autorisées sont rejetées"""
    
    # Configuration
    base_url = "http://localhost:5000"  # Ajuster selon votre configuration
    
    # Données de connexion (vous devrez ajuster selon votre système)
    login_data = {
        "username": "admin",  # Ou un utilisateur avec les droits d'upload
        "password": "adminpass"
    }
    
    print("=== Test de validation des extensions de fichiers ===")
    
    # 1. Se connecter pour obtenir un token
    try:
        print("1. Connexion...")
        response = requests.post(f"{base_url}/api/auth/login", json=login_data)
        if not response.ok:
            print(f"✗ Échec de la connexion: {response.status_code}")
            return False
        
        token = response.json().get('token')
        if not token:
            print("✗ Token non reçu")
            return False
        
        print("✓ Connexion réussie")
        headers = {'Authorization': f'Bearer {token}'}
        
    except Exception as e:
        print(f"✗ Erreur de connexion: {e}")
        return False
    
    # 2. Test avec un fichier .eps (doit être rejeté)
    print("\n2. Test avec fichier .eps (doit être rejeté)...")
    try:
        # Créer un fichier temporaire .eps
        with tempfile.NamedTemporaryFile(suffix='.eps', delete=False) as tmp_eps:
            tmp_eps.write(b'%!PS-Adobe-3.0 EPSF-3.0\n%%BoundingBox: 0 0 100 100\nnewpath\n')
            eps_path = tmp_eps.name
        
        with open(eps_path, 'rb') as f:
            files = {'file': ('test.eps', f, 'application/postscript')}
            response = requests.post(f"{base_url}/api/photos/upload", 
                                   files=files, headers=headers)
        
        os.unlink(eps_path)  # Nettoyer le fichier temporaire
        
        if response.status_code == 400:
            result = response.json()
            if 'Type de fichier non autorisé' in result.get('error', ''):
                print("✓ Fichier .eps correctement rejeté")
            else:
                print(f"✗ Fichier .eps rejeté mais avec un message différent: {result.get('error')}")
                return False
        else:
            print(f"✗ Fichier .eps accepté (erreur!) - Status: {response.status_code}")
            return False
    
    except Exception as e:
        print(f"✗ Erreur lors du test .eps: {e}")
        return False
    
    # 3. Test avec un fichier .jpg (doit être accepté)
    print("\n3. Test avec fichier .jpg (doit être accepté)...")
    try:
        # Créer un fichier temporaire .jpg minimal
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_jpg:
            # En-tête JPEG minimal (pour que PIL ne se plaigne pas)
            jpeg_header = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
            tmp_jpg.write(jpeg_header)
            jpg_path = tmp_jpg.name
        
        with open(jpg_path, 'rb') as f:
            files = {'file': ('test.jpg', f, 'image/jpeg')}
            response = requests.post(f"{base_url}/api/photos/upload", 
                                   files=files, headers=headers)
        
        os.unlink(jpg_path)  # Nettoyer le fichier temporaire
        
        if response.status_code == 200:
            print("✓ Fichier .jpg correctement accepté")
        else:
            result = response.json()
            print(f"✗ Fichier .jpg rejeté - Status: {response.status_code}, Error: {result.get('error')}")
            return False
    
    except Exception as e:
        print(f"✗ Erreur lors du test .jpg: {e}")
        return False
    
    print("\n=== Tous les tests passés avec succès! ===")
    return True

def check_allowed_extensions():
    """Afficher les extensions autorisées configurées"""
    print("\n=== Extensions autorisées dans le code ===")
    
    # Lire les extensions depuis auth_routes.py
    try:
        with open('/home/projet/photo-validator/frontend/auth_routes.py', 'r') as f:
            content = f.read()
        
        # Chercher les définitions d'extensions
        import re
        
        # Chercher les lignes contenant allowed_extensions
        allowed_pattern = r"allowed_extensions\s*=\s*\{([^}]+)\}"
        matches = re.findall(allowed_pattern, content)
        
        if matches:
            for i, match in enumerate(matches, 1):
                extensions = [ext.strip().strip("'\"") for ext in match.split(',')]
                print(f"Configuration {i}: {', '.join(extensions)}")
        
        # Chercher les lignes contenant image_extensions
        image_pattern = r"image_extensions\s*=\s*\{([^}]+)\}"
        matches = re.findall(image_pattern, content)
        
        if matches:
            for i, match in enumerate(matches, 1):
                extensions = [ext.strip().strip("'\"") for ext in match.split(',')]
                print(f"Image extensions {i}: {', '.join(extensions)}")
                
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier: {e}")

if __name__ == '__main__':
    check_allowed_extensions()
    
    print("\nVoulez-vous lancer les tests de validation d'upload?")
    print("(Assurez-vous que le serveur tourne sur localhost:5000)")
    response = input("Continuer? (y/N): ").strip().lower()
    
    if response in ['y', 'yes', 'oui']:
        test_file_extension_validation()
    else:
        print("Tests annulés.")