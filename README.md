# IMPACTX

The Industry Driven Hackathon | Dayananda Sagar University | Imaginext &amp; Wise Work

# LearnAble AI — AI-Powered Inclusive Learning Assistant

LearnAble AI is a full-stack educational accessibility web application designed for students with dyslexia, low vision, or hearing impairment. It converts conventional PDF study materials into simplified text, Text-to-Speech audio, live captions/transcripts, high-contrast/custom-spaced reading layouts, and personalised practice quizzes.

> **Educational Support Notice:** LearnAble AI adapts educational materials for accessibility and comfort. It does **not** diagnose dyslexia, visual impairment, or hearing impairment.

## Tech Stack

- **Frontend:** React.js, Vite, React Router DOM, Axios, React Context API, Lucide React
- **Backend:** Python, Flask, Flask-CORS, Flask-JWT-Extended, PyMongo
- **Database:** MongoDB (local or MongoDB Atlas)
- **AI:** Google Gemini API (`google-genai` SDK via Flask backend only)
- **Document Processing:** PyMuPDF (`fitz`) with modular extractor interface for future OCR
- **Speech:** Browser `SpeechSynthesis` API (TTS), Web Speech API (live captions), and modular Whisper-compatible HTTP transcription service for uploaded audio files
