import React, { useEffect, useState } from 'react';
import { Download, Lock, ShieldCheck, Trash2 } from 'lucide-react';
import { apiFetch } from '../api';
import type { MoodCheckin } from '../types';

interface PrivacyPrefs {
  privacy_anonymous_community: number;
  privacy_include_insights: number;
  privacy_retention_days: number;
}

interface DataCounts {
  moodCheckins: number;
  studyTasks: number;
  chatMessages: number;
  focusSessions: number;
}

export function PrivacyPage() {
  const [prefs, setPrefs] = useState<PrivacyPrefs>({
    privacy_anonymous_community: 1,
    privacy_include_insights: 1,
    privacy_retention_days: 90,
  });
  const [counts, setCounts] = useState<DataCounts>({
    moodCheckins: 0,
    studyTasks: 0,
    chatMessages: 0,
    focusSessions: 0,
  });
  const [checkins, setCheckins] = useState<MoodCheckin[]>([]);
  const [confirmScope, setConfirmScope] = useState<'moods' | 'chat' | 'all' | null>(null);
  const [feedback, setFeedback] = useState('');
  const [loading, setLoading] = useState(true);

  const loadPrivacy = async () => {
    try {
      const [privRes, moodRes] = await Promise.all([
        apiFetch<{ preferences: PrivacyPrefs; counts: DataCounts }>('/api/privacy'),
        apiFetch<{ checkins: MoodCheckin[] }>('/api/moods'),
      ]);
      setPrefs(privRes.preferences);
      setCounts(privRes.counts);
      setCheckins(moodRes.checkins);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPrivacy();
  }, []);

  const savePreferences = async (nextPrefs: PrivacyPrefs) => {
    setPrefs(nextPrefs);
    setFeedback('');
    try {
      await apiFetch('/api/privacy', {
        method: 'PUT',
        body: JSON.stringify({
          privacy_anonymous_community: Boolean(nextPrefs.privacy_anonymous_community),
          privacy_include_insights: Boolean(nextPrefs.privacy_include_insights),
          privacy_retention_days: nextPrefs.privacy_retention_days,
        }),
      });
      setFeedback('Privacy preferences saved.');
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : 'Unable to save preferences.');
    }
  };

  const handleExport = async () => {
    try {
      const data = await apiFetch<Record<string, unknown>>('/api/privacy/export');
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `mindmate-my-data-${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setFeedback('Downloaded your personal wellbeing export (JSON).');
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : 'Export failed.');
    }
  };

  const handleDeleteScope = async (scope: 'moods' | 'chat' | 'all') => {
    try {
      await apiFetch(`/api/privacy/data?scope=${scope}`, { method: 'DELETE' });
      setConfirmScope(null);
      setFeedback(
        scope === 'moods'
          ? 'All mood check-in records were deleted.'
          : scope === 'chat'
          ? 'Your AI Companion conversation history was cleared.'
          : 'All mood check-ins, AI chats, and focus logs were deleted.'
      );
      await loadPrivacy();
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : 'Delete failed.');
    }
  };

  if (loading) {
    return <p className="text-sm text-slate-500">Loading privacy settings...</p>;
  }

  return (
    <div className="space-y-6">
      {/* Transparent Data Explanation */}
      <section className="bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4">
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#EDE9FE] text-[#5B4FE9] flex items-center justify-center shrink-0">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="font-display text-xl font-semibold text-slate-900">
              How MINDMATE Protects Your Privacy
            </h2>
            <p className="text-sm text-slate-600 mt-1 leading-relaxed">
              Your wellbeing records are stored in an isolated SQLite database tied strictly to your authenticated account. Other students cannot view your mood check-ins, stress scores, or AI companion chats.
            </p>
          </div>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3 pt-2">
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70">
            <p className="text-xs text-slate-500">Mood Check-ins Stored</p>
            <p className="font-mono-tabular text-xl font-semibold text-slate-900 mt-1">{counts.moodCheckins}</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70">
            <p className="text-xs text-slate-500">AI Chat Messages</p>
            <p className="font-mono-tabular text-xl font-semibold text-slate-900 mt-1">{counts.chatMessages}</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70">
            <p className="text-xs text-slate-500">Study Tasks</p>
            <p className="font-mono-tabular text-xl font-semibold text-slate-900 mt-1">{counts.studyTasks}</p>
          </div>
          <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70">
            <p className="text-xs text-slate-500">Focus Sessions</p>
            <p className="font-mono-tabular text-xl font-semibold text-slate-900 mt-1">{counts.focusSessions}</p>
          </div>
        </div>
      </section>

      <div className="grid lg:grid-cols-12 gap-6">
        {/* Privacy Controls */}
        <section className="lg:col-span-6 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-5">
          <h3 className="font-display text-lg font-semibold text-slate-900">Privacy Preferences</h3>

          <label className="flex items-start justify-between gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200/70 cursor-pointer">
            <div>
              <p className="text-sm font-semibold text-slate-900">Anonymous Community Alias</p>
              <p className="text-xs text-slate-600 mt-0.5">
                Hide your real name in Peer Community posts and comments (uses your generated nature alias).
              </p>
            </div>
            <input
              type="checkbox"
              checked={Boolean(prefs.privacy_anonymous_community)}
              onChange={(e) =>
                savePreferences({ ...prefs, privacy_anonymous_community: e.target.checked ? 1 : 0 })
              }
              className="mt-1 w-4 h-4 accent-[#5B4FE9]"
            />
          </label>

          <label className="flex items-start justify-between gap-4 p-4 rounded-xl bg-slate-50 border border-slate-200/70 cursor-pointer">
            <div>
              <p className="text-sm font-semibold text-slate-900">Personal Wellbeing Insights</p>
              <p className="text-xs text-slate-600 mt-0.5">
                Compute gentle trend summaries on your private Dashboard & Analytics pages.
              </p>
            </div>
            <input
              type="checkbox"
              checked={Boolean(prefs.privacy_include_insights)}
              onChange={(e) =>
                savePreferences({ ...prefs, privacy_include_insights: e.target.checked ? 1 : 0 })
              }
              className="mt-1 w-4 h-4 accent-[#5B4FE9]"
            />
          </label>

          <div>
            <label htmlFor="retention-select" className="block text-xs font-medium text-slate-700 mb-1.5">
              Personal Check-in Retention Window
            </label>
            <select
              id="retention-select"
              value={prefs.privacy_retention_days}
              onChange={(e) =>
                savePreferences({ ...prefs, privacy_retention_days: Number(e.target.value) })
              }
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
            >
              <option value={30}>30 Days</option>
              <option value={90}>90 Days (Recommended)</option>
              <option value={180}>180 Days (1 Semester)</option>
              <option value={365}>365 Days (Academic Year)</option>
            </select>
          </div>

          {feedback && (
            <p className="text-xs font-medium text-teal-800 bg-[#ECFDF5] p-3 rounded-xl border border-teal-200">
              {feedback}
            </p>
          )}
        </section>

        {/* Data Export & Deletion */}
        <section className="lg:col-span-6 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-5">
          <div className="flex items-center gap-2">
            <Lock className="w-4 h-4 text-slate-600" />
            <h3 className="font-display text-lg font-semibold text-slate-900">Your Data Controls</h3>
          </div>

          <div className="p-4 rounded-xl bg-[#EFF6FF]/70 border border-sky-200/80 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-slate-900">Download Personal Archive</p>
              <p className="text-xs text-slate-600 mt-0.5">Export mood check-ins, study tasks, and focus logs as JSON.</p>
            </div>
            <button
              type="button"
              onClick={handleExport}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl text-xs font-semibold text-white bg-[#5B4FE9] hover:bg-[#4C40D4] shrink-0"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Export JSON</span>
            </button>
          </div>

          <div className="space-y-2.5 pt-2 border-t border-slate-100">
            <p className="text-xs font-semibold text-slate-700">Delete Personal Records</p>
            <div className="grid sm:grid-cols-3 gap-2">
              <button
                type="button"
                onClick={() => setConfirmScope('moods')}
                className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear Moods</span>
              </button>
              <button
                type="button"
                onClick={() => setConfirmScope('chat')}
                className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-medium text-rose-700 bg-rose-50 hover:bg-rose-100 border border-rose-200"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Clear AI Chats</span>
              </button>
              <button
                type="button"
                onClick={() => setConfirmScope('all')}
                className="inline-flex items-center justify-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-semibold text-white bg-rose-700 hover:bg-rose-800"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>Delete All Logs</span>
              </button>
            </div>

            {confirmScope && (
              <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 space-y-3 mt-2">
                <p className="text-xs font-medium text-rose-900">
                  Are you sure you want to permanently delete{' '}
                  {confirmScope === 'moods'
                    ? 'all mood check-ins'
                    : confirmScope === 'chat'
                    ? 'your AI companion history'
                    : 'all mood check-ins, AI chats, and focus logs'}
                  ? This cannot be undone.
                </p>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => handleDeleteScope(confirmScope)}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-white bg-rose-700 hover:bg-rose-800"
                  >
                    Yes, Permanently Delete
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmScope(null)}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-white border border-slate-200"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            )}
          </div>
        </section>
      </div>

      {/* View Personal Check-in Data Table */}
      <section className="bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4">
        <div>
          <h3 className="font-display text-lg font-semibold text-slate-900">
            Inspect Stored Mood Check-in Records
          </h3>
          <p className="text-xs text-slate-500">Full transparency of every private check-in stored for your account</p>
        </div>

        {checkins.length === 0 ? (
          <p className="text-sm text-slate-500">No personal mood check-in records currently stored.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-slate-200 text-slate-500">
                  <th className="py-2.5 pr-4 font-semibold">Date</th>
                  <th className="py-2.5 pr-4 font-semibold">Mood</th>
                  <th className="py-2.5 pr-4 font-semibold">Stress</th>
                  <th className="py-2.5 pr-4 font-semibold">Energy</th>
                  <th className="py-2.5 font-semibold">Reflection Note</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {checkins.map((c) => (
                  <tr key={c.id}>
                    <td className="py-2.5 pr-4 font-mono-tabular text-slate-600 whitespace-nowrap">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                    <td className="py-2.5 pr-4 font-medium text-slate-900">{c.mood}</td>
                    <td className="py-2.5 pr-4 font-mono-tabular text-slate-700">{c.stress_level}/10</td>
                    <td className="py-2.5 pr-4 font-mono-tabular text-slate-700">{c.energy_level}/10</td>
                    <td className="py-2.5 text-slate-600">{c.note || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
