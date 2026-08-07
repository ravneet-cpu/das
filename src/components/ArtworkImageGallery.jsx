// src/components/ArtworkImageGallery.jsx
import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Image as ImageIcon, ZoomIn, X } from 'lucide-react';

// Mapping des champs vers des labels lisibles
const IMAGE_FIELD_LABELS = {
  'MAIN300': { label: 'Main Images', icon: '🎨', description: 'Primary views' },
  'OTHER300': { label: 'Other Views', icon: '👁️', description: 'Additional perspectives' },
  'DET300': { label: 'Details', icon: '🔍', description: 'Close-up details' },
  'INSITU300': { label: 'In Situ', icon: '🏛️', description: 'Installed/displayed' },
  'BACK300': { label: 'Back Views', icon: '🔄', description: 'Reverse side' },
  'FRONT300': { label: 'Front Views', icon: '⬜', description: 'Front view' },
  'FRAME300': { label: 'Frame', icon: '🖼️', description: 'Frame details' },
  'LEFT300': { label: 'Left Side', icon: '⬅️', description: 'Left side view' },
  'FRONTRIGHT300': { label: 'Front Right', icon: '↗️', description: 'Front right angle' },
  'PERS300': { label: 'Perspective', icon: '📐', description: 'Perspective views' },
  // Local-catalogue type keys (FM/300/A5 dirs)
  'MAIN': { label: 'Main (FM)', icon: '🎨', description: 'Full-resolution images' },
  '300': { label: 'Web 300', icon: '🖼️', description: 'Web-size images' },
  'A5': { label: 'A5', icon: '📄', description: 'A5 prints' },
};

export const ArtworkImageGallery = ({ artwork, showTitle = true }) => {
  const [expandedSections, setExpandedSections] = useState({ MAIN300: true }); // Main section open by default
  const [selectedImage, setSelectedImage] = useState(null);
  const [showAllImages, setShowAllImages] = useState(false);

  // Get image fields from artwork data
  const imageFields = artwork?.image_fields || {};
  
  // Parse URLs (handle multiple URLs separated by newlines)
  const parseImageUrls = (urlString) => {
    if (!urlString || typeof urlString !== 'string') return [];
    return urlString.split('\n').map(url => url.trim()).filter(url => url.length > 0);
  };

  // Get all available image sections
  const availableImageSections = Object.entries(imageFields)
    .map(([fieldName, urlString]) => ({
      fieldName,
      urls: parseImageUrls(urlString),
      ...IMAGE_FIELD_LABELS[fieldName]
    }))
    .filter(section => section.urls.length > 0)
    .sort((a, b) => {
      // Sort by priority: MAIN first, then alphabetically
      if (a.fieldName === 'MAIN300' || a.fieldName === 'MAIN') return -1;
      if (b.fieldName === 'MAIN300' || b.fieldName === 'MAIN') return 1;
      return (a.label || a.fieldName || '').localeCompare(b.label || b.fieldName || '');
    });

  // Toggle section expansion
  const toggleSection = (fieldName) => {
    setExpandedSections(prev => ({
      ...prev,
      [fieldName]: !prev[fieldName]
    }));
  };

  // Open image in modal
  const openImageModal = (imageUrl, sectionLabel) => {
    setSelectedImage({ url: imageUrl, section: sectionLabel });
  };

  // Close image modal
  const closeImageModal = () => {
    setSelectedImage(null);
  };

  if (availableImageSections.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <ImageIcon className="h-12 w-12 mx-auto mb-2 opacity-50" />
        <p>No additional images available</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {showTitle && (
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900 flex items-center">
            <ImageIcon className="h-5 w-5 mr-2" />
            Artwork Images ({availableImageSections.reduce((total, section) => total + section.urls.length, 0)})
          </h3>
          
          {availableImageSections.length > 1 && (
            <button
              onClick={() => setShowAllImages(!showAllImages)}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium"
            >
              {showAllImages ? 'Collapse All' : 'Expand All'}
            </button>
          )}
        </div>
      )}

      {/* Image Sections */}
      <div className="space-y-3">
        {availableImageSections.map((section) => {
          const isExpanded = showAllImages || expandedSections[section.fieldName];
          const urlCount = section.urls.length;

          return (
            <div key={section.fieldName} className="border border-gray-200 rounded-lg overflow-hidden">
              {/* Section Header */}
              <button
                onClick={() => toggleSection(section.fieldName)}
                className="w-full px-4 py-3 bg-gray-50 hover:bg-gray-100 flex items-center justify-between transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <span className="text-lg">{section.icon}</span>
                  <div className="text-left">
                    <div className="font-medium text-gray-900">{section.label}</div>
                    <div className="text-sm text-gray-500">{section.description}</div>
                  </div>
                </div>
                
                <div className="flex items-center space-x-2">
                  <span className="text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded-full">
                    {urlCount} image{urlCount !== 1 ? 's' : ''}
                  </span>
                  {isExpanded ? (
                    <ChevronUp className="h-4 w-4 text-gray-500" />
                  ) : (
                    <ChevronDown className="h-4 w-4 text-gray-500" />
                  )}
                </div>
              </button>

              {/* Section Content */}
              {isExpanded && (
                <div className="p-4 bg-white">
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                    {section.urls.map((imageUrl, idx) => (
                      <div
                        key={idx}
                        className="relative group cursor-pointer bg-gray-100 rounded-lg overflow-hidden aspect-square"
                        onClick={() => openImageModal(imageUrl, section.label)}
                      >
                        <img
                          src={imageUrl}
                          alt={`${section.label} ${idx + 1}`}
                          className="w-full h-full object-cover transition-transform group-hover:scale-105"
                          onError={(e) => {
                            e.target.style.display = 'none';
                            e.target.nextSibling.style.display = 'flex';
                          }}
                        />
                        
                        {/* Error placeholder */}
                        <div 
                          className="absolute inset-0 bg-gray-200 flex items-center justify-center text-gray-400 text-xs"
                          style={{ display: 'none' }}
                        >
                          <ImageIcon className="h-6 w-6" />
                        </div>
                        
                        {/* Hover overlay */}
                        <div className="absolute inset-0 bg-black bg-opacity-0 group-hover:bg-opacity-30 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-all">
                          <ZoomIn className="h-6 w-6 text-white" />
                        </div>
                        
                        {/* Image number */}
                        <div className="absolute top-2 left-2 bg-black bg-opacity-60 text-white text-xs px-2 py-1 rounded">
                          {idx + 1}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Image Modal */}
      {selectedImage && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="relative max-w-4xl max-h-full bg-white rounded-lg overflow-hidden">
            {/* Modal Header */}
            <div className="px-4 py-3 bg-gray-50 border-b flex items-center justify-between">
              <div>
                <h4 className="font-medium text-gray-900">{selectedImage.section}</h4>
                <p className="text-sm text-gray-500">{artwork?.title || artwork?.IdName}</p>
              </div>
              <button
                onClick={closeImageModal}
                className="p-2 hover:bg-gray-200 rounded-full transition-colors"
              >
                <X className="h-5 w-5 text-gray-500" />
              </button>
            </div>
            
            {/* Modal Image */}
            <div className="p-4">
              <img
                src={selectedImage.url}
                alt={selectedImage.section}
                className="max-w-full max-h-[70vh] mx-auto rounded"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'flex';
                }}
              />
              
              {/* Error placeholder for modal */}
              <div 
                className="w-full h-64 bg-gray-200 flex items-center justify-center text-gray-400"
                style={{ display: 'none' }}
              >
                <div className="text-center">
                  <ImageIcon className="h-12 w-12 mx-auto mb-2" />
                  <p>Image could not be loaded</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};