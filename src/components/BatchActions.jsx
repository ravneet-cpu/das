// src/components/BatchActions.jsx
import React, { useState } from 'react';

export function BatchActions({ selectedCount, onProcess, selectedPhotos }) {
  const [action, setAction] = useState('');
  const [rejectReason, setRejectReason] = useState('');
  const [customReason, setCustomReason] = useState('');
  const [showConfirm, setShowConfirm] = useState(false);
  
  const handleActionChange = (e) => {
    setAction(e.target.value);
    setRejectReason('');
    setCustomReason('');
    setShowConfirm(false);
  };
  
  const handleRejectReasonChange = (e) => {
    setRejectReason(e.target.value);
    if (e.target.value !== 'custom') {
      setCustomReason('');
    }
  };
  
  const handleProcessClick = () => {
    if (action === 'valider') {
      setShowConfirm(true);
    } else if (action === 'refuser' && rejectReason) {
      setShowConfirm(true);
    }
  };
  
  const confirmProcess = () => {
    let reason = rejectReason;
    if (rejectReason === 'custom' && customReason) {
      reason = customReason;
    }
    
    onProcess(selectedPhotos, action, reason);
    setShowConfirm(false);
    setAction('');
    setRejectReason('');
    setCustomReason('');
  };
  
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
      <div className="flex flex-col md:flex-row md:items-center space-y-3 md:space-y-0 md:space-x-4">
        <div className="flex-shrink-0">
		<span className="font-medium">{selectedCount} photo{selectedCount > 1 ? 's' : ''} selected</span>
        </div>
        
        <div className="flex-grow flex flex-col md:flex-row md:items-center space-y-3 md:space-y-0 md:space-x-3">
          <select
            value={action}
            onChange={handleActionChange}
            className="border border-gray-300 rounded px-3 py-2 w-full md:w-auto"
          >
             <option value="">-- Batch Action --</option>
            <option value="valider">Validate all photos</option>
            <option value="refuser">Reject all photos</option>
          </select>
          
          {action === 'refuser' && (
            <select
              value={rejectReason}
              onChange={handleRejectReasonChange}
              className="border border-gray-300 rounded px-3 py-2 w-full md:w-auto"
            >
              <option value="">-- Motif de rejet --</option>
              <option value="trop-petite">Trop petite</option>
              <option value="mal-prise">Mal prise</option>
              <option value="sans-id">Sans identifiant</option>
              <option value="custom">Autre raison...</option>
            </select>
          )}
          
          {action === 'refuser' && rejectReason === 'custom' && (
            <input
              type="text"
              value={customReason}
              onChange={(e) => setCustomReason(e.target.value)}
              placeholder="Précisez la raison du rejet"
              className="border border-gray-300 rounded px-3 py-2 w-full md:w-auto"
            />
          )}
          
          <button
            onClick={handleProcessClick}
            disabled={!action || (action === 'refuser' && !rejectReason)}
            className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Traiter par lot
          </button>
        </div>
      </div>
      
      {/* Modal de confirmation */}
      {showConfirm && (
        <div className="fixed inset-0 flex items-center justify-center z-50 bg-black bg-opacity-50">
          <div className="bg-white p-5 rounded-lg shadow-lg max-w-md w-full">
            <h3 className="text-lg font-bold mb-3">Confirmation</h3>
            <p>
              Êtes-vous sûr de vouloir {action === 'valider' ? 'valider' : 'refuser'} {selectedCount} photo{selectedCount > 1 ? 's' : ''} ?
              {action === 'refuser' && rejectReason && (
                <span className="block mt-2">
                  Motif : {rejectReason === 'custom' ? customReason : rejectReason}
                </span>
              )}
            </p>
            <div className="flex justify-end mt-4 space-x-3">
              <button
                onClick={() => setShowConfirm(false)}
                className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-100"
              >
                Annuler
              </button>
              <button
                onClick={confirmProcess}
                className={`px-4 py-2 rounded text-white ${
                  action === 'valider' ? 'bg-green-600 hover:bg-green-700' : 'bg-red-600 hover:bg-red-700'
                }`}
              >
                Confirmer
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
