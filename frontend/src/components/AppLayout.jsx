import React, { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import {
  BookOpen,
  FileText,
  Upload,
  Sparkles,
  Headphones,
  CheckSquare,
  BarChart3,
  Sliders,
  User,
  LogOut,
  LayoutDashboard,
  Menu,
  X,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useAccessibility } from '../context/AccessibilityContext';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/documents', label: 'My Documents', icon: FileText },
  { to: '/upload', label: 'Upload Notes', icon: Upload },
  { to: '/reader', label: 'Accessible Reader', icon: BookOpen },
  { to: '/simplify', label: 'AI Simplification', icon: Sparkles },
  { to: '/audio-captions', label: 'Audio and Captions', icon: Headphones },
  { to: '/practice', label: 'Practice Centre', icon: CheckSquare },
  { to: '/progress', label: 'Progress', icon: BarChart3 },
  { to: '/settings/accessibility', label: 'Accessibility Settings', icon: Sliders },
  { to: '/profile', label: 'Profile', icon: User },
];

export default function AppLayout({ children }) {
  const { user, logout } = useAuth();
  const { prefs, savePreferences } = useAccessibility();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const toggleQuickContrast = async () => {
    await savePreferences({ high_contrast: !prefs.high_contrast });
  };

  const toggleQuickTheme = async () => {
    await savePreferences({ theme: prefs.theme === 'dark' ? 'light' : 'dark' });
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? 'open' : ''}`} aria-label="Primary Navigation">
        <div className="sidebar-brand">
          <div className="brand-mark" aria-hidden="true">LA</div>
          <div>
            <div className="brand-title">LearnAble AI</div>
            <div className="brand-subtitle">Inclusive Learning</div>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm mobile-menu-btn"
            style={{ marginLeft: 'auto' }}
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation menu"
          >
            <X size={16} />
          </button>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              onClick={() => setSidebarOpen(false)}
            >
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div style={{ padding: '4px 8px', fontSize: '0.84rem', color: 'var(--text-muted)' }}>
            Signed in as <strong style={{ color: 'var(--text-primary)' }}>{user?.full_name}</strong>
          </div>
          <button type="button" className="btn btn-secondary btn-sm" onClick={handleLogout}>
            <LogOut size={16} aria-hidden="true" />
            <span>Log Out</span>
          </button>
        </div>
      </aside>

      <div className="main-area">
        <header className="topbar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm mobile-menu-btn"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open navigation menu"
            >
              <Menu size={18} />
            </button>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', alignItems: 'center' }}>
              {(prefs.modes || []).length > 0 ? (
                prefs.modes.map((m) => (
                  <span key={m} className="badge badge-primary">
                    {m.replace('_', ' ')} mode
                  </span>
                ))
              ) : (
                <span className="badge">Standard Profile</span>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={toggleQuickContrast}
              aria-pressed={prefs.high_contrast}
            >
              {prefs.high_contrast ? 'High Contrast: On' : 'High Contrast: Off'}
            </button>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={toggleQuickTheme}
            >
              {prefs.theme === 'dark' ? 'Light Theme' : 'Dark Theme'}
            </button>
          </div>
        </header>

        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}
