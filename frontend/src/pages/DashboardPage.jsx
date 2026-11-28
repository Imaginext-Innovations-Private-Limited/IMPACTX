import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen,
  CheckSquare,
  FileText,
  Headphones,
  Sliders,
  Sparkles,
  Upload,
  TrendingUp,
} from 'lucide-react';
import api, { getErrorMessage } from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useAccessibility } from '../context/AccessibilityContext';

export default function DashboardPage() {
  const { user } = useAuth();
  const { prefs } = useAccessibility();
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    api
      .get('/progress')
      .then(({ data }) => {
        if (active) setProgress(data);
      })
      .catch((err) => {
        if (active) setError(getErrorMessage(err, 'Could not load dashboard summary.'));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const stats = progress?.stats || {
    documents_uploaded: 0,
    documents_simplified: 0,
    transcripts_saved: 0,
    practice_attempts: 0,
    average_score: 0,
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Welcome back, {user?.full_name}</h1>
          <p className="page-subtitle">
            Your inclusive learning workspace is ready with your saved accessibility preferences.
          </p>
        </div>
        <Link to="/upload" className="btn btn-primary">
          <Upload size={17} />
          <span>Upload New Notes</span>
        </Link>
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {/* Stats Summary */}
      <div className="grid-4" style={{ marginBottom: '22px' }}>
        <div className="card">
          <div style={{ color: 'var(--text-muted)', fontSize: '0.84rem', fontWeight: 600 }}>
            Uploaded Documents
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, marginTop: '6px' }}>
            {loading ? '—' : stats.documents_uploaded}
          </div>
        </div>

        <div className="card">
          <div style={{ color: 'var(--text-muted)', fontSize: '0.84rem', fontWeight: 600 }}>
            Simplified Notes
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, marginTop: '6px' }}>
            {loading ? '—' : stats.documents_simplified}
          </div>
        </div>

        <div className="card">
          <div style={{ color: 'var(--text-muted)', fontSize: '0.84rem', fontWeight: 600 }}>
            Practice Attempts
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, marginTop: '6px' }}>
            {loading ? '—' : stats.practice_attempts}
          </div>
        </div>

        <div className="card">
          <div style={{ color: 'var(--text-muted)', fontSize: '0.84rem', fontWeight: 600 }}>
            Average Practice Score
          </div>
          <div style={{ fontSize: '1.85rem', fontWeight: 700, marginTop: '6px', color: 'var(--primary)' }}>
            {loading ? '—' : `${stats.average_score}%`}
          </div>
        </div>
      </div>

      {/* Accessibility Profile + User Summary */}
      <div className="grid-2" style={{ marginBottom: '22px' }}>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h2 className="card-title" style={{ margin: 0 }}>Accessibility Mode Summary</h2>
            <Link to="/settings/accessibility" className="btn btn-secondary btn-sm">
              <Sliders size={14} /> Customize
            </Link>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '14px' }}>
            {(prefs.modes || []).length > 0 ? (
              prefs.modes.map((m) => (
                <span key={m} className="badge badge-primary">
                  {m.replace('_', ' ')} mode
                </span>
              ))
            ) : (
              <span className="badge">No specific mode selected (Standard)</span>
            )}
          </div>
          <div style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
            <div>Font Size: <strong>{prefs.font_size}px</strong></div>
            <div>Font Style: <strong>{prefs.font_style}</strong></div>
            <div>Line Spacing: <strong>{prefs.line_spacing}</strong></div>
            <div>High Contrast: <strong>{prefs.high_contrast ? 'On' : 'Off'}</strong></div>
            <div>Theme: <strong>{prefs.theme}</strong></div>
            <div>Reading Zoom: <strong>{prefs.zoom}%</strong></div>
          </div>
        </div>

        <div className="card">
          <h2 className="card-title">Student Profile & Learning Progress</h2>
          <p style={{ margin: '0 0 12px', color: 'var(--text-secondary)', fontSize: '0.92rem' }}>
            Signed in as <strong>{user?.full_name}</strong> ({user?.email})
          </p>
          <div style={{ marginBottom: '12px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.86rem', marginBottom: '6px' }}>
              <span>Simplification Coverage</span>
              <span>
                {stats.documents_uploaded > 0
                  ? `${Math.round((stats.documents_simplified / stats.documents_uploaded) * 100)}%`
                  : '0%'}
              </span>
            </div>
            <div style={{ height: '8px', backgroundColor: 'var(--bg-subtle)', borderRadius: '999px', overflow: 'hidden' }}>
              <div
                style={{
                  height: '100%',
                  width: `${
                    stats.documents_uploaded > 0
                      ? Math.round((stats.documents_simplified / stats.documents_uploaded) * 100)
                      : 0
                  }%`,
                  backgroundColor: 'var(--primary)',
                }}
              />
            </div>
          </div>
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
            <Link to="/progress" className="btn btn-secondary btn-sm">
              <TrendingUp size={14} /> View Progress & Revision Plan
            </Link>
            <Link to="/profile" className="btn btn-secondary btn-sm">
              Edit Profile
            </Link>
          </div>
        </div>
      </div>

      {/* Quick Access Feature Cards */}
      <h2 style={{ fontSize: '1.15rem', fontWeight: 700, margin: '0 0 12px' }}>
        Quick Access Tools
      </h2>
      <div className="grid-4" style={{ marginBottom: '24px' }}>
        <Link to="/reader" className="card">
          <BookOpen size={20} color="var(--primary)" />
          <div className="card-title" style={{ marginTop: '10px' }}>Accessible Reader</div>
          <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
            Read original or simplified notes with custom fonts, contrast, and audio.
          </p>
        </Link>

        <Link to="/simplify" className="card">
          <Sparkles size={20} color="var(--accent)" />
          <div className="card-title" style={{ marginTop: '10px' }}>AI Simplification</div>
          <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
            Simplify complex passages, define tricky terms, and extract key concepts.
          </p>
        </Link>

        <Link to="/audio-captions" className="card">
          <Headphones size={20} color="var(--success)" />
          <div className="card-title" style={{ marginTop: '10px' }}>Audio & Captions</div>
          <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
            Listen with Text-to-Speech or record live speech captions & transcripts.
          </p>
        </Link>

        <Link to="/practice" className="card">
          <CheckSquare size={20} color="var(--primary)" />
          <div className="card-title" style={{ marginTop: '10px' }}>Practice Centre</div>
          <p style={{ margin: 0, fontSize: '0.86rem', color: 'var(--text-secondary)' }}>
            Generate personalised quizzes from your PDFs and track your scores.
          </p>
        </Link>
      </div>

      {/* Recent Documents & Recent Practice */}
      <div className="grid-2">
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h2 className="card-title" style={{ margin: 0 }}>Recent Documents</h2>
            <Link to="/documents" style={{ fontSize: '0.86rem', color: 'var(--primary)', fontWeight: 600 }}>
              View all
            </Link>
          </div>
          {progress?.recent_documents?.length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {progress.recent_documents.map((doc) => (
                <div
                  key={doc.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    backgroundColor: 'var(--bg-subtle)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                    <FileText size={16} color="var(--primary)" />
                    <span style={{ fontWeight: 500, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {doc.filename}
                    </span>
                  </div>
                  <Link to={`/reader/${doc.id}`} className="btn btn-secondary btn-sm">
                    Open
                  </Link>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', margin: 0 }}>
              No documents uploaded yet. Upload your first PDF study notes to get started.
            </p>
          )}
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h2 className="card-title" style={{ margin: 0 }}>Recent Practice Activities</h2>
            <Link to="/practice" style={{ fontSize: '0.86rem', color: 'var(--primary)', fontWeight: 600 }}>
              Open Practice
            </Link>
          </div>
          {progress?.recent_attempts?.length ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {progress.recent_attempts.map((att) => (
                <div
                  key={att.id}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px 12px',
                    borderRadius: '8px',
                    backgroundColor: 'var(--bg-subtle)',
                  }}
                >
                  <div>
                    <div style={{ fontWeight: 600, fontSize: '0.92rem' }}>{att.title}</div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {att.correct_count}/{att.total_questions} correct
                    </div>
                  </div>
                  <span className="badge badge-primary">{att.score_percent}%</span>
                </div>
              ))}
            </div>
          ) : (
            <p style={{ color: 'var(--text-muted)', margin: 0 }}>
              No practice quizzes completed yet. Try generating questions from an uploaded PDF.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
