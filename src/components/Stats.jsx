import React, { useState, useEffect } from 'react';
import { BarChart3, TrendingUp, Clock, CheckCircle, XCircle, RefreshCw, ArrowRight, ThumbsUp, ThumbsDown } from 'lucide-react';

// Utility function to safely format numbers
const formatNumber = (num) => {
  if (num === null || num === undefined || isNaN(num)) {
    return '0';
  }
  return Number(num).toLocaleString();
};

const Stats = ({ setView, canValidate, canViewGallery }) => {
  const [stats, setStats] = useState({
    total: 0,
    pending: 0,
    validated: 0,
    rejected: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Fetch stats from backend
  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch('/api/photos/stats', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) {
        throw new Error(`Error ${response.status}`);
      }
      
      const data = await response.json();
      // Stats data loaded
      
      setStats(data);
      setLastUpdated(new Date());
      
    } catch (err) {
      // Error loading stats
      setError(`Loading error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  // Calculate percentages
  const getPercentage = (value, total) => {
    if (total === 0) return 0;
    return ((value / total) * 100).toFixed(1);
  };

  // Initialize and setup auto-refresh
  useEffect(() => {
    fetchStats();
    
    // Auto-refresh every 30 seconds
    const interval = setInterval(fetchStats, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading && !lastUpdated) {
    return (
      <div className="min-h-screen bg-gray-50 py-8 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <RefreshCw className="h-8 w-8 text-blue-500 animate-spin mx-auto mb-2" />
              <p className="text-gray-600">Loading statistics...</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8 px-4">
      <div className="max-w-6xl mx-auto">
        
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              Validation Statistics
            </h1>
            {lastUpdated && (
              <p className="text-gray-600">
                Last updated: {lastUpdated.toLocaleTimeString()}
              </p>
            )}
          </div>
          
          <button
            onClick={fetchStats}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 mb-6">
            {error}
          </div>
        )}

        {/* Main Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          
          {/* Total */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="p-3 bg-blue-100 rounded-full">
                <BarChart3 className="h-6 w-6 text-blue-600" />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-600">Total Photos</p>
                <p className="text-3xl font-bold text-gray-900">{formatNumber(stats.total)}</p>
              </div>
            </div>
          </div>

          {/* Pending */}
          <div 
            className={`bg-white rounded-lg shadow p-6 ${canValidate ? 'cursor-pointer hover:shadow-lg hover:scale-105 transition-all duration-200' : ''}`}
            onClick={canValidate ? () => setView('pending') : undefined}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="p-3 bg-yellow-100 rounded-full">
                  <Clock className="h-6 w-6 text-yellow-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Pending</p>
                  <p className="text-3xl font-bold text-gray-900">{formatNumber(stats.pending)}</p>
                  <p className="text-sm text-gray-500">{getPercentage(stats.pending, stats.total)}%</p>
                </div>
              </div>
              {canValidate && <ArrowRight className="h-5 w-5 text-gray-400" />}
            </div>
          </div>

          {/* Validated */}
          <div 
            className={`bg-white rounded-lg shadow p-6 ${canViewGallery ? 'cursor-pointer hover:shadow-lg hover:scale-105 transition-all duration-200' : ''}`}
            onClick={canViewGallery ? () => setView('validated') : undefined}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="p-3 bg-green-100 rounded-full">
                  <ThumbsUp className="h-6 w-6 text-green-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Validated</p>
                  <p className="text-3xl font-bold text-gray-900">{formatNumber(stats.validated)}</p>
                  <p className="text-sm text-gray-500">{getPercentage(stats.validated, stats.total)}%</p>
                </div>
              </div>
              {canViewGallery && <ArrowRight className="h-5 w-5 text-gray-400" />}
            </div>
          </div>

          {/* Rejected */}
          <div 
            className={`bg-white rounded-lg shadow p-6 ${canViewGallery ? 'cursor-pointer hover:shadow-lg hover:scale-105 transition-all duration-200' : ''}`}
            onClick={canViewGallery ? () => setView('rejected') : undefined}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <div className="p-3 bg-red-100 rounded-full">
                  <ThumbsDown className="h-6 w-6 text-red-600" />
                </div>
                <div className="ml-4">
                  <p className="text-sm font-medium text-gray-600">Rejected</p>
                  <p className="text-3xl font-bold text-gray-900">{formatNumber(stats.rejected)}</p>
                  <p className="text-sm text-gray-500">{getPercentage(stats.rejected, stats.total)}%</p>
                </div>
              </div>
              {canViewGallery && <ArrowRight className="h-5 w-5 text-gray-400" />}
            </div>
          </div>
        </div>

        {/* Progress Overview */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">Validation Progress</h2>
          
          <div className="space-y-4">
            
            {/* Overall Progress */}
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Overall Progress</span>
                <span className="text-sm text-gray-600">
                  {getPercentage(stats.validated + stats.rejected, stats.total)}% 
                  ({formatNumber(stats.validated + stats.rejected)} / {formatNumber(stats.total)})
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-blue-500 h-2 rounded-full transition-all duration-300" 
                  style={{ width: `${getPercentage(stats.validated + stats.rejected, stats.total)}%` }}
                />
              </div>
            </div>

            {/* Validated Progress */}
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Validated Photos</span>
                <span className="text-sm text-gray-600">
                  {getPercentage(stats.validated, stats.total)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-green-500 h-2 rounded-full transition-all duration-300" 
                  style={{ width: `${getPercentage(stats.validated, stats.total)}%` }}
                />
              </div>
            </div>

            {/* Rejected Progress */}
            <div>
              <div className="flex justify-between mb-2">
                <span className="text-sm font-medium text-gray-700">Rejected Photos</span>
                <span className="text-sm text-gray-600">
                  {getPercentage(stats.rejected, stats.total)}%
                </span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div 
                  className="bg-red-500 h-2 rounded-full transition-all duration-300" 
                  style={{ width: `${getPercentage(stats.rejected, stats.total)}%` }}
                />
              </div>
            </div>
          </div>
        </div>


        {/* Summary */}
        {stats.total > 0 && (
          <div className="mt-8 text-center text-gray-600">
            <p>
              Out of {formatNumber(stats.total)} total photos, 
              <span className="font-medium text-green-600 mx-1">{formatNumber(stats.validated)} have been validated</span>
              and 
              <span className="font-medium text-red-600 mx-1">{formatNumber(stats.rejected)} have been rejected</span>.
              There are still 
              <span className="font-medium text-yellow-600 mx-1">{formatNumber(stats.pending)} photos pending</span> 
              validation.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default Stats;