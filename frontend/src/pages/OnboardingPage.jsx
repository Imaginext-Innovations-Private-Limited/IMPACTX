import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Eye, Headphones, Check, ArrowRight, AlertCircle } from 'lucide-react';
import { useAccessibility } from '../context/AccessibilityContext';
import AccessibilityControlsPanel from '../components/AccessibilityControlsPanel';
import { getErrorMessage } from '../api/client';

const MODE_OPTIONS = [
  {
    id: 'dyslexia',
    title: 'Dyslexia-friendly mode',
    description:
      'Uses readable fonts, wider line and letter spacing, warm gentle background, and simpler sentence layouts.',
    icon: BookOpen,
    suggestedPatch: {
      font_style: 'dyslexia',
      line_spacing: 1.8,
      letter_spacing: 0.05,
      font_size: 19,
    },
  },
  {
    id: 'low_vision',
    title: 'Low-vision mode',
    description:
      'Increases text size, supports high contrast themes, reading zoom, and pairs easily with Text-to-Speech.',
    icon: Eye,
    suggestedPatch: {
      font_size: 22,
      high_contrast: true,
      zoom: 110,
      line_spacing: 1.7,
    },
  },
  {
    id: 'hearing',
    title: 'Hearing-accessible mode',
    description:
      'Prioritizes visual transcripts, real-time speech captions, keyword highlights, and text-first study workflows.',
    icon: Headphones,
    suggestedPatch: {
      highlight_keywords: true,
    },
  },
];

export default function OnboardingPage() {
  const { prefs, updateLocalPrefs, savePreferences, saving } = useAccessibility();
  const navigate = useNavigate();
  const [error, setError] = useState('');

  const toggleMode = (option) => {
    const current = prefs.modes || [];
    const exists = current.includes(option.id);
    const nextModes = exists
      ? current.filter((m) => m !== option.id)
      : [...current, option.id];

    const patch = { modes: nextModes };
    if (!exists) {
      Object.assign(patch, option.suggestedPatch);
    }
    updateLocalPrefs(patch);
  };

  const handleFinish = async () => {
    setError('');
    try {
      await savePreferences({ ...prefs, onboarding_completed: true });
      navigate('/dashboard');
    } catch (err) {
      setError(getErrorMessage(err, 'Could not save accessibility settings.'));
    }
  };

  return (
    <div style={{ maxWidth: '980px', margin: '0 auto', padding: '36px 24px' }}>
      <div className="page-header">
        <div>
          <span className="badge badge-primary" style={{ marginBottom: '8px' }}>
            Step 1 of 1 — Personalise Your Learning Comfort
          </span>
          <h1 className="page-title">Accessibility Onboarding</h1>
          <p className="page-subtitle">
            Select one or more modes that fit how you learn best. You can change any setting anytime.
            LearnAble AI adapts your study workspace and never diagnoses any condition.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="grid-3" style={{ marginBottom: '22px' }}>
        {MODE_OPTIONS.map((option) => {
          const Icon = option.icon;
          const selected = (prefs.modes || []).includes(option.id);
          return (
            <button
              key={option.id}
              type="button"
              onClick={() => toggleMode(option)}
              aria-pressed={selected}
              className="card"
              style={{
                textAlign: 'left',
                cursor: 'pointer',
                borderColor: selected ? 'var(--primary)' : 'var(--border-color)',
                backgroundColor: selected ? 'var(--primary-soft)' : 'var(--bg-surface)',
                borderWidth: selected ? '2px' : '1px',
              }}
            >
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '12px',
                }}
              >
                <Icon size={22} color="var(--primary)" />
                {selected && (
                  <span className="badge badge-primary">
                    <Check size={13} /> Selected
                  </span>
                )}
              </div>
              <div className="card-title">{option.title}</div>
              <p style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-secondary)' }}>
                {option.description}
              </p>
            </button>
          );
        })}
      </div>

      <AccessibilityControlsPanel showSaveButton={false} />

      <div style={{ marginTop: '22px', marginBottom: '22px' }}>
        <h3 className="card-title" style={{ marginBottom: '10px' }}>
          Live Reading Preview
        </h3>
        <div className="accessible-reading-surface">
          <p>
            Photosynthesis is how plants turn sunlight into energy. Clear spacing, readable
            typography, and{' '}
            <span className={prefs.highlight_keywords ? 'keyword-highlight' : ''}>
              highlighted key concepts
            </span>{' '}
            help make complex study notes easier to follow at your own pace.
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleFinish}
          disabled={saving}
        >
          <span>{saving ? 'Saving Preferences...' : 'Save & Open Dashboard'}</span>
          <ArrowRight size={18} />
        </button>
      </div>
    </div>
  );
}
