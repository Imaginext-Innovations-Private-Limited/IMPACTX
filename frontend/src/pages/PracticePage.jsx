import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { AlertCircle, CheckCircle2, CheckSquare, Sparkles, XCircle } from 'lucide-react';
import api, { getErrorMessage } from '../api/client';

export default function PracticePage() {
  const { docId } = useParams();

  const [docs, setDocs] = useState([]);
  const [selectedDocId, setSelectedDocId] = useState(docId || '');
  const [questionCount, setQuestionCount] = useState(5);
  const [difficulty, setDifficulty] = useState('mixed');
  const [selectedTypes, setSelectedTypes] = useState([
    'multiple_choice',
    'short_answer',
    'concept',
  ]);

  const [practiceSet, setPracticeSet] = useState(null);
  const [viewLayout, setViewLayout] = useState('single'); // single | list
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState({});
  const [attemptResult, setAttemptResult] = useState(null);
  const [pastAttempts, setPastAttempts] = useState([]);

  const [generating, setGenerating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api
      .get('/documents')
      .then(({ data }) => {
        const list = data.documents || [];
        setDocs(list);
        if (!selectedDocId && list.length > 0) {
          setSelectedDocId(list[0].id);
        }
      })
      .catch(() => {});

    api
      .get('/practice/attempts')
      .then(({ data }) => setPastAttempts(data.attempts || []))
      .catch(() => {});
  }, []);

  const toggleType = (type) => {
    setSelectedTypes((prev) =>
      prev.includes(type)
        ? prev.length > 1
          ? prev.filter((t) => t !== type)
          : prev
        : [...prev, type]
    );
  };

  const handleGenerate = async () => {
    if (!selectedDocId) {
      setError('Please upload and select a PDF document first.');
      return;
    }
    setError('');
    setGenerating(true);
    setAttemptResult(null);
    setAnswers({});
    setCurrentIndex(0);
    try {
      const { data } = await api.post('/practice/generate', {
        document_id: selectedDocId,
        question_count: questionCount,
        question_types: selectedTypes,
        difficulty,
      });
      setPracticeSet(data.practice_set);
    } catch (err) {
      setError(
        getErrorMessage(
          err,
          'Could not generate practice questions. Check GEMINI_API_KEY configuration.'
        )
      );
    } finally {
      setGenerating(false);
    }
  };

  const handleSubmit = async () => {
    if (!practiceSet) return;
    setError('');
    setSubmitting(true);
    try {
      const { data } = await api.post('/practice/submit', {
        practice_set_id: practiceSet.id,
        answers,
      });
      setAttemptResult(data.attempt);
      setPastAttempts((prev) => [data.attempt, ...prev]);
    } catch (err) {
      setError(getErrorMessage(err, 'Failed to evaluate your answers.'));
    } finally {
      setSubmitting(false);
    }
  };

  const questions = practiceSet?.questions || [];
  const activeQuestion = questions[currentIndex];

  const renderQuestionCard = (q, idx) => (
    <div key={q.id} className="card accessible-reading-surface" style={{ maxWidth: '100%' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginBottom: '12px' }}>
        <span className="badge badge-primary">Question {idx + 1}</span>
        <span className="badge badge-accent">{q.question_type.replace('_', ' ')}</span>
        <span className="badge">{q.difficulty}</span>
      </div>

      <h3 style={{ margin: '0 0 14px', fontSize: '1.1em' }}>{q.question_text}</h3>

      {q.question_type === 'multiple_choice' && q.options?.length > 0 ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {q.options.map((opt, oIdx) => {
            const checked = answers[q.id] === opt;
            return (
              <label
                key={oIdx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '10px',
                  padding: '12px 14px',
                  borderRadius: '8px',
                  border: `2px solid ${checked ? 'var(--primary)' : 'var(--border-color)'}`,
                  backgroundColor: checked ? 'var(--primary-soft)' : 'var(--bg-surface)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="radio"
                  name={`q-${q.id}`}
                  checked={checked}
                  onChange={() => setAnswers((prev) => ({ ...prev, [q.id]: opt }))}
                />
                <span>{opt}</span>
              </label>
            );
          })}
        </div>
      ) : (
        <textarea
          className="form-textarea"
          rows={4}
          placeholder="Type your answer in your own words..."
          value={answers[q.id] || ''}
          onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
        />
      )}
    </div>
  );

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Personalised Practice Centre</h1>
          <p className="page-subtitle">
            Generate multiple-choice, short-answer, and concept questions directly from your
            uploaded study documents.
          </p>
        </div>
      </div>

      {error && (
        <div className="alert alert-error" role="alert">
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {docs.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '44px 24px' }}>
          <CheckSquare size={34} color="var(--primary)" style={{ marginBottom: '12px' }} />
          <h2 className="card-title">Upload notes to start practising</h2>
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Practice questions are generated strictly from your uploaded PDF documents.
          </p>
          <Link to="/upload" className="btn btn-primary">
            Upload PDF Notes
          </Link>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          {/* Generator Controls */}
          <div className="card">
            <div className="grid-3">
              <div className="form-group">
                <label className="form-label" htmlFor="prac-doc-select">
                  Source Document
                </label>
                <select
                  id="prac-doc-select"
                  className="form-select"
                  value={selectedDocId}
                  onChange={(e) => setSelectedDocId(e.target.value)}
                >
                  {docs.map((d) => (
                    <option key={d.id} value={d.id}>
                      {d.filename}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="prac-count">
                  Number of Questions
                </label>
                <select
                  id="prac-count"
                  className="form-select"
                  value={questionCount}
                  onChange={(e) => setQuestionCount(parseInt(e.target.value, 10))}
                >
                  <option value={3}>3 Questions</option>
                  <option value={5}>5 Questions</option>
                  <option value={8}>8 Questions</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="prac-diff">
                  Difficulty Level
                </label>
                <select
                  id="prac-diff"
                  className="form-select"
                  value={difficulty}
                  onChange={(e) => setDifficulty(e.target.value)}
                >
                  <option value="mixed">Mixed</option>
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>
            </div>

            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                justifyContent: 'space-between',
                alignItems: 'center',
                gap: '12px',
              }}
            >
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px' }}>
                {[
                  ['multiple_choice', 'Multiple Choice'],
                  ['short_answer', 'Short Answer'],
                  ['concept', 'Concept-Based'],
                ].map(([key, label]) => (
                  <label key={key} style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                    <input
                      type="checkbox"
                      checked={selectedTypes.includes(key)}
                      onChange={() => toggleType(key)}
                    />
                    <span>{label}</span>
                  </label>
                ))}
              </div>

              <button
                type="button"
                className="btn btn-primary"
                onClick={handleGenerate}
                disabled={generating}
              >
                <Sparkles size={16} />
                <span>{generating ? 'Generating Questions...' : 'Generate Practice Set'}</span>
              </button>
            </div>
          </div>

          {/* Active Quiz */}
          {practiceSet && !attemptResult && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: '10px',
                }}
              >
                <h2 style={{ margin: 0, fontSize: '1.2rem' }}>{practiceSet.title}</h2>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    type="button"
                    className={`btn btn-sm ${viewLayout === 'single' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setViewLayout('single')}
                  >
                    One at a Time
                  </button>
                  <button
                    type="button"
                    className={`btn btn-sm ${viewLayout === 'list' ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setViewLayout('list')}
                  >
                    All Questions
                  </button>
                </div>
              </div>

              {viewLayout === 'single' && activeQuestion ? (
                <>
                  {renderQuestionCard(activeQuestion, currentIndex)}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={currentIndex === 0}
                      onClick={() => setCurrentIndex((i) => i - 1)}
                    >
                      Previous
                    </button>
                    <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
                      {currentIndex + 1} of {questions.length}
                    </span>
                    {currentIndex < questions.length - 1 ? (
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => setCurrentIndex((i) => i + 1)}
                      >
                        Next Question
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={handleSubmit}
                        disabled={submitting}
                      >
                        {submitting ? 'Evaluating...' : 'Submit Practice'}
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <>
                  {questions.map((q, idx) => renderQuestionCard(q, idx))}
                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      type="button"
                      className="btn btn-primary"
                      onClick={handleSubmit}
                      disabled={submitting}
                    >
                      {submitting ? 'Evaluating...' : 'Submit All Answers'}
                    </button>
                  </div>
                </>
              )}
            </div>
          )}

          {/* Evaluation Result */}
          {attemptResult && (
            <div className="card">
              <div
                style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  gap: '12px',
                  marginBottom: '18px',
                }}
              >
                <div>
                  <h2 className="card-title" style={{ margin: 0 }}>
                    Practice Results: {attemptResult.title}
                  </h2>
                  <p style={{ margin: '4px 0 0', color: 'var(--text-secondary)' }}>
                    You answered {attemptResult.correct_count} out of {attemptResult.total_questions}{' '}
                    questions correctly.
                  </p>
                </div>
                <span className="badge badge-primary" style={{ fontSize: '1.05rem', padding: '8px 16px' }}>
                  Score: {attemptResult.score_percent}%
                </span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {attemptResult.results.map((r, idx) => (
                  <div
                    key={r.id}
                    className="accessible-reading-surface"
                    style={{
                      maxWidth: '100%',
                      padding: '16px',
                      borderColor: r.is_correct ? 'var(--success)' : 'var(--danger)',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      {r.is_correct ? (
                        <CheckCircle2 size={18} color="var(--success)" />
                      ) : (
                        <XCircle size={18} color="var(--danger)" />
                      )}
                      <strong>
                        Q{idx + 1}: {r.question_text}
                      </strong>
                    </div>
                    <div style={{ fontSize: '0.92em', marginBottom: '4px' }}>
                      <strong>Your answer:</strong> {r.user_answer || 'No answer provided'}
                    </div>
                    <div style={{ fontSize: '0.92em', marginBottom: '4px' }}>
                      <strong>Correct answer:</strong> {r.correct_answer}
                    </div>
                    <div style={{ fontSize: '0.9em', color: 'var(--text-secondary)' }}>
                      <strong>Explanation:</strong> {r.feedback} {r.explanation}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Previous Attempts */}
          {pastAttempts.length > 0 && (
            <div className="card">
              <h2 className="card-title">Completed Practice Attempts</h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                {pastAttempts.slice(0, 6).map((att) => (
                  <div
                    key={att.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '10px 14px',
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
            </div>
          )}
        </div>
      )}
    </div>
  );
}
