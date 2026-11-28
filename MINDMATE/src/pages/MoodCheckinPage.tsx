import React, { useEffect, useState } from 'react';
import {
  CloudRain,
  Flame,
  Heart,
  Meh,
  Smile,
  Sparkles,
  Trash2,
} from 'lucide-react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { MoodCheckin, MoodOption } from '../types';
import { apiFetch } from '../api';

const MOOD_CARDS: Array<{
  label: MoodOption;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  tone: string;
}> = [
  { label: 'Happy', description: 'Upbeat & motivated', icon: Sparkles, tone: 'bg-[#ECFDF5] text-teal-800 border-teal-200' },
  { label: 'Calm', description: 'Steady & grounded', icon: Heart, tone: 'bg-[#EFF6FF] text-sky-800 border-sky-200' },
  { label: 'Neutral', description: 'Balanced, getting by', icon: Meh, tone: 'bg-slate-50 text-slate-800 border-slate-200' },
  { label: 'Stressed', description: 'Pressured by workload', icon: Flame, tone: 'bg-amber-50 text-amber-800 border-amber-200' },
  { label: 'Anxious', description: 'Restless or worried', icon: Smile, tone: 'bg-[#F3F0FF] text-indigo-800 border-indigo-200' },
  { label: 'Sad', description: 'Low or drained', icon: CloudRain, tone: 'bg-rose-50 text-rose-800 border-rose-200' },
];

export function MoodCheckinPage() {
  const [selectedMood, setSelectedMood] = useState<MoodOption>('Calm');
  const [stressLevel, setStressLevel] = useState(4);
  const [energyLevel, setEnergyLevel] = useState(7);
  const [note, setNote] = useState('');
  const [checkins, setCheckins] = useState<MoodCheckin[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const loadCheckins = async () => {
    try {
      const res = await apiFetch<{ checkins: MoodCheckin[] }>('/api/moods');
      setCheckins(res.checkins);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCheckins();
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setFeedback(null);
    try {
      await apiFetch('/api/moods', {
        method: 'POST',
        body: JSON.stringify({
          mood: selectedMood,
          stress_level: stressLevel,
          energy_level: energyLevel,
          note,
        }),
      });
      setNote('');
      setFeedback({ type: 'success', text: 'Your mood check-in has been saved privately.' });
      await loadCheckins();
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Unable to save check-in.',
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await apiFetch(`/api/moods/${id}`, { method: 'DELETE' });
      setCheckins((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      setFeedback({
        type: 'error',
        text: err instanceof Error ? err.message : 'Unable to delete entry.',
      });
    }
  };

  const chartData = [...checkins]
    .slice(0, 12)
    .reverse()
    .map((c) => ({
      date: new Date(c.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }),
      stress: c.stress_level,
      energy: c.energy_level,
      mood: c.mood,
    }));

  return (
    <div className="space-y-6">
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Check-in Form */}
        <form
          onSubmit={handleSubmit}
          className="lg:col-span-6 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-5"
        >
          <div>
            <h2 className="font-display text-xl font-semibold text-slate-900">How are you feeling right now?</h2>
            <p className="text-sm text-slate-500 mt-1">
              Check-ins stay private in your personal wellbeing log.
            </p>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
            {MOOD_CARDS.map((item) => {
              const Icon = item.icon;
              const active = selectedMood === item.label;
              return (
                <button
                  key={item.label}
                  type="button"
                  onClick={() => setSelectedMood(item.label)}
                  className={`p-3.5 rounded-xl border text-left transition-all ${
                    active
                      ? 'border-[#5B4FE9] bg-[#F3F0FF] ring-2 ring-[#5B4FE9]/20'
                      : 'border-slate-200 bg-white hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <Icon className={`w-4 h-4 ${active ? 'text-[#5B4FE9]' : 'text-slate-500'}`} />
                    <span className="text-sm font-semibold text-slate-900">{item.label}</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">{item.description}</p>
                </button>
              );
            })}
          </div>

          <div className="grid sm:grid-cols-2 gap-4 pt-1">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70 space-y-2">
              <div className="flex items-center justify-between text-xs font-medium">
                <label htmlFor="stress-slider" className="text-slate-700">Current Stress Level</label>
                <span className="font-mono-tabular font-semibold text-slate-900">{stressLevel} / 10</span>
              </div>
              <input
                id="stress-slider"
                type="range"
                min={1}
                max={10}
                value={stressLevel}
                onChange={(e) => setStressLevel(Number(e.target.value))}
                className="w-full accent-[#5B4FE9]"
              />
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>Low (1)</span>
                <span>High (10)</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70 space-y-2">
              <div className="flex items-center justify-between text-xs font-medium">
                <label htmlFor="energy-slider" className="text-slate-700">Current Energy Level</label>
                <span className="font-mono-tabular font-semibold text-slate-900">{energyLevel} / 10</span>
              </div>
              <input
                id="energy-slider"
                type="range"
                min={1}
                max={10}
                value={energyLevel}
                onChange={(e) => setEnergyLevel(Number(e.target.value))}
                className="w-full accent-teal-600"
              />
              <div className="flex justify-between text-[11px] text-slate-400">
                <span>Drained (1)</span>
                <span>Energized (10)</span>
              </div>
            </div>
          </div>

          <div>
            <label htmlFor="mood-note" className="block text-xs font-medium text-slate-700 mb-1.5">
              Short Reflection (Optional)
            </label>
            <textarea
              id="mood-note"
              rows={3}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="What's contributing to how you feel today? (exams, sleep, friends, workload...)"
              className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
            />
          </div>

          {feedback && (
            <div
              className={`p-3 rounded-xl text-sm ${
                feedback.type === 'success'
                  ? 'bg-[#ECFDF5] text-teal-900 border border-teal-200'
                  : 'bg-rose-50 text-rose-800 border border-rose-200'
              }`}
            >
              {feedback.text}
            </div>
          )}

          <button
            type="submit"
            disabled={saving}
            className="w-full py-3 rounded-xl text-sm font-semibold text-white bg-[#5B4FE9] hover:bg-[#4C40D4] transition-colors disabled:opacity-60"
          >
            {saving ? 'Saving Check-in...' : 'Save Mood Check-in'}
          </button>
        </form>

        {/* Trend Chart */}
        <div className="lg:col-span-6 bg-white rounded-2xl border border-slate-200/80 p-6 flex flex-col justify-between space-y-4">
          <div>
            <h3 className="font-display text-lg font-semibold text-slate-900">Stress vs. Energy Trend</h3>
            <p className="text-xs text-slate-500">Recent check-in pattern over time</p>
          </div>

          <div className="h-72 w-full">
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#64748B' }} />
                  <YAxis domain={[1, 10]} tick={{ fontSize: 12, fill: '#64748B' }} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="stress" name="Stress Level" stroke="#5B4FE9" strokeWidth={2.5} dot={{ r: 4 }} />
                  <Line type="monotone" dataKey="energy" name="Energy Level" stroke="#0D9488" strokeWidth={2.5} dot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center bg-slate-50 rounded-xl text-sm text-slate-500">
                Log at least one check-in to visualize your trend.
              </div>
            )}
          </div>
        </div>
      </div>

      {/* History Timeline */}
      <section className="bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-lg font-semibold text-slate-900">Recent Check-in History</h3>
          <span className="text-xs text-slate-500 font-mono-tabular">{checkins.length} entries</span>
        </div>

        {loading ? (
          <p className="text-sm text-slate-500">Loading history...</p>
        ) : checkins.length === 0 ? (
          <p className="text-sm text-slate-500">No mood check-ins saved yet.</p>
        ) : (
          <div className="divide-y divide-slate-100">
            {checkins.map((item) => (
              <div key={item.id} className="py-3.5 flex items-start justify-between gap-4">
                <div className="space-y-1 min-w-0">
                  <div className="flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    <span className="font-semibold text-sm text-slate-900">{item.mood}</span>
                    <span aria-hidden="true">·</span>
                    <span className="font-mono-tabular">Stress {item.stress_level}/10</span>
                    <span aria-hidden="true">·</span>
                    <span className="font-mono-tabular">Energy {item.energy_level}/10</span>
                    <span aria-hidden="true">·</span>
                    <span>{new Date(item.created_at).toLocaleString()}</span>
                  </div>
                  {item.note && <p className="text-sm text-slate-700">{item.note}</p>}
                </div>
                <button
                  type="button"
                  onClick={() => handleDelete(item.id)}
                  className="p-2 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition-colors shrink-0"
                  aria-label="Delete mood check-in"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
