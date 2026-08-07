#!/usr/bin/env python3
import sys
sys.path.append('/app')

from filemaker_service import FileMakerService

fm = FileMakerService()
fm.layout = 'CRMRecordUsers'

if fm.connect():
    try:
        # Get ALL records (increase limit)
        url = f'https://{fm.server}/fmi/data/vLatest/databases/{fm.database}/layouts/{fm.layout}/records?_limit=100'
        response = fm.session.get(url, timeout=30)
        
        if response.status_code == 200:
            data = response.json().get('response', {}).get('data', [])
            print(f"📊 Total users in FileMaker CRMRecordUsers: {len(data)}\n")
            
            # Count DasStatus values
            das_count = {}
            das_examples = {}
            
            for record in data:
                field_data = record.get('fieldData', {})
                das = field_data.get('DasStatus', '')
                email = field_data.get('Email', '')
                name = field_data.get('TotalName', '')
                actif = field_data.get('ActifCrm', '')
                
                # Count
                das_count[das] = das_count.get(das, 0) + 1
                
                # Store examples
                if das not in das_examples:
                    das_examples[das] = []
                if len(das_examples[das]) < 5:
                    das_examples[das].append({
                        'name': name,
                        'email': email,
                        'actif': actif
                    })
            
            # Display statistics
            print("="*80)
            print("STATISTIQUES DasStatus:")
            print("="*80)
            
            for das_value in sorted(das_count.keys(), key=lambda x: das_count[x], reverse=True):
                count = das_count[das_value]
                display_value = f"'{das_value}'" if das_value else "(vide)"
                print(f"\n📌 DasStatus = {display_value}: {count} utilisateurs")
                print("-"*80)
                
                for user in das_examples[das_value][:3]:
                    print(f"  • {user['name']:20} | {user['email']:35} | ActifCrm: {user['actif']}")
            
            # Show unique values
            print("\n" + "="*80)
            print("VALEURS UNIQUES du champ DasStatus:")
            print("="*80)
            unique_values = [v for v in das_count.keys() if v]
            if unique_values:
                for val in unique_values:
                    print(f"  - '{val}' (longueur: {len(val)} caractères)")
            else:
                print("  ⚠️ Aucune valeur non-vide trouvée")
            
            print(f"\n  Total valeurs vides: {das_count.get('', 0)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    fm.disconnect()

