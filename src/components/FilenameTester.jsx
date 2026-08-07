// src/components/FilenameTester.jsx
import React, { useState } from 'react';

const FilenameTester = () => {
  const [filename, setFilename] = useState('');
  const [testResults, setTestResults] = useState(null);
  const [loadStatus, setLoadStatus] = useState(null);
  const [validateStatus, setValidateStatus] = useState(null);
  const [authToken, setAuthToken] = useState(localStorage.getItem('token') || '');
  
  const API_BASE_URL = 'http://185.133.250.8:5000';
  
  const testFilename = async () => {
    if (!filename) return;
    
    // Reset statuses
    setTestResults(null);
    setLoadStatus(null);
    setValidateStatus(null);
    
    // Store token
    if (authToken) {
      localStorage.setItem('token', authToken);
    }
    
    // Create test results
    const results = {
      original: filename,
      encoded: encodeURIComponent(filename),
      doubleEncoded: encodeURIComponent(encodeURIComponent(filename)),
      urlEncoded: encodeURI(filename),
      rawEncoded: filename.replace(/ /g, '%20')
    };
    
    setTestResults(results);
    
    // Test loading image with different encodings
    const encodings = [
      { name: 'Original', value: filename },
      { name: 'Encoded', value: encodeURIComponent(filename) },
      { name: 'Double Encoded', value: encodeURIComponent(encodeURIComponent(filename)) },
      { name: 'URL Encoded', value: encodeURI(filename) },
      { name: 'Raw Encoded', value: filename.replace(/ /g, '%20') }
    ];
    
    const loadResults = {};
    
    for (const encoding of encodings) {
      try {
        const url = `${API_BASE_URL}/api/photos/${encoding.value}`;
        
        const response = await fetch(url, {
          headers: {
            'Authorization': `Bearer ${authToken}`
          }
        });
        
        loadResults[encoding.name] = {
          status: response.status,
          statusText: response.statusText,
          success: response.ok
        };
      } catch (error) {
        loadResults[encoding.name] = {
          status: 0,
          statusText: error.message,
          success: false
        };
      }
    }
    
    setLoadStatus(loadResults);
    
    // Test validation with different encodings
    const validateResults = {};
    
    for (const encoding of encodings) {
      try {
        const url = `${API_BASE_URL}/api/photos/validate`;
        
        const payload = {
          photoId: encoding.value,
          decision: 'valider'
        };
        
        const response = await fetch(url, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${authToken}`
          },
          body: JSON.stringify(payload)
        });
        
        // Try to get response text
        let responseText = '';
        try {
          responseText = await response.text();
        } catch (e) {}
        
        validateResults[encoding.name] = {
          status: response.status,
          statusText: response.statusText,
          success: response.ok,
          response: responseText.substring(0, 100) // First 100 chars
        };
      } catch (error) {
        validateResults[encoding.name] = {
          status: 0,
          statusText: error.message,
          success: false
        };
      }
    }
    
    setValidateStatus(validateResults);
  };
  
  return (
    <div className="bg-white shadow-lg rounded-lg p-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-4">Filename Tester</h2>
      
      <div className="mb-4">
        <label className="block text-gray-700 mb-2 font-medium">Auth Token:</label>
        <input
          type="text"
          value={authToken}
          onChange={(e) => setAuthToken(e.target.value)}
          className="border rounded px-3 py-2 w-full"
          placeholder="Enter your auth token"
        />
      </div>
      
      <div className="mb-4">
        <label className="block text-gray-700 mb-2 font-medium">Filename to Test:</label>
        <div className="flex">
          <input
            type="text"
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            className="border rounded-l px-3 py-2 flex-1"
            placeholder="Enter filename with special characters or spaces"
          />
          <button
            onClick={testFilename}
            className="bg-blue-500 hover:bg-blue-600 text-white font-medium py-2 px-4 rounded-r"
          >
            Test
          </button>
        </div>
      </div>
      
      {testResults && (
        <div className="mb-4">
          <h3 className="font-semibold text-lg mb-2">Encoding Results:</h3>
          <div className="bg-gray-50 p-4 rounded space-y-2 text-sm">
            <div><span className="font-medium">Original:</span> {testResults.original}</div>
            <div><span className="font-medium">encodeURIComponent:</span> {testResults.encoded}</div>
            <div><span className="font-medium">Double encoded:</span> {testResults.doubleEncoded}</div>
            <div><span className="font-medium">encodeURI:</span> {testResults.urlEncoded}</div>
            <div><span className="font-medium">Raw encoded:</span> {testResults.rawEncoded}</div>
          </div>
        </div>
      )}
      
      {loadStatus && (
        <div className="mb-4">
          <h3 className="font-semibold text-lg mb-2">Image Load Tests:</h3>
          <div className="bg-gray-50 p-4 rounded">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Encoding</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Result</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {Object.entries(loadStatus).map(([key, value]) => (
                  <tr key={key}>
                    <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{key}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500">{value.status} {value.statusText}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${value.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {value.success ? 'Success' : 'Failed'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      
      {validateStatus && (
        <div className="mb-4">
          <h3 className="font-semibold text-lg mb-2">Validation Tests:</h3>
          <div className="bg-gray-50 p-4 rounded">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Encoding</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Result</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Response</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {Object.entries(validateStatus).map(([key, value]) => (
                  <tr key={key}>
                    <td className="px-3 py-2 whitespace-nowrap text-sm font-medium text-gray-900">{key}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-500">{value.status} {value.statusText}</td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm">
                      <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${value.success ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
                        {value.success ? 'Success' : 'Failed'}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-sm text-gray-500 truncate max-w-xs">{value.response}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
      
      {/* Test image display */}
      {filename && (
        <div>
          <h3 className="font-semibold text-lg mb-2">Image Test:</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {testResults && [
              { label: 'Original', url: `${API_BASE_URL}/api/photos/${testResults.original}` },
              { label: 'Encoded', url: `${API_BASE_URL}/api/photos/${testResults.encoded}` }
            ].map(test => (
              <div key={test.label} className="border rounded overflow-hidden">
                <div className="bg-gray-100 p-2 border-b">
                  <h4 className="font-medium text-sm">{test.label}</h4>
                </div>
                <div className="p-2 bg-gray-800 flex items-center justify-center" style={{ minHeight: '200px' }}>
                  <img 
                    src={test.url}
                    alt={`${test.label} test`}
                    className="max-w-full max-h-48 object-contain"
                    onError={(e) => {
                      console.error(`Error loading ${test.label} image:`, e);
                      e.target.src = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48cmVjdCB3aWR0aD0iMjAwIiBoZWlnaHQ9IjIwMCIgZmlsbD0iI2VlZWVlZSIvPjx0ZXh0IHg9IjEwMCIgeT0iMTAwIiBmb250LWZhbWlseT0iQXJpYWwiIGZvbnQtc2l6ZT0iMTYiIHRleHQtYW5jaG9yPSJtaWRkbGUiIGRvbWluYW50LWJhc2VsaW5lPSJtaWRkbGUiPkxvYWQgRXJyb3I8L3RleHQ+PC9zdmc+';
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default FilenameTester;
