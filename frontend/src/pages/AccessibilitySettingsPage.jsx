import React, { useState } from 'react';
import { CheckCircle2, BookOpen, Eye, Headphones } from 'lucide-react';
import { useAccessibility } from '../context/AccessibilityContext';
import AccessibilityControlsPanel from '../components/AccessibilityControlsPanel';

const MODES = [
  { id: 'dyslexia', label: 'Dyslexia-friendly mode', icon: BookOpen },
  { id: 'low_vision', label: 'Low-vision mode', icon: Eye },
  { id: 'hearing', label: 'Hearing-accessible mode', icon: Headphones },
];

export default function AccessibilitySettingsPage() {
  const { prefs, updateLocalPrefs } = useAccessibility();
  const [savedBanner, setSavedBanner] = useState(false);

  const toggleMode = (id) => {
    const current = prefs.modes || [];
    const next = current.includes(id)
      ? current.filter((m) => m !== id)
      : [...current, id];
    updateLocalPrefs({ modes: next });
    setSavedBanner(false);
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Accessibility Settings</h1>
          <p className="page-subtitle">
            Combine multiple accessibility modes and fine-tune typography, spacing, contrast, and
            theme preferences. Changes persist in your MongoDB profile.
          </p>
        </div>
      </div>

      {savedBanner && (
        <div className="alert alert-success" role="status">
          <CheckCircle2 size={18} />
          <span>Your accessibility preferences have been saved to your account.</span>
        </div>
      )}

      <div className="card" style={{ marginBottom: '18px' }}>
        <h2 className="card-title">Active Accessibility Modes</h2>
        <div className="grid-3" style={{ marginTop: '12px' }}>
          {MODES.map(({ id, label, icon: Icon }) => {
            const active = (prefs.modes || []).includes(id);
            return (
              <button
                key={id}
                type="button"
                className="btn"
                onClick={() => toggleMode(id)}
                aria-pressed={active}
                style={{
                  justifyContent: 'flex-start',
                  padding: '14px 16px',
                  borderColor: active ? 'var(--primary)' : 'var(--border-color)',
                  backgroundColor: active ? 'var(--primary-soft)' : 'var(--bg-subtle)',
                  color: 'var(--text-primary)',
                }}
              >
                <Icon size={18} color="var(--primary)" />
                <span>{label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <AccessibilityControlsPanel onSaved={() => setSavedBanner(true)} />

      <div style={{ marginTop: '18px' }}>
        <h2 className="card-title">Live Reading Preview</h2>
        <div className="accessible-reading-surface">
          <p>
            Inclusive learning puts you in control of how information looks and sounds. Adjust
            font size, spacing, high contrast, and{' '}
            <span className={prefs.highlight_keywords ? 'keyword-highlight' : ''}>
              highlighted key terms
            </span>{' '}
            until reading feels effortless.
          </p>
        </div>
      </div>
    </div>
  );
}
