// src/services/odooService.js
import apiService from './apiService';

const API_BASE_URL = apiService.API_BASE_URL;

// Service pour interagir avec l'API Odoo via notre backend
const odooService = {
  // Rechercher une œuvre par ID
  async searchArtworkById(idName) {
    try {
      const response = await fetch(`${API_BASE_URL}/api/artworks/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({ 
          query: idName,
          searchType: 'artwork_id',
          limit: 1
        })
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || `HTTP Error: ${response.status}`);
      }
      
      const data = await response.json();
      
      // Convert the new format to the expected format
      if (data.success && data.artworks && data.artworks.length > 0) {
        return {
          success: true,
          artwork: data.artworks[0],
          message: 'Artwork found in database'
        };
      } else {
        return {
          success: false,
          message: 'Artwork not found in OperaCRM database',
          id_name: idName,
          suggestions: [
            'Check if the artwork ID is spelled correctly',
            'This may be a new artwork to be added to the collection',
            'Verify the ID format (e.g., ARTIST-12345)'
          ]
        };
      }
    } catch (error) {
      console.error('Erreur lors de la recherche d\'œuvre:', error);
      throw error;
    }
  }
};

export default odooService;
