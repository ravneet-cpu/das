import React, { useState } from 'react';
import { LogOut, User, BarChart3, CheckCircle, Image, Settings, Upload, Clock, Palette, Search, Camera, Menu, X, ThumbsUp, ThumbsDown, Grid, Star, Shield, ListChecks, Download, Trash2, ChevronDown } from 'lucide-react';

function downloadFMLog() {
  const token = localStorage.getItem('token');
  window.location.href = `/api/fm-push-log/download?token=${encodeURIComponent(token)}`;
}

async function resetFMLog() {
  if (!confirm('Archive and clear the FM log? Do this after sending the CSV to FileMaker.')) return;
  const token = localStorage.getItem('token');
  const res = await fetch('/api/fm-push-log/reset', { method: 'POST', headers: { Authorization: `Bearer ${token}` } });
  const d = await res.json();
  alert(d.success ? `Archived as ${d.archived_to}. Log is now empty.` : (d.message || d.error));
}

export const Navbar = ({ user, view, setView, canValidate, canViewGallery, canUpload, canAdmin }) => {
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [photosOpen, setPhotosOpen] = useState(false);
  const [moreOpen, setMoreOpen] = useState(false);

  const handleLogout = () => {
    localStorage.removeItem('token');
    window.location.reload();
  };

  const primaryItems = [
    { key: 'stats', label: 'Overview', icon: BarChart3, show: true },
    { key: 'upload', label: 'Upload', icon: Upload, show: canUpload },
  ];

  const photosItems = [
    { key: 'pending', label: 'Pending', icon: Grid, show: canValidate },
    { key: 'bulk-pending', label: 'Bulk Validate', icon: ListChecks, show: canValidate },
    { key: 'scheduled', label: 'Scheduled', icon: Clock, show: canUpload },
    { key: 'validated', label: 'Validated', icon: ThumbsUp, show: canViewGallery },
    { key: 'rejected', label: 'Rejected', icon: ThumbsDown, show: canViewGallery },
  ];

  const moreItems = [
    { key: 'search', label: 'Search', icon: Search, show: canViewGallery },
    { key: 'admin', label: 'Admin', icon: Settings, show: canAdmin },
  ];

  const showPhotos = photosItems.some(i => i.show);
  const showMore = moreItems.some(i => i.show);

  const DropdownBtn = ({ label, icon: Icon, open, onClick, count }) => (
    <button onClick={onClick}
      className={`inline-flex items-center gap-1 px-2.5 py-1.5 text-[11px] font-semibold border-2 rounded transition ${open ? 'bg-gray-200 border-gray-400' : 'border-transparent hover:bg-gray-100 hover:border-gray-300'}`}>
      <Icon className="h-3.5 w-3.5" />{label}{count ? ` (${count})` : ''}
      <ChevronDown className={`h-3 w-3 transition ${open ? 'rotate-180' : ''}`} />
    </button>
  );

  return (
    <nav className="bg-white border-b-2 border-gray-300 sticky top-2 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex justify-between items-center h-20 gap-3 lg:gap-4">
          
          {/* Logo */}
          <div className="flex items-center shrink-0">
            <div className="flex items-center">
              <Palette className="h-8 w-8 text-black mr-3" />
              <div>
                <h1 className="text-xl font-bold text-black">
                  GALLERY
                </h1>
                <p className="text-xs text-black tracking-widest">
                  VALIDATION SYSTEM
                </p>
              </div>
            </div>
          </div>

          {/* Navigation Menu */}
           <div className="hidden lg:flex flex-1 min-w-0 items-center justify-center">
             <div className="flex items-center gap-1 whitespace-nowrap px-1">
              {/* Primary items */}
              {primaryItems.filter(i => i.show).map((item) => {
                const Icon = item.icon;
                return (
                  <button key={item.key} onClick={() => setView(item.key)}
                    className={`inline-flex items-center gap-1 px-2.5 py-1.5 text-[11px] font-semibold border-2 rounded transition ${view === item.key ? 'bg-gray-200 border-gray-400' : 'border-transparent hover:bg-gray-100 hover:border-gray-300'}`}>
                    <Icon className="h-3.5 w-3.5" /><span>{item.label}</span>
                  </button>
                );
              })}
              {/* Photos dropdown */}
              {showPhotos && (
                <div className="relative">
                  <DropdownBtn label="Photos" icon={Camera} open={photosOpen} onClick={() => { setPhotosOpen(!photosOpen); setMoreOpen(false); }}
                    count={photosItems.filter(i => i.show).length} />
                  {photosOpen && (
                    <div className="absolute top-full left-0 mt-1 bg-white border-2 border-gray-300 rounded-lg shadow-lg z-50 min-w-[160px] py-1">
                      {photosItems.filter(i => i.show).map(item => (
                        <button key={item.key} onClick={() => { setView(item.key); setPhotosOpen(false); }}
                          className={`w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 hover:bg-gray-100 ${view === item.key ? 'bg-blue-50 font-bold' : ''}`}>
                          <item.icon className="h-3.5 w-3.5" />{item.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
              {/* More dropdown */}
              {showMore && (
                <div className="relative">
                  <DropdownBtn label="More" icon={Menu} open={moreOpen} onClick={() => { setMoreOpen(!moreOpen); setPhotosOpen(false); }} />
                  {moreOpen && (
                    <div className="absolute top-full left-0 mt-1 bg-white border-2 border-gray-300 rounded-lg shadow-lg z-50 min-w-[140px] py-1">
                      {moreItems.filter(i => i.show).map(item => (
                        <button key={item.key} onClick={() => { setView(item.key); setMoreOpen(false); }}
                          className={`w-full text-left px-3 py-1.5 text-xs flex items-center gap-2 hover:bg-gray-100 ${view === item.key ? 'bg-blue-50 font-bold' : ''}`}>
                          <item.icon className="h-3.5 w-3.5" />{item.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* FM Export */}
          <div className="hidden lg:flex items-center gap-1 shrink-0">
            <button onClick={downloadFMLog} title="Download FM push log CSV"
              className="flex items-center gap-1 px-3 py-2 bg-white border-2 border-gray-400 text-black text-xs hover:bg-gray-100 rounded">
              <Download className="h-4 w-4" /> Export FM
            </button>
          </div>

          {/* User Menu */}
          <div className="hidden lg:block relative shrink-0">
            <div>
              <button
                onClick={() => setUserMenuOpen(!userMenuOpen)}
                className="flex items-center px-4 py-2 bg-white border-2 border-gray-400 text-black text-sm transition-all duration-300 hover:bg-gray-100 rounded"
              >
                <User className="h-5 w-5 text-black mr-3" />
                <span className="font-medium tracking-wide">{user?.username?.toUpperCase()}</span>
              </button>
            </div>

            {userMenuOpen && (
              <div className="origin-top-right absolute right-0 mt-2 w-56 bg-white border-2 border-gray-400 rounded-lg shadow-lg z-50">
                <div className="py-2">
                  <div className="px-4 py-3 border-b-2 border-gray-300">
                    <div className="text-black font-medium tracking-wide">{user?.username?.toUpperCase()}</div>
                    <div className="text-black text-xs tracking-wider uppercase">
                      {user?.role}
                    </div>
                  </div>
                  
                  <button
                    onClick={() => setView('account')}
                    className="flex items-center w-full px-4 py-3 text-sm text-black hover:text-black hover:bg-gray-100 transition-all duration-300"
                  >
                    <User className="h-4 w-4 mr-3" />
                    MY ACCOUNT
                  </button>
                  
                  <button
                    onClick={() => setView('marked')}
                    className="flex items-center w-full px-4 py-3 text-sm text-black hover:text-black hover:bg-gray-100 transition-all duration-300"
                  >
                    <Star className="h-4 w-4 mr-3" />
                    MARKED PHOTOS
                  </button>
                  
                  <button
                    onClick={() => {
                      setView('security');
                      setUserMenuOpen(false);
                    }}
                    className="flex items-center w-full px-4 py-3 text-sm text-black hover:text-black hover:bg-gray-100 transition-all duration-300"
                  >
                    <Shield className="h-4 w-4 mr-3" />
                    SECURITY
                  </button>
                  
                  <button
                    onClick={handleLogout}
                    className="flex items-center w-full px-4 py-3 text-sm text-black hover:text-black hover:bg-gray-100 transition-all duration-300"
                  >
                    <LogOut className="h-4 w-4 mr-3" />
                    SIGN OUT
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Mobile menu button */}
           <div className="lg:hidden flex items-center space-x-2 shrink-0">
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="bg-white border-2 border-gray-400 p-3 text-black hover:bg-gray-100 transition-all duration-300 rounded"
            >
              {mobileMenuOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
            </button>
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="bg-white border-2 border-gray-400 p-3 text-black hover:bg-gray-100 transition-all duration-300 rounded"
            >
              <User className="h-6 w-6" />
            </button>
          </div>
        </div>

        {/* Mobile Navigation */}
        {mobileMenuOpen && (
          <div className="lg:hidden">
            <div className="px-2 pt-2 pb-4 space-y-1 border-t-2 border-gray-300 bg-white">
              {menuItems.filter(item => item.show).map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.key}
                    onClick={() => {
                      setView(item.key);
                      setMobileMenuOpen(false); // Fermer le menu après sélection
                    }}
                    className={`flex items-center w-full px-4 py-3 text-base font-medium transition-all duration-300 border-2 rounded ${
                      view === item.key
                        ? 'bg-gray-200 text-black border-gray-400'
                        : 'text-black hover:text-black hover:bg-gray-100 border-transparent hover:border-gray-300'
                    }`}
                  >
                    <Icon className="h-5 w-5 mr-3" />
                    {item.label.toUpperCase()}
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Click outside to close menus */}
      {(userMenuOpen || mobileMenuOpen) && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => {
            setUserMenuOpen(false);
            setMobileMenuOpen(false);
          }}
        />
      )}
    </nav>
  );
};
