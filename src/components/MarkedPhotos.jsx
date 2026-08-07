import React, { useState, useEffect } from 'react';
import apiService from '../services/apiService';

const MarkedPhotos = () => {
  const [markedPhotos, setMarkedPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [selectedPhoto, setSelectedPhoto] = useState(null);

  useEffect(() => {
    fetchMarkedPhotos();
  }, [page]);

  const fetchMarkedPhotos = async () => {
    try {
      setLoading(true);
      const response = await apiService.getMarkedPhotos(page, 20);
      
      if (response.success) {
        setMarkedPhotos(response.marked_photos);
        setTotalPages(response.total_pages);
        setError(null);
      } else {
        setError('Error loading marked photos');
      }
    } catch (err) {
      setError(`Error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUnmark = async (photoId) => {
    try {
      const response = await apiService.unmarkPhoto(photoId);
      if (response.success) {
        // Remove from list immediately for better UX
        setMarkedPhotos(prev => prev.filter(p => p.photo_id !== photoId));
      }
    } catch (err) {
      console.error('Error unmarking photo:', err);
    }
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    return new Date(dateString).toLocaleString('fr-FR');
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      'pending': { color: 'bg-yellow-500', text: 'Pending' },
      'validated': { color: 'bg-green-500', text: 'Validated' },
      'rejected': { color: 'bg-red-500', text: 'Rejected' }
    };
    
    const config = statusConfig[status] || { color: 'bg-gray-500', text: status || 'Unknown' };
    
    return (
      <span className={`px-2 py-1 rounded text-white text-xs ${config.color}`}>
        {config.text}
      </span>
    );
  };

  if (loading && page === 1) {
    return (
      <div className="flex justify-center items-center min-h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
        {error}
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">
          My Marked Photos ({markedPhotos.length} photos)
        </h1>
        <button
          onClick={fetchMarkedPhotos}
          className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded"
        >
          Refresh
        </button>
      </div>

      {markedPhotos.length === 0 ? (
        <div className="text-center py-12">
          <div className="text-gray-500 text-lg mb-4">
             No marked photos
          </div>
          <p className="text-gray-400">
            Use the star on photos to mark them and find them here
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {markedPhotos.map((photo) => (
            <div
              key={photo.photo_id}
              className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow"
            >
              <div className="relative">
                <img
                  src={apiService.getPhotoUrl(photo.photo_id, 300)}
                  alt={photo.photo_filename}
                  className="w-full h-48 object-cover cursor-pointer"
                  onClick={() => setSelectedPhoto(photo)}
                  onError={(e) => {
                    e.target.src = '/placeholder-image.png';
                  }}
                />
                <button
                  onClick={() => handleUnmark(photo.photo_id)}
                  className="absolute top-2 right-2 bg-white rounded-full p-1 shadow-md hover:bg-gray-100"
                 title="Remove mark"
                >
                  <svg className="w-5 h-5 text-yellow-500 fill-current" viewBox="0 0 24 24">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  </svg>
                </button>
              </div>

              <div className="p-4">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-medium text-gray-800 truncate flex-1">
                    {photo.photo_filename || photo.photo_id}
                  </h3>
                  {photo.status && getStatusBadge(photo.status)}
                </div>

                {photo.classification && (
                  <div className="text-sm text-gray-600 mb-2">
                    <span className="font-medium">Classification:</span> {photo.classification}
                  </div>
                )}

                {photo.note && (
                  <div className="text-sm text-gray-600 mb-2">
                    <span className="font-medium">Note:</span> {photo.note}
                  </div>
                )}

                {photo.reject_reason && (
                  <div className="text-sm text-red-600 mb-2">
                    <span className="font-medium">Rejection reason:</span> {photo.reject_reason}
                  </div>
                )}

                <div className="text-xs text-gray-500 mt-2">
                  Marked on {formatDate(photo.marked_at)}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center items-center space-x-2 mt-8">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="px-3 py-2 bg-gray-200 text-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-300"
          >
            Previous
          </button>
          
          <span className="px-4 py-2 text-gray-700">
            Page {page} of {totalPages}
          </span>
          
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="px-3 py-2 bg-gray-200 text-gray-700 rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-300"
          >
            Next
          </button>
        </div>
      )}

      {/* Photo Detail Modal */}
      {selectedPhoto && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl max-h-full overflow-auto">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-xl font-bold">
                {selectedPhoto.photo_filename || selectedPhoto.photo_id}
              </h2>
              <button
                onClick={() => setSelectedPhoto(null)}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ×
              </button>
            </div>
            
            <div className="p-4">
              <img
                src={apiService.getPhotoUrl(selectedPhoto.photo_id)}
                alt={selectedPhoto.photo_filename}
                className="max-w-full max-h-96 mx-auto object-contain"
                onError={(e) => {
                  e.target.src = '/placeholder-image.png';
                }}
              />
              
              <div className="mt-4 space-y-2">
                {selectedPhoto.status && (
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">Status:</span>
                    {getStatusBadge(selectedPhoto.status)}
                  </div>
                )}
                
                {selectedPhoto.classification && (
                  <div>
                    <span className="font-medium">Classification:</span> {selectedPhoto.classification}
                  </div>
                )}
                
                {selectedPhoto.note && (
                  <div>
                    <span className="font-medium">Note:</span> {selectedPhoto.note}
                  </div>
                )}
                
                {selectedPhoto.reject_reason && (
                  <div className="text-red-600">
			<span className="font-medium">Rejection reason:</span> {selectedPhoto.reject_reason}
                  </div>
                )}
                
                <div className="text-sm text-gray-500">
		  Marked on {formatDate(selectedPhoto.marked_at)}
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MarkedPhotos;
