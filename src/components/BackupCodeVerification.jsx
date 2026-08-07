import React, { useState } from 'react';
import { Key, ArrowLeft, AlertCircle, Loader } from 'lucide-react';

const BackupCodeVerification = ({ username, onSuccess, onBack }) => {
  const [backupCode, setBackupCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!backupCode || backupCode.length < 8) {
      setError('Please enter a valid backup code');
      return;
    }

    setIsSubmitting(true);
    setError('');

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
          username, 
          password: sessionStorage.getItem('temp_password'),
          twofa_code: backupCode // Les codes de sauvegarde utilisent le même champ
        }),
      });

      const data = await response.json();

      if (data.success && data.token) {
        // Clear temporary password
        sessionStorage.removeItem('temp_password');
        
        localStorage.setItem('token', data.token);
        localStorage.setItem('user', JSON.stringify({
          username: data.username,
          role: data.role
        }));
        
        onSuccess();
      } else {
        setError(data.error || 'Backup code invalid or already used');
      }
    } catch (error) {
	setError('Connection error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCodeChange = (e) => {
    let value = e.target.value.toUpperCase().replace(/[^A-Z0-9-]/g, '');
    
    // Auto-format with dash (XXXX-XXXX)
    if (value.length > 4 && !value.includes('-')) {
      value = value.slice(0, 4) + '-' + value.slice(4, 8);
    }
    
    setBackupCode(value);
    setError('');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="flex items-center mb-6">
            <button
              onClick={onBack}
              className="flex items-center text-gray-600 hover:text-gray-900 transition-colors"
            >
              <ArrowLeft className="h-5 w-5 mr-1" />
              Back
            </button>
          </div>
          
          <div className="text-center">
            <Key className="mx-auto h-16 w-16 text-indigo-600" />
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
              Backup Code
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              Enter one of your backup codes for <strong>{username}</strong>
            </p>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4">
            <div className="flex">
              <AlertCircle className="h-5 w-5 text-red-400 mr-2 flex-shrink-0" />
              <div className="text-sm text-red-700">{error}</div>
            </div>
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit}>
          <div>
            <label htmlFor="backup-code" className="block text-sm font-medium text-gray-700 mb-2">
              Backup Code
            </label>
            <input
              id="backup-code"
              type="text"
              placeholder="XXXX-XXXX"
              maxLength="9"
              value={backupCode}
              onChange={handleCodeChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-md text-center text-xl font-mono tracking-wider focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              disabled={isSubmitting}
              autoComplete="one-time-code"
              autoFocus
            />
            <p className="mt-1 text-xs text-gray-500">
              Format: XXXX-XXXX (e.g. A1B2-C3D4)
            </p>
          </div>

          <div>
            <button
              type="submit"
              disabled={isSubmitting || backupCode.length < 8}
              className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isSubmitting ? (
                <>
                  <Loader className="animate-spin -ml-1 mr-3 h-5 w-5" />
                  Verifying...
                </>
              ) : (
                'Log in'
              )}
            </button>
          </div>
        </form>

        {/* Warnings */}
        <div className="space-y-4">
          <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-md">
            <div className="flex">
              <AlertCircle className="h-5 w-5 text-yellow-400 mr-2 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-yellow-700">
                <strong>Important:</strong> Each backup code can only be used once.
                Once used, it will no longer be valid.
              </div>
            </div>
          </div>

          <div className="p-4 bg-blue-50 border border-blue-200 rounded-md">
            <div className="text-sm text-blue-700">
              <strong>Lost backup codes?</strong>
              <p className="mt-1">
                Contact the system administrator to reset your two-factor authentication.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default BackupCodeVerification;
