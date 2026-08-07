#!/usr/bin/env python3
"""
Script de nettoyage pour déplacer tous les fichiers .eps vers un dossier de quarantaine
et empêcher leur traitement dans l'application photo-validator.
"""

import os
import shutil
from datetime import datetime
import sqlite3

def main():
    # Configuration des chemins
    photos_base_dir = '/home/projet/photo-validator/photos'
    quarantine_dir = os.path.join(photos_base_dir, 'quarantine_eps')
    
    # Créer le dossier de quarantaine
    os.makedirs(quarantine_dir, exist_ok=True)
    
    # Chercher tous les fichiers .eps dans le répertoire photos
    eps_files = []
    for root, dirs, files in os.walk(photos_base_dir):
        # Ignorer le dossier de quarantaine lui-même
        if 'quarantine_eps' in root:
            continue
            
        for file in files:
            if file.lower().endswith('.eps'):
                eps_files.append(os.path.join(root, file))
    
    print(f"Trouvé {len(eps_files)} fichiers .eps à déplacer")
    
    if len(eps_files) == 0:
        print("Aucun fichier .eps trouvé. Nettoyage terminé.")
        return
    
    # Créer un fichier de log
    log_file = os.path.join(quarantine_dir, f'cleanup_log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.txt')
    
    moved_files = []
    failed_files = []
    
    with open(log_file, 'w') as log:
        log.write(f"Nettoyage des fichiers .eps - {datetime.now()}\n")
        log.write("="*50 + "\n\n")
        
        for eps_file in eps_files:
            try:
                # Calculer le nom de fichier de destination
                filename = os.path.basename(eps_file)
                relative_path = os.path.relpath(eps_file, photos_base_dir)
                
                # Créer la structure de dossiers dans la quarantaine si nécessaire
                dest_dir = os.path.join(quarantine_dir, os.path.dirname(relative_path))
                os.makedirs(dest_dir, exist_ok=True)
                
                dest_file = os.path.join(dest_dir, filename)
                
                # Gérer les conflits de noms
                counter = 1
                base_name, ext = os.path.splitext(dest_file)
                while os.path.exists(dest_file):
                    dest_file = f"{base_name}_{counter}{ext}"
                    counter += 1
                
                # Déplacer le fichier
                shutil.move(eps_file, dest_file)
                
                moved_files.append((eps_file, dest_file))
                log.write(f"DÉPLACÉ: {relative_path} -> {os.path.relpath(dest_file, quarantine_dir)}\n")
                print(f"✓ Déplacé: {filename}")
                
            except Exception as e:
                failed_files.append((eps_file, str(e)))
                log.write(f"ÉCHEC: {eps_file} - Erreur: {e}\n")
                print(f"✗ Échec: {filename} - {e}")
        
        log.write(f"\n" + "="*50 + "\n")
        log.write(f"RÉSUMÉ:\n")
        log.write(f"Fichiers déplacés: {len(moved_files)}\n")
        log.write(f"Échecs: {len(failed_files)}\n")
    
    # Nettoyer les entrées de base de données si elles existent
    cleanup_database_entries([os.path.basename(f[0]) for f in moved_files])
    
    print(f"\nNettoyage terminé:")
    print(f"- {len(moved_files)} fichiers déplacés vers {quarantine_dir}")
    print(f"- {len(failed_files)} échecs")
    print(f"- Log détaillé: {log_file}")
    
    if len(moved_files) > 0:
        print(f"\nLes fichiers .eps ont été déplacés vers {quarantine_dir}")
        print("Ils peuvent être supprimés définitivement ou convertis vers un format supporté.")

def cleanup_database_entries(filenames):
    """Nettoyer les entrées de base de données pour les fichiers déplacés"""
    try:
        db_path = '/home/projet/photo-validator/frontend/photo_validator.db'
        if not os.path.exists(db_path):
            print("Base de données non trouvée, pas de nettoyage nécessaire")
            return
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Vérifier si la table photo_validations existe
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='photo_validations'")
        if not cursor.fetchone():
            print("Table photo_validations non trouvée")
            conn.close()
            return
        
        cleaned_count = 0
        for filename in filenames:
            cursor.execute('DELETE FROM photo_validations WHERE photo_id = ? OR photo_filename = ?', 
                         (filename, filename))
            if cursor.rowcount > 0:
                cleaned_count += 1
        
        conn.commit()
        conn.close()
        
        if cleaned_count > 0:
            print(f"✓ Nettoyé {cleaned_count} entrées de la base de données")
        
    except Exception as e:
        print(f"Erreur lors du nettoyage de la base de données: {e}")

if __name__ == '__main__':
    print("=== Script de nettoyage des fichiers .eps ===")
    print("Ce script va déplacer tous les fichiers .eps vers un dossier de quarantaine.")
    
    response = input("\nContinuer? (y/N): ").strip().lower()
    if response in ['y', 'yes', 'oui']:
        main()
    else:
        print("Nettoyage annulé.")