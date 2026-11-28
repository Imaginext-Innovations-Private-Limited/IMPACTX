# MINDMATE – Student Wellbeing Companion

MINDMATE is a privacy-first student wellbeing platform built to help college and university students manage academic stress, track emotional wellbeing, organize study schedules, practice guided relaxation, and connect with peer and campus support resources.

## Key Capabilities
- **Student Authentication & Demo Mode**: Secure registration/login with scrypt password hashing, plus instant Demo Mode (`maya.patel@campus.edu` / `MindMate2026!`).
- **Mood & Stress Check-in**: 6 mood states (`Happy`, `Calm`, `Neutral`, `Stressed`, `Sad`, `Anxious`), 1–10 stress and energy tracking, private reflection notes, and Recharts trend visualizations.
- **AI Wellbeing Companion**: Empathetic, non-diagnostic student assistant powered by Gemini API (`gemini-4-hydrogen`) with an intelligent offline fallback if no API key is configured, plus immediate crisis keyword detection.
- **Smart Study Planner**: Add, edit, complete, and delete tasks with subject, priority, deadline, and daily study time-slot scheduling.
- **Pomodoro Focus Timer**: Interactive 25m Focus / 5m Short Break / 15m Long Break timer that logs completed sessions to SQLite.
- **Stress Relief Toolkit**: Animated 4-4-4-4 Box Breathing exercise, guided meditation scripts, positive affirmations, and a 20-20-20 screen-break reminder.
- **Peer Support Community**: Anonymous-by-default campus feed with reactions, comments, and moderation reporting—never exposing private emails or mood records.
- **Wellbeing Analytics Dashboard**: Weekly mood/stress trends, mood distribution, study completion metrics, and automated insights.
- **Counselling & Emergency Support**: Campus counsellor directory with explicit-consent booking requests and 24/7 crisis helplines.
- **Privacy & Data Protection**: Granular visibility into stored SQLite records, JSON export, and one-click deletion controls.

## Project Structure
```text
├── backend/
│   ├── database.py         # SQLite schema & sample data seeding
│   ├── main.py             # Python FastAPI REST API
│   └── requirements.txt    # Python dependencies
├── src/
│   ├── server/             # Node Express + SQLite + Gemini API runtime
│   ├── components/         # Shared layout, sidebar, and UI components
│   ├── pages/              # All 12 MINDMATE pages
│   └── App.tsx             # Root router and auth state
├── server.ts               # Unified Express + Vite dev/prod entry point
├── run.bat                 # One-click Windows launcher
└── .env.example            # Environment variable template
```

## Windows Setup & Execution

### Prerequisites
- Python 3.10+ (`python --version`)
- Node.js 18+ (`node --version`)

### Step 1: Install Dependencies
```cmd
pip install -r backend\requirements.txt
npm install
```

### Step 2: Configure Environment (Optional)
Copy `.env.example` to `.env`. If you have a Gemini API key, add it to `GEMINI_API_KEY`; otherwise MINDMATE automatically runs its built-in empathetic fallback engine.

### Step 3: Run with `run.bat`
Double-click `run.bat` or execute it in Command Prompt:
```cmd
run.bat
```
Then open **http://localhost:3000** in your browser.

### Alternative: Single-Command Full-Stack Mode
```cmd
npm run dev
```

## Demo Credentials
- **Email**: `maya.patel@campus.edu`
- **Password**: `MindMate2026!`
- Or click **"Explore Demo Mode"** on the Welcome or Sign In page.
