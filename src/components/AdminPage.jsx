// src/components/AdminPage.jsx
import React, { useState } from 'react';
import { Users, Database, Image, Calendar, RefreshCw, Settings } from 'lucide-react';
import UserManagement from './UserManagement';
import ArtistIndexingManager from './ArtistIndexingManager';
import { FileMakerImageManager } from './FileMakerImageManager';
import { ScheduledUploadsManager } from './ScheduledUploadsManager';

// Super-admin only: manually re-sync validated DAS images into OperaCRM.
function CrmSyncPanel() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const runResync = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const resp = await fetch('/api/admin/resync-crm', {
        method: 'POST',
        headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
      });
      const data = await resp.json();
      if (resp.ok && data.success) setResult(data);
      else setError(data.error || 'Re-sync failed');
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-xl">
      <h3 className="text-xl font-semibold text-gray-900 mb-2">
        Re-sync validated photos to CRM
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        Pushes every validated DAS photo to OperaCRM. Matches artworks by ID
        number (accent/prefix-insensitive) and only fills empty fields — existing
        CRM images are never overwritten. Runs automatically every 20 minutes;
        use this to force it now.
      </p>
      <button
        onClick={runResync}
        disabled={loading}
        className={`flex items-center px-4 py-2 rounded-md text-white font-medium ${
          loading ? 'bg-gray-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
        }`}
      >
        <RefreshCw className={`h-5 w-5 mr-2 ${loading ? 'animate-spin' : ''}`} />
        {loading ? 'Syncing… (may take ~30s)' : 'Re-sync now'}
      </button>

      {error && (
        <div className="mt-4 p-3 rounded bg-red-50 border border-red-200 text-red-700 text-sm">
          {error}
        </div>
      )}
      {result && (
        <div className="mt-4 p-4 rounded bg-green-50 border border-green-200 text-sm text-gray-800">
          <div className="font-semibold text-green-800 mb-2">✓ Sync complete</div>
          <div>Pushed to CRM: <b>{result.pushed}</b></div>
          <div>Already in CRM (left alone): {result.already_in_crm}</div>
          <div>Artwork not in CRM: {result.not_in_crm}</div>
          <div>Ambiguous (skipped): {result.ambiguous}</div>
          <div>Errors: {result.errors}</div>
        </div>
      )}
    </div>
  );
}

export function AdminPage() {
  const [activeTab, setActiveTab] = useState('users');

  const tabs = [
    { id: 'users', label: 'User Management', icon: Users },
    { id: 'indexing', label: 'Artists Index', icon: Database },
    { id: 'images', label: 'FileMaker Images', icon: Image },
    { id: 'scheduled', label: 'Scheduled Uploads', icon: Calendar },
    { id: 'crmsync', label: 'CRM Sync', icon: RefreshCw },
  ];

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center mb-6">
        <Settings className="h-8 w-8 text-blue-600 mr-3" />
        <h2 className="text-3xl font-bold text-gray-900">Administration</h2>
      </div>

      <div className="border-b border-gray-200 mb-8">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                <Icon className="h-5 w-5 mr-2" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="mt-6">
        {activeTab === 'users' && <UserManagement />}
        {activeTab === 'indexing' && <ArtistIndexingManager />}
        {activeTab === 'images' && <FileMakerImageManager />}
        {activeTab === 'scheduled' && <ScheduledUploadsManager />}
        {activeTab === 'crmsync' && <CrmSyncPanel />}
      </div>
    </div>
  );
}
