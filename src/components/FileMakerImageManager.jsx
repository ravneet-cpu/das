// src/components/FileMakerImageManager.jsx
import React, { useState } from 'react';
import { Search, Save, Trash2, Plus, Image, Eye, AlertCircle, CheckCircle, Archive, Download } from 'lucide-react';

const IMAGE_FIELD_LABELS = {
  // Champs d'images principaux
  'MAINFM': { label: 'MAINFM (Legacy)', icon: '🖼️', description: 'Image principale FileMaker (champ legacy)', category: 'primary' },
  'MAIN300': { label: 'Images Principales', icon: '🎨', description: 'Vues principales de l\'œuvre', category: 'primary' },
  'DET300': { label: 'Détails', icon: '🔍', description: 'Détails en gros plan', category: 'primary' },
  'BACK300': { label: 'Vues Arrière', icon: '🔄', description: 'Vue arrière/verso', category: 'primary' },
  'FRONT300': { label: 'Vues Frontales', icon: '⬜', description: 'Vue frontale', category: 'primary' },
  'FRAME300': { label: 'Cadre', icon: '🖼️', description: 'Détails du cadre', category: 'primary' },
  'FRONTRIGHT300': { label: 'Frontal Droit', icon: '↗️', description: 'Angle frontal droit', category: 'primary' },
  'INSITU300': { label: 'In Situ', icon: '🏛️', description: 'Installé/exposé', category: 'primary' },
  'LEFT300': { label: 'Côté Gauche', icon: '⬅️', description: 'Vue côté gauche', category: 'primary' },
  'OTHER300': { label: 'Autres Vues', icon: '👁️', description: 'Perspectives additionnelles', category: 'primary' },
  'PERS300': { label: 'Perspective', icon: '📐', description: 'Vues en perspective', category: 'primary' },
  
  // Champs de sauvegarde
  'ImageBAK1': { label: 'ImageBAK1', icon: '💾', description: 'Sauvegarde d\'images anciennes #1', category: 'backup' },
  'ImageBAK2': { label: 'ImageBAK2', icon: '💾', description: 'Sauvegarde d\'images anciennes #2', category: 'backup' },
  'ImageBAK3': { label: 'ImageBAK3', icon: '💾', description: 'Sauvegarde d\'images anciennes #3', category: 'backup' },
  'ImageBAK4': { label: 'ImageBAK4', icon: '💾', description: 'Sauvegarde d\'images anciennes #4', category: 'backup' },
  'ImageBAK5': { label: 'ImageBAK5', icon: '💾', description: 'Sauvegarde d\'images anciennes #5', category: 'backup' },
  
  // Champs spéciaux
  'UrlOpensea': { label: 'URL OpenSea', icon: '🌐', description: 'Lien vers OpenSea NFT marketplace', category: 'special' },
  'UHDPictureUrl': { label: 'URL Image UHD', icon: '🖼️', description: 'Lien vers image Ultra Haute Définition', category: 'special' }
};

export function FileMakerImageManager() {
  const [searchId, setSearchId] = useState('');
  const [artwork, setArtwork] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [imageFields, setImageFields] = useState({});
  const [showBackupFields, setShowBackupFields] = useState(false);
  const [certificateDownloading, setCertificateDownloading] = useState(false);

  // Rechercher un artwork par ID
  const searchArtwork = async () => {
    if (!searchId.trim()) {
      setMessage({ type: 'error', text: 'Veuillez saisir un ID d\'artwork' });
      return;
    }

    setLoading(true);
    setMessage(null);

    try {
      const response = await fetch(`/api/filemaker/artwork/${encodeURIComponent(searchId.trim())}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setArtwork(data);
        
        // Initialiser les champs d'images
        const fields = {};
        Object.keys(IMAGE_FIELD_LABELS).forEach(fieldName => {
          const fieldValue = data[fieldName] || '';
          fields[fieldName] = fieldValue.split('\n').filter(url => url.trim()).map(url => url.trim());
        });
        setImageFields(fields);
        
        setMessage({ type: 'success', text: `Artwork ${searchId} trouvé` });
      } else {
        setMessage({ type: 'error', text: 'Artwork non trouvé' });
        setArtwork(null);
        setImageFields({});
      }
    } catch (error) {
	setMessage({ type: 'error', text: `Error: ${error.message}` });
      setArtwork(null);
      setImageFields({});
    }

    setLoading(false);
  };

  // Ajouter une URL à un champ
  const addImageUrl = (fieldName) => {
    setImageFields(prev => ({
      ...prev,
      [fieldName]: [...(prev[fieldName] || []), '']
    }));
  };

  // Supprimer une URL d'un champ
  const removeImageUrl = (fieldName, index) => {
    setImageFields(prev => ({
      ...prev,
      [fieldName]: prev[fieldName].filter((_, i) => i !== index)
    }));
  };

  // Modifier une URL
  const updateImageUrl = (fieldName, index, value) => {
    setImageFields(prev => ({
      ...prev,
      [fieldName]: prev[fieldName].map((url, i) => i === index ? value : url)
    }));
  };

  // Sauvegarder les modifications
  const saveChanges = async () => {
    if (!artwork) return;

    setSaving(true);
    setMessage(null);

    try {
      const updates = {};
      Object.keys(imageFields).forEach(fieldName => {
        const urls = imageFields[fieldName].filter(url => url.trim());
        updates[fieldName] = urls.join('\n');
      });

      const response = await fetch('/api/admin/filemaker/update-image-fields', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          artworkId: artwork.IdName,
          fields: updates
        })
      });

      if (response.ok) {
	setMessage({ type: 'success', text: 'Changes saved successfully' });
      } else {
        const errorData = await response.json();
	 setMessage({ type: 'error', text: `Save error: ${errorData.error || 'Unknown error'}` });
      }
    } catch (error) {
	 setMessage({ type: 'error', text: `Error: ${error.message}` });
    }

    setSaving(false);
  };

  const deleteAllPhotos = async () => {
    if (!artwork) return;
    
    const confirmDelete = window.confirm(
      `⚠️ ATTENTION : Voulez-vous vraiment supprimer TOUTES les photos de l'artwork ${artwork.IdName} ?\n\nCette action est irréversible !`
    );
    
    if (!confirmDelete) return;
    
    setSaving(true);
    setMessage(null);
    
    try {
      // Vider tous les champs d'images
      const emptyUpdates = {};
      Object.keys(IMAGE_FIELD_LABELS).forEach(fieldName => {
        emptyUpdates[fieldName] = '';
      });
      
      const response = await fetch('/api/admin/filemaker/update-image-fields', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          artworkId: artwork.IdName,
          fields: emptyUpdates
        })
      });
      
      if (response.ok) {
        // Vider l'état local
        const emptyFields = {};
        Object.keys(IMAGE_FIELD_LABELS).forEach(fieldName => {
          emptyFields[fieldName] = [];
        });
        setImageFields(emptyFields);
	setMessage({ type: 'success', text: 'All photos deleted successfully!' });
      } else {
        const errorData = await response.json();
	setMessage({ type: 'error', text: `Delete error: ${errorData.error || 'Unknown error'}` });
      }
    } catch (error) {
	setMessage({ type: 'error', text: `Error: ${error.message}` });
    }

    setSaving(false);
  };

  // Download certificate function
  const downloadCertificate = async (artworkId) => {
    if (!artworkId) return;
    
    setCertificateDownloading(true);
    
    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/certificate/download/${artworkId}`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.ok) {
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `Certificat_${artworkId}.pdf`;
        document.body.appendChild(a);
        a.click();
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
      } else {
        const error = await response.json();
	 setMessage({ type: 'error', text: `Download error: ${error.error || 'Unknown error'}` });
      }
    } catch (error) {
      console.error('Certificate download error:', error);
      setMessage({ type: 'error', text: 'Connection error during download' });
    } finally {
      setCertificateDownloading(false);
    }
  };

  // Filtrer les champs par catégorie
  const getPrimaryFields = () => Object.entries(IMAGE_FIELD_LABELS).filter(([_, info]) => info.category === 'primary');
  const getBackupFields = () => Object.entries(IMAGE_FIELD_LABELS).filter(([_, info]) => info.category === 'backup');
  const getSpecialFields = () => Object.entries(IMAGE_FIELD_LABELS).filter(([_, info]) => info.category === 'special');

  const renderFieldSection = (fields, title, sectionKey) => (
    <div className="space-y-4">
      <h5 className="text-md font-semibold text-gray-800 border-b pb-2">{title}</h5>
      {fields.map(([fieldName, fieldInfo]) => (
        <div key={fieldName} className="border border-gray-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center">
              <span className="text-lg mr-2">{fieldInfo.icon}</span>
              <div>
                <h6 className="font-medium text-gray-900">{fieldInfo.label}</h6>
                <p className="text-sm text-gray-500">{fieldInfo.description}</p>
              </div>
            </div>
            <button
              onClick={() => addImageUrl(fieldName)}
              className="px-3 py-1 bg-blue-100 text-blue-700 rounded-md hover:bg-blue-200 flex items-center text-sm"
            >
              <Plus className="h-3 w-3 mr-1" />
              Add
            </button>
          </div>

          <div className="space-y-2">
            {(imageFields[fieldName] || []).map((url, index) => (
              <div key={index} className="flex gap-2">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => updateImageUrl(fieldName, index, e.target.value)}
                  placeholder="https://images.operagallery.com/..."
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-sm"
                />
                {url && (
                  <a
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="px-2 py-2 text-gray-500 hover:text-blue-600"
                    title="Voir l'image"
                  >
                    <Eye className="h-4 w-4" />
                  </a>
                )}
                <button
                  onClick={() => removeImageUrl(fieldName, index)}
                  className="px-2 py-2 text-red-500 hover:text-red-700"
                  title="Supprimer"
                >
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            ))}
            
            {(!imageFields[fieldName] || imageFields[fieldName].length === 0) && (
		<p className="text-sm text-gray-500 italic">No image for this field</p>
            )}
          </div>
        </div>
      ))}
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
          <Image className="h-5 w-5 mr-2 text-blue-600" />
		FileMaker Image Management
        </h3>

        {/* Recherche */}
        <div className="flex gap-4 mb-6">
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              ID Artwork
            </label>
            <input
              type="text"
              value={searchId}
              onChange={(e) => setSearchId(e.target.value)}
              placeholder="ex: PICASSO-123, MONET-456..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              onKeyPress={(e) => e.key === 'Enter' && searchArtwork()}
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={searchArtwork}
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              <Search className="h-4 w-4 mr-2" />
		{loading ? 'Search...' : 'Search'}
            </button>
          </div>
        </div>

        {/* Messages */}
        {message && (
          <div className={`mb-4 p-3 rounded-md flex items-center ${
            message.type === 'success' 
              ? 'bg-green-50 text-green-800 border border-green-200'
              : 'bg-red-50 text-red-800 border border-red-200'
          }`}>
            {message.type === 'success' ? (
              <CheckCircle className="h-4 w-4 mr-2" />
            ) : (
              <AlertCircle className="h-4 w-4 mr-2" />
            )}
            {message.text}
          </div>
        )}

        {/* Informations de l'artwork */}
        {artwork && (
          <div className="mb-6 p-4 bg-gray-50 rounded-md">
            <div className="flex justify-between items-start mb-2">
              <h4 className="font-semibold text-gray-900">Artwork Information</h4>
              {artwork.CertificateFMUrl && (
                <button
                  onClick={() => downloadCertificate(artwork.IdName)}
                  disabled={certificateDownloading}
                  className="px-3 py-1 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center text-sm"
		  title="Download PDF certificate"
                >
                  <Download className="h-3 w-3 mr-1" />
		{certificateDownloading ? 'Downloading...' : 'PDF Certificate'}
                </button>
              )}
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <span className="font-medium">ID:</span> {artwork.IdName}
              </div>
              <div>
                <span className="font-medium">Titre:</span> {artwork.Title || 'N/A'}
              </div>
              <div>
                <span className="font-medium">Artiste:</span> {artwork.Artist || 'N/A'}
              </div>
              <div>
                <span className="font-medium">Date:</span> {artwork.Date || 'N/A'}
              </div>
            </div>
            {artwork.CertificateWording && (
              <div className="mt-3 p-2 bg-green-50 border border-green-200 rounded text-sm">
                <span className="font-medium text-green-800">Certificate:</span>
                <p className="text-green-700 mt-1">{artwork.CertificateWording}</p>
              </div>
            )}
          </div>
        )}

        {/* Édition des champs d'images */}
        {artwork && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h4 className="text-lg font-semibold text-gray-900">Image Fields</h4>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowBackupFields(!showBackupFields)}
                  className="px-3 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 flex items-center text-sm"
                >
                  <Archive className="h-4 w-4 mr-2" />
                  {showBackupFields ? 'Hide' : 'Show'} Backup
                </button>
                <button
                  onClick={deleteAllPhotos}
                  disabled={saving}
                  className="px-3 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center text-sm"
                  title="Delete all photos of this artwork"
                >
                  <Trash2 className="h-4 w-4 mr-2" />
               	    Delete All
                </button>
                <button
                  onClick={saveChanges}
                  disabled={saving}
                  className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
                >
                  <Save className="h-4 w-4 mr-2" />
                  {saving ? 'Saving...' : 'Saving'}
                </button>
              </div>
            </div>

            {/* Champs principaux */}
            {renderFieldSection(getPrimaryFields(), "Main Image Fields", 'primary')}

            {/* Champs spéciaux */}
            <div className="mt-8">
              {renderFieldSection(getSpecialFields(), "Special Fields (OpenSea & UHD)", 'special')}
            </div>

            {/* Champs de backup */}
            {showBackupFields && (
              <div className="mt-8">
                {renderFieldSection(getBackupFields(), "Backup Fields (ImageBAK1-5)", 'backup')}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
