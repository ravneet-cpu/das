// src/services/apiService.js
const API_BASE_URL = window.location.origin;

// Helper function to handle API responses consistently
const handleResponse = async (response) => {
  // Session expired / invalid token -> clear auth and redirect to login
  if (response.status === 401) {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/';
    return { success: false, error: 'Session expired' };  // don't throw, redirect already happening
  }

  if (!response.ok) {
    // Try to get error details from response
    let errorText;
    try {
      const errorData = await response.json();
      errorText = errorData.error || `HTTP Error: ${response.status}`;
    } catch (e) {
      try {
        // If JSON parsing fails, try to get the response text
        errorText = await response.text();
        if (!errorText) {
          errorText = `HTTP Error: ${response.status}`;
        }
      } catch (textError) {
        errorText = `HTTP Error: ${response.status}`;
      }
    }
    throw new Error(errorText);
  }
  
  try {
    return await response.json();
  } catch (e) {
    console.error('Error parsing JSON:', e);
    return { success: true }; // Default response if parsing fails
  }
};

// Get auth token from localStorage
const getAuthToken = () => localStorage.getItem('token');

// Create headers with auth token
const createHeaders = (contentType = 'application/json') => {
  const headers = {
    'Content-Type': contentType,
  };
  
  const token = getAuthToken();
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  
  return headers;
};

// Fix TIFF file paths if needed
const fixTiffPath = (photoId) => {
  // If it's a TIFF file, ensure we're using the correct format
  if (photoId && (photoId.toLowerCase().endsWith('.tif') || photoId.toLowerCase().endsWith('.tiff'))) {
    // Return the photoId unchanged, but log for debugging
    console.log('TIFF file detected:', photoId);
  }
  return photoId;
};

// Improved function to handle special filenames (including those with hyphens)
const handleSpecialFilename = (photoId) => {
  if (!photoId) return photoId;
  
  // For filenames starting with a hyphen, we need special handling
  if (photoId.startsWith('-')) {
    console.log('Handling filename with leading hyphen:', photoId);
    
    // Make sure we still encode the filename for URL safety
    const encodedPhotoId = encodeURIComponent(photoId);
    
    // Log for debugging
    console.log('Encoded filename with hyphen:', encodedPhotoId);
    
    return encodedPhotoId;
  }
  
  // For filenames with spaces or special characters, make sure they're properly encoded
  if (photoId.includes(' ') || /[^a-zA-Z0-9._-]/.test(photoId)) {
    console.log('Handling filename with spaces or special chars:', photoId);
    const encodedPhotoId = encodeURIComponent(photoId);
    console.log('Encoded filename:', encodedPhotoId);
    return encodedPhotoId;
  }
  
  return photoId;
};

// Create query string from parameters object
const createQueryString = (params = {}) => {
  const searchParams = new URLSearchParams();
  
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.append(key, value);
    }
  });
  
  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : '';
};

// API service functions
const apiService = {
  // Base URL for external access
  API_BASE_URL,
  
  // Photo endpoints
  async fetchNextPhoto() {
    console.log('Fetching next photo...');
    const response = await fetch(`${API_BASE_URL}/api/photos/next`, {
      headers: createHeaders()
    });
    return handleResponse(response);
  },
  
  async validatePhoto(photoId, decision, classification = null, rejectReason = null, newFilename = null) {
    console.log(`Validating photo ${photoId} with decision ${decision} and classification ${classification}`);

    // Fix TIFF path if needed
    const fixedPhotoId = fixTiffPath(photoId);

    // For the validation API, we DO NOT encode the photoId in the payload
    // The backend will handle the filename as-is
    const payload = {
      photoId: fixedPhotoId,
      decision,
    };

    if (classification) {
      payload.classification = classification;
    }

    if (rejectReason) {
      payload.rejectReason = rejectReason;
    }

    if (newFilename && newFilename !== photoId) {
      payload.newFilename = newFilename;
    }
    
    console.log('Validation payload:', JSON.stringify(payload));
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/photos/validate`, {
        method: 'POST',
        headers: createHeaders(),
        body: JSON.stringify(payload)
      });
      
      console.log('Validation response status:', response.status, response.statusText);
      
      // Try to log the response text for debugging
      try {
        const responseClone = response.clone();
        const responseText = await responseClone.text();
        console.log('Validation response text:', responseText);
      } catch (e) {
        console.warn('Could not log response text:', e);
      }
      
      return handleResponse(response);
    } catch (error) {
      console.error('Error during validation:', error);
      throw error;
    }
  },
  
  async fetchPhotoList(params = {}) {
    // Default params
    const defaultParams = {
      page: 1,
      limit: 50
    };
    
    const mergedParams = { ...defaultParams, ...params };
    const queryString = createQueryString(mergedParams);
    
    console.log(`Fetching photo list with params: ${queryString}`);
    
    const response = await fetch(`${API_BASE_URL}/api/photos/list${queryString}`, {
      headers: createHeaders()
    });
    return handleResponse(response);
  },
  
  async fetchStats() {
    const response = await fetch(`${API_BASE_URL}/api/photos/stats`, {
      headers: createHeaders()
    });
    return handleResponse(response);
  },
  
  async processBatch(photoIds, decision, rejectReason = null) {
    // Fix TIFF paths if needed and handle special filenames
    const fixedPhotoIds = photoIds.map(fixTiffPath);

    const response = await fetch(`${API_BASE_URL}/api/photos/batch`, {
      method: 'POST',
      headers: createHeaders(),
      body: JSON.stringify({
        photoIds: fixedPhotoIds,
        decision,
        rejectReason: rejectReason || null
      })
    });

    return handleResponse(response);
  },

  // Upload photo endpoint
  async uploadPhoto(file, customFilename = null) {
    console.log('Uploading photo:', file.name);

    const formData = new FormData();
    formData.append('file', file);

    if (customFilename) {
      formData.append('custom_filename', customFilename);
      console.log('Using custom filename:', customFilename);
    }

    // Get token but don't set Content-Type (FormData sets it automatically with boundary)
    const token = getAuthToken();
    const headers = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/api/photos/upload`, {
        method: 'POST',
        headers: headers,
        body: formData
      });

      console.log('Upload response status:', response.status, response.statusText);
      return handleResponse(response);
    } catch (error) {
      console.error('Error during upload:', error);
      throw error;
    }
  },

  // Collaboration endpoints
  async fetchCollaborationStatus() {
    const response = await fetch(`${API_BASE_URL}/api/collaboration/status`, {
      headers: createHeaders()
    });
    return handleResponse(response);
  },
  
  async lockPhoto(photoId, duration = 300) {
    const fixedPhotoId = fixTiffPath(photoId);
    
    const response = await fetch(`${API_BASE_URL}/api/collaboration/lock`, {
      method: 'POST',
      headers: createHeaders(),
      body: JSON.stringify({ photoId: fixedPhotoId, duration })
    });
    return handleResponse(response);
  },
  
  async unlockPhoto(photoId) {
    const fixedPhotoId = fixTiffPath(photoId);
    
    const response = await fetch(`${API_BASE_URL}/api/collaboration/unlock`, {
      method: 'POST',
      headers: createHeaders(),
      body: JSON.stringify({ photoId: fixedPhotoId })
    });
    return handleResponse(response);
  },
  
  // Helper for image URLs - fixed to ensure complete URLs with proper encoding
  getPhotoUrl(photoId, size = null) {
    if (!photoId) return '';
    
    const fixedPhotoId = fixTiffPath(photoId);
    const safePhotoId = handleSpecialFilename(fixedPhotoId);
    
    let url = `${API_BASE_URL}/api/photos/${safePhotoId}`;
    if (size) {
      url += `?size=${size}`;
    }
    console.log('Generated image URL:', url);
    return url;
  },
  
  // Get photo details URL
  getPhotoDetailsUrl(photoId) {
    if (!photoId) return '';
    
    const fixedPhotoId = fixTiffPath(photoId);
    const safePhotoId = handleSpecialFilename(fixedPhotoId);
    
    const url = `${API_BASE_URL}/api/photos/details/${safePhotoId}`;
    return url;
  },

  // Task management endpoints
  async fetchTasks(params = {}) {
    const queryString = createQueryString(params);
    
    const response = await fetch(`${API_BASE_URL}/api/tasks${queryString}`, {
      headers: createHeaders()
    });
    return handleResponse(response);
  },

  async createTask(taskData) {
    const response = await fetch(`${API_BASE_URL}/api/tasks`, {
      method: 'POST',
      headers: createHeaders(),
      body: JSON.stringify(taskData)
    });
    return handleResponse(response);
  },

  async updateTask(taskId, updateData) {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}`, {
      method: 'PUT',
      headers: createHeaders(),
      body: JSON.stringify(updateData)
    });
    return handleResponse(response);
  },

  async fetchTaskHistory(taskId) {
    const response = await fetch(`${API_BASE_URL}/api/tasks/${taskId}/history`, {
      headers: createHeaders()
    });
    return handleResponse(response);
  },

  // User management endpoints
  async fetchUsers() {
    const response = await fetch(`${API_BASE_URL}/api/auth/users`, {
      headers: createHeaders()
    });
    return handleResponse(response);
  },

  async createUser(userData) {
    const response = await fetch(`${API_BASE_URL}/api/auth/create-user`, {
      method: 'POST',
      headers: createHeaders(),
      body: JSON.stringify(userData)
    });
    return handleResponse(response);
  },

  // Photo marking endpoints
  async markPhoto(photoId, photoFilename = '', note = '', action = 'toggle') {
    const response = await fetch(`${API_BASE_URL}/api/photos/mark`, {
      method: 'POST',
      headers: createHeaders(),
      body: JSON.stringify({
        photo_id: photoId,
        photo_filename: photoFilename,
        note: note,
        action: action
      })
    });
    return handleResponse(response);
  },

  async getMarkedPhotos(page = 1, limit = 20) {
    const response = await fetch(`${API_BASE_URL}/api/photos/marked?page=${page}&limit=${limit}`, {
      headers: createHeaders()
    });
    return handleResponse(response);
  },

  async getMarkStatus(photoId) {
    // Encode the photoId to handle special characters and paths
    const encodedPhotoId = encodeURIComponent(photoId);
    const response = await fetch(`${API_BASE_URL}/api/photos/${encodedPhotoId}/mark-status`, {
      headers: createHeaders()
    });
    return handleResponse(response);
  },

  async unmarkPhoto(photoId) {
    return this.markPhoto(photoId, '', '', 'unmark');
  }
};

export default apiService;
