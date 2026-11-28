import React, { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { AlertCircle, BookOpen, Sparkles, Tag } from 'lucide-react';
import api, { getErrorMessage } from '../api/client';

export default function SimplifyPage() {
  const { docId } = useParams();
  const navigate = useNavigate();

  const [docs, setDocs] = useState([]);
  const [activeDoc, setActiveDoc] = useState(null);
  const [selectionMode, setSelectionMode] = useState('all'); // all | custom
  const [customPassage, setCustomPassage] = useState('');
  const [result, setResult] = useState(null);
  const [loadingDoc, setLoadingDoc] = useState(true);
  const [simplifying, setSimplifying] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get('/documents')
      .then(({ data }) => {
        const list = data.documents || [];
        setDocs(list);
        if (!docId && list.length > 0) {
          navigate(`/simplify/${list[0].id}`, { replace: true });
        } else if (!docId) {
          setLoadingDoc(false);
        }
      })
      .catch((err) => {
        setError(getErrorMessage(err, 'Could not load documents.'));
        setLoadingDoc(false);
      });
  }, [docId, navigate]);

  useEffect(() => {
    if (!docId) return;
    setLoadingDoc(true);
    setError('');
    api
      .get(`/documents/${docId}`)
      .then(({ data }) => {
        setActiveDoc(data.document);
        setCustomPassage((data.document?.extracted_text || '').slice(0, 2500));
        setResult(data.document?.latest_simplification || null);
      })
      .catch((err) => {
        setError(getErrorMessage(err, 'Failed to load document content.'));
      })
      .finally(() => setLoadingDoc(false));
  }, [docId]);

  const handleSimplify = async () => {
    if (!activeDoc) return;
    const textToSimplify =
      selectionMode === 'custom' ? customPassage.trim() : (activeDoc.extracted_text || '').trim();

    if (!textToSimplify) {
      setError('Please provide or select educational text to simplify.');
      return;
    }

    setError('');
    setSimplifying(true);
    try {
      const { data } = await api.post('/ai/simplify', {
        document_id: activeDoc.id,
        text: textToSimplify,
      });
      setResult(data.simplification);
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          'AI simplification failed. Verify GEMINI_API_KEY is configured on the Flask backend.'
        )
      );
    } finally {
      setSimplifying(false);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">AI Text Simplification</h1>
          <p className="page-subtitle">
            Powered by Google Gemini on the Flask backend: simplifies vocabulary, shortens sentences,
            explains difficult words, and extracts key concepts without altering meaning.
          </p>
        </div>
        {activeDoc && (
          <Link to={`/reader/${activeDoc.id}`} className="btn btn-secondary btn-sm">
            <BookOpen size={15} /> Open in Accessible Reader
          </Link>
        )}
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {docs.length === 0 && !loadingDoc ? (
        <div className="card" style={{ textAlign: 'center', padding: '44px 24px' }}>
          <Sparkles size={34} color="var(--accent)" style={{ marginBottom: '12px' }} />
          <h2 className="card-title">Upload a document to simplify</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Upload your PDF study notes first, then select all or part of the text to simplify.
          </p>
          <Link to="/upload" className="btn btn-primary">
            Upload PDF Notes
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div className="card">
            <div className="grid-2" style={{ alignItems: 'end' }}>
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label className="form-label" htmlFor="simplify-doc-select">
                  1. Select Uploaded Document
                </label>
                <select
                  id="simplify-doc-select"
                  className="form-select"
                  value={docId || ''}
                  onChange={(e) => navigate(`/simplify/${e.target.value}`)}
                >
                  {docs.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.filename} ({d.word_count} words)
                    </option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className={`btn btn-sm ${selectionMode === 'all' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setSelectionMode('all')}
                >
                  Use Entire Document
                </button>
                <button
                  type="button"
                  className={`btn btn-sm ${selectionMode === 'custom' ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setSelectionMode('custom')}
                >
                  Select Part of Text
                </button>
                <button
                  type="button"
                  className="btn btn-accent"
                  onClick={handleSimplify}
                  disabled={simplifying || loadingDoc || !activeDoc?.extracted_text}
                  style={{ marginLeft: 'auto' }}
                >
                  <Sparkles size={16} />
                  <span>{simplifying ? 'Simplifying with Gemini...' : 'Simplify Text'}</span>
                </button>
              </div>
            </div>

            {selectionMode === 'custom' && (
              <div className="form-group" style={{ marginTop: '16px', marginBottom: 0 }}>
                <label className="form-label" htmlFor="simplify-passage-input">
                  2. Edit or trim the passage you want simplified
                </label>
                <textarea
                  id="simplify-passage-input"
                  className="form-textarea"
                  rows={6}
                  value={customPassage}
                  onChange={(e) => setCustomPassage(e.target.value)}
                />
              </div>
            )}
          </div>

          {/* Original vs Simplified View */}
          <div className="grid-2">
            <div className="card">
              <h2 className="card-title">Original Extracted Text</h2>
              <div
                className="accessible-reading-surface"
                style={{ maxHeight: '420px', overflowY: 'auto', whiteSpace: 'pre-wrap' }}
              >
                {selectionMode === 'custom'
                  ? customPassage
                  : activeDoc?.extracted_text || 'No extracted text available.'}
              </div>
            </div>

            <div className="card">
              <h2 className="card-title">Simplified Text</h2>
              {simplifying ? (
                <div style={{ padding: '24px', color: 'var(--text-secondary)' }}>
                  Analysing concepts and rewriting into clear, accessible language...
                </div>
              ) : result?.simplified_text ? (
                <div
                  className="accessible-reading-surface"
                  style={{ maxHeight: '420px', overflowY: 'auto', whiteSpace: 'pre-wrap' }}
                >
                  {result.simplified_text}
                </div>
              ) : (
                <p style={{ color: 'var(--text-muted)' }}>
                  Click <strong>Simplify Text</strong> to generate an accessible version here.
                </p>
              )}
            </div>
          </div>

          {result && (
            <div className="grid-2">
              <div className="card">
                <h2 className="card-title">Difficult Word Explanations</h2>
                {result.difficult_words?.length ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {result.difficult_words.map((item, idx) => (
                      <div
                        key={idx}
                        style={{
                          padding: '12px',
                          borderRadius: '8px',
                          backgroundColor: 'var(--bg-subtle)',
                        }}
                      >
                        <div style={{ fontWeight: 700, color: 'var(--primary)' }}>{item.word}</div>
                        <div style={{ fontSize: '0.92rem', marginTop: '4px' }}>
                          {item.simple_explanation}
                        </div>
                        {item.example && (
                          <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                            Example: {item.example}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ color: 'var(--text-muted)', margin: 0 }}>No difficult terms listed.</p>
                )}
              </div>

              <div className="card">
                <h2 className="card-title">Important Keywords & Summary</h2>
                {result.reading_summary && (
                  <p style={{ color: 'var(--text-secondary)', marginTop: 0 }}>
                    {result.reading_summary}
                  </p>
                )}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {(result.key_concepts || []).map((kw, idx) => (
                    <span key={idx} className="badge badge-accent">
                      <Tag size={12} /> {kw}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
