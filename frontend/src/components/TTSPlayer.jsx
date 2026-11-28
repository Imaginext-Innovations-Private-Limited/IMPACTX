import React, { useEffect, useRef, useState } from 'react';
import { Pause, Play, RotateCcw, Square, Volume2, AlertCircle } from 'lucide-react';
import { useAccessibility } from '../context/AccessibilityContext';

export default function TTSPlayer({
  text = '',
  simplifiedText = '',
  defaultSource = 'original',
  compact = false,
}) {
  const { prefs, updateLocalPrefs } = useAccessibility();
  const speechSupported =
    typeof window !== 'undefined' &&
    'speechSynthesis' in window &&
    typeof window.SpeechSynthesisUtterance !== 'undefined';

  const [voices, setVoices] = useState([]);
  const [selectedVoice, setSelectedVoice] = useState(prefs.tts_voice || '');
  const [rate, setRate] = useState(prefs.tts_speed || 1.0);
  const [source, setSource] = useState(
    defaultSource === 'simplified' && simplifiedText ? 'simplified' : 'original'
  );
  const [status, setStatus] = useState('idle'); // idle | playing | paused
  const [errorMsg, setErrorMsg] = useState('');
  const utteranceRef = useRef(null);

  useEffect(() => {
    if (!simplifiedText && source === 'simplified') {
      setSource('original');
    }
  }, [simplifiedText, source]);

  useEffect(() => {
    if (!speechSupported) return;

    const loadVoices = () => {
      const available = window.speechSynthesis.getVoices();
      setVoices(available);
      if (!selectedVoice && available.length > 0) {
        const english = available.find((v) => v.lang.startsWith('en')) || available[0];
        setSelectedVoice(english.name);
      }
    };

    loadVoices();
    window.speechSynthesis.addEventListener('voiceschanged', loadVoices);
    return () => {
      window.speechSynthesis.removeEventListener('voiceschanged', loadVoices);
      window.speechSynthesis.cancel();
    };
  }, [speechSupported]);

  const activeText =
    source === 'simplified' && simplifiedText ? simplifiedText : text;

  const handlePlay = () => {
    if (!speechSupported) return;
    const cleanText = (activeText || '').trim();
    if (!cleanText) {
      setErrorMsg('There is no text selected to read aloud.');
      return;
    }

    setErrorMsg('');
    window.speechSynthesis.cancel();

    const utterance = new window.SpeechSynthesisUtterance(cleanText);
    const chosen = voices.find((v) => v.name === selectedVoice);
    if (chosen) utterance.voice = chosen;
    utterance.rate = Number(rate) || 1.0;

    utterance.onstart = () => setStatus('playing');
    utterance.onpause = () => setStatus('paused');
    utterance.onresume = () => setStatus('playing');
    utterance.onend = () => setStatus('idle');
    utterance.onerror = (event) => {
      if (event.error !== 'interrupted' && event.error !== 'canceled') {
        setErrorMsg(`Audio playback error: ${event.error || 'unknown error'}`);
      }
      setStatus('idle');
    };

    utteranceRef.current = utterance;
    window.speechSynthesis.speak(utterance);
  };

  const handlePause = () => {
    if (!speechSupported) return;
    if (window.speechSynthesis.speaking && !window.speechSynthesis.paused) {
      window.speechSynthesis.pause();
      setStatus('paused');
    }
  };

  const handleResume = () => {
    if (!speechSupported) return;
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
      setStatus('playing');
    }
  };

  const handleStop = () => {
    if (!speechSupported) return;
    window.speechSynthesis.cancel();
    setStatus('idle');
  };

  if (!speechSupported) {
    return (
      <div className="alert alert-warning" role="status">
        <AlertCircle size={18} />
        <div>
          <strong>Text-to-Speech unavailable:</strong> Your current browser does not
          support the Web SpeechSynthesis API. Try a modern Chrome, Edge, or Safari browser.
        </div>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: compact ? '16px' : '22px' }}>
      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
          marginBottom: '14px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Volume2 size={20} color="var(--primary)" />
          <h3 className="card-title" style={{ margin: 0 }}>
            Text-to-Speech Audio Player
          </h3>
          <span className={`badge ${status === 'playing' ? 'badge-success' : ''}`}>
            {status === 'playing'
              ? 'Speaking'
              : status === 'paused'
              ? 'Paused'
              : 'Ready'}
          </span>
        </div>

        {simplifiedText && (
          <div style={{ display: 'flex', gap: '6px' }}>
            <button
              type="button"
              className={`btn btn-sm ${
                source === 'original' ? 'btn-primary' : 'btn-secondary'
              }`}
              onClick={() => {
                handleStop();
                setSource('original');
              }}
            >
              Original Text
            </button>
            <button
              type="button"
              className={`btn btn-sm ${
                source === 'simplified' ? 'btn-primary' : 'btn-secondary'
              }`}
              onClick={() => {
                handleStop();
                setSource('simplified');
              }}
            >
              Simplified Text
            </button>
          </div>
        )}
      </div>

      {errorMsg && (
        <div className="alert alert-error" role="alert">
          <AlertCircle size={16} />
          <span>{errorMsg}</span>
        </div>
      )}

      <div
        style={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: '10px',
          alignItems: 'center',
          marginBottom: '14px',
        }}
      >
        <button
          type="button"
          className="btn btn-primary btn-sm"
          onClick={handlePlay}
          disabled={!activeText.trim()}
        >
          <Play size={16} />
          <span>{status === 'playing' ? 'Restart' : 'Play'}</span>
        </button>

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={handlePause}
          disabled={status !== 'playing'}
        >
          <Pause size={16} />
          <span>Pause</span>
        </button>

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={handleResume}
          disabled={status !== 'paused'}
        >
          <RotateCcw size={16} />
          <span>Resume</span>
        </button>

        <button
          type="button"
          className="btn btn-secondary btn-sm"
          onClick={handleStop}
          disabled={status === 'idle'}
        >
          <Square size={16} />
          <span>Stop</span>
        </button>
      </div>

      <div className="grid-2" style={{ gap: '14px' }}>
        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="tts-voice-select">
            Voice
          </label>
          <select
            id="tts-voice-select"
            className="form-select"
            value={selectedVoice}
            onChange={(e) => {
              setSelectedVoice(e.target.value);
              updateLocalPrefs({ tts_voice: e.target.value });
            }}
          >
            {voices.length === 0 ? (
              <option value="">Default System Voice</option>
            ) : (
              voices.map((v) => (
                <option key={`${v.name}-${v.lang}`} value={v.name}>
                  {v.name} ({v.lang})
                </option>
              ))
            )}
          </select>
        </div>

        <div className="form-group" style={{ marginBottom: 0 }}>
          <label className="form-label" htmlFor="tts-speed-range">
            Speech Speed: {Number(rate).toFixed(2)}x
          </label>
          <input
            id="tts-speed-range"
            type="range"
            min="0.6"
            max="1.8"
            step="0.1"
            value={rate}
            onChange={(e) => {
              const val = parseFloat(e.target.value);
              setRate(val);
              updateLocalPrefs({ tts_speed: val });
            }}
            style={{ width: '100%', accentColor: 'var(--primary)' }}
          />
        </div>
      </div>
    </div>
  );
}
