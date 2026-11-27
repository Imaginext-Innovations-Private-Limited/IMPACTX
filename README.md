# 🌾 Farm Advisor — Multilingual AI Farm Advisory Platform

A full-stack, **multilingual farm advisory web application** for Karnataka farmers built with:
- **Backend:** FastAPI (Python 3.12) + SQLite (SQLAlchemy)
- **Frontend:** React 18 (Vite + Tailwind CSS + Lucide Icons + Recharts)
- **AI:** Google Gemini 2.5 Flash (vision + agentic tool calling) + Sarvam AI (Indic STT/TTS)
- **Data:** Open-Meteo (free weather API) + Agmarknet data.gov.in (live APMC mandi prices)

---

## 📋 Prerequisites

| Tool | Version | Notes |
|------|---------|-------|
| Python | 3.12+ | `python --version` |
| Node.js | 18+ | Portable copy at `nodejs/node-v20.18.0-win-x64/` |
| pip | latest | Included with Python |

---

## ⚡ Quick Start (Windows)

```bat
cd C:\Users\Lokesh\.gemini\antigravity\scratch\farm-advisor
start_app.bat
```

Then open **http://localhost:5173** in your browser.

---

## 🔧 Manual Setup

### 1. Backend Setup

```bash
cd backend
python -m pip install -r requirements.txt
```

### 2. Configure API Keys (Optional)

```bash
copy .env.example .env
# Edit .env and fill in your keys
```

### 3. Start Backend

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

### 4. Start Frontend

```bash
# Windows (uses portable Node.js)
set PATH=C:\Users\Lokesh\.gemini\antigravity\scratch\farm-advisor\nodejs\node-v20.18.0-win-x64;%PATH%
cd frontend
npm run dev
```

---

## 🔑 API Key Configuration

All keys are **optional** — the app runs in **Demo/Cached Mode** when any key is absent.

| Key | Service | Purpose | Get It |
|-----|---------|---------|--------|
| `GEMINI_API_KEY` | Google Gemini | 4-mode camera scanner + voice assistant tool calling | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| `SARVAM_API_KEY` | Sarvam AI | Indic speech-to-text (saaras:v4) + text-to-speech (bulbul:v3) | [sarvam.ai](https://www.sarvam.ai/) |
| `DATA_GOV_API_KEY` | data.gov.in | Live Agmarknet APMC mandi prices | [data.gov.in](https://data.gov.in/user/register) |

Create a `.env` file in the `backend/` folder:

```env
GEMINI_API_KEY=your_key_here
SARVAM_API_KEY=your_key_here
DATA_GOV_API_KEY=your_key_here
```

---

## 📦 Sprint Features

### Sprint 1 — Core Foundation
- **Top Commodity Ticker Bar** — Live rates for Paddy, Areca, Ginger, Corn, Pepper, Coconut with ▲/▼ indicators
- **Multilingual Voice Assistant** — 6-language (Kannada, Hindi, Tamil, Telugu, Marathi, English) mic + text chat
- **4-Mode Smart Camera Scanner** — Crop Info, Crop Disease, Fertilizer/Pesticide, Soil Analysis
- **Navigation Shell** — Mobile-first tab navigation

### Sprint 2 — Weather & Markets
- **16-Day Weather Forecast** — Open-Meteo integration + Farm Action Advisory Banner
- **Commodity Market Analytics** — 14-day price history, cross-mandi comparison, 6-year Recharts seasonal chart
- **9-Category Agri News Feed** — Commodity rates, subsidies, weather alerts, insurance, solar schemes
- **Animal Husbandry Module** — Dairy procurement rates (KMF, Amul, Dodla), breed cards, feed plans

### Sprint 3 — Notifications & Finance
- **Notification Center** — Scheme deadlines, insurance reminders, drought/flood relief with document checklists
- **Farm & Household Balance Sheet** — Annual income/expense ledger with SQLite persistence
- **Crop Profit Comparator** — Alternative crop ROI comparison
- **Credit Advisory Hub** — Kisan Credit Card and loan guidance

### Sprint 4 — Live AI & External APIs
- **Real Gemini Vision Scanner** — `gemini-2.5-flash` multimodal analysis for all 4 scanner modes
- **Agentic Voice Assistant** — Gemini tool calling with 5 farm data tools + Sarvam STT/TTS
- **Live Weather Sync** — Open-Meteo forecast with SQLite cache fallback
- **Live Agmarknet Prices** — data.gov.in APMC mandi prices with SQLite upsert
- **Status Pills** — Live AI / Demo Mode indicator on every AI-powered feature
- **TTS Audio Playback** — Sarvam base64 WAV auto-play + browser speechSynthesis fallback

---

## 🗂️ Project Structure

```
farm-advisor/
├── backend/
│   ├── main.py              # FastAPI app entry point
│   ├── config.py            # Sprint 4: dotenv + API key helpers
│   ├── .env.example         # Template for API keys
│   ├── .env                 # Your actual keys (gitignored)
│   ├── database.py          # SQLite engine + session
│   ├── models.py            # SQLAlchemy models (all sprints)
│   ├── seed_data.py         # Seed functions
│   ├── requirements.txt     # Python dependencies
│   └── routers/
│       ├── commodities.py   # /api/commodities
│       ├── voice.py         # /api/voice + Sarvam + Gemini tools
│       ├── scan.py          # /api/scan + Gemini Vision
│       ├── weather.py       # /api/weather + Open-Meteo
│       ├── markets.py       # /api/markets + Agmarknet
│       ├── news.py          # /api/news
│       ├── dairy.py         # /api/dairy
│       ├── notifications.py # /api/notifications
│       └── finance.py       # /api/finance
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api/client.js    # Axios API client
│   │   ├── components/
│   │   │   ├── VoiceAssistant.jsx   # Sprint 4: TTS + status pill
│   │   │   ├── NotificationDrawer.jsx
│   │   │   └── CommodityTicker.jsx
│   │   └── pages/
│   │       ├── HomePage.jsx   # Commodity ticker + scanner
│   │       ├── WeatherPage.jsx
│   │       ├── MarketsPage.jsx
│   │       ├── NewsPage.jsx
│   │       ├── DairyPage.jsx
│   │       └── FinancePage.jsx
│   └── package.json
├── nodejs/                  # Portable Node.js v20
├── start_app.bat            # One-click startup script
└── README.md                # This file
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/commodities/ticker` | Live commodity ticker data |
| POST | `/api/scan/` | 4-mode camera scanner (Gemini Vision) |
| POST | `/api/voice/text-query` | Text-based voice assistant (Gemini + tools) |
| POST | `/api/voice/query` | Audio voice assistant (Sarvam STT + Gemini + TTS) |
| GET | `/api/weather/forecast` | 16-day Open-Meteo forecast + farm advisory |
| GET | `/api/markets/{commodity}` | Analytics + Agmarknet live prices |
| GET | `/api/news/` | 9-category agri news feed |
| GET | `/api/dairy/procurement-rates` | Dairy milk procurement rates |
| GET | `/api/notifications/` | Scheme and insurance notifications |
| GET | `/api/finance/ledger` | Farm balance sheet ledger |
| GET | `/docs` | FastAPI Swagger UI |

---

## 🛠️ Troubleshooting

**Backend won't start:**
```bash
# Check Python path
C:\Users\Lokesh\AppData\Local\Programs\Python\Python312\python.exe --version
# Reinstall dependencies
cd backend && python -m pip install -r requirements.txt
```

**Frontend won't build:**
```bash
set PATH=C:\Users\Lokesh\.gemini\antigravity\scratch\farm-advisor\nodejs\node-v20.18.0-win-x64;%PATH%
cd frontend && npm install && npm run build
```

**API calls fail (CORS):**  
Ensure the backend is running on port 8000 and frontend on port 5173. The Vite proxy in `vite.config.js` forwards `/api` to `localhost:8000`.

**Scanner returns "Demo Mode":**  
Add `GEMINI_API_KEY=your_key` to `backend/.env` and restart the backend.

---

## 📄 License

Built for educational and agricultural advisory purposes for Karnataka farmers.
