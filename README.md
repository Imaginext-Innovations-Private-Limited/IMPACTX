# ScamShield AI v2.0 — Digital Arrest and UPI Fraud Detector

Track B · Problem Statement 5 · Wisework × Imagenext internship hackathon

A local multilingual hackathon prototype that assesses risk in suspicious messages, payment requests, screenshots and call transcripts. It identifies warning signs, not proven fraud. It does not intercept calls or messages or monitor bank transactions.

## Run on Windows

Install Python 3.11+ and Tesseract OCR (English; add hin, ben, kan, tel, ori, mar for regional OCR). Open CMD in the project folder.

- `run.bat` — sets up dependencies if needed; prompts privately for Groq and Sarvam keys. Press Enter to skip either. Open http://127.0.0.1:8000 after startup.
- `run.bat offline` — no cloud keys or cloud analysis. Browser dictation may still use the browser provider; do not dictate secrets.
- `test_project.bat` — runs the test suite with live test names and exit status.

Keys are not saved by the launcher. Existing environment keys can be used in normal mode. Never commit keys, private inputs, or personal recordings. Initial setup requires internet.

## Demo

1. Paste a message or upload a screenshot; check the extracted text before analysis.
2. Click **Analyze** once after reviewing the text. With Groq configured, approve the consent prompt for one combined AI + local assessment, or decline for local-only analysis. Without a key or if the provider fails, the offline engine remains available. Editing text or settings clears stale results; nothing is analyzed automatically.
3. For voice, use browser dictation (browser support varies) or upload a consented recording with Sarvam configured. Review the transcript before analysis.
4. Select English, Hindi, Bengali, Kannada, Telugu, Odia or Marathi and click Hear warning. The app can reuse saved audio, synthesize fixed safety scripts with Sarvam, or fall back to browser and bundled basic voices. Verify actual pronunciation with fluent speakers.
5. For financial cybercrime, guidance links to 1930 and https://cybercrime.gov.in/. Contact your bank if money was transferred or credentials exposed.

## Architecture and boundaries

- FastAPI backend, HTML/CSS/JS frontend, Pillow/Tesseract OCR.
- Offline: contextual rules and a small TF-IDF/logistic-regression classifier trained on synthetic examples.
- Optional cloud: Groq GPT-OSS 120B with structured output, best-effort redaction, evidence validation and offline fallback. The higher warning level is retained on disagreement.
- Sarvam speech transcription and fixed multilingual voice warnings. No user messages are sent for fixed-script TTS. Cloud analysis/transcription require consent; provider policies apply. Redaction is not foolproof; use synthetic or anonymized demo data.
- Risk scores are heuristic, not probabilities. Unit tests do not establish real-world accuracy. Low scores do not prove safety. No government or bank endorsement.

## Project layout

- `scamshield/` — backend and detection
- `static/` — interface, fonts and bundled offline voices
- `tools/` — launch and optional voice-generation utilities
- `tests/` — regression and integration tests (cloud responses mocked)
- `demo_assets/` — synthetic demo inputs
- `docs/` — engineering, team and demonstration guidance
- `voice_cache/` — local generated audio, excluded from GitHub

See [demo script](docs/DEMO_SCRIPT.md), [engineering decisions](docs/ENGINEERING_DECISIONS.md), [team sprint](docs/TEAM_SPRINT.md), and [optional legacy voice generation](docs/AUTOMATIC_VOICES.md). Older release notes and large test logs can be kept in a private archive outside the repo. Do not distribute generated or recorded voices without checking permissions and provider terms.

License: MIT. Educational prototype.
