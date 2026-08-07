import React, { useState, useEffect } from 'react';
import { Clock, User, CheckCircle, XCircle, Tag, RefreshCw, ChevronLeft, ChevronRight } from 'lucide-react';

const ValidationHistory = () => {
  const [validations, setValidations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalValidations, setTotalValidations] = useState(0);

  // Fetch validation history
  const fetchValidations = async (page = 1) => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/validations/recent?page=${page}&limit=20`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
	throw new Error(`Error ${response.status}`);
      }
      
      const data = await response.json();
      setValidations(data.validations || []);
      setCurrentPage(page);
      setTotalPages(data.total_pages || 1);
      setTotalValidations(data.total || 0);
      
    } catch (err) {
      console.error('Error fetching validations:', err);
      setError(`Error loading: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Handle page change
  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= totalPages) {
      fetchValidations(newPage);
    }
  };

  // Get status icon and color
  const getStatusDisplay = (status) => {
    switch (status) {
      case 'validated':
        return {
          icon: <CheckCircle className="h-5 w-5 text-green-500" />,
          text: 'Validated',
          bgColor: 'bg-green-50',
          textColor: 'text-green-800'
        };
      case 'rejected':
        return {
          icon: <XCircle className="h-5 w-5 text-red-500" />,
          text: 'Rejected',
          bgColor: 'bg-red-50',
          textColor: 'text-red-800'
        };
      case 'scheduled':
        return {
          icon: <Clock className="h-5 w-5 text-blue-500" />,
          text: 'Scheduled',
          bgColor: 'bg-blue-50',
          textColor: 'text-blue-800'
        };
      default:
        return {
          icon: <Clock className="h-5 w-5 text-gray-500" />,
          text: 'Pending',
          bgColor: 'bg-gray-50',
          textColor: 'text-gray-800'
        };
    }
  };

  // Format date
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Initialize
  useEffect(() => {
    fetchValidations(1);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-4">
            Validation History
          </h1>
          
          <div className="bg-white rounded-lg shadow p-6 mb-6">
            <div className="flex items-center justify-between">
              <p className="text-gray-600">
                {totalValidations} action{totalValidations !== 1 ? 's' : ''} total
              </p>
              <button
                onClick={() => fetchValidations(currentPage)}
                className="flex items-center gap-2 px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
              >
                <RefreshCw className="h-4 w-4" />
                Refresh
              </button>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 mb-6">
            {error}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <RefreshCw className="h-8 w-8 text-blue-500 animate-spin mx-auto mb-2" />
		<p className="text-gray-600">Loading history...</p>
            </div>
          </div>
        )}

        {/* Validations List */}
        {!loading && validations.length > 0 && (
          <>
            <div className="bg-white rounded-lg shadow overflow-hidden mb-8">
              <div className="divide-y divide-gray-200">
                {validations.map((validation, index) => {
                  const statusDisplay = getStatusDisplay(validation.status);
                  
                  return (
                    <div key={index} className="p-6 hover:bg-gray-50">
                      <div className="flex items-start gap-4">
                        
                        {/* Status Icon */}
                        <div className="flex-shrink-0">
                          {statusDisplay.icon}
                        </div>
                        
                        {/* Content */}
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between">
                            
                            {/* Main Info */}
                            <div className="flex-1">
                              <h3 className="text-lg font-medium text-gray-900 mb-1">
                                {validation.photo_filename || validation.photo_id}
                              </h3>
                              
                              <div className="flex items-center gap-4 mb-2">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusDisplay.bgColor} ${statusDisplay.textColor}`}>
                                  {statusDisplay.text}
                                </span>
                                
                                {validation.classification && (
                                  <span className="inline-flex items-center gap-1 text-sm text-green-600">
                                    <Tag className="h-4 w-4" />
                                    {validation.classification}
                                  </span>
                                )}
                              </div>
                              
                              <div className="flex items-center gap-6 text-sm text-gray-500">
                                {validation.validator_username && (
                                  <span className="flex items-center gap-1">
                                    <User className="h-4 w-4" />
                                    Validated by: <strong>{validation.validator_username}</strong>
                                  </span>
                                )}
                                
                                {validation.submitted_by && (
                                  <span className="flex items-center gap-1">
                                    <User className="h-4 w-4" />
                                    Submitted by: <strong>{validation.submitted_by}</strong>
                                  </span>
                                )}
                              </div>
                              
                              {validation.reject_reason && (
                                <div className="mt-2 p-3 bg-red-50 border border-red-200 rounded">
                                  <p className="text-sm text-red-700">
                                    <strong>Rejection reason:</strong> {validation.reject_reason}
                                  </p>
                                </div>
                              )}
                            </div>
                            
                            {/* Date */}
                            <div className="flex-shrink-0 text-right">
                              <p className="text-sm text-gray-500">
                                {formatDate(validation.validated_at)}
                              </p>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2">
                <button
                  onClick={() => handlePageChange(currentPage - 1)}
                  disabled={currentPage === 1}
                  className="flex items-center gap-1 px-3 py-2 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-4 w-4" />
                  Previous
                </button>
                
                <div className="flex items-center gap-1">
                  {[...Array(Math.min(5, totalPages))].map((_, i) => {
                    let pageNum;
                    if (totalPages <= 5) {
                      pageNum = i + 1;
                    } else if (currentPage <= 3) {
                      pageNum = i + 1;
                    } else if (currentPage >= totalPages - 2) {
                      pageNum = totalPages - 4 + i;
                    } else {
                      pageNum = currentPage - 2 + i;
                    }
                    
                    return (
                      <button
                        key={pageNum}
                        onClick={() => handlePageChange(pageNum)}
                        className={`px-3 py-2 rounded ${
                          pageNum === currentPage
                            ? 'bg-blue-500 text-white'
                            : 'bg-white border border-gray-300 hover:bg-gray-50'
                        }`}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>
                
                <button
                  onClick={() => handlePageChange(currentPage + 1)}
                  disabled={currentPage === totalPages}
                  className="flex items-center gap-1 px-3 py-2 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            )}
          </>
        )}

        {/* Empty state */}
        {!loading && validations.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📋</div>
		<h3 className="text-lg font-medium text-gray-900 mb-2">No action found</h3>
            <p className="text-gray-600">
              No validation or rejection has been performed yet.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default ValidationHistory;
