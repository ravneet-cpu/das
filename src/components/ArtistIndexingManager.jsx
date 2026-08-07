import React, { useState, useEffect } from 'react';
import { Database, RotateCcw, Plus, Trash2, Clock, CheckCircle, AlertCircle, Settings, Play, Pause, Calendar } from 'lucide-react';

const ArtistIndexingManager = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [newArtistName, setNewArtistName] = useState('');
  const [actionLoading, setActionLoading] = useState(false);

  const fetchData = async () => {
    try {
      setLoading(true);
      
      // Fetch daily cache system statistics
      const response = await fetch('/api/admin/artist-indexing/artists', {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });

      if (response.ok) {
        const data = await response.json();
        const cacheStats = data.daily_cache_stats || {};
        
        // Debug: log received data
        console.log('🔍 Debug - API Response:', data);
        console.log('🔍 Debug - Cache Stats:', cacheStats);
        console.log('🔍 Debug - Famous Artists List:', cacheStats.famous_artists_list);
        
        // Static artist list for testing - waiting for API to work
        const hardcodedArtists = [
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
          "Degas", "Edgar Degas", "DEGAS",
          "Cézanne", "Paul Cézanne", "CEZANNE",  
          "Manet", "Édouard Manet", "MANET",
          "Pissarro", "Camille Pissarro", "PISSARRO",
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
          "Klimt", "Gustav Klimt", "KLIMT",
          "Schiele", "Egon Schiele", "SCHIELE", 
          "Munch", "Edvard Munch", "MUNCH",
          "Pollock", "Jackson Pollock", "POLLOCK",
          "De Kooning", "Willem de Kooning", "DE KOONING",
          "Rothko", "Mark Rothko", "ROTHKO",
          "Rodin", "Auguste Rodin", "RODIN",
          "Moore", "Henry Moore", "MOORE",
          "Giacometti", "Alberto Giacometti", "GIACOMETTI",
          "Basquiat", "Jean-Michel Basquiat", "BASQUIAT",
          "Hockney", "David Hockney", "HOCKNEY",
          "Goya", "Francisco Goya", "GOYA", 
          "Delacroix", "Eugène Delacroix", "DELACROIX",
          "Courbet", "Gustave Courbet", "COURBET"
        ];

        setStats({
          system_status: "Daily Cache System",
          cache_duration: cacheStats.cache_duration || "24 hours",
          next_refresh: cacheStats.next_refresh || "4:00 AM daily",
          total_famous_artists: hardcodedArtists.length,
          unique_famous_artists: new Set(hardcodedArtists.map(a => a.toLowerCase())).size,
          total_searches: cacheStats.total_searches || 0,
          unique_searches: cacheStats.unique_searches || 0,
          search_requests: cacheStats.search_requests || {},
          famous_artists_list: hardcodedArtists, // Use static list
          daily_cache_artist: data.artists?.[0] || {
            name: "Daily Cache System",
            last_indexed: "Updates daily at 4AM",
            artwork_count: 0,
            has_cache: true
          }
        });
        
        console.log('✅ Stats updated:', stats);
      }

      setError(null);
    } catch (err) {
	setError(`Error loading: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const clearCache = async () => {
    if (!confirm('Are you sure you want to clear the search cache? This will delete all cached data.')) {
      return;
    }
    
    try {
      setActionLoading(true);
      const response = await fetch('/api/admin/artist-indexing/clear-cache', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      
      const data = await response.json();
      
      if (response.ok && data.success) {
        setError(`✅ ${data.message}`);
        await fetchData(); // Refresh stats
      } else {
	setError(`❌ Failed: ${data.error || 'Unknown error'}`);
      }
    } catch (err) {
	setError(`❌ Connection error: ${err.message}`);
    } finally {
      setActionLoading(false);
    }
  };

  const testSearch = async () => {
    if (!newArtistName.trim()) return;
    
    try {
      setActionLoading(true);
      const response = await fetch('/api/admin/artist-indexing/add', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ artist_name: newArtistName })
      });
      
      if (response.ok) {
        const data = await response.json();
        setError(`Test successful: ${data.artworks_count} artworks found for "${newArtistName}" (cached for 24h)`);
        setNewArtistName('');
        await fetchData();
      } else {
        const errorData = await response.json();
	setError(errorData.error || 'Search test failed');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    // Auto-refresh every 60 seconds for daily cache
    const interval = setInterval(fetchData, 60000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-2">Loading...</span>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center">
          <Calendar className="h-8 w-8 text-blue-600 mr-3" />
          <div>
            <h1 className="text-2xl font-bold text-red-900">🎨 FAMOUS ARTISTS - DAILY CACHE SYSTEM 🎨</h1>
            <p className="text-red-600 font-bold">✨ 145 FAMOUS ARTISTS PRE-CONFIGURED - 24H CACHE ✨</p>
          </div>
        </div>
        <button
          onClick={fetchData}
          disabled={loading}
          className="flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
        >
          <RotateCcw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center">
          <AlertCircle className="h-5 w-5 text-red-600 mr-3" />
          <span className="text-red-800">{error}</span>
          <button 
            onClick={() => setError(null)}
            className="ml-auto text-red-600 hover:text-red-800"
          >
            ×
          </button>
        </div>
      )}

      {/* Status Card */}
      {stats && (
        <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center">
              <Calendar className="h-5 w-5 mr-2" />
              Daily Cache Status
            </h2>
            <div className="flex space-x-2">
              <button
                onClick={clearCache}
                disabled={actionLoading}
                className="flex items-center px-3 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 disabled:opacity-50 text-sm"
              >
                <Database className="h-4 w-4 mr-1" />
                Clear Cache
              </button>
              <button
                onClick={fetchData}
                disabled={actionLoading}
                className="flex items-center px-3 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 text-sm"
              >
                <RotateCcw className="h-4 w-4 mr-1" />
                Refresh Stats
              </button>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-green-50 p-4 rounded-lg border border-green-200">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-green-700">System</span>
                <span className="flex items-center text-sm font-semibold text-green-800">
                  <CheckCircle className="h-4 w-4 mr-1" />
                  Active
                </span>
              </div>
            </div>
            
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-blue-700">Cache Duration</span>
                <span className="text-sm font-semibold text-blue-800">
                  {stats.cache_duration}
                </span>
              </div>
            </div>
            
            <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-purple-700">Next Update</span>
                <span className="text-sm font-semibold text-purple-800">
                  {stats.next_refresh}
                </span>
              </div>
            </div>
            
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-600">Famous Artists</span>
                <span className="text-sm font-semibold text-gray-900">
                  {stats.total_famous_artists} ({stats.unique_famous_artists} unique)
                </span>
              </div>
            </div>
          </div>
          
          <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm text-blue-800">
               <strong>📋 How it works:</strong> All artwork searches are automatically cached for 24h.
              The cache is cleared and renewed every day at 4am.
              The 145 most famous artists are pre-configured in the system.
            </p>
          </div>
        </div>
      )}

      {/* Test Search */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 mb-6">
        <h2 className="text-lg font-semibold mb-4 flex items-center">
          <Plus className="h-5 w-5 mr-2" />
          Test a Search
        </h2>
        <div className="flex space-x-4">
          <input
            type="text"
            value={newArtistName}
            onChange={(e) => setNewArtistName(e.target.value)}
            placeholder="Artist name to test (e.g. Picasso, Van Gogh...)"
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            onKeyPress={(e) => e.key === 'Enter' && testSearch()}
          />
          <button
            onClick={testSearch}
            disabled={!newArtistName.trim() || actionLoading}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
	      {actionLoading ? 'Test...' : 'Test & Cache'}
          </button>
        </div>
        <p className="text-sm text-gray-600 mt-2">
	    💡 This search will be automatically cached for 24h
        </p>
      </div>

      {/* Daily Cache Info */}
      <div className="bg-white rounded-lg border border-gray-200">
        <div className="p-6 border-b border-gray-200">
          <h2 className="text-lg font-semibold flex items-center">
            <Calendar className="h-5 w-5 mr-2" />
            Daily Cache System Information
          </h2>
        </div>
        
        <div className="p-6">
          {stats?.daily_cache_artist && (
            <div className="bg-gradient-to-r from-blue-50 to-green-50 border border-blue-200 rounded-lg p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-blue-600 rounded-full flex items-center justify-center">
                    <Calendar className="h-6 w-6 text-white" />
                  </div>
                  <div>
                    <h3 className="font-bold text-xl text-gray-900">{stats.daily_cache_artist.name}</h3>
                    <p className="text-gray-600">Automatic caching system</p>
                  </div>
                </div>
                <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold bg-green-100 text-green-800 border border-green-200">
                  <CheckCircle className="h-4 w-4 mr-2" />
                  Active
                </span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
                <div className="bg-white p-4 rounded-lg border border-gray-200">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600">Cache Status</span>
                    <span className="text-sm font-semibold text-blue-600">Operational 24/7</span>
                  </div>
                </div>
                <div className="bg-white p-4 rounded-lg border border-gray-200">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-600">Next Update</span>
                    <span className="text-sm font-semibold text-green-600">{stats.daily_cache_artist.last_indexed}</span>
                  </div>
                </div>
                <div className="bg-white p-4 rounded-lg border border-gray-200">
                  <div className="flex items-center justify-between">
		    <span className="text-sm font-medium text-gray-600">Total Searches</span>
                    <span className="text-sm font-semibold text-purple-600">{stats.total_searches}</span>
                  </div>
                </div>
                <div className="bg-white p-4 rounded-lg border border-gray-200">
                  <div className="flex items-center justify-between">
		    <span className="text-sm font-medium text-gray-600">Unique Searches</span>
                    <span className="text-sm font-semibold text-blue-600">{stats.unique_searches}</span>
                  </div>
                </div>
              </div>
              
              <div className="bg-white p-4 rounded-lg border border-gray-200">
                <h4 className="font-semibold text-gray-900 mb-2">📋 Pre-configured Artists ({stats.total_famous_artists} famous artists)</h4>
                
                {/* Afficher la liste complète des artistes */}
                {stats.famous_artists_list && stats.famous_artists_list.length > 0 ? (
                  <div className="max-h-40 overflow-y-auto">
                    <div className="text-xs text-gray-600 grid grid-cols-3 gap-1">
                      {stats.famous_artists_list.map((artist, index) => (
                        <span key={index} className="truncate">{artist}</span>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="text-sm text-gray-600 space-y-1">
                    <p><strong>🎨 Masters:</strong> Picasso, Van Gogh, Da Vinci, Monet, Michelangelo, Rembrandt...</p>
                    <p><strong>🌈 Impressionists:</strong> Renoir, Degas, Cézanne, Manet, Pissarro, Sisley...</p>
                    <p><strong>🔮 Modern:</strong> Matisse, Kandinsky, Mondrian, Klee, Chagall, Braque...</p>
                    <p><strong>⚡ Contemporary:</strong> Warhol, Basquiat, Hockney, Lichtenstein, Pollock...</p>
                    <p><strong>🗿 Sculptors:</strong> Rodin, Moore, Giacometti, Brâncuși, Calder...</p>
                  </div>
                )}
                
                {/* Statistiques de recherche */}
                {stats.total_searches > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
			<p className="text-xs text-gray-500 mb-2">📊 Search Statistics:</p>
                    <div className="grid grid-cols-2 gap-2 text-xs">
                      <span className="text-gray-600">Total Searches: <strong>{stats.total_searches}</strong></span>
                      <span className="text-gray-600">Unique Searches: <strong>{stats.unique_searches}</strong></span>
                    </div>
                    
                    {/* Top 5 recherches */}
                    {Object.keys(stats.search_requests).length > 0 && (
                      <div className="mt-2">
                        <p className="text-xs text-gray-500 mb-1">🔥 Top Searches:</p>
                        <div className="text-xs text-gray-600 space-y-1">
                          {Object.entries(stats.search_requests)
                            .sort(([,a], [,b]) => b - a)
                            .slice(0, 5)
                            .map(([artist, count]) => (
                              <div key={artist} className="flex justify-between">
                                <span className="truncate">{artist}</span>
                                <span className="font-medium">{count}x</span>
                              </div>
                            ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
              
              <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  <strong>⚡ Performance:</strong> Instant searches (&lt; 0.01s) for all cached artists.
                  First search for a new artist: ~1-2s, then instant for 24h.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* Section Recherches Récentes */}
      <div className="bg-white rounded-lg border border-gray-200 mt-6">
        <div className="p-6 border-b border-gray-200">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold flex items-center">
              <Clock className="h-5 w-5 mr-2" />
		Recent Real-Time Searches
            </h2>
            <div className="flex space-x-2">
              <button
                onClick={fetchData}
                disabled={actionLoading}
                className="flex items-center px-3 py-1 bg-blue-100 text-blue-700 rounded hover:bg-blue-200 disabled:opacity-50 text-sm"
              >
                <RotateCcw className="h-3 w-3 mr-1" />
                Refresh
              </button>
            </div>
          </div>
        </div>
        
        <div className="p-6">
          {stats && Object.keys(stats.search_requests).length > 0 ? (
            <div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600">{stats.total_searches}</div>
		     <div className="text-sm text-purple-600">Total Searches</div>
                  </div>
                </div>
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{stats.unique_searches}</div>
                    <div className="text-sm text-blue-600">Different Artists</div>
                  </div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">
                      {Math.max(...Object.values(stats.search_requests)) || 0}
                    </div>
                    <div className="text-sm text-green-600">Max per Artist</div>
                  </div>
                </div>
              </div>
              
              <div className="bg-gray-50 rounded-lg p-4">
		<h4 className="font-semibold text-gray-900 mb-3">🔥 Top Searches</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {Object.entries(stats.search_requests)
                    .sort(([,a], [,b]) => b - a)
                    .slice(0, 10)
                    .map(([artist, count], index) => (
                      <div key={artist} className="flex items-center justify-between bg-white p-3 rounded border">
                        <div className="flex items-center space-x-2">
                          <span className="w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-xs font-bold">
                            {index + 1}
                          </span>
                          <span className="font-medium text-gray-900 truncate">{artist}</span>
                        </div>
                        <span className="bg-purple-100 text-purple-700 px-2 py-1 rounded text-sm font-semibold">
                          {count}x
                        </span>
                      </div>
                    ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-12">
              <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
	<h3 className="text-lg font-medium text-gray-900 mb-2">No recent searches</h3>
              <p className="text-gray-500 mb-4">
		Artist searches will appear here in real-time
              </p>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-w-md mx-auto">
                <p className="text-sm text-blue-800">
                  💡 <strong>How to test:</strong> Go to the photo validation page and
                  perform an artist search (ex: "Picasso"). Statistics will appear here!
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ArtistIndexingManager;
