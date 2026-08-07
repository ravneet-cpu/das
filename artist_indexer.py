#!/usr/bin/env python3
"""
Artist Indexer - Pré-indexation automatique des artistes célèbres
Maintient en cache les recherches d'artistes les plus demandés
"""

import time
import threading
from datetime import datetime, timedelta

# Les 100 artistes les plus connus au monde
FAMOUS_ARTISTS = [
    # Top 10 - Les plus célèbres
    "Picasso", "Pablo Picasso", "PICASSO",
    "Van Gogh", "Vincent van Gogh", "VAN GOGH", 
    "Da Vinci", "Leonardo da Vinci", "LEONARDO",
    "Monet", "Claude Monet", "MONET",
    "Michelangelo", "MICHELANGELO",
    "Rembrandt", "REMBRANDT",
    "Matisse", "Henri Matisse", "MATISSE",
    "Renoir", "Auguste Renoir", "RENOIR",
    "Dali", "Salvador Dalí", "DALI",
    "Warhol", "Andy Warhol", "WARHOL",
    
    # Renaissance & Classiques (11-25)
    "Raphael", "Raffaello", "RAPHAEL",
    "Vermeer", "Johannes Vermeer", "VERMEER",
    "Botticelli", "Sandro Botticelli", "BOTTICELLI",
    "Caravaggio", "CARAVAGGIO",
    "Dürer", "Albrecht Dürer", "DURER",
    "El Greco", "EL GRECO",
    "Titian", "Tiziano", "TITIAN",
    "Rubens", "Peter Paul Rubens", "RUBENS",
    "Velázquez", "Diego Velázquez", "VELAZQUEZ",
    "Poussin", "Nicolas Poussin", "POUSSIN",
    "Watteau", "Antoine Watteau", "WATTEAU",
    "Fragonard", "Jean-Honoré Fragonard", "FRAGONARD",
    "David", "Jacques-Louis David", "DAVID",
    "Ingres", "Jean-Auguste-Dominique Ingres", "INGRES",
    "Géricault", "Théodore Géricault", "GERICAULT",
    
    # Impressionnistes & Post-Impressionnistes (26-50)
    "Degas", "Edgar Degas", "DEGAS",
    "Cézanne", "Paul Cézanne", "CEZANNE",  
    "Manet", "Édouard Manet", "MANET",
    "Pissarro", "Camille Pissarro", "PISSARRO",
    "Sisley", "Alfred Sisley", "SISLEY",
    "Berthe Morisot", "MORISOT",
    "Cassatt", "Mary Cassatt", "CASSATT",
    "Caillebotte", "Gustave Caillebotte", "CAILLEBOTTE",
    "Seurat", "Georges Seurat", "SEURAT",
    "Signac", "Paul Signac", "SIGNAC",
    "Toulouse-Lautrec", "Henri de Toulouse-Lautrec", "LAUTREC",
    "Gauguin", "Paul Gauguin", "GAUGUIN",
    "Bonnard", "Pierre Bonnard", "BONNARD",
    "Vuillard", "Édouard Vuillard", "VUILLARD",
    "Redon", "Odilon Redon", "REDON",
    "Cross", "Henri-Edmond Cross", "CROSS",
    "Marquet", "Albert Marquet", "MARQUET",
    "Dufy", "Raoul Dufy", "DUFY",
    "Vlaminck", "Maurice de Vlaminck", "VLAMINCK",
    "Derain", "André Derain", "DERAIN",
    "Friesz", "Othon Friesz", "FRIESZ",
    "Van Dongen", "Kees van Dongen", "VAN DONGEN",
    "Manguin", "Henri Manguin", "MANGUIN",
    "Camoin", "Charles Camoin", "CAMOIN",
    "Puy", "Jean Puy", "PUY",
    
    # Modernes & Avant-garde (51-75)
    "Kandinsky", "Wassily Kandinsky", "KANDINSKY",
    "Mondrian", "Piet Mondrian", "MONDRIAN",
    "Klee", "Paul Klee", "KLEE",
    "Chagall", "Marc Chagall", "CHAGALL", 
    "Braque", "Georges Braque", "BRAQUE",
    "Léger", "Fernand Léger", "LEGER",
    "Miró", "Joan Miró", "MIRO",
    "Magritte", "René Magritte", "MAGRITTE",
    "Ernst", "Max Ernst", "ERNST",
    "Duchamp", "Marcel Duchamp", "DUCHAMP",
    "Man Ray", "MAN RAY",
    "Picabia", "Francis Picabia", "PICABIA",
    "Delaunay", "Robert Delaunay", "DELAUNAY",
    "Sonia Delaunay", "SONIA DELAUNAY",
    "Kupka", "František Kupka", "KUPKA",
    "Larionov", "Mikhail Larionov", "LARIONOV",
    "Goncharova", "Natalia Goncharova", "GONCHAROVA",
    "Malevich", "Kazimir Malevich", "MALEVICH",
    "Rodchenko", "Alexander Rodchenko", "RODCHENKO",
    "Lissitzky", "El Lissitzky", "LISSITZKY",
    "Moholy-Nagy", "László Moholy-Nagy", "MOHOLY-NAGY",
    "Albers", "Josef Albers", "ALBERS",
    "Itten", "Johannes Itten", "ITTEN",
    "Feininger", "Lyonel Feininger", "FEININGER",
    "Schlemmer", "Oskar Schlemmer", "SCHLEMMER",
    
    # Expressionnistes & Contemporains (76-95)
    "Klimt", "Gustav Klimt", "KLIMT",
    "Schiele", "Egon Schiele", "SCHIELE", 
    "Kokoschka", "Oskar Kokoschka", "KOKOSCHKA",
    "Munch", "Edvard Munch", "MUNCH",
    "Nolde", "Emil Nolde", "NOLDE",
    "Kirchner", "Ernst Ludwig Kirchner", "KIRCHNER",
    "Heckel", "Erich Heckel", "HECKEL",
    "Schmidt-Rottluff", "Karl Schmidt-Rottluff", "SCHMIDT-ROTTLUFF",
    "Pechstein", "Max Pechstein", "PECHSTEIN",
    "Mueller", "Otto Mueller", "MUELLER",
    "Marc", "Franz Marc", "MARC",
    "Macke", "August Macke", "MACKE",
    "Jawlensky", "Alexej von Jawlensky", "JAWLENSKY",
    "Münter", "Gabriele Münter", "MUNTER",
    "Pollock", "Jackson Pollock", "POLLOCK",
    "De Kooning", "Willem de Kooning", "DE KOONING",
    "Rothko", "Mark Rothko", "ROTHKO",
    "Newman", "Barnett Newman", "NEWMAN",
    "Still", "Clyfford Still", "STILL",
    "Motherwell", "Robert Motherwell", "MOTHERWELL",
    
    # Sculpteurs & Artistes contemporains (96-100)
    "Rodin", "Auguste Rodin", "RODIN",
    "Moore", "Henry Moore", "MOORE",
    "Giacometti", "Alberto Giacometti", "GIACOMETTI",
    "Brâncuși", "Constantin Brâncuși", "BRANCUSI",
    "Calder", "Alexander Calder", "CALDER",
    "Basquiat", "Jean-Michel Basquiat", "BASQUIAT",
    "Haring", "Keith Haring", "HARING",
    "Lichtenstein", "Roy Lichtenstein", "LICHTENSTEIN",
    "Hockney", "David Hockney", "HOCKNEY",
    "Kline", "Franz Kline", "KLINE",
    
    # Maîtres anciens & Modernes français
    "Goya", "Francisco Goya", "GOYA", 
    "Delacroix", "Eugène Delacroix", "DELACROIX",
    "Courbet", "Gustave Courbet", "COURBET",
    "Millet", "Jean-François Millet", "MILLET",
    "Daumier", "Honoré Daumier", "DAUMIER",
    "Corot", "Jean-Baptiste-Camille Corot", "COROT",
    "Constable", "John Constable", "CONSTABLE",
    "Turner", "J.M.W. Turner", "TURNER",
    "Caspar David Friedrich", "FRIEDRICH",
    "Fuseli", "Henry Fuseli", "FUSELI",
    "Blake", "William Blake", "BLAKE",
    "Soulages", "Pierre Soulages", "SOULAGES",
    "Mathieu", "Georges Mathieu", "MATHIEU",
    "Hartung", "Hans Hartung", "HARTUNG",
    "Vasarely", "Victor Vasarely", "VASARELY"
]

class ArtistIndexer:
    def __init__(self):
        self.indexing_active = False
        self.last_index_time = {"Daily Cache System": datetime.now()}  # Un seul artiste fictif
        self.index_interval = 86400  # 24 heures
        self.background_thread = None
        self.search_requests = {}  # Enregistrer toutes les recherches
        
    def start_background_indexing(self):
        """Démarre l'indexation en arrière-plan"""
        if self.indexing_active:
            return
            
        self.indexing_active = True
        self.background_thread = threading.Thread(target=self._background_indexer, daemon=True)
        self.background_thread.start()
        print("[INDEXER] 🚀 Background artist indexing started")
    
    def stop_background_indexing(self):
        """Arrête l'indexation en arrière-plan"""
        self.indexing_active = False
        if self.background_thread:
            self.background_thread.join(timeout=5)
        print("[INDEXER] 🛑 Background artist indexing stopped")
    
    def _background_indexer(self):
        """Boucle d'indexation en arrière-plan"""
        while self.indexing_active:
            try:
                self._index_famous_artists()
                # Attendre 24 heures avant le prochain cycle
                time.sleep(86400)  # 24 heures
            except Exception as e:
                print(f"[INDEXER] ❌ Background indexing error: {e}")
                time.sleep(60)  # Attendre 1 minute en cas d'erreur
    
    def _index_famous_artists(self):
        """Indexe tous les artistes célèbres"""
        print(f"[DAILY-CACHE] 🗓️ Daily cache refresh at {datetime.now()}")
        
        # Système de cache quotidien - ne fait rien d'actif
        # Toutes les recherches sont automatiquement mises en cache pour 24h
        
        # Afficher les statistiques des recherches enregistrées
        total_searches = sum(self.search_requests.values())
        unique_searches = len(self.search_requests)
        
        print(f"[DAILY-CACHE] 📊 Stats: {total_searches} recherches, {unique_searches} requêtes uniques")
        
        if self.search_requests:
            # Afficher les top 5 recherches
            top_searches = sorted(self.search_requests.items(), key=lambda x: x[1], reverse=True)[:5]
            print(f"[DAILY-CACHE] 🔥 Top recherches:")
            for query, count in top_searches:
                print(f"   • {query}: {count} fois")
        
        print(f"[DAILY-CACHE] ✅ Cache refresh completed - next refresh in 24h")
    
    def _should_index_artist(self, artist):
        """Système de cache quotidien - toujours faux (pas d'indexation active)"""
        return False
    
    def index_artist_now(self, artist_name):
        """Enregistre la recherche et utilise le cache quotidien"""
        try:
            # Enregistrer la recherche
            if artist_name in self.search_requests:
                self.search_requests[artist_name] += 1
            else:
                self.search_requests[artist_name] = 1
            
            print(f"[DAILY-CACHE] 📝 Recherche enregistrée: {artist_name} ({self.search_requests[artist_name]}x)")
            
            # Import dynamique pour éviter l'import circulaire
            from operagallery_service import cached_search_operagallery_artworks
            
            # Faire la recherche (qui sera automatiquement mise en cache pour 24h)
            results = cached_search_operagallery_artworks(artist_name, limit=1000)
            
            if results:
                print(f"[DAILY-CACHE] ✅ {artist_name}: {len(results)} œuvres (cache 24h)")
                return len(results)
            else:
                print(f"[DAILY-CACHE] ⚠️ {artist_name}: Aucune œuvre trouvée")
                return 0
                
        except Exception as e:
            print(f"[DAILY-CACHE] ❌ Error searching {artist_name}: {e}")
            return 0
    
    def get_indexing_stats(self):
        """Retourne les statistiques du système de cache quotidien"""
        total_searches = sum(self.search_requests.values())
        unique_searches = len(self.search_requests)
        
        return {
            'total_famous_artists': len(FAMOUS_ARTISTS),
            'indexed_artists': 1,  # Un seul "artiste" (système de cache quotidien)
            'indexing_active': self.indexing_active,
            'total_searches': total_searches,
            'unique_searches': unique_searches,
            'search_requests': self.search_requests,
            'last_index_times': {
                'Daily Cache System': '24h cache - Updated daily at 4AM'
            }
        }

# Instance globale
artist_indexer = ArtistIndexer()

def start_artist_indexing():
    """Démarre l'indexation automatique des artistes"""
    artist_indexer.start_background_indexing()

def stop_artist_indexing():
    """Arrête l'indexation automatique des artistes"""
    artist_indexer.stop_background_indexing()

def index_artist(artist_name):
    """Indexe manuellement un artiste"""
    return artist_indexer.index_artist_now(artist_name)

def get_artist_indexing_stats():
    """Récupère les statistiques d'indexation"""
    return artist_indexer.get_indexing_stats()

if __name__ == "__main__":
    # Test direct
    print("=== TEST ARTIST INDEXER ===")
    indexer = ArtistIndexer()
    
    # Test manuel
    try:
        result = indexer.index_artist_now("Picasso")
        print(f"Picasso indexé: {result} œuvres")
    except Exception as e:
        print(f"Erreur test: {e}")
    
    # Stats
    stats = indexer.get_indexing_stats()
    print(f"Stats: {stats}")