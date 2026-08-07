// src/services/apiService.js
const API_BASE_URL = 'http://185.133.250.8:5000';

// Helper function to handle API responses consistently
const handleResponse = async (response) => {
  if (!response.ok) {
    // Try to get error details from response
    let errorText;
    try {
      const errorData = await response.json();
      errorText = errorData.error || `HTTP Error: ${response.status}`;
    } catch (e) {
      errorText = `HTTP Error: ${response.status}`;
    }
    throw new Error(errorText);
  }
  return response.json();
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

// API service functions
const apiService = {
  // Photo endpoints
  async fetchNextPhoto() {
    console.log('Fetching next photo...');
    const response = await fetch(`${API_BASE_URL}/api/photos/next`, {
      headers: createHeaders()
    });
    return handleResponse(response);
  },
  
  async validatePhoto(photoId, decision, rejectReason = null, newFilename = null) {
    console.log(`Validating photo ${photoId} with decision ${decision}`);
    const payload = {
      photoId,
      decision,
      rejectReason
    };
    
    if (newFilename && newFilename !== photoId) {
      payload.newFilename = newFilename;
    }
    
    const response = await fetch(`${API_BASE_URL}/api/photos/validate`, {
      method: 'POST',
      headers: createHeaders(),
      body: JSON.stringify(payload)
    });
    
    return handleResponse(response);
  },
  
  async fetchPhotoList() {
    const response = await fetch(`${API_BASE_URL}/api/photos/list`, {
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
    const response = await fetch(`${API_BASE_URL}/api/photos/batch`, {
      method: 'POST',
      headers: createHeaders(),
      body: JSON.stringify({
        photoIds,
        decision,
        rejectReason: rejectReason || null
      })
    });
    
    return handleResponse(response);
  },
  
  // Collaboration endpoints
  async fetchCollaborationStatus() {
    const response = await fetch(`${API_BASE_URL}/api/collaboration/status`, {
      headers: createHeaders()
    });
    return handleResponse(response);
  },
  
  async lockPhoto(photoId, duration = 300) {
    const response = await fetch(`${API_BASE_URL}/api/collaboration/lock`, {
      method: 'POST',
      headers: createHeaders(),
      body: JSON.stringify({ photoId, duration })
    });
    return handleResponse(response);
  },
  
  async unlockPhoto(photoId) {
    const response = await fetch(`${API_BASE_URL}/api/collaboration/unlock`, {
      method: 'POST',
      headers: createHeaders(),
      body: JSON.stringify({ photoId })
    });
    return handleResponse(response);
  },
  
  // Helper for image URLs
  getPhotoUrl(photoId, size = null) {
    let url = `${API_BASE_URL}/api/photos/${encodeURIComponent(photoId)}`;
    if (size) {
      url += `?size=${size}`;
    }
    return url;
  }
};

export default apiService;
