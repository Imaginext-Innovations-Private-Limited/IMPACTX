import React, { useEffect, useState } from 'react';
import { CheckCircle, Pause, Play, RotateCcw, Timer } from 'lucide-react';
import type { FocusSession } from '../types';
import { apiFetch } from '../api';

type TimerMode = 'focus' | 'short_break' | 'long_break';

const MODE_CONFIG: Record<TimerMode, { label: string; minutes: number; hint: string }> = {
  focus: { label: 'Focus Sprint', minutes: 25, hint: 'Single-task gently for 25 minutes.' },
  short_break: { label: 'Short Break', minutes: 5, hint: 'Stand up, stretch, and rest your eyes.' },
  long_break: { label: 'Long Break', minutes: 15, hint: 'Hydrate, walk around, and step away from screens.' },
};

export function PomodoroPage() {
  const [mode, setMode] = useState<TimerMode>('focus');
  const [secondsLeft, setSecondsLeft] = useState(MODE_CONFIG.focus.minutes * 60);
  const [running, setRunning] = useState(false);
  const [subject, setSubject] = useState('Algorithms & Complexity');
  const [sessions, setSessions] = useState<FocusSession[]>([]);
  const [statusMessage, setStatusMessage] = useState('');

  const loadSessions = async () => {
    try {
      const res = await apiFetch<{ sessions: FocusSession[] }>('/api/focus');
      setSessions(res.sessions);
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const recordSession = async (completedMode: TimerMode) => {
    try {
      const res = await apiFetch<{ session: FocusSession }>('/api/focus', {
        method: 'POST',
        body: JSON.stringify({
          mode: completedMode,
          duration_minutes: MODE_CONFIG[completedMode].minutes,
          subject: completedMode === 'focus' ? subject : 'Rest & Recovery',
        }),
      });
      setSessions((prev) => [res.session, ...prev]);
      setStatusMessage(
        completedMode === 'focus'
          ? `Recorded ${MODE_CONFIG.focus.minutes}-minute focus session for ${subject}.`
          : `Completed ${MODE_CONFIG[completedMode].label}!`
      );
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (!running) return;
    const interval = window.setInterval(() => {
      setSecondsLeft((prev) => {
        if (prev <= 1) {
          setRunning(false);
          recordSession(mode);
          return MODE_CONFIG[mode].minutes * 60;
        }
        return prev - 1;
      });
    }, 1000);
    return () => window.clearInterval(interval);
  }, [running, mode, subject]);

  const switchMode = (nextMode: TimerMode) => {
    setRunning(false);
    setMode(nextMode);
    setSecondsLeft(MODE_CONFIG[nextMode].minutes * 60);
    setStatusMessage('');
  };

  const resetTimer = () => {
    setRunning(false);
    setSecondsLeft(MODE_CONFIG[mode].minutes * 60);
  };

  const totalSeconds = MODE_CONFIG[mode].minutes * 60;
  const progress = Math.max(0, Math.min(1, (totalSeconds - secondsLeft) / totalSeconds));
  const radius = 92;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - progress);

  const mins = String(Math.floor(secondsLeft / 60)).padStart(2, '0');
  const secs = String(secondsLeft % 60).padStart(2, '0');

  const focusSessionsOnly = sessions.filter((s) => s.mode === 'focus');
  const totalFocusMinutes = focusSessionsOnly.reduce((sum, s) => sum + s.duration_minutes, 0);

  return (
    <div className="grid lg:grid-cols-12 gap-6">
      {/* Main Timer Card */}
      <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 flex flex-col items-center text-center space-y-6">
        <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-xl">
          {(Object.keys(MODE_CONFIG) as TimerMode[]).map((key) => (
            <button
              key={key}
              type="button"
              onClick={() => switchMode(key)}
              className={`px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap ${
                mode === key ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {MODE_CONFIG[key].label} ({MODE_CONFIG[key].minutes}m)
            </button>
          ))}
        </div>

        {/* Circular SVG Timer */}
        <div className="relative w-56 h-56 flex items-center justify-center">
          <svg className="w-full h-full -rotate-90" viewBox="0 0 220 220" aria-hidden="true">
            <circle cx="110" cy="110" r={radius} fill="none" stroke="#E2E8F0" strokeWidth="10" />
            <circle
              cx="110"
              cy="110"
              r={radius}
              fill="none"
              stroke={mode === 'focus' ? '#5B4FE9' : '#0D9488'}
              strokeWidth="10"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={strokeDashoffset}
              className="transition-all duration-300"
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span className="font-mono-tabular text-4xl sm:text-5xl font-semibold text-slate-900 tracking-tight">
              {mins}:{secs}
            </span>
            <span className="text-xs text-slate-500 mt-1">{MODE_CONFIG[mode].label}</span>
          </div>
        </div>

        <p className="text-sm text-slate-600">{MODE_CONFIG[mode].hint}</p>

        {mode === 'focus' && (
          <div className="w-full max-w-xs text-left">
            <label htmlFor="focus-subject" className="block text-xs font-medium text-slate-600 mb-1">
              Study Subject
            </label>
            <input
              id="focus-subject"
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="w-full px-3.5 py-2 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
            />
          </div>
        )}

        <div className="flex flex-wrap items-center justify-center gap-3">
          <button
            type="button"
            onClick={() => setRunning((r) => !r)}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white bg-[#5B4FE9] hover:bg-[#4C40D4] transition-colors"
          >
            {running ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            <span>{running ? 'Pause' : 'Start Timer'}</span>
          </button>

          <button
            type="button"
            onClick={resetTimer}
            className="inline-flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Reset</span>
          </button>

          <button
            type="button"
            onClick={() => {
              setRunning(false);
              recordSession(mode);
              setSecondsLeft(MODE_CONFIG[mode].minutes * 60);
            }}
            className="inline-flex items-center gap-2 px-4 py-3 rounded-xl text-sm font-medium text-teal-800 bg-[#ECFDF5] hover:bg-[#D1FAE5] transition-colors"
          >
            <CheckCircle className="w-4 h-4" />
            <span>Complete & Log</span>
          </button>
        </div>

        {statusMessage && (
          <p className="text-sm font-medium text-teal-700" role="status">
            {statusMessage}
          </p>
        )}
      </div>

      {/* Session History */}
      <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-5">
        <div className="grid grid-cols-2 gap-3">
          <div className="p-4 rounded-xl bg-[#F3F0FF]/70 border border-[#DDD6FE]/70">
            <p className="text-xs text-slate-600">Focus Sessions</p>
            <p className="font-mono-tabular text-2xl font-semibold text-slate-900 mt-1">
              {focusSessionsOnly.length}
            </p>
          </div>
          <div className="p-4 rounded-xl bg-[#ECFDF5]/70 border border-teal-200/70">
            <p className="text-xs text-slate-600">Total Focus Time</p>
            <p className="font-mono-tabular text-2xl font-semibold text-slate-900 mt-1">
              {totalFocusMinutes}m
            </p>
          </div>
        </div>

        <div>
          <h3 className="font-display text-lg font-semibold text-slate-900 mb-3">Recent Completed Sessions</h3>
          {sessions.length === 0 ? (
            <div className="p-6 text-center rounded-xl bg-slate-50 text-sm text-slate-500">
              Complete a Pomodoro sprint to see your session log here.
            </div>
          ) : (
            <ul className="divide-y divide-slate-100 max-h-[340px] overflow-y-auto">
              {sessions.map((s) => (
                <li key={s.id} className="py-3 flex items-center justify-between gap-3 text-sm">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <Timer className="w-4 h-4 text-[#5B4FE9] shrink-0" />
                    <div className="min-w-0">
                      <p className="font-medium text-slate-900 truncate">{s.subject}</p>
                      <p className="text-xs text-slate-500">
                        {s.mode === 'focus' ? 'Focus Sprint' : s.mode === 'short_break' ? 'Short Break' : 'Long Break'} ·{' '}
                        {new Date(s.completed_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <span className="font-mono-tabular text-xs font-semibold text-slate-700 shrink-0">
                    {s.duration_minutes} min
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
