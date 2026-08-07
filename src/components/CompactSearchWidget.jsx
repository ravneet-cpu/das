import React, { useState } from 'react';
import { Search, X, ExternalLink } from 'lucide-react';

const CompactSearchWidget = ({ onArtworkFound, onClose }) => {
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const searchType = formData.get('searchType');
    const query = formData.get('query');
    
    if (!query.trim()) return;
    
    setLoading(true);
    try {
      let response;
      if (searchType === 'global') {
        response = await fetch('/api/artworks/search', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify({
            search_type: 'global',
            query: query,
            limit: 10
          })
        });
      } else {
        response = await fetch(`/api/filemaker/artwork/${encodeURIComponent(query)}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
      }
      
      const data = await response.json();
      if (response.ok && data.success) {
        if (searchType === 'id' && data.artwork) {
          setSearchResults([data.artwork]);
        } else if (data.artworks && data.artworks.length > 0) {
          setSearchResults(data.artworks.slice(0, 6));
        } else {
          setSearchResults([]);
        }
      } else {
        setSearchResults([]);
      }
    } catch (err) {
      setSearchResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectArtwork = (artwork) => {
    if (onArtworkFound) {
      onArtworkFound(artwork);
    }
    setSearchResults([]);
    if (onClose) {
      onClose();
    }
  };

  return (
    <div className="absolute top-full left-0 mt-1 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
      <div className="p-3 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-medium text-gray-900">Search Artwork</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSearch} className="space-y-2">
          <div className="flex gap-2">
            <label className="flex items-center">
              <input type="radio" name="searchType" value="global" defaultChecked className="mr-1" />
              <span className="text-sm">Global</span>
            </label>
            <label className="flex items-center">
              <input type="radio" name="searchType" value="id" className="mr-1" />
              <span className="text-sm">ID</span>
            </label>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              name="query"
              placeholder="Search..."
              className="flex-1 px-2 py-1 border border-gray-300 rounded text-sm"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading}
              className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 disabled:opacity-50"
            >
              <Search className="w-4 h-4" />
            </button>
          </div>
        </form>
      </div>

      {/* Search Results */}
      {searchResults.length > 0 && (
        <div className="max-h-80 overflow-y-auto border-t border-gray-200">
          <div className="p-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="font-medium text-gray-900">
                Results ({searchResults.length})
              </h4>
              <button
                onClick={() => setSearchResults([])}
                className="text-gray-400 hover:text-gray-600"
              >
                <X className="w-3 h-3" />
              </button>
            </div>
            <div className="space-y-2">
              {searchResults.map((artwork, index) => (
                <div
                  key={artwork.IdName || index}
                  className="flex items-center gap-3 p-2 border border-gray-200 rounded hover:bg-gray-50 cursor-pointer"
                  onClick={() => handleSelectArtwork(artwork)}
                >
                  {/* Thumbnail */}
                  {artwork.main_picture_hd && (
                    <img
                      src={artwork.main_picture_hd}
                      alt={artwork.ArtistName}
                      className="w-12 h-12 object-cover rounded"
                      onError={(e) => {
                        e.target.style.display = 'none';
                      }}
                    />
                  )}
                  
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-sm text-gray-900 truncate">
                      {artwork.IdName}
                    </div>
                    <div className="text-xs text-gray-600 truncate">
                      {artwork.ArtistName}
                    </div>
                    {artwork.Title && (
                      <div className="text-xs text-gray-500 truncate">
                        {artwork.Title}
                      </div>
                    )}
                  </div>
                  
                  <ExternalLink className="w-3 h-3 text-gray-400 flex-shrink-0" />
                </div>
              ))}
            </div>
            
            {searchResults.length >= 6 && (
              <div className="mt-3 pt-2 border-t border-gray-200">
                <button
                  onClick={() => {
                    if (onClose) onClose();
                    // Open full search page
                    window.open('/search', '_blank');
                  }}
                  className="w-full px-3 py-2 text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded"
                >
                  View all results in new page →
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default CompactSearchWidget;