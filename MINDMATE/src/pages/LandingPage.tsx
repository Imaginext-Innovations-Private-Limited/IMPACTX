import React, { useState } from 'react';
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  HeartHandshake,
  LifeBuoy,
  Lock,
  MessageCircleHeart,
  ShieldCheck,
  Smile,
  Timer,
  Users,
  Wind,
} from 'lucide-react';
import type { PageId, User } from '../types';

interface LandingPageProps {
  user: User | null;
  onNavigate: (page: PageId) => void;
  onStartDemo: () => Promise<void>;
  demoLoading: boolean;
}

export function LandingPage({ user, onNavigate, onStartDemo, demoLoading }: LandingPageProps) {
  const [heroImgError, setHeroImgError] = useState(false);

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900">
      {/* Top Bar Contract: Brand wordmark — 4 concise links — 1 primary CTA */}
      <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200/80">
        <div className="max-w-[1200px] mx-auto px-6 py-4 flex items-center justify-between gap-8">
          <button
            type="button"
            onClick={() => onNavigate('landing')}
            className="font-display text-lg font-bold tracking-tight text-slate-900 whitespace-nowrap shrink-0 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5B4FE9] rounded-md"
          >
            MINDMATE
          </button>

          <nav className="hidden md:flex items-center gap-7 text-sm font-medium text-slate-600" aria-label="Landing Navigation">
            <a href="#features" className="hover:text-slate-900 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0">
              Features
            </a>
            <a href="#toolkit" className="hover:text-slate-900 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0">
              Toolkit
            </a>
            <a href="#privacy" className="hover:text-slate-900 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0">
              Privacy
            </a>
            <a href="#support" className="hover:text-slate-900 hover:underline underline-offset-4 transition-colors whitespace-nowrap shrink-0">
              Support
            </a>
          </nav>

          <div className="flex items-center shrink-0">
            <button
              type="button"
              onClick={() => onNavigate(user ? 'dashboard' : 'auth')}
              className="px-4 py-2 text-xs sm:text-sm font-semibold text-white bg-[#5B4FE9] hover:bg-[#4C40D4] rounded-lg transition-colors whitespace-nowrap shrink-0"
            >
              {user ? 'Open Dashboard' : 'Sign In'}
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-[1200px] mx-auto px-6 pt-12 pb-10 lg:pt-16 lg:pb-14">
        <div className="grid lg:grid-cols-12 gap-10 items-stretch">
          <div className="lg:col-span-6 flex flex-col justify-center space-y-6">
            <p className="text-sm font-medium text-[#5B4FE9]">
              Privacy-First Student Wellbeing Companion
            </p>
            <h1 className="font-display text-[clamp(2.25rem,4vw,3.5rem)] font-bold leading-[1.12] tracking-tight text-slate-900 text-balance">
              Calm academic stress and protect your balance.
            </h1>
            <p className="text-base sm:text-lg text-slate-600 leading-relaxed max-w-[54ch]">
              MINDMATE brings daily mood check-ins, gentle AI reflection, structured study planning, focus sessions, and verified campus support into one private student space.
            </p>

            <div className="flex flex-wrap items-center gap-3 pt-2">
              <button
                type="button"
                onClick={user ? () => onNavigate('dashboard') : onStartDemo}
                disabled={demoLoading}
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-white bg-[#5B4FE9] hover:bg-[#4C40D4] transition-colors disabled:opacity-60 whitespace-nowrap"
              >
                <span>{user ? 'Continue to Dashboard' : demoLoading ? 'Opening Demo...' : 'Explore Demo Workspace'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              {!user && (
                <button
                  type="button"
                  onClick={() => onNavigate('auth')}
                  className="inline-flex items-center gap-2 px-6 py-3 rounded-xl text-sm font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 transition-colors whitespace-nowrap"
                >
                  <span>Create Free Account</span>
                </button>
              )}
            </div>

            <div className="pt-2 flex flex-wrap items-center gap-3 text-xs text-slate-500">
              <span>Local SQLite privacy</span>
              <span aria-hidden="true">·</span>
              <span>Anonymous peer support</span>
              <span aria-hidden="true">·</span>
              <span>No clinical diagnosis</span>
            </div>
          </div>

          <div className="lg:col-span-6">
            <div className="h-full min-h-[280px] sm:min-h-[360px] rounded-2xl overflow-hidden border border-slate-200/80 bg-[#F3F0FF] relative">
              {!heroImgError ? (
                <img
                  src="/src/assets/images/hero_calm_campus_1795623792178.jpg"
                  alt="Calm sunlit university study lounge with oak tables and greenery"
                  referrerPolicy="no-referrer"
                  onError={() => setHeroImgError(true)}
                  className="w-full h-full object-cover"
                />
              ) : (
                <div className="w-full h-full flex flex-col items-center justify-center p-8 text-center bg-gradient-to-br from-[#EDE9FE] via-[#EFF6FF] to-[#ECFDF5]">
                  <HeartHandshake className="w-12 h-12 text-[#5B4FE9] mb-3" />
                  <p className="font-display text-lg font-semibold text-slate-800">Calm Academic Sanctuary</p>
                  <p className="text-sm text-slate-600 mt-1">Reflect, plan, and recharge at your own pace.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 4-column summary strip */}
        <div className="mt-10 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border border-slate-200/80 p-5">
            <p className="text-xs font-medium text-slate-500">01. Emotional Awareness</p>
            <p className="font-display text-lg font-semibold text-slate-900 mt-1">6-Mood Daily Check-in</p>
            <p className="text-sm text-slate-600 mt-1">Track stress and energy alongside private reflection notes.</p>
          </div>
          <div className="bg-[#F3F0FF]/60 rounded-xl border border-[#DDD6FE]/70 p-5">
            <p className="text-xs font-medium text-[#5B4FE9]">02. Compassionate Guidance</p>
            <p className="font-display text-lg font-semibold text-slate-900 mt-1">AI Wellbeing Companion</p>
            <p className="text-sm text-slate-600 mt-1">Supportive reflection for deadlines, loneliness, and burnout.</p>
          </div>
          <div className="bg-[#EFF6FF]/70 rounded-xl border border-[#BFDBFE]/70 p-5">
            <p className="text-xs font-medium text-sky-700">03. Sustainable Focus</p>
            <p className="font-display text-lg font-semibold text-slate-900 mt-1">Planner & Pomodoro</p>
            <p className="text-sm text-slate-600 mt-1">Time-blocked study tasks paired with 25-minute focus sprints.</p>
          </div>
          <div className="bg-[#ECFDF5]/70 rounded-xl border border-[#A7F3D0]/70 p-5">
            <p className="text-xs font-medium text-teal-800">04. Real Human Care</p>
            <p className="font-display text-lg font-semibold text-slate-900 mt-1">Campus & Crisis Support</p>
            <p className="text-sm text-slate-600 mt-1">Verified 24/7 helplines and consent-first counsellor outreach.</p>
          </div>
        </div>
      </section>

      {/* Capabilities Section */}
      <section id="features" className="max-w-[1200px] mx-auto px-6 py-12 border-t border-slate-200/70">
        <div className="max-w-2xl mb-8">
          <h2 className="font-display text-2xl sm:text-3xl font-semibold text-slate-900 text-balance">
            Built around how university semesters actually feel.
          </h2>
          <p className="text-slate-600 mt-2">
            Every workspace module connects to your private SQLite wellbeing record so insights stay meaningful and strictly under your control.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="md:col-span-2 bg-white rounded-2xl border border-slate-200/80 p-6 flex flex-col justify-between">
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-xl bg-[#EDE9FE] text-[#5B4FE9] flex items-center justify-center">
                <MessageCircleHeart className="w-5 h-5" />
              </div>
              <h3 className="font-display text-xl font-semibold text-slate-900">
                Non-Judgmental AI Companion & Stress Triage
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed max-w-[60ch]">
                Talk through exam overwhelm, procrastination, or feeling disconnected on campus. Powered by Gemini with an automatic offline empathetic fallback—and immediate crisis-line guidance whenever urgent distress is detected.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Never diagnoses · Never replaces human care</span>
              <button
                type="button"
                onClick={user ? () => onNavigate('companion') : onStartDemo}
                className="font-semibold text-[#5B4FE9] hover:underline"
              >
                Try AI Companion
              </button>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 flex flex-col justify-between">
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-xl bg-[#ECFDF5] text-teal-700 flex items-center justify-center">
                <Smile className="w-5 h-5" />
              </div>
              <h3 className="font-display text-xl font-semibold text-slate-900">
                Mood, Stress & Energy Trends
              </h3>
              <p className="text-sm text-slate-600 leading-relaxed">
                Spot how sleep, heavy deadlines, and study breaks shift your weekly baseline using visual Recharts timelines.
              </p>
            </div>
            <div className="mt-6 pt-4 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
              <span>Private history</span>
              <BarChart3 className="w-4 h-4 text-teal-600" />
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 space-y-3">
            <div className="w-10 h-10 rounded-xl bg-[#EFF6FF] text-sky-700 flex items-center justify-center">
              <BookOpen className="w-5 h-5" />
            </div>
            <h3 className="font-display text-lg font-semibold text-slate-900">Smart Study Planner</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Organize subjects, priorities, deadlines, and daily Morning/Afternoon/Evening slots without overwhelming to-do sprawl.
            </p>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 space-y-3">
            <div className="w-10 h-10 rounded-xl bg-[#EDE9FE] text-[#5B4FE9] flex items-center justify-center">
              <Timer className="w-5 h-5" />
            </div>
            <h3 className="font-display text-lg font-semibold text-slate-900">Pomodoro Focus Timer</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              25-minute focus blocks with 5-minute short breaks and 15-minute long breaks, logging every completed sprint automatically.
            </p>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200/80 p-6 space-y-3">
            <div className="w-10 h-10 rounded-xl bg-[#ECFDF5] text-teal-700 flex items-center justify-center">
              <Users className="w-5 h-5" />
            </div>
            <h3 className="font-display text-lg font-semibold text-slate-900">Peer Support Community</h3>
            <p className="text-sm text-slate-600 leading-relaxed">
              Share small wins and study strategies under an anonymous campus alias with built-in reporting and zero personal data leaks.
            </p>
          </div>
        </div>
      </section>

      {/* Toolkit & Privacy Section */}
      <section id="toolkit" className="max-w-[1200px] mx-auto px-6 py-12 border-t border-slate-200/70">
        <div className="grid lg:grid-cols-12 gap-8 items-center">
          <div className="lg:col-span-6 space-y-4">
            <div className="inline-flex items-center gap-2 text-xs font-medium text-teal-700">
              <Wind className="w-4 h-4" />
              <span>Stress Relief Toolkit</span>
            </div>
            <h2 className="font-display text-2xl sm:text-3xl font-semibold text-slate-900 text-balance">
              Three minutes to reset between lectures.
            </h2>
            <p className="text-sm sm:text-base text-slate-600 leading-relaxed">
              Includes an animated 4-4-4-4 Box Breathing circle, short guided meditation exercises, positive affirmations, and a 20-20-20 eye-strain reminder for late study sessions.
            </p>
            <div id="privacy" className="pt-4 border-t border-slate-200/80 space-y-2">
              <div className="flex items-center gap-2 text-sm font-semibold text-slate-900">
                <Lock className="w-4 h-4 text-[#5B4FE9]" />
                <span>Your Wellbeing Records Stay Yours</span>
              </div>
              <p className="text-sm text-slate-600">
                Mood check-ins and AI chats are private to your account. You can view, export as JSON, or permanently delete your records anytime in Privacy Settings.
              </p>
            </div>
          </div>

          <div id="support" className="lg:col-span-6 bg-white rounded-2xl border border-slate-200/80 p-6 sm:p-8 space-y-5">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-rose-50 text-rose-700 flex items-center justify-center shrink-0">
                <LifeBuoy className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-display text-lg font-semibold text-slate-900">
                  Human Counselling & 24/7 Helplines
                </h3>
                <p className="text-sm text-slate-600 mt-1">
                  We never contact anyone automatically without your explicit consent. Reach out directly whenever you want human support.
                </p>
              </div>
            </div>

            <div className="grid sm:grid-cols-2 gap-3 text-sm">
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70">
                <p className="font-semibold text-slate-900">988 Crisis Lifeline</p>
                <p className="text-xs text-slate-600 mt-0.5">Call or text 988 (24/7, free & confidential)</p>
              </div>
              <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/70">
                <p className="font-semibold text-slate-900">Crisis Text Line</p>
                <p className="text-xs text-slate-600 mt-0.5">Text HOME to 741741 anytime</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3 pt-1">
              <button
                type="button"
                onClick={user ? () => onNavigate('support') : onStartDemo}
                className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl text-sm font-semibold text-white bg-teal-700 hover:bg-teal-800 transition-colors"
              >
                <ShieldCheck className="w-4 h-4" />
                <span>{user ? 'View Support Directory' : 'Launch Demo Workspace'}</span>
              </button>
              <span className="text-xs text-slate-500">Demo login: maya.patel@campus.edu</span>
            </div>
          </div>
        </div>
      </section>

      <footer className="border-t border-slate-200 bg-white">
        <div className="max-w-[1200px] mx-auto px-6 py-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-slate-500">
          <p>MINDMATE – Student Wellbeing Companion · Non-diagnostic educational & wellness support tool.</p>
          <div className="flex items-center gap-4">
            <button type="button" onClick={() => onNavigate('auth')} className="hover:text-slate-900">
              Sign In / Register
            </button>
            <button type="button" onClick={onStartDemo} className="hover:text-slate-900">
              Demo Mode
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
