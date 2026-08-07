import React, { useState, useEffect, useCallback } from 'react';
import { Search, Filter, Grid, List, Eye, Download, X, ChevronDown, ChevronRight, Loader, AlertCircle, Image as ImageIcon, CheckCircle, Camera, Bookmark, Check, Zap, FileText, FileImage, Table, Copy } from 'lucide-react';

const ImageSearchEngine = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState('all'); // 'all', 'artist', 'artwork_id', 'title'
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [viewMode, setViewMode] = useState('grid'); // 'grid', 'list'
  const [selectedArtwork, setSelectedArtwork] = useState(null);
  const [showFilters, setShowFilters] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalResults, setTotalResults] = useState(0);
  const [filters, setFilters] = useState({
    hasImages: false,
    stockFilter: 'all', // all, in_stock, in_transit, available
    galleryFilter: 'all', // all, specific gallery
    qualityFilter: 'all', // all, excellent, good, acceptable, poor, no_image
    markedFilter: 'all', // all, marked, unmarked
    category: '',
    medium: ''
  });
  const [markedArtworks, setMarkedArtworks] = useState(new Set());
  const [analyzingQuality, setAnalyzingQuality] = useState({});
  const [detailedQuality, setDetailedQuality] = useState({});
  const [availableGalleries, setAvailableGalleries] = useState([]);

  // Debounced search
  const [searchTimeout, setSearchTimeout] = useState(null);

  const searchTypes = [
    { value: 'all', label: '🔍 Global Search', placeholder: 'Picasso, Celosía, Denzler, Two Dancers...' },
    { value: 'artist', label: '👨‍🎨 Artist', placeholder: 'Pablo PICASSO, Rafael CANOGAR, Andy DENZLER...' },
    { value: 'artwork_id', label: '🆔 Artwork ID', placeholder: 'PICAPA-53742, CANORA-53741, DENZAN-53738...' },
    { value: 'title', label: '🎨 Title', placeholder: 'Celosía, Untitled, Two Dancers and Oriental...' }
  ];

  // Abort controller for debounced search
  const abortRef = React.useRef(null);
  const queryRef = React.useRef('');

  const performSearch = async (query = searchQuery, page = 1) => {
    if (!query.trim() && searchType !== 'all' && filters.galleryFilter === 'all') return;

    // Cancel any in-flight request
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    const requestQuery = query.trim();
    queryRef.current = requestQuery;

    try {
      setLoading(true);
      setError(null);

      const response = await fetch('/api/artworks/search-new', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          query: requestQuery,
          searchType, page, filters,
          qualityFilter: filters.qualityFilter,
          stockFilter: filters.stockFilter,
          galleryFilter: filters.galleryFilter,
          limit: 200
        }),
        signal: controller.signal
      });

      if (!response.ok) {
        if (response.status === 401) {
          setError('Session expired. Please re-login.');
        } else if (response.status >= 500) {
          setError('Backend server is down. Please try again later.');
        } else {
          setError(`Server error (${response.status})`);
        }
        setResults([]);
        setTotalResults(0);
        return;
      }

      const data = await response.json();

      // Ignore stale responses (from cancelled/overwritten requests)
      if (requestQuery !== queryRef.current) return;

      if (data.error) {
        setError(data.error);
        setResults([]);
        setTotalResults(0);
        return;
      }
      
      // Apply image filter only if enabled
      let filteredArtworks = data.artworks || [];
      if (filters.hasImages) {
        filteredArtworks = filteredArtworks.filter(artwork => 
          artwork.image_count > 0 && artwork.all_image_urls && artwork.all_image_urls.length > 0
        );
      }
      
      // Apply marking filter
      if (filters.markedFilter === 'marked') {
        filteredArtworks = filteredArtworks.filter(artwork => 
          markedArtworks.has(String(artwork.IdName || artwork.id || 'NO_ID'))
        );
      } else if (filters.markedFilter === 'unmarked') {
        filteredArtworks = filteredArtworks.filter(artwork => 
          !markedArtworks.has(String(artwork.IdName || artwork.id || 'NO_ID'))
        );
      }
      
      // Gallery filter is now applied on the backend
      
      // Galleries are now loaded at component startup
      
      // Filtering applied
      setResults(filteredArtworks);
      setTotalResults(filteredArtworks.length);
      setCurrentPage(page);

    } catch (err) {
      if (err.name === 'AbortError') return;
      if (err.message?.includes('Failed to fetch') || err.message?.includes('NetworkError')) {
        setError('Backend server is down. Please try again later.');
      }
    } finally {
      setLoading(false);
    }
  };

  const getQualityIcon = (qualityAnalysis) => {
    if (!qualityAnalysis || qualityAnalysis.error) {
      return <div className="w-4 h-4 rounded-full bg-gray-400 flex items-center justify-center">
        <AlertCircle className="w-3 h-3 text-white" />
      </div>;
    }

    const colorCode = qualityAnalysis.color_code;
    const baseClasses = "w-4 h-4 rounded-full flex items-center justify-center";
    
    switch(colorCode) {
      case 'green':
        return <div className={`${baseClasses} bg-green-500`} title="Excellent quality (300+ DPI)">
          <CheckCircle className="w-3 h-3 text-white" />
        </div>;
      case 'lightgreen':
        return <div className={`${baseClasses} bg-green-400`} title="Good quality (200+ DPI)">
          <CheckCircle className="w-3 h-3 text-white" />
        </div>;
      case 'orange':
        return <div className={`${baseClasses} bg-orange-500`} title="Acceptable quality (150+ DPI)">
          <AlertCircle className="w-3 h-3 text-white" />
        </div>;
      case 'red':
        return <div className={`${baseClasses} bg-red-500`} title="Poor quality (less than 150 DPI)">
          <X className="w-3 h-3 text-white" />
        </div>;
      default:
        return <div className={`${baseClasses} bg-gray-500`} title="Unknown quality">
          <AlertCircle className="w-3 h-3 text-white" />
        </div>;
    }
  };


  // Debounced search effect
  useEffect(() => {
    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }

    const timeout = setTimeout(() => {
      if (searchQuery.length >= 2) {
        performSearch();
      }
    }, 800);

    setSearchTimeout(timeout);

    return () => clearTimeout(timeout);
  }, [searchQuery, searchType, filters]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    performSearch();
  };

  const openArtworkModal = (artwork) => {
    setSelectedArtwork(artwork);
  };

  const closeArtworkModal = () => {
    setSelectedArtwork(null);
  };

  const toggleMarkArtwork = async (artworkId) => {
    const isMarked = markedArtworks.has(artworkId.toString());
    const endpoint = isMarked ? 'unmark-for-processing' : 'mark-for-processing';
    
    try {
      const response = await fetch(`/api/artworks/${artworkId}/${endpoint}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      const result = await response.json();
      
      if (result.success) {
        setMarkedArtworks(prev => {
          const newSet = new Set(prev);
          if (isMarked) {
            newSet.delete(artworkId.toString());
          } else {
            newSet.add(artworkId.toString());
          }
          return newSet;
        });
      }
    } catch (err) {
      // Error updating mark
    }
  };

  // Load marked artworks and galleries on component mount
  useEffect(() => {
    const loadMarkedArtworks = async () => {
      try {
        const response = await fetch('/api/artworks/marked-for-processing', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        const result = await response.json();
        
        if (result.success) {
          setMarkedArtworks(new Set(result.marked_artwork_ids));
        }
      } catch (err) {
        // Error loading marked artworks
      }
    };

    const loadGalleries = async () => {
      try {
        const response = await fetch('/api/artworks/galleries', {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        const result = await response.json();
        
        if (result.success) {
          setAvailableGalleries(result.galleries);
        }
      } catch (err) {
        // Error loading galleries
      }
    };
    
    loadMarkedArtworks();
    loadGalleries();
  }, []);

  const analyzeDetailedQuality = async (artworkId) => {
    setAnalyzingQuality(prev => ({ ...prev, [artworkId]: true }));
    
    try {
      const response = await fetch(`/api/artworks/${artworkId}/analyze-quality`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      const result = await response.json();
      
      if (result.success) {
        setDetailedQuality(prev => ({
          ...prev,
          [artworkId]: result.quality_analysis
        }));
      }
    } catch (err) {
      // Error analyzing quality
    } finally {
      setAnalyzingQuality(prev => ({ ...prev, [artworkId]: false }));
    }
  };

  const currentSearchType = searchTypes.find(t => t.value === searchType);

  // Export functions
  const exportToCSV = () => {
    if (!results.length) return;
    
    const headers = ['ID', 'Title', 'Artist', 'Year', 'Category', 'Medium', 'Dimensions', 'Location', 'Status', 'Images'];
    const csvData = results.map(artwork => [
      artwork.IdName || '',
      artwork.title || artwork.name || '',
      artwork.artist || artwork.ArtistName || '',
      artwork.year || '',
      artwork.category || artwork.Category || '',
      artwork.medium || artwork.Medium || '',
      artwork.dimensions || '',
      artwork.location || '',
      artwork.status || '',
      (artwork.all_image_urls?.length || artwork.image_count || 0)
    ]);
    
    const csvContent = [headers, ...csvData]
      .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
      .join('\\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const searchInfo = searchQuery ? `_${searchQuery.replace(/[^a-zA-Z0-9]/g, '_')}` : '';
    link.href = URL.createObjectURL(blob);
    link.download = `operacrm_search${searchInfo}_${new Date().toISOString().split('T')[0]}.csv`;
    link.click();
  };

  const exportToPDF = () => {
    if (!results.length) return;
    
    const printWindow = window.open('', '_blank');
    const searchInfo = searchQuery ? ` for "${searchQuery}"` : '';
    const currentDate = new Date().toLocaleDateString();
    
    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>OperaGallery Search Results</title>
        <style>
          body { font-family: Arial, sans-serif; margin: 20px; color: #333; }
          .header { text-align: center; border-bottom: 2px solid #000; padding-bottom: 20px; margin-bottom: 30px; }
          .header h1 { margin: 0; color: #000; font-size: 28px; }
          .header p { margin: 5px 0; color: #666; }
          .filters { background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px; }
          .artwork { border: 1px solid #ddd; margin-bottom: 20px; padding: 15px; border-radius: 8px; page-break-inside: avoid; }
          .artwork-content { display: flex; gap: 15px; align-items: start; }
          .artwork-image { flex-shrink: 0; width: 150px; height: 120px; overflow: hidden; border-radius: 6px; border: 1px solid #eee; }
          .artwork-image img { width: 100%; height: 100%; object-fit: cover; }
          .artwork-details { flex: 1; min-width: 0; }
          .artwork-header { display: flex; justify-content: space-between; align-items: start; margin-bottom: 10px; }
          .artwork-title { font-size: 18px; font-weight: bold; color: #000; margin: 0; }
          .artwork-id { background: #e3f2fd; color: #1565c0; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-size: 12px; }
          .artwork-info { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; }
          .info-item { font-size: 14px; }
          .info-label { font-weight: bold; color: #555; }
          .stats { text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; }
          @media print { body { margin: 0; } .no-print { display: none; } }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>🎨 OperaGallery Search Results</h1>
          <p>Search${searchInfo} • ${currentSearchType?.label || 'Unknown'} • ${currentDate}</p>
          <p>${results.length} artwork${results.length > 1 ? 's' : ''} found</p>
        </div>
        
        <div class="filters">
          <strong>Search Parameters:</strong>
          Query: "${searchQuery || 'All'}" • 
          Type: ${currentSearchType?.label || 'Unknown'} • 
          With Images: ${filters.hasImages ? 'Yes' : 'No'} • 
          Quality Filter: ${filters.qualityFilter} • 
          Gallery: ${filters.galleryFilter}
        </div>
        
        ${results.map(artwork => {
          const mainImage = artwork.main_picture_hd || (artwork.all_image_urls && artwork.all_image_urls[0]);
          return `
          <div class="artwork">
            <div class="artwork-content">
              ${mainImage ? `
                <div class="artwork-image">
                  <img src="${mainImage}" alt="${artwork.title || artwork.name || 'Artwork'}" onerror="this.style.display='none'" />
                </div>
              ` : ''}
              <div class="artwork-details">
                <div class="artwork-header">
                  <h3 class="artwork-title">${artwork.title || artwork.name || 'Untitled'}</h3>
                  <span class="artwork-id">${artwork.IdName || 'No ID'}</span>
                </div>
                <div class="artwork-info">
                  <div class="info-item"><span class="info-label">Artist:</span> ${artwork.artist || artwork.ArtistName || 'Unknown'}</div>
                  <div class="info-item"><span class="info-label">Year:</span> ${artwork.year || 'N/A'}</div>
                  <div class="info-item"><span class="info-label">Category:</span> ${artwork.category || artwork.Category || 'N/A'}</div>
                  <div class="info-item"><span class="info-label">Medium:</span> ${(artwork.medium || artwork.Medium || 'N/A').substring(0, 80)}${(artwork.medium || artwork.Medium || '').length > 80 ? '...' : ''}</div>
                  <div class="info-item"><span class="info-label">Dimensions:</span> ${artwork.dimensions || 'N/A'}</div>
                  <div class="info-item"><span class="info-label">Location:</span> ${artwork.location || 'N/A'}</div>
                  <div class="info-item"><span class="info-label">Status:</span> ${artwork.status || 'N/A'}</div>
                  <div class="info-item"><span class="info-label">Images:</span> ${artwork.all_image_urls?.length || artwork.image_count || 0} photo${(artwork.all_image_urls?.length || artwork.image_count || 0) > 1 ? 's' : ''}</div>
                </div>
              </div>
            </div>
          </div>
        `;
        }).join('')}
        
        <div class="stats">
          <p><strong>Total: ${results.length} artwork${results.length > 1 ? 's' : ''}</strong></p>
          <p>Generated on ${currentDate} from OperaCRM database</p>
        </div>
        
        <script>
          window.onload = function() {
            window.print();
            setTimeout(() => window.close(), 1000);
          };
        </script>
      </body>
      </html>
    `;
    
    printWindow.document.write(htmlContent);
    printWindow.document.close();
  };

  const exportToJSON = () => {
    if (!results.length) return;
    
    const exportData = {
      search_info: {
        query: searchQuery,
        search_type: searchType,
        search_type_label: currentSearchType?.label,
        total_results: results.length,
        filters: filters,
        export_date: new Date().toISOString(),
        database: 'OperaCRM'
      },
      artworks: results.map(artwork => ({
        id: artwork.IdName,
        title: artwork.title || artwork.name,
        artist: artwork.artist || artwork.ArtistName,
        year: artwork.year,
        category: artwork.category || artwork.Category,
        medium: artwork.medium || artwork.Medium,
        dimensions: artwork.dimensions,
        location: artwork.location,
        status: artwork.status,
        image_count: artwork.all_image_urls?.length || artwork.image_count || 0,
        image_urls: artwork.all_image_urls || [],
        main_image: artwork.main_picture_hd
      }))
    };
    
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const link = document.createElement('a');
    const searchInfo = searchQuery ? `_${searchQuery.replace(/[^a-zA-Z0-9]/g, '_')}` : '';
    link.href = URL.createObjectURL(blob);
    link.download = `operagallery_search${searchInfo}_${new Date().toISOString().split('T')[0]}.json`;
    link.click();
  };

  return (
    <div className="min-h-screen bg-white py-8 px-4">
      <div className="max-w-7xl mx-auto">
        
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-black mb-4">
            🎨 OperaGallery Search
          </h1>
          <p className="text-gray-600 text-lg">
            Explore the artwork collection from the OperaGallery database
          </p>
        </div>

        {/* Search Interface */}
        <div className="bg-white rounded-xl shadow-lg border-2 border-gray-300 p-6 mb-8">
          
          {/* Search Type Selector */}
          <div className="mb-6">
            <div className="flex flex-wrap gap-2 justify-center">
              {searchTypes.map((type) => (
                <button
                  key={type.value}
                  onClick={() => setSearchType(type.value)}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all ${
                    searchType === type.value
                      ? 'bg-black text-white shadow-lg scale-105'
                      : 'bg-white border-2 border-gray-400 text-black hover:bg-gray-100'
                  }`}
                >
                  {type.label}
                </button>
              ))}
            </div>
          </div>

          {/* Search Bar */}
          <form onSubmit={handleSearchSubmit} className="relative mb-4">
            <div className="flex items-center">
              <div className="relative flex-1">
                <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={currentSearchType?.placeholder}
                  className="w-full text-lg py-4 pl-12 pr-4 border-2 border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-black focus:border-black"
                />
              </div>
{/* Filters button hidden
              <button
                type="button"
                onClick={() => setShowFilters(!showFilters)}
                className={`ml-3 px-4 py-4 rounded-xl border-2 transition-all ${
                  showFilters 
                    ? 'bg-black text-white border-black' 
                    : 'border-gray-400 text-black hover:bg-gray-100'
                }`}
              >
                <Filter className="h-5 w-5" />
              </button> */}

              <button
                type="submit"
                disabled={loading}
                className="ml-3 px-6 py-4 bg-black text-white rounded-xl hover:bg-gray-800 disabled:opacity-50 transition-all"
              >
                {loading ? <Loader className="h-5 w-5 animate-spin" /> : 'Search'}
              </button>
            </div>
          </form>

          {/* Advanced Filters */}
          {showFilters && (
            <div className="bg-gray-50 rounded-xl p-4 border-2 border-gray-300 mt-4">
              <h3 className="font-semibold text-black mb-3 flex items-center">
                <Filter className="h-4 w-4 mr-2" />
                Advanced OperaCRM filters
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
                <div>
                  <label className="block text-sm font-medium text-black mb-1">
                    <Zap className="inline w-4 h-4 mr-1" />
                    Stock status
                  </label>
                  <select
                    value={filters.stockFilter}
                    onChange={(e) => setFilters({...filters, stockFilter: e.target.value})}
                    className="w-full py-2 px-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-black"
                  >
                    <option value="all">📦 All statuses</option>
                    <option value="in_stock">✅ In stock</option>
                    <option value="in_transit">🚚 In transit</option>
                    <option value="available">📦 Available (In stock + In transit)</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-black mb-1">
                    🏛️ Gallery
                  </label>
                  <select
                    value={filters.galleryFilter}
                    onChange={(e) => setFilters({...filters, galleryFilter: e.target.value})}
                    className="w-full py-2 px-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-black"
                  >
                    <option value="all">🏛️ All galleries</option>
                    {availableGalleries.map(gallery => (
                      <option key={typeof gallery === 'object' ? gallery.id : gallery} value={typeof gallery === 'object' ? gallery.id : gallery}>
                        📍 {typeof gallery === 'object' ? gallery.name : gallery}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-black mb-1">
                    <Camera className="inline w-4 h-4 mr-1" />
                    A5 print quality
                  </label>
                  <select
                    value={filters.qualityFilter}
                    onChange={(e) => setFilters({...filters, qualityFilter: e.target.value})}
                    className="w-full py-2 px-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-black"
                  >
                    <option value="all">🔍 All qualities</option>
                    <option value="excellent">🟢 Excellent (300+ DPI)</option>
                    <option value="good">🟢 Good (200+ DPI)</option>
                    <option value="acceptable">🟠 Acceptable (150+ DPI)</option>
                    <option value="poor">🔴 Insufficient (less than 150 DPI)</option>
                    <option value="no_image">⚪ No image</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-black mb-1">
                    <Bookmark className="inline w-4 h-4 mr-1" />
                    Marked photos
                  </label>
                  <select
                    value={filters.markedFilter}
                    onChange={(e) => setFilters({...filters, markedFilter: e.target.value})}
                    className="w-full py-2 px-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-black"
                  >
                    <option value="all">📋 All photos</option>
                    <option value="marked">🔖 Marked for processing ({markedArtworks.size})</option>
                    <option value="unmarked">📄 Unmarked</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-black mb-1">
                    📂 Category
                  </label>
                  <input
                    type="text"
                    value={filters.category}
                    onChange={(e) => setFilters({...filters, category: e.target.value})}
                    placeholder="Painting, Sculpture, Photography..."
                    className="w-full py-2 px-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-black"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-black mb-1">
                    🎭 Medium
                  </label>
                  <input
                    type="text"
                    value={filters.medium}
                    onChange={(e) => setFilters({...filters, medium: e.target.value})}
                    placeholder="oil on canvas, Bronze, Acrylic..."
                    className="w-full py-2 px-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-black"
                  />
                </div>
              </div>
              <div className="mt-4">
                <label className="flex items-center text-black">
                  <input
                    type="checkbox"
                    checked={filters.hasImages}
                    onChange={(e) => setFilters({...filters, hasImages: e.target.checked})}
                    className="mr-2"
                  />
                  With images only
                </label>
              </div>
            </div>
          )}
        </div>

        {/* Results Header */}
        {(results.length > 0 || loading) && (
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center">
              <h2 className="text-xl font-semibold text-black mr-4">
                {loading ? 'OperaCRM search in progress...' : `${totalResults} artwork${totalResults > 1 ? 's' : ''} found in OperaCRM`}
              </h2>
              {searchQuery && (
                <span className="bg-gray-100 border border-gray-400 text-black px-3 py-1 rounded-full text-sm">
                  "{searchQuery}"
                </span>
              )}
            </div>
            
            <div className="flex items-center gap-2">
              {/* Export Buttons */}
              {!loading && results.length > 0 && (
                <div className="flex items-center gap-2 mr-4">
                  <div className="relative group">
                    <button className="bg-green-600 text-white px-3 py-2 rounded-lg hover:bg-green-700 transition-colors flex items-center gap-2">
                      <Download className="h-4 w-4" />
                      Export
                      <ChevronDown className="h-3 w-3" />
                    </button>
                    <div className="absolute right-0 top-full mt-1 bg-white border-2 border-gray-300 rounded-lg shadow-lg z-50 min-w-48 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all">
                      <button
                        onClick={exportToCSV}
                        className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center gap-3 border-b border-gray-100"
                      >
                        <Table className="h-4 w-4 text-green-600" />
                        <div>
                          <div className="font-medium text-black">CSV Export</div>
                          <div className="text-xs text-gray-500">Spreadsheet format for Excel</div>
                        </div>
                      </button>
                      <button
                        onClick={exportToPDF}
                        className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center gap-3 border-b border-gray-100"
                      >
                        <FileText className="h-4 w-4 text-red-600" />
                        <div>
                          <div className="font-medium text-black">PDF Report</div>
                          <div className="text-xs text-gray-500">Beautiful report with photos</div>
                        </div>
                      </button>
                      <button
                        onClick={exportToJSON}
                        className="w-full px-4 py-3 text-left hover:bg-gray-50 flex items-center gap-3 rounded-b-lg"
                      >
                        <FileImage className="h-4 w-4 text-blue-600" />
                        <div>
                          <div className="font-medium text-black">JSON Data</div>
                          <div className="text-xs text-gray-500">Raw data with image URLs</div>
                        </div>
                      </button>
                    </div>
                  </div>
                </div>
              )}
              
              {/* View Mode Buttons */}
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded-lg ${viewMode === 'grid' ? 'bg-black text-white' : 'bg-white border-2 border-gray-400 text-black'}`}
              >
                <Grid className="h-5 w-5" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded-lg ${viewMode === 'list' ? 'bg-black text-white' : 'bg-white border-2 border-gray-400 text-black'}`}
              >
                <List className="h-5 w-5" />
              </button>
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="bg-white border-2 border-red-500 rounded-xl p-4 mb-6 flex items-center">
            <AlertCircle className="h-5 w-5 text-red-500 mr-3" />
            <span className="text-black">{error}</span>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <Loader className="h-12 w-12 text-black animate-spin mx-auto mb-4" />
            <p className="text-black">Search in progress in OperaGallery...</p>
          </div>
        )}

        {/* Results Grid */}
        {!loading && results.length > 0 && (
          <div className={`grid gap-6 mb-8 ${
            viewMode === 'grid' 
              ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4' 
              : 'grid-cols-1'
          }`}>
            {results.map((artwork) => (
              <ArtworkCard 
                key={artwork.id || artwork.IdName} 
                artwork={artwork} 
                viewMode={viewMode}
                onView={() => openArtworkModal(artwork)}
                getQualityIcon={getQualityIcon}
                toggleMarkArtwork={toggleMarkArtwork}
                isMarked={markedArtworks.has(String(artwork.IdName || artwork.id || 'NO_ID'))}
                analyzeDetailedQuality={analyzeDetailedQuality}
                analyzingQuality={analyzingQuality}
                detailedQuality={detailedQuality}
              />
            ))}
          </div>
        )}

        {/* No Results */}
        {!loading && searchQuery && results.length === 0 && (
          <div className="text-center py-12">
            <ImageIcon className="h-24 w-24 text-secondary mx-auto mb-4" />
            <h3 className="text-xl font-elegant font-semibold text-primary mb-2">No results found</h3>
            <p className="text-secondary font-body">
              Try different terms or use advanced filters
            </p>
          </div>
        )}

        {/* Pagination */}
        {!loading && results.length > 0 && totalResults > 100 && (
          <div className="flex justify-center">
            <Pagination 
              currentPage={currentPage}
              totalPages={Math.ceil(totalResults / 100)}
              onPageChange={(page) => performSearch(searchQuery, page)}
            />
          </div>
        )}
      </div>

      {/* Artwork Modal */}
      {selectedArtwork && (
        <ArtworkModal 
          artwork={selectedArtwork} 
          onClose={closeArtworkModal} 
        />
      )}
    </div>
  );
};

// Artwork Card Component - OperaCRM Data
const ArtworkCard = ({ artwork, viewMode, onView, getQualityIcon, toggleMarkArtwork, isMarked, analyzeDetailedQuality, analyzingQuality, detailedQuality }) => {
  const mainImage = artwork.main_picture_hd || (artwork.all_image_urls && artwork.all_image_urls[0]);
  const imageCount = artwork.image_count || (artwork.all_image_urls ? artwork.all_image_urls.length : 0);
  // Ensure artworkId is always a string
  const artworkId = String(artwork.IdName || artwork.id || 'NO_ID');
  const qualityData = detailedQuality[artworkId] || artwork.quality_analysis;
  
  // Image data processed

  if (viewMode === 'list') {
    return (
      <div className="bg-white rounded-xl shadow-lg border-2 border-gray-300 overflow-hidden hover:shadow-xl transition-shadow">
        <div className="flex">
          <div className="w-48 h-32 flex-shrink-0">
            {mainImage ? (
              <img 
                src={mainImage} 
                alt={artwork.title || artwork.IdName}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzlmYTZiNyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlPC90ZXh0Pjwvc3ZnPg==';
                }}
              />
            ) : (
              <div className="w-full h-full bg-gray-100 flex items-center justify-center">
                <ImageIcon className="h-8 w-8 text-gray-400" />
              </div>
            )}
          </div>
          <div className="flex-1 p-4">
            <div className="flex justify-between items-start mb-2">
              <div className="flex items-center space-x-2">
                <h3 className="font-semibold text-lg text-black">{artwork.title || artwork.IdName}</h3>
                {getQualityIcon && qualityData && getQualityIcon(qualityData)}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleMarkArtwork(artworkId);
                  }}
                  className={`p-1 rounded transition-colors ${
                    isMarked 
                      ? 'bg-yellow-100 text-yellow-600 hover:bg-yellow-200' 
                      : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
                  }`}
                  title={isMarked ? "Retirer le marquage" : "Marquer pour traiter plus tard"}
                >
                  {isMarked ? <Check className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
                </button>
              </div>
              <span className="bg-gray-100 border border-gray-400 text-black px-2 py-1 rounded text-sm">
                {imageCount} photo{imageCount > 1 ? 's' : ''}
              </span>
            </div>
            <p className="text-gray-600 mb-1">{artwork.artist}</p>
            <p className="text-gray-600 text-sm mb-1">{artwork.year} • {artwork.category}</p>
            <p className="text-gray-500 text-sm mb-1">{artwork.medium}</p>
            
            {qualityData && !qualityData.error && (
              <div className="bg-blue-50 p-2 rounded text-xs mb-2">
                <div className="flex items-center justify-between mb-1">
                  <div className="font-medium text-blue-800">📐 Qualité impression A5:</div>
                  {qualityData.estimated && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        analyzeDetailedQuality(artworkId);
                      }}
                      disabled={analyzingQuality[artworkId]}
                      className="bg-blue-500 text-white px-1 py-0.5 rounded text-xs hover:bg-blue-600 disabled:opacity-50 flex items-center"
                      title="Analyse précise"
                    >
                      {analyzingQuality[artworkId] ? '⏳' : <Zap className="w-3 h-3" />}
                    </button>
                  )}
                </div>
                <div className="text-blue-700">
                  <span className="font-medium">{qualityData.equivalent_dpi_a5} DPI</span> • 
                  <span className="ml-1">{qualityData.dimensions?.width}×{qualityData.dimensions?.height}px</span> • 
                  <span className="ml-1">{qualityData.file_size_mb}MB</span>
                </div>
                <div className={`text-xs mt-1 ${
                  qualityData.color_code === 'green' ? 'text-green-600' :
                  qualityData.color_code === 'orange' ? 'text-orange-600' :
                  qualityData.color_code === 'red' ? 'text-red-600' : 'text-gray-600'
                }`}>
                  {qualityData.print_quality_a5}
                  {qualityData.estimated && <span className="text-gray-500 ml-1">(estimation)</span>}
                </div>
              </div>
            )}
            <div className="flex gap-2">
              <button
                onClick={onView}
                className="bg-black text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors"
              >
                <Eye className="h-4 w-4 inline mr-2" />
                Voir les photos
              </button>
              <span className="bg-blue-100 text-blue-800 px-2 py-2 rounded text-xs">
                ID: {artwork.IdName}
              </span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl shadow-lg border-2 border-gray-300 overflow-hidden hover:shadow-xl hover:scale-105 transition-all cursor-pointer"
         onClick={onView}>
      <div className="relative">
        {mainImage ? (
          <img 
            src={mainImage} 
            alt={artwork.title || artwork.IdName}
            className="w-full h-48 object-cover"
            onError={(e) => {
              e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzlmYTZiNyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlPC90ZXh0Pjwvc3ZnPg==';
            }}
          />
        ) : (
          <div className="w-full h-48 bg-gray-100 flex items-center justify-center">
            <ImageIcon className="h-12 w-12 text-gray-400" />
          </div>
        )}
        <div className="absolute top-2 right-2 bg-black text-white px-2 py-1 rounded text-sm">
          {imageCount} photo{imageCount > 1 ? 's' : ''}
        </div>
        <div className="absolute top-2 left-2 flex space-x-1">
          {getQualityIcon && qualityData && getQualityIcon(qualityData)}
          <button
            onClick={(e) => {
              e.stopPropagation();
              toggleMarkArtwork(artworkId);
            }}
            className={`p-1 rounded transition-colors ${
              isMarked 
                ? 'bg-yellow-100 text-yellow-600 hover:bg-yellow-200' 
                : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
            }`}
            title={isMarked ? "Retirer le marquage" : "Marquer pour traiter plus tard"}
          >
            {isMarked ? <Check className="w-3 h-3" /> : <Bookmark className="w-3 h-3" />}
          </button>
        </div>
      </div>
      <div className="p-4">
        <h3 className="font-semibold text-black mb-1 truncate">{artwork.title || artwork.IdName}</h3>
        <p className="text-gray-600 text-sm mb-1">{artwork.artist}</p>
        <p className="text-gray-500 text-xs mb-1">{artwork.year} • {artwork.category}</p>
        <p className="text-blue-600 text-xs font-mono mb-1">{artwork.IdName}</p>
        
        {/* Certificate Information */}
        {artwork.filemakerData?.CertificateFMUrl && (
          <div className="bg-green-50 border border-green-200 rounded p-2 mb-2">
            <p className="text-green-800 text-xs font-medium mb-1">📜 Certificate:</p>
            <a 
              href={artwork.filemakerData.CertificateFMUrl} 
              target="_blank" 
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-green-600 hover:text-green-800 underline text-xs"
            >
              View PDF Certificate
            </a>
            {artwork.filemakerData?.CertificateWording && (
              <p className="text-green-700 text-xs mt-1 italic">
                {artwork.filemakerData.CertificateWording.length > 80 
                  ? artwork.filemakerData.CertificateWording.substring(0, 80) + '...' 
                  : artwork.filemakerData.CertificateWording}
              </p>
            )}
          </div>
        )}
        
        {qualityData && !qualityData.error && (
          <div className="bg-blue-50 p-1 rounded text-xs">
            <div className="flex items-center justify-between">
              <div className="font-medium text-blue-800">📐 A5: {qualityData.equivalent_dpi_a5} DPI</div>
              {qualityData.estimated && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    analyzeDetailedQuality(artworkId);
                  }}
                  disabled={analyzingQuality[artworkId]}
                  className="bg-blue-500 text-white px-0.5 py-0.5 rounded text-xs hover:bg-blue-600 disabled:opacity-50"
                  title="Analyse précise"
                >
                  {analyzingQuality[artworkId] ? '⏳' : <Zap className="w-2 h-2" />}
                </button>
              )}
            </div>
            <div className="text-blue-700">{qualityData.dimensions?.width}×{qualityData.dimensions?.height}</div>
            {qualityData.estimated && <div className="text-gray-500 text-xs">(estimation)</div>}
          </div>
        )}
      </div>
    </div>
  );
};

// Artwork Modal Component
const ArtworkModal = ({ artwork, onClose }) => {
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [editingCategory, setEditingCategory] = useState(false);
  const [newCategory, setNewCategory] = useState(artwork.category || '');
  const images = artwork.all_image_urls || (artwork.main_picture_hd ? [artwork.main_picture_hd] : []);

  // Derive per-image label
  const currentImageUrl = images[currentImageIndex] || '';
  const imageLabels = artwork.image_labels || {};
  const currentLabel = imageLabels[currentImageUrl] || '';
  const headerTitle = currentLabel
    ? `${artwork.title || artwork.IdName} - ${currentLabel}`
    : (artwork.title || artwork.IdName);

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl border-2 border-gray-300 max-w-6xl w-full max-h-[90vh] overflow-hidden">
        
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b-2 border-gray-300">
          <div>
            <h2 className="text-2xl font-bold text-black">{headerTitle}</h2>
            <p className="text-gray-600">{artwork.artist} • {artwork.year}</p>
            <p className="text-blue-600 text-sm font-mono mt-1">OperaCRM ID: {artwork.IdName}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors text-black"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex flex-col lg:flex-row">
          
          {/* Image Display */}
          <div className="lg:w-2/3 p-6">
            {images.length > 0 ? (
              <div>
                <div className="mb-4">
                  <img 
                    src={images[currentImageIndex]} 
                    alt={`${artwork.title || artwork.IdName} - Image ${currentImageIndex + 1}`}
                    className="w-full max-h-96 object-contain bg-gray-50 rounded-lg"
                    onError={(e) => {
                      e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNTAwIiBoZWlnaHQ9IjMwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNiIgZmlsbD0iIzlmYTZiNyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vbiBkaXNwb25pYmxlPC90ZXh0Pjwvc3ZnPg==';
                    }}
                  />
                </div>
                
                {images.length > 1 && (
                  <div className="grid grid-cols-4 md:grid-cols-6 gap-2">
                    {images.map((image, index) => (
                      <button
                        key={index}
                        onClick={() => setCurrentImageIndex(index)}
                        className={`aspect-square rounded overflow-hidden border-2 transition-all ${
                          index === currentImageIndex 
                            ? 'border-blue-500 ring-2 ring-blue-200' 
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <img 
                          src={image} 
                          alt={`Miniature ${index + 1}`}
                          className="w-full h-full object-cover"
                          onError={(e) => {
                            e.target.style.display = 'none';
                          }}
                        />
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-gray-100 rounded-lg h-96 flex items-center justify-center">
                <div className="text-center text-secondary">
                  <ImageIcon className="h-16 w-16 mx-auto mb-2" />
                  <p className="font-body">Noe image disponible</p>
                </div>
              </div>
            )}
          </div>

          {/* Artwork Info */}
          <div className="lg:w-1/3 p-6 bg-gray-50">
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-black mb-2">Informations OperaCRM</h3>
                <div className="space-y-2 text-sm">
                  <p className="text-black"><span className="font-medium">ID:</span> {artwork.IdName}</p>
                  <p className="text-black"><span className="font-medium">Titre:</span> {artwork.title}</p>
                  <p className="text-black"><span className="font-medium">Artiste:</span> {artwork.artist}</p>
                  <p className="text-black"><span className="font-medium">Année:</span> {artwork.year}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-black">
                      <span className="font-medium">Catégorie:</span>
                      {editingCategory ? (
                        <select
                          value={newCategory}
                          onChange={(e) => setNewCategory(e.target.value)}
                          className="ml-2 px-2 py-1 border rounded text-sm"
                        >
                          <option value="Painting">Painting</option>
                          <option value="Sculpture">Sculpture</option>
                          <option value="Drawing">Drawing</option>
                          <option value="Print">Print</option>
                          <option value="Photography">Photography</option>
                          <option value="Mixed Media">Mixed Media</option>
                          <option value="Digital Art">Digital Art</option>
                          <option value="Installation">Installation</option>
                          <option value="Other">Other</option>
                        </select>
                      ) : (
                        <span className="ml-1">{artwork.category}</span>
                      )}
                    </span>
                    <div className="flex space-x-1">
                      {editingCategory ? (
                        <>
                          <button
                            onClick={() => {
                              // TODO: Implement save category
                              // Category saved
                              setEditingCategory(false);
                            }}
                            className="text-green-600 hover:text-green-800 text-xs"
                            title="Sauvegarder"
                          >
                            ✓
                          </button>
                          <button
                            onClick={() => {
                              setNewCategory(artwork.category || '');
                              setEditingCategory(false);
                            }}
                            className="text-red-600 hover:text-red-800 text-xs"
                            title="Annuler"
                          >
                            ✗
                          </button>
                        </>
                      ) : (
                        <button
                          onClick={() => setEditingCategory(true)}
                          className="text-blue-600 hover:text-blue-800 text-xs"
                          title="Modifier catégorie"
                        >
                          ✏️
                        </button>
                      )}
                    </div>
                  </div>
                  <p className="text-black"><span className="font-medium">Medium:</span> {artwork.medium}</p>
                  <p className="text-black"><span className="font-medium">Dimensions:</span> {artwork.dimensions}</p>
                  <p className="text-black"><span className="font-medium">Location:</span> {artwork.location}</p>
                  <p className="text-black"><span className="font-medium">Status:</span> {artwork.status}</p>
                </div>
              </div>

              {artwork.description && (
                <div>
                  <h3 className="font-semibold text-black mb-2">Description</h3>
                  <p className="text-sm text-gray-600">{artwork.description}</p>
                </div>
              )}

              {(artwork.provenance || artwork.exhibited) && (
                <div>
                  <h3 className="font-semibold text-black mb-2">Provenance & Expositions</h3>
                  {artwork.provenance && (
                    <p className="text-sm text-gray-600 mb-2"><span className="font-medium">Provenance:</span> {artwork.provenance}</p>
                  )}
                  {artwork.exhibited && (
                    <p className="text-sm text-gray-600"><span className="font-medium">Exposé:</span> {artwork.exhibited}</p>
                  )}
                </div>
              )}

              <div>
                <h3 className="font-semibold text-black mb-2">Photos</h3>
                <p className="text-sm text-gray-600">
                  {images.length} image{images.length > 1 ? 's' : ''} disponible{images.length > 1 ? 's' : ''}
                </p>
                {images.length > 1 && (
                  <p className="text-xs text-gray-500 mt-1">
                    Image {currentImageIndex + 1} sur {images.length}
                  </p>
                )}
                {currentImageUrl && (
                  <div className="flex items-center gap-1 mt-2">
                    <input
                      type="text"
                      readOnly
                      value={currentImageUrl}
                      onClick={(e) => { e.target.select(); navigator.clipboard.writeText(e.target.value); }}
                      className="flex-1 text-xs px-2 py-1 border rounded bg-gray-50 cursor-pointer"
                      title="Click to copy URL"
                    />
                    <button
                      onClick={() => navigator.clipboard.writeText(currentImageUrl)}
                      className="p-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 flex-shrink-0"
                      title="Copy URL"
                    >
                      <Copy className="w-3 h-3" />
                    </button>
                  </div>
                )}
              </div>

              {artwork.price_estimate && (
                <div>
                  <h3 className="font-semibold text-black mb-2">Estimation</h3>
                  <p className="text-sm text-green-600 font-semibold">{artwork.price_estimate}</p>
                </div>
              )}

              {/* Certificate Information */}
              {artwork.filemakerData?.CertificateFMUrl && (
                <div>
                  <h3 className="font-semibold text-black mb-2">📜 Certificate</h3>
                  <div className="bg-green-50 border border-green-200 rounded p-3">
                    <a 
                      href={artwork.filemakerData.CertificateFMUrl} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-green-600 hover:text-green-800 underline text-sm font-medium"
                    >
                      📄 View PDF Certificate
                    </a>
                    {artwork.filemakerData?.CertificateWording && (
                      <div className="mt-2">
                        <p className="text-xs text-gray-600 mb-1">Certificate Information:</p>
                        <p className="text-green-700 text-sm italic">
                          {artwork.filemakerData.CertificateWording}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Pagination Component
const Pagination = ({ currentPage, totalPages, onPageChange }) => {
  const getVisiblePages = () => {
    const delta = 2;
    const range = [];
    const rangeWithDots = [];

    for (let i = Math.max(2, currentPage - delta); i <= Math.min(totalPages - 1, currentPage + delta); i++) {
      range.push(i);
    }

    if (currentPage - delta > 2) {
      rangeWithDots.push(1, '...');
    } else {
      rangeWithDots.push(1);
    }

    rangeWithDots.push(...range);

    if (currentPage + delta < totalPages - 1) {
      rangeWithDots.push('...', totalPages);
    } else {
      rangeWithDots.push(totalPages);
    }

    return rangeWithDots;
  };

  if (totalPages <= 1) return null;

  return (
    <div className="flex items-center space-x-2">
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="px-3 py-2 rounded-lg border-2 border-gray-400 text-primary font-body hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Précédent
      </button>

      {getVisiblePages().map((page, index) => (
        <button
          key={index}
          onClick={() => typeof page === 'number' && onPageChange(page)}
          disabled={page === '...'}
          className={`px-3 py-2 rounded-lg font-body ${
            page === currentPage
              ? 'bg-black text-white'
              : page === '...'
              ? 'text-secondary cursor-default'
              : 'border-2 border-gray-400 text-primary hover:bg-gray-100'
          }`}
        >
          {page}
        </button>
      ))}

      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="px-3 py-2 rounded-lg border-2 border-gray-400 text-primary font-body hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        Suivant
      </button>
    </div>
  );
};

export default ImageSearchEngine;
