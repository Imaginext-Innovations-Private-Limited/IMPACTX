import React, { useState } from 'react';
import {
  Activity,
  BarChart3,
  BookOpen,
  HeartHandshake,
  LayoutDashboard,
  LifeBuoy,
  LogOut,
  Menu,
  MessageCircleHeart,
  ShieldCheck,
  Smile,
  Timer,
  Users,
  Wind,
  X,
} from 'lucide-react';
import type { PageId, User } from '../types';

interface AppLayoutProps {
  user: User;
  activePage: PageId;
  onNavigate: (page: PageId) => void;
  onLogout: () => void;
  children: React.ReactNode;
}

interface NavItem {
  id: PageId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'mood', label: 'Mood Check-in', icon: Smile },
  { id: 'companion', label: 'AI Companion', icon: MessageCircleHeart },
  { id: 'planner', label: 'Study Planner', icon: BookOpen },
  { id: 'pomodoro', label: 'Pomodoro Timer', icon: Timer },
  { id: 'toolkit', label: 'Stress Relief Toolkit', icon: Wind },
  { id: 'community', label: 'Peer Community', icon: Users },
  { id: 'analytics', label: 'Wellbeing Analytics', icon: BarChart3 },
  { id: 'support', label: 'Counselling & Support', icon: LifeBuoy },
  { id: 'privacy', label: 'Privacy Settings', icon: ShieldCheck },
];

const PAGE_TITLES: Record<PageId, string> = {
  landing: 'Welcome',
  auth: 'Sign In',
  dashboard: 'Student Dashboard',
  mood: 'Mood & Stress Check-in',
  companion: 'AI Wellbeing Companion',
  planner: 'Smart Study Planner',
  pomodoro: 'Pomodoro Focus Timer',
  toolkit: 'Stress Relief Toolkit',
  community: 'Peer Support Community',
  analytics: 'Wellbeing Analytics',
  support: 'Counselling & Emergency Support',
  privacy: 'Privacy & Data Protection',
};

export function AppLayout({ user, activePage, onNavigate, onLogout, children }: AppLayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const handleSelect = (page: PageId) => {
    onNavigate(page);
    setMobileOpen(false);
  };

  const initials = user.name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase();

  const SidebarContent = (
    <div className="flex h-full flex-col bg-white border-r border-slate-200/80">
      <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
        <button
          type="button"
          onClick={() => handleSelect('dashboard')}
          className="flex items-center gap-2.5 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5B4FE9] rounded-lg"
        >
          <span className="w-8 h-8 rounded-xl bg-[#EDE9FE] text-[#5B4FE9] flex items-center justify-center shrink-0">
            <HeartHandshake className="w-4 h-4" />
          </span>
          <span className="font-display text-lg font-semibold tracking-tight text-slate-900 whitespace-nowrap">
            MINDMATE
          </span>
        </button>
        <button
          type="button"
          onClick={() => setMobileOpen(false)}
          className="lg:hidden p-2 rounded-lg text-slate-500 hover:text-slate-900 hover:bg-slate-100"
          aria-label="Close navigation menu"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-3 py-4 space-y-1" aria-label="Primary Workspace Navigation">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => handleSelect(item.id)}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-colors whitespace-nowrap text-left min-h-[42px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[#5B4FE9] ${
                isActive
                  ? 'bg-[#EDE9FE] text-[#4338CA]'
                  : 'text-slate-600 hover:bg-slate-100/80 hover:text-slate-900'
              }`}
            >
              <Icon className={`w-4 h-4 shrink-0 ${isActive ? 'text-[#5B4FE9]' : 'text-slate-400'}`} />
              <span className="truncate">{item.label}</span>
            </button>
          );
        })}
      </nav>

      <div className="p-4 border-t border-slate-100 space-y-3">
        <div className="flex items-center gap-3 px-2">
          {user.is_demo ? (
            <img
              src="/src/assets/images/avatar_student_profile_1795623793545.jpg"
              alt={user.name}
              referrerPolicy="no-referrer"
              className="w-9 h-9 rounded-full object-cover border border-slate-200 shrink-0"
            />
          ) : (
            <div className="w-9 h-9 rounded-full bg-[#D1FAE5] text-[#065F46] font-semibold text-xs flex items-center justify-center shrink-0">
              {initials}
            </div>
          )}
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-900 truncate">{user.name}</p>
            <p className="text-xs text-slate-500 truncate">
              {user.is_demo ? 'Demo Student' : user.year_of_study}
            </p>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <button
            type="button"
            onClick={() => handleSelect('landing')}
            className="px-3 py-2 text-xs font-medium text-slate-600 bg-slate-50 hover:bg-slate-100 rounded-lg border border-slate-200 transition-colors whitespace-nowrap"
          >
            Home Page
          </button>
          <button
            type="button"
            onClick={onLogout}
            className="inline-flex items-center justify-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-white hover:bg-rose-50 hover:text-rose-700 rounded-lg border border-slate-200 transition-colors whitespace-nowrap"
          >
            <LogOut className="w-3.5 h-3.5" />
            <span>Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen flex bg-[#F8FAFC] text-slate-900">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:block w-64 shrink-0 sticky top-0 h-screen">
        {SidebarContent}
      </aside>

      {/* Mobile Drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div
            className="fixed inset-0 bg-slate-900/30 backdrop-blur-xs"
            onClick={() => setMobileOpen(false)}
            aria-hidden="true"
          />
          <div className="relative w-72 max-w-[85vw] h-full z-10">{SidebarContent}</div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 min-w-0 flex flex-col">
        <header className="sticky top-0 z-30 bg-white/90 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-8 py-3.5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <button
              type="button"
              onClick={() => setMobileOpen(true)}
              className="lg:hidden p-2 -ml-1 rounded-lg text-slate-600 hover:bg-slate-100 min-h-[40px] min-w-[40px] flex items-center justify-center"
              aria-label="Open navigation menu"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="min-w-0">
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <span>MINDMATE</span>
                <span aria-hidden="true">/</span>
                <span className="truncate">{PAGE_TITLES[activePage]}</span>
              </div>
              <h1 className="font-display text-lg sm:text-xl font-semibold text-slate-900 truncate">
                {PAGE_TITLES[activePage]}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={() => onNavigate('support')}
              className="hidden sm:inline-flex items-center gap-1.5 px-3.5 py-2 rounded-lg text-xs font-medium text-teal-800 bg-[#ECFDF5] border border-teal-200/70 hover:bg-teal-100/70 transition-colors whitespace-nowrap shrink-0"
            >
              <Activity className="w-3.5 h-3.5" />
              <span>Urgent Support</span>
            </button>
            <button
              type="button"
              onClick={() => onNavigate('mood')}
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold text-white bg-[#5B4FE9] hover:bg-[#4C40D4] transition-colors whitespace-nowrap shrink-0"
            >
              <span>Log Mood</span>
            </button>
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1240px] w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
