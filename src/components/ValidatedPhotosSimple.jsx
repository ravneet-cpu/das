import React, { useState, useEffect } from 'react';
import { RefreshCw, CheckCircle } from 'lucide-react';

const ValidatedPhotosSimple = () => {
  const [photos, setPhotos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [total, setTotal] = useState(0);

  const fetchPhotos = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Fetching validated photos...');
      
      const response = await fetch('/api/photos/list?status=validated&limit=24', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      console.log('Response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('API response:', data);
      console.log('Photos array:', data.photos);
      console.log('Photos array length:', data.photos ? data.photos.length : 0);
      console.log('Total photos:', data.total);
      
      setPhotos(data.photos || []);
      setTotal(data.total || 0);
      
      console.log('State after setting photos:', data.photos || []);
      console.log('State after setting total:', data.total || 0);
    } catch (err) {
      console.error('Error fetching photos:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPhotos();
  }, []);

  const getPhotoUrl = (photoId) => {
    return `/api/photos/${encodeURIComponent(photoId)}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black mx-auto mb-4"></div>
          <p className="text-black">Loading validated photos...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600 mb-4">Error: {error}</p>
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

  console.log('Render - photos state:', photos);
  console.log('Render - total state:', total);
  console.log('Render - photos.length:', photos.length);

  return (
    <div className="min-h-screen bg-white py-8 px-4">
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-black mb-2">✅ Validated Photos</h1>
            <p className="text-gray-600">
              {total} validated photo{total !== 1 ? 's' : ''} found
            </p>
          </div>
          
          <button
            onClick={fetchPhotos}
            className="bg-black text-white px-4 py-2 rounded-lg hover:bg-gray-800 transition-colors flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
        </div>

        {photos.length === 0 ? (
          <div className="text-center py-12">
            <CheckCircle className="h-24 w-24 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-600 mb-2">No validated photos yet</h3>
            <p className="text-gray-500">Photos that have been validated will appear here.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-6">
            {photos.map((photo) => (
              <div
                key={photo.id}
                className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden hover:shadow-xl transition-shadow"
              >
                <div className="aspect-square relative overflow-hidden">
                  <img
                    src={getPhotoUrl(photo.id)}
                    alt={photo.filename}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSIjZjNmNGY2Ii8+PHRleHQgeD0iNTAlIiB5PSI1MCUiIGZvbnQtZmFtaWx5PSJBcmlhbCIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzlmYTZiNyIgdGV4dC1hbmNob3I9Im1pZGRsZSIgZHk9Ii4zZW0iPkltYWdlPC90ZXh0Pjwvc3ZnPg==';
                    }}
                  />
                </div>
                
                <div className="p-3">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-1">
                      <CheckCircle className="h-4 w-4 text-green-500" />
                      <span className="text-green-600 font-medium text-sm">Validated</span>
                      {photo.classification && (
                        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-xs font-medium ml-1">
                          {photo.classification}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <h3 className="font-medium text-black text-sm mb-1 truncate">
                    {photo.filename}
                  </h3>
                  
                  {photo.validated_by && (
                    <div className="text-xs text-green-600">
                      ✅ Validated by: {photo.validated_by}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default ValidatedPhotosSimple;