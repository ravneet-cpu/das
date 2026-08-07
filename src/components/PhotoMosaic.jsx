import React, { useState, useEffect } from 'react';
import { ThumbsUp, ThumbsDown, AlertTriangle, Clock, FileText, Image, Star } from 'lucide-react';
import apiService from '../services/apiService';

const PhotoMosaic = ({ status = 'pending', onPhotoSelect, onValidatePhoto, onRejectPhoto }) => {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [photoToReject, setPhotoToReject] = useState(null);
  const [rejectReason, setRejectReason] = useState('');
  const [customReason, setCustomReason] = useState('');
  const [showValidateModal, setShowValidateModal] = useState(false);
  const [photoToValidate, setPhotoToValidate] = useState(null);
  const [classification, setClassification] = useState('');
  const [markedPhotos, setMarkedPhotos] = useState(new Set());

  const rejectReasons = [
    'Poor photo quality',
    'Bad lighting',
    'Blurry photo',
    'Poor framing',
    'Reflections on artwork',
    'Partially visible artwork',
    'Color issues',
    'Inappropriate format',
    'Incorrect filename',
    'Artwork not found in database',
    'Duplicate artwork detected',
    'Other (specify)'
  ];

  const classifications = [
    { value: 'MAIN', label: 'MAIN - Main image' },
    { value: 'FRAME', label: 'FRAME - Frame' },
    { value: 'DET', label: 'DET - Detail' },
    { value: 'PERS', label: 'PERS - Perspective' },
    { value: 'LEFT', label: 'LEFT - Left side' },
    { value: 'BACK', label: 'BACK - Back/Reverse' },
    { value: 'FRONTRIGHT', label: 'FRONTRIGHT - Front right' },
    { value: 'VIDEO', label: 'VIDEO - Video' },
    { value: 'INSITU', label: 'INSITU - Installation' },
    { value: 'OTHER-n', label: 'OTHER-n - Other (specify number)' }
  ];

  // Fetch photos by status
  const fetchPhotos = async () => {
    try {
      console.log(`PhotoMosaic: Fetching photos with status=${status}`);
      setLoading(true);
      setError(null);
      
      const queryParams = new URLSearchParams({
        status: status,
        limit: 100
      });
      
      const response = await fetch(`/api/photos/list?${queryParams}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      console.log(`PhotoMosaic: Response status ${response.status}`);
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}`);
      }
      
      const data = await response.json();
      console.log(`PhotoMosaic: Got ${data.photos?.length || 0} photos`);
      setPhotos(data.photos || []);
      
      // Check marked status for loaded photos
      if (data.photos && data.photos.length > 0) {
        const photoIds = data.photos.map(photo => photo.id);
        checkMarkedStatus(photoIds);
      }
      
    } catch (err) {
      console.error('PhotoMosaic: Error fetching photos:', err);
      setError(`Loading error: ${err.message}`);
    } finally {
      console.log('PhotoMosaic: Finished fetching, setting loading to false');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPhotos();
  }, [status]);

  // Check marked photos status
  const checkMarkedStatus = async (photoIds) => {
    try {
      const marked = new Set();
      for (const photoId of photoIds) {
        try {
          const response = await apiService.getMarkStatus(photoId);
          if (response.success && response.is_marked) {
            marked.add(photoId);
          }
        } catch (err) {
          console.error(`Error checking mark status for ${photoId}:`, err);
        }
      }
      setMarkedPhotos(marked);
    } catch (err) {
      console.error('Error checking marked photos:', err);
    }
  };

  // Handle photo marking
  const handleMarkPhoto = async (photoId, photoFilename) => {
    try {
      const isMarked = markedPhotos.has(photoId);
      const response = await apiService.markPhoto(photoId, photoFilename, '', isMarked ? 'unmark' : 'mark');
      
      if (response.success) {
        setMarkedPhotos(prev => {
          const newSet = new Set(prev);
          if (isMarked) {
            newSet.delete(photoId);
          } else {
            newSet.add(photoId);
          }
          return newSet;
        });
      }
    } catch (err) {
      console.error('Error marking photo:', err);
    }
  };

  // Handle photo selection (no popup)
  const handlePhotoClick = (photo) => {
    setSelectedPhoto(photo);
    // Don't show details popup, just select the photo
    if (onPhotoSelect) {
      onPhotoSelect(photo);
    }
  };

  // Handle photo validation - show classification popup for small buttons
  const handleValidateClick = (photo) => {
    console.log('PhotoMosaic handleValidateClick called with photo:', photo);
    setPhotoToValidate(photo);
    setShowValidateModal(true);
    setClassification('');
  };

  // Handle photo validation - open modal (for detailed validation)
  const handleValidateDetailedClick = (photo) => {
    setPhotoToValidate(photo);
    setShowValidateModal(true);
    setClassification('');
  };

  // Handle photo validation - confirm from modal
  const handleValidateConfirm = async () => {
    if (!photoToValidate || !classification) return;
    
    if (onValidatePhoto) {
      await onValidatePhoto(photoToValidate, classification);
      fetchPhotos(); // Refresh list
    }
    
    setShowValidateModal(false);
    setPhotoToValidate(null);
    setClassification('');
  };

  // Handle photo rejection - show reason popup for small buttons
  const handleRejectClick = (photo) => {
    console.log('PhotoMosaic handleRejectClick called with photo:', photo);
    setPhotoToReject(photo);
    setShowRejectModal(true);
    setRejectReason('');
  };

  // Handle photo rejection - open modal (for detailed rejection)
  const handleRejectDetailedClick = (photo) => {
    setPhotoToReject(photo);
    setShowRejectModal(true);
    setRejectReason('');
    setCustomReason('');
  };

  // Handle photo rejection - confirm from modal
  const handleRejectConfirm = async () => {
    if (!photoToReject || !rejectReason) return;

    const finalReason = rejectReason === 'Other (specify)' ? customReason : rejectReason;
    
    if (onRejectPhoto) {
      await onRejectPhoto(photoToReject, finalReason);
      fetchPhotos(); // Refresh list
    }
    
    setShowRejectModal(false);
    setPhotoToReject(null);
    setRejectReason('');
    setCustomReason('');
  };

  // Get image URL
  const getImageUrl = (photo) => {
    if (!photo) return '';
    return `/api/photos/${encodeURIComponent(photo.id)}`;
  };

  // Get status color
  const getStatusColor = (photoStatus) => {
    switch (photoStatus) {
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'validated': return 'bg-green-100 text-green-800';
      case 'rejected': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  // Get status icon
  const getStatusIcon = (photoStatus) => {
    switch (photoStatus) {
      case 'pending': return <Clock className="w-4 h-4" />;
      case 'validated': return <ThumbsUp className="w-4 h-4" />;
      case 'rejected': return <ThumbsDown className="w-4 h-4" />;
      default: return <FileText className="w-4 h-4" />;
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading photos...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
        <div className="flex items-center">
          <AlertTriangle className="h-5 w-5 text-red-400 mr-2" />
          <span className="text-red-800">{error}</span>
        </div>
      </div>
    );
  }

  if (photos.length === 0) {
    return (
      <div className="text-center py-12">
        <Image className="h-16 w-16 mx-auto mb-4 text-gray-400" />
        <p className="text-gray-600 text-lg">No {status} photos found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900 capitalize">
          {status} Photos ({photos.length})
        </h2>
        <button
          onClick={fetchPhotos}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Photo Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {photos.map((photo) => (
          <div
            key={photo.id}
            className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow cursor-pointer"
            onClick={() => handlePhotoClick(photo)}
          >
            {/* Photo */}
            <div className="aspect-square bg-gray-100 relative">
              <img
                src={getImageUrl(photo)}
                alt={photo.filename}
                className="w-full h-full object-cover"
                onError={(e) => {
                  e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vdCBhdmFpbGFibGU8L3RleHQ+PC9zdmc+';
                }}
              />
              
              {/* Status badge */}
              <div className={`absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-medium flex items-center ${getStatusColor(photo.status)}`}>
                {getStatusIcon(photo.status)}
                <span className="ml-1 capitalize">{photo.status}</span>
              </div>
              
              {/* Mark button */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleMarkPhoto(photo.id, photo.filename);
                }}
                className="absolute top-2 left-2 p-1 rounded-full bg-white shadow-md hover:bg-gray-100 transition-colors"
                title={markedPhotos.has(photo.id) ? 'Retirer le marquage' : 'Marquer cette photo'}
              >
                <Star 
                  className={`w-4 h-4 ${
                    markedPhotos.has(photo.id) 
                      ? 'text-yellow-500 fill-current' 
                      : 'text-gray-400'
                  }`} 
                />
              </button>
              
            </div>

            {/* Photo Info */}
            <div className="p-3">
              <div className="text-sm font-medium text-gray-900 truncate mb-1">
                {photo.filename}
              </div>
              
              {photo.artwork_id && (
                <div className="text-xs text-blue-600 font-mono mb-1">
                  {photo.artwork_id}
                </div>
              )}
              
              <div className="text-xs text-gray-500 mb-2">
                {photo.created_at ? new Date(photo.created_at).toLocaleDateString() : 'Unknown date'}
              </div>
              
              {/* Action buttons for pending photos */}
              {photo.status === 'pending' && (
                <div className="flex gap-1 mt-2">
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleValidateClick(photo);
                    }}
                    className="flex-1 px-2 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 transition-colors flex items-center justify-center"
                    title="Accept photo"
                  >
                    <ThumbsUp className="w-3 h-3 mr-1" />
                    Accept
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRejectClick(photo);
                    }}
                    className="flex-1 px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700 transition-colors flex items-center justify-center"
                    title="Reject photo"
                  >
                    <ThumbsDown className="w-3 h-3 mr-1" />
                    Reject
                  </button>
                </div>
              )}
              
              {/* Rejection reasons for rejected photos */}
              {photo.status === 'rejected' && photo.rejection_reason && (
                <div className="mt-2">
                  <div className="text-xs text-red-600 font-medium mb-1">Rejection reasons:</div>
                  <div className="text-xs text-red-500 bg-red-50 p-2 rounded">
                    {Array.isArray(photo.rejection_reason) 
                      ? photo.rejection_reason.join(', ') 
                      : photo.rejection_reason}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Validation Modal */}
      {showValidateModal && photoToValidate && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-gray-900 flex items-center">
                  <ThumbsUp className="w-5 h-5 text-green-600 mr-2" />
                  Validate Photo
                </h3>
                <button
                  onClick={() => setShowValidateModal(false)}
                  className="p-2 hover:bg-gray-100 rounded-full"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="mb-4">
                <p className="text-gray-600 text-sm mb-2">
                  Photo: <span className="font-medium">{photoToValidate.filename}</span>
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select classification:
                </label>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {classifications.map((classif) => (
                    <label key={classif.value} className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer">
                      <input
                        type="radio"
                        name="classification"
                        value={classif.value}
                        checked={classification === classif.value}
                        onChange={(e) => setClassification(e.target.value)}
                        className="mr-3 w-4 h-4 text-green-600"
                      />
                      <span className="text-sm text-gray-800">{classif.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={() => setShowValidateModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleValidateConfirm}
                  disabled={!classification}
                  className="flex-1 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Confirm Validate
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Rejection Modal */}
      {showRejectModal && photoToReject && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-bold text-gray-900 flex items-center">
                  <ThumbsDown className="w-5 h-5 text-red-600 mr-2" />
                  Reject Photo
                </h3>
                <button
                  onClick={() => setShowRejectModal(false)}
                  className="p-2 hover:bg-gray-100 rounded-full"
                >
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>

              <div className="mb-4">
                <p className="text-gray-600 text-sm mb-2">
                  Photo: <span className="font-medium">{photoToReject.filename}</span>
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select rejection reason:
                </label>
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {rejectReasons.map((reason) => (
                    <label key={reason} className="flex items-center p-2 hover:bg-gray-50 rounded cursor-pointer">
                      <input
                        type="radio"
                        name="rejectReason"
                        value={reason}
                        checked={rejectReason === reason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        className="mr-3 w-4 h-4 text-red-600"
                      />
                      <span className="text-sm text-gray-800">{reason}</span>
                    </label>
                  ))}
                </div>
              </div>

              {rejectReason === 'Other (specify)' && (
                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Custom reason:
                  </label>
                  <textarea
                    value={customReason}
                    onChange={(e) => setCustomReason(e.target.value)}
                    placeholder="Enter custom rejection reason..."
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-red-500"
                    rows="3"
                  />
                </div>
              )}

              <div className="flex gap-2">
                <button
                  onClick={() => setShowRejectModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleRejectConfirm}
                  disabled={!rejectReason || (rejectReason === 'Other (specify)' && !customReason.trim())}
                  className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Confirm Reject
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default PhotoMosaic;