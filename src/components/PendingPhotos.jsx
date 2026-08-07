import React, { useState, useEffect } from 'react';
import { ThumbsUp, ThumbsDown, Clock, AlertTriangle, CheckCircle, X, Info, Edit, Search, Save, RefreshCw, Camera, Zap } from 'lucide-react';
import { ArtworkSearch } from './ArtworkSearch';
import { PhotoDetail } from './PhotoDetail';

const PendingPhotos = () => {
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [showValidationModal, setShowValidationModal] = useState(false);
  const [classification, setClassification] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [customReason, setCustomReason] = useState('');
  const [validationLoading, setValidationLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Photos state
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [photosError, setPhotosError] = useState(null);
  const [markedPhotos, setMarkedPhotos] = useState(new Set());
  
  // Extended features from PhotoValidator
  const [newFilename, setNewFilename] = useState('');
  const [showRenameForm, setShowRenameForm] = useState(false);
  const [existingArtwork, setExistingArtwork] = useState(null);
  const [showArtworkSearch, setShowArtworkSearch] = useState(false);
  const [autoSearchLoading, setAutoSearchLoading] = useState(false);
  const [autoSearchCompleted, setAutoSearchCompleted] = useState(false);
  const [duplicateDetection, setDuplicateDetection] = useState(null);
  const [showDuplicateWarning, setShowDuplicateWarning] = useState(false);
  const [qualityAnalysis, setQualityAnalysis] = useState(null);
  const [qualityAnalyzing, setQualityAnalyzing] = useState(false);
  const [fileDetails, setFileDetails] = useState(null);
  const [searchResults, setSearchResults] = useState([]);
  const [allSearchResults, setAllSearchResults] = useState([]);
  const [showAllResults, setShowAllResults] = useState(false);
  const [modalInitialMode, setModalInitialMode] = useState('choose');
 const [selectedPhotos, setSelectedPhotos] = useState(new Set());
  const togglePhotoSelection = (photoId) => {
    setSelectedPhotos((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(photoId)) {
        newSet.delete(photoId);
      } else {
        newSet.add(photoId);
      }
      return newSet;
    });
  };

  const handleSelectAll = () => {
    if (selectedPhotos.size === photos.length) {
      setSelectedPhotos(new Set());
    } else {
      const allIds = photos.map((p) => p.id);
      setSelectedPhotos(new Set(allIds));
    }
  };
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);
  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalPhotos, setTotalPhotos] = useState(0);
  const photosPerPage = 24; // 6 colonnes x 4 lignes = 24 photos par page
  
  
  // Fetch pending photos
  const fetchPhotos = async (page = 1) => {
    try {
      setLoading(true);
      setPhotosError(null);
      
      const response = await fetch(`/api/photos/list?status=pending&page=${page}&limit=${photosPerPage}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Photos data received:', data);
      setPhotos(data.photos || []);
      setTotalPages(data.total_pages || 1);
      setTotalPhotos(data.total || 0);
      setCurrentPage(page);
      
      // Marked status check disabled for better performance
      
    } catch (err) {
      console.error('Error fetching photos:', err);
      setPhotosError(`Loading error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

 const handleDeleteAllPending = async () => {
    try {
      setDeleteLoading(true);

      const response = await fetch("/api/photos/delete-all-pending", {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Delete failed");
      }

      alert(data.message);

      setShowDeleteModal(false);
      fetchPhotos(currentPage); // refresh list
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setDeleteLoading(false);
    }
  };

  // Check marked photos status
  const checkMarkedStatus = async (photoIds) => {
    try {
      const marked = new Set();
      for (const photoId of photoIds) {
        try {
          const response = await fetch(`/api/photos/${encodeURIComponent(photoId)}/mark-status`, {
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            }
          });
          if (response.ok) {
            const result = await response.json();
            if (result.success && result.is_marked) {
              marked.add(photoId);
            }
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
const handleDeleteSelected = async () => {
    try {
      setDeleteLoading(true);

      const response = await fetch("/api/photos/delete-selected-pending", {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          photoIds: Array.from(selectedPhotos),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Delete failed");
      }

      alert(data.message);

      setSelectedPhotos(new Set());
      setShowDeleteModal(false);
      fetchPhotos(currentPage);
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      setDeleteLoading(false);
    }
  };

  // Handle photo marking
  const handleMarkPhoto = async (photoId, photoFilename) => {
    try {
      const isMarked = markedPhotos.has(photoId);
      const response = await fetch(`/api/photos/${encodeURIComponent(photoId)}/mark`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          filename: photoFilename,
          note: '',
          action: isMarked ? 'unmark' : 'mark'
        })
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
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
      }
    } catch (err) {
      console.error('Error marking photo:', err);
    }
  };

  // Get image URL
  const getImageUrl = (photo) => {
    if (!photo) return '';
    return `/api/photos/${encodeURIComponent(photo.id)}`;
  };

  // Get thumbnail URL for mosaic view
    const getThumbnailUrl = (photo) => {
    if (!photo) return '';
    return `/api/photos/${encodeURIComponent(photo.id)}/thumbnail`;
  };
  // Load photos on component mount
  useEffect(() => {
    fetchPhotos();
  }, []);


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
    'Potential duplicate found in Odoo',
    'Other (specify)'
  ];

  // Handle photo selection from mosaic
  const handlePhotoSelect = async (photo) => {
    // Use PhotoDetail instead of modal - it handles everything
    handleShowDetail(photo);
  };

  // Check if photo needs renaming and prompt user
  const checkForMissingArtworkId = (photo) => {
    // Check if photo has no artwork_id or artwork_id is null/empty
    if (!photo?.artwork_id || photo.artwork_id === null || photo.artwork_id === '') {
      // Show a notification that this photo needs attention
      console.log('Photo missing artwork ID, consider renaming:', photo.filename);
      
      // Optionally auto-show rename form for missing IDs
      // Uncomment the lines below if you want to automatically show the rename form
      // setTimeout(() => {
      //   setShowRenameForm(true);
      // }, 1000);
    }
  };

  // Fetch photo details/metadata
  const fetchFileDetails = async (photoId) => {
    try {
      if (!photoId) return;
      
      const response = await fetch(`/api/photos/details/${encodeURIComponent(photoId)}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        // Photo details unavailable
        setFileDetails(null);
        return;
      }
      
      const details = await response.json();
      setFileDetails(details);
      
    } catch (err) {
      // Error loading photo details
      setFileDetails(null);
    }
  };

  // Handle artwork found
  const handleArtworkFound = (artwork) => {
    setExistingArtwork(artwork);
    // Check if this constitutes a duplicate
    if (artwork && artwork.all_image_urls && artwork.all_image_urls.length > 0) {
      setDuplicateDetection({
        isDuplicate: true,
        artwork: artwork,
        similarity: 'Exact ID match',
        recommendation: 'reject'
      });
      setShowDuplicateWarning(true);
    }
  };


  // Analyze photo quality
  const analyzePhotoQuality = async (photo) => {
    if (!photo || qualityAnalyzing) return;
    
    try {
      setQualityAnalyzing(true);
      setError(null);
      
      const response = await fetch(`/api/photos/${encodeURIComponent(photo.id)}/analyze-quality`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        console.log('Quality analysis failed with status:', response.status);
        setQualityAnalysis(null);
        return;
      }
      
      const result = await response.json();
      
      if (result.success) {
        setQualityAnalysis(result.quality_analysis);
      } else {
        console.log('Quality analysis error:', result.error);
        setQualityAnalysis(null);
      }
    } catch (err) {
      // Error in quality analysis - just log it, don't show to user
      console.log('Quality analysis error:', err.message);
      setQualityAnalysis(null);
    } finally {
      setQualityAnalyzing(false);
    }
  };

  // Automatic duplicate detection with OperaCRM
  const performAutomaticDuplicateCheck = async (photo) => {
    if (!photo || !photo.filename) return;
    
    try {
      setAutoSearchLoading(true);
      
      // Extract artwork ID from filename
      const idMatch = photo.id.match(/([A-Z]+-\d+)/);
      if (idMatch && idMatch[1]) {
        const artworkId = idMatch[1];
        
        // Search in FileMaker automatically
        const response = await fetch(`/api/filemaker/artwork/${artworkId}`, {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        if (response.ok) {
          const result = await response.json();
          
          if (result.success && result.artwork) {
            setDuplicateDetection({
              isDuplicate: true,
              artwork: result.artwork,
              similarity: 'OperaCRM ID match',
              recommendation: 'reject',
              confidence: 'high'
            });
            setShowDuplicateWarning(true);
            setExistingArtwork(result.artwork);
          }
        }
      }
      
      setAutoSearchCompleted(true);
    } catch (error) {
      // Error in duplicate detection
    } finally {
      setAutoSearchLoading(false);
    }
  };

  // Handle rename submission
  const handleRenameSubmit = async (e) => {
    e.preventDefault();
    if (!newFilename || newFilename === selectedPhoto.filename) {
      setShowRenameForm(false);
      return;
    }

    try {
      const response = await fetch('/api/photos/rename', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          photoId: selectedPhoto.id,
          newFilename: newFilename
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'Renaming error');
      }

      const result = await response.json();
      
      // Update current photo with new filename and ID
      setSelectedPhoto(prev => ({ 
        ...prev,
	filename: `${result.new_filename}_MAIN`,
        id: result.new_photo_id || prev.id
      }));
      setShowRenameForm(false);
      setError(null);
      
    } catch (err) {
      setError(`Renaming error: ${err.message}`);
    }
  };

  // Handle photo validation (from PhotoValidationModal)
  const handleValidatePhoto = async (photo, classification) => {
    console.log('PendingPhotos handleValidatePhoto called with:', { photo, classification });
    
    try {
      console.log('Starting validation with classification:', classification);
      setValidationLoading(true);
      setError(null);

      const payload = {
        photoId: photo.id,
        decision: 'valider',
        classification: classification,
        newFilename: photo.filename
      };
      console.log('Validation payload:', payload);

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
        console.error('API Error:', errorData);
        throw new Error(errorData.error || `Error ${response.status}`);
      }

      // Photo validated successfully - refresh the current page
      
	console.log('Photo validated successfully');
      alert("Image validated successfully");
      await  fetchPhotos(currentPage);
      if (window.setAppView) {
        window.setAppView("validated");
      }
      // Close modal and reset
      setShowValidationModal(false);
      setSelectedPhoto(null);
      
    } catch (err) {
      setError(`Validation error: ${err.message}`);
    } finally {
      setValidationLoading(false);
    }
  };

  // Handle photo rejection (from PhotoValidationModal)
  const handleRejectPhoto = async (photo, reason) => {
    console.log('PendingPhotos handleRejectPhoto called with:', { photo, reason });
    
    try {
      console.log('Starting rejection with reason:', reason);
      setValidationLoading(true);
      setError(null);

      const payload = {
        photoId: photo.id,
        decision: 'refuser',
        rejectReason: reason,
        newFilename: photo.filename
      };
      console.log('Rejection payload:', payload);

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

      // Photo rejected successfully - refresh the current page
      console.log('Photo rejected successfully');
      fetchPhotos(currentPage);
      
      // Close modal and reset
      setShowValidationModal(false);
      setSelectedPhoto(null);
      
    } catch (err) {
      setError(`Rejection error: ${err.message}`);
    } finally {
      setValidationLoading(false);
    }
  };

  // Submit validation/rejection
  const submitValidation = async (photo, isValid, reason = null) => {
    if (!photo) return;

    try {
      setValidationLoading(true);
      setError(null);

      const payload = {
        photoId: photo.id,
        decision: isValid ? 'valider' : 'refuser',
        classification: isValid ? classification : undefined,
        rejectReason: reason || rejectReason,
        newFilename: photo.filename
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

      // Reset forms
      setShowValidationModal(false);
      setClassification('');
      setRejectReason('');
      setCustomReason('');
      setSelectedPhoto(null);
      
      // Refresh current page
      fetchPhotos(currentPage);

    } catch (err) {
      // Validation error occurred
      setError(`Validation error: ${err.message}`);
    } finally {
      setValidationLoading(false);
    }
  };

  // Handle showing photo detail
  const handleShowDetail = (photo) => {
    setSelectedPhoto(photo);
    setShowDetail(true);
  };

  // Handle back from detail
  const handleBackFromDetail = () => {
    setShowDetail(false);
    setSelectedPhoto(null);
    // Refresh the photos list in case something changed
    fetchPhotos(currentPage);
  };

  // Handle validate submit
  const handleValidateSubmit = () => {
    if (!classification) {
      setError('Please select a classification');
      return;
    }
    submitValidation(selectedPhoto, true);
  };

  // Handle reject submit
  const handleRejectSubmit = () => {
    let finalReason = rejectReason;
    
    if (rejectReason === 'Other (specify)' && customReason) {
      finalReason = customReason;
    }
    
    if (!finalReason) {
      setError('Please select or enter a rejection reason');
      return;
    }
    
    submitValidation(selectedPhoto, false, finalReason);
  };

  // If showing detail view, render PhotoDetail component
  if (showDetail && selectedPhoto) {
    return (
      <PhotoDetail
        photo={selectedPhoto}
        onBack={handleBackFromDetail}
        onValidate={(validatedPhoto) => {
          // Refresh photos after validation
          fetchPhotos(currentPage);
        }}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-7xl mx-auto">
        
        {/* Header */}
        <div className="bg-white rounded-lg shadow-md p-6 mb-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center">
              <Clock className="w-8 h-8 text-yellow-500 mr-3" />
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Pending Photos</h1>
                <p className="text-gray-600">Photos awaiting validation</p>
              </div>
            </div>
            <div className="flex items-center space-x-2 px-4 py-2 bg-yellow-100 rounded-lg">
              <Clock className="w-5 h-5 text-yellow-600" />
              <span className="text-yellow-800 font-medium">Pending Review</span>
            </div>
          </div>
        </div>


        {/* Error Alert */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <AlertTriangle className="h-5 w-5 text-red-400 mr-2" />
                <span className="text-red-800">{error}</span>
              </div>
              <button
                onClick={() => setError(null)}
                className="text-red-400 hover:text-red-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>
        )}

        {/* Photo Mosaic */}
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              Pending Photos ({totalPhotos})
            </h2>
            <div className="flex items-center gap-3">
              <span className="text-sm text-gray-500">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => fetchPhotos(currentPage)}
                className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors flex items-center"
              >
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh
              </button>

              <button
            onClick={() => setShowDeleteModal(true)}
            disabled={selectedPhotos.size === 0}
            className={`px-4 py-2 rounded-lg transition-colors flex items-center ${
              selectedPhotos.size === 0
                ? "bg-gray-400 cursor-not-allowed text-white"
                : "bg-red-600 hover:bg-red-700 text-white"
            }`}
          >
            Delete Selected ({selectedPhotos.size})
          </button>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                <p className="text-gray-600">Loading photos...</p>
              </div>
            </div>
          ) : photosError ? (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
              <div className="flex items-center">
                <AlertTriangle className="h-5 w-5 text-red-400 mr-2" />
                <span className="text-red-800">{photosError}</span>
              </div>
            </div>
          ) : photos.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="h-16 w-16 mx-auto mb-4 text-gray-400" />
              <p className="text-gray-600 text-lg">No pending photos found</p>
            </div>
          ) : (
            <>
              {/* Select All */}
              <div className="flex items-center mb-4">
                <input
                  type="checkbox"
                  checked={
                    photos.length > 0 && selectedPhotos.size === photos.length
                  }
                  onChange={handleSelectAll}
                  className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
                />
                <span className="ml-2 text-sm text-gray-700 font-medium">
                  Select All
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-4">
                {photos.map((photo) => (
                  <div
                    key={photo.id}
                    // className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-all duration-200 cursor-pointer transform hover:scale-105"
                    className={`bg-white rounded-lg shadow-md overflow-hidden transition-all duration-200 cursor-pointer transform hover:scale-105 ${
                      selectedPhotos.has(photo.id) ? "ring-4 ring-red-400" : ""
                    }`}
                    onClick={(e) => {
                      // Only handle photo select if the click didn't come from button interactions
                      // if (!e.target.closest("button")) {
                      if (!e.target.closest("button") && !e.target.closest("input")) {
                        handlePhotoSelect(photo);
                      }
                    }}
                  >
                    {/* Photo */}
                    <div className="aspect-square bg-gray-100 relative">
                      {/* Selection Checkbox */}
                      <div className="absolute top-2 left-2 z-10">
                        <input
                          type="checkbox"
                          checked={selectedPhotos.has(photo.id)}
                          onChange={(e) => {
                            e.stopPropagation();
                            togglePhotoSelection(photo.id);
                          }}
                          className="w-5 h-5 text-red-600 bg-white border-gray-300 rounded shadow focus:ring-red-500 cursor-pointer"
                        />
                      </div>

                      <img
                        src={getThumbnailUrl(photo)}
                        alt={photo.filename}
                        className="w-full h-full object-cover"
                        loading="lazy"
                        decoding="async"
                        onError={(e) => {
                          e.target.src =
                            "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vdCBhdmFpbGFibGU8L3RleHQ+PC9zdmc+";
                        }}
                      />

                      {/* Status badge */}
                      <div className="absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
                        <Clock className="w-3 h-3" />
                      </div>

                      {/* FM + Odoo Existence Indicator */}
                      {photo.exists_status && (
                        <div
                          className={`absolute bottom-2 right-2 w-4 h-4 rounded-full border-2 
                        ${
                          photo.exists_status === "green"
                            ? "bg-green-500 border-green-700"
                            : "bg-red-500 border-red-700"
                        }`}
                          title={
                            photo.exists_status === "green"
                              ? "Exists in Odoo or FileMaker"
                              : "Not found in Odoo or FileMaker"
                          }
                        />
                      )}

                      {/* Mark button */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          handleMarkPhoto(photo.id, photo.filename);
                        }}
                        className="absolute top-2 right-2 p-1 rounded-full bg-white shadow-md hover:bg-gray-100 transition-colors"
                        title={
                          markedPhotos.has(photo.id)
                            ? "Remove bookmark"
                            : "Mark this photo"
                        }
                      >
                        <Zap
                          className={`w-3 h-3 ${
                            markedPhotos.has(photo.id)
                              ? "text-yellow-500 fill-current"
                              : "text-gray-400"
                          }`}
                        />
                      </button>
                    </div>

                    {/* Photo Info */}
                    <div className="p-2">
                      <div className="text-sm font-medium text-gray-900 truncate mb-1">
                        {photo.filename}
                      </div>

                      {photo.artwork_id && (
                        <div className="text-xs text-blue-600 font-mono mb-1">
                          {photo.artwork_id}
                        </div>
                      )}

                      <div className="text-xs text-gray-500 mb-2">
                        {photo.created_at
                          ? new Date(photo.created_at).toLocaleDateString()
                          : "Unknown date"}
                      </div>

                      {/* Quick Action Buttons */}
                      {/* <div className="flex gap-1"> */}
                      {/* Validate Button */}
                      {/* <button
                        onClick={(e) => {
                          e.stopPropagation();
                          console.log('Clicked validate button for photo:', photo.id);
                          setSelectedPhoto(photo);
                          setModalInitialMode('validate');
                          setShowValidationModal(true);
                        }}
                        className="flex-1 px-2 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700 transition-colors flex items-center justify-center"
                        disabled={validationLoading}
                      >
                        <ThumbsUp className="w-3 h-3 mr-1" />
                        Valid
                      </button> */}

                      {/* Reject Button */}
                      {/* <button
                        onClick={(e) => {
                          e.stopPropagation();
                          console.log('Clicked reject button for photo:', photo.id);
                          setSelectedPhoto(photo);
                          setModalInitialMode('reject');
                          setShowValidationModal(true);
                        }}
                        className="flex-1 px-2 py-1 bg-red-600 text-white rounded text-xs hover:bg-red-700 transition-colors flex items-center justify-center"
                        disabled={validationLoading}
                      >
                        <ThumbsDown className="w-3 h-3 mr-1" />
                        Reject
                      </button> */}
                      {/* </div> */}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
          
          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-6 pt-4 border-t border-gray-200">
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => fetchPhotos(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Previous
                </button>
                
                {/* Page Numbers */}
                <div className="flex space-x-1">
                  {[...Array(Math.min(5, totalPages))].map((_, i) => {
                    const page = Math.max(1, Math.min(totalPages - 4, currentPage - 2)) + i;
                    return (
                      <button
                        key={page}
                        onClick={() => fetchPhotos(page)}
                        className={`px-3 py-2 text-sm rounded-lg ${
                          currentPage === page
                            ? 'bg-blue-600 text-white'
                            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                      >
                        {page}
                      </button>
                    );
                  })}
                </div>
                
                <button
                  onClick={() => fetchPhotos(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="px-3 py-2 text-sm bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                </button>
              </div>
              
              <div className="text-sm text-gray-500">
                Showing {(currentPage - 1) * photosPerPage + 1} to {Math.min(currentPage * photosPerPage, totalPhotos)} of {totalPhotos} photos
              </div>
            </div>
          )}
        </div>

        {/* Selected Photo Details and Validation */}
        {selectedPhoto && (
          <div id="validation-section" className="mt-8 bg-white rounded-lg shadow-md overflow-hidden">
            {/* Photo Header */}
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-b border-gray-200 p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <Camera className="w-8 h-8 text-blue-600 mr-3" />
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900">Selected Photo</h2>
                    <p className="text-gray-600">Detailed validation and analysis</p>
                  </div>
                </div>
                <button
                  onClick={() => setSelectedPhoto(null)}
                  className="p-2 hover:bg-gray-100 rounded-full transition-colors"
                >
                  <X className="w-6 h-6 text-gray-500" />
                </button>
              </div>
            </div>

            <div className="p-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* Photo Display */}
                <div className="space-y-4">
                  <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden border-2 border-gray-200">
                    <img
                      src={`/api/photos/${encodeURIComponent(selectedPhoto.id)}`}
                      alt={selectedPhoto.filename}
                      className="w-full h-full object-contain"
                      onError={(e) => {
                        e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vdCBhdmFpbGFibGU8L3RleHQ+PC9zdmc+';
                      }}
                    />
                  </div>
                  
                  {/* Validation Actions */}
                  <div className="flex gap-3">
                    <button
                      onClick={() => {
			handleValidatePhoto(selectedPhoto, "MAIN");
                        setModalInitialMode('validate');
                        setShowValidationModal(true);
                        setClassification('');
                      }}
                      disabled={validationLoading}
                      className={`flex-1 px-4 py-3 font-semibold rounded-lg transition-all duration-200 flex items-center justify-center ${
                        validationLoading 
                          ? 'bg-gray-400 cursor-not-allowed' 
                          : 'bg-green-600 hover:bg-green-700 hover:scale-105 active:scale-95'
                      } text-white`}
                    >
                      <ThumbsUp className="w-5 h-5 mr-2" />
                      Validate
                    </button>
                    <button
                      onClick={() => {
                        setModalInitialMode('reject');
                        setShowValidationModal(true);
                        setRejectReason('');
                      }}
                      disabled={validationLoading}
                      className={`flex-1 px-4 py-3 font-semibold rounded-lg transition-all duration-200 flex items-center justify-center ${
                        validationLoading 
                          ? 'bg-gray-400 cursor-not-allowed' 
                          : 'bg-red-600 hover:bg-red-700 hover:scale-105 active:scale-95'
                      } text-white`}
                    >
                      <ThumbsDown className="w-5 h-5 mr-2" />
                      Reject
                    </button>
                  </div>
                </div>

                {/* Photo Information and Controls */}
                <div className="space-y-6">
                  {/* Basic Info */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 mb-3 flex items-center">
                      <Info className="w-5 w-5 mr-2" />
                      File Information
                    </h3>
                    <div className="space-y-2 text-sm">
                      <div>
                        <span className="font-medium">Name:</span>
                        <span className="ml-2">{selectedPhoto.filename}</span>
                      </div>
                      <div>
                        <span className="font-medium">Path:</span>
                        <span className="ml-2 font-mono text-xs">{selectedPhoto.id}</span>
                      </div>
                      <div>
                        <span className="font-medium">Status:</span>
                        <span className="ml-2 px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">
                          {selectedPhoto.status}
                        </span>
                      </div>
                      {selectedPhoto.artwork_id && (
                        <div>
                          <span className="font-medium">Artwork ID:</span>
                          <span className="ml-2 font-mono text-blue-600">{selectedPhoto.artwork_id}</span>
                        </div>
                      )}
                      
                      {/* Missing Artwork ID Warning */}
                      {(!selectedPhoto.artwork_id || selectedPhoto.artwork_id === null || selectedPhoto.artwork_id === '') && (
                        <div className="p-2 bg-orange-50 border border-orange-200 rounded">
                          <div className="flex items-center text-orange-700">
                            <AlertTriangle className="h-4 w-4 mr-2" />
                            <span className="text-sm font-medium">Missing Artwork ID</span>
                          </div>
                          <p className="text-xs text-orange-600 mt-1">
                            This photo may need to be renamed with a proper artwork ID format (e.g., ARTIST-12345.jpg)
                          </p>
                        </div>
                      )}
                    </div>
                    
                    {/* Control Buttons */}
                    <div className="flex gap-2 mt-4">
                      <button
                        onClick={() => setShowRenameForm(!showRenameForm)}
                        className="flex items-center px-3 py-1 bg-white border border-gray-300 text-gray-700 rounded hover:bg-gray-50 text-sm"
                      >
                        <Edit className="h-4 w-4 mr-1" />
                        Rename
                      </button>
                      <div className="relative">
                        <button
                          onClick={() => setShowArtworkSearch(!showArtworkSearch)}
                          className="flex items-center px-3 py-1 bg-blue-50 border border-blue-200 text-blue-700 rounded hover:bg-blue-100 text-sm"
                        >
                          <Search className="h-4 w-4 mr-1" />
                          Search Database
                        </button>
                        
                        {/* Compact Search Dropdown */}
                        {showArtworkSearch && (
                          <div className="absolute top-full left-0 mt-1 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-50">
                            <div className="p-3 border-b border-gray-200">
                              <div className="flex items-center justify-between mb-3">
                                <h3 className="font-medium text-gray-900">Search Artwork</h3>
                                <button
                                  onClick={() => setShowArtworkSearch(false)}
                                  className="text-gray-400 hover:text-gray-600"
                                >
                                  <X className="w-4 h-4" />
                                </button>
                              </div>

                              <form onSubmit={async (e) => {
                                e.preventDefault();
                                const formData = new FormData(e.target);
                                const searchType = formData.get('searchType');
                                const query = formData.get('query');
                                
                                if (!query.trim()) return;
                                
                                try {
                                  // Search in OperaCRM/Odoo artworks!
                                  let response;
                                  if (searchType === 'global') {
                                    response = await fetch('/api/artworks/search', {
                                      method: 'POST',
                                      headers: {
                                        'Content-Type': 'application/json',
                                        'Authorization': `Bearer ${localStorage.getItem('token')}`
                                      },
                                      body: JSON.stringify({
                                        searchType: 'all',
                                        query: query,
                                        limit: 50
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
                                      setAllSearchResults([data.artwork]);
                                    } else if (data.artworks && data.artworks.length > 0) {
                                      setSearchResults(data.artworks.slice(0, 12)); // Show 12 in compact
                                      setAllSearchResults(data.artworks);
                                    } else {
                                      setSearchResults([]);
                                      setAllSearchResults([]);
                                    }
                                  } else {
                                    setSearchResults([]);
                                    setAllSearchResults([]);
                                  }
                                } catch (err) {
                                  setSearchResults([]);
                                  setAllSearchResults([]);
                                }
                              }} className="space-y-2">
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
                                  />
                                  <button
                                    type="submit"
                                    className="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
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
                                        onClick={() => {
                                          // Set existing artwork info for photo validation
                                          setExistingArtwork(artwork);
                                          setSearchResults([]);
                                          setShowArtworkSearch(false);
                                        }}
                                      >
                                        {/* Artwork Thumbnail */}
                                        {artwork.main_picture_hd && (
                                          <img
                                            src={artwork.main_picture_hd}
                                            alt={artwork.artist}
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
                                            {artwork.artist}
                                          </div>
                                          {artwork.title && (
                                            <div className="text-xs text-gray-500 truncate">
                                              {artwork.title}
                                            </div>
                                          )}
                                        </div>
                                      </div>
                                    ))}
                                  </div>
                                  
                                </div>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Rename Form */}
                    {showRenameForm && (
                      <div className="mt-4 p-3 bg-white border border-gray-200 rounded">
                        <h4 className="font-medium text-gray-900 mb-2">
                          {!selectedPhoto?.artwork_id ? 'Photo Missing Artwork ID' : 'Rename Photo'}
                        </h4>
                        {!selectedPhoto?.artwork_id && (
                          <p className="text-sm text-orange-600 mb-3">
                            ⚠️ This photo appears to be missing an artwork ID. Please provide a proper filename or skip if not needed.
                          </p>
                        )}
                        
                        <form onSubmit={handleRenameSubmit}>
                          <div className="space-y-3">
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-1">
                                New filename
                              </label>
                              <input
                                type="text"
                                value={newFilename}
                                onChange={(e) => setNewFilename(e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                                placeholder="e.g., ARTIST-12345.jpg or PICAPA-67890.jpg"
                              />
                              <p className="text-xs text-gray-500 mt-1">
                                Format: ARTIST-NUMBER.extension (e.g., PICAPA-12345.jpg)
                              </p>
                            </div>
                            
                            <div className="flex items-center gap-2">
                              <button
                                type="submit"
                                className="flex items-center px-3 py-2 bg-green-600 text-white rounded hover:bg-green-700"
                              >
                                <Save className="h-4 w-4 mr-1" />
                                Save
                              </button>
                              
                              <button
                                type="button"
                                onClick={() => {
                                  setShowRenameForm(false);
                                  setNewFilename('');
                                }}
                                className="flex items-center px-3 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
                              >
                                <X className="h-4 w-4 mr-1" />
                                Cancel
                              </button>
                              
                              {!selectedPhoto?.artwork_id && (
                                <button
                                  type="button"
                                  onClick={() => {
                                    setShowRenameForm(false);
                                    setNewFilename('');
                                    // Mark as skipped for this session
                                    console.log('Skipping rename for photo:', selectedPhoto?.id);
                                  }}
                                  className="flex items-center px-3 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600"
                                >
                                  SKIP
                                </button>
                              )}
                            </div>
                          </div>
                        </form>
                      </div>
                    )}
                  </div>

                  {/* Quality Analysis */}
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 mb-3 flex items-center">
                      <Camera className="w-5 h-5 mr-2 text-blue-600" />
                      A5 Print Quality Analysis
                    </h3>
                    
                    {qualityAnalyzing ? (
                      <div className="flex items-center justify-center py-6">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mr-3"></div>
                        <span className="text-blue-600">Analyzing quality...</span>
                      </div>
                    ) : qualityAnalysis ? (
                      <div className="space-y-3">
                        <div className="flex items-center p-3 bg-white border border-blue-200 rounded">
                          <div className="mr-3">
                            <div className={`w-6 h-6 rounded-full flex items-center justify-center ${
                              qualityAnalysis.color_code === 'green' ? 'bg-green-500' :
                              qualityAnalysis.color_code === 'lightgreen' ? 'bg-green-400' :
                              qualityAnalysis.color_code === 'orange' ? 'bg-orange-500' : 'bg-red-500'
                            }`}>
                              <Camera className="w-4 h-4 text-white" />
                            </div>
                          </div>
                          <div className="flex-1">
                            <span className={`font-bold text-lg ${
                              qualityAnalysis.color_code === 'green' ? 'text-green-600' :
                              qualityAnalysis.color_code === 'lightgreen' ? 'text-green-500' :
                              qualityAnalysis.color_code === 'orange' ? 'text-orange-600' : 'text-red-600'
                            }`}>
                              {qualityAnalysis.print_quality_a5}
                            </span>
                          </div>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-3 text-sm">
                          <div>
                            <span className="font-medium">A5 DPI:</span>
                            <span className="ml-2 font-mono">{qualityAnalysis.equivalent_dpi_a5}</span>
                          </div>
                          <div>
                            <span className="font-medium">Resolution:</span>
                            <span className="ml-2 font-mono">{qualityAnalysis.dimensions?.width} × {qualityAnalysis.dimensions?.height}</span>
                          </div>
                          <div>
                            <span className="font-medium">File size:</span>
                            <span className="ml-2">{qualityAnalysis.file_size_mb} MB</span>
                          </div>
                          <div>
                            <span className="font-medium">Format:</span>
                            <span className="ml-2">{qualityAnalysis.format}</span>
                          </div>
                        </div>

                        {qualityAnalysis.recommendations && qualityAnalysis.recommendations.length > 0 && (
                          <div className="bg-blue-100 p-3 rounded border border-blue-200">
                            <p className="font-medium text-blue-800 mb-2">💡 Recommendations:</p>
                            <ul className="text-sm text-blue-700 space-y-1">
                              {qualityAnalysis.recommendations.map((rec, i) => (
                                <li key={i} className="flex items-start">
                                  <span className="mr-2">•</span>
                                  <span>{rec}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="text-center py-6 text-gray-500">
                        <Camera className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                        <p>Quality analysis will load automatically</p>
                      </div>
                    )}
                  </div>

                  {/* Technical Details */}
                  {fileDetails && (
                    <div className="bg-gray-50 rounded-lg p-4">
                      <h3 className="font-semibold text-gray-900 mb-3">📄 Technical Information</h3>
                      <div className="grid grid-cols-2 gap-3 text-sm">
                        <div>
                          <span className="font-medium">Dimensions:</span>
                          <span className="ml-2">{fileDetails.width} × {fileDetails.height} px</span>
                        </div>
                        <div>
                          <span className="font-medium">Size:</span>
                          <span className="ml-2">{fileDetails.size}</span>
                        </div>
                        <div>
                          <span className="font-medium">Type:</span>
                          <span className="ml-2">{fileDetails.type}</span>
                        </div>
                        <div>
                          <span className="font-medium">Paper format:</span>
                          <span className="ml-2">{fileDetails.paperFormat}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Automatic checks status */}
                  <div className="bg-gray-50 rounded-lg p-4">
                    <h3 className="font-semibold text-gray-900 mb-3">🔍 Automatic Checks</h3>
                    <div className="space-y-2 text-sm">
                      {autoSearchLoading && (
                        <div className="flex items-center text-blue-600">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                          Checking for duplicates...
                        </div>
                      )}
                      {autoSearchCompleted && !duplicateDetection && (
                        <div className="text-green-600">
                          ✓ No duplicates detected automatically
                        </div>
                      )}
                      {qualityAnalyzing && (
                        <div className="flex items-center text-blue-600">
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
                          Analyzing image quality...
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>


              {/* Existing Artwork Info */}
              {existingArtwork && (
                <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
                  <h4 className="font-semibold text-green-900 mb-3">🎨 Artwork found in database</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <div className="mb-2">
                        <span className="font-medium">ID:</span>
                        <span className="ml-2 font-mono text-blue-600">{existingArtwork.IdName}</span>
                      </div>
                      <div className="mb-2">
                        <span className="font-medium">Title:</span>
                        <span className="ml-2">{existingArtwork.title}</span>
                      </div>
                      <div className="mb-2">
                        <span className="font-medium">Artist:</span>
                        <span className="ml-2">{existingArtwork.artist}</span>
                      </div>
                      <div className="mb-2">
                        <span className="font-medium">Year:</span>
                        <span className="ml-2">{existingArtwork.year}</span>
                      </div>
                    </div>
                    <div>
                      <div className="mb-2">
                        <span className="font-medium">Medium:</span>
                        <span className="ml-2">{existingArtwork.medium}</span>
                      </div>
                      <div className="mb-2">
                        <span className="font-medium">Dimensions:</span>
                        <span className="ml-2">{existingArtwork.dimensions}</span>
                      </div>
                      <div className="mb-2">
                        <span className="font-medium">Existing images:</span>
                        <span className="ml-2">{existingArtwork.image_count} photo(s)</span>
                      </div>
                    </div>
                  </div>
                  
                  {existingArtwork.all_image_urls && existingArtwork.all_image_urls.length > 0 && (
                    <div className="mt-4">
                      <h5 className="font-medium text-green-800 mb-3">All photos of this artwork ({existingArtwork.all_image_urls.length}):</h5>
                      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                        {existingArtwork.all_image_urls.map((imageUrl, index) => (
                          <div key={index} className="border border-green-200 rounded overflow-hidden bg-white shadow-sm hover:shadow-md transition-shadow">
                            <img 
                              src={imageUrl} 
                              alt={`Photo ${index + 1} - ${existingArtwork.IdName}`}
                              className="w-full h-32 object-cover hover:scale-105 transition-transform cursor-pointer"
                              onClick={() => window.open(imageUrl, '_blank')}
                              onError={(e) => {
                                e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vdCBhdmFpbGFibGU8L3RleHQ+PC9zdmc+';
                              }}
                            />
                            <div className="px-2 py-1 text-xs text-center text-gray-600 bg-gray-50">
                              Vue {index + 1}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Duplicate Warning */}
              {showDuplicateWarning && duplicateDetection && (
                <div className="mt-6 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                  <div className="flex items-start mb-4">
                    <AlertTriangle className="h-6 w-6 text-orange-500 mr-3 mt-1" />
                    <div className="flex-1">
                      <h4 className="font-semibold text-orange-800 mb-2">Potential duplicate detected</h4>
                      <p className="text-orange-700 text-sm mb-3">
                        This photo appears to match an artwork already present in the database.
                      </p>
                      
                      <div className="flex gap-2 mt-4">
                        <button
                          onClick={() => {
                            setRejectReason('Potential duplicate found in Odoo');
                            setShowRejectionForm(true);
                            setShowDuplicateWarning(false);
                          }}
                          className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600"
                        >
                          Reject as duplicate
                        </button>
                        <button
                          onClick={() => setShowDuplicateWarning(false)}
                          className="px-3 py-1 bg-gray-500 text-white rounded text-sm hover:bg-gray-600"
                        >
                          Continue anyway
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

	  {showDeleteModal && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <div className="bg-white rounded-lg p-6 w-96 shadow-lg">
              <h3 className="text-lg font-bold mb-4 text-gray-900">
                Confirm Deletion
              </h3>

              <p className="text-gray-600 mb-6">
                Are you sure you want to delete the selected photos? This action
                cannot be undone.
              </p>

              <div className="flex justify-end gap-3">
                <button
                  onClick={() => setShowDeleteModal(false)}
                  className="px-4 py-2 bg-gray-400 text-white rounded hover:bg-gray-500"
                >
                  No
                </button>

                <button
                  onClick={handleDeleteSelected}
                  disabled={deleteLoading}
                  className={`px-4 py-2 text-white rounded ${
                    deleteLoading
                      ? "bg-gray-500"
                      : "bg-red-600 hover:bg-red-700"
                  }`}
                >
                  {deleteLoading ? "Deleting..." : "Yes, Delete"}
                </button>
              </div>
            </div>
          </div>
        )}
        {/* End of component */}

      </div>
    </div>
  );
};

export default PendingPhotos;
