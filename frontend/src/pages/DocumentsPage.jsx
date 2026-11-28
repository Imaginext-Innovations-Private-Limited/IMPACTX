import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen,
  CheckSquare,
  FileText,
  Sparkles,
  Trash2,
  Upload,
  AlertCircle,
} from 'lucide-react';
import api, { getErrorMessage } from '../api/client';

export default function DocumentsPage() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deletingId, setDeletingId] = useState('');

  const loadDocuments = async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await api.get('/documents');
      setDocuments(data.documents || []);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to load your documents.'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, []);

  const handleDelete = async (docId, filename) => {
    if (!window.confirm(`Delete "${filename}"? This cannot be undone.`)) return;
    setDeletingId(docId);
    try {
      await api.delete(`/documents/${docId}`);
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
    } catch (err) {
      setError(getErrorMessage(err, 'Could not delete document.'));
    } finally {
      setDeletingId('');
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">My Documents</h1>
          <p className="page-subtitle">
            Manage your uploaded study PDFs and launch accessible reading, simplification, or practice.
          </p>
        </div>
        <Link to="/upload" className="btn btn-primary">
          <Upload size={17} /> Upload PDF
        </Link>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="card">Loading your documents...</div>
      ) : documents.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '44px 24px' }}>
          <FileText size={36} color="var(--text-muted)" style={{ marginBottom: '12px' }} />
          <h2 className="card-title">No uploaded documents yet</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '18px' }}>
            Upload your lecture notes, handouts, or textbook chapters in PDF format.
          </p>
          <Link to="/upload" className="btn btn-primary">
            Upload First PDF
          </Link>
        </div>
      ) : (
        <div className="grid-2">
          {documents.map((doc) => (
            <div key={doc.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px' }}>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center', minWidth: 0 }}>
                  <FileText size={22} color="var(--primary)" style={{ flexShrink: 0 }} />
                  <div style={{ minWidth: 0 }}>
                    <h2
                      className="card-title"
                      style={{ margin: 0, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
                    >
                      {doc.filename}
                    </h2>
                    <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                      Uploaded {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'} •{' '}
                      {doc.page_count} page(s) • {doc.word_count} words
                    </div>
                  </div>
                </div>
                <span className={`badge ${doc.status === 'ready' ? 'badge-success' : 'badge-warning'}`}>
                  {doc.status === 'ready' ? 'Ready' : 'Needs OCR'}
                </span>
              </div>

              {doc.has_simplification && (
                <div>
                  <span className="badge badge-accent">Simplified Version Available</span>
                </div>
              )}

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: 'auto', paddingTop: '6px' }}>
                <Link to={`/reader/${doc.id}`} className="btn btn-primary btn-sm">
                  <BookOpen size={14} /> Open
                </Link>
                <Link to={`/simplify/${doc.id}`} className="btn btn-secondary btn-sm">
                  <Sparkles size={14} /> Simplify
                </Link>
                <Link to={`/practice/${doc.id}`} className="btn btn-secondary btn-sm">
                  <CheckSquare size={14} /> Practice
                </Link>
                <button
                  type="button"
                  className="btn btn-danger btn-sm"
                  style={{ marginLeft: 'auto' }}
                  disabled={deletingId === doc.id}
                  onClick={() => handleDelete(doc.id, doc.filename)}
                >
                  <Trash2 size={14} /> {deletingId === doc.id ? 'Deleting...' : 'Delete'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
