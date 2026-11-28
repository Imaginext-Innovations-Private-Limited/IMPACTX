# 🌊🌡️ Urban Flood & Heatwave Early-Warning System

A full-stack, multimodal early-warning platform that predicts flood-prone streets and heatwave risk in cities by combining **rainfall forecasts**, **drainage & lake sensor data**, **citizen-uploaded photos (AI-analysed)**, and **ML risk models**. It alerts residents and suggests **safe evacuation routes** and **cooling centres**.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🗺️ **Live Flood Risk Map** | Interactive Leaflet map with colour-coded risk zones |
| 🌡️ **Heatwave Risk Map** | Heat-index map with Urban Heat Island correction |
| 🚨 **Real-time Alerts** | Severity-graded alerts (INFO / WARNING / CRITICAL) |
| 📸 **Citizen Reports** | Photo upload + Gemini Vision AI analysis |
| 🧭 **Safe Route Finder** | OSRM-based routing that flags flooded zones |
| ❄️ **Cooling Centres** | Nearest shelters with capacity & medical info |
| 📊 **Analytics Dashboard** | 24-hour rainfall, temperature, and zone risk charts |
| 🤖 **ML Flood Predictor** | Rule-based + sklearn ensemble (falls back gracefully) |
| ⏱️ **Background Scheduler** | Auto-refreshes forecasts every 30 minutes |

---

## 🏗️ Architecture

```
urban-flood-heatwave-system/
├── backend/                  # FastAPI Python backend
│   ├── app/
│   │   ├── api/              # REST API routers
│   │   │   ├── flood.py      # Flood zone & prediction endpoints
│   │   │   ├── heatwave.py   # Heatwave prediction endpoints
│   │   │   ├── alerts.py     # Alert CRUD
│   │   │   ├── routes.py     # Safe route & cooling centres
│   │   │   ├── reports.py    # Citizen photo reports
│   │   │   └── auth.py       # JWT authentication
│   │   ├── core/
│   │   │   ├── config.py     # Environment config (Pydantic settings)
│   │   │   └── database.py   # Async SQLAlchemy setup
│   │   ├── ml/
│   │   │   ├── flood_predictor.py    # Rule-based + ML flood scorer
│   │   │   ├── heatwave_calculator.py# Steadman heat index + risk
│   │   │   └── photo_analyser.py     # Gemini Vision AI wrapper
│   │   ├── models/           # SQLAlchemy ORM models
│   │   └── services/
│   │       ├── weather_service.py    # OpenWeatherMap API client
│   │       ├── alert_service.py      # Alert creation & management
│   │       ├── route_service.py      # OSRM routing + haversine
│   │       └── scheduler.py          # Background forecast refresh
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                 # React + Vite + Tailwind dashboard
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx     # Command overview
│   │   │   ├── FloodMap.jsx      # Interactive flood risk map
│   │   │   ├── HeatwaveMap.jsx   # Heatwave heat-index map
│   │   │   ├── AlertsPage.jsx    # Alert feed with dismiss
│   │   │   ├── ReportPage.jsx    # Citizen photo report form
│   │   │   ├── RouteFinder.jsx   # Safe route + cooling centres
│   │   │   └── AnalyticsPage.jsx # Recharts trend visualisations
│   │   ├── components/
│   │   │   ├── FloodRiskMap.jsx  # Leaflet map component
│   │   │   ├── RiskBadge.jsx     # Colour-coded risk pill
│   │   │   ├── AlertBanner.jsx   # Animated alert card
│   │   │   └── StatCard.jsx      # Dashboard metric card
│   │   ├── services/api.js       # Axios API client
│   │   └── store/alertStore.js   # Zustand global state
│   ├── package.json
│   └── Dockerfile
│
├── scripts/seed_data.py      # Populate DB with sample Mumbai zones
├── docker-compose.yml
└── .env.example
```

---

## 🚀 Quick Start

### Option A — Docker (recommended)

```bash
# 1. Clone / navigate to project
cd urban-flood-heatwave-system

# 2. Copy and fill in your API keys
cp .env.example .env

# 3. Start everything
docker-compose up --build

# 4. Seed sample data (first time only)
docker exec flood_backend python scripts/seed_data.py
```

Open **http://localhost:3000**

---

### Option B — Local Dev

#### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

# Create .env from example
copy ..\.env.example .env

# Start API server
uvicorn app.main:app --reload --port 8000

# (New terminal) Seed database
python ../scripts/seed_data.py
```

API docs at **http://localhost:8000/docs**

#### Frontend
```bash
cd frontend
npm install
npm run dev
```

Dashboard at **http://localhost:5173**

---

## 🔑 API Keys Needed

| Service | Purpose | Free tier? |
|---|---|---|
| [OpenWeatherMap](https://openweathermap.org/api) | Rainfall forecasts & temperature | ✅ Yes |
| [Google Gemini](https://aistudio.google.com) | Citizen photo AI analysis | ✅ Yes |

The app runs in **demo mode** (with mock data) without any API keys.

---

## 📡 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/flood/zones` | List all flood zones with risk scores |
| GET | `/api/flood/predict?lat=&lon=` | On-demand flood risk prediction |
| GET | `/api/heatwave/predict?lat=&lon=` | On-demand heatwave risk |
| GET | `/api/alerts/` | Active alerts (filterable by city) |
| GET | `/api/routes/safe-route` | Flood-aware routing |
| GET | `/api/routes/cooling-centres` | Nearest cooling centres |
| POST | `/api/reports/` | Submit citizen photo report |
| POST | `/api/auth/token` | Get JWT token |

---

## 🧠 How the Risk Models Work

### Flood Risk (0–1 score)
Combines weighted factors:
- **Rainfall** (last 1h + 3h) — 35%
- **Drainage stress** (capacity vs. blockage) — 25%
- **Lake/reservoir level** — 15%
- **Elevation** (lower = more risk) — 10%
- **Soil saturation** — 10%
- **Citizen reports** — 5%

An optional **scikit-learn gradient-boosted model** (`flood_model.pkl`) is loaded if present; otherwise the transparent rule-based scorer is used.

### Heatwave Risk (0–1 score)
Based on:
- **Steadman's Heat Index formula** (feels-like temperature)
- **Urban Heat Island offset** (configurable, default +3°C)
- **UV Index** contribution
- **Consecutive hot days** amplifier
- **Wind speed** as a relief factor

---

## 🗣️ Citizen Reporting Flow

1. Resident opens the **Report** page
2. Uploads a photo + GPS location
3. Backend sends the photo to **Gemini Vision API**
4. AI classifies it: `flooded_road`, `blocked_drain`, `heat_haze`, etc.
5. Result is stored and displayed on the map
6. High-confidence reports boost the **flood risk score** for that zone

---

## 👥 Demo Credentials

| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Resident | `resident` | `resident123` |

---

## 📊 Sample Cities Seeded

The seed script populates **Mumbai** zones:
Dharavi · Kurla · Andheri · Worli · Bandra · Dadar · Colaba

To add your city, edit `scripts/seed_data.py` and re-run it.
