import React from 'react';
import { Link } from 'react-router-dom';
import {
  BookOpen,
  Eye,
  Headphones,
  Sparkles,
  Upload,
  CheckCircle2,
  ArrowRight,
  ShieldCheck,
  Sliders,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function LandingPage() {
  const { isAuthenticated } = useAuth();

  return (
    <div style={{ minHeight: '100vh', backgroundColor: 'var(--bg-page)' }}>
      {/* Navigation Bar */}
      <header
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderBottom: '1px solid var(--border-color)',
          position: 'sticky',
          top: 0,
          zIndex: 20,
        }}
      >
        <div
          style={{
            maxWidth: '1200px',
            margin: '0 auto',
            padding: '14px 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: '16px',
            flexWrap: 'wrap',
          }}
        >
          <Link to="/" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div className="brand-mark" aria-hidden="true">LA</div>
            <div>
              <div className="brand-title">LearnAble AI</div>
              <div className="brand-subtitle">AI-Powered Inclusive Learning Assistant</div>
            </div>
          </Link>

          <nav style={{ display: 'flex', alignItems: 'center', gap: '18px', flexWrap: 'wrap' }}>
            <a href="#features" style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
              Features
            </a>
            <a href="#how-it-works" style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
              How It Works
            </a>
            <a href="#benefits" style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
              Benefits
            </a>
            {isAuthenticated ? (
              <Link to="/dashboard" className="btn btn-primary btn-sm">
                Go to Dashboard
              </Link>
            ) : (
              <>
                <Link to="/login" className="btn btn-secondary btn-sm">
                  Log In
                </Link>
                <Link to="/register" className="btn btn-primary btn-sm">
                  Get Started
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section style={{ maxWidth: '1200px', margin: '0 auto', padding: '64px 24px 48px' }}>
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-color)',
            borderRadius: '20px',
            padding: '48px 36px',
            boxShadow: 'var(--shadow-md)',
          }}
        >
          <span className="badge badge-primary" style={{ marginBottom: '16px' }}>
            Built for Dyslexia, Low Vision & Hearing Accessibility
          </span>
          <h1
            style={{
              margin: '0 0 16px',
              fontSize: 'clamp(2rem, 4vw, 3rem)',
              lineHeight: 1.15,
              fontWeight: 800,
              color: 'var(--text-primary)',
              maxWidth: '760px',
            }}
          >
            Learning should be accessible to everyone.
          </h1>
          <p
            style={{
              margin: '0 0 28px',
              fontSize: '1.12rem',
              color: 'var(--text-secondary)',
              maxWidth: '720px',
              lineHeight: 1.65,
            }}
          >
            LearnAble AI transforms educational materials into accessible learning experiences
            through AI-powered text simplification, audio, captions, and personalised
            accessibility tools.
          </p>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '24px' }}>
            <Link to={isAuthenticated ? '/dashboard' : '/register'} className="btn btn-primary">
              <span>{isAuthenticated ? 'Open Learning Workspace' : 'Create Free Student Account'}</span>
              <ArrowRight size={18} />
            </Link>
            <Link to="/login" className="btn btn-secondary">
              Sign In to Existing Account
            </Link>
          </div>

          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              fontSize: '0.86rem',
              color: 'var(--text-muted)',
              paddingTop: '16px',
              borderTop: '1px solid var(--border-color)',
            }}
          >
            <ShieldCheck size={16} color="var(--primary)" />
            <span>
              Educational accessibility support tool: LearnAble AI adapts study content for your
              comfort and does not diagnose dyslexia, visual impairment, or hearing impairment.
            </span>
          </div>
        </div>
      </section>

      {/* Accessibility Feature Overview */}
      <section id="features" style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px 24px 48px' }}>
        <div style={{ marginBottom: '24px' }}>
          <h2 style={{ margin: '0 0 8px', fontSize: '1.75rem', fontWeight: 700 }}>
            Tailored Accessibility Modes & Study Tools
          </h2>
          <p style={{ margin: 0, color: 'var(--text-secondary)' }}>
            Combine reading, visual, audio, and practice adaptations inside one distraction-free workspace.
          </p>
        </div>

        <div className="grid-3">
          <div className="card">
            <div className="badge badge-primary" style={{ marginBottom: '12px' }}>
              <BookOpen size={14} /> Dyslexia-Friendly
            </div>
            <h3 className="card-title">Clear Typography & AI Simplification</h3>
            <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
              Switch to Atkinson Hyperlegible fonts, widen line and letter spacing, highlight key
              concepts, and simplify dense academic paragraphs with plain-language word explanations.
            </p>
          </div>

          <div className="card">
            <div className="badge badge-accent" style={{ marginBottom: '12px' }}>
              <Eye size={14} /> Low-Vision Support
            </div>
            <h3 className="card-title">High Contrast, Zoom & Audio Reading</h3>
            <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
              Combine scalable text up to 32px, reading zoom, light/dark high-contrast themes,
              and natural SpeechSynthesis audio with adjustable speed and voice selection.
            </p>
          </div>

          <div className="card">
            <div className="badge badge-success" style={{ marginBottom: '12px' }}>
              <Headphones size={14} /> Hearing-Accessible
            </div>
            <h3 className="card-title">Live Captions & Editable Transcripts</h3>
            <p style={{ color: 'var(--text-secondary)', margin: 0 }}>
              Capture live speech-to-text captions in real time or transcribe supported audio files,
              edit notes cleanly, and revisit saved study transcripts anytime.
            </p>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section id="how-it-works" style={{ maxWidth: '1200px', margin: '0 auto', padding: '12px 24px 48px' }}>
        <div className="card" style={{ padding: '32px' }}>
          <h2 style={{ margin: '0 0 20px', fontSize: '1.6rem', fontWeight: 700 }}>
            How LearnAble AI Works
          </h2>
          <div className="grid-4">
            <div>
              <div className="badge badge-primary" style={{ marginBottom: '10px' }}>Step 1</div>
              <h3 className="card-title"><Sliders size={16} style={{ verticalAlign: 'middle' }} /> Set Preferences</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', margin: 0 }}>
                Choose dyslexia-friendly, low-vision, or hearing-accessible settings during onboarding.
              </p>
            </div>
            <div>
              <div className="badge badge-primary" style={{ marginBottom: '10px' }}>Step 2</div>
              <h3 className="card-title"><Upload size={16} style={{ verticalAlign: 'middle' }} /> Upload Notes</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', margin: 0 }}>
                Upload PDF study materials. PyMuPDF extracts text cleanly and flags scanned files safely.
              </p>
            </div>
            <div>
              <div className="badge badge-primary" style={{ marginBottom: '10px' }}>Step 3</div>
              <h3 className="card-title"><Sparkles size={16} style={{ verticalAlign: 'middle' }} /> Adapt Content</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', margin: 0 }}>
                Simplify passages with Gemini AI, inspect difficult words, or listen via Text-to-Speech.
              </p>
            </div>
            <div>
              <div className="badge badge-primary" style={{ marginBottom: '10px' }}>Step 4</div>
              <h3 className="card-title"><CheckCircle2 size={16} style={{ verticalAlign: 'middle' }} /> Practise & Track</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.92rem', margin: 0 }}>
                Generate personalised quizzes from your notes, get clear feedback, and build revision plans.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section id="benefits" style={{ maxWidth: '1200px', margin: '0 auto', padding: '12px 24px 64px' }}>
        <div className="grid-2">
          <div className="card">
            <h3 className="card-title">Why Students Choose LearnAble AI</h3>
            <ul style={{ margin: '10px 0 0', paddingLeft: '20px', color: 'var(--text-secondary)', lineHeight: 1.8 }}>
              <li>Preserves academic accuracy while lowering reading friction.</li>
              <li>Stores personal preferences, documents, transcripts, and scores securely.</li>
              <li>Allows combining high contrast, dark theme, font size, and spacing together.</li>
              <li>Grounds practice questions directly in your own course PDFs.</li>
            </ul>
          </div>

          <div
            className="card"
            style={{
              backgroundColor: 'var(--primary-soft)',
              borderColor: 'var(--primary)',
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }}
          >
            <div>
              <h3 className="card-title">Ready to make your study materials accessible?</h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '20px' }}>
                Create your account in seconds, customize your accessibility profile, and upload
                your first PDF lecture notes.
              </p>
            </div>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <Link to="/register" className="btn btn-primary">
                Register Now
              </Link>
              <Link to="/login" className="btn btn-secondary">
                Student Login
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer
        style={{
          borderTop: '1px solid var(--border-color)',
          backgroundColor: 'var(--bg-surface)',
          padding: '24px',
        }}
      >
        <div
          style={{
            maxWidth: '1200px',
            margin: '0 auto',
            display: 'flex',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
            fontSize: '0.88rem',
            color: 'var(--text-muted)',
          }}
        >
          <span>LearnAble AI — AI-Powered Inclusive Learning Assistant</span>
          <span>Designed for accessible reading, listening, captioning, and practice.</span>
        </div>
      </footer>
    </div>
  );
}
