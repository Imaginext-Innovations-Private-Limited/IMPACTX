import React, { useEffect, useRef, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  Headphones,
  Mic,
  MicOff,
  Save,
  Trash2,
  Upload,
  Volume2,
} from 'lucide-react';
import api, { getErrorMessage } from '../api/client';
import TTSPlayer from '../components/TTSPlayer';

export default function AudioCaptionsPage({ initialTab = 'captions' }) {
  const [activeTab, setActiveTab] = useState(initialTab);

  // TTS studio state
  const [docs, setDocs] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState('');
  const [ttsDoc, setTtsDoc] = useState(null);
  const [customSpeechText, setCustomSpeechText] = useState(
    'Welcome to LearnAble AI. Select any uploaded document or paste study notes here to listen with Text-to-Speech.'
  );

  // Live Web Speech API Captions state
  const SpeechRecognitionAPI =
    typeof window !== 'undefined'
      ? window.SpeechRecognition || window.webkitSpeechRecognition
      : null;
  const speechRecSupported = Boolean(SpeechRecognitionAPI);

  const recognitionRef = useRef(null);
  const isListeningRef = useRef(false);
  const [listening, setListening] = useState(false);
  const [interimText, setInterimText] = useState('');
  const [transcriptTitle, setTranscriptTitle] = useState('Lecture Notes Transcript');
  const [transcriptText, setTranscriptText] = useState('');
  const [editingId, setEditingId] = useState('');

  // Audio upload transcription state
  const [whisperConfigured, setWhisperConfigured] = useState(false);
  const [audioFile, setAudioFile] = useState(null);
  const [transcribing, setTranscribing] = useState(false);

  // Saved transcripts
  const [savedTranscripts, setSavedTranscripts] = useState([]);
  const [statusMsg, setStatusMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setActiveTab(initialTab);
  }, [initialTab]);

  useEffect(() => {
    api
      .get('/documents')
      .then(({ data }) => {
        const list = data.documents || [];
        setDocs(list);
        if (list.length > 0) setSelectedDocId(list[0].id);
      })
      .catch(() => {});

    api
      .get('/transcripts')
      .then(({ data }) => setSavedTranscripts(data.transcripts || []))
      .catch(() => {});

    api
      .get('/transcripts/capabilities')
      .then(({ data }) => setWhisperConfigured(Boolean(data.whisper_configured)))
      .catch(() => {});

    return () => {
      isListeningRef.current = false;
      recognitionRef.current?.stop();
    };
  }, []);

  useEffect(() => {
    if (!selectedDocId) {
      setTtsDoc(null);
      return;
    }
    api
      .get(`/documents/${selectedDocId}`)
      .then(({ data }) => setTtsDoc(data.document))
      .catch(() => {});
  }, [selectedDocId]);

  const startLiveCaptions = () => {
    if (!speechRecSupported) return;
    setErrorMsg('');
    setStatusMsg('');

    const recognition = new SpeechRecognitionAPI();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onresult = (event) => {
      let finalChunk = '';
      let interimChunk = '';
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const chunk = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalChunk += `${chunk.trim()} `;
        } else {
          interimChunk += chunk;
        }
      }
      if (finalChunk) {
        setTranscriptText((prev) => `${prev}${prev ? ' ' : ''}${finalChunk.trim()}`);
      }
      setInterimText(interimChunk);
    };

    recognition.onerror = (event) => {
      if (event.error === 'not-allowed') {
        setErrorMsg('Microphone permission was denied. Please allow microphone access to use live captions.');
      } else if (event.error !== 'no-speech' && event.error !== 'aborted') {
        setErrorMsg(`Speech recognition error: ${event.error}`);
      }
      isListeningRef.current = false;
      setListening(false);
    };

    recognition.onend = () => {
      setInterimText('');
      if (isListeningRef.current) {
        try {
          recognition.start();
        } catch {
          isListeningRef.current = false;
          setListening(false);
        }
      } else {
        setListening(false);
      }
    };

    recognitionRef.current = recognition;
    isListeningRef.current = true;
    setListening(true);
    recognition.start();
  };

  const stopLiveCaptions = () => {
    isListeningRef.current = false;
    setListening(false);
    setInterimText('');
    recognitionRef.current?.stop();
  };

  const handleAudioUploadTranscribe = async () => {
    if (!audioFile) return;
    setErrorMsg('');
    setStatusMsg('');
    setTranscribing(true);

    const formData = new FormData();
    formData.append('file', audioFile);
    formData.append('title', transcriptTitle || audioFile.name);

    try {
      const { data } = await api.post('/transcripts/transcribe', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const created = data.transcript;
      setSavedTranscripts((prev) => [created, ...prev]);
      setEditingId(created.id);
      setTranscriptTitle(created.title);
      setTranscriptText(created.text);
      setStatusMsg('Audio transcribed and saved successfully.');
    } catch (err) {
      setErrorMsg(getErrorMessage(err, 'Audio transcription failed.'));
    } finally {
      setTranscribing(false);
    }
  };

  const handleSaveTranscript = async () => {
    if (!transcriptText.trim()) {
      setErrorMsg('Transcript text cannot be empty before saving.');
      return;
    }
    setErrorMsg('');
    setStatusMsg('');
    setSaving(true);
    try {
      if (editingId) {
        const { data } = await api.put(`/transcripts/${editingId}`, {
          title: transcriptTitle.trim() || 'Untitled Transcript',
          text: transcriptText.trim(),
        });
        setSavedTranscripts((prev) =>
          prev.map((item) => (item.id === editingId ? data.transcript : item))
        );
        setStatusMsg('Transcript changes saved.');
      } else {
        const { data } = await api.post('/transcripts', {
          title: transcriptTitle.trim() || 'Live Speech Transcript',
          text: transcriptText.trim(),
          source_type: 'live_speech',
          provider: 'web_speech_api',
        });
        setSavedTranscripts((prev) => [data.transcript, ...prev]);
        setEditingId(data.transcript.id);
        setStatusMsg('Transcript saved to your library.');
      }
    } catch (err) {
      setErrorMsg(getErrorMessage(err, 'Could not save transcript.'));
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteTranscript = async (id) => {
    try {
      await api.delete(`/transcripts/${id}`);
      setSavedTranscripts((prev) => prev.filter((t) => t.id !== id));
      if (editingId === id) {
        setEditingId('');
        setTranscriptText('');
        setTranscriptTitle('Lecture Notes Transcript');
      }
    } catch (err) {
      setErrorMsg(getErrorMessage(err, 'Could not delete transcript.'));
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Audio & Hearing Captions</h1>
          <p className="page-subtitle">
            Listen to your documents with Text-to-Speech, or capture live captions and transcripts.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'captions' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('captions')}
          >
            <Headphones size={15} /> Captions & Transcripts
          </button>
          <button
            type="button"
            className={`btn btn-sm ${activeTab === 'tts' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setActiveTab('tts')}
          >
            <Volume2 size={15} /> Text-to-Speech Studio
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="alert alert-error" role="alert">
          <AlertCircle size={18} />
          <span>{errorMsg}</span>
        </div>
      )}
      {statusMsg && (
        <div className="alert alert-success" role="status">
          <CheckCircle2 size={18} />
          <span>{statusMsg}</span>
        </div>
      )}

      {activeTab === 'tts' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div className="card">
            <div className="form-group">
              <label className="form-label" htmlFor="tts-doc-select">
                Choose Document to Listen To (or use custom text below)
              </label>
              <select
                id="tts-doc-select"
                className="form-select"
                value={selectedDocId}
                onChange={(e) => setSelectedDocId(e.target.value)}
              >
                <option value="">Custom Study Text</option>
                {docs.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.filename}
                  </option>
                ))}
              </select>
            </div>

            {!selectedDocId && (
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" htmlFor="tts-custom-text">
                  Text to Read Aloud
                </label>
                <textarea
                  id="tts-custom-text"
                  className="form-textarea"
                  value={customSpeechText}
                  onChange={(e) => setCustomSpeechText(e.target.value)}
                />
              </div>
            )}
          </div>

          <TTSPlayer
            text={selectedDocId ? ttsDoc?.extracted_text || '' : customSpeechText}
            simplifiedText={
              selectedDocId ? ttsDoc?.latest_simplification?.simplified_text || '' : ''
            }
          />
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* Live Microphone Speech-to-Text */}
          <div className="card">
            <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '12px', marginBottom: '14px' }}>
              <div>
                <h2 className="card-title" style={{ margin: 0 }}>Live Microphone Captions (Web Speech API)</h2>
                <p style={{ margin: '4px 0 0', fontSize: '0.88rem', color: 'var(--text-secondary)' }}>
                  Real-time browser speech recognition for lectures and spoken explanations.
                </p>
              </div>
              {speechRecSupported ? (
                listening ? (
                  <button type="button" className="btn btn-danger" onClick={stopLiveCaptions}>
                    <MicOff size={17} /> Stop Live Captions
                  </button>
                ) : (
                  <button type="button" className="btn btn-primary" onClick={startLiveCaptions}>
                    <Mic size={17} /> Start Live Captions
                  </button>
                )
              ) : null}
            </div>

            {!speechRecSupported && (
              <div className="alert alert-warning">
                <AlertCircle size={18} />
                <div>
                  <strong>Browser Limitation:</strong> Live microphone speech recognition requires a
                  browser with Web Speech API support (such as Google Chrome or Microsoft Edge).
                </div>
              </div>
            )}

            <div className="live-caption-box" aria-live="polite" aria-label="Live Captions">
              {transcriptText || interimText ? (
                <>
                  <span>{transcriptText.slice(-320)} </span>
                  <span className="live-caption-interim">{interimText}</span>
                </>
              ) : (
                <span style={{ color: '#94a3b8' }}>
                  {listening
                    ? 'Listening... speak clearly into your microphone to see live captions here.'
                    : 'Live captions will appear here in high-contrast large text when active.'}
                </span>
              )}
            </div>
          </div>

          {/* Audio File Upload Transcription */}
          <div className="card">
            <h2 className="card-title">Upload Audio File for Transcription (Whisper-Compatible)</h2>
            <p style={{ margin: '0 0 12px', color: 'var(--text-secondary)', fontSize: '0.9rem' }}>
              Supported formats: MP3, WAV, M4A, OGG, WebM. Browser Web Speech API cannot transcribe
              pre-recorded files directly, so uploaded audio uses the backend Whisper-compatible service.
            </p>

            {!whisperConfigured && (
              <div className="alert alert-info">
                <AlertCircle size={18} />
                <div>
                  <strong>Service Configuration Notice:</strong> A Whisper-compatible endpoint is not
                  currently configured on the backend (<code>WHISPER_API_URL</code> in{' '}
                  <code>backend/.env</code>). Live microphone captions above still work in supported
                  browsers, and you can edit and save transcripts below.
                </div>
              </div>
            )}

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', alignItems: 'center' }}>
              <input
                type="file"
                accept=".mp3,.wav,.m4a,.ogg,.webm,.mp4,.mpeg"
                onChange={(e) => setAudioFile(e.target.files?.[0] || null)}
              />
              <button
                type="button"
                className="btn btn-secondary"
                disabled={!audioFile || transcribing}
                onClick={handleAudioUploadTranscribe}
              >
                <Upload size={16} />
                <span>{transcribing ? 'Transcribing...' : 'Transcribe Audio File'}</span>
              </button>
            </div>
          </div>

          {/* Transcript Editor + Saved Transcripts */}
          <div className="grid-2">
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h2 className="card-title" style={{ margin: 0 }}>
                  {editingId ? 'Edit Saved Transcript' : 'Transcript Workspace'}
                </h2>
                {editingId && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={() => {
                      setEditingId('');
                      setTranscriptTitle('Lecture Notes Transcript');
                      setTranscriptText('');
                    }}
                  >
                    New Transcript
                  </button>
                )}
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="transcript-title-input">
                  Transcript Title
                </label>
                <input
                  id="transcript-title-input"
                  type="text"
                  className="form-input"
                  value={transcriptTitle}
                  onChange={(e) => setTranscriptTitle(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="transcript-body-input">
                  Transcript Text (Editable)
                </label>
                <textarea
                  id="transcript-body-input"
                  className="form-textarea"
                  rows={8}
                  placeholder="Speak with Live Captions above or type/edit your transcript notes here..."
                  value={transcriptText}
                  onChange={(e) => setTranscriptText(e.target.value)}
                />
              </div>

              <button
                type="button"
                className="btn btn-primary"
                onClick={handleSaveTranscript}
                disabled={saving}
              >
                <Save size={16} />
                <span>{saving ? 'Saving...' : editingId ? 'Update Transcript' : 'Save Transcript'}</span>
              </button>
            </div>

            <div className="card">
              <h2 className="card-title">Saved Transcripts</h2>
              {savedTranscripts.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', margin: 0 }}>
                  No saved transcripts yet. Record live captions or transcribe audio and save it here.
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {savedTranscripts.map((item) => (
                    <div
                      key={item.id}
                      style={{
                        padding: '12px',
                        borderRadius: '8px',
                        backgroundColor: 'var(--bg-subtle)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        gap: '10px',
                        alignItems: 'center',
                      }}
                    >
                      <div style={{ minWidth: 0 }}>
                        <div style={{ fontWeight: 600 }}>{item.title}</div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                          {item.source_type.replace('_', ' ')} •{' '}
                          {item.updated_at ? new Date(item.updated_at).toLocaleString() : ''}
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          onClick={() => {
                            setEditingId(item.id);
                            setTranscriptTitle(item.title);
                            setTranscriptText(item.text);
                          }}
                        >
                          Open / Edit
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          onClick={() => handleDeleteTranscript(item.id)}
                          aria-label={`Delete ${item.title}`}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
