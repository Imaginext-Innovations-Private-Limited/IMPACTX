# 🌾 Kisan Mitra — Voice-First Farm Advisor Agent

Farmers speak in their own language (Kannada, Hindi, Telugu, Tamil, Marathi, Malayalam, Bengali, Gujarati, Punjabi, English).
An LLM agent **calls tools** for live data and replies with crop, irrigation and selling advice — by voice (web) or WhatsApp.
Bonus: **leaf-photo disease detection** with a vision model.

## Architecture
```
Farmer ── voice (Web Speech API STT/TTS) ──┐
       └─ WhatsApp (Twilio webhook) ───────┤
                                           ▼
                                  FastAPI  (/api/chat, /api/diagnose, /whatsapp)
                                           ▼
                        Agent loop (OpenAI-compatible tool calling)
                        LLM = Groq (Llama 3.3 70B)
                           ├─ get_weather      → Open-Meteo (forecast, ET0, soil moisture)  [no key]
                           ├─ get_soil_health  → ISRIC SoilGrids (pH, SOC, N, clay, sand)   [no key]
                           ├─ get_market_prices→ Agmarknet / data.gov.in (demo fallback)
                           └─ diagnose_leaf    → Vision LLM (Llama 4 Scout Vision)
```

## Quick start (Windows)
1. Double-click `setup.bat` (installs everything, opens `.env` - paste `GROQ_API_KEY=gsk_...`, save).
2. Double-click `run.bat`.
3. Open http://localhost:8000 in Chrome/Edge.

## Setup (manual)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env      # set GROQ_API_KEY (gsk_...)
uvicorn app.main:app --reload
```
Open http://localhost:8000 in **Chrome/Edge** (voice recognition support). Choose language, enter your village, tap 🎤.

Sample questions: "Should I irrigate my ragi today?", "Which crop suits my soil this kharif?", "Is it a good time to sell tomato?"

## WhatsApp (Twilio sandbox)
1. `ngrok http 8000`
2. Twilio Console → Messaging → WhatsApp Sandbox → "When a message comes in": `https://<ngrok>/whatsapp` (POST).
3. Set `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` in `.env` (needed to download leaf photos).
4. On WhatsApp: `lang kn`, `loc Mandya`, then ask a question or send a leaf photo.

## Notes
- Market prices use demo values until you add a free `DATA_GOV_API_KEY` (the agent tells the farmer when data is approximate).
- Browser STT/TTS quality depends on the OS having a voice for that language; swap in Bhashini/Whisper + a TTS API for production.
- WhatsApp voice notes can be supported by transcribing the audio media with Whisper before calling `run_agent`.
- Advice is decision support, not a substitute for local agri-extension (KVK) experts.
- Smoke test: `python tests_smoke.py`
