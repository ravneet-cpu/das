
import requests
import sys
import os

# Configuration
API_URL = "http://127.0.0.1:5001/api/admin/process-scheduled-uploads"
CRON_TOKEN_FILE = "/home/projet/photo-validator/.cron_token"

def get_cron_token():
    """Retrieve permanent token for cron scheduler"""
    try:
        if os.path.exists(CRON_TOKEN_FILE):
            with open(CRON_TOKEN_FILE, 'r') as f:
                token = f.read().strip()
                if token:
                    return token
        print(f"[CRON] ❌ Token file not found: {CRON_TOKEN_FILE}")
        return None
    except Exception as e:
         print(f"[CRON] ❌ Token read error: {e}")
        return None

if __name__ == "__main__":
    try:
        # Récupérer le token cron
        token = get_cron_token()
        if not token:
            print("[CRON] ❌ Unable to retrieve cron token")
            sys.exit(1)

        # Appeler l'API pour traiter les uploads programmés
        response = requests.post(API_URL, headers={
            'Authorization': f'Bearer {token}'
        }, timeout=30)

        if response.status_code == 200:
            data = response.json()
            processed_count = data.get('processed_count', 0)

            print(f"[CRON] {processed_count} scheduled uploads processed")

            if processed_count > 0:
                print(f"[CRON] ✅ {processed_count} photos publiées dans FileMaker")
            else:
                 print("[CRON] 📅 No scheduled uploads to process at this time")

        elif response.status_code == 403:
            print("[CRON] ❌ Cron token expired")
            sys.exit(1)
        else:
            print(f"[CRON] ❌ Erreur API: {response.status_code}")
            print(response.text)
            sys.exit(1)

    except Exception as e:
        print(f"[CRON] ❌ Error processing scheduled uploads: {e}")
        sys.exit(1)
