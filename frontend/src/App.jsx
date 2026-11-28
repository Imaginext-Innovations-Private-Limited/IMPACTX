import React from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import ProtectedRoute from './components/ProtectedRoute';
import AppLayout from './components/AppLayout';
import LandingPage from './pages/LandingPage';
import RegisterPage from './pages/RegisterPage';
import LoginPage from './pages/LoginPage';
import OnboardingPage from './pages/OnboardingPage';
import DashboardPage from './pages/DashboardPage';
import UploadPage from './pages/UploadPage';
import DocumentsPage from './pages/DocumentsPage';
import ReaderPage from './pages/ReaderPage';
import SimplifyPage from './pages/SimplifyPage';
import AudioCaptionsPage from './pages/AudioCaptionsPage';
import PracticePage from './pages/PracticePage';
import ProgressPage from './pages/ProgressPage';
import AccessibilitySettingsPage from './pages/AccessibilitySettingsPage';
import ProfilePage from './pages/ProfilePage';

function ProtectedShell({ children }) {
  return (
    <ProtectedRoute>
      <AppLayout>{children}</AppLayout>
    </ProtectedRoute>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/onboarding"
        element={
          <ProtectedRoute>
            <OnboardingPage />
          </ProtectedRoute>
        }
      />

      <Route
        path="/dashboard"
        element={
          <ProtectedShell>
            <DashboardPage />
          </ProtectedShell>
        }
      />
      <Route
        path="/upload"
        element={
          <ProtectedShell>
            <UploadPage />
          </ProtectedShell>
        }
      />
      <Route
        path="/documents"
        element={
          <ProtectedShell>
            <DocumentsPage />
          </ProtectedShell>
        }
      />
      <Route
        path="/reader"
        element={
          <ProtectedShell>
            <ReaderPage />
          </ProtectedShell>
        }
      />
      <Route
        path="/reader/:docId"
        element={
          <ProtectedShell>
            <ReaderPage />
          </ProtectedShell>
        }
      />
      <Route
        path="/simplify"
        element={
          <ProtectedShell>
            <SimplifyPage />
          </ProtectedShell>
        }
      />
      <Route
        path="/simplify/:docId"
        element={
          <ProtectedShell>
            <SimplifyPage />
          </ProtectedShell>
        }
      />
      <Route
        path="/audio-captions"
        element={
          <ProtectedShell>
            <AudioCaptionsPage initialTab="captions" />
          </ProtectedShell>
        }
      />
      <Route
        path="/tts"
        element={
          <ProtectedShell>
            <AudioCaptionsPage initialTab="tts" />
          </ProtectedShell>
        }
      />
      <Route
        path="/captions"
        element={
          <ProtectedShell>
            <AudioCaptionsPage initialTab="captions" />
          </ProtectedShell>
        }
      />
      <Route
        path="/practice"
        element={
          <ProtectedShell>
            <PracticePage />
          </ProtectedShell>
        }
      />
      <Route
        path="/practice/:docId"
        element={
          <ProtectedShell>
            <PracticePage />
          </ProtectedShell>
        }
      />
      <Route
        path="/progress"
        element={
          <ProtectedShell>
            <ProgressPage />
          </ProtectedShell>
        }
      />
      <Route
        path="/settings/accessibility"
        element={
          <ProtectedShell>
            <AccessibilitySettingsPage />
          </ProtectedShell>
        }
      />
      <Route
        path="/profile"
        element={
          <ProtectedShell>
            <ProfilePage />
          </ProtectedShell>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
