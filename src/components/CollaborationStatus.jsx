// src/components/CollaborationStatus.jsx
import React, { useState } from 'react';

export function CollaborationStatus({ status }) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const { active_users = [], locked_photos = [] } = status;
  
  return (
    <div className="bg-white rounded-lg shadow-sm p-3">
      <div 
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-2">
          <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-blue-500" viewBox="0 0 20 20" fill="currentColor">
            <path d="M13 6a3 3 0 11-6 0 3 3 0 016 0zM18 8a2 2 0 11-4 0 2 2 0 014 0zM14 15a4 4 0 00-8 0v3h8v-3zM6 8a2 2 0 11-4 0 2 2 0 014 0zM16 18v-3a5.972 5.972 0 00-.75-2.906A3.005 3.005 0 0119 15v3h-3zM4.75 12.094A5.973 5.973 0 004 15v3H1v-3a3 3 0 013.75-2.906z" />
          </svg>
          <h3 className="font-medium">
            Collaboration
          </h3>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Compteur d'utilisateurs actifs */}
          <div className="flex items-center">
            <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-green-100 text-green-800 text-xs font-medium mr-1">
              {active_users.length}
            </span>
            <span className="text-sm text-gray-600">utilisateurs actifs</span>
          </div>
          
          {/* Compteur de photos verrouillées */}
          <div className="flex items-center">
            <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-yellow-100 text-yellow-800 text-xs font-medium mr-1">
              {locked_photos.length}
            </span>
		<span className="text-sm text-gray-600">locked photos</span>
          </div>
          
          {/* Icône d'expansion */}
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            className={`h-5 w-5 text-gray-400 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
            viewBox="0 0 20 20" 
            fill="currentColor"
          >
            <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
          </svg>
        </div>
      </div>
      
      {/* Détails (visibles seulement si développé) */}
      {isExpanded && (
        <div className="mt-3 border-t pt-3">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Liste des utilisateurs actifs */}
            <div>
		<h4 className="text-sm font-medium text-gray-700 mb-2">Active Users</h4>
              {active_users.length === 0 ? (
		<p className="text-sm text-gray-500 italic">No active users</p>
              ) : (
                <ul className="text-sm space-y-1">
                  {active_users.map(user => (
                    <li key={user.username} className="flex items-center space-x-2">
                      <span className="h-2 w-2 rounded-full bg-green-500"></span>
                      <span>{user.username}</span>
                      <span className="text-xs text-gray-500">
                        {new Date(user.last_active).toLocaleTimeString()}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
            
            {/* Liste des photos verrouillées */}
            <div>
		<h4 className="text-sm font-medium text-gray-700 mb-2">Locked Photos</h4>
              {locked_photos.length === 0 ? (
		<p className="text-sm text-gray-500 italic">No locked photos</p>
              ) : (
                <ul className="text-sm space-y-1">
                  {locked_photos.map(lock => (
                    <li key={lock.photo_id} className="flex items-center space-x-2">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 text-yellow-500" viewBox="0 0 20 20" fill="currentColor">
                        <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd" />
                      </svg>
                      <span className="truncate max-w-xs">{lock.photo_id}</span>
                      <span className="text-xs text-gray-500">
                        par {lock.username}, expire à {new Date(lock.expires_at).toLocaleTimeString()}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
