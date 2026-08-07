import React, { useState } from 'react';
import { Smartphone, ArrowLeft, AlertCircle, Loader } from 'lucide-react';

const TOTPVerification = ({ username, onSuccess, onBack, onUseBackupCode }) => {
  const [code, setCode] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showBackupCodeOption, setShowBackupCodeOption] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!code || code.length !== 6) {
      setError('Please enter a 6-digit code');
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
          password: sessionStorage.getItem('temp_password'), // Password stored temporarily
          twofa_code: code 
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
	setError(data.error || 'Invalid code');
      }
    } catch (error) {
	setError('Connection error. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCodeChange = (e) => {
    const value = e.target.value.replace(/\D/g, '').slice(0, 6);
    setCode(value);
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
            <Smartphone className="mx-auto h-16 w-16 text-indigo-600" />
            <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
              Authentication Code
            </h2>
            <p className="mt-2 text-sm text-gray-600">
              Open your authenticator app and enter the 6-digit code for <strong>{username}</strong>
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
            <label htmlFor="totp-code" className="block text-sm font-medium text-gray-700 mb-2">
              Verification Code
            </label>
            <input
              id="totp-code"
              type="text"
              placeholder="000000"
              maxLength="6"
              value={code}
              onChange={handleCodeChange}
              className="w-full px-4 py-3 border border-gray-300 rounded-md text-center text-2xl font-mono tracking-wider focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              disabled={isSubmitting}
              autoComplete="one-time-code"
              autoFocus
            />
            <p className="mt-1 text-xs text-gray-500">
              Enter the code displayed in your authenticator app
            </p>
          </div>

          <div>
            <button
              type="submit"
              disabled={isSubmitting || code.length !== 6}
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

          {/* Alternative options */}
          <div className="text-center space-y-2">
            {!showBackupCodeOption ? (
              <button
                type="button"
                onClick={() => setShowBackupCodeOption(true)}
                className="text-sm text-indigo-600 hover:text-indigo-500 underline"
              >
                I lost my phone
              </button>
            ) : (
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={onUseBackupCode}
                  className="text-sm text-indigo-600 hover:text-indigo-500 underline"
                >
                  Use a backup code
                </button>
                <button
                  type="button"
                  onClick={() => setShowBackupCodeOption(false)}
                  className="block mx-auto text-xs text-gray-500 hover:text-gray-700"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </form>

        {/* Help */}
        <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-md">
          <div className="text-sm text-blue-700">
            <strong>Need help?</strong>
            <ul className="mt-2 space-y-1 text-xs">
              <li>• Make sure your phone's time is correct</li>
              <li>• The code changes every 30 seconds</li>
              <li>• Use a backup code if you no longer have access to the app</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TOTPVerification;
