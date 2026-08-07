// src/components/ArtworkSearch.jsx
import React, { useState } from 'react';
import { Search, CheckCircle, AlertTriangle, Database, Filter, X, ChevronDown, ChevronRight, Copy, ExternalLink, Eye, Image as ImageIcon } from 'lucide-react';
import { ArtworkImageGallery } from './ArtworkImageGallery';
// Utilise maintenant le service OperaGallery intégré

export const ArtworkSearch = ({ photoId, onArtworkFound }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchType, setSearchType] = useState('global'); // 'id', 'global', 'artist', 'title', 'medium', 'category'
  const [showFilters, setShowFilters] = useState(false);
  const [modalArtwork, setModalArtwork] = useState(null);  // popup modal
  const [copiedUrl, setCopiedUrl] = useState('');  // flash copied
  
  // Advanced filters
  const [filters, setFilters] = useState({
    category: '',
    medium: '',
    year: '',
    artist: '',
    title: ''
  });

  // Extract potential artwork ID from photo filename
  React.useEffect(() => {
    if (photoId) {
      // Look for a pattern that resembles an artwork ID (e.g., TIANLI-45492)
      const idMatch = photoId.match(/([A-Z]+-\d+)/);
      if (idMatch && idMatch[1]) {
        setSearchQuery(idMatch[1]);
        setSearchType('id');
      }
    }
  }, [photoId]);

  // Handle filter changes
  const handleFilterChange = (filterName, value) => {
    setFilters(prev => ({
      ...prev,
      [filterName]: value
    }));
  };

  // Clear filters
  const clearFilters = () => {
    setFilters({
      category: '',
      medium: '',
      year: '',
      artist: '',
      title: ''
    });
  };

  // Handle search
  const handleSearch = async (e) => {
    e.preventDefault();
    
    const query = searchQuery.trim();
    if (!query && !filters.category && !filters.medium && !filters.year && !filters.artist && !filters.title) {
      setError('Please enter search terms or select filters');
      return;
    }

    setLoading(true);
    setError(null);
    setSearchResults(null);

    try {
      let response;
      
      if (searchType === 'id') {
        // Search by ID in FileMaker
        response = await fetch(`/api/filemaker/artwork/${query}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
      } else {
        // Build search request based on type and filters
        let searchRequest = {
          query: query,
          searchType: searchType === 'global' ? 'all' : searchType === 'date' ? 'year' : searchType,
          limit: 1000
        };

        // Add filters to search request
        if (filters.category) searchRequest.category = filters.category;
        if (filters.medium) searchRequest.medium = filters.medium;
        if (filters.year) searchRequest.year = filters.year;
        if (filters.artist) searchRequest.artist = filters.artist;
        if (filters.title) searchRequest.title = filters.title;

        // For global search, combine all filter values into the main query
        if (searchType === 'global') {
          const filterQueries = [];
          if (filters.category) filterQueries.push(filters.category);
          if (filters.medium) filterQueries.push(filters.medium);
          if (filters.year) filterQueries.push(filters.year);
          if (filters.artist) filterQueries.push(filters.artist);
          if (filters.title) filterQueries.push(filters.title);
          
          if (filterQueries.length > 0) {
            searchRequest.query = [query, ...filterQueries].filter(Boolean).join(' ');
          }
        }

        response = await fetch('/api/artworks/search', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: JSON.stringify(searchRequest)
        });
      }
      
      const result = await response.json();
      setSearchResults(result);
      
      // If artwork is found, notify parent component
      if (result.success) {
        if (searchType === 'id' && result.artwork) {
          onArtworkFound && onArtworkFound(result.artwork);
        } else if (result.artworks && result.artworks.length > 0) {
          // For other searches, use the first result
          onArtworkFound && onArtworkFound(result.artworks[0]);
        }
      }
    } catch (err) {
      setError(err.message || 'Search error occurred');
      // Search error occurred
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white border-2 border-gray-300 rounded-lg p-6 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center">
          <Database className="h-6 w-6 text-blue-600 mr-3" />
          <h3 className="text-lg font-bold text-black">OPERAGALLERY SEARCH v2</h3>
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className="flex items-center px-3 py-1 bg-blue-50 border border-blue-200 text-blue-700 rounded hover:bg-blue-100 text-sm"
        >
          <Filter className="h-4 w-4 mr-1" />
          Filters
          {showFilters ? <ChevronDown className="h-4 w-4 ml-1" /> : <ChevronRight className="h-4 w-4 ml-1" />}
        </button>
      </div>
      
      {/* Search Type Selection */}
      <div className="mb-4">
        <div className="flex flex-wrap gap-2">
          {[
            { value: 'global', label: 'Global Search (All fields)' },
            { value: 'id', label: 'By ID' },
            { value: 'artist', label: 'By Artist' },
            { value: 'title', label: 'By Title' },
            { value: 'date', label: 'By Date' }
          ].map(option => (
            <label key={option.value} className="flex items-center">
              <input
                type="radio"
                value={option.value}
                checked={searchType === option.value}
                onChange={(e) => setSearchType(e.target.value)}
                className="mr-2"
              />
              <span className="text-sm font-medium">{option.label}</span>
            </label>
          ))}
        </div>
      </div>
      
      {/* Advanced Filters */}
      {showFilters && (
        <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="flex items-center justify-between mb-3">
            <h4 className="font-semibold text-gray-900">Advanced Filters</h4>
            <button
              onClick={clearFilters}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Clear all
            </button>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <input
                type="text"
                value={filters.category}
                onChange={(e) => handleFilterChange('category', e.target.value)}
                placeholder="e.g., painting, sculpture..."
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Medium</label>
              <input
                type="text"
                value={filters.medium}
                onChange={(e) => handleFilterChange('medium', e.target.value)}
                placeholder="e.g., oil on canvas, bronze..."
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Year</label>
              <input
                type="text"
                value={filters.year}
                onChange={(e) => handleFilterChange('year', e.target.value)}
                placeholder="e.g., 1950, 1960-1970..."
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Artist</label>
              <input
                type="text"
                value={filters.artist}
                onChange={(e) => handleFilterChange('artist', e.target.value)}
                placeholder="e.g., Picasso, Van Gogh..."
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
              <input
                type="text"
                value={filters.title}
                onChange={(e) => handleFilterChange('title', e.target.value)}
                placeholder="e.g., Les Demoiselles..."
                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      )}
      
      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex items-center">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={
                searchType === 'global' ? 'Search across all fields (artist, title, medium, category...)' :
                searchType === 'id' ? 'OperaGallery ID (e.g.: PICAPA-666)' :
                searchType === 'artist' ? 'Artist name (supports multiple words)' :
                searchType === 'title' ? 'Artwork title (supports multiple words)' :
                searchType === 'date' ? 'Date or year (e.g., 1968, 2020-2023...)'
                : 'Enter search terms...'
              }
              className="w-full pl-10 pr-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="ml-3 px-4 py-3 bg-black text-white rounded-lg hover:bg-gray-800 disabled:opacity-50 min-w-24"
          >
            {loading ? 'SEARCHING...' : 'SEARCH'}
          </button>
        </div>
        
        {/* Search hints */}
        <div className="mt-2 text-xs text-gray-600">
          {searchType === 'global' && (
            <p>💡 Global search looks in artist, title, medium, category, and other fields simultaneously</p>
          )}
          {(searchType === 'artist' || searchType === 'title') && (
            <p>💡 Supports multiple words: "Pablo Picasso", "Les Demoiselles d'Avignon"</p>
          )}
          {searchType === 'date' && (
            <p>💡 Search by year or date range: "1968", "2020", "1950-1960"</p>
          )}
          {showFilters && (
            <p>💡 Use filters above to narrow down your search results</p>
          )}
        </div>
      </form>
      
      {error && (
        <div className="bg-red-50 border-2 border-red-300 px-4 py-3 mb-4 flex items-center rounded-lg">
          <AlertTriangle className="h-5 w-5 mr-3 text-red-600" />
          <span className="text-sm text-red-800">{error}</span>
        </div>
      )}
      
      {searchResults && (
        <div className={`border-2 p-4 rounded-lg ${searchResults.success ? 'border-green-400 bg-green-50' : 'border-yellow-400 bg-yellow-50'}`}>
          {searchResults.success && searchType === 'id' && searchResults.artwork ? (
            // Single artwork found by ID
            <div>
              <div className="flex items-start mb-4">
                <div className="bg-green-600 text-white p-2 rounded mr-3">
                  <CheckCircle className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-black font-semibold">ARTWORK FOUND IN OPERAGALLERY</p>
                  <p className="text-gray-600 text-sm mt-1">This artwork already exists in the OperaGallery database</p>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                <div className="space-y-2">
                  <h4 className="text-black font-semibold text-base">OPERAGALLERY DETAILS</h4>
                  <div className="text-gray-700 text-sm space-y-1">
                    <p><span className="font-medium">ID:</span> {searchResults.artwork.IdName}</p>
                    <p><span className="font-medium">Title:</span> {searchResults.artwork.title}</p>
                    <p><span className="font-medium">Artist:</span> {searchResults.artwork.artist}</p>
                    <p><span className="font-medium">Year:</span> {searchResults.artwork.year}</p>
                    <p><span className="font-medium">Category:</span> {searchResults.artwork.category}</p>
                    <p><span className="font-medium">Medium:</span> {searchResults.artwork.medium}</p>
                  </div>
                </div>
                
                {/* 🎯 NOUVELLE GALERIE D'IMAGES AVEC TOUS LES TYPES */}
                <ArtworkImageGallery artwork={searchResults.artwork} />
                
                {/* Fallback: Afficher l'image principale si pas d'autres images */}
                {(!searchResults.artwork.image_fields || Object.keys(searchResults.artwork.image_fields).length === 0) && searchResults.artwork.main_picture_hd && (
                  <div>
                    <h4 className="text-black font-semibold text-base mb-2">REFERENCE IMAGE</h4>
                    <div className="border-2 border-gray-300 rounded-lg overflow-hidden">
                      <img 
                        src={searchResults.artwork.main_picture_hd} 
                        alt={`Artwork ${searchResults.artwork.IdName}`}
                        className="w-full h-auto"
                        style={{ maxHeight: '200px', objectFit: 'contain' }}
                      />
                    </div>
                  </div>
                )}
              </div>
              
              <div className="mt-4 p-3 border-2 border-orange-400 bg-orange-50 rounded-lg">
                <div className="flex items-start">
                  <AlertTriangle className="h-5 w-5 text-orange-600 mr-3 mt-0.5" />
                  <div>
                    <p className="text-black font-semibold text-sm mb-1">DUPLICATE WARNING</p>
                    <p className="text-gray-700 text-sm">
                      This artwork already exists in OperaGallery. Make sure not to create a duplicate.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          ) : searchResults.success && searchResults.artworks && searchResults.artworks.length > 0 ? (
            // Multiple artworks found
            <div>
              <div className="flex items-start mb-4">
                <div className="bg-green-600 text-white p-2 rounded mr-3">
                  <CheckCircle className="h-5 w-5" />
                </div>
                <div>
                  <p className="text-black font-semibold">ARTWORKS FOUND</p>
                  <p className="text-gray-600 text-sm mt-1">
                    Found {searchResults.artworks.length} artwork(s) 
                    {searchType === 'global' && searchQuery ? ` matching "${searchQuery}"` : ''}
                    {searchType !== 'global' && searchType !== 'id' ? ` in ${searchType}` : ''}
                  </p>
                </div>
              </div>
              
              {/* Active filters display */}
              {(filters.category || filters.medium || filters.year || filters.artist || filters.title) && (
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm font-medium text-blue-900 mb-2">Active filters:</p>
                  <div className="flex flex-wrap gap-2">
                    {filters.category && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                        Category: {filters.category}
                      </span>
                    )}
                    {filters.medium && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                        Medium: {filters.medium}
                      </span>
                    )}
                    {filters.year && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                        Year: {filters.year}
                      </span>
                    )}
                    {filters.artist && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                        Artist: {filters.artist}
                      </span>
                    )}
                    {filters.title && (
                      <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                        Title: {filters.title}
                      </span>
                    )}
                  </div>
                </div>
              )}
              
              <div className="max-h-80 overflow-y-auto space-y-3">
                {searchResults.artworks.slice(0, 20).map((artwork, index) => (
                  <div key={index} className="border border-gray-300 rounded-lg p-3 bg-white">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="md:col-span-2 space-y-1">
                        <p className="text-sm"><span className="font-medium">ID:</span> {artwork.IdName}</p>
                        <p className="text-sm"><span className="font-medium">Title:</span> {artwork.title}</p>
                        <p className="text-sm"><span className="font-medium">Artist:</span> {artwork.artist}</p>
                        <p className="text-sm"><span className="font-medium">Year:</span> {artwork.year}</p>
                        <p className="text-sm"><span className="font-medium">Category:</span> {artwork.category}</p>
                        <p className="text-sm"><span className="font-medium">Medium:</span> {artwork.medium}</p>
                        {artwork.dimensions && (
                          <p className="text-sm"><span className="font-medium">Dimensions:</span> {artwork.dimensions}</p>
                        )}
                        {artwork.location && (
                          <p className="text-sm"><span className="font-medium">Location:</span> {artwork.location}</p>
                        )}
                        {artwork.image_count > 0 && (
                          <p className="text-sm"><span className="font-medium">Images:</span> {artwork.image_count} available</p>
                        )}
                        {artwork.filemakerData?.CertificateFMUrl && (
                          <p className="text-sm">
                            <span className="font-medium">Certificate:</span>{' '}
                            <a 
                              href={artwork.filemakerData.CertificateFMUrl} 
                              target="_blank" 
                              rel="noopener noreferrer"
                              className="text-green-600 hover:text-green-800 underline"
                            >
                              View PDF
                            </a>
                          </p>
                        )}
                        {artwork.filemakerData?.CertificateWording && (
                          <p className="text-sm">
                            <span className="font-medium">Certificate Info:</span>{' '}
                            <span className="text-yellow-800 italic">
                              {artwork.filemakerData.CertificateWording.length > 100 
                                ? artwork.filemakerData.CertificateWording.substring(0, 100) + '...' 
                                : artwork.filemakerData.CertificateWording}
                            </span>
                          </p>
                        )}
                      </div>
                      <div className="flex flex-col items-center justify-center gap-1">
                        {artwork.main_picture_hd && (
                          <>
                            <img 
                              src={artwork.main_picture_hd} 
                              alt={`Artwork ${artwork.IdName}`}
                              className="w-20 h-20 object-cover rounded border"
                              onError={(e) => {
                                e.target.style.display = 'none';
                              }}
                            />
                            <input
                              type="text"
                              readOnly
                              value={artwork.main_picture_hd}
                              onClick={(e) => { e.target.select(); navigator.clipboard.writeText(e.target.value); }}
                              className="w-32 text-xs px-1 py-0.5 border rounded bg-gray-50 cursor-pointer truncate"
                              title="Click to copy URL"
                            />
                          </>
                        )}
                        <button
                          onClick={() => { setModalArtwork(artwork); onArtworkFound && onArtworkFound(artwork); }}
                          className="px-3 py-1 bg-blue-500 text-white rounded text-sm hover:bg-blue-600"
                        >
                          <Eye className="w-3 h-3 inline mr-1" /> View
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              
              {searchResults.artworks.length > 20 && (
                <p className="text-sm text-gray-600 mt-3">
                  Showing first 20 results. Total: {searchResults.artworks.length} artworks.
                </p>
              )}
            </div>
          ) : (
            // No results found
            <div className="flex items-start">
              <div className="bg-yellow-600 text-white p-2 rounded mr-3">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <p className="text-black font-semibold">
                  {searchType === 'id' ? 'ARTWORK NOT FOUND' : 'NO ARTWORKS FOUND'}
                </p>
                <p className="text-gray-700 text-sm mt-1">
                  {searchType === 'id' 
                    ? 'No artwork found with this ID in OperaGallery. If you validate this photo, it will be considered as a new artwork.'
                    : searchType === 'global'
                    ? `No artworks found matching "${searchQuery}". Try different search terms or use the filters above.`
                    : `No artworks found in ${searchType} matching "${searchQuery}". Try different search terms or expand your search.`
                  }
                </p>
              </div>
            </div>
          )}
        </div>
      )}
      {/* Image Modal Popup */}
      {modalArtwork && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4" onClick={() => setModalArtwork(null)}>
          <div className="bg-white rounded-xl shadow-xl border-2 border-gray-300 max-w-4xl w-full max-h-[90vh] overflow-auto" onClick={e => e.stopPropagation()}>
            <div className="flex justify-between items-center p-4 border-b-2 sticky top-0 bg-white z-10">
              <div>
                <h2 className="text-xl font-bold text-black">{modalArtwork.title || modalArtwork.IdName}</h2>
                <p className="text-gray-600 text-sm">{modalArtwork.artist}{modalArtwork.year ? ' • ' + modalArtwork.year : ''}</p>
                <p className="text-blue-600 text-xs font-mono">{modalArtwork.IdName}</p>
              </div>
              <button onClick={() => setModalArtwork(null)} className="p-2 hover:bg-gray-100 rounded-full"><X className="h-5 w-5" /></button>
            </div>
            <div className="p-4">
              {(modalArtwork.all_image_urls && modalArtwork.all_image_urls.length > 0) ? (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {modalArtwork.all_image_urls.map((url, i) => (
                    <div key={i} className="border rounded-lg overflow-hidden bg-gray-50">
                      <img src={url} className="w-full h-32 object-cover" onError={e => { e.target.style.display='none' }} />
                      <div className="p-2 flex items-center gap-1">
                        <input type="text" readOnly value={url} className="flex-1 text-xs px-1 py-1 border rounded bg-white truncate"
                          onClick={e => { e.target.select(); navigator.clipboard.writeText(e.target.value); setCopiedUrl(url); setTimeout(()=>setCopiedUrl(''),2000); }} />
                        <button onClick={() => { navigator.clipboard.writeText(url); setCopiedUrl(url); setTimeout(()=>setCopiedUrl(''),2000); }}
                          className="p-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 flex-shrink-0" title="Copy URL">
                          {copiedUrl === url ? <CheckCircle className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-gray-400"><ImageIcon className="h-12 w-12 mx-auto mb-2" /><p>No images available</p></div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ArtworkSearch;
