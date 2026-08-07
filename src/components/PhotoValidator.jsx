import React, { useState, useEffect, useCallback } from 'react';
import { ThumbsUp, ThumbsDown, Loader, RefreshCw, Info, Edit, Search, Save, X, AlertTriangle, Camera, Zap, CheckCircle, Star } from 'lucide-react';
import { ArtworkSearch } from './ArtworkSearch';
import odooService from '../services/odooService';
import apiService from '../services/apiService';

const ErrorAlert = ({ message, onDismiss }) => (
  <div className="mb-4 p-4 bg-white border-2 border-red-500 text-black relative rounded-lg">
    {message}
    <button 
      onClick={onDismiss} 
      className="absolute top-2 right-2 text-black hover:text-gray-600 font-bold text-xl"
    >
      ×
    </button>
  </div>
);

const ExistingPhotoQuality = ({ imageUrl }) => {
  const [quality, setQuality] = useState(null);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    const analyzeImageQuality = async () => {
      if (!imageUrl || analyzing) return;
      
      setAnalyzing(true);
      try {
        // Create a hidden image to get dimensions
        const img = new window.Image();
        img.crossOrigin = 'anonymous';
        
        img.onload = () => {
          const width = img.naturalWidth;
          const height = img.naturalHeight;
          
          // Calculate DPI equivalent for A5
          const a5WidthInches = 5.83;
          const a5HeightInches = 8.27;
          const dpiWidth = width / a5WidthInches;
          const dpiHeight = height / a5HeightInches;
          const equivalentDpi = Math.min(dpiWidth, dpiHeight);
          
          // Determine quality level
          let qualityLevel, colorCode;
          if (equivalentDpi >= 300) {
            qualityLevel = 'excellent';
            colorCode = 'green';
          } else if (equivalentDpi >= 200) {
            qualityLevel = 'good';
            colorCode = 'lightgreen';
          } else if (equivalentDpi >= 150) {
            qualityLevel = 'acceptable';
            colorCode = 'orange';
          } else {
            qualityLevel = 'poor';
            colorCode = 'red';
          }
          
          setQuality({
            dimensions: { width, height },
            equivalent_dpi_a5: Math.round(equivalentDpi * 10) / 10,
            quality_level: qualityLevel,
            color_code: colorCode
          });
          setAnalyzing(false);
        };
        
        img.onerror = () => {
          setQuality({ error: 'Analysis failed' });
          setAnalyzing(false);
        };
        
        img.src = imageUrl;
      } catch (err) {
        setQuality({ error: 'Analysis error' });
        setAnalyzing(false);
      }
    };

    analyzeImageQuality();
  }, [imageUrl]);

  const getQualityIcon = (colorCode) => {
    const baseClasses = "w-4 h-4 rounded-full flex items-center justify-center";
    switch(colorCode) {
      case 'green':
        return <div className={`${baseClasses} bg-green-500`} title="Excellent quality"><CheckCircle className="w-2 h-2 text-white" /></div>;
      case 'lightgreen':
        return <div className={`${baseClasses} bg-green-400`} title="Good quality"><CheckCircle className="w-2 h-2 text-white" /></div>;
      case 'orange':
        return <div className={`${baseClasses} bg-orange-500`} title="Acceptable quality"><AlertTriangle className="w-2 h-2 text-white" /></div>;
      case 'red':
        return <div className={`${baseClasses} bg-red-500`} title="Poor quality"><X className="w-2 h-2 text-white" /></div>;
      default:
        return <div className={`${baseClasses} bg-gray-500`} title="Analysis in progress"><Loader className="w-2 h-2 text-white animate-spin" /></div>;
    }
  };

  if (analyzing) {
    return (
      <div className="flex items-center text-xs text-gray-500">
        <Loader className="w-3 h-3 mr-1 animate-spin" />
        Analyzing...
      </div>
    );
  }

  if (quality?.error) {
    return (
      <div className="flex items-center text-xs text-gray-500">
        <div className="w-4 h-4 rounded-full bg-gray-400 flex items-center justify-center">
          <X className="w-2 h-2 text-white" />
        </div>
        <span className="ml-1">N/A</span>
      </div>
    );
  }

  if (quality) {
    return (
      <div className="flex items-center text-xs" title={`${quality.dimensions?.width} × ${quality.dimensions?.height} - ${quality.equivalent_dpi_a5} DPI A5`}>
        {getQualityIcon(quality.color_code)}
        <span className={`ml-1 font-medium ${
          quality.color_code === 'green' ? 'text-green-600' :
          quality.color_code === 'lightgreen' ? 'text-green-500' :
          quality.color_code === 'orange' ? 'text-orange-600' :
          quality.color_code === 'red' ? 'text-red-600' : 'text-gray-600'
        }`}>
          {quality.equivalent_dpi_a5} DPI
        </span>
      </div>
    );
  }

  return null;
};

const PhotoValidator = () => {
  const [currentPhoto, setCurrentPhoto] = useState(null);
  const [loading, setLoading] = useState(true);
  const [imageLoading, setImageLoading] = useState(false);
  const [error, setError] = useState(null);
  const [validationLoading, setValidationLoading] = useState(false);
  const [fileDetails, setFileDetails] = useState(null);
  const [stats, setStats] = useState({
    total: 0,
    validated: 0,
    rejected: 0,
    pending: 0
  });

  // Extended features
  const [newFilename, setNewFilename] = useState('');
  const [showRenameForm, setShowRenameForm] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [customReason, setCustomReason] = useState('');
  const [showRejectForm, setShowRejectForm] = useState(false);
  const [existingArtwork, setExistingArtwork] = useState(null);
  const [showArtworkSearch, setShowArtworkSearch] = useState(false);
  const [classification, setClassification] = useState('');
  const [showClassificationForm, setShowClassificationForm] = useState(false);
  const [autoSearchLoading, setAutoSearchLoading] = useState(false);
  const [autoSearchCompleted, setAutoSearchCompleted] = useState(false);
  const [duplicateDetection, setDuplicateDetection] = useState(null);
  const [showDuplicateWarning, setShowDuplicateWarning] = useState(false);
  const [qualityAnalysis, setQualityAnalysis] = useState(null);
  const [qualityAnalyzing, setQualityAnalyzing] = useState(false);
  
  // Photo marking state
  const [isPhotoMarked, setIsPhotoMarked] = useState(false);
  const [markNote, setMarkNote] = useState('');
  const [showMarkDialog, setShowMarkDialog] = useState(false);
  
  // FileMaker integration states
  const [filemakerData, setFilemakerData] = useState(null);
  const [filemakerLoading, setFilemakerLoading] = useState(false);
  const [artworkExists, setArtworkExists] = useState(null);
  
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

  // Fetch next photo from backend
  const fetchNextPhoto = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/photos/next', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        if (response.status === 404) {
          setCurrentPhoto(null);
          setError('No photos to validate found.');
          return;
        }
        throw new Error(`Error ${response.status}`);
      }
      
      const data = await response.json();
      // Next photo loaded
      
      if (data.photo) {
        setCurrentPhoto(data.photo);
        setNewFilename(data.photo.filename || data.photo.id);
        setImageLoading(true);
        // Reset forms
        setShowRenameForm(false);
        setShowRejectForm(false);
        setShowArtworkSearch(false);
        setShowClassificationForm(false);
        setRejectReason('');
        setCustomReason('');
        setClassification('');
        setExistingArtwork(null);
        setDuplicateDetection(null);
        setShowDuplicateWarning(false);
        setQualityAnalysis(null);
        setFilemakerData(null);
        setArtworkExists(null);
        // Fetch photo details, check for duplicates, analyze quality, and check FileMaker
        await Promise.all([
          fetchFileDetails(data.photo.id),
          performAutomaticDuplicateCheck(data.photo),
          analyzePhotoQuality(data.photo),
          checkArtworkInFileMaker(data.photo)
        ]);
      } else {
        setCurrentPhoto(null);
        setError('No photos available');
      }
      
    } catch (err) {
      // Error loading next photo
      setError(`Loading error: ${err.message}`);
      setCurrentPhoto(null);
    } finally {
      setLoading(false);
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
      // Photo details loaded
      setFileDetails(details);
      
    } catch (err) {
      // Error loading photo details
      setFileDetails(null);
    }
  };

  // Fetch statistics
  const fetchStats = async () => {
    try {
      const response = await fetch('/api/photos/stats', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}`);
      }
      
      const data = await response.json();
      // Stats loaded
      setStats(data);
      
    } catch (err) {
      // Error loading stats
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
      
      const result = await response.json();
      
      if (result.success) {
        setQualityAnalysis(result.quality_analysis);
      } else {
        setError(`Quality analysis error: ${result.error}`);
      }
    } catch (err) {
      // Error in quality analysis
      setError(`Erreur d'analyse qualité: ${err.message}`);
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

  // Check if artwork exists in FileMaker
  const checkArtworkInFileMaker = async (photo) => {
    if (!photo || !photo.filename) return;
    
    try {
      setFilemakerLoading(true);
      
      const response = await fetch(`/api/filemaker/artwork/check/${encodeURIComponent(photo.filename)}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const result = await response.json();
        setArtworkExists(result);
        
        // If artwork exists, fetch its image fields
        if (result.exists && result.artwork_id) {
          await fetchFileMakerImageFields(result.artwork_id);
        }
      }
    } catch (error) {
      console.log('Error checking FileMaker:', error);
    } finally {
      setFilemakerLoading(false);
    }
  };

  // Fetch FileMaker image fields for artwork
  const fetchFileMakerImageFields = async (artworkId) => {
    try {
      const response = await fetch(`/api/filemaker/artwork/${artworkId}/images`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setFilemakerData(result.image_fields);
        }
      }
    } catch (error) {
      console.log('Error fetching FileMaker image fields:', error);
    }
  };

  // Handle rename submission
    const handleRenameSubmit = async (e) => {
  e.preventDefault();

  // ❌ No rename if input is empty
  if (!newFilename) {
    setShowRenameForm(false);
    return;
  }

  // ✅ ADDED:
  // Remove extension if user typed (.jpg, .png, .jpeg, .tiff, etc.)
  // Backend will automatically preserve the ORIGINAL extension
  const cleanFilename = newFilename.replace(/\.[^/.]+$/, "");

  // ✅ ADDED:
  // Compare only base filename (without extension)
  // If name didn't actually change, skip rename
  const currentBaseName = currentPhoto.filename.replace(/\.[^/.]+$/, "");
  if (cleanFilename === currentBaseName) {
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
        photoId: currentPhoto.id,

        // ✅ ADDED:
        // Send filename WITHOUT extension
        // Backend enforces extension preservation
        newFilename: cleanFilename
      })
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || 'Renaming error');
    }

    const result = await response.json();

    // ✅ ADDED:
    // Backend returns FINAL filename (with original extension)
    // Update state using backend response, not local guess
    setCurrentPhoto(prev => ({
      ...prev,
      filename: result.new_filename,
      id: result.new_photo_id || prev.id
    }));

    setShowRenameForm(false);
    setError(null);

  } catch (err) {
    setError(`Renaming error: ${err.message}`);
  }
};

  // Handle photo validation
  const handleValidation = async (decision, reason = null, filename = null) => {
    if (!currentPhoto || validationLoading) return;
    
    // Check if classification is required for validation
    if (decision && !classification) {
      setError('Please select a classification for this photo');
      setShowClassificationForm(true);
      return;
    }
    
    try {
      setValidationLoading(true);
      setError(null);
      
      const payload = {
        photoId: currentPhoto.id,
        decision: decision ? 'valider' : 'refuser',
        classification: decision ? classification : undefined,
        rejectReason: reason,
        newFilename: filename || newFilename
      };
      
      // Validation started
      console.log('Starting validation with payload:', payload);
      
      // Add timeout to prevent hanging requests
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 second timeout
      
      const response = await fetch('/api/photos/validate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `Error ${response.status}`);
      }
      
      const result = await response.json();
      console.log('Validation response:', result);
      // Validation completed
      
      // Reset forms
      setShowRejectForm(false);
      setShowClassificationForm(false);
      setRejectReason('');
      setCustomReason('');
      setClassification('');
      
      // Fetch next photo and update stats
      await Promise.all([
        fetchNextPhoto(),
        fetchStats()
      ]);
      
    } catch (err) {
      // Validation error occurred
      console.error('Validation error:', err);
      
      if (err.name === 'AbortError') {
        setError('Validation request timed out. Please try again.');
      } else {
        setError(`Validation error: ${err.message}`);
      }
    } finally {
      setValidationLoading(false);
    }
  };

  // Handle reject with reason
  const handleRejectSubmit = () => {
    let finalReason = rejectReason;
    
    if (rejectReason === 'Other (specify)' && customReason) {
      finalReason = customReason;
    }
    
    if (!finalReason) {
      setError('Please select or enter a rejection reason');
      return;
    }
    
    handleValidation(false, finalReason);
  };

  // Handle validate with classification
  const handleValidateSubmit = () => {
    if (!classification) {
      setError('Please select a classification');
      return;
    }
    
    handleValidation(true);
  };

  // Simple validation
  const handleSimpleValidation = (decision) => {
    if (decision) {
      setShowClassificationForm(true);
    } else {
      setShowRejectForm(true);
    }
  };

  // Keyboard shortcuts
  const handleKeyPress = useCallback((event) => {
    if (validationLoading || loading || showRenameForm || showRejectForm) return;
    
    if (event.key === 'ArrowLeft' || event.key === 'q' || event.key === 'Q') {
      event.preventDefault();
      setShowRejectForm(true);
    } else if (event.key === 'ArrowRight' || event.key === 'd' || event.key === 'D') {
      event.preventDefault();
      handleSimpleValidation(true);
    } else if (event.key === 'r' || event.key === 'R') {
      event.preventDefault();
      fetchNextPhoto();
    } else if (event.key === 'e' || event.key === 'E') {
      event.preventDefault();
      setShowRenameForm(true);
    } else if (event.key === 's' || event.key === 'S') {
      event.preventDefault();
      setShowArtworkSearch(!showArtworkSearch);
    }
  }, [validationLoading, loading, showRenameForm, showRejectForm, showArtworkSearch]);

  // Photo marking functions
  const checkMarkStatus = async (photoId) => {
    if (!photoId) return;
    try {
      const response = await apiService.getMarkStatus(photoId);
      if (response.success) {
        setIsPhotoMarked(response.is_marked);
        setMarkNote(response.note || '');
      }
    } catch (err) {
      // Error checking mark status
    }
  };

  const handleMarkPhoto = async () => {
    if (!currentPhoto?.id) return;
    
    try {
      const response = await apiService.markPhoto(
        currentPhoto.id,
        currentPhoto.filename || '',
        markNote,
        'mark'
      );
      
      if (response.success) {
        setIsPhotoMarked(true);
        setShowMarkDialog(false);
      }
    } catch (err) {
      // Error updating photo mark
    }
  };

  const handleUnmarkPhoto = async () => {
    if (!currentPhoto?.id) return;
    
    try {
      const response = await apiService.unmarkPhoto(currentPhoto.id);
      if (response.success) {
        setIsPhotoMarked(false);
        setMarkNote('');
      }
    } catch (err) {
      // Error removing photo mark
    }
  };

  // Initialize data
  useEffect(() => {
    fetchNextPhoto();
    fetchStats();
  }, []);

  // Check mark status when photo changes
  useEffect(() => {
    if (currentPhoto?.id) {
      checkMarkStatus(currentPhoto.id);
    }
  }, [currentPhoto?.id]);

  // Setup keyboard events
  useEffect(() => {
    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [handleKeyPress]);

  // Periodic stats update
  useEffect(() => {
    const intervalId = setInterval(fetchStats, 10000); // Every 10 seconds
    return () => clearInterval(intervalId);
  }, []);

  // Get image URL
  const getImageUrl = () => {
    if (!currentPhoto) return '';
    
    // Always use the local photo endpoint for local photos first
    // The local endpoint will serve the actual uploaded file
    return `/api/photos/${encodeURIComponent(currentPhoto.id)}`;
  };

  // Get quality icon based on analysis
  const getQualityIcon = (analysis) => {
    if (!analysis || analysis.error) {
      return <div className="w-6 h-6 rounded-full bg-gray-400 flex items-center justify-center">
        <AlertTriangle className="w-4 h-4 text-white" />
      </div>;
    }

    const colorCode = analysis.color_code;
    const baseClasses = "w-6 h-6 rounded-full flex items-center justify-center";
    
    switch(colorCode) {
      case 'green':
        return <div className={`${baseClasses} bg-green-500`} title="Excellent quality (300+ DPI)">
          <Camera className="w-4 h-4 text-white" />
        </div>;
      case 'lightgreen':
        return <div className={`${baseClasses} bg-green-400`} title="Good quality (200+ DPI)">
          <Camera className="w-4 h-4 text-white" />
        </div>;
      case 'orange':
        return <div className={`${baseClasses} bg-orange-500`} title="Acceptable quality (150+ DPI)">
          <AlertTriangle className="w-4 h-4 text-white" />
        </div>;
      case 'red':
        return <div className={`${baseClasses} bg-red-500`} title="Insufficient quality (less than 150 DPI)">
          <X className="w-4 h-4 text-white" />
        </div>;
      default:
        return <div className={`${baseClasses} bg-gray-500`} title="Unknown quality">
          <AlertTriangle className="w-4 h-4 text-white" />
        </div>;
    }
  };

  return (
    <div className="min-h-screen bg-white py-8 px-4">
      <div className="max-w-6xl mx-auto">
        
        {/* Header with stats */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden mb-6 border-2 border-gray-300">
          <div className="p-6 bg-white text-black border-b-2 border-gray-300">
            <h1 className="text-3xl font-bold text-center mb-4 text-black">
              Photo Validation
            </h1>
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-center">
              <div className="bg-white border-2 border-gray-400 rounded-lg p-3">
                <div className="text-2xl font-bold text-black">{stats.total}</div>
                <div className="text-sm text-black">Total</div>
              </div>
              <div className="bg-white border-2 border-gray-400 rounded-lg p-3">
                <div className="text-2xl font-bold text-black">{stats.pending}</div>
                <div className="text-sm text-black">Pending</div>
              </div>
              <div className="bg-white border-2 border-gray-400 rounded-lg p-3">
                <div className="text-2xl font-bold text-black">{stats.validated}</div>
                <div className="text-sm text-black">Validated</div>
              </div>
              <div className="bg-white border-2 border-gray-400 rounded-lg p-3">
                <div className="text-2xl font-bold text-black">{stats.rejected}</div>
                <div className="text-sm text-black">Rejected</div>
              </div>
            </div>
            
            {stats.total > 0 && (
              <div className="mt-4">
                <div className="flex justify-between text-sm mb-2 text-black">
                  <span>Progress</span>
                  <span>{(((stats.validated + stats.rejected) / stats.total) * 100).toFixed(1)}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3 border border-gray-400">
                  <div 
                    className="bg-black h-3 rounded-full transition-all duration-300" 
                    style={{ width: `${((stats.validated + stats.rejected) / stats.total) * 100}%` }}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Photo info and controls */}
        {currentPhoto && (
          <div className="bg-white rounded-xl shadow-lg overflow-hidden mb-6">
            <div className="p-6">
              <div className="flex justify-between items-start mb-4">
                <h2 className="text-xl font-semibold flex items-center">
                  <Info className="mr-2 h-5 w-5" />
                  File Information
                </h2>
              </div>
              
              <div className="grid grid-cols-1 gap-6">
                <div>
                  <p className="mb-2"><span className="font-medium">Name:</span> {currentPhoto.filename}</p>
                  <p className="mb-2"><span className="font-medium">Path:</span> {currentPhoto.id}</p>
                  <p className="mb-2"><span className="font-medium">Status:</span> 
                    <span className="ml-2 px-2 py-1 text-xs bg-yellow-100 text-yellow-800 rounded">
                      {currentPhoto.status}
                    </span>
                  </p>
                  {currentPhoto.artwork_id && (
                    <p className="mb-2"><span className="font-medium">ID Œuvre détecté:</span> 
                      <span className="ml-2 px-2 py-1 text-xs bg-purple-100 text-purple-800 rounded font-mono">
                        {currentPhoto.artwork_id}
                      </span>
                    </p>
                  )}
                  
                  {/* FileMaker Integration Status */}
                  {filemakerLoading && (
                    <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                      <div className="flex items-center text-blue-700">
                        <Loader className="h-4 w-4 animate-spin mr-2" />
                        Checking in FileMaker...
                      </div>
                    </div>
                  )}
                  
                  {artworkExists && (
                    <div className={`mb-4 p-3 rounded-lg ${
                      artworkExists.exists 
                        ? 'bg-green-50 border border-green-200' 
                        : 'bg-orange-50 border border-orange-200'
                    }`}>
                      <div className="flex items-center mb-2">
                        {artworkExists.exists ? (
                          <CheckCircle className="h-5 w-5 text-green-600 mr-2" />
                        ) : (
                          <AlertTriangle className="h-5 w-5 text-orange-600 mr-2" />
                        )}
                        <span className={`font-medium ${
                          artworkExists.exists ? 'text-green-800' : 'text-orange-800'
                        }`}>
                          FileMaker: {artworkExists.exists ? 'Artwork Found' : 'Artwork Not Found'}
                        </span>
                      </div>
                      
                      {artworkExists.exists && artworkExists.artwork_info && (
                        <div className="text-sm text-green-700 ml-7">
                          <p><span className="font-medium">Artist:</span> {artworkExists.artwork_info.artist}</p>
                          <p><span className="font-medium">Title:</span> {artworkExists.artwork_info.title}</p>
                          <p><span className="font-medium">Year:</span> {artworkExists.artwork_info.year}</p>
                          {artworkExists.artwork_info.medium && (
                            <p><span className="font-medium">Medium:</span> {artworkExists.artwork_info.medium}</p>
                          )}
                        </div>
                      )}
                      
                      {!artworkExists.exists && (
                        <p className="text-sm text-orange-700 ml-7">
                          {artworkExists.message || 'This artwork was not found in the FileMaker database'}
                        </p>
                      )}
                    </div>
                  )}
                  
                  {/* FileMaker Image Fields Display */}
                  {filemakerData && (
                    <div className="mb-4 p-4 bg-gray-50 border border-gray-200 rounded-lg">
                      <h4 className="font-semibold text-gray-800 mb-3 flex items-center">
                        <Camera className="h-5 w-5 mr-2" />
                        FileMaker Image Fields
                      </h4>
                      
                      <div className="space-y-3 text-sm">
                        {/* MAIN300 Images */}
                        {filemakerData.MAIN300 && filemakerData.MAIN300.length > 0 && (
                          <div>
                            <span className="font-medium text-gray-700">MAIN300 ({filemakerData.MAIN300.length}):</span>
                            <div className="mt-1 flex flex-wrap gap-1">
                              {filemakerData.MAIN300.slice(0, 3).map((url, index) => (
                                <a key={index} href={url} target="_blank" rel="noopener noreferrer" 
                                   className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded hover:bg-blue-200">
                                  Image {index + 1}
                                </a>
                              ))}
                              {filemakerData.MAIN300.length > 3 && (
                                <span className="text-xs text-gray-500">+{filemakerData.MAIN300.length - 3} more</span>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* BACK300 Images */}
                        {filemakerData.BACK300 && filemakerData.BACK300.length > 0 && (
                          <div>
                            <span className="font-medium text-gray-700">BACK300 ({filemakerData.BACK300.length}):</span>
                            <div className="mt-1 flex flex-wrap gap-1">
                              {filemakerData.BACK300.slice(0, 3).map((url, index) => (
                                <a key={index} href={url} target="_blank" rel="noopener noreferrer" 
                                   className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded hover:bg-green-200">
                                  Back {index + 1}
                                </a>
                              ))}
                              {filemakerData.BACK300.length > 3 && (
                                <span className="text-xs text-gray-500">+{filemakerData.BACK300.length - 3} more</span>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* OTHER300 Images */}
                        {filemakerData.OTHER300 && filemakerData.OTHER300.length > 0 && (
                          <div>
                            <span className="font-medium text-gray-700">OTHER300 ({filemakerData.OTHER300.length}):</span>
                            <div className="mt-1 flex flex-wrap gap-1">
                              {filemakerData.OTHER300.slice(0, 3).map((url, index) => (
                                <a key={index} href={url} target="_blank" rel="noopener noreferrer" 
                                   className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded hover:bg-purple-200">
                                  Other {index + 1}
                                </a>
                              ))}
                              {filemakerData.OTHER300.length > 3 && (
                                <span className="text-xs text-gray-500">+{filemakerData.OTHER300.length - 3} more</span>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* DET300 Images */}
                        {filemakerData.DET300 && filemakerData.DET300.length > 0 && (
                          <div>
                            <span className="font-medium text-gray-700">DET300 ({filemakerData.DET300.length}):</span>
                            <div className="mt-1 flex flex-wrap gap-1">
                              {filemakerData.DET300.slice(0, 3).map((url, index) => (
                                <a key={index} href={url} target="_blank" rel="noopener noreferrer" 
                                   className="text-xs bg-yellow-100 text-yellow-800 px-2 py-1 rounded hover:bg-yellow-200">
                                  Detail {index + 1}
                                </a>
                              ))}
                              {filemakerData.DET300.length > 3 && (
                                <span className="text-xs text-gray-500">+{filemakerData.DET300.length - 3} more</span>
                              )}
                            </div>
                          </div>
                        )}
                        
                        {/* MAINFM Field */}
                        {filemakerData.MAINFM && (
                          <div>
                            <span className="font-medium text-gray-700">MAINFM:</span>
                            <a href={filemakerData.MAINFM} target="_blank" rel="noopener noreferrer" 
                               className="ml-2 text-xs bg-red-100 text-red-800 px-2 py-1 rounded hover:bg-red-200">
                              View Image
                            </a>
                          </div>
                        )}
                        
                        {/* MAINFMTest Field */}
                        {filemakerData.MAINFMTest && (
                          <div>
                            <span className="font-medium text-gray-700">MAINFMTest:</span>
                            <a href={filemakerData.MAINFMTest} target="_blank" rel="noopener noreferrer" 
                               className="ml-2 text-xs bg-pink-100 text-pink-800 px-2 py-1 rounded hover:bg-pink-200">
                              View Test Image
                            </a>
                          </div>
                        )}
                        
                        {/* Certificate Fields */}
                        {filemakerData.CertificateFMUrl && (
                          <div>
                            <span className="font-medium text-gray-700">Certificate:</span>
                            <a href={filemakerData.CertificateFMUrl} target="_blank" rel="noopener noreferrer" 
                               className="ml-2 text-xs bg-indigo-100 text-indigo-800 px-2 py-1 rounded hover:bg-indigo-200">
                              View Certificate
                            </a>
                          </div>
                        )}
                        
                        {filemakerData.CertificateWording && (
                          <div>
                            <span className="font-medium text-gray-700">Certificate Info:</span>
                            <p className="text-xs text-gray-600 mt-1 max-h-20 overflow-y-auto">
                              {filemakerData.CertificateWording.length > 200 
                                ? filemakerData.CertificateWording.substring(0, 200) + '...' 
                                : filemakerData.CertificateWording}
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                  
                  {/* Rename and Search Controls */}
                  <div className="flex gap-2 mt-4">
                    <button
                      onClick={() => setShowRenameForm(!showRenameForm)}
                      className="flex items-center px-3 py-1 bg-white border-2 border-gray-400 text-black rounded hover:bg-gray-100 text-sm"
                    >
                      <Edit className="h-4 w-4 mr-1" />
                      Rename (E)
                    </button>
                    
                    <button
                      onClick={() => setShowArtworkSearch(!showArtworkSearch)}
                      className="flex items-center px-3 py-1 bg-white border-2 border-blue-500 text-blue-600 rounded hover:bg-blue-50 text-sm font-medium"
                    >
                      <Search className="h-4 w-4 mr-1" />
                      🔍 Search in database (S)
                    </button>
                  </div>
                </div>

                {/* Rename form */}
                {showRenameForm && (
                  <div className="mt-4 p-4 bg-gray-50 rounded-lg">
                    <form onSubmit={handleRenameSubmit}>
                      <div className="flex items-center gap-2">
                        <input
                          type="text"
                          value={newFilename}
                          onChange={(e) => setNewFilename(e.target.value)}
                          className="flex-1 px-3 py-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                          placeholder="New filename"
                        />
                        <button
                          type="submit"
                          className="flex items-center px-3 py-2 bg-green-500 text-white rounded hover:bg-green-600"
                        >
                          <Save className="h-4 w-4 mr-1" />
                          Save
                        </button>
                        <button
                          type="button"
                          onClick={() => setShowRenameForm(false)}
                          className="flex items-center px-3 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
                        >
                          <X className="h-4 w-4" />
                        </button>
                      </div>
                    </form>
                  </div>
                )}

                {/* Artwork search */}
                {showArtworkSearch && (
                  <div className="mt-4">
                    <ArtworkSearch 
                      photoId={currentPhoto.id}
                      onArtworkFound={handleArtworkFound}
                    />
                    
                    {existingArtwork && (
                      <div className="mt-4 p-4 bg-green-50 border border-green-200 rounded">
                        <h4 className="font-semibold text-green-800 mb-3">Artwork found in database:</h4>
                        
                        <div className="mb-4">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-green-700">
                            <p><span className="font-medium">ID:</span> {existingArtwork.IdName}</p>
                            <p><span className="font-medium">Title:</span> {existingArtwork.title}</p>
                            <p><span className="font-medium">Artist:</span> {existingArtwork.artist}</p>
                            <p><span className="font-medium">Year:</span> {existingArtwork.year}</p>
                          </div>
                          {existingArtwork.description && (
                            <p className="text-sm text-green-600 mt-2">{existingArtwork.description}</p>
                          )}
                        </div>
                        
                        {existingArtwork.all_image_urls && existingArtwork.all_image_urls.length > 0 ? (
                          <div>
                            <h5 className="font-medium text-green-800 mb-3">All photos of this artwork ({existingArtwork.all_image_urls.length}):</h5>
                            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                              {existingArtwork.all_image_urls.map((imageUrl, index) => (
                                <div key={index} className="border rounded overflow-hidden bg-white shadow-sm hover:shadow-md transition-shadow">
                                  <img 
                                    src={imageUrl} 
                                    alt={`Photo ${index + 1} - ${existingArtwork.IdName}`}
                                    className="w-full h-32 object-cover hover:scale-105 transition-transform cursor-pointer"
                                    onClick={() => window.open(imageUrl, '_blank')}
                                    onError={(e) => {
                                      e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZGRkIi8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzk5OSIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlIG5vbiBkaXNwb25pYmxlPC90ZXh0Pjwvc3ZnPg==';
                                      e.target.alt = 'Image not available';
                                    }}
                                  />
                                  <div className="px-2 py-1 text-xs text-center text-gray-600 bg-gray-50">
                                    Vue {index + 1}
                                  </div>
                                </div>
                              ))}
                            </div>
                            <div className="mt-3 text-xs text-green-600 bg-green-100 p-2 rounded">
                              💡 <strong>Tip:</strong> Visually compare with the current photo. Click on an image to enlarge.
                            </div>
                          </div>
                        ) : existingArtwork.main_picture_hd ? (
                          <div>
                            <h5 className="font-medium text-green-800 mb-2">Main image available:</h5>
                            <div className="border rounded overflow-hidden bg-white inline-block">
                              <img 
                                src={existingArtwork.main_picture_hd} 
                                alt={`Artwork ${existingArtwork.IdName}`}
                                className="h-48 object-contain cursor-pointer"
                                onClick={() => window.open(existingArtwork.main_picture_hd, '_blank')}
                              />
                            </div>
                          </div>
                        ) : (
                          <div className="text-sm text-green-600 bg-green-100 p-2 rounded">
                            ℹ️ No image available for this artwork in database
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {/* Quality Analysis - Section prioritaire */}
                <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-300 rounded-lg p-4 shadow-md">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="font-bold text-black flex items-center text-lg">
                      <Camera className="h-6 w-6 mr-2 text-blue-600" />
                      📐 A5 Print Quality
                    </h4>
                  </div>
                  
                  {qualityAnalyzing ? (
                    <div className="flex items-center justify-center py-6">
                      <Loader className="h-8 w-8 text-blue-500 animate-spin mr-3" />
                      <span className="text-blue-600 text-lg">Analysis in progress...</span>
                    </div>
                  ) : qualityAnalysis ? (
                    <div>
                      <div className="flex items-center mb-4 p-3 rounded-lg bg-white border">
                        <div className="mr-4">
                          {getQualityIcon(qualityAnalysis)}
                        </div>
                        <div className="flex-1">
                          <span className={`font-bold text-xl ${
                            qualityAnalysis.color_code === 'green' ? 'text-green-600' :
                            qualityAnalysis.color_code === 'lightgreen' ? 'text-green-500' :
                            qualityAnalysis.color_code === 'orange' ? 'text-orange-600' :
                            qualityAnalysis.color_code === 'red' ? 'text-red-600' : 'text-gray-600'
                          }`}>
                            {qualityAnalysis.print_quality_a5}
                          </span>
                          <div className="text-sm text-gray-600 mt-1">
                            This photo {qualityAnalysis.color_code === 'red' ? 'is NOT' : 'is'} suitable for A5 printing
                          </div>
                        </div>
                      </div>
                      
                      {!qualityAnalysis.error && (
                        <div className="grid grid-cols-2 gap-4 text-sm mb-4 bg-white p-3 rounded-lg">
                          <div className="text-black">
                            <span className="font-bold">🔍 A5 equivalent DPI:</span> 
                            <span className={`ml-2 font-mono text-lg ${
                              qualityAnalysis.equivalent_dpi_a5 >= 300 ? 'text-green-600' :
                              qualityAnalysis.equivalent_dpi_a5 >= 200 ? 'text-orange-500' :
                              qualityAnalysis.equivalent_dpi_a5 >= 150 ? 'text-orange-600' : 'text-red-600'
                            }`}>
                              {qualityAnalysis.equivalent_dpi_a5}
                            </span>
                          </div>
                          <div className="text-black">
                            <span className="font-bold">📏 Resolution:</span> 
                            <span className="ml-2 font-mono">{qualityAnalysis.dimensions?.width} × {qualityAnalysis.dimensions?.height}</span>
                          </div>
                          <div className="text-black">
                            <span className="font-bold">💾 File size:</span> 
                            <span className="ml-2">{qualityAnalysis.file_size_mb} MB</span>
                          </div>
                          <div className="text-black">
                            <span className="font-bold">📄 Format:</span> 
                            <span className="ml-2">{qualityAnalysis.format}</span>
                          </div>
                        </div>
                      )}
                      
                      {qualityAnalysis.recommendations && qualityAnalysis.recommendations.length > 0 && (
                        <div className="bg-blue-100 p-3 rounded-lg mb-3">
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
                      
                      {qualityAnalysis.validation_issues && qualityAnalysis.validation_issues.length > 0 && (
                        <div className="bg-red-100 p-3 rounded-lg border border-red-200">
                          <p className="font-medium text-red-800 mb-2">⚠️ Issues detected:</p>
                          <ul className="text-sm text-red-700 space-y-1">
                            {qualityAnalysis.validation_issues.map((issue, i) => (
                              <li key={i} className="flex items-start">
                                <span className="mr-2">•</span>
                                <span>{issue}</span>
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="text-center py-6 text-gray-500">
                      <Camera className="h-12 w-12 mx-auto mb-3 text-gray-400" />
                      <p className="text-lg mb-2">Quality not analyzed</p>
                      <p className="text-sm">Click "Analyze" to check A5 print quality</p>
                    </div>
                  )}
                </div>
                
                {/* Artwork Metadata from OperaCRM */}
                {existingArtwork && (
                  <div className="bg-white border-2 border-green-400 rounded-lg p-4">
                    <h4 className="font-bold text-black mb-3 flex items-center">
                      🎨 OperaCRM Information
                      <span className="ml-2 px-2 py-1 text-xs bg-green-100 text-green-800 rounded">
                        Found in OperaCRM
                      </span>
                    </h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                      <div>
                        <div className="text-black mb-2">
                          <span className="font-bold">ID:</span> 
                          <span className="ml-2 font-mono text-blue-600">{existingArtwork.IdName}</span>
                        </div>
                        <div className="text-black mb-2">
                          <span className="font-bold">Artist:</span> 
                          <span className="ml-2">{existingArtwork.artist}</span>
                        </div>
                        <div className="text-black mb-2">
                          <span className="font-bold">Title:</span> 
                          <span className="ml-2">{existingArtwork.title}</span>
                        </div>
                        <div className="text-black mb-2">
                          <span className="font-bold">Year:</span> 
                          <span className="ml-2">{existingArtwork.year}</span>
                        </div>
                      </div>
                      <div>
                        <div className="text-black mb-2">
                          <span className="font-bold">Category:</span> 
                          <span className="ml-2">{existingArtwork.category}</span>
                        </div>
                        <div className="text-black mb-2">
                          <span className="font-bold">Medium:</span> 
                          <span className="ml-2">{existingArtwork.medium}</span>
                        </div>
                        <div className="text-black mb-2">
                          <span className="font-bold">Dimensions:</span> 
                          <span className="ml-2">{existingArtwork.dimensions}</span>
                        </div>
                        <div className="text-black mb-2">
                          <span className="font-bold">Existing images:</span> 
                          <span className="ml-2">{existingArtwork.image_count} photo(s)</span>
                        </div>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm mt-3">
                      <div>
                        <div className="text-black mb-2">
                          <span className="font-bold">Location:</span> 
                          <span className="ml-2">{existingArtwork.location}</span>
                        </div>
                        <div className="text-black mb-2">
                          <span className="font-bold">Status:</span> 
                          <span className="ml-2">{existingArtwork.status}</span>
                        </div>
                      </div>
                      <div>
                        {existingArtwork.price_estimate && (
                          <div className="text-black mb-2">
                            <span className="font-bold">Price:</span> 
                            <span className="ml-2 text-green-700 font-semibold">{existingArtwork.price_estimate}</span>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    {/* Quality Analysis of OperaCRM Photos */}
                    {existingArtwork.all_image_urls && existingArtwork.all_image_urls.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-gray-300">
                        <h5 className="font-bold text-black mb-3 flex items-center">
                          <Camera className="h-4 w-4 mr-2 text-blue-600" />
                          📊 OperaCRM photos quality ({existingArtwork.all_image_urls.length})
                        </h5>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {existingArtwork.all_image_urls.slice(0, 4).map((imageUrl, index) => (
                            <div key={index} className="border border-green-200 rounded-lg overflow-hidden bg-gray-50">
                              <div className="relative">
                                <img 
                                  src={imageUrl} 
                                  alt={`OperaCRM Photo ${index + 1}`}
                                  className="w-full h-24 object-cover hover:scale-105 transition-transform cursor-pointer"
                                  onClick={() => window.open(imageUrl, '_blank')}
                                  onError={(e) => {
                                    e.target.style.display = 'none';
                                    e.target.nextSibling.style.display = 'block';
                                  }}
                                />
                                <div className="hidden absolute inset-0 bg-gray-200 flex items-center justify-center text-gray-500 text-xs">
                                  Image not accessible
                                </div>
                              </div>
                              <div className="p-2">
                                <div className="flex items-center justify-between mb-1">
                                  <span className="text-xs font-medium text-gray-700">Photo {index + 1}</span>
                                  <ExistingPhotoQuality imageUrl={imageUrl} />
                                </div>
                                <div className="text-xs text-gray-600">
                                  💡 Click to enlarge
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                        {existingArtwork.all_image_urls.length > 4 && (
                          <p className="text-xs text-gray-600 mt-2">
                            +{existingArtwork.all_image_urls.length - 4} more photos...
                          </p>
                        )}
                      </div>
                    )}
                    
                    {existingArtwork.description && (
                      <div className="mt-3 pt-3 border-t border-gray-300">
                        <div className="text-black">
                          <span className="font-bold">Description:</span> 
                          <p className="mt-1 text-sm">{existingArtwork.description}</p>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Duplicate Warning with Quality Info */}
                {currentPhoto.duplicate_warning && (
                  <div className="bg-white border-2 border-orange-400 rounded-lg p-4">
                    <h4 className="font-bold text-orange-800 mb-3 flex items-center">
                      ⚠️ Potential duplicate detected
                    </h4>
                    <p className="text-orange-700 mb-4">
                      This photo appears to match an artwork already present in the Odoo database.
                    </p>
                    
                    {/* Existing Artwork Info */}
                    {existingArtwork && (
                      <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mb-4">
                        <h5 className="font-semibold text-orange-800 mb-2">Existing artwork information:</h5>
                        <div className="text-sm text-orange-700 space-y-1">
                          <div><strong>ID:</strong> {existingArtwork.IdName}</div>
                          <div><strong>Title:</strong> {existingArtwork.title}</div>
                          <div><strong>Artist:</strong> {existingArtwork.artist}</div>
                          <div><strong>Photos:</strong> {existingArtwork.image_count}</div>
                        </div>
                      </div>
                    )}
                    
                    {currentPhoto.artwork_metadata && currentPhoto.artwork_metadata.all_image_urls && currentPhoto.artwork_metadata.all_image_urls.length > 0 && (
                      <div>
                        <p className="text-orange-700 text-sm font-medium mb-3">
                          Existing photos in Odoo ({currentPhoto.artwork_metadata.all_image_urls.length}):
                        </p>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {currentPhoto.artwork_metadata.all_image_urls.slice(0, 4).map((imageUrl, index) => (
                            <div key={index} className="border-2 border-orange-200 rounded-lg overflow-hidden bg-white">
                              <div className="relative">
                                <img 
                                  src={imageUrl} 
                                  alt={`Existing photo ${index + 1}`}
                                  className="w-full h-32 object-cover hover:scale-105 transition-transform cursor-pointer"
                                  onClick={() => window.open(imageUrl, '_blank')}
                                  onError={(e) => {
                                    e.target.style.display = 'none';
                                    e.target.nextSibling.style.display = 'block';
                                  }}
                                />
                                <div className="hidden absolute inset-0 bg-gray-200 flex items-center justify-center text-gray-500 text-sm">
                                  Image not accessible
                                </div>
                              </div>
                              <div className="p-2">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="text-xs font-medium text-gray-700">Photo {index + 1}</span>
                                  <ExistingPhotoQuality imageUrl={imageUrl} />
                                </div>
                                <div className="text-xs text-gray-600">
                                  💡 Click to enlarge
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                        {currentPhoto.artwork_metadata.all_image_urls.length > 4 && (
                          <p className="text-xs text-orange-600 mt-2">
                            +{currentPhoto.artwork_metadata.all_image_urls.length - 4} more photos...
                          </p>
                        )}
                      </div>
                    )}
                    
                    {/* Action buttons */}
                    <div className="flex gap-3 mt-4 pt-3 border-t border-orange-200">
                      <button
                        onClick={() => {
                          setRejectReason('Potential duplicate found in Odoo');
                          setShowRejectForm(true);
                        }}
                        className="flex items-center px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600 text-sm font-medium"
                      >
                        <X className="w-4 h-4 mr-2" />
                        Reject as duplicate
                      </button>
                      <button
                        onClick={() => {
                          setShowDuplicateWarning(false);
                          setDuplicateDetection(null);
                        }}
                        className="flex items-center px-4 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 text-sm font-medium"
                      >
                        <CheckCircle className="w-4 h-4 mr-2" />
                        Continue anyway
                      </button>
                    </div>
                  </div>
                )}
                
                {fileDetails && (
                  <div className="bg-white border-2 border-gray-300 rounded-lg p-4">
                    <h4 className="font-bold text-black mb-3">📄 Technical Information</h4>
                    <div className="grid grid-cols-2 gap-3 text-sm">
                      <div className="text-black">
                        <span className="font-bold">Dimensions:</span> 
                        <span className="ml-2">{fileDetails.width} × {fileDetails.height} px</span>
                      </div>
                      <div className="text-black">
                        <span className="font-bold">Size:</span> 
                        <span className="ml-2">{fileDetails.size}</span>
                      </div>
                      <div className="text-black">
                        <span className="font-bold">Type:</span> 
                        <span className="ml-2">{fileDetails.type}</span>
                      </div>
                      <div className="text-black">
                        <span className="font-bold">Paper format:</span> 
                        <span className="ml-2">{fileDetails.paperFormat}</span>
                      </div>
                    </div>
                  </div>
                )}

              </div>


              {/* Duplicate warning */}
              {showDuplicateWarning && duplicateDetection && (
                <div className="mt-4 p-4 bg-orange-50 border border-orange-200 rounded-lg">
                  <div className="flex items-start mb-4">
                    <AlertTriangle className="h-6 w-6 text-orange-500 mr-3 mt-1" />
                    <div className="flex-1">
                      <h4 className="font-semibold text-orange-800 mb-2">Potential duplicate detected</h4>
                      <p className="text-orange-700 text-sm mb-3">
                        This photo appears to match an artwork already present in the Odoo database.
                      </p>
                      
                      <div className="mb-4">
                        <h5 className="font-medium text-orange-800 mb-2">Existing artwork information:</h5>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-sm text-orange-700">
                          <p><span className="font-medium">ID:</span> {duplicateDetection.artwork.IdName}</p>
                          <p><span className="font-medium">Title:</span> {duplicateDetection.artwork.title}</p>
                          <p><span className="font-medium">Artist:</span> {duplicateDetection.artwork.artist}</p>
                          <p><span className="font-medium">Photos:</span> {duplicateDetection.artwork.image_count || 'N/A'}</p>
                        </div>
                      </div>
                      
                      {duplicateDetection.artwork.all_image_urls && duplicateDetection.artwork.all_image_urls.length > 0 && (
                        <div className="mb-4">
                          <h5 className="font-medium text-orange-800 mb-3">Existing photos in Odoo ({duplicateDetection.artwork.all_image_urls.length}):</h5>
                          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
                            {duplicateDetection.artwork.all_image_urls.map((imageUrl, index) => (
                              <div key={index} className="border rounded overflow-hidden bg-white">
                                <img 
                                  src={imageUrl} 
                                  alt={`Photo ${index + 1}`}
                                  className="w-full h-24 object-cover hover:scale-105 transition-transform cursor-pointer"
                                  onClick={() => window.open(imageUrl, '_blank')}
                                  onError={(e) => {
                                    e.target.style.display = 'none';
                                  }}
                                />
                                <div className="px-2 py-1 text-xs text-center text-gray-600">
                                  Photo {index + 1}
                                </div>
                              </div>
                            ))}
                          </div>
                          <p className="text-xs text-orange-600 mt-2">
                            💡 Click on a photo to enlarge it
                          </p>
                        </div>
                      )}
                      
                      <div className="flex gap-2 mt-4">
                        <button
                          onClick={() => {
                            setRejectReason('Potential duplicate found in Odoo');
                            setShowRejectForm(true);
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

        {/* Main validation area */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          
          {error && (
            <div className="p-6">
              <ErrorAlert 
                message={error} 
                onDismiss={() => setError(null)}
              />
            </div>
          )}

          {/* Image display */}
          <div className="relative" style={{ height: currentPhoto && (showDuplicateWarning || existingArtwork) ? '50vh' : '70vh', minHeight: '400px' }}>
            {loading ? (
              <div className="absolute inset-0 flex items-center justify-center bg-white">
                <div className="text-center">
                  <Loader className="h-12 w-12 text-black animate-spin mx-auto mb-4" />
                  <p className="text-black">Loading photo...</p>
                </div>
              </div>
            ) : currentPhoto ? (
              <>
                {currentPhoto.file_type === 'video' ? (
                  <div className="w-full h-full bg-black flex flex-col items-center justify-center">
                    <video
                      key={currentPhoto.id}
                      controls
                      preload="metadata"
                      className="w-full h-full object-contain"
                      onLoadedMetadata={() => setImageLoading(false)}
                      onError={() => {
                        setImageLoading(false);
                        setError('Video load failed. File may still be uploading.');
                      }}
                    >
                      <source src={`/api/photos/${encodeURIComponent(currentPhoto.id)}`} />
                      Your browser does not support video.
                    </video>
                  </div>
                ) : (
                <>
                {imageLoading && (
                  <div className="absolute inset-0 flex items-center justify-center bg-white z-10">
                    <div className="text-center">
                      <Loader className="h-8 w-8 text-black animate-spin mx-auto mb-2" />
                      <p className="text-black text-sm">Loading image...</p>
                    </div>
                  </div>
                )}
                <img
                  src={getImageUrl()}
                  alt={`Photo: ${currentPhoto.filename}`}
                  className="w-full h-full object-contain bg-gray-50"
                  onLoad={() => setImageLoading(false)}
                  onError={(e) => {
                    // Image load failed
                    setImageLoading(false);
                    setError('Unable to load image. File may be too large or corrupted.');
                  }}
                  loading="lazy"
                  style={{ maxWidth: '100%', maxHeight: '100%' }}
                />
                </>
                )}
              </>
            ) : (
              <div className="absolute inset-0 flex items-center justify-center bg-gray-50">
                <div className="text-center">
                  <div className="text-6xl mb-4">📷</div>
                  <p className="text-gray-600 text-lg mb-4">No photos to validate</p>
                  <button
                    onClick={fetchNextPhoto}
                    className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 flex items-center mx-auto"
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Validation controls */}
          {currentPhoto && (
            <div className="p-6 bg-white border-t-2 border-gray-300">
              
              {/* Reject form */}
              {showRejectForm && (
                <div className="mb-6 p-6 bg-white border-2 border-red-300 rounded-lg shadow-lg">
                  <h3 className="text-xl font-bold text-black mb-6 flex items-center">
                    <AlertTriangle className="h-6 w-6 mr-3 text-red-500" />
                    Rejection reason
                  </h3>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-6">
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
                        <span className="text-black font-medium">{reason}</span>
                      </label>
                    ))}
                  </div>
                  
                  {rejectReason === 'Autre (préciser)' && (
                    <textarea
                      value={customReason}
                      onChange={(e) => setCustomReason(e.target.value)}
                      placeholder="Précisez le motif de rejet..."
                      className="w-full px-4 py-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500 mb-6 text-black bg-white"
                      rows="4"
                    />
                  )}
                  
                  <div className="flex gap-3">
                    <button
                      onClick={handleRejectSubmit}
                      disabled={validationLoading || !rejectReason}
                      className="px-6 py-3 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {validationLoading ? 'Processing...' : 'Confirm rejection'}
                    </button>
                    <button
                      onClick={() => {
                        setShowRejectForm(false);
                        setRejectReason('');
                        setCustomReason('');
                      }}
                      className="px-6 py-3 bg-gray-600 text-white font-semibold rounded-lg hover:bg-gray-700 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
              
              {/* Classification form */}
              {showClassificationForm && (
                <div className="mb-6 p-6 bg-white border-2 border-green-400 rounded-lg shadow-lg">
                  <h3 className="text-xl font-bold text-black mb-6 flex items-center">
                    <ThumbsUp className="h-6 w-6 mr-3 text-green-600" />
                    Photo classification
                  </h3>
                  
                  <div className="grid grid-cols-1 gap-3 mb-6">
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
                        <span className="text-black font-medium">{classif.label}</span>
                      </label>
                    ))}
                  </div>
                  
                  <div className="flex gap-3">
                    <button
                      onClick={handleValidateSubmit}
                      disabled={validationLoading || !classification}
                      className="px-6 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    >
                      {validationLoading ? 'Processing...' : 'Confirm validation'}
                    </button>
                    <button
                      onClick={() => {
                        setShowClassificationForm(false);
                        setClassification('');
                      }}
                      className="px-6 py-3 bg-gray-600 text-white font-semibold rounded-lg hover:bg-gray-700 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
              
              <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
                
                <button
                  onClick={() => handleSimpleValidation(false)}
                  disabled={validationLoading}
                  className={`flex items-center px-8 py-3 font-bold rounded-lg transition-all duration-200 border-2 ${
                    validationLoading 
                      ? 'bg-gray-400 border-gray-400 cursor-not-allowed' 
                      : 'bg-red-600 border-red-700 hover:bg-red-700 hover:scale-105 active:scale-95'
                  } text-white`}
                >
                  {validationLoading ? (
                    <Loader className="h-5 w-5 mr-2 animate-spin" />
                  ) : (
                    <ThumbsDown className="h-5 w-5 mr-2" />
                  )}
                  {validationLoading ? 'Processing...' : 'Reject (Q or ←)'}
                </button>

                <div className="flex flex-col items-center text-sm text-black">
                  <RefreshCw 
                    className="h-6 w-6 mb-1 cursor-pointer hover:text-gray-600 text-black" 
                    onClick={fetchNextPhoto}
                  />
                  <span>R to refresh</span>
                </div>

                <div className="flex flex-col items-center text-sm text-black">
                  <Star 
                    className={`h-6 w-6 mb-1 cursor-pointer hover:text-yellow-600 ${
                      isPhotoMarked ? 'text-yellow-500 fill-current' : 'text-black'
                    }`}
                    onClick={isPhotoMarked ? handleUnmarkPhoto : () => setShowMarkDialog(true)}
                  />
                 <span>{isPhotoMarked ? 'Marked' : 'Mark'}</span>
                </div>

                <button
                  onClick={() => handleSimpleValidation(true)}
                  disabled={validationLoading}
                  className={`flex items-center px-8 py-3 font-bold rounded-lg transition-all duration-200 border-2 ${
                    validationLoading 
                      ? 'bg-gray-400 border-gray-400 cursor-not-allowed' 
                      : 'bg-green-600 border-green-700 hover:bg-green-700 hover:scale-105 active:scale-95'
                  } text-white`}
                >
                  {validationLoading ? (
                    <Loader className="h-5 w-5 mr-2 animate-spin" />
                  ) : (
                    <ThumbsUp className="h-5 w-5 mr-2" />
                  )}
                  {validationLoading ? 'Validating...' : 'Validate (D or →)'}
                </button>
                
              </div>
              
              <div className="text-center mt-4 text-sm text-black">
                Shortcuts: Q/← Reject • D/→ Validate • R Refresh • E Rename • S Search
                {autoSearchLoading && (
                  <div className="mt-2 flex items-center justify-center text-black">
                    <Loader className="h-4 w-4 animate-spin mr-2 text-black" />
                    Automatic duplicate check...
                  </div>
                )}
                {autoSearchCompleted && !duplicateDetection && (
                  <div className="mt-2 text-black text-xs">
                    ✓ No duplicates detected automatically
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Mark Photo Dialog */}
      {showMarkDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
            <h3 className="text-lg font-bold mb-4">Mark the photo</h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Note (optional)
              </label>
              <textarea
                value={markNote}
                onChange={(e) => setMarkNote(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md"
                rows="3"
                placeholder="Add a personal note for this photo..."
              />
            </div>
            <div className="flex justify-end space-x-2">
              <button
                onClick={() => setShowMarkDialog(false)}
                className="px-4 py-2 text-gray-600 hover:text-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleMarkPhoto}
                className="px-4 py-2 bg-yellow-500 text-white rounded hover:bg-yellow-600"
              >
                Mark
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default PhotoValidator;
