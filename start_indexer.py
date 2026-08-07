#!/usr/bin/env python3
"""
Script de démarrage de l'indexeur d'artistes - évite les imports circulaires
"""

import time
import sys
import os

# Ajouter le répertoire actuel au path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    """Démarre l'indexeur après un délai pour éviter les imports circulaires"""
    
    print("[INDEXER-STARTUP] 🕐 Waiting 10 seconds for app to fully start...")
    time.sleep(10)  # Attendre que l'app soit complètement démarrée
    
    try:
        print("[INDEXER-STARTUP] 🎨 Starting artist indexing...")
        from artist_indexer import start_artist_indexing
        start_artist_indexing()
        print("[INDEXER-STARTUP] ✅ Artist indexing started successfully")
        
        # Garder le script vivant
        while True:
            time.sleep(60)  # Vérifier toutes les minutes
            
    except KeyboardInterrupt:
        print("[INDEXER-STARTUP] 🛑 Indexer stopped by user")
    except Exception as e:
        print(f"[INDEXER-STARTUP] ❌ Error: {e}")
        # Retry après 30 secondes
        time.sleep(30)
        main()

if __name__ == "__main__":
    main()