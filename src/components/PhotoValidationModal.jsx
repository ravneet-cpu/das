import React, { useState, useEffect } from 'react';
import { ThumbsUp, ThumbsDown, X, CheckCircle } from 'lucide-react';

const PhotoValidationModal = ({ 
  photo, 
  isOpen, 
  onClose, 
  onValidate, 
  onReject, 
  loading = false,
  initialMode = 'choose' // Allow setting initial mode
}) => {
  const [classification, setClassification] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [customReason, setCustomReason] = useState('');
  const [mode, setMode] = useState(initialMode); // Use initialMode prop

  // Update mode when initialMode changes
  useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);

  // Classification values must match dasKey in artworkImageConfig.ts (CRM).
  // Display order mirrors ARTWORK_IMAGE_TYPES.displayOrder.
  const classifications = [
    { value: 'LEFT',          label: 'LEFT — Left side' },
    { value: 'MAIN',          label: 'MAIN — Front / Main image' },
    { value: 'RIGHT',         label: 'RIGHT — Right side' },
    { value: 'BACK',          label: 'BACK — Back / Reverse' },
    { value: 'PERS',          label: 'PERS — Perspective' },
    { value: 'INSITU',        label: 'INSITU — In Situ / Installation' },
    { value: 'EDITIONNUMBER', label: 'EDITIONNUMBER — Edition number' },
    { value: 'DET',           label: 'DET — Detail 1' },
    { value: 'DET2',          label: 'DET2 — Detail 2' },
    { value: 'OTHER',         label: 'OTHER — Other' },
    { value: 'OTHER2',        label: 'OTHER2 — Other 2' },
    { value: 'FRAME',         label: 'FRAME — Frame (admin)' },
    { value: 'VIDEO',         label: 'VIDEO — Video' },
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

  const handleValidateSubmit = () => {
    if (!classification) return;
    onValidate(photo, classification);
    handleClose();
  };

  const handleRejectSubmit = () => {
    let finalReason = rejectReason;
    if (rejectReason === 'Other (specify)' && customReason) {
      finalReason = customReason;
    }
    if (!finalReason) return;
    
    onReject(photo, finalReason);
    handleClose();
  };

  const handleClose = () => {
    setClassification('');
    setRejectReason('');
    setCustomReason('');
    setMode(initialMode);
    onClose();
  };

  if (!isOpen || !photo) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-xl font-bold text-gray-900">
              {mode === 'choose' ? 'Review Photo' : 
               mode === 'validate' ? 'Validate Photo' : 'Reject Photo'}
            </h3>
            <button
              onClick={handleClose}
              className="p-2 hover:bg-gray-100 rounded-full"
            >
              <X className="w-6 h-6" />
            </button>
          </div>

          {/* Photo info */}
          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h4 className="font-semibold text-gray-900 mb-2">Photo: {photo.filename}</h4>
            <div className="text-sm text-gray-600">
              <p>Path: {photo.id}</p>
              {photo.artwork_id && (
                <p>Artwork ID: <span className="font-mono text-blue-600">{photo.artwork_id}</span></p>
              )}
            </div>
          </div>

          {/* Mode selection */}
          {mode === 'choose' && (
            <div className="space-y-4">
              <div className="flex gap-4">
                <button
                  onClick={() => setMode('validate')}
                  className="flex-1 px-6 py-4 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors flex items-center justify-center font-semibold"
                >
                  <ThumbsUp className="w-5 h-5 mr-2" />
                  Validate Photo
                </button>
                <button
                  onClick={() => setMode('reject')}
                  className="flex-1 px-6 py-4 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors flex items-center justify-center font-semibold"
                >
                  <ThumbsDown className="w-5 h-5 mr-2" />
                  Reject Photo
                </button>
              </div>
              <button
                onClick={handleClose}
                className="w-full px-6 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
            </div>
          )}

          {/* Validation form */}
          {mode === 'validate' && (
            <div className="space-y-6">
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">Select Classification:</h4>
                <div className="grid grid-cols-1 gap-2 max-h-60 overflow-y-auto">
                  {classifications.map((classif) => (
                    <label key={classif.value} className="flex items-center p-3 hover:bg-gray-50 rounded cursor-pointer border">
                      <input
                        type="radio"
                        name="classification"
                        value={classif.value}
                        checked={classification === classif.value}
                        onChange={(e) => setClassification(e.target.value)}
                        className="mr-3 w-4 h-4 text-green-600"
                      />
                      <span className="text-gray-800">{classif.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex gap-3">
                <button
                  onClick={handleValidateSubmit}
                  disabled={loading || !classification}
                  className="flex-1 px-6 py-3 bg-green-600 text-white font-semibold rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="w-4 h-4 mr-2" />
                      Validate Photo
                    </>
                  )}
                </button>
                <button
                  onClick={() => setMode('choose')}
                  className="px-6 py-3 bg-gray-600 text-white font-semibold rounded-lg hover:bg-gray-700 transition-colors"
                >
                  Back
                </button>
              </div>
            </div>
          )}

          {/* Rejection form */}
          {mode === 'reject' && (
            <div className="space-y-6">
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">Select Rejection Reason:</h4>
                <div className="grid grid-cols-1 gap-2 max-h-60 overflow-y-auto">
                  {rejectReasons.map((reason) => (
                    <label key={reason} className="flex items-center p-3 hover:bg-gray-50 rounded cursor-pointer border">
                      <input
                        type="radio"
                        name="rejectReason"
                        value={reason}
                        checked={rejectReason === reason}
                        onChange={(e) => setRejectReason(e.target.value)}
                        className="mr-3 w-4 h-4 text-red-600"
                      />
                      <span className="text-gray-800">{reason}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Custom reason */}
              {rejectReason === 'Other (specify)' && (
                <div>
                  <textarea
                    value={customReason}
                    onChange={(e) => setCustomReason(e.target.value)}
                    placeholder="Specify the rejection reason..."
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500"
                    rows="3"
                  />
                </div>
              )}

              <div className="flex gap-3">
                <button
                  onClick={handleRejectSubmit}
                  disabled={loading || !rejectReason}
                  className="flex-1 px-6 py-3 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Processing...
                    </>
                  ) : (
                    <>
                      <X className="w-4 h-4 mr-2" />
                      Reject Photo
                    </>
                  )}
                </button>
                <button
                  onClick={() => setMode('choose')}
                  className="px-6 py-3 bg-gray-600 text-white font-semibold rounded-lg hover:bg-gray-700 transition-colors"
                >
                  Back
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default PhotoValidationModal;