import React, { useState, useContext } from 'react';
import { LogIn, AlertCircle, Loader, Palette, Mail, Shield } from 'lucide-react';
import { AuthContext } from '../context/AuthContext';
import TOTPVerification from './TOTPVerification';
import BackupCodeVerification from './BackupCodeVerification';

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [twoFACode, setTwoFACode] = useState('');
  const [loginError, setLoginError] = useState('');
  const [showTwoFA, setShowTwoFA] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [twoFAMethod, setTwoFAMethod] = useState(''); // 'email' or 'totp'
  const [showBackupCode, setShowBackupCode] = useState(false);
  
  const { login, error, loading } = useContext(AuthContext);
  
  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoginError('');
    
    if (isSubmitting) {
      console.log('[LOGIN DEBUG] Already submitting, ignoring');
      return;
    }
    
    setIsSubmitting(true);
    
    if (!showTwoFA) {
      // First step: username/password
      if (!username || !password) {
        setLoginError('Please enter username and password');
        setIsSubmitting(false);
        return;
      }
      
      try {
        console.log('[LOGIN DEBUG] Step 1 - Sending username/password');
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ username, password }),
        });
        
        const data = await response.json();
        console.log('[LOGIN DEBUG] Step 1 response:', data);
        
        if (data.requires_totp_setup) {
          // User needs to configure TOTP first - redirect to setup
          localStorage.setItem('temp_token', data.temp_token || '');
          localStorage.setItem('setup_username', username);
          sessionStorage.setItem('temp_password', password);
          // Trigger TOTP setup flow
          window.location.href = '/#totp-first-setup';
          window.location.reload();
        } else if (data.requires_2fa) {
          setShowTwoFA(true);
          setTwoFAMethod(data.twofa_method || 'totp'); // Default to TOTP
          // For TOTP, store password temporarily
          sessionStorage.setItem('temp_password', password);
          setLoginError('');
        } else if (data.success && data.token) {
          // Direct login without 2FA
          localStorage.setItem('token', data.token);
          localStorage.setItem('user', JSON.stringify({
            username: data.username,
            role: data.role
          }));
          // Force reload to trigger AuthContext to pick up the new token
          window.location.reload();
        } else {
          setLoginError(data.error || 'Authentication failed');
        }
      } catch (error) {
        setLoginError('Network error. Please try again.');
      } finally {
        setIsSubmitting(false);
      }
    } else {
      // Second step: 2FA code
      if (!twoFACode) {
        setLoginError('Please enter the verification code');
        setIsSubmitting(false);
        return;
      }
      
      try {
        console.log('[LOGIN DEBUG] Step 2 - Sending 2FA code:', twoFACode);
        const response = await fetch('/api/auth/login', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ username, password, twofa_code: twoFACode }),
        });
        
        const data = await response.json();
        console.log('[LOGIN DEBUG] Step 2 response:', data);
        
        if (data.success && data.token) {
          // Login successful, update AuthContext directly without calling API again
          localStorage.setItem('token', data.token);
          localStorage.setItem('user', JSON.stringify({
            username: data.username,
            role: data.role
          }));
          // Force reload to trigger AuthContext to pick up the new token
          window.location.reload();
        } else {
          setLoginError(data.error || 'Invalid verification code');
        }
      } catch (error) {
        setLoginError('Network error. Please try again.');
      } finally {
        setIsSubmitting(false);
      }
    }
  };

  const handleTOTPSuccess = () => {
    window.location.reload();
  };

  const handleBackToLogin = () => {
    setShowTwoFA(false);
    setShowBackupCode(false);
    setTwoFACode('');
    setLoginError('');
    sessionStorage.removeItem('temp_password');
  };

  const handleUseBackupCode = () => {
    setShowBackupCode(true);
  };
  
  const handleResend2FA = async () => {
    try {
      console.log('[LOGIN DEBUG] Resending 2FA code for:', username);
      const response = await fetch('/api/auth/resend-2fa', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username }),
      });
      
      const data = await response.json();
      console.log('[LOGIN DEBUG] Resend response:', data);
      if (data.success) {
        setLoginError('New verification code sent!');
        setTimeout(() => setLoginError(''), 3000);
      } else {
        setLoginError(data.error || 'Failed to resend code');
      }
    } catch (error) {
      setLoginError('Network error. Please try again.');
    }
  };
  
  // If showing TOTP verification
  if (showTwoFA && twoFAMethod === 'totp' && !showBackupCode) {
    return (
      <TOTPVerification
        username={username}
        onSuccess={handleTOTPSuccess}
        onBack={handleBackToLogin}
        onUseBackupCode={handleUseBackupCode}
      />
    );
  }

  // If showing backup code verification
  if (showTwoFA && showBackupCode) {
    return (
      <BackupCodeVerification
        username={username}
        onSuccess={handleTOTPSuccess}
        onBack={() => setShowBackupCode(false)}
      />
    );
  }

  return (
    <div className="min-h-screen bg-white flex items-center justify-center px-4">
      <div className="bg-white border-2 border-gray-300 rounded-lg shadow-lg p-12 w-full max-w-lg">
        <div className="flex justify-center mb-8">
          <div className="w-20 h-20 bg-white border-2 border-gray-400 rounded flex items-center justify-center">
            <Palette className="w-10 h-10 text-black" />
          </div>
        </div>
        
        <h1 className="text-4xl font-elegant text-center mb-2 text-black">OperaGallery</h1>
        <h2 className="text-lg font-body text-center mb-8 text-secondary">Collection Management System</h2>
        
        {(loginError || error) && (
          <div className="bg-white border-2 border-red-500 text-black px-4 py-3 mb-6 flex items-center rounded">
            <AlertCircle className="w-5 h-5 mr-3" />
            <span className="text-sm">{loginError || error}</span>
          </div>
        )}
        
        <form onSubmit={handleSubmit} className="space-y-6">
          {!showTwoFA ? (
            <>
              <div>
                <label htmlFor="username" className="block text-primary font-body font-semibold mb-3 tracking-wide">
                  USERNAME
                </label>
                <input
                  type="text"
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="input-elegant"
                  disabled={loading}
                  placeholder="Enter your username"
                />
              </div>
              
              <div>
                <label htmlFor="password" className="block text-primary font-body font-semibold mb-3 tracking-wide">
                  PASSWORD
                </label>
                <input
                  type="password"
                  id="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-elegant"
                  disabled={loading}
                  placeholder="Enter your password"
                />
              </div>
            </>
          ) : null}
          
          {!showTwoFA && (
            <button
              type="submit"
              disabled={loading || isSubmitting}
              className="w-full btn-primary mt-8 font-elegant text-lg tracking-wide"
            >
              {(loading || isSubmitting) ? (
                <div className="flex items-center justify-center">
                  <Loader className="w-5 h-5 mr-3 animate-spin" />
                  <span className="font-body">
                    Authenticating...
                  </span>
                </div>
              ) : (
                'Access Collection'
              )}
            </button>
          )}
          
        </form>
        
        <div className="mt-8 pt-8 border-t-2 border-gray-300">
          <p className="text-gray-500 text-center text-sm font-body">
            Secure access to the OperaGallery collection management system.<br/>
            Please contact your administrator for access credentials.
          </p>
        </div>
      </div>
    </div>
  );
};

export default Login;