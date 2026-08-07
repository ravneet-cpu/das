import React, { useState, useEffect } from 'react';
import { 
  Shield, 
  Smartphone, 
  Mail, 
  RotateCcw, 
  Download, 
  AlertCircle, 
  CheckCircle,
  Settings
} from 'lucide-react';

// Function to trigger navigation to TOTP setup
const navigateToTOTPSetup = () => {
  if (window.setAppView) {
    window.setAppView('totp-setup');
  }
};

const SecuritySettings = () => {
  const [totpStatus, setTotpStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState('');

  // Load TOTP status
  const loadTOTPStatus = async () => {
    try {
      const response = await fetch('/api/auth/totp/status', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      const data = await response.json();
      
      if (response.ok) {
        setTotpStatus(data);
      } else {
	setError(data.error || 'Error loading status');
      }
    } catch (err) {
	setError('Connection error');
    } finally {
      setLoading(false);
    }
  };

  // Regenerate backup codes (new TOTP configuration)
  const regenerateBackupCodes = async () => {
    setActionLoading(true);
    setError('');
    
    try {
      const response = await fetch('/api/auth/totp/setup', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        }
      });
      
      const data = await response.json();
      
      if (data.success) {
        // Automatically download new codes
        downloadBackupCodes(data.backup_codes);
        await loadTOTPStatus(); // Reload status
      } else {
	setError(data.error || 'Error during regeneration');
      }
    } catch (err) {
	 setError('Connection error');
    } finally {
      setActionLoading(false);
    }
  };


  const downloadBackupCodes = (codes) => {
    const content = `2FA BACKUP CODES - Photo Validator

IMPORTANT: Keep these codes in a safe place. Each code can only be used once.

${codes.map((code, i) => `${i + 1}. ${code}`).join('\n')}

Generated on: ${new Date().toLocaleDateString('en-US')} at ${new Date().toLocaleTimeString('en-US')}`;

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'photo-validator-backup-codes.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  useEffect(() => {
    loadTOTPStatus();
  }, []);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-1/3"></div>
          <div className="h-32 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-8">
      {/* Header */}
      <div className="flex items-center space-x-3">
        <Settings className="h-8 w-8 text-gray-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Security Settings</h1>
          <p className="text-gray-600">Manage your two-factor authentication</p>
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

      {/* Current 2FA Status */}
      <div className="bg-white border border-gray-200 rounded-lg p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-4">
            <div className={`p-3 rounded-full ${totpStatus?.totp_enabled ? 'bg-green-100' : 'bg-gray-100'}`}>
              <Shield className={`h-6 w-6 ${totpStatus?.totp_enabled ? 'text-green-600' : 'text-gray-600'}`} />
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900">
		 Two-Factor Authentication
              </h3>
              <p className="text-sm text-gray-600 mt-1">
                {totpStatus?.totp_enabled
                  ? 'Your account is protected by TOTP authentication'
                  : 'Your account is not protected by TOTP authentication'}
              </p>
              <div className="flex items-center mt-2">
                {totpStatus?.totp_enabled ? (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                    <CheckCircle className="h-3 w-3 mr-1" />
                    Enabled
                  </span>
                ) : (
                  <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                    <AlertCircle className="h-3 w-3 mr-1" />
			Disabled
                  </span>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* TOTP Actions */}
      {totpStatus?.totp_enabled ? (
        <div className="space-y-6">
          {/* Regenerate backup codes */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-4">
                <div className="p-3 rounded-full bg-blue-100">
                  <RotateCcw className="h-6 w-6 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    Backup Codes
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    Regenerate your backup codes if you have lost them
                  </p>
                </div>
              </div>
              <button
                onClick={regenerateBackupCodes}
                disabled={actionLoading}
                className="flex items-center px-4 py-2 border border-blue-300 text-sm font-medium rounded-md text-blue-700 bg-blue-50 hover:bg-blue-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-colors"
              >
                <Download className="h-4 w-4 mr-2" />
                {actionLoading ? 'Generating...' : 'Regenerate'}
              </button>
            </div>
          </div>

          {/* Security Policy Information */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-4">
                <div className="p-3 rounded-full bg-gray-100">
                  <AlertCircle className="h-6 w-6 text-gray-600" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    Security Policy
                  </h3>
                  <p className="text-sm text-gray-600 mt-1">
                    TOTP authentication is mandatory and cannot be disabled for security reasons
                  </p>
                  <p className="text-xs text-gray-500 mt-2">
                    Contact your system administrator if you encounter problems with your authenticator
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : (
        /* Configure TOTP */
        <div className="bg-white border border-gray-200 rounded-lg p-6">
          <div className="flex items-center space-x-4 mb-4">
            <div className="p-3 rounded-full bg-indigo-100">
              <Smartphone className="h-6 w-6 text-indigo-600" />
            </div>
            <div>
              <h3 className="text-lg font-medium text-gray-900">
		Configure TOTP Authentication
              </h3>
              <p className="text-sm text-gray-600 mt-1">
		Use an app like Google Authenticator to secure your account
              </p>
            </div>
          </div>
          
          <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-4">
            <div className="flex">
              <AlertCircle className="h-5 w-5 text-yellow-400 mr-2 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-yellow-700">
                <strong>Recommended:</strong> TOTP authentication is more secure than email and works offline.
              </div>
            </div>
          </div>

          <button
            onClick={navigateToTOTPSetup}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          >
            <Smartphone className="h-4 w-4 mr-2" />
		Configure TOTP
          </button>
        </div>
      )}

      {/* Additional Information */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
        <h4 className="text-lg font-medium text-blue-900 mb-3">
          About Two-Factor Authentication
        </h4>
        <div className="space-y-2 text-sm text-blue-800">
          <p>• <strong>TOTP (recommended):</strong> Use Google Authenticator, Microsoft Authenticator, or another compatible app</p>
          <p>• <strong>Backup codes:</strong> Keep them in a safe place to access your account if you lose your phone</p>
          <p>• <strong>Security:</strong> 2FA protects your account even if your password is compromised</p>
        </div>
      </div>
    </div>
  );
};

export default SecuritySettings;
