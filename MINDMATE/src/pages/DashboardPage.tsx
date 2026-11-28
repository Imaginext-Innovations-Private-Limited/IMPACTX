import React, { useEffect, useState } from 'react';
import {
  ArrowRight,
  CheckCircle2,
  Circle,
  MessageCircleHeart,
  Smile,
  Timer,
  Wind,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { AnalyticsData, MoodCheckin, MoodOption, PageId, StudyTask, User } from '../types';
import { apiFetch } from '../api';

interface DashboardPageProps {
  user: User;
  onNavigate: (page: PageId) => void;
}

const QUICK_MOODS: MoodOption[] = ['Happy', 'Calm', 'Neutral', 'Stressed', 'Anxious', 'Sad'];

export function DashboardPage({ user, onNavigate }: DashboardPageProps) {
  const [tasks, setTasks] = useState<StudyTask[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null);
  const [latestMood, setLatestMood] = useState<MoodCheckin | null>(null);
  const [loading, setLoading] = useState(true);
  const [quickStatus, setQuickStatus] = useState('');

  const loadDashboard = async () => {
    try {
      const [tasksRes, moodsRes, analyticsRes] = await Promise.all([
        apiFetch<{ tasks: StudyTask[] }>('/api/tasks'),
        apiFetch<{ checkins: MoodCheckin[] }>('/api/moods'),
        apiFetch<AnalyticsData>('/api/analytics'),
      ]);
      setTasks(tasksRes.tasks);
      setLatestMood(moodsRes.checkins[0] || null);
      setAnalytics(analyticsRes);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDashboard();
  }, []);

  const handleQuickMood = async (mood: MoodOption) => {
    setQuickStatus('');
    const defaultStress = mood === 'Stressed' || mood === 'Anxious' ? 7 : mood === 'Sad' ? 6 : 3;
    const defaultEnergy = mood === 'Happy' || mood === 'Calm' ? 7 : 5;
    try {
      await apiFetch('/api/moods', {
        method: 'POST',
        body: JSON.stringify({
          mood,
          stress_level: defaultStress,
          energy_level: defaultEnergy,
          note: 'Quick dashboard pulse check-in',
        }),
      });
      setQuickStatus(`Logged "${mood}" check-in.`);
      await loadDashboard();
    } catch (err) {
      setQuickStatus(err instanceof Error ? err.message : 'Could not save mood.');
    }
  };

  const toggleTask = async (task: StudyTask) => {
    try {
      const res = await apiFetch<{ task: StudyTask }>(`/api/tasks/${task.id}`, {
        method: 'PUT',
        body: JSON.stringify({ completed: !task.completed }),
      });
      setTasks((prev) => prev.map((t) => (t.id === task.id ? res.task : t)));
      const analyticsRes = await apiFetch<AnalyticsData>('/api/analytics');
      setAnalytics(analyticsRes);
    } catch (err) {
      console.error(err);
    }
  };

  const pendingTasks = tasks.filter((t) => !t.completed).slice(0, 4);
  const firstName = user.name.split(' ')[0];

  if (loading) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-28 bg-white rounded-2xl border border-slate-200" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-white rounded-2xl border border-slate-200" />
          ))}
        </div>
        <div className="h-64 bg-white rounded-2xl border border-slate-200" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Welcome & Quick Mood Pulse */}
      <section className="bg-gradient-to-r from-[#F3F0FF] via-white to-[#ECFDF5] rounded-2xl border border-slate-200/80 p-6 flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <div className="flex items-center gap-4">
          {user.is_demo ? (
            <img
              src="/src/assets/images/avatar_student_profile_1795623793545.jpg"
              alt={user.name}
              referrerPolicy="no-referrer"
              className="w-14 h-14 rounded-2xl object-cover border border-slate-200 shrink-0"
            />
          ) : (
            <div className="w-14 h-14 rounded-2xl bg-[#EDE9FE] text-[#5B4FE9] font-display text-lg font-bold flex items-center justify-center shrink-0">
              {firstName.slice(0, 2).toUpperCase()}
            </div>
          )}
          <div>
            <h2 className="font-display text-xl sm:text-2xl font-semibold text-slate-900">
              Good to see you, {firstName}
            </h2>
            <p className="text-sm text-slate-600 mt-0.5">
              {user.major} · {user.university}
              {latestMood ? ` · Latest mood: ${latestMood.mood}` : ''}
            </p>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs font-medium text-slate-500 mr-1">Quick check-in:</span>
            {QUICK_MOODS.map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => handleQuickMood(m)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium bg-white border border-slate-200 text-slate-700 hover:border-[#5B4FE9] hover:text-[#5B4FE9] transition-colors"
              >
                {m}
              </button>
            ))}
          </div>
          {quickStatus && <p className="text-xs font-medium text-teal-700">{quickStatus}</p>}
        </div>
      </section>

      {/* Summary Metrics */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5">
          <p className="text-xs font-medium text-slate-500">Check-ins Recorded</p>
          <p className="font-mono-tabular text-2xl font-semibold text-slate-900 mt-1">
            {analytics?.summary.totalCheckins ?? 0}
          </p>
          <p className="text-xs text-slate-500 mt-1">Private emotional log</p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5">
          <p className="text-xs font-medium text-slate-500">Average Stress</p>
          <p className="font-mono-tabular text-2xl font-semibold text-slate-900 mt-1">
            {analytics?.summary.avgStress ?? 0} / 10
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Avg Energy: {analytics?.summary.avgEnergy ?? 0} / 10
          </p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5">
          <p className="text-xs font-medium text-slate-500">Study Tasks Done</p>
          <p className="font-mono-tabular text-2xl font-semibold text-slate-900 mt-1">
            {analytics?.summary.completedTasks ?? 0} / {analytics?.summary.totalTasks ?? 0}
          </p>
          <p className="text-xs text-teal-700 mt-1">
            {analytics?.summary.completionRate ?? 0}% completion rate
          </p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5">
          <p className="text-xs font-medium text-slate-500">Pomodoro Focus</p>
          <p className="font-mono-tabular text-2xl font-semibold text-slate-900 mt-1">
            {analytics?.summary.totalFocusSessions ?? 0} sessions
          </p>
          <p className="text-xs text-[#5B4FE9] mt-1">
            {analytics?.summary.totalFocusMinutes ?? 0} mindful minutes
          </p>
        </div>
      </section>

      {/* Main 2-column Workspace Grid */}
      <div className="grid lg:grid-cols-12 gap-6">
        {/* Weekly Trend Chart */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4">
          <div className="flex items-center justify-between gap-4">
            <div>
              <h3 className="font-display text-lg font-semibold text-slate-900">Mood & Stress Snapshot</h3>
              <p className="text-xs text-slate-500">Recent mood score (1–5) vs stress level (1–10)</p>
            </div>
            <button
              type="button"
              onClick={() => onNavigate('analytics')}
              className="text-xs font-semibold text-[#5B4FE9] hover:underline inline-flex items-center gap-1 whitespace-nowrap"
            >
              <span>Full Analytics</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="h-60 w-full">
            {analytics && analytics.weeklyTrends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={analytics.weeklyTrends}>
                  <defs>
                    <linearGradient id="dashMood" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#5B4FE9" stopOpacity={0.22} />
                      <stop offset="95%" stopColor="#5B4FE9" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="dashStress" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#0D9488" stopOpacity={0.18} />
                      <stop offset="95%" stopColor="#0D9488" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#64748B' }} />
                  <YAxis tick={{ fontSize: 12, fill: '#64748B' }} domain={[0, 10]} />
                  <Tooltip />
                  <Area type="monotone" dataKey="stress" name="Stress (1-10)" stroke="#0D9488" fill="url(#dashStress)" strokeWidth={2} />
                  <Area type="monotone" dataKey="energy" name="Energy (1-10)" stroke="#5B4FE9" fill="url(#dashMood)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center bg-slate-50 rounded-xl p-6">
                <Smile className="w-8 h-8 text-slate-400 mb-2" />
                <p className="text-sm font-medium text-slate-700">No check-ins recorded yet</p>
                <button
                  type="button"
                  onClick={() => onNavigate('mood')}
                  className="mt-3 px-4 py-2 text-xs font-semibold text-white bg-[#5B4FE9] rounded-lg"
                >
                  Log First Mood
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Upcoming Study Tasks */}
        <div className="lg:col-span-5 bg-white rounded-2xl border border-slate-200/80 p-6 flex flex-col justify-between space-y-4">
          <div className="space-y-4">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h3 className="font-display text-lg font-semibold text-slate-900">Today&apos;s Priority Tasks</h3>
                <p className="text-xs text-slate-500">Check off tasks as you finish them</p>
              </div>
              <button
                type="button"
                onClick={() => onNavigate('planner')}
                className="text-xs font-semibold text-[#5B4FE9] hover:underline whitespace-nowrap"
              >
                Open Planner
              </button>
            </div>

            {pendingTasks.length === 0 ? (
              <div className="p-6 rounded-xl bg-[#ECFDF5]/60 border border-teal-200/60 text-center">
                <p className="text-sm font-medium text-teal-900">All planned tasks are complete!</p>
                <p className="text-xs text-teal-700 mt-1">Take a well-earned break or add tomorrow&apos;s focus goal.</p>
              </div>
            ) : (
              <ul className="divide-y divide-slate-100">
                {pendingTasks.map((task) => (
                  <li key={task.id} className="py-3 flex items-start gap-3">
                    <button
                      type="button"
                      onClick={() => toggleTask(task)}
                      className="mt-0.5 text-slate-400 hover:text-[#5B4FE9] transition-colors shrink-0"
                      aria-label={`Mark ${task.title} complete`}
                    >
                      {task.completed ? (
                        <CheckCircle2 className="w-5 h-5 text-teal-600" />
                      ) : (
                        <Circle className="w-5 h-5" />
                      )}
                    </button>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-slate-900 truncate">{task.title}</p>
                      <p className="text-xs text-slate-500 truncate">
                        {task.subject} · {task.priority.toUpperCase()} · Due {task.deadline}
                      </p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Quick Actions */}
          <div className="grid grid-cols-3 gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => onNavigate('companion')}
              className="p-3 rounded-xl bg-[#F3F0FF] hover:bg-[#EDE9FE] text-left transition-colors"
            >
              <MessageCircleHeart className="w-4 h-4 text-[#5B4FE9] mb-1.5" />
              <p className="text-xs font-semibold text-slate-900">AI Chat</p>
            </button>
            <button
              type="button"
              onClick={() => onNavigate('pomodoro')}
              className="p-3 rounded-xl bg-[#EFF6FF] hover:bg-[#DBEAFE] text-left transition-colors"
            >
              <Timer className="w-4 h-4 text-sky-700 mb-1.5" />
              <p className="text-xs font-semibold text-slate-900">25m Focus</p>
            </button>
            <button
              type="button"
              onClick={() => onNavigate('toolkit')}
              className="p-3 rounded-xl bg-[#ECFDF5] hover:bg-[#D1FAE5] text-left transition-colors"
            >
              <Wind className="w-4 h-4 text-teal-700 mb-1.5" />
              <p className="text-xs font-semibold text-slate-900">Breathe</p>
            </button>
          </div>
        </div>
      </div>

      {/* Wellbeing Insight Banner */}
      {analytics && analytics.insights.length > 0 && (
        <section className="bg-white rounded-2xl border border-slate-200/80 p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <p className="text-xs font-semibold text-[#5B4FE9]">Wellbeing Insight</p>
            <p className="text-sm text-slate-700 mt-1">{analytics.insights[0]}</p>
          </div>
          <button
            type="button"
            onClick={() => onNavigate('toolkit')}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-teal-800 bg-[#ECFDF5] hover:bg-[#D1FAE5] transition-colors whitespace-nowrap shrink-0"
          >
            Open Relaxation Toolkit
          </button>
        </section>
      )}
    </div>
  );
}
