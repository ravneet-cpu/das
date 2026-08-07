#!/usr/bin/env python3
import sys
sys.path.append('/app')

from filemaker_service import FileMakerService

fm = FileMakerService()
fm.layout = 'CRMRecordUsers'

if fm.connect():
    try:
        url = f'https://{fm.server}/fmi/data/vLatest/databases/{fm.database}/layouts/{fm.layout}/records?_limit=100'
        response = fm.session.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json().get('response', {}).get('data', [])
            
            print("="*100)
            print("UTILISATEURS AVEC ACCÈS DAS (DasStatus non-vide)")
            print("="*100)
            
            das_users = []
            
            for record in data:
                field_data = record.get('fieldData', {})
                das = field_data.get('DasStatus', '').strip()
                
                if das:  # Only users with DasStatus set
                    das_users.append({
                        'das_status': das,
                        'name': field_data.get('TotalName', 'N/A'),
                        'first_name': field_data.get('FirstName', ''),
                        'last_name': field_data.get('LastName', ''),
                        'email': field_data.get('Email', 'N/A'),
                        'email_login': field_data.get('EmailLoginCrm', 'N/A'),
                        'actif_crm': field_data.get('ActifCrm', 'N/A'),
                        'category': field_data.get('CategoryCRM', 'N/A'),
                        'password_hash': 'SET' if field_data.get('PasswordHash') else 'EMPTY',
                        'code_gallery': field_data.get('CodeGallery', 'N/A')
                    })
            
            # Sort by DasStatus (Admin first)
            das_users.sort(key=lambda x: (x['das_status'] != 'Admin', x['name']))
            
            print(f"\n📊 Total: {len(das_users)} utilisateurs avec accès DAS\n")
            
            for i, user in enumerate(das_users, 1):
                print(f"{i}. {user['name']:20} ({user['das_status']})")
                print(f"   Email Login:   {user['email_login']}")
                print(f"   Email:         {user['email']}")
                print(f"   Nom/Prénom:    {user['last_name']} {user['first_name']}")
                print(f"   ActifCrm:      {user['actif_crm']}")
                print(f"   Category:      {user['category']}")
                print(f"   PasswordHash:  {user['password_hash']}")
                print(f"   CodeGallery:   {user['code_gallery']}")
                print()
            
            print("="*100)
            print("RÉSUMÉ:")
            print("="*100)
            admin_count = len([u for u in das_users if 'Admin' in u['das_status']])
            user_count = len([u for u in das_users if u['das_status'] == 'User'])
            print(f"  • Admins DAS:  {admin_count}")
            print(f"  • Users DAS:   {user_count}")
            print(f"  • Total accès: {len(das_users)}")
            print(f"  • Sans accès:  {len(data) - len(das_users)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    fm.disconnect()

