import React, { useState, useEffect } from 'react';
import { Search, Filter, ChevronLeft, ChevronRight, Eye, RefreshCw, ThumbsUp, ThumbsDown, Edit, Star } from 'lucide-react';
import { PhotoDetail } from './PhotoDetail';
import apiService from '../services/apiService';

const PhotoGrid = () => {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalPhotos, setTotalPhotos] = useState(0);
  const [filters, setFilters] = useState({
    status: 'rejected',
    limit: 24
  });
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [validationLoading, setValidationLoading] = useState({});
  const [showClassificationModal, setShowClassificationModal] = useState(false);
  const [pendingValidationPhoto, setPendingValidationPhoto] = useState(null);
  const [classification, setClassification] = useState('');
  const [userRole, setUserRole] = useState(null);
  const [markedPhotos, setMarkedPhotos] = useState(new Set());

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

  // Check if user can validate photos (admin or validator)
  const canValidatePhotos = () => {
    return userRole === 'admin' || userRole === 'validator';
  };

  // Fetch photos from backend
  const fetchPhotos = async (page = 1) => {
    try {
      setLoading(true);
      setError(null);
      
      const params = new URLSearchParams({
        page: page.toString(),
        limit: filters.limit.toString()
      });
      
      if (filters.status) {
        params.append('status', filters.status);
      }
      
      const response = await fetch(`/api/photos/list?${params}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
	throw new Error(`Error ${response.status}`);
      }
      
      const data = await response.json();
      // Photos data loaded
      
      setPhotos(data.photos || []);
      setCurrentPage(page);
      setTotalPages(data.total_pages || 1);
      setTotalPhotos(data.total || 0);
      
      // Check marked status for loaded photos
      if (data.photos && data.photos.length > 0) {
        const photoIds = data.photos.map(photo => photo.id);
        checkMarkedStatus(photoIds);
      }
      
    } catch (err) {
      // Error loading photos
      setError(`Loading error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle filter change
  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
    setCurrentPage(1); // Reset to first page when filters change
  };

  // Handle page change
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchPhotos(newPage);
    }
  };

  // Check marked photos status
  const checkMarkedStatus = async (photoIds) => {
    try {
      const marked = new Set();
      // Check each photo's mark status
      for (const photoId of photoIds) {
        try {
          const response = await apiService.getMarkStatus(photoId);
          if (response.success && response.is_marked) {
            marked.add(photoId);
          }
        } catch (err) {
          // Error checking mark status
        }
      }
      setMarkedPhotos(marked);
    } catch (err) {
      // Error loading marked photos
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
      // Error updating photo mark
    }
  };

  // Get status badge style
  const getStatusBadge = (status) => {
    const styles = {
      pending: 'bg-yellow-100 text-yellow-800',
      validated: 'bg-green-100 text-green-800',
      rejected: 'bg-red-100 text-red-800'
    };
    
    const labels = {
      pending: 'Pending',
      validated: 'Validated',
      rejected: 'Rejected'
    };
    
    return (
      <span className={`px-2 py-1 text-xs rounded-full ${styles[status] || 'bg-gray-100 text-gray-800'}`}>
        {labels[status] || status}
      </span>
    );
  };

  // Format file size
  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  // Get photo URL
  const getPhotoUrl = (photoId) => {
    return `/api/photos/${encodeURIComponent(photoId)}`;
  };

  const classifications = [
    { value: 'MAIN',          label: 'MAIN - Main image' },
    { value: 'LEFT',          label: 'LEFT - Left view' },
    { value: 'RIGHT',         label: 'RIGHT - Right view' },
    { value: 'BACK',          label: 'BACK - Back/Reverse' },
    { value: 'PERS',          label: 'PERS - Perspective' },
    { value: 'INSITU',        label: 'INSITU - In situ / Installation' },
    { value: 'EDITIONNUMBER', label: 'EDITIONNUMBER - Edition number' },
    { value: 'DET',           label: 'DET - Detail 1' },
    { value: 'DET2',          label: 'DET2 - Detail 2' },
    { value: 'OTHER',         label: 'OTHER - Other' },
    { value: 'OTHER2',        label: 'OTHER2 - Other 2 / Signatures' },
    { value: 'FRAME',         label: 'FRAME - Frame (admin only)' },
  ];

  // Handle validation request (opens classification modal for validation)
  const handleValidationRequest = (photo, decision) => {
    if (decision) {
      // For validation, show classification modal
      setPendingValidationPhoto(photo);
      setClassification('');
      setShowClassificationModal(true);
    } else {
      // For rejection, validate directly (no classification needed)
      handleDirectValidation(photo, false);
    }
  };

  // Handle direct validation with classification
  const handleDirectValidation = async (photo, decision, selectedClassification = null) => {
    if (validationLoading[photo.id]) return;
    
    try {
      setValidationLoading(prev => ({ ...prev, [photo.id]: true }));
      setError(null);
      
      const payload = {
        photoId: photo.id,
        decision: decision ? 'validate' : 'reject',
        classification: decision ? selectedClassification : undefined,
        rejectReason: decision ? undefined : 'Rejected from gallery'
      };
      
      const response = await fetch('/api/photos/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(payload)
      });
      
      if (!response.ok) {
        const errorData = await response.json();
	 throw new Error(errorData.error || `Error ${response.status}`);
      }
      
      // Refresh the current page
      fetchPhotos(currentPage);
      
    } catch (err) {
      // Validation error occurred
      setError(`Validation error: ${err.message}`);
    } finally {
      setValidationLoading(prev => ({ ...prev, [photo.id]: false }));
    }
  };

  // Handle classification submission
  const handleClassificationSubmit = () => {
    if (!classification) {
      setError('Please select a classification');
      return;
    }
    
    if (pendingValidationPhoto) {
      handleDirectValidation(pendingValidationPhoto, true, classification);
      setShowClassificationModal(false);
      setPendingValidationPhoto(null);
      setClassification('');
    }
  };

  // Handle photo detail view
  const handleViewDetail = (photo) => {
    setSelectedPhoto(photo);
    setShowDetail(true);
  };

  // Handle back from detail view
  const handleBackFromDetail = () => {
    setShowDetail(false);
    setSelectedPhoto(null);
    // Refresh photos to get updated status
    fetchPhotos(currentPage);
  };

  // Initialize user role
  useEffect(() => {
    const role = getUserRole();
    setUserRole(role);
  }, []);

  // Initialize
  useEffect(() => {
    fetchPhotos(1);
  }, [filters]);

  // If showing detail view, render PhotoDetail component
  if (showDetail && selectedPhoto) {
    return (
      <PhotoDetail
        photo={selectedPhoto}
        onBack={handleBackFromDetail}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            ❌ Rejected Photos
          </h1>
          
          {/* Filters */}
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
              
              <div className="flex flex-col sm:flex-row gap-4">
                {/* Status filter */}
                <div className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-gray-500" />
                  <select
                    value={filters.status}
                    onChange={(e) => handleFilterChange('status', e.target.value)}
                    className="border border-gray-300 rounded px-3 py-1 text-sm"
                  >
                    <option value="">All statuses</option>
                    <option value="pending">Pending</option>
                    <option value="validated">Validated</option>
                    <option value="rejected">Rejected</option>
                  </select>
                </div>
                
                {/* Limit filter */}
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600">Per page:</span>
                  <select
                    value={filters.limit}
                    onChange={(e) => handleFilterChange('limit', parseInt(e.target.value))}
                    className="border border-gray-300 rounded px-3 py-1 text-sm"
                  >
                    <option value="12">12</option>
                    <option value="24">24</option>
                    <option value="48">48</option>
                    <option value="96">96</option>
                  </select>
                </div>
              </div>
              
              <div className="flex items-center gap-4">
                <span className="text-sm text-gray-600">
                  {totalPhotos} photo{totalPhotos !== 1 ? 's' : ''} total
                </span>
                <button
                  onClick={() => fetchPhotos(currentPage)}
                  className="flex items-center gap-2 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
                >
                  <RefreshCw className="h-4 w-4" />
                  Refresh
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 mb-6">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <RefreshCw className="h-8 w-8 text-blue-500 animate-spin mx-auto mb-2" />
              <p className="text-gray-600">Loading photos...</p>
            </div>
          </div>
        )}

        {/* Photo Grid */}
        {!loading && photos.length > 0 && (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4 mb-8">
              {photos.map((photo) => (
                <div key={photo.id} className="bg-white rounded-lg shadow hover:shadow-lg transition-shadow">
                  
                  {/* Image / Video thumbnail */}
                  <div className="aspect-square bg-gray-100 rounded-t-lg overflow-hidden relative">
                    {photo.file_type === 'video' ? (
                      <div
                        className="w-full h-full flex flex-col items-center justify-center bg-gray-900 cursor-pointer hover:bg-gray-800 transition-colors"
                        onClick={() => handleViewDetail(photo)}
                      >
                        <div className="text-5xl mb-2">🎬</div>
                        <span className="text-white text-xs font-medium px-2 py-1 bg-blue-600 rounded">VIDEO</span>
                        <p className="text-gray-300 text-xs mt-2 px-2 text-center truncate w-full">{photo.filename}</p>
                      </div>
                    ) : (
                    <img
                      src={getPhotoUrl(photo.id)}
                      alt={photo.filename}
                      className="w-full h-full object-cover hover:scale-105 transition-transform cursor-pointer"
                      loading="lazy"
                      onClick={() => handleViewDetail(photo)}
                    />
                    )}
                    {/* Mark button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMarkPhoto(photo.id, photo.filename);
                      }}
                      className="absolute top-2 right-2 p-1 rounded-full bg-white shadow-md hover:bg-gray-100 transition-colors"
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
                  
                  {/* Info */}
                  <div className="p-3">
                    <div className="mb-2">
                      {getStatusBadge(photo.status)}
                    </div>
                    
                    <h3 className="font-medium text-sm text-gray-900 mb-1 truncate" title={photo.filename}>
                      {photo.filename}
                    </h3>
                    
                    <div className="text-xs text-gray-500 space-y-1">
                      <p>Size: {formatFileSize(photo.size)}</p>
                      <p title={new Date(photo.modified_at).toLocaleString()}>
                        Modified: {new Date(photo.modified_at).toLocaleDateString()}
                      </p>
                      {photo.submitted_by && (
                        <p className="text-purple-600 font-medium">
                          📤 {photo.submitted_by}
                        </p>
                      )}
                      {photo.validated_by && (
                        <p className="text-blue-600 font-medium">
                          ✅ {photo.validated_by}
                        </p>
                      )}
                      {photo.classification && (
                        <p className="text-green-600 font-medium">
                          Type: {photo.classification}
                        </p>
                      )}
                      {photo.reject_reason && (
                        <p className="text-red-600 font-medium" title={photo.reject_reason}>
                          Reason: {photo.reject_reason.length > 20 ? photo.reject_reason.substring(0, 20) + '...' : photo.reject_reason}
                        </p>
                      )}
                    </div>
                    
                    <div className="mt-2 space-y-1">
                      <button
                        onClick={() => handleViewDetail(photo)}
                        className="w-full flex items-center justify-center gap-1 px-2 py-1 bg-blue-50 text-blue-600 rounded text-xs hover:bg-blue-100"
                      >
                        <Edit className="h-3 w-3" />
                        Details
                      </button>
                      
                      {photo.status === 'pending' && canValidatePhotos() && (
                        <div className="flex gap-1">
                          <button
                            onClick={() => handleValidationRequest(photo, false)}
                            disabled={validationLoading[photo.id]}
                            className="flex-1 flex items-center justify-center gap-1 px-2 py-1 bg-red-50 text-red-600 rounded text-xs hover:bg-red-100 disabled:opacity-50"
                          >
                            <ThumbsDown className="h-3 w-3" />
                            Reject
                          </button>
                          <button
                            onClick={() => handleValidationRequest(photo, true)}
                            disabled={validationLoading[photo.id]}
                            className="flex-1 flex items-center justify-center gap-1 px-2 py-1 bg-green-50 text-green-600 rounded text-xs hover:bg-green-100 disabled:opacity-50"
                          >
                            <ThumbsUp className="h-3 w-3" />
                            Validate
                          </button>
                        </div>
                      )}
                      
                      {photo.status === 'pending' && !canValidatePhotos() && (
                        <div className="text-center py-1">
                          <span className="text-xs text-gray-500 italic">Pending validation</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="flex items-center gap-1 px-3 py-2 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </button>
                
                <div className="flex items-center gap-1">
                  {/* Page numbers */}
                  {[...Array(Math.min(5, totalPages))].map((_, i) => {
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
                        onClick={() => handlePageChange(pageNum)}
                        className={`px-3 py-2 rounded ${
                          pageNum === currentPage
                            ? 'bg-blue-500 text-white'
                            : 'bg-white border border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>
                
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="flex items-center gap-1 px-3 py-2 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}
          </>
        )}

        {/* Empty state */}
        {!loading && photos.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📷</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">No photos found</h3>
            <p className="text-gray-600 mb-4">
              {filters.status 
                ? `No photos with status "${filters.status}"`
                : 'No photos available'
              }
            </p>
            <button
              onClick={() => {
                setFilters({ status: '', limit: 24 });
                fetchPhotos(1);
              }}
              className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600"
            >
              Reset filters
            </button>
          </div>
        )}
      </div>

      {/* Classification Modal */}
      {showClassificationModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-semibold mb-4">Select a classification</h3>
            <p className="text-gray-600 mb-4">
              Photo: {pendingValidationPhoto?.filename}
            </p>
            
            <div className="space-y-2 mb-6">
              {classifications.map((option) => (
                <label key={option.value} className="flex items-center">
                  <input
                    type="radio"
                    name="classification"
                    value={option.value}
                    checked={classification === option.value}
                    onChange={(e) => setClassification(e.target.value)}
                    className="mr-3"
                  />
                  <span className="text-sm">{option.label}</span>
                </label>
              ))}
            </div>
            
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded mb-4 text-sm">
                {error}
              </div>
            )}
            
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowClassificationModal(false);
                  setPendingValidationPhoto(null);
                  setClassification('');
                  setError(null);
                }}
                className="px-4 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleClassificationSubmit}
                disabled={!classification}
                className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Validate
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PhotoGrid;
