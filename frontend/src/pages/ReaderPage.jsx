import React, { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import {
  AlertCircle,
  BookOpen,
  HelpCircle,
  Sparkles,
  Volume2,
  Sliders,
} from 'lucide-react';
import api, { getErrorMessage } from '../api/client';
import { useAccessibility } from '../context/AccessibilityContext';
import AccessibilityControlsPanel from '../components/AccessibilityControlsPanel';
import TTSPlayer from '../components/TTSPlayer';

function highlightTextSegments(paragraph, keywords, enabled) {
  if (!enabled || !keywords || keywords.length === 0) {
    return paragraph;
  }
  const escaped = keywords
    .map((k) => String(k || '').trim())
    .filter((k) => k.length > 2)
    .map((k) => k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'));
  if (escaped.length === 0) return paragraph;

  const regex = new RegExp(`\\b(${escaped.join('|')})\\b`, 'gi');
  const parts = paragraph.split(regex);
  return parts.map((part, idx) => {
    const isMatch = escaped.some((kw) => new RegExp(`^${kw}$`, 'i').test(part));
    if (isMatch) {
      return (
        <mark key={idx} className="keyword-highlight">
          {part}
        </mark>
      );
    }
    return <React.Fragment key={idx}>{part}</React.Fragment>;
  });
}

export default function ReaderPage() {
  const { docId } = useParams();
  const navigate = useNavigate();
  const { prefs } = useAccessibility();

  const [docs, setDocs] = useState([]);
  const [activeDoc, setActiveDoc] = useState(null);
  const [viewMode, setViewMode] = useState('original'); // original | simplified
  const [showControls, setShowControls] = useState(true);
  const [showTTS, setShowTTS] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Word explainer
  const [lookupWord, setLookupWord] = useState('');
  const [wordInfo, setWordInfo] = useState(null);
  const [wordLoading, setWordLoading] = useState(false);
  const [wordError, setWordError] = useState('');

  useEffect(() => {
    api
      .get('/documents')
      .then(({ data }) => {
        const list = data.documents || [];
        setDocs(list);
        if (!docId && list.length > 0) {
          navigate(`/reader/${list[0].id}`, { replace: true });
        } else if (!docId && list.length === 0) {
          setLoading(false);
        }
      })
      .catch((err) => {
        setError(getErrorMessage(err, 'Could not load documents.'));
        setLoading(false);
      });
  }, [docId, navigate]);

  useEffect(() => {
    if (!docId) return;
    setLoading(true);
    setError('');
    api
      .get(`/documents/${docId}`)
      .then(({ data }) => {
        setActiveDoc(data.document);
        if (data.document?.latest_simplification?.simplified_text) {
          setViewMode('simplified');
        } else {
          setViewMode('original');
        }
      })
      .catch((err) => {
        setError(getErrorMessage(err, 'Could not open selected document.'));
      })
      .finally(() => setLoading(false));
  }, [docId]);

  const simplification = activeDoc?.latest_simplification || null;
  const displayedText = useMemo(() => {
    if (!activeDoc) return '';
    if (viewMode === 'simplified' && simplification?.simplified_text) {
      return simplification.simplified_text;
    }
    return activeDoc.extracted_text || '';
  }, [activeDoc, viewMode, simplification]);

  const keywords = useMemo(() => {
    const kws = [...(simplification?.key_concepts || [])];
    for (const dw of simplification?.difficult_words || []) {
      if (dw?.word) kws.push(dw.word);
    }
    return kws;
  }, [simplification]);

  const paragraphs = useMemo(() => {
    return (displayedText || '')
      .split(/\n{2,}/)
      .map((p) => p.trim())
      .filter(Boolean);
  }, [displayedText]);

  const handleExplainWord = async (e) => {
    e?.preventDefault();
    const term = lookupWord.trim();
    if (!term) return;
    setWordLoading(true);
    setWordError('');
    try {
      const { data } = await api.post('/ai/explain-word', {
        word: term,
        context: displayedText.slice(0, 1200),
      });
      setWordInfo(data.explanation);
    } catch (err) {
      setWordError(getErrorMessage(err, 'Could not explain this word right now.'));
    } finally {
      setWordLoading(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Accessible Reader</h1>
          <p className="page-subtitle">
            Read your study notes with combined font, spacing, contrast, zoom, keyword highlighting,
            and Text-to-Speech controls.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setShowControls((v) => !v)}
          >
            <Sliders size={15} /> {showControls ? 'Hide Display Controls' : 'Show Display Controls'}
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => setShowTTS((v) => !v)}
          >
            <Volume2 size={15} /> {showTTS ? 'Hide Audio Player' : 'Show Audio Player'}
          </button>
        </div>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {docs.length === 0 && !loading ? (
        <div className="card" style={{ textAlign: 'center', padding: '44px 24px' }}>
          <BookOpen size={34} color="var(--text-muted)" style={{ marginBottom: '12px' }} />
          <h2 className="card-title">No documents available to read</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Upload a PDF document first to open it in the Accessible Reader.
          </p>
          <Link to="/upload" className="btn btn-primary">
            Upload PDF Notes
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* Document Selector & Original/Simplified Toggle */}
          <div
            className="card"
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '14px',
            }}
          >
            <div style={{ flex: '1 1 280px' }}>
              <label className="form-label" htmlFor="reader-doc-select">
                Select Document
              </label>
              <select
                id="reader-doc-select"
                className="form-select"
                value={docId || ''}
                onChange={(e) => navigate(`/reader/${e.target.value}`)}
              >
                {docs.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.filename} ({d.word_count} words)
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
              <button
                type="button"
                className={`btn btn-sm ${viewMode === 'original' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setViewMode('original')}
              >
                Original Text
              </button>
              <button
                type="button"
                className={`btn btn-sm ${viewMode === 'simplified' ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setViewMode('simplified')}
                disabled={!simplification?.simplified_text}
                title={
                  simplification?.simplified_text
                    ? 'View AI-simplified version'
                    : 'Generate a simplified version first'
                }
              >
                Simplified Text
              </button>
              {activeDoc && (
                <Link to={`/simplify/${activeDoc.id}`} className="btn btn-secondary btn-sm">
                  <Sparkles size={14} /> {simplification ? 'Re-Simplify' : 'Simplify with AI'}
                </Link>
              )}
            </div>
          </div>

          {showControls && <AccessibilityControlsPanel compact />}

          {showTTS && activeDoc && (
            <TTSPlayer
              compact
              text={activeDoc.extracted_text || ''}
              simplifiedText={simplification?.simplified_text || ''}
              defaultSource={viewMode}
            />
          )}

          {/* Reading Surface + Vocabulary Helper */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 2fr) minmax(260px, 1fr)',
              gap: '18px',
              alignItems: 'start',
            }}
          >
            <div>
              {loading ? (
                <div className="card">Loading document content...</div>
              ) : activeDoc?.status === 'needs_ocr' ? (
                <div className="alert alert-warning">
                  <AlertCircle size={18} />
                  <span>{activeDoc.status_message}</span>
                </div>
              ) : (
                <article className="accessible-reading-surface" aria-label="Document Reading Area">
                  {paragraphs.length === 0 ? (
                    <p>No text available in this document.</p>
                  ) : (
                    paragraphs.map((para, idx) => (
                      <p key={idx}>
                        {highlightTextSegments(
                          para,
                          keywords,
                          Boolean(prefs.highlight_keywords)
                        )}
                      </p>
                    ))
                  )}
                </article>
              )}
            </div>

            <aside className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                <HelpCircle size={18} color="var(--accent)" />
                <h2 className="card-title" style={{ margin: 0 }}>Word & Concept Helper</h2>
              </div>

              <form onSubmit={handleExplainWord} style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
                <input
                  type="text"
                  className="form-input"
                  placeholder="Type a difficult word..."
                  value={lookupWord}
                  onChange={(e) => setLookupWord(e.target.value)}
                  aria-label="Word to explain"
                />
                <button type="submit" className="btn btn-primary btn-sm" disabled={wordLoading}>
                  {wordLoading ? '...' : 'Explain'}
                </button>
              </form>

              {wordError && (
                <div className="alert alert-error" style={{ padding: '8px 10px', fontSize: '0.84rem' }}>
                  {wordError}
                </div>
              )}

              {wordInfo && (
                <div
                  style={{
                    padding: '12px',
                    borderRadius: '8px',
                    backgroundColor: 'var(--accent-soft)',
                    marginBottom: '14px',
                  }}
                >
                  <div style={{ fontWeight: 700, marginBottom: '4px' }}>
                    {wordInfo.word}{' '}
                    {wordInfo.syllables_hint && (
                      <span style={{ fontWeight: 400, fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        ({wordInfo.syllables_hint})
                      </span>
                    )}
                  </div>
                  <p style={{ margin: '0 0 6px', fontSize: '0.9rem' }}>
                    {wordInfo.simple_explanation}
                  </p>
                  {wordInfo.example && (
                    <p style={{ margin: 0, fontSize: '0.84rem', color: 'var(--text-secondary)' }}>
                      Example: {wordInfo.example}
                    </p>
                  )}
                </div>
              )}

              {simplification?.key_concepts?.length > 0 && (
                <div style={{ marginBottom: '14px' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.88rem', marginBottom: '8px' }}>
                    Key Concepts
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                    {simplification.key_concepts.map((concept, idx) => (
                      <span key={idx} className="badge badge-accent">
                        {concept}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {simplification?.difficult_words?.length > 0 && (
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.88rem', marginBottom: '8px' }}>
                    Glossary from Simplification
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {simplification.difficult_words.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '10px',
                          borderRadius: '8px',
                          backgroundColor: 'var(--bg-subtle)',
                          fontSize: '0.88rem',
                        }}
                      >
                        <strong>{item.word}:</strong> {item.simple_explanation}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </aside>
          </div>
        </div>
      )}
    </div>
  );
}
