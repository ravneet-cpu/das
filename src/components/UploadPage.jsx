// src/components/UploadPage.jsx
import React, { useState, useRef } from 'react';
import { Upload, X, AlertCircle, CheckCircle, Image, Camera, Info, Loader, Search, Eye } from 'lucide-react';

export function UploadPage() {
  const [files, setFiles] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const [validationResults, setValidationResults] = useState(null);
  const [error, setError] = useState(null);
  const [fileQualities, setFileQualities] = useState({});
  const [analyzingFiles, setAnalyzingFiles] = useState({});
  const [customFilenames, setCustomFilenames] = useState({});
  const [artworkSearchResults, setArtworkSearchResults] = useState({});
  const [searchingArtworks, setSearchingArtworks] = useState({});
  const [manualSearchQuery, setManualSearchQuery] = useState('');
  const [manualSearchResults, setManualSearchResults] = useState([]);
  const [manualSearchLoading, setManualSearchLoading] = useState(false);
  const fileInputRef = useRef(null);

  // Utility function to detect file type
  const getFileType = (filename) => {
    const ext = filename.toLowerCase().split('.').pop();
    
    const imageExts = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'tiff', 'tif'];
    const pdfExts = ['pdf'];
    const videoExts = ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv'];
    
    if (imageExts.includes(ext)) return 'image';
    if (pdfExts.includes(ext)) return 'pdf';
    if (videoExts.includes(ext)) return 'video';
    return 'unknown';
  };

  // Get button text based on file types
  const getButtonText = () => {
    if (files.length === 0) return 'No files selected';
    
    const fileTypes = files.map(file => getFileType(file.name));
    const hasImages = fileTypes.includes('image');
    const hasPdfs = fileTypes.includes('pdf');
    const hasVideos = fileTypes.includes('video');
    
    let types = [];
    if (hasImages) types.push('images');
    if (hasPdfs) types.push('PDFs');
    if (hasVideos) types.push('videos');
    
    if (types.length === 1) {
      return `Verify ${types[0]}`;
    } else if (types.length === 2) {
      return `Verify ${types[0]} & ${types[1]}`;
    } else if (types.length === 3) {
      return 'Verify files';
    } else {
      return 'Verify files';
    }
  };

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files);
    const newFiles = [...files, ...selectedFiles];
    setFiles(newFiles);
    
    // Initialize custom filenames and search for artworks
    selectedFiles.forEach((file, index) => {
      const fileIndex = files.length + index;
      setCustomFilenames(prev => ({ ...prev, [fileIndex]: file.name }));
      analyzeFileQuality(file, fileIndex);
      // searchArtworkFromFilename removed - artwork search now handled by validate-upload endpoint
    });
  };

  const removeFile = (index) => {
    setFiles(prevFiles => prevFiles.filter((_, i) => i !== index));
    // Also clean quality data and custom filenames
    setFileQualities(prev => {
      const newQualities = {...prev};
      delete newQualities[index];
      return newQualities;
    });
    setAnalyzingFiles(prev => {
      const newAnalyzing = {...prev};
      delete newAnalyzing[index];
      return newAnalyzing;
    });
    setCustomFilenames(prev => {
      const newCustom = {...prev};
      delete newCustom[index];
      return newCustom;
    });
    setArtworkSearchResults(prev => {
      const newResults = {...prev};
      delete newResults[index];
      return newResults;
    });
    setSearchingArtworks(prev => {
      const newSearching = {...prev};
      delete newSearching[index];
      return newSearching;
    });
  };

  // Analyze file quality client-side (quick estimation)
  const analyzeFileQuality = async (file, fileIndex) => {
    setAnalyzingFiles(prev => ({ ...prev, [fileIndex]: true }));
    
    try {
      // Analyze file client-side for quick estimation
      const img = new window.Image();
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      
      img.onload = () => {
        const width = img.naturalWidth;
        const height = img.naturalHeight;
        
        // Calculate A5 equivalent DPI
        const a5WidthInches = 5.83;
        const a5HeightInches = 8.27;
        const dpiWidth = width / a5WidthInches;
        const dpiHeight = height / a5HeightInches;
        const equivalentDpi = Math.min(dpiWidth, dpiHeight);
        
        // Determine quality
        let qualityLevel, colorCode, description;
        if (equivalentDpi >= 300) {
          qualityLevel = 'excellent';
          colorCode = 'green';
          description = 'Excellent quality for A5 printing (≥300 DPI)';
        } else if (equivalentDpi >= 200) {
          qualityLevel = 'good';
          colorCode = 'lightgreen';
          description = 'Good quality for A5 printing (≥200 DPI)';
        } else if (equivalentDpi >= 150) {
          qualityLevel = 'acceptable';
          colorCode = 'orange';
          description = 'Acceptable quality for A5 printing (≥150 DPI)';
        } else {
          qualityLevel = 'poor';
          colorCode = 'red';
          description = 'Insufficient quality for A5 printing (<150 DPI)';
        }
        
        const analysis = {
          dimensions: { width, height },
          equivalent_dpi_a5: Math.round(equivalentDpi * 10) / 10,
          file_size_mb: Math.round(file.size / 1024 / 1024 * 100) / 100,
          quality_level: qualityLevel,
          color_code: colorCode,
          print_quality_a5: description,
          format: file.type.split('/')[1].toUpperCase(),
          estimated: true
        };
        
        setFileQualities(prev => ({ ...prev, [fileIndex]: analysis }));
        setAnalyzingFiles(prev => ({ ...prev, [fileIndex]: false }));
      };
      
      img.onerror = async () => {
        // Client-side analysis failed, falling back to server-side analysis
        
        // Set loading state with informative message
        setFileQualities(prev => ({ 
          ...prev, 
          [fileIndex]: {
            error: 'Browser analysis failed. Starting server analysis - this may take some time...',
            quality_level: 'loading',
            color_code: 'blue',
            server_analysis_pending: true
          }
        }));
        
        // Try server-side analysis as fallback
        try {
          const formData = new FormData();
          formData.append('file', file);
          
          const response = await fetch('/api/photos/analyze-single', {
            method: 'POST',
            headers: {
              'Authorization': `Bearer ${localStorage.getItem('token')}`
            },
            body: formData
          });
          
          if (response.ok) {
            const serverAnalysis = await response.json();
            if (serverAnalysis.success) {
              setFileQualities(prev => ({ 
                ...prev, 
                [fileIndex]: {
                  ...serverAnalysis.quality_analysis,
                  server_analyzed: true,
                  estimated: false
                }
              }));
            } else {
              throw new Error(serverAnalysis.error || 'Server analysis failed');
            }
          } else {
            throw new Error('Server analysis request failed');
          }
        } catch (serverErr) {
          console.error('Server analysis also failed:', serverErr);
          setFileQualities(prev => ({ 
            ...prev, 
            [fileIndex]: {
              error: 'File analysis failed (both browser and server). The file may be corrupted or in an unsupported format.',
              quality_level: 'error',
              color_code: 'red',
              server_analysis_failed: true
            }
          }));
        }
        
        setAnalyzingFiles(prev => ({ ...prev, [fileIndex]: false }));
      };
      
      // Create URL for image
      const fileReader = new FileReader();
      fileReader.onload = (e) => {
        img.src = e.target.result;
      };
      fileReader.readAsDataURL(file);
      
    } catch (err) {
      console.error('Error analyzing file:', err);
      
      // Try server-side analysis as fallback for catch block errors too
      try {
        setFileQualities(prev => ({ 
          ...prev, 
          [fileIndex]: {
            error: 'Initial analysis failed. Starting server analysis - this may take some time...',
            quality_level: 'loading',
            color_code: 'blue',
            server_analysis_pending: true
          }
        }));
        
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/photos/analyze-single', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: formData
        });
        
        if (response.ok) {
          const serverAnalysis = await response.json();
          if (serverAnalysis.success) {
            setFileQualities(prev => ({ 
              ...prev, 
              [fileIndex]: {
                ...serverAnalysis.quality_analysis,
                server_analyzed: true,
                estimated: false
              }
            }));
          } else {
            throw new Error(serverAnalysis.error || 'Server analysis failed');
          }
        } else {
          throw new Error('Server analysis request failed');
        }
      } catch (serverErr) {
        console.error('Server analysis also failed:', serverErr);
        setFileQualities(prev => ({ 
          ...prev, 
          [fileIndex]: {
            error: 'File analysis failed completely. The file may be corrupted, too large, or in an unsupported format.',
            quality_level: 'error',
            color_code: 'red',
            analysis_failed: true
          }
        }));
      }
      
      setAnalyzingFiles(prev => ({ ...prev, [fileIndex]: false }));
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const droppedFiles = Array.from(e.dataTransfer.files);
      const currentFileCount = files.length;
      setFiles(prevFiles => [...prevFiles, ...droppedFiles]);
      
      // Initialize custom filenames, analyze quality and search artworks
      droppedFiles.forEach((file, index) => {
        const fileIndex = currentFileCount + index;
        setCustomFilenames(prev => ({ ...prev, [fileIndex]: file.name }));
        analyzeFileQuality(file, fileIndex);
        // searchArtworkFromFilename removed - artwork search now handled by validate-upload endpoint
      });
    }
  };

  // Removed searchArtworkFromFilename - artwork search now handled by validate-upload endpoint

  // Manual search function for additional verification
  const performManualSearch = async (query) => {
    if (!query.trim()) {
      setManualSearchResults([]);
      return;
    }

    setManualSearchLoading(true);

    try {
      const response = await fetch(`/api/operacrm/search?q=${encodeURIComponent(query)}&limit=10000`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        const responseText = await response.text();
        console.log('Search response:', responseText);
        
        if (!responseText.trim()) {
          console.error('Empty response received');
          setManualSearchResults([]);
          return;
        }
        
        let data;
        try {
          data = JSON.parse(responseText);
        } catch (jsonError) {
          console.error('JSON parse error:', jsonError, 'Response text:', responseText);
          setManualSearchResults([]);
          return;
        }
        
        const artworks = data.artworks || data.photos || []; // Handle both formats
        if (data.success && artworks.length > 0) {
          // For each artwork, also search for existing photos
          const artworksWithPhotos = await Promise.all(
            artworks.map(async (artwork) => {
              try {
                const artworkId = artwork.IdName || artwork.id;
                const photosResponse = await fetch(`/api/photos/list?artwork_id=${encodeURIComponent(artworkId)}`, {
                  headers: {
                    'Authorization': `Bearer ${localStorage.getItem('token')}`
                  }
                });
                
                let existingPhotos = [];
                if (photosResponse.ok) {
                  const photosData = await photosResponse.json();
                  existingPhotos = photosData.photos || [];
                }
                
                return {
                  ...artwork,
                  existingPhotos,
                  // Normalize field names for consistent display
                  IdName: artwork.IdName || artwork.id,
                  title: artwork.title || artwork.name,
                  main_picture_hd: artwork.main_picture_hd || artwork.images?.primary_image
                };
              } catch (error) {
                return {
                  ...artwork,
                  existingPhotos: [],
                  // Normalize field names for consistent display
                  IdName: artwork.IdName || artwork.id,
                  title: artwork.title || artwork.name,
                  main_picture_hd: artwork.main_picture_hd || artwork.images?.primary_image
                };
              }
            })
          );
          
          setManualSearchResults(artworksWithPhotos);
        } else {
          setManualSearchResults([]);
        }
      } else {
        console.error('Search request failed:', response.status, response.statusText);
        const errorText = await response.text();
        console.error('Error response:', errorText);
        setManualSearchResults([]);
      }
    } catch (error) {
      console.error('Manual search error:', error);
      setManualSearchResults([]);
    } finally {
      setManualSearchLoading(false);
    }
  };

  const handleManualSearch = (e) => {
    e.preventDefault();
    performManualSearch(manualSearchQuery);
  };

  const validateFiles = async () => {
    setUploading(true);
    setError(null);
    setValidationResults(null);
    
    try {
      const validationPromises = files.map(async (file) => {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/photos/validate-upload-metadata', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          },
          body: formData
        });
        
        const result = await response.json();
        
        if (!response.ok) {
          throw new Error(result.error || 'Validation error');
        }
        
        return {
          file: file,
          ...result
        };
      });
      
      const results = await Promise.all(validationPromises);
      setValidationResults(results);
      
    } catch (err) {
      console.error('Validation error:', err);
      setError(err.message || 'An error occurred during validation');
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (files.length === 0) {
      setError('Please select at least one file to upload');
      return;
    }
    
    // First validate files
    await validateFiles();
  };

  const confirmUpload = async () => {
    setUploading(true);
    setError(null);
    
    try {
      const uploadPromises = files.map(async (file, index) => {
        const formData = new FormData();
        formData.append('file', file);
        
        // Add custom filename if provided
        const customName = customFilenames[index];
        if (customName && customName !== file.name) {
          formData.append('custom_filename', customName);
        }
        
        const response = await fetch('/api/photos/upload', {
          method: 'POST',
          body: formData,
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        });
        
        const result = await response.json();
        
        if (!response.ok) {
          throw new Error(result.error || 'Upload error');
        }
        
        return {
          file: file,
          success: true,
          filename: result.filename,
          original_filename: result.original_filename
        };
      });
      
      const uploadResults = await Promise.all(uploadPromises);
      
      // Clear files and validation results after successful upload
      setFiles([]);
      setValidationResults(null);
      setCustomFilenames({});
      setArtworkSearchResults({});
      setSearchingArtworks({});
      setManualSearchQuery('');
      setManualSearchResults([]);
      
      // Show success message
      setError(null);
      alert(`Upload successful! ${uploadResults.length} file(s) uploaded.`);
      
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      
    } catch (err) {
      console.error('Upload error:', err);
      setError(err.message || 'An error occurred during upload');
    } finally {
      setUploading(false);
    }
  };

  const truncateFilename = (filename, maxLength = 30) => {
    if (filename.length <= maxLength) return filename;
    const ext = filename.split('.').pop();
    const name = filename.substring(0, filename.length - ext.length - 1);
    return `${name.substring(0, maxLength - ext.length - 3)}...${ext}`;
  };

  const getQualityIcon = (colorCode) => {
    const baseClasses = "w-5 h-5 rounded-full flex items-center justify-center";
    switch(colorCode) {
      case 'green':
        return <div className={`${baseClasses} bg-green-500`} title="Excellent quality"><CheckCircle className="w-3 h-3 text-white" /></div>;
      case 'lightgreen':
        return <div className={`${baseClasses} bg-green-400`} title="Good quality"><CheckCircle className="w-3 h-3 text-white" /></div>;
      case 'orange':
        return <div className={`${baseClasses} bg-orange-500`} title="Acceptable quality"><AlertCircle className="w-3 h-3 text-white" /></div>;
      case 'red':
        return <div className={`${baseClasses} bg-red-500`} title="Analysis failed"><X className="w-3 h-3 text-white" /></div>;
      case 'blue':
        return <div className={`${baseClasses} bg-blue-500`} title="Server analysis in progress"><Loader className="w-3 h-3 text-white animate-spin" /></div>;
      case 'gray':
        return <div className={`${baseClasses} bg-gray-500`} title="Analysis error"><AlertCircle className="w-3 h-3 text-white" /></div>;
      default:
        return <div className={`${baseClasses} bg-gray-500`} title="Analysis in progress"><Info className="w-3 h-3 text-white" /></div>;
    }
  };

  const getUploadRecommendation = (qualities) => {
    const poorQualities = Object.values(qualities).filter(q => q.quality_level === 'poor');
    const excellentQualities = Object.values(qualities).filter(q => q.quality_level === 'excellent');
    const totalAnalyzed = Object.values(qualities).filter(q => !q.error).length;
    
    if (poorQualities.length > 0) {
      return {
        type: 'warning',
        message: `⚠️ ${poorQualities.length} photo(s) with insufficient quality for A5 printing. Consider using higher resolution images.`,
        color: 'red'
      };
    } else if (excellentQualities.length === totalAnalyzed && totalAnalyzed > 0) {
      return {
        type: 'success',
        message: `✅ All photos are excellent quality for A5 printing!`,
        color: 'green'
      };
    } else if (totalAnalyzed > 0) {
      return {
        type: 'info',
        message: `ℹ️ Photos analyzed: acceptable to excellent quality for A5 printing.`,
        color: 'blue'
      };
    }
    return null;
  };

  return (
    <div className="container mx-auto px-4 py-8">
      <h2 className="text-2xl font-bold mb-6">Photo Upload</h2>
      
      {error && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4 flex items-center">
          <AlertCircle className="w-5 h-5 mr-2" />
          <span>{error}</span>
        </div>
      )}
      
      <div 
        className="border-2 border-dashed border-gray-300 rounded-lg p-8 mb-6 text-center"
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        <div className="flex justify-center mb-4">
          <Upload className="w-12 h-12 text-gray-400" />
        </div>
        <p className="text-lg mb-2">Drag and drop files here, or</p>
        <p className="text-sm text-gray-600 mb-4">
          Accepted formats: Images (JPG, PNG, GIF...), PDFs, Videos (MP4, MOV, AVI...)
        </p>
        <input
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.gif,.bmp,.tiff,.tif,.pdf,.mp4,.avi,.mov,.wmv,.flv,.webm,.mkv"
          onChange={handleFileChange}
          className="hidden"
          id="file-upload"
          ref={fileInputRef}
        />
        <label
          htmlFor="file-upload"
          className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 cursor-pointer"
        >
          Select Files
        </label>
      </div>
      
      {files.length > 0 && (
        <div className="mb-6">
          <h3 className="text-lg font-medium mb-3 flex items-center">
            Selected Files ({files.length})
            <Camera className="w-5 h-5 ml-2 text-blue-500" />
          </h3>
          
          {/* Global recommendation */}
          {Object.keys(fileQualities).length > 0 && (() => {
            const recommendation = getUploadRecommendation(fileQualities);
            return recommendation && (
              <div className={`mb-4 p-3 rounded-lg ${
                recommendation.color === 'red' ? 'bg-red-50 border border-red-200' :
                recommendation.color === 'green' ? 'bg-green-50 border border-green-200' :
                'bg-blue-50 border border-blue-200'
              }`}>
                <p className={`text-sm ${
                  recommendation.color === 'red' ? 'text-red-700' :
                  recommendation.color === 'green' ? 'text-green-700' :
                  'text-blue-700'
                }`}>
                  {recommendation.message}
                </p>
              </div>
            );
          })()}
          
          <div className="max-h-80 overflow-y-auto border border-gray-200 rounded-md">
            {files.map((file, index) => {
              const quality = fileQualities[index];
              const isAnalyzing = analyzingFiles[index];
              
              return (
                <div 
                  key={index} 
                  className="flex items-center justify-between px-4 py-3 border-b last:border-b-0 hover:bg-gray-50"
                >
                  <div className="flex items-center flex-1">
                    <Image className="w-5 h-5 mr-3 text-gray-500" />
                    <div className="flex-1">
                      <div className="flex items-center mb-1">
                        <input
                          type="text"
                          value={customFilenames[index] || file.name}
                          onChange={(e) => setCustomFilenames(prev => ({ ...prev, [index]: e.target.value }))}
                          className="font-medium bg-white border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 rounded px-3 py-1 max-w-xs text-sm"
                          placeholder="Filename"
                        />
                        {isAnalyzing ? (
                          <div className="ml-2 w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                        ) : quality && (
                          <div className="ml-2">
                            {getQualityIcon(quality.color_code)}
                          </div>
                        )}
                        {searchingArtworks[index] && (
                          <div className="ml-2 flex items-center text-xs text-blue-600">
                            <Search className="w-3 h-3 mr-1 animate-pulse" />
                            Searching artwork...
                          </div>
                        )}
                      </div>
                      
                      <div className="text-xs text-gray-500 flex items-center space-x-3">
                        <span>{(file.size / 1024).toFixed(1)} KB</span>
                        {quality && !quality.error && (
                          <>
                            <span>•</span>
                            <span>{quality.dimensions?.width} × {quality.dimensions?.height}</span>
                            <span>•</span>
                            <span className={`font-medium ${
                              quality.color_code === 'green' ? 'text-green-600' :
                              quality.color_code === 'lightgreen' ? 'text-green-500' :
                              quality.color_code === 'orange' ? 'text-orange-600' :
                              quality.color_code === 'red' ? 'text-red-600' : 'text-gray-600'
                            }`}>
                              {quality.equivalent_dpi_a5} DPI A5
                            </span>
                          </>
                        )}
                        {quality && quality.error && (
                          <>
                            <span>•</span>
                            <span className="text-red-500">{quality.error}</span>
                          </>
                        )}
                      </div>
                      
                      {quality && !quality.error && (
                        <div className="text-xs mt-1">
                          <span className={`px-2 py-1 rounded ${
                            quality.color_code === 'green' ? 'bg-green-100 text-green-700' :
                            quality.color_code === 'lightgreen' ? 'bg-green-50 text-green-600' :
                            quality.color_code === 'orange' ? 'bg-orange-100 text-orange-700' :
                            quality.color_code === 'red' ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-700'
                          }`}>
                            {quality.print_quality_a5}
                          </span>
                        </div>
                      )}
                      
                      {/* Artwork Search Results */}
                      {artworkSearchResults[index] && (
                        <div className="mt-2 p-2 bg-blue-50 border border-blue-200 rounded text-xs">
                          <div className="flex items-center justify-between mb-1">
                            <span className="font-medium text-blue-800">🎨 Artwork found: {artworkSearchResults[index].artworkId}</span>
                            {artworkSearchResults[index].existingPhotos.length > 0 && (
                              <span className="text-orange-600 font-medium">
                                ⚠️ {artworkSearchResults[index].existingPhotos.length} existing photo(s)
                              </span>
                            )}
                          </div>
                          {artworkSearchResults[index].artwork.title && (
                            <div className="text-blue-700 mb-1">
                              📝 {artworkSearchResults[index].artwork.title}
                            </div>
                          )}
                          {artworkSearchResults[index].artwork.artist && (
                            <div className="text-blue-700 mb-1">
                              👤 {artworkSearchResults[index].artwork.artist}
                            </div>
                          )}
                          {artworkSearchResults[index].existingPhotos.length > 0 && (
                            <div className="mt-2">
                              <div className="text-xs font-medium text-orange-700 mb-1">Existing photos:</div>
                              <div className="grid grid-cols-3 gap-1">
                                {artworkSearchResults[index].existingPhotos.slice(0, 3).map((photo, photoIndex) => (
                                  <div key={photoIndex} className="relative">
                                    <img
                                      src={`/api/photos/${encodeURIComponent(photo.id)}`}
                                      alt={photo.filename}
                                      className="w-full h-8 object-cover rounded border"
                                      onError={(e) => {
                                        e.target.style.display = 'none';
                                      }}
                                    />
                                    <div className="absolute inset-0 bg-black bg-opacity-0 hover:bg-opacity-30 transition-opacity flex items-center justify-center">
                                      <Eye className="w-3 h-3 text-white opacity-0 hover:opacity-100" />
                                    </div>
                                  </div>
                                ))}
                              </div>
                              {artworkSearchResults[index].existingPhotos.length > 3 && (
                                <div className="text-xs text-gray-500 mt-1">
                                  +{artworkSearchResults[index].existingPhotos.length - 3} more
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <button
                    onClick={() => removeFile(index)}
                    className="ml-3 text-red-500 hover:text-red-700 p-1"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}
      
      <div className="flex justify-end">
        <button
          onClick={handleSubmit}
          disabled={uploading || files.length === 0}
          className={`px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 focus:outline-none ${
            (uploading || files.length === 0) ? 'opacity-50 cursor-not-allowed' : ''
          }`}
        >
          {uploading ? 'Verification in progress...' : getButtonText()}
        </button>
      </div>
      
      {validationResults && (
        <div className="mt-8">
          <h3 className="text-lg font-medium mb-3">Verification results</h3>
          
          {/* Manual Search Section */}
          <div className="mb-6 p-4 bg-gray-50 border border-gray-200 rounded-lg">
            <h4 className="text-md font-medium mb-3 flex items-center">
              <Search className="w-4 h-4 mr-2" />
		 Additional Search in OperaGallery
            </h4>
            <p className="text-sm text-gray-600 mb-3">
		 Manually check if an artwork or photo is already referenced in the database
            </p>
            
            <form onSubmit={handleManualSearch} className="flex gap-2 mb-4">
              <input
                type="text"
                value={manualSearchQuery}
                onChange={(e) => setManualSearchQuery(e.target.value)}
		placeholder="Search by name, artist, ID, keyword..."
                className="flex-1 px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                disabled={manualSearchLoading || !manualSearchQuery.trim()}
                className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                {manualSearchLoading ? (
                  <Loader className="w-4 h-4 animate-spin" />
                ) : (
                  <Search className="w-4 h-4" />
                )}
              </button>
            </form>
            
            {/* Manual Search Results */}
            {manualSearchResults.length > 0 && (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                <h5 className="text-sm font-medium text-gray-700">
			{manualSearchResults.length} result(s) found:
                </h5>
                {manualSearchResults.map((artwork, index) => (
                  <div key={artwork.IdName || index} className="bg-white p-3 border border-gray-200 rounded text-sm">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="font-medium text-gray-900 mb-1">
				🎨 {artwork.title || 'No title'}
                          <span className="font-mono bg-gray-100 px-2 py-1 rounded ml-2">
                            {artwork.IdName}
                          </span>
                        </div>
                        <div className="text-gray-600 mb-1">
				👤 {artwork.artist || 'Unknown artist'}
                        </div>
                        <div className="text-gray-500 text-xs">
                          📅 {artwork.year || 'N/A'} • 📋 {artwork.category || 'N/A'}
                        </div>
                        {artwork.existingPhotos && artwork.existingPhotos.length > 0 && (
                          <div className="mt-2 p-2 bg-orange-50 border border-orange-200 rounded">
                            <span className="text-orange-800 font-medium text-xs">
				⚠️ {artwork.existingPhotos.length} existing photo(s) found!
                            </span>
                            <div className="grid grid-cols-4 gap-1 mt-2">
                              {artwork.existingPhotos.slice(0, 4).map((photo, photoIndex) => (
                                <img
                                  key={photoIndex}
                                  src={`/api/photos/${encodeURIComponent(photo.id)}`}
                                  alt={photo.filename}
                                  className="w-full h-8 object-cover rounded border"
                                  onError={(e) => {
                                    e.target.style.display = 'none';
                                  }}
                                />
                              ))}
                            </div>
                            {artwork.existingPhotos.length > 4 && (
                              <div className="text-xs text-orange-600 mt-1">
				 +{artwork.existingPhotos.length - 4} other photo(s)
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                      {artwork.main_picture_hd && (
                        <img
                          src={artwork.main_picture_hd}
                          alt={artwork.title}
                          className="w-16 h-16 object-cover rounded border ml-3"
                          onError={(e) => {
                            e.target.style.display = 'none';
                          }}
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
            
            {manualSearchQuery && manualSearchResults.length === 0 && !manualSearchLoading && (
              <div className="text-gray-500 text-sm">
		No results found for "{manualSearchQuery}"
              </div>
            )}
          </div>
          
          {/* Validation results rendered */}
          <div className="space-y-4">
            {validationResults.map((result, index) => (
              <div key={index} className="border border-gray-200 rounded-lg p-4">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center space-x-3">
                    <h4 className="font-medium">{result.file.name}</h4>
                    {result.quality_analysis && getQualityIcon(result.quality_analysis.color_code)}
                  </div>
                  <span className={`px-2 py-1 rounded text-sm ${
                    result.artwork_found 
                      ? 'bg-green-100 text-green-800' 
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {result.artwork_found ? 'Found in OperaCRM' : 'Not found'}
                  </span>
                </div>
                
                {result.quality_analysis && (
                  <div className="bg-blue-50 rounded p-3 mb-3">
                    <h5 className="font-medium mb-2 flex items-center">
                      <Camera className="w-4 h-4 mr-2" />
                      Quality analysis for A5 printing
                    </h5>
                    <div className="grid grid-cols-2 gap-2 text-sm mb-2">
                      <div><strong>Resolution:</strong> {result.quality_analysis.dimensions?.width} × {result.quality_analysis.dimensions?.height}</div>
                      <div><strong>A5 equivalent DPI:</strong> {result.quality_analysis.equivalent_dpi_a5}</div>
                      <div><strong>Quality:</strong> <span className={`font-medium ${
                        result.quality_analysis.color_code === 'green' ? 'text-green-600' :
                        result.quality_analysis.color_code === 'lightgreen' ? 'text-green-500' :
                        result.quality_analysis.color_code === 'orange' ? 'text-orange-600' :
                        result.quality_analysis.color_code === 'red' ? 'text-red-600' : 'text-gray-600'
                      }`}>{result.quality_analysis.print_quality_a5}</span></div>
                      <div><strong>File size:</strong> {result.quality_analysis.file_size_mb} MB</div>
                    </div>
                    
                    {result.quality_analysis.recommendations && result.quality_analysis.recommendations.length > 0 && (
                      <div className="mt-2">
                        <strong className="text-sm">Recommendations:</strong>
                        <ul className="text-sm mt-1 space-y-1">
                          {result.quality_analysis.recommendations.map((rec, i) => (
                            <li key={i} className="flex items-start">
                              <span className="mr-2">•</span>
                              <span>{rec}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {result.quality_analysis.validation_issues && result.quality_analysis.validation_issues.length > 0 && (
                      <div className="mt-2 p-2 bg-red-100 rounded">
                        <strong className="text-sm text-red-800">Issues detected:</strong>
                        <ul className="text-sm mt-1 space-y-1">
                          {result.quality_analysis.validation_issues.map((issue, i) => (
                            <li key={i} className="text-red-700">• {issue}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
                
                {result.upload_recommendation && (
                  <div className={`p-3 rounded mb-3 ${
                    result.upload_recommendation.should_accept 
                      ? 'bg-green-100 border border-green-300' 
                      : 'bg-red-100 border border-red-300'
                  }`}>
                    <div className="flex items-center">
                      {result.upload_recommendation.should_accept ? (
                        <CheckCircle className="w-4 h-4 mr-2 text-green-600" />
                      ) : (
                        <X className="w-4 h-4 mr-2 text-red-600" />
                      )}
                      <span className={`text-sm font-medium ${
                        result.upload_recommendation.should_accept ? 'text-green-800' : 'text-red-800'
                      }`}>
                        {result.upload_recommendation.should_accept ? 'Upload recommended' : 'Upload not recommended'}
                      </span>
                    </div>
                    <p className={`text-sm mt-1 ${
                      result.upload_recommendation.should_accept ? 'text-green-700' : 'text-red-700'
                    }`}>
                      {result.upload_recommendation.reason}
                    </p>
                  </div>
                )}
                
                {result.artwork_id && (
                  <p className="text-sm text-gray-600 mb-2">
                    ID extracted from filename: <strong>{result.artwork_id}</strong>
                  </p>
                )}
                
                {result.artwork_found && result.artwork_metadata && (
                  <div className="bg-gray-50 rounded p-3 mb-3">
                    <h5 className="font-medium mb-2">Artwork information:</h5>
                    <div className="grid grid-cols-2 gap-2 text-sm">
                      <div><strong>Title:</strong> {result.artwork_metadata.title}</div>
                      <div><strong>Artist:</strong> {result.artwork_metadata.artist}</div>
                      <div><strong>Year:</strong> {result.artwork_metadata.year}</div>
                      <div><strong>Category:</strong> {result.artwork_metadata.category}</div>
                    </div>
                  </div>
                )}
                
                {result.duplicate_warning && (
                  <div className="bg-orange-100 border border-orange-400 text-orange-700 px-3 py-2 rounded mb-3">
                    <div className="flex items-center mb-2">
                      <AlertCircle className="w-4 h-4 mr-2" />
                      <span className="font-medium">Warning - Existing photos detected</span>
                    </div>
                    <p className="text-sm mb-3">{result.duplicate_warning.message}</p>
                    
                    {result.duplicate_warning.existing_images && result.duplicate_warning.existing_images.length > 0 && (
                      <div>
                        <p className="text-sm font-medium mb-2">Existing photos:</p>
                        <div className="grid grid-cols-3 gap-2">
                          {result.duplicate_warning.existing_images.slice(0, 3).map((imageUrl, imgIndex) => (
                            <div key={imgIndex} className="relative">
                              <img 
                                src={imageUrl} 
                                alt={`Existing photo ${imgIndex + 1}`}
                                className="w-full h-20 object-cover rounded border"
                                onError={(e) => {
                                  e.target.style.display = 'none';
                                }}
                              />
                            </div>
                          ))}
                        </div>
                        {result.duplicate_warning.existing_images.length > 3 && (
                          <p className="text-xs text-gray-500 mt-1">
                            +{result.duplicate_warning.existing_images.length - 3} additional photo(s)
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                )}
                
                {!result.artwork_found && result.artwork_id && (
                  <div className="bg-yellow-100 border border-yellow-400 text-yellow-700 px-3 py-2 rounded">
                    <div className="flex items-center">
                      <AlertCircle className="w-4 h-4 mr-2" />
                      <span className="text-sm">
                        ID {result.artwork_id} was not found in FileMaker or OperaCRM
                      </span>
                    </div>
                  </div>
                )}
                
                {!result.artwork_id && (
                  <div className="bg-gray-100 border border-gray-300 text-gray-600 px-3 py-2 rounded">
                    <div className="flex items-center">
                      <AlertCircle className="w-4 h-4 mr-2" />
                      <span className="text-sm">
                        No artwork ID detected in filename
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
          
          <div className="flex justify-end space-x-4 mt-6">
            <button
              onClick={() => {
                setValidationResults(null);
                setFiles([]);
                setCustomFilenames({});
                setArtworkSearchResults({});
                setSearchingArtworks({});
                setManualSearchQuery('');
                setManualSearchResults([]);
                if (fileInputRef.current) {
                  fileInputRef.current.value = '';
                }
              }}
              className="px-4 py-2 bg-gray-500 text-white rounded-md hover:bg-gray-600 focus:outline-none"
            >
              Cancel
            </button>
            <button
              onClick={confirmUpload}
              disabled={uploading}
              className={`px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 focus:outline-none ${
                uploading ? 'opacity-50 cursor-not-allowed' : ''
              }`}
            >
              {uploading ? 'Upload in progress...' : 'Confirm upload'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
