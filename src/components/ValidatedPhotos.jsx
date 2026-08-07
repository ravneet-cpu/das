import React, { useState, useEffect } from 'react';
import { Search, Filter, ChevronLeft, ChevronRight, Eye, RefreshCw, CheckCircle, Calendar, X, Copy, Image as ImageIcon } from 'lucide-react';
import { PhotoDetail } from './PhotoDetail';
import { CompactArtworkSearch } from './CompactArtworkSearch';

const ValidatedPhotos = () => {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalPhotos, setTotalPhotos] = useState(0);
  const [filters, setFilters] = useState({
    status: 'validated',
    limit: 24
  });
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [userRole, setUserRole] = useState(null);
  const [artworkSearchResults, setArtworkSearchResults] = useState([]);
  const [showArtworkResults, setShowArtworkResults] = useState(false);
  const [modalArtwork, setModalArtwork] = useState(null);
  const [copiedUrl, setCopiedUrl] = useState('');
  

  // Get user role from token
  const getUserRole = () => {
    try {
      const token = localStorage.getItem('token');
      if (!token) return null;
      
      // Decode JWT token (simple base64 decode for payload)
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.role;
    } catch (error) {
      // Token decode error
      return null;
    }
  };

  useEffect(() => {
    const role = getUserRole();
    setUserRole(role);
    fetchPhotos();
  }, [currentPage, filters]);

  const fetchPhotos = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const queryParams = new URLSearchParams({
        page: currentPage,
        limit: filters.limit,
        status: 'validated'
      });

      const response = await fetch(`/api/photos/list?${queryParams}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setPhotos(data.photos || []);
      setTotalPages(data.total_pages || 1);
      setTotalPhotos(data.total || 0);
    } catch (err) {
      // Error loading validated photos
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return 'Invalid date';
    }
  };

  const getPhotoUrl = (photoId) => {
    return `/api/photos/${encodeURIComponent(photoId)}`;
  };

  const handleViewDetail = (photo) => {
    setSelectedPhoto(photo);
    setShowDetail(true);
  };

  const handleBackFromDetail = () => {
    setShowDetail(false);
    setSelectedPhoto(null);
    // Force refresh photos to get updated status after rename
    // Reset current page to 1 to ensure we see the renamed photo
    setCurrentPage(1);
    // Add small delay to ensure any pending operations complete
    setTimeout(() => {
      fetchPhotos();
    }, 100);
  };

  const handleArtworkSearchResults = (results) => {
    setArtworkSearchResults(results);
    setShowArtworkResults(results.length > 0);
  };

  const handleArtworkSearchError = (error) => {
    setError(`Search error: ${error}`);
  };

  const renderStatusBadge = (status, classification) => {
    return (
      <div className="flex items-center gap-1">
        <CheckCircle className="h-4 w-4 text-green-500" />
        <span className="text-green-600 font-medium text-sm">Validated</span>
        {classification && (
          <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium ml-1">
            {classification}
          </span>
        )}
      </div>
    );
  };

  const imagePhotos = photos.filter(p => p.file_type !== 'video');
  const videoPhotos = photos.filter(p => p.file_type === 'video');

  // Show detail view if a photo is selected
  if (showDetail && selectedPhoto) {
    return (
      <PhotoDetail
        photo={selectedPhoto}
        onBack={handleBackFromDetail}
      />
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black mx-auto mb-4"></div>
          <p className="text-black tracking-wide">Loading validated photos...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Error loading validated photos: {error}</p>
          <button 
            onClick={fetchPhotos}
            className="bg-black text-white px-4 py-2 rounded hover:bg-gray-800"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-white py-8 px-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-black mb-2">✅ Validated Photos</h1>
            <p className="text-gray-600">
              {totalPhotos} validated photo{totalPhotos !== 1 ? 's' : ''} found
            </p>
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={fetchPhotos}
              className="bg-black text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Refresh
            </button>
          </div>
        </div>

        {/* Artwork Search */}
        <CompactArtworkSearch
          onResults={handleArtworkSearchResults}
          onError={handleArtworkSearchError}
          placeholder="Search artworks by name, artist, medium, category..."
        />

        {/* Artwork Search Results */}
        {showArtworkResults && (
          <div className="bg-white border border-gray-200 rounded-lg mb-6 p-4">
            <h3 className="text-lg font-semibold mb-4">Search Results ({artworkSearchResults.length})</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {artworkSearchResults.map((artwork) => (
                <div key={artwork.id} onClick={() => setModalArtwork(artwork)}
                  className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="font-medium text-gray-900 mb-1">{artwork.title || 'No title'}</h4>
                      <p className="text-sm text-gray-600 mb-2">{artwork.artist || 'Unknown artist'}</p>
                      <div className="text-xs text-gray-500 space-y-1">
                        <p><span className="font-medium">ID:</span> {artwork.IdName}</p>
                        <p><span className="font-medium">Category:</span> {artwork.category || 'N/A'}</p>
                        <p><span className="font-medium">Medium:</span> {artwork.medium || 'N/A'}</p>
                        <p><span className="font-medium">Year:</span> {artwork.year || 'N/A'}</p>
                        {artwork.dimensions && (
                          <p><span className="font-medium">Size:</span> {artwork.dimensions}</p>
                        )}
                      </div>
                    </div>
                    {artwork.main_picture_hd && (
                      <img 
                        src={artwork.main_picture_hd} 
                        alt={artwork.title}
                        className="w-16 h-16 object-cover rounded ml-3"
                      />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Photos Grid */}
        {photos.length === 0 ? (
          <div className="text-center py-12">
            <CheckCircle className="h-24 w-24 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-600 mb-2">No validated photos yet</h3>
            <p className="text-gray-500">Photos that have been validated will appear here.</p>
          </div>
        ) : (
          <>
            {/* Enhanced Mosaic View */}
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-6">
              {imagePhotos.map((photo) => (
                <div
                  key={photo.id}
                  className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden hover:shadow-xl transition-shadow cursor-pointer group"
                  onClick={() => handleViewDetail(photo)}
                >
                  <div className="aspect-square relative overflow-hidden">
                    <img
                      src={getPhotoUrl(photo.id)}
                      alt={photo.filename}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-200"
                      onError={(e) => {
                        e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzlmYTZiNyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlPC90ZXh0Pjwvc3ZnPg==';
                      }}
                    />
                    <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 transition-opacity duration-200 flex items-center justify-center">
                      <Eye className="h-8 w-8 text-white opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
                    </div>
                    
                    {/* Double Check Button */}
                    <div className="absolute top-2 right-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          if (window.confirm('Flag this validated photo for review?')) {
                            console.log('Flagging photo for review:', photo.id);
                          }
                        }}
                        className="bg-yellow-600 hover:bg-yellow-700 text-white p-1.5 rounded-full shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-200"
                        title="Double Check - Flag for review"
                      >
                        <RefreshCw className="h-3 w-3" />
                      </button>
                    </div>
                  </div>
                  
                  <div className="p-3">
                    <div className="flex items-center justify-between mb-2">
                      {renderStatusBadge(photo.status, photo.classification)}
                    </div>
                    
                    <h3 className="font-medium text-black text-sm mb-1 truncate">
                      {photo.filename}
                    </h3>
                    
                    {/* Enhanced Information */}
                    {(photo.artwork_title || photo.artwork_id) && (
                      <div className="text-xs text-blue-600 mb-1 truncate">
                        🎨 {photo.artwork_title || photo.artwork_id}
                      </div>
                    )}
                    
                    {photo.artist_name && (
                      <div className="text-xs text-gray-600 mb-1 truncate">
                        👤 {photo.artist_name}
                      </div>
                    )}
                    
                    <div className="flex items-center text-xs text-gray-500 mb-1">
                      <Calendar className="h-3 w-3 mr-1" />
                      {formatDate(photo.validated_at || photo.created_at)}
                    </div>
                    
                    {photo.submitted_by && (
                      <div className="text-xs text-gray-600 mb-1">
                        📤 Submitted: {photo.submitted_by}
                      </div>
                    )}
                    
                    {photo.validated_by && (
                      <div className="text-xs text-green-600">
                        ✅ Validated: {photo.validated_by}
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center mt-8 space-x-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                  className="p-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                
                <div className="flex items-center space-x-1">
                  {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => {
                    let pageNum;
                    if (totalPages <= 5) {
                      pageNum = i + 1;
                    } else if (currentPage <= 3) {
                      pageNum = i + 1;
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i;
                    } else {
                      pageNum = currentPage - 2 + i;
                    }
                    
                    return (
                      <button
                        key={pageNum}
                        onClick={() => setCurrentPage(pageNum)}
                        className={`px-3 py-1 rounded-lg ${
                          currentPage === pageNum
                            ? 'bg-black text-white'
                            : 'border border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>
                
                <button
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="p-2 rounded-lg border border-gray-300 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
                
                <span className="text-sm text-gray-600 ml-4">
                  Page {currentPage} of {totalPages} ({totalPhotos} total)
                </span>
              </div>
            )}
          </>
        )}

        {/* Videos Section */}
        {videoPhotos.length > 0 && (
          <div className="mt-12">
            <h2 className="text-2xl font-bold text-black mb-6">🎬 Validated Videos ({videoPhotos.length})</h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
              {videoPhotos.map((video) => (
                <div key={video.id} className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
                  <div className="aspect-video bg-black relative">
                    <video
                      controls
                      preload="metadata"
                      className="w-full h-full object-contain"
                      src={getPhotoUrl(video.id)}
                    >
                      Your browser does not support video.
                    </video>
                  </div>
                  <div className="p-3">
                    <div className="flex items-center gap-1 mb-2">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-green-600 font-medium text-sm">Validated</span>
                      {video.classification && (
                        <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-xs font-medium ml-1">
                          {video.classification}
                        </span>
                      )}
                    </div>
                    <h3 className="font-medium text-black text-sm mb-1 truncate" title={video.filename}>
                      {video.filename}
                    </h3>
                    {video.artwork_id && (
                      <div className="text-xs text-blue-600 mb-1">🎨 {video.artwork_id}</div>
                    )}
                    <div className="flex items-center text-xs text-gray-500 mb-1">
                      <Calendar className="h-3 w-3 mr-1" />
                      {formatDate(video.validated_at || video.created_at)}
                    </div>
                    {video.validated_by && (
                      <div className="text-xs text-green-600">✅ Validated: {video.validated_by}</div>
                    )}
                    <div className="mt-2">
                      <a
                        href={video.streaming_url || `https://images.operagallery.com/video/${encodeURIComponent(video.filename)}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-blue-500 hover:underline break-all"
                      >
                        Open in Odoo/FM URL ↗
                      </a>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

      </div>

      {/* Artwork Detail Modal */}
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
              {(modalArtwork.all_image_urls?.length > 0) ? (
                <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                  {modalArtwork.all_image_urls.map((url, i) => (
                    <div key={i} className="border rounded-lg overflow-hidden bg-gray-50">
                      <img src={url} className="w-full h-32 object-cover" onError={e => e.target.style.display='none'} />
                      <div className="p-2 flex items-center gap-1">
                        <input type="text" readOnly value={url} className="flex-1 text-xs px-1 py-1 border rounded bg-white truncate"
                          onClick={e => { e.target.select(); navigator.clipboard.writeText(e.target.value); setCopiedUrl(url); setTimeout(() => setCopiedUrl(''), 2000); }} />
                        <button onClick={() => { navigator.clipboard.writeText(url); setCopiedUrl(url); setTimeout(() => setCopiedUrl(''), 2000); }}
                          className="p-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 flex-shrink-0">
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

export default ValidatedPhotos;