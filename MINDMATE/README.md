# MINDMATE – Student Wellbeing Companion

MINDMATE is a privacy-first student wellbeing platform built to help college and university students manage academic stress, track emotional wellbeing, organize study schedules, practice guided relaxation, and connect with peer and campus support resources.

## Key Capabilities
- **Student Authentication & Demo Mode**: Secure registration/login with scrypt password hashing, plus instant Demo Mode (`maya.patel@campus.edu` / `MindMate2026!`).
- **Mood & Stress Check-in**: Optional in-browser facial-expression estimate (face-api.js; camera frames are not uploaded or stored), manual confirmation, 6 mood states (`Happy`, `Calm`, `Neutral`, `Stressed`, `Sad`, `Anxious`), 1–10 stress and energy tracking, private reflection notes, and Recharts trend visualizations.
- **AI Wellbeing Companion**: Text and browser voice interaction (Web Speech API speech recognition and speech synthesis), empathetic, non-diagnostic student assistant powered by Gemini API (`gemini-4-hydrogen`) with an intelligent offline fallback if no API key is configured, plus immediate crisis keyword detection.
- **Smart Study Planner**: Add, edit, complete, and delete tasks with subject, priority, deadline, and daily study time-slot scheduling.
- **Pomodoro Focus Timer**: Deadline-based 25m Focus / 5m Short Break / 15m Long Break timer, optional automatic cycles, in-app alerts, browser notifications, sound cues, and SQLite session logging.
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
npm install --legacy-peer-deps
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

## Added Features and Browser Permissions

### Facial-expression estimate
- Open Mood Check-in and choose **Enable camera**. Camera access requires user permission; `localhost` is treated as a secure context by modern browsers.
- The browser loads the face-api.js tiny-face and expression model files from jsDelivr on first use. Camera frames are analysed locally in the browser and are not sent to the application server or saved.
- The expression model's labels are not a reliable measure of actual emotion. The displayed percentage is only the model score for a facial-expression class, not psychological confidence. Students must confirm or change the mood manually. Stress and anxiety must never be inferred as a diagnosis.
- If camera permission is denied, the camera is unavailable, or the model cannot load, use the existing manual mood selection.

### Voice companion
- Use a current browser with Web Speech API support (Chrome/Edge are recommended). Grant microphone permission when prompted.
- Speech recognition availability and language support depend on the browser and operating system. Text chat remains available if voice recognition is unsupported or denied.
- Browser speech synthesis reads the assistant reply aloud. Use **Stop speaking** to interrupt playback.

### Pomodoro alerts
- Browser notification permission can be enabled from the Pomodoro page. If denied or unsupported, the app still displays in-page status messages and attempts a short sound cue.
- The timer uses an absolute deadline rather than counting interval ticks, so it calculates elapsed time correctly after tab throttling or returning to a backgrounded tab. A browser may defer JavaScript execution and notifications while the device is asleep or the browser is fully suspended; it cannot guarantee an alert at the exact second in those conditions.
- Automatic cycles use one long break after every four completed focus sessions; otherwise a short break follows a focus session.

### Dependency note
The updated project adds `face-api.js` and `react-is`, and aligns esbuild with Vite 8's peer dependency range. Install dependencies with:
```cmd
npm.cmd install --legacy-peer-deps
```
