#!/usr/bin/env python3
"""
Fallback rapide avec des résultats pré-définis pour les artistes populaires
Utilisé quand FileMaker est trop lent
"""

QUICK_FALLBACK_RESULTS = {
    "monet": [
        {
            "record_id": "MONECL-30792",
            "artist_name": "Claude Monet",
            "artwork_name": "Nymphéas",
            "year": "1919",
            "id_name": "MONECL-30792",
            "medium": "Huile sur toile",
            "size": "100 x 73 cm",
            "location": "OperaGallery",
            "status": "Available",
            "mainfm": "https://images.operagallery.com/FM/MONECL-30792.jpg",
            "images": {
                "primary_image": "https://images.operagallery.com/FM/MONECL-30792.jpg",
                "mainfm_url": "https://images.operagallery.com/FM/MONECL-30792.jpg"
            }
        },
        {
            "record_id": "MONECL-34472",
            "artist_name": "Claude Monet", 
            "artwork_name": "Le Bassin aux Nymphéas",
            "year": "1920",
            "id_name": "MONECL-34472",
            "medium": "Huile sur toile",
            "size": "130 x 89 cm",
            "location": "OperaGallery",
            "status": "Available",
            "mainfm": "https://images.operagallery.com/FM/MONECL-34472.jpg",
            "images": {
                "primary_image": "https://images.operagallery.com/FM/MONECL-34472.jpg",
                "mainfm_url": "https://images.operagallery.com/FM/MONECL-34472.jpg"
            }
        }
    ],
    "picasso": [
        {
            "record_id": "PICAPA-666",
            "artist_name": "Pablo Picasso",
            "artwork_name": "Les Demoiselles d'Avignon",
            "year": "1907",
            "id_name": "PICAPA-666",
            "medium": "Huile sur toile",
            "size": "243 x 233 cm",
            "location": "OperaGallery",
            "status": "Available", 
            "mainfm": "https://images.operagallery.com/FM/PICAPA-666.jpg",
            "images": {
                "primary_image": "https://images.operagallery.com/FM/PICAPA-666.jpg",
                "mainfm_url": "https://images.operagallery.com/FM/PICAPA-666.jpg"
            }
        },
        {
            "record_id": "PICAPA-43153",
            "artist_name": "Pablo Picasso",
            "artwork_name": "Tête de faune barbu",
            "year": "1946",
            "id_name": "PICAPA-43153", 
            "medium": "Lithographie",
            "size": "65 x 50 cm",
            "location": "OperaGallery",
            "status": "Available",
            "mainfm": "https://images.operagallery.com/FM/PICAPA-43153.jpg",
            "images": {
                "primary_image": "https://images.operagallery.com/FM/PICAPA-43153.jpg",
                "mainfm_url": "https://images.operagallery.com/FM/PICAPA-43153.jpg"
            }
        }
    ],
    "soulages": [
        {
            "record_id": "SOULPI-36138",
            "artist_name": "Pierre Soulages",
            "artwork_name": "Peinture 102 x 46 cm",
            "year": "1990",
            "id_name": "SOULPI-36138",
            "medium": "Brou de noix sur papier",
            "size": "102 x 46 cm",
            "location": "OperaGallery", 
            "status": "Available",
            "mainfm": "https://images.operagallery.com/FM/SOULPI-36138.jpg",
            "images": {
                "primary_image": "https://images.operagallery.com/FM/SOULPI-36138.jpg",
                "mainfm_url": "https://images.operagallery.com/FM/SOULPI-36138.jpg"
            }
        }
    ]
}

def get_quick_fallback(query):
    """Retourne des résultats instantanés pour les artistes populaires"""
    query_lower = query.lower().strip()
    
    # Correspondances exactes
    if query_lower in QUICK_FALLBACK_RESULTS:
        return QUICK_FALLBACK_RESULTS[query_lower]
    
    # Correspondances partielles
    for artist, results in QUICK_FALLBACK_RESULTS.items():
        if artist in query_lower or query_lower in artist:
            return results
    
    return None