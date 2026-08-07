import React, { useState, useEffect } from 'react';
import { Camera, Play, Pause, RotateCcw, Filter, Download, Eye, AlertTriangle, CheckCircle, Loader } from 'lucide-react';

const QualityChecker = () => {
  const [scanning, setScanning] = useState(false);
  const [results, setResults] = useState([]);
  const [stats, setStats] = useState({});
  const [selectedFolder, setSelectedFolder] = useState('a-valider');
  const [filterQuality, setFilterQuality] = useState('all');
  const [error, setError] = useState(null);

  const folders = [
    { value: 'a-valider', label: '📂 To validate' },
    { value: 'valides', label: '✅ Validated' },
    { value: 'refuses', label: '❌ Rejected' }
  ];

  const qualityFilters = [
    { value: 'all', label: '🔍 All qualities', color: 'gray' },
    { value: 'excellent', label: '🟢 Excellent (300+ DPI)', color: 'green' },
    { value: 'good', label: '🟢 Good (200+ DPI)', color: 'lightgreen' },
    { value: 'acceptable', label: '🟠 Acceptable (150+ DPI)', color: 'orange' },
    { value: 'poor', label: '🔴 Insufficient (<150 DPI)', color: 'red' },
    { value: 'error', label: '⚪ Analysis error', color: 'gray' }
  ];

  const scanPhotos = async () => {
    setScanning(true);
    setError(null);
    setResults([]);

    try {
      const response = await fetch('/api/photos/batch-analyze-quality', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          folder: selectedFolder
        })
      });

      const data = await response.json();

      if (data.success) {
        setResults(data.results);
        setStats(data.stats);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError(`Scan error: ${err.message}`);
    } finally {
      setScanning(false);
    }
  };

  const getQualityIcon = (qualityLevel) => {
    const baseClasses = "w-5 h-5 rounded-full flex items-center justify-center";
    
    switch(qualityLevel) {
      case 'excellent':
        return <div className={`${baseClasses} bg-green-500`} title="Excellent quality">
          <CheckCircle className="w-3 h-3 text-white" />
        </div>;
      case 'good':
        return <div className={`${baseClasses} bg-green-400`} title="Good quality">
          <CheckCircle className="w-3 h-3 text-white" />
        </div>;
      case 'acceptable':
        return <div className={`${baseClasses} bg-orange-500`} title="Acceptable quality">
          <AlertTriangle className="w-3 h-3 text-white" />
        </div>;
      case 'poor':
        return <div className={`${baseClasses} bg-red-500`} title="Insufficient quality">
          <AlertTriangle className="w-3 h-3 text-white" />
        </div>;
      default:
        return <div className={`${baseClasses} bg-gray-500`} title="Unknown quality">
          <AlertTriangle className="w-3 h-3 text-white" />
        </div>;
    }
  };

  const filteredResults = results.filter(result => {
    if (filterQuality === 'all') return true;
    return result.quality_analysis?.quality_level === filterQuality;
  });

  const exportResults = () => {
    const csvContent = [
      ['File', 'Quality', 'A5 DPI', 'Resolution', 'Size (MB)', 'Recommendations'].join(','),
      ...filteredResults.map(result => [
        result.filename,
        result.quality_analysis?.print_quality_a5 || 'Error',
        result.quality_analysis?.equivalent_dpi_a5 || 'N/A',
        result.quality_analysis?.dimensions ? 
          `${result.quality_analysis.dimensions.width}x${result.quality_analysis.dimensions.height}` : 'N/A',
        result.quality_analysis?.file_size_mb || 'N/A',
        result.quality_analysis?.recommendations?.join('; ') || ''
      ].map(field => `"${field}"`).join(','))
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `quality_report_${selectedFolder}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-white py-8 px-4">
      <div className="max-w-7xl mx-auto">
        
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-black mb-4 flex items-center justify-center">
            <Camera className="mr-4" />
            🔍 Photo Quality Checker
          </h1>
          <p className="text-gray-600 text-lg">
            Analyze A5 print quality of all photos in database
          </p>
        </div>

        {/* Controls */}
        <div className="bg-white rounded-xl shadow-lg border-2 border-gray-300 p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
            <div>
              <label className="block text-sm font-medium text-black mb-2">📂 Folder to analyze</label>
              <select
                value={selectedFolder}
                onChange={(e) => setSelectedFolder(e.target.value)}
                className="w-full py-2 px-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={scanning}
              >
                {folders.map(folder => (
                  <option key={folder.value} value={folder.value}>
                    {folder.label}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-black mb-2">🎯 Filter by quality</label>
              <select
                value={filterQuality}
                onChange={(e) => setFilterQuality(e.target.value)}
                className="w-full py-2 px-3 border-2 border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {qualityFilters.map(filter => (
                  <option key={filter.value} value={filter.value}>
                    {filter.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-end">
              <button
                onClick={scanPhotos}
                disabled={scanning}
                className={`w-full py-2 px-4 rounded-lg font-medium transition-colors flex items-center justify-center ${
                  scanning 
                    ? 'bg-gray-400 text-white cursor-not-allowed' 
                    : 'bg-blue-500 text-white hover:bg-blue-600'
                }`}
              >
                {scanning ? (
                  <>
                    <Loader className="w-5 h-5 mr-2 animate-spin" />
                    Analysis in progress...
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5 mr-2" />
                    Start analysis
                  </>
                )}
              </button>
            </div>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6 flex items-center">
            <AlertTriangle className="w-5 h-5 mr-2" />
            <span>{error}</span>
          </div>
        )}

        {/* Statistics */}
        {stats.total > 0 && (
          <div className="bg-white rounded-xl shadow-lg border-2 border-gray-300 p-6 mb-8">
            <h2 className="text-2xl font-bold text-black mb-4">📊 Statistics</h2>
            <div className="grid grid-cols-2 md:grid-cols-6 gap-4">
              <div className="bg-gray-100 p-4 rounded-lg text-center">
                <div className="text-2xl font-bold text-black">{stats.total}</div>
                <div className="text-sm text-gray-600">Total</div>
              </div>
              <div className="bg-green-100 p-4 rounded-lg text-center">
                <div className="text-2xl font-bold text-green-600">{stats.excellent}</div>
                <div className="text-sm text-green-700">Excellent</div>
              </div>
              <div className="bg-green-50 p-4 rounded-lg text-center">
                <div className="text-2xl font-bold text-green-500">{stats.good}</div>
                <div className="text-sm text-green-600">Good</div>
              </div>
              <div className="bg-orange-100 p-4 rounded-lg text-center">
                <div className="text-2xl font-bold text-orange-600">{stats.acceptable}</div>
                <div className="text-sm text-orange-700">Acceptable</div>
              </div>
              <div className="bg-red-100 p-4 rounded-lg text-center">
                <div className="text-2xl font-bold text-red-600">{stats.poor}</div>
                <div className="text-sm text-red-700">Insufficient</div>
              </div>
              <div className="bg-gray-100 p-4 rounded-lg text-center">
                <div className="text-2xl font-bold text-gray-600">{stats.error}</div>
                <div className="text-sm text-gray-700">Errors</div>
              </div>
            </div>
          </div>
        )}

        {/* Results */}
        {filteredResults.length > 0 && (
          <div className="bg-white rounded-xl shadow-lg border-2 border-gray-300 overflow-hidden">
            <div className="p-6 border-b border-gray-200 flex justify-between items-center">
              <h2 className="text-2xl font-bold text-black">
                📋 Results ({filteredResults.length})
              </h2>
              <button
                onClick={exportResults}
                className="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 flex items-center"
              >
                <Download className="w-4 h-4 mr-2" />
                Export CSV
              </button>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Photo
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Quality
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      DPI A5
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Resolution
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Size
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {filteredResults.map((result, index) => (
                    <tr key={index} className="hover:bg-gray-50">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-medium text-gray-900">
                          {result.filename}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          {getQualityIcon(result.quality_analysis?.quality_level)}
                          <span className={`ml-2 text-sm font-medium ${
                            result.quality_analysis?.color_code === 'green' ? 'text-green-600' :
                            result.quality_analysis?.color_code === 'lightgreen' ? 'text-green-500' :
                            result.quality_analysis?.color_code === 'orange' ? 'text-orange-600' :
                            result.quality_analysis?.color_code === 'red' ? 'text-red-600' : 'text-gray-600'
                          }`}>
                            {result.quality_analysis?.quality_level || 'error'}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {result.quality_analysis?.equivalent_dpi_a5 || 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {result.quality_analysis?.dimensions ? 
                          `${result.quality_analysis.dimensions.width} × ${result.quality_analysis.dimensions.height}` : 'N/A'}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {result.quality_analysis?.file_size_mb ? `${result.quality_analysis.file_size_mb} MB` : 'N/A'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* No results */}
        {!scanning && results.length === 0 && (
          <div className="text-center py-12">
            <Camera className="h-24 w-24 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-600 mb-2">No analysis performed</h3>
            <p className="text-gray-500">
              Select a folder and click "Start analysis" to begin
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default QualityChecker;