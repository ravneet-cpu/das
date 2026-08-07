// src/components/ScheduledUploadsManager.jsx
import React, { useState, useEffect } from 'react';
import { Clock, Trash2, Play, RefreshCw, Calendar, User, Image, AlertCircle, CheckCircle } from 'lucide-react';

export function ScheduledUploadsManager() {
  const [uploads, setUploads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [message, setMessage] = useState(null);

  useEffect(() => {
    loadScheduledUploads();
  }, []);

  const loadScheduledUploads = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/admin/scheduled-uploads', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setUploads(data.uploads || []);
      } else {
        const error = await response.json();
	 setMessage({ type: 'error', text: error.error || 'Loading error' });
      }
    } catch (error) {
      console.error('Error loading scheduled uploads:', error);
      setMessage({ type: 'error', text: 'Connection error' });
    } finally {
      setLoading(false);
    }
  };

  const cancelUpload = async (uploadId) => {
    const confirmCancel = window.confirm('Are you sure you want to cancel this scheduled upload?');
    if (!confirmCancel) return;

    try {
      const token = localStorage.getItem('token');
      const response = await fetch(`/api/admin/scheduled-uploads/${uploadId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        setMessage({ type: 'success', text: 'Upload cancelled successfully' });
        loadScheduledUploads(); // Reload the list
      } else {
        const error = await response.json();
	setMessage({ type: 'error', text: error.error || 'Error during cancellation' });
      }
    } catch (error) {
      console.error('Error cancelling upload:', error);
      setMessage({ type: 'error', text: 'Connection error' });
    }
  };

  const processUploads = async () => {
    setProcessing(true);
    try {
      const token = localStorage.getItem('token');
      const response = await fetch('/api/admin/process-scheduled-uploads', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (response.ok) {
        const data = await response.json();
        setMessage({ type: 'success', text: data.message });
        loadScheduledUploads(); // Reload the list
      } else {
        const error = await response.json();
	setMessage({ type: 'error', text: error.error || 'Error during processing' });
      }
    } catch (error) {
      console.error('Error processing uploads:', error);
      setMessage({ type: 'error', text: 'Connection error' });
    } finally {
      setProcessing(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'scheduled':
        return <Clock className="h-4 w-4 text-blue-500" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'cancelled':
        return <Trash2 className="h-4 w-4 text-gray-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'scheduled':
        return 'Scheduled';
      case 'completed':
        return 'Completed';
      case 'failed':
        return 'Failed';
      case 'cancelled':
        return 'Cancelled';
      default:
        return status;
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'scheduled':
        return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'completed':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'failed':
        return 'bg-red-100 text-red-800 border-red-200';
      case 'cancelled':
        return 'bg-gray-100 text-gray-800 border-gray-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('fr-FR');
  };

  const isOverdue = (scheduledDate, status) => {
    return status === 'scheduled' && new Date(scheduledDate) < new Date();
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="bg-white rounded-lg shadow-md">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-bold text-gray-900 flex items-center">
              <Calendar className="h-6 w-6 mr-2" />
              Scheduled Uploads
            </h2>
            <div className="flex gap-2">
              <button
                onClick={loadScheduledUploads}
                disabled={loading}
                className="px-4 py-2 bg-gray-100 text-gray-700 rounded-md hover:bg-gray-200 disabled:opacity-50 flex items-center"
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
                Refresh
              </button>
              <button
                onClick={processUploads}
                disabled={processing || uploads.filter(u => u.status === 'scheduled').length === 0}
                className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
              >
                <Play className={`h-4 w-4 mr-2 ${processing ? 'animate-spin' : ''}`} />
                {processing ? 'Processing...' : 'Process now'}
              </button>
            </div>
          </div>
        </div>

        {/* Message */}
        {message && (
          <div className={`m-6 p-3 rounded-md flex items-center ${
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
            <button
              onClick={() => setMessage(null)}
              className="ml-auto text-lg font-bold opacity-50 hover:opacity-100"
            >
              ×
            </button>
          </div>
        )}

        {/* Content */}
        <div className="p-6">
          {loading ? (
            <div className="text-center py-8">
              <RefreshCw className="h-8 w-8 animate-spin text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600">Loading scheduled uploads...</p>
            </div>
          ) : uploads.length === 0 ? (
            <div className="text-center py-8">
              <Calendar className="h-12 w-12 text-gray-300 mx-auto mb-4" />
		 <h3 className="text-lg font-medium text-gray-900 mb-2">No scheduled uploads</h3>
              <p className="text-gray-500">Scheduled uploads will appear here</p>
            </div>
          ) : (
            <div className="space-y-4">
              {uploads.map((upload) => (
                <div
                  key={upload.id}
                  className={`border rounded-lg p-4 ${
                    isOverdue(upload.scheduled_date, upload.status) 
                      ? 'border-orange-300 bg-orange-50' 
                      : 'border-gray-200 bg-white'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      {/* Status */}
                      <div className={`flex items-center px-2 py-1 rounded-md text-xs font-medium border ${getStatusColor(upload.status)}`}>
                        {getStatusIcon(upload.status)}
                        <span className="ml-1">{getStatusText(upload.status)}</span>
                      </div>

                      {/* Artwork Info */}
                      <div>
                        <div className="flex items-center text-sm font-medium text-gray-900">
                          <Image className="h-4 w-4 mr-1" />
                          {upload.artwork_id}
                          <span className="ml-2 px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">
                            {upload.classification}
                          </span>
                        </div>
                        <div className="text-sm text-gray-500">
                          {upload.photo_filename}
                        </div>
                      </div>

                      {/* Dates */}
                      <div className="text-sm text-gray-600">
                        <div className="flex items-center">
                          <Clock className="h-3 w-3 mr-1" />
                          <span className={isOverdue(upload.scheduled_date, upload.status) ? 'text-orange-600 font-medium' : ''}>
                            {formatDate(upload.scheduled_date)}
                          </span>
                        </div>
                        {upload.processed_at && (
                          <div className="text-xs text-gray-400 mt-1">
                            Processed on {formatDate(upload.processed_at)}
                          </div>
                        )}
                      </div>

                      {/* Creator */}
                      <div className="text-sm text-gray-500 flex items-center">
                        <User className="h-3 w-3 mr-1" />
                        {upload.created_by}
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center space-x-2">
                      {isOverdue(upload.scheduled_date, upload.status) && (
                        <span className="text-xs text-orange-600 font-medium">EN RETARD</span>
                      )}
                      
                      {upload.status === 'scheduled' && (
                        <button
                          onClick={() => cancelUpload(upload.id)}
                          className="px-3 py-1 bg-red-100 text-red-700 rounded-md hover:bg-red-200 flex items-center text-sm"
                          title="Annuler cet upload"
                        >
                          <Trash2 className="h-3 w-3 mr-1" />
                          Annuler
                        </button>
                      )}

                      {upload.error_message && (
                        <div className="text-xs text-red-600 max-w-xs truncate" title={upload.error_message}>
                           Error: {upload.error_message}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
