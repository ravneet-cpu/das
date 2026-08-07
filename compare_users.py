import sqlite3
import sys
sys.path.append('/app')

conn = sqlite3.connect('/app/data/photo_validator.db')
cursor = conn.cursor()

cursor.execute('SELECT username, email, role FROM users WHERE username != "admin" ORDER BY username')
photo_users = cursor.fetchall()
conn.close()

print("="*100)
print("COMPARAISON: FileMaker DasStatus vs Photo Validator")
print("="*100)

# FileMaker users with DAS access
fm_das = {
    'aurelie@operagallery.com': 'Admin',
    'genevad@operagallery.com': 'Admin',
    'stephane@operagallery.com': 'Admin',
    'londona@operagallery.com': 'User',
    'gregory@operagallery.com': 'User',
    'hakam.pro@operagallery.com': 'User',
    'lauren@operagallery.com': 'User',
    'hkgadmin@operagallery.com': 'User',
    'nancy@operagallery.com': 'User'
}

print(f"\nFileMaker DasStatus actif: {len(fm_das)} users")
print(f"Photo Validator DB: {len(photo_users)} users")
print()

# Find matches
matches = 0
not_in_fm = 0
fm_emails_lower = [e.lower() for e in fm_das.keys()]

print("UTILISATEURS DANS PHOTO VALIDATOR:")
print("-"*100)

for username, email, role in photo_users:
    email_check = (email or '').lower()
    username_check = (username or '').lower()
    
    in_fm = email_check in fm_emails_lower or username_check in fm_emails_lower
    
    if in_fm:
        print(f"✅ {username:30} | {email:35} | {role}")
        matches += 1
    else:
        print(f"❌ {username:30} | {email:35} | {role}")
        not_in_fm += 1

print()
print("="*100)
print(f"✅ Correspondances: {matches}")
print(f"❌ Non autorisés selon FM: {not_in_fm}")
print(f"📊 Taux de correspondance: {(matches/len(photo_users)*100):.1f}%")

