// src/App.jsx
import React, { useState, useContext } from 'react';
import PhotoGrid from './components/PhotoGrid';
import PhotoValidator from './components/PhotoValidator';
import { Navbar } from './components/Navbar';
import Stats from './components/Stats';
import { AdminPage } from './components/AdminPage';
import { UploadPage } from './components/UploadPage';
import ValidationHistory from './components/ValidationHistory';
import ImageSearchEngine from './components/ImageSearchEngine';
import QualityChecker from './components/QualityChecker';
import ValidatedPhotos from './components/ValidatedPhotos';
import PendingPhotos from './components/PendingPhotos';
import BulkPhotoValidation from "./components/BulkPhotoValidation";
import RejectedPhotos from './components/RejectedPhotos';
import MarkedPhotos from './components/MarkedPhotos';
import MyAccount from './components/MyAccount';
import TwoFactorSetup from './components/TwoFactorSetup';
import TOTPSetup from './components/TOTPSetup';
import SecuritySettings from './components/SecuritySettings';
import Login from './components/Login';
import { AuthContext, AuthProvider } from './context/AuthContext';
import { APP_VERSION } from "./version";
import ScheduledPhotos from "./components/ScheduledPhotos";

function AppContent() {
  const { user, loading } = useContext(AuthContext);
  const [view, setView] = useState('stats'); // 'stats', 'validator', 'gallery', 'upload', 'admin', 'history', 'search', 'quality', 'validated', 'pending', 'marked', 'security', 'totp-setup'
  const [showFirstLogin2FA, setShowFirstLogin2FA] = useState(false);

  // Make setView available globally for SecuritySettings
  React.useEffect(() => {
    window.setAppView = setView;
    return () => {
      delete window.setAppView;
    };
  }, []);

  // Check for first-time TOTP setup on page load
  React.useEffect(() => {
    if (window.location.hash === '#totp-first-setup') {
      const setupUsername = localStorage.getItem('setup_username');
      const tempToken = localStorage.getItem('temp_token');
      if (setupUsername && tempToken) {
        setView('totp-first-setup');
        // Clear the hash
        window.history.replaceState(null, null, '/');
      }
    }
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen bg-white flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-black mx-auto mb-4"></div>
          <p className="text-black tracking-wide">Loading...</p>
        </div>
      </div>
    );
  }

  // Special case: first-time TOTP setup doesn't require authenticated user
  if (view === 'totp-first-setup') {
    const setupUsername = localStorage.getItem('setup_username');
    const tempToken = localStorage.getItem('temp_token');
    if (setupUsername && tempToken) {
      return (
        <TOTPSetup
          onComplete={() => {
            // Clear temporary data and redirect to login
            localStorage.removeItem('setup_username');
            localStorage.removeItem('temp_token');
            sessionStorage.removeItem('temp_password');
            window.location.href = '/';
            window.location.reload();
          }}
          onBack={() => {
            // Clear temporary data and redirect to login
            localStorage.removeItem('setup_username');
            localStorage.removeItem('temp_token');
            sessionStorage.removeItem('temp_password');
            window.location.href = '/';
            window.location.reload();
          }}
        />
      );
    }
  }

  if (!user) {
    return <Login />;
  }

  // Check permissions
  const canValidate = user.role === 'validator' || user.role === 'admin';
  const canViewGallery = user.role === 'validator' || user.role === 'admin' || user.role === 'uploader';
  const canUpload = user.role === 'uploader' || user.role === 'admin';
  const canAdmin = user.role === 'admin';

  // Render current view
  const renderContent = () => {
    switch (view) {
      case 'gallery':
        if (!canViewGallery) {
          setView('stats');
          return null;
        }
        return <PhotoGrid />;
      
      case 'upload':
        if (!canUpload) {
          setView('stats');
          return null;
        }
        return <UploadPage />;
      
      case 'admin':
        if (!canAdmin) {
          setView('stats');
          return null;
        }
        return <AdminPage />;
      
      case 'history':
        if (!canAdmin) {
          setView('stats');
          return null;
        }
        return <ValidationHistory />;
      
      case 'search':
        if (!canViewGallery) {
          setView('stats');
          return null;
        }
        return <ImageSearchEngine />;
      
      case 'quality':
        if (!canValidate && !canAdmin) {
          setView('stats');
          return null;
        }
        return <QualityChecker />;
      case "scheduled":
        if (!canUpload) {
          setView("stats");
          return null;
        }
        return <ScheduledPhotos />;
      
      case 'validated':
        if (!canViewGallery) {
          setView('stats');
          return null;
        }
        return <ValidatedPhotos />;
      
      case 'pending':
        if (!canValidate) {
          setView('stats');
          return null;
        }
        return <PendingPhotos />;

      case "bulk-pending":
        if (!canValidate) {
          setView("stats");
          return null;
        }
        return <BulkPhotoValidation />;
      
      case 'rejected':
        if (!canViewGallery) {
          setView('stats');
          return null;
        }
        return <RejectedPhotos />;
      
      case 'marked':
        return <MarkedPhotos />;
      
      case 'account':
        return <MyAccount />;
      
      case 'security':
        return <SecuritySettings />;
      
      case 'totp-setup':
        return (
          <TOTPSetup
            onComplete={() => setView('security')}
            onBack={() => setView('security')}
          />
        );
      
      case 'totp-first-setup':
        return (
          <TOTPSetup
            onComplete={() => {
              // Clear temporary data and redirect to login
              localStorage.removeItem('setup_username');
              localStorage.removeItem('temp_token');
              sessionStorage.removeItem('temp_password');
              window.location.href = '/';
              window.location.reload();
            }}
            onBack={() => {
              // Clear temporary data and redirect to login
              localStorage.removeItem('setup_username');
              localStorage.removeItem('temp_token');
              sessionStorage.removeItem('temp_password');
              window.location.href = '/';
              window.location.reload();
            }}
          />
        );
      
      case 'stats':
      default:
        return <Stats setView={setView} canValidate={canValidate} canViewGallery={canViewGallery} />;
    }
  };

  // Show first-time 2FA setup if needed
  if (showFirstLogin2FA) {
    return (
      <TwoFactorSetup
        onComplete={(method) => {
          if (method === 'totp') {
            setView('totp-setup');
          }
          setShowFirstLogin2FA(false);
        }}
        onSkip={() => setShowFirstLogin2FA(false)}
      />
    );
  }

  return (
    <div className="min-h-screen bg-white">
      <Navbar 
        user={user} 
        view={view} 
        setView={setView}
        canValidate={canValidate}
        canViewGallery={canViewGallery}
        canUpload={canUpload}
        canAdmin={canAdmin}
      />
      
      <main className="min-h-screen bg-white">
        {renderContent()}
      </main>
    </div>
  );
}

function App() {
  // VERSION 2.0 TIMESTAMP: 2025-08-13-08:50 - FORCE RECOMPILE
  console.log("🚀 NEW APP VERSION 2.0 LOADING!");
  return (
    <AuthProvider>
      <AppContent />
	   <footer style={{
        textAlign: "center",
        fontSize: "0.85rem",
        color: "#666",
        padding: "10px 0",
        borderTop: "1px solid #eee",
        backgroundColor: "#fafafa"
      }}>
        Build version: {APP_VERSION}
      </footer>
    </AuthProvider>
  );
}

export default App;
