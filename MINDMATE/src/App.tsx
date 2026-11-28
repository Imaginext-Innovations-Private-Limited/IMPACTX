import { useState } from 'react';
import { apiFetch, setAuthToken } from './api';
import { AppLayout } from './components/AppLayout';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { AuthPage } from './pages/AuthPage';
import { CommunityPage } from './pages/CommunityPage';
import { CompanionPage } from './pages/CompanionPage';
import { DashboardPage } from './pages/DashboardPage';
import { LandingPage } from './pages/LandingPage';
import { MoodCheckinPage } from './pages/MoodCheckinPage';
import { PomodoroPage } from './pages/PomodoroPage';
import { PrivacyPage } from './pages/PrivacyPage';
import { StudyPlannerPage } from './pages/StudyPlannerPage';
import { SupportPage } from './pages/SupportPage';
import { ToolkitPage } from './pages/ToolkitPage';
import type { PageId, User } from './types';

export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [page, setPage] = useState<PageId>('landing');
  const [demoLoading, setDemoLoading] = useState(false);

  const handleStartDemo = async () => {
    setDemoLoading(true);
    try {
      const res = await apiFetch<{ token: string; user: User }>('/api/auth/demo', {
        method: 'POST',
      });
      setAuthToken(res.token);
      setUser(res.user);
      setPage('dashboard');
    } catch (err) {
      console.error(err);
      setPage('auth');
    } finally {
      setDemoLoading(false);
    }
  };

  const handleAuthSuccess = (loggedInUser: User) => {
    setUser(loggedInUser);
    setPage('dashboard');
  };

  const handleLogout = () => {
    setAuthToken(null);
    setUser(null);
    setPage('landing');
  };

  const handleNavigate = (target: PageId) => {
    if (!user && target !== 'landing' && target !== 'auth') {
      setPage('auth');
      return;
    }
    setPage(target);
  };

  if (page === 'landing') {
    return (
      <LandingPage
        user={user}
        onNavigate={handleNavigate}
        onStartDemo={handleStartDemo}
        demoLoading={demoLoading}
      />
    );
  }

  if (page === 'auth' || !user) {
    return (
      <AuthPage
        onSuccess={handleAuthSuccess}
        onBack={() => setPage('landing')}
        onStartDemo={handleStartDemo}
        demoLoading={demoLoading}
      />
    );
  }

  return (
    <AppLayout user={user} activePage={page} onNavigate={handleNavigate} onLogout={handleLogout}>
      {page === 'dashboard' && <DashboardPage user={user} onNavigate={handleNavigate} />}
      {page === 'mood' && <MoodCheckinPage />}
      {page === 'companion' && <CompanionPage onNavigate={handleNavigate} />}
      {page === 'planner' && <StudyPlannerPage />}
      {page === 'pomodoro' && <PomodoroPage />}
      {page === 'toolkit' && <ToolkitPage />}
      {page === 'community' && <CommunityPage />}
      {page === 'analytics' && <AnalyticsPage />}
      {page === 'support' && <SupportPage />}
      {page === 'privacy' && <PrivacyPage />}
    </AppLayout>
  );
}
