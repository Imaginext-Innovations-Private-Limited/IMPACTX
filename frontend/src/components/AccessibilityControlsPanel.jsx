import React from 'react';
import { RotateCcw, Save } from 'lucide-react';
import { useAccessibility } from '../context/AccessibilityContext';

export default function AccessibilityControlsPanel({
  showSaveButton = true,
  onSaved,
  compact = false,
}) {
  const { prefs, saving, updateLocalPrefs, savePreferences, resetPreferences } =
    useAccessibility();

  const handleSave = async () => {
    await savePreferences(prefs);
    if (onSaved) onSaved();
  };

  return (
    <div className="card" style={{ padding: compact ? '16px' : '22px' }}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '10px',
          marginBottom: '16px',
        }}
      >
        <h3 className="card-title" style={{ margin: 0 }}>
          Reading & Display Controls
        </h3>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={resetPreferences}
            disabled={saving}
          >
            <RotateCcw size={14} />
            <span>Reset</span>
          </button>
          {showSaveButton && (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={handleSave}
              disabled={saving}
            >
              <Save size={14} />
              <span>{saving ? 'Saving...' : 'Save Preferences'}</span>
            </button>
          )}
        </div>
      </div>

      <div className="grid-3" style={{ gap: '14px' }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="ctrl-font-size">
            Font Size: {prefs.font_size}px
          </label>
          <input
            id="ctrl-font-size"
            type="range"
            min="14"
            max="32"
            step="1"
            value={prefs.font_size}
            onChange={(e) =>
              updateLocalPrefs({ font_size: parseInt(e.target.value, 10) })
            }
          />
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="ctrl-line-spacing">
            Line Spacing: {prefs.line_spacing}
          </label>
          <input
            id="ctrl-line-spacing"
            type="range"
            min="1.2"
            max="2.6"
            step="0.1"
            value={prefs.line_spacing}
            onChange={(e) =>
              updateLocalPrefs({ line_spacing: parseFloat(e.target.value) })
            }
          />
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="ctrl-letter-spacing">
            Letter Spacing: {prefs.letter_spacing}em
          </label>
          <input
            id="ctrl-letter-spacing"
            type="range"
            min="0"
            max="0.16"
            step="0.01"
            value={prefs.letter_spacing}
            onChange={(e) =>
              updateLocalPrefs({ letter_spacing: parseFloat(e.target.value) })
            }
          />
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="ctrl-zoom">
            Reading Zoom: {prefs.zoom}%
          </label>
          <input
            id="ctrl-zoom"
            type="range"
            min="80"
            max="160"
            step="10"
            value={prefs.zoom}
            onChange={(e) =>
              updateLocalPrefs({ zoom: parseInt(e.target.value, 10) })
            }
          />
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="ctrl-font-style">
            Font Style
          </label>
          <select
            id="ctrl-font-style"
            className="form-select"
            value={prefs.font_style}
            onChange={(e) => updateLocalPrefs({ font_style: e.target.value })}
          >
            <option value="default">Default Clean Sans (Inter)</option>
            <option value="dyslexia">Dyslexia-Friendly (Atkinson Hyperlegible)</option>
            <option value="serif">Readable Serif (Lora)</option>
            <option value="mono">Monospace (JetBrains Mono)</option>
          </select>
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="ctrl-theme">
            Theme
          </label>
          <select
            id="ctrl-theme"
            className="form-select"
            value={prefs.theme}
            onChange={(e) => updateLocalPrefs({ theme: e.target.value })}
          >
            <option value="light">Light Theme</option>
            <option value="dark">Dark Theme</option>
          </select>
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '18px',
          marginTop: '16px',
          paddingTop: '14px',
          borderTop: '1px solid var(--border-color)',
        }}
      >
        <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={Boolean(prefs.high_contrast)}
            onChange={(e) => updateLocalPrefs({ high_contrast: e.target.checked })}
          />
          <span style={{ fontWeight: 500 }}>High Contrast Mode</span>
        </label>

        <label style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={Boolean(prefs.highlight_keywords)}
            onChange={(e) => updateLocalPrefs({ highlight_keywords: e.target.checked })}
          />
          <span style={{ fontWeight: 500 }}>Highlight Key Concepts</span>
        </label>
      </div>
    </div>
  );
}
