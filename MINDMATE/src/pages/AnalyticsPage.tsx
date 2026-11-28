import React, { useEffect, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { AnalyticsData } from '../types';
import { apiFetch } from '../api';

export function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<AnalyticsData>('/api/analytics')
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-white rounded-2xl border border-slate-200" />
          ))}
        </div>
        <div className="h-80 bg-white rounded-2xl border border-slate-200" />
      </div>
    );
  }

  if (!data) {
    return <p className="text-sm text-rose-700">Unable to load wellbeing analytics.</p>;
  }

  return (
    <div className="space-y-6">
      {/* KPI Row */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5">
          <p className="text-xs font-medium text-slate-500">Total Mood Check-ins</p>
          <p className="font-mono-tabular text-2xl font-semibold text-slate-900 mt-1">
            {data.summary.totalCheckins}
          </p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5">
          <p className="text-xs font-medium text-slate-500">Average Stress / Energy</p>
          <p className="font-mono-tabular text-2xl font-semibold text-slate-900 mt-1">
            {data.summary.avgStress} / {data.summary.avgEnergy}
          </p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5">
          <p className="text-xs font-medium text-slate-500">Task Completion</p>
          <p className="font-mono-tabular text-2xl font-semibold text-teal-700 mt-1">
            {data.summary.completionRate}%
          </p>
          <p className="text-xs text-slate-500 mt-0.5 font-mono-tabular">
            {data.summary.completedTasks} of {data.summary.totalTasks} tasks
          </p>
        </div>
        <div className="bg-white rounded-2xl border border-slate-200/80 p-5">
          <p className="text-xs font-medium text-slate-500">Focus Sessions Completed</p>
          <p className="font-mono-tabular text-2xl font-semibold text-[#5B4FE9] mt-1">
            {data.summary.totalFocusSessions}
          </p>
          <p className="text-xs text-slate-500 mt-0.5 font-mono-tabular">
            {data.summary.totalFocusMinutes} total minutes
          </p>
        </div>
      </section>

      {/* Insights Section */}
      <section className="bg-[#F3F0FF]/70 rounded-2xl border border-[#DDD6FE] p-6 space-y-3">
        <h2 className="font-display text-lg font-semibold text-slate-900">
          Personal Wellbeing Insights
        </h2>
        <ul className="space-y-2 text-sm text-slate-700">
          {data.insights.map((insight) => (
            <li key={insight} className="flex items-start gap-2">
              <span className="text-[#5B4FE9] font-bold">·</span>
              <span>{insight}</span>
            </li>
          ))}
        </ul>
      </section>

      {/* Charts Grid */}
      <div className="grid lg:grid-cols-12 gap-6">
        <section className="lg:col-span-12 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4">
          <div>
            <h3 className="font-display text-lg font-semibold text-slate-900">
              Weekly Mood, Stress & Energy Trends
            </h3>
            <p className="text-xs text-slate-500">
              Mood score (1 = Sad, 5 = Happy) alongside self-reported stress and energy (1–10)
            </p>
          </div>
          <div className="h-72 w-full">
            {data.weeklyTrends.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.weeklyTrends}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="date" tick={{ fontSize: 12, fill: '#64748B' }} />
                  <YAxis domain={[0, 10]} tick={{ fontSize: 12, fill: '#64748B' }} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="stress" name="Stress (1-10)" stroke="#E11D48" strokeWidth={2.5} />
                  <Line type="monotone" dataKey="energy" name="Energy (1-10)" stroke="#0D9488" strokeWidth={2.5} />
                  <Line type="monotone" dataKey="moodScore" name="Mood Score (1-5)" stroke="#5B4FE9" strokeWidth={2.5} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center bg-slate-50 rounded-xl text-sm text-slate-500">
                No check-ins recorded yet.
              </div>
            )}
          </div>
        </section>

        <section className="lg:col-span-6 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4">
          <div>
            <h3 className="font-display text-lg font-semibold text-slate-900">Mood Distribution</h3>
            <p className="text-xs text-slate-500">Frequency of each logged emotional state</p>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.moodCounts}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="mood" tick={{ fontSize: 12, fill: '#64748B' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#64748B' }} />
                <Tooltip />
                <Bar dataKey="count" name="Check-ins" fill="#5B4FE9" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>

        <section className="lg:col-span-6 bg-white rounded-2xl border border-slate-200/80 p-6 space-y-4">
          <div>
            <h3 className="font-display text-lg font-semibold text-slate-900">7-Day Focus Sessions</h3>
            <p className="text-xs text-slate-500">Completed Pomodoro sprints across the past week</p>
          </div>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.focusByDay}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis dataKey="day" tick={{ fontSize: 12, fill: '#64748B' }} />
                <YAxis allowDecimals={false} tick={{ fontSize: 12, fill: '#64748B' }} />
                <Tooltip />
                <Bar dataKey="sessions" name="Focus Sessions" fill="#0D9488" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </section>
      </div>
    </div>
  );
}
