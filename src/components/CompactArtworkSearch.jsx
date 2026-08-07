import React, { useState, useEffect } from 'react';
import { Search, Filter, X, ChevronDown, ChevronUp, Loader } from 'lucide-react';

export const CompactArtworkSearch = ({ onResults, onError, placeholder = "Search artworks...", className = "" }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState('global');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState({
    category: '',
    medium: '',
    year: '',
    artist: '',
    title: ''
  });

  const searchTypes = [
    { value: 'global', label: 'Global Search (All fields)' },
    { value: 'artist', label: 'Artist' },
    { value: 'title', label: 'Title' },
    { value: 'category', label: 'Category' },
    { value: 'medium', label: 'Medium' },
    { value: 'id', label: 'Artwork ID' }
  ];

  const handleSearch = async (e) => {
    e.preventDefault();
    
    const query = searchQuery.trim();
    if (!query && !filters.category && !filters.medium && !filters.year && !filters.artist && !filters.title) {
      setError('Please enter search terms or select filters');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      let response;
      
      if (searchType === 'id') {
        response = await fetch(`/api/filemaker/artwork/${query}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
      } else {
        let searchRequest = {
          query: query,
          searchType: searchType === 'global' ? 'all' : searchType,
          limit: 1000
        };

        if (filters.category) searchRequest.category = filters.category;
        if (filters.medium) searchRequest.medium = filters.medium;
        if (filters.year) searchRequest.year = filters.year;
        if (filters.artist) searchRequest.artist = filters.artist;
        if (filters.title) searchRequest.title = filters.title;

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
      
      if (result.success) {
        if (searchType === 'id' && result.artwork) {
          onResults([result.artwork]);
        } else if (result.artworks) {
          onResults(result.artworks);
        } else {
          onResults([]);
        }
      } else {
        setError(result.error || 'Search failed');
        onError && onError(result.error || 'Search failed');
      }
    } catch (err) {
      setError(err.message || 'Search error occurred');
      onError && onError(err.message || 'Search error occurred');
    } finally {
      setLoading(false);
    }
  };

  const clearSearch = () => {
    setSearchQuery('');
    setFilters({
      category: '',
      medium: '',
      year: '',
      artist: '',
      title: ''
    });
    setError(null);
    onResults([]);
  };

  return (
    <div className={`bg-white border border-gray-200 rounded-lg p-4 mb-4 ${className}`}>
      <form onSubmit={handleSearch} className="space-y-3">
        <div className="flex gap-2">
          <div className="flex-1">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={placeholder}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          <select
            value={searchType}
            onChange={(e) => setSearchType(e.target.value)}
            className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {searchTypes.map(type => (
              <option key={type.value} value={type.value}>
                {type.label}
              </option>
            ))}
          </select>
{/* Filter button hidden
          <button
            type="button"
            onClick={() => setShowFilters(!showFilters)}
            className="px-3 py-2 border border-gray-300 rounded-md hover:bg-gray-50 flex items-center gap-1"
          >
            <Filter className="w-4 h-4" />
            {showFilters ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button> */}
          
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            {loading ? <Loader className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            {loading ? 'Searching...' : 'Search'}
          </button>
          
          {(searchQuery || Object.values(filters).some(v => v)) && (
            <button
              type="button"
              onClick={clearSearch}
              className="px-3 py-2 border border-gray-300 rounded-md hover:bg-gray-50 text-gray-600"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {showFilters && (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3 p-3 bg-gray-50 rounded-md">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <input
                type="text"
                value={filters.category}
                onChange={(e) => setFilters({ ...filters, category: e.target.value })}
                placeholder="e.g., Painting"
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Medium</label>
              <input
                type="text"
                value={filters.medium}
                onChange={(e) => setFilters({ ...filters, medium: e.target.value })}
                placeholder="e.g., Oil"
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Year</label>
              <input
                type="text"
                value={filters.year}
                onChange={(e) => setFilters({ ...filters, year: e.target.value })}
                placeholder="e.g., 1960"
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Artist</label>
              <input
                type="text"
                value={filters.artist}
                onChange={(e) => setFilters({ ...filters, artist: e.target.value })}
                placeholder="e.g., Picasso"
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Title</label>
              <input
                type="text"
                value={filters.title}
                onChange={(e) => setFilters({ ...filters, title: e.target.value })}
                placeholder="e.g., Femme"
                className="w-full px-2 py-1 border border-gray-300 rounded text-sm"
              />
            </div>
          </div>
        )}

        {error && (
          <div className="text-red-600 text-sm bg-red-50 p-2 rounded">
            {error}
          </div>
        )}
      </form>
    </div>
  );
};