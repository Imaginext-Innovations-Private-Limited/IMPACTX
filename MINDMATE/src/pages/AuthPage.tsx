import React, { useState } from 'react';
import { ArrowLeft, HeartHandshake, Lock, Sparkles, UserPlus } from 'lucide-react';
import type { PageId, User } from '../types';
import { apiFetch, setAuthToken } from '../api';

interface AuthPageProps {
  onSuccess: (user: User) => void;
  onBack: () => void;
  onStartDemo: () => Promise<void>;
  demoLoading: boolean;
}

export function AuthPage({ onSuccess, onBack, onStartDemo, demoLoading }: AuthPageProps) {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [university, setUniversity] = useState('Crestwood Institute of Technology');
  const [major, setMajor] = useState('Computer Applications (MCA)');
  const [yearOfStudy, setYearOfStudy] = useState('Year 2');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      if (mode === 'login') {
        const res = await apiFetch<{ token: string; user: User }>('/api/auth/login', {
          method: 'POST',
          body: JSON.stringify({ email, password }),
        });
        setAuthToken(res.token);
        onSuccess(res.user);
      } else {
        const res = await apiFetch<{ token: string; user: User }>('/api/auth/register', {
          method: 'POST',
          body: JSON.stringify({
            name,
            email,
            password,
            university,
            major,
            year_of_study: yearOfStudy,
          }),
        });
        setAuthToken(res.token);
        onSuccess(res.user);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to authenticate. Please verify your details.');
    } finally {
      setLoading(false);
    }
  };

  const fillDemoCredentials = () => {
    setMode('login');
    setEmail('maya.patel@campus.edu');
    setPassword('MindMate2026!');
    setError('');
  };

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col justify-center py-10 px-4 sm:px-6">
      <div className="max-w-[960px] w-full mx-auto">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-2 text-sm font-medium text-slate-600 hover:text-slate-900 mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Welcome Page</span>
        </button>

        <div className="grid md:grid-cols-12 gap-6 items-stretch">
          {/* Left Form Panel */}
          <div className="md:col-span-7 bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8">
            <div className="flex items-center gap-2.5 mb-6">
              <span className="w-9 h-9 rounded-xl bg-[#EDE9FE] text-[#5B4FE9] flex items-center justify-center">
                <HeartHandshake className="w-5 h-5" />
              </span>
              <div>
                <h1 className="font-display text-xl font-bold text-slate-900">MINDMATE Account</h1>
                <p className="text-xs text-slate-500">Private student wellbeing & study workspace</p>
              </div>
            </div>

            <div className="flex items-center gap-1 p-1 bg-slate-100 rounded-xl mb-6">
              <button
                type="button"
                onClick={() => {
                  setMode('login');
                  setError('');
                }}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
                  mode === 'login' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                onClick={() => {
                  setMode('register');
                  setError('');
                }}
                className={`flex-1 py-2 text-sm font-medium rounded-lg transition-colors ${
                  mode === 'register' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                Create Account
              </button>
            </div>

            {error && (
              <div className="mb-4 p-3.5 rounded-xl bg-rose-50 border border-rose-200 text-sm text-rose-800" role="alert">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === 'register' && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1.5" htmlFor="auth-name">
                    Full Name
                  </label>
                  <input
                    id="auth-name"
                    type="text"
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="e.g., Aarav Sharma"
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5" htmlFor="auth-email">
                  Campus or Personal Email
                </label>
                <input
                  id="auth-email"
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="student@university.edu"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1.5" htmlFor="auth-password">
                  Password {mode === 'register' && <span className="text-slate-400">(6+ characters)</span>}
                </label>
                <input
                  id="auth-password"
                  type="password"
                  required
                  minLength={6}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
                />
              </div>

              {mode === 'register' && (
                <div className="grid sm:grid-cols-2 gap-3 pt-1">
                  <div className="sm:col-span-2">
                    <label className="block text-xs font-medium text-slate-700 mb-1.5" htmlFor="auth-uni">
                      College / University
                    </label>
                    <input
                      id="auth-uni"
                      type="text"
                      value={university}
                      onChange={(e) => setUniversity(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1.5" htmlFor="auth-major">
                      Course / Major
                    </label>
                    <input
                      id="auth-major"
                      type="text"
                      value={major}
                      onChange={(e) => setMajor(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-slate-700 mb-1.5" htmlFor="auth-year">
                      Year of Study
                    </label>
                    <select
                      id="auth-year"
                      value={yearOfStudy}
                      onChange={(e) => setYearOfStudy(e.target.value)}
                      className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-[#5B4FE9]"
                    >
                      <option value="Year 1">Year 1</option>
                      <option value="Year 2">Year 2</option>
                      <option value="Year 3">Year 3</option>
                      <option value="Final Year">Final Year</option>
                      <option value="Postgraduate">Postgraduate</option>
                    </select>
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 rounded-xl text-sm font-semibold text-white bg-[#5B4FE9] hover:bg-[#4C40D4] transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
              >
                {mode === 'login' ? <Lock className="w-4 h-4" /> : <UserPlus className="w-4 h-4" />}
                <span>{loading ? 'Please wait...' : mode === 'login' ? 'Sign In to Workspace' : 'Create Student Account'}</span>
              </button>
            </form>
          </div>

          {/* Right Demo Mode & Privacy Panel */}
          <div className="md:col-span-5 flex flex-col justify-between bg-gradient-to-br from-[#F3F0FF] via-[#EFF6FF] to-[#ECFDF5] rounded-2xl border border-slate-200/80 p-6 sm:p-8 space-y-6">
            <div className="space-y-4">
              <div className="w-10 h-10 rounded-xl bg-white text-[#5B4FE9] border border-slate-200/80 flex items-center justify-center">
                <Sparkles className="w-5 h-5" />
              </div>
              <h2 className="font-display text-xl font-semibold text-slate-900">
                Try Demo Mode Instantly
              </h2>
              <p className="text-sm text-slate-600 leading-relaxed">
                Want to explore all 12 MINDMATE modules with sample mood check-ins, study tasks, and focus history right away? Enter Demo Mode with one click.
              </p>

              <button
                type="button"
                onClick={onStartDemo}
                disabled={demoLoading}
                className="w-full py-3 px-4 rounded-xl text-sm font-semibold text-white bg-teal-700 hover:bg-teal-800 transition-colors disabled:opacity-60"
              >
                {demoLoading ? 'Starting Demo Session...' : 'Enter Demo Mode (Maya Patel)'}
              </button>
            </div>

            <div className="bg-white/90 rounded-xl border border-slate-200/80 p-4 space-y-2">
              <p className="text-xs font-semibold text-slate-900">Sample Login Credentials</p>
              <div className="text-xs text-slate-600 space-y-1 font-mono-tabular">
                <p>Email: maya.patel@campus.edu</p>
                <p>Pass: MindMate2026!</p>
              </div>
              <button
                type="button"
                onClick={fillDemoCredentials}
                className="text-xs font-semibold text-[#5B4FE9] hover:underline pt-1"
              >
                Auto-fill credentials
              </button>
            </div>

            <p className="text-xs text-slate-500 leading-relaxed">
              Your passwords are salted & hashed with scrypt, and personal mood records or AI conversations are never shared with other students.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
