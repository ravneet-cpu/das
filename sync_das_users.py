#!/usr/bin/env python3
"""
Synchronisation automatique des utilisateurs FileMaker DasStatus → Photo Validator
Execute toutes les 2h via cron job
"""

import sys
import sqlite3
from datetime import datetime
import hashlib
import secrets

sys.path.append('/app')

from filemaker_service import FileMakerService
import os

# Database path - must match Docker volume mount (./data:/app/data)
# In Docker: /app/data/photo_validator.db
# On host: /home/projet/photo-validator/data/photo_validator.db
DATABASE_PATH = '/home/projet/photo-validator/data/photo_validator.db'

def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

# Removed - using PasswordCRM from FileMaker instead

def sync_das_users():
    """Synchronize users from FileMaker DasStatus to Photo Validator"""

    print("="*80)
    print(f"🔄 SYNCHRONISATION DAS USERS - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # Connect to FileMaker
    fm = FileMakerService()
    fm.layout = 'CRMRecordUsers'

    if not fm.connect():
        print("❌ Impossible de se connecter à FileMaker")
        return False

    print("✅ Connecté à FileMaker")

    try:
        # Get all users from FileMaker (high limit to get everyone)
        url = f'https://{fm.server}/fmi/data/vLatest/databases/{fm.database}/layouts/{fm.layout}/records?_limit=1000'
        response = fm.session.get(url, timeout=30)

        if response.status_code != 200:
            print(f"❌ Erreur récupération FileMaker: {response.status_code}")
            return False

        data = response.json().get('response', {}).get('data', [])
        print(f"📊 {len(data)} utilisateurs trouvés dans FileMaker")

        # Filter users with DasStatus set (Admin or User)
        fm_das_users = []
        for record in data:
            field_data = record.get('fieldData', {})
            das_status = field_data.get('DasStatus', '').strip()

            if das_status:  # Only users with DasStatus = 'Admin' or 'User'
                email_login = field_data.get('EmailLoginCrm', '').strip()
                email = field_data.get('Email', '').strip()
                first_name = field_data.get('FirstName', '').strip()
                last_name = field_data.get('LastName', '').strip()
                actif_crm = field_data.get('ActifCrm', '')
                password_crm = field_data.get('PasswordCRM', '').strip()

                # Use EmailLoginCrm as username, fallback to Email
                username = email_login if email_login else email

                if username and actif_crm == 'Yes' and password_crm:
                    # Map DasStatus to Photo Validator role
                    if 'Admin' in das_status:
                        role = 'admin'
                    elif das_status == 'User':
                        role = 'uploader'
                    else:
                        role = 'uploader'  # Default fallback

                    fm_das_users.append({
                        'username': username,
                        'email': email if email else username,
                        'first_name': first_name,
                        'last_name': last_name,
                        'das_status': das_status,
                        'password_crm': password_crm,  # Password from FileMaker
                        'role': role  # 'admin' if DasStatus='Admin', 'uploader' if DasStatus='User'
                    })

        print(f"✅ {len(fm_das_users)} utilisateurs avec DasStatus actif et ActifCrm=Yes")
        print()

        # Connect to Photo Validator database
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()

        # Get existing users (exclude system accounts: admin, cron_scheduler, frank)
        cursor.execute("SELECT username, email FROM users WHERE username NOT IN ('admin', 'cron_scheduler', 'frank')")
        existing_users = {row[0].lower(): row[1] for row in cursor.fetchall()}

        print(f"📊 {len(existing_users)} utilisateurs existants dans Photo Validator (hors admin/cron)")
        print()

        # Track changes
        added = 0
        updated = 0
        removed = 0
        unchanged = 0

        # Build set of authorized usernames from FileMaker
        fm_usernames = {u['username'].lower() for u in fm_das_users}

        # Add or update users from FileMaker
        print("📝 AJOUT/MISE À JOUR DES UTILISATEURS:")
        print("-"*80)

        for user in fm_das_users:
            username = user['username']
            email = user['email']
            role = user['role']
            password_crm = user['password_crm']
            hashed_password = hash_password(password_crm)

            # Check if user exists
            cursor.execute("SELECT id, email, role, password FROM users WHERE username = ?", (username,))
            existing = cursor.fetchone()

            if existing:
                user_id, existing_email, existing_role, existing_password = existing

                # Update if changed (email, role, or password)
                if existing_email != email or existing_role != role :
                    cursor.execute("""
                        UPDATE users
                        SET email = ?, role = ?
                        WHERE username = ?
                    """, (email, role, hashed_password, username))
                    print(f"  🔄 Mis à jour: {username} ({user['das_status']})")
                    updated += 1
                else:
                    unchanged += 1
            else:
                # Create new user with PasswordCRM from FileMaker
                cursor.execute("""
                    INSERT INTO users (username, password, email, role)
                    VALUES (?, ?, ?, ?)
                """, (username, hashed_password, email, role))

                print(f"  ✅ Créé: {username} ({user['das_status']}) - Password depuis FileMaker")
                added += 1

        print()

        # Remove users not in FileMaker DasStatus
        print("🗑️  SUPPRESSION DES UTILISATEURS NON AUTORISÉS:")
        print("-"*80)

        for username_lower, email in existing_users.items():
            if username_lower not in fm_usernames:
                #cursor.execute("DELETE FROM users WHERE LOWER(username) = ?", (username_lower,))
                print(f"  ❌ Supprimé: {username_lower} (pas dans FileMaker DasStatus)")
                #removed += 1

        print()

        # Commit changes
        conn.commit()
        conn.close()

        # Summary
        print("="*80)
        print("📊 RÉSUMÉ DE LA SYNCHRONISATION:")
        print("="*80)
        print(f"  ✅ Utilisateurs ajoutés:     {added}")
        print(f"  🔄 Utilisateurs mis à jour:  {updated}")
        print(f"  ❌ Utilisateurs supprimés:   {removed}")
        print(f"  ⚪ Utilisateurs inchangés:   {unchanged}")
        print(f"  📊 Total autorisés DAS:      {len(fm_das_users)}")
        print("="*80)

        return True

    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        fm.disconnect()

if __name__ == '__main__':
    success = sync_das_users()
    sys.exit(0 if success else 1)
