#!/usr/bin/env python3
import sys
sys.path.append('/app')

from filemaker_service import FileMakerService

# Create FileMaker service instance
fm = FileMakerService()

# Temporarily change layout to CRMRecordUsers
fm.layout = 'CRMRecordUsers'

print("Connecting to FileMaker...")
if fm.connect():
    print("✅ Connected successfully\n")
    
    # Get records
    try:
        url = f'https://{fm.server}/fmi/data/vLatest/databases/{fm.database}/layouts/{fm.layout}/records?_limit=15'
        response = fm.session.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json().get('response', {}).get('data', [])
            print(f"Found {len(data)} users in CRMRecordUsers\n")
            
            # Group by DasStatus values
            das_values = {}
            
            for record in data:
                field_data = record.get('fieldData', {})
                das_status = field_data.get('DasStatus', '')
                email = field_data.get('Email', 'N/A')
                email_login = field_data.get('EmailLoginCrm', 'N/A')
                total_name = field_data.get('TotalName', 'N/A')
                actif = field_data.get('ActifCrm', 'N/A')
                category = field_data.get('CategoryCRM', 'N/A')
                
                # Add to grouping
                if das_status not in das_values:
                    das_values[das_status] = []
                
                das_values[das_status].append({
                    'name': total_name,
                    'email': email,
                    'email_login': email_login,
                    'actif': actif,
                    'category': category
                })
            
            # Display grouped by DasStatus
            print("="*80)
            print("VALEURS DU CHAMP 'DasStatus':")
            print("="*80)
            
            for das_value, users in das_values.items():
                print(f"\n📌 DasStatus = '{das_value}' ({len(users)} users)")
                print("-"*80)
                for user in users[:3]:  # Show first 3 of each group
                    print(f"  • {user['name']}")
                    print(f"    Email: {user['email']}")
                    print(f"    Login: {user['email_login']}")
                    print(f"    ActifCrm: {user['actif']}")
                    print(f"    Category: {user['category']}")
                    print()
                if len(users) > 3:
                    print(f"  ... et {len(users) - 3} autres utilisateurs")
        else:
            print(f"❌ Error: {response.status_code}")
            print(response.text[:500])
    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    fm.disconnect()
else:
    print("❌ Connection failed")

