import React, { useState } from 'react';
import { Shield, Mail, Smartphone, ArrowRight, AlertCircle } from 'lucide-react';

const TwoFactorSetup = ({ onComplete, onSkip }) => {
  const [selectedMethod, setSelectedMethod] = useState('totp');

  const handleContinue = () => {
    // Only TOTP is available now
    onComplete('totp');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <Shield className="mx-auto h-16 w-16 text-indigo-600" />
          <h2 className="mt-6 text-3xl font-extrabold text-gray-900">
            Secure your account
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Set up two-factor authentication to protect your account
          </p>
        </div>

        <div className="space-y-4">
          {/* TOTP Option Mandatory */}
          <div className="relative border-2 rounded-lg p-4 border-indigo-500 bg-indigo-50">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                <input
                  type="radio"
                  className="mt-1 h-4 w-4 text-indigo-600 border-gray-300 focus:ring-indigo-500"
                  checked={true}
                  readOnly
                />
              </div>
              <div className="ml-3 flex-1">
                <div className="flex items-center">
                  <Smartphone className="h-5 w-5 text-indigo-600 mr-2" />
                  <h3 className="text-lg font-medium text-gray-900">
                    Authenticator Application
                  </h3>
                  <span className="ml-2 inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                    Mandatory
                  </span>
                </div>
                <p className="mt-1 text-sm text-gray-600">
                  Use Google Authenticator, Microsoft Authenticator or another TOTP app
                </p>
                <div className="mt-2 text-xs text-gray-500">
                  ✓ More secure • ✓ Works offline • ✓ Temporary codes
                </div>
              </div>
            </div>
          </div>

          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
            <div className="flex">
              <AlertCircle className="h-5 w-5 text-yellow-400 mr-2 flex-shrink-0 mt-0.5" />
              <div className="text-sm text-yellow-700">
                <strong>New security policy:</strong> TOTP authentication is now mandatory for all users. Email authentication has been disabled for security reasons.
              </div>
            </div>
          </div>
        </div>

        {/* Action buttons */}
        <div className="space-y-3">
          <button
            onClick={handleContinue}
            className="group relative w-full flex justify-center py-3 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
          >
            Continue
            <ArrowRight className="ml-2 h-4 w-4" />
          </button>

        </div>

      </div>
    </div>
  );
};

export default TwoFactorSetup;