import React, { useEffect, useState } from 'react';
import { AlertCircle, CalendarCheck, Sparkles, TrendingUp } from 'lucide-react';
import api, { getErrorMessage } from '../api/client';

export default function ProgressPage() {
  const [progress, setProgress] = useState(null);
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [generatingPlan, setGeneratingPlan] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get('/progress')
      .then(({ data }) => {
        setProgress(data);
        setPlan(data.latest_revision_plan || null);
      })
      .catch((err) => setError(getErrorMessage(err, 'Failed to load progress.')))
      .finally(() => setLoading(false));
  }, []);

  const handleGeneratePlan = async () => {
    setError('');
    setGeneratingPlan(true);
    try {
      const { data } = await api.post('/ai/revision-plan');
      setPlan(data.revision_plan);
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          'Could not generate revision plan. Verify GEMINI_API_KEY is configured.'
        )
      );
    } finally {
      setGeneratingPlan(false);
    }
  };

  const stats = progress?.stats || {};

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Learning Progress & Revision Plans</h1>
          <p className="page-subtitle">
            Review your study activity, practice scores, and generate a personalised Gemini revision plan.
          </p>
        </div>
        <button
          type="button"
          className="btn btn-primary"
          onClick={handleGeneratePlan}
          disabled={generatingPlan}
        >
          <Sparkles size={16} />
          <span>{generatingPlan ? 'Generating Plan...' : 'Generate AI Revision Plan'}</span>
        </button>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="card">Loading learning progress...</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div className="grid-4">
            <div className="card">
              <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>Documents</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{stats.documents_uploaded || 0}</div>
            </div>
            <div className="card">
              <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>Simplified</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{stats.documents_simplified || 0}</div>
            </div>
            <div className="card">
              <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>Saved Transcripts</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700 }}>{stats.transcripts_saved || 0}</div>
            </div>
            <div className="card">
              <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)' }}>Average Score</div>
              <div style={{ fontSize: '1.75rem', fontWeight: 700, color: 'var(--primary)' }}>
                {stats.average_score || 0}%
              </div>
            </div>
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <CalendarCheck size={20} color="var(--accent)" />
              <h2 className="card-title" style={{ margin: 0 }}>
                {plan ? plan.plan_title : 'Personalised Learning & Revision Plan'}
              </h2>
            </div>

            {plan ? (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                <p style={{ margin: 0, color: 'var(--text-secondary)' }}>{plan.summary}</p>

                {plan.focus_areas?.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    {plan.focus_areas.map((area, idx) => (
                      <span key={idx} className="badge badge-accent">
                        {area}
                      </span>
                    ))}
                  </div>
                )}

                <div className="grid-2">
                  {(plan.daily_steps || []).map((step, idx) => (
                    <div
                      key={idx}
                      style={{
                        padding: '14px',
                        borderRadius: '10px',
                        backgroundColor: 'var(--bg-subtle)',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
                        <strong>
                          Step {step.step_number || idx + 1}: {step.title}
                        </strong>
                        <span className="badge badge-primary">{step.duration_minutes || 15} min</span>
                      </div>
                      <p style={{ margin: 0, fontSize: '0.92rem', color: 'var(--text-secondary)' }}>
                        {step.activity}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)', margin: 0 }}>
                Click <strong>Generate AI Revision Plan</strong> to get a structured, accessible
                revision schedule tailored to your uploaded documents and quiz results.
              </p>
            )}
          </div>

          <div className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
              <TrendingUp size={18} color="var(--primary)" />
              <h2 className="card-title" style={{ margin: 0 }}>Recent Practice Performance</h2>
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
                      padding: '12px',
                      borderRadius: '8px',
                      backgroundColor: 'var(--bg-subtle)',
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600 }}>{att.title}</div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                        {att.document_filename} • {att.correct_count}/{att.total_questions} correct
                      </div>
                    </div>
                    <span className="badge badge-primary">{att.score_percent}%</span>
                  </div>
                ))}
              </div>
            ) : (
              <p style={{ color: 'var(--text-muted)', margin: 0 }}>No practice attempts recorded yet.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
