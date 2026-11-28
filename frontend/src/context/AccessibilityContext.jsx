import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import api from '../api/client';
import { useAuth } from './AuthContext';

export const DEFAULT_PREFS = {
  modes: [],
  font_size: 18,
  font_style: 'default',
  high_contrast: false,
  theme: 'light',
  line_spacing: 1.6,
  letter_spacing: 0.02,
  zoom: 100,
  highlight_keywords: true,
  tts_speed: 1.0,
  tts_voice: '',
  onboarding_completed: false,
};

const FONT_FAMILIES = {
  default: "'Inter', system-ui, -apple-system, sans-serif",
  dyslexia: "'Atkinson Hyperlegible', 'Inter', Verdana, sans-serif",
  serif: "'Lora', Georgia, serif",
  mono: "'JetBrains Mono', monospace",
};

const AccessibilityContext = createContext(null);

export function AccessibilityProvider({ children }) {
  const { user, setUser, isAuthenticated } = useAuth();
  const [prefs, setPrefs] = useState(DEFAULT_PREFS);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (user?.accessibility) {
      setPrefs({ ...DEFAULT_PREFS, ...user.accessibility });
    } else if (!isAuthenticated) {
      setPrefs(DEFAULT_PREFS);
    }
  }, [user, isAuthenticated]);

  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--a11y-font-size', `${prefs.font_size}px`);
    root.style.setProperty('--a11y-line-height', `${prefs.line_spacing}`);
    root.style.setProperty('--a11y-letter-spacing', `${prefs.letter_spacing}em`);
    root.style.setProperty(
      '--a11y-font-family',
      FONT_FAMILIES[prefs.font_style] || FONT_FAMILIES.default
    );
    root.style.setProperty('--a11y-zoom', `${(prefs.zoom || 100) / 100}`);

    root.classList.toggle('theme-dark', prefs.theme === 'dark');
    root.classList.toggle('a11y-high-contrast', Boolean(prefs.high_contrast));
    root.classList.toggle('mode-dyslexia', (prefs.modes || []).includes('dyslexia'));
    root.classList.toggle('mode-low-vision', (prefs.modes || []).includes('low_vision'));
    root.classList.toggle('mode-hearing', (prefs.modes || []).includes('hearing'));
  }, [prefs]);

  const updateLocalPrefs = useCallback((patch) => {
    setPrefs((prev) => ({ ...prev, ...patch }));
  }, []);

  const savePreferences = useCallback(
    async (patch = {}) => {
      const next = { ...prefs, ...patch };
      setPrefs(next);
      if (!isAuthenticated) return next;
      setSaving(true);
      try {
        const { data } = await api.put('/accessibility', next);
        setPrefs({ ...DEFAULT_PREFS, ...data.accessibility });
        if (data.user) {
          setUser(data.user);
        }
        return data.accessibility;
      } finally {
        setSaving(false);
      }
    },
    [prefs, isAuthenticated, setUser]
  );

  const resetPreferences = useCallback(async () => {
    return savePreferences({
      ...DEFAULT_PREFS,
      onboarding_completed: prefs.onboarding_completed,
    });
  }, [savePreferences, prefs.onboarding_completed]);

  return (
    <AccessibilityContext.Provider
      value={{
        prefs,
        saving,
        updateLocalPrefs,
        savePreferences,
        resetPreferences,
      }}
    >
      {children}
    </AccessibilityContext.Provider>
  );
}

export function useAccessibility() {
  const ctx = useContext(AccessibilityContext);
  if (!ctx) {
    throw new Error('useAccessibility must be used inside AccessibilityProvider');
  }
  return ctx;
}
