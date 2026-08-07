// src/components/DebugPage.jsx
import React, { useState, useEffect } from 'react';

const DebugPage = () => {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState(null);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [token, setToken] = useState('');

  // Get the API URL from the window location
  const apiBaseUrl = window.location.origin;

  useEffect(() => {
    // Get the token from localStorage
    const storedToken = localStorage.getItem('token');
    if (storedToken) {
      setToken(storedToken);
    }
    
    // Fetch photos when the component mounts
    fetchPhotos();
  }, []);

  const fetchPhotos = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`${apiBaseUrl}/api/photos/list`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText}`);
      }
      
      const data = await response.json();
      // Photos data loaded
      
      if (data.photos) {
        setPhotos(data.photos);
      } else {
        setPhotos([]);
      }
    } catch (err) {
      // Error loading photos
      setError(`Error fetching photos: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const validatePhoto = async (photoId, decision) => {
    try {
      setLoading(true);
      setError(null);
      setResult(null);
      
      // Build the request payload
      const payload = {
        photoId: photoId,
        decision: decision
      };
      
      // Validation request prepared
      
      // Make the request
      const response = await fetch(`${apiBaseUrl}/api/photos/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });
      
      // Get the response text
      const responseText = await response.text();
      
      // Try to parse as JSON
      let responseData;
      try {
        responseData = JSON.parse(responseText);
      } catch (e) {
        responseData = { text: responseText };
      }
      
      // Set the result
      setResult({
        status: response.status,
        statusText: response.statusText,
        data: responseData,
        raw: responseText
      });
      
      if (!response.ok) {
        throw new Error(`API error: ${response.status} ${response.statusText} - ${responseText}`);
      }
      
      // Photo validation successful
      
      // Refresh photos list
      await fetchPhotos();
    } catch (err) {
      // Photo validation error
      setError(`Error validating photo: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-4 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold mb-4">Photo Validator Debug</h1>
      
      {/* Token display */}
      <div className="mb-4 p-4 bg-gray-100 rounded">
        <h2 className="text-lg font-semibold mb-2">Auth Token</h2>
        <div className="flex items-center space-x-2">
          <input 
            type="text" 
            value={token} 
            onChange={(e) => setToken(e.target.value)} 
            className="border rounded px-2 py-1 flex-1"
            placeholder="Enter auth token"
          />
          <button 
            onClick={() => {
              localStorage.setItem('token', token);
              fetchPhotos();
            }}
            className="bg-blue-500 text-white px-3 py-1 rounded"
          >
            Update
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          API URL: {apiBaseUrl}
        </p>
      </div>
      
      {/* Error display */}
      {error && (
        <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
          {error}
        </div>
      )}
      
      {/* Result display */}
      {result && (
        <div className="mb-4 p-4 bg-gray-100 rounded">
          <h2 className="text-lg font-semibold mb-2">API Response</h2>
          <div className="mb-2">
            <span className="font-medium">Status:</span> 
            <span className={result.status >= 200 && result.status < 300 ? 'text-green-600' : 'text-red-600'}>
              {result.status} {result.statusText}
            </span>
          </div>
          <div className="bg-blue-50 p-3 rounded">
            <p className="text-sm text-blue-800">
              Réponse reçue avec {result.data?.artworks?.length || 0} résultats
            </p>
          </div>
        </div>
      )}
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Photos list */}
        <div>
          <h2 className="text-lg font-semibold mb-2">Available Photos</h2>
          <div className="mb-2">
            <button 
              onClick={fetchPhotos} 
              disabled={loading}
              className="bg-blue-500 text-white px-3 py-1 rounded disabled:opacity-50"
            >
              {loading ? 'Loading...' : 'Refresh Photos'}
            </button>
          </div>
          
          <div className="bg-gray-100 p-4 rounded max-h-96 overflow-y-auto">
            {photos.length === 0 ? (
              <p className="text-gray-500">No photos found.</p>
            ) : (
              <div className="space-y-2">
                {photos.map(photo => (
                  <div 
                    key={photo.id} 
                    className={`p-2 border rounded cursor-pointer ${selectedPhoto?.id === photo.id ? 'bg-blue-100 border-blue-500' : 'bg-white hover:bg-gray-50'}`}
                    onClick={() => setSelectedPhoto(photo)}
                  >
                    <div className="font-medium truncate">{photo.id}</div>
                    <div className="text-xs text-gray-500 flex justify-between">
                      <span>{photo.type || 'Unknown type'}</span>
                      {photo.width && photo.height && (
                        <span>{photo.width} × {photo.height}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
        
        {/* Selected photo details */}
        <div>
          <h2 className="text-lg font-semibold mb-2">Photo Details</h2>
          
          {selectedPhoto ? (
            <div className="bg-gray-100 p-4 rounded">
              <div className="mb-2">
                <span className="font-medium">ID:</span> {selectedPhoto.id}
              </div>
              
              {/* Image preview */}
              <div className="mb-4 bg-gray-200 p-2 rounded flex items-center justify-center">
                <img 
                  src={selectedPhoto.artwork_id ? 
                    `${apiBaseUrl}/api/operacrm/image/${selectedPhoto.artwork_id}/image_1920` :
                    `${apiBaseUrl}/api/photos/${encodeURIComponent(selectedPhoto.id)}`
                  }
                  alt="Photo preview"
                  className="max-h-48 max-w-full object-contain"
                  onError={(e) => {
                    // Image load failed
                    e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwIiBoZWlnaHQ9IjEwMCIgZmlsbD0iI2VlZSIvPjx0ZXh0IHg9IjUwIiB5PSI1MCIgZm9udC1mYW1pbHk9IkFyaWFsIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIiBkb21pbmFudC1iYXNlbGluZT0ibWlkZGxlIiBmb250LXNpemU9IjE0Ij5JbWFnZSBFcnJvcjwvdGV4dD48L3N2Zz4=';
                  }}
                />
              </div>
              
              {/* Properties */}
              <h3 className="font-medium mb-1">Information:</h3>
              <div className="bg-white p-2 rounded mb-4 text-sm space-y-1">
                <div><span className="font-medium">ID:</span> {selectedPhoto.id}</div>
                <div><span className="font-medium">Name:</span> {selectedPhoto.filename}</div>
                <div><span className="font-medium">Status:</span> {selectedPhoto.status || 'Not specified'}</div>
                <div><span className="font-medium">Size:</span> {selectedPhoto.size_mb ? `${selectedPhoto.size_mb} MB` : 'Not specified'}</div>
              </div>
              
              {/* Validation buttons */}
              <div className="flex space-x-2">
                <button 
                  onClick={() => validatePhoto(selectedPhoto.id, 'valider')}
                  disabled={loading}
                  className="bg-green-500 text-white px-4 py-2 rounded disabled:opacity-50"
                >
                  {loading ? 'Processing...' : 'Validate'}
                </button>
                <button 
                  onClick={() => validatePhoto(selectedPhoto.id, 'refuser')}
                  disabled={loading}
                  className="bg-red-500 text-white px-4 py-2 rounded disabled:opacity-50"
                >
                  {loading ? 'Processing...' : 'Reject'}
                </button>
              </div>
              
              {/* Raw ID testing */}
              <div className="mt-4 pt-4 border-t">
                <h3 className="font-medium mb-1">Test with Different ID Formats:</h3>
                <div className="space-y-2">
                  <button 
                    onClick={() => validatePhoto(selectedPhoto.id, 'valider')}
                    className="text-xs bg-blue-100 px-2 py-1 rounded"
                  >
                    Raw ID: {selectedPhoto.id}
                  </button>
                  <button 
                    onClick={() => validatePhoto(encodeURIComponent(selectedPhoto.id), 'valider')}
                    className="text-xs bg-blue-100 px-2 py-1 rounded"
                  >
                    URL Encoded: {encodeURIComponent(selectedPhoto.id)}
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-gray-100 p-4 rounded text-gray-500">
              Select a photo from the list to see details.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default DebugPage;
