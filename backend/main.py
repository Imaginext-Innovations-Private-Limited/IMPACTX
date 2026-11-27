"""
Farm Advisor – FastAPI Backend
Entry point: uvicorn main:app --reload --port 8000
Sprint 4: Real Gemini Vision, Sarvam Speech, Agmarknet Live, dotenv config
"""
import config  # loads .env via python-dotenv at import time
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
import json

from database import engine, ensure_sqlite_columns
import models
from routers import (
    commodities,
    voice,
    scan,
    weather,
    markets,
    news,
    dairy,
    notifications,
    finance,
    help_directory,
    livestock_pets,
)
import whatsapp_bot
from seed_data import seed

# Create all tables (Sprint 1, 2 & 3)
models.Base.metadata.create_all(bind=engine)
ensure_sqlite_columns()

# Seed on startup
seed()

app = FastAPI(
    title="Farm Advisor API",
    description="Multilingual AI-powered farm advisory platform for Karnataka farmers",
    version="4.0.0-sprint4",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS for local React dev (Vite default port 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploaded images
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Sprint 1 Routers
app.include_router(commodities.router)
app.include_router(voice.router)
app.include_router(scan.router)

# Sprint 2 Routers
app.include_router(weather.router)
app.include_router(markets.router)
app.include_router(news.router)
app.include_router(dairy.router)

# Sprint 3 Routers
app.include_router(notifications.router)
app.include_router(finance.router)

# Sprint 5 Routers (Help Directory & Livestock/Pet Marketplace)
app.include_router(help_directory.router)
app.include_router(livestock_pets.router)

# WhatsApp Cloud API Webhook & Local Simulation
app.include_router(whatsapp_bot.router)


def _parse_float(val):
    if val is None or val == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@app.post("/api/voice-query")
async def api_voice_query(request: Request):
    """
    Unified live voice query endpoint supporting JSON, Form, and audio input
    with optional lat, lon, location_name, and user_id context.
    """
    content_type = request.headers.get("content-type", "")
    query_text = None
    audio_bytes = None
    lang = "auto"
    parsed_keyterms = None
    lat = None
    lon = None
    location_name = None
    user_id = None

    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            body = {}
        query_text = body.get("text") or body.get("query") or ""
        lang = body.get("language", "kn-IN")
        parsed_keyterms = body.get("keyterms")
        lat = _parse_float(body.get("lat"))
        lon = _parse_float(body.get("lon"))
        location_name = body.get("location_name")
        user_id = body.get("user_id")
    elif "multipart/form-data" in content_type:
        form = await request.form()
        audio = form.get("audio")
        query_text = form.get("text") or form.get("query")
        lang = form.get("language", "auto")
        keyterms_val = form.get("keyterms")
        if keyterms_val:
            try:
                parsed_keyterms = json.loads(keyterms_val)
            except Exception:
                parsed_keyterms = [k.strip() for k in str(keyterms_val).split(",") if k.strip()]
        if audio and hasattr(audio, "read"):
            audio_bytes = await audio.read()
        lat = _parse_float(form.get("lat"))
        lon = _parse_float(form.get("lon"))
        location_name = form.get("location_name")
        user_id = form.get("user_id")
    else:
        params = dict(request.query_params)
        query_text = params.get("text") or params.get("query") or ""
        lang = params.get("language", "kn-IN")
        lat = _parse_float(params.get("lat"))
        lon = _parse_float(params.get("lon"))
        location_name = params.get("location_name")
        user_id = params.get("user_id")

    try:
        return await voice.process_voice_or_text(
            query_text=query_text,
            audio_bytes=audio_bytes,
            language=lang,
            keyterms=parsed_keyterms,
            lat=lat,
            lon=lon,
            location_name=location_name,
            user_id=user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))


@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": "Farm Advisor",
        "sprint": 2,
        "version": "2.0.0",
        "modules": [
            "commodities",
            "voice",
            "scan",
            "weather",
            "markets",
            "news",
            "dairy",
            "finance",
            "finance_wealth",
            "help_directory",
            "livestock_pets",
        ],
    }


@app.get("/api")
def api_root():
    return {
        "message": "Farm Advisor API – Sprint 1 & 2 Active",
        "endpoints": {
            "commodities": "/api/commodities",
            "ticker": "/api/commodities/ticker",
            "weather": "/api/weather/forecast",
            "weather_locations": "/api/weather/locations",
            "market_analytics": "/api/markets/{commodity}",
            "news": "/api/news",
            "news_categories": "/api/news/categories",
            "dairy_rates": "/api/dairy/procurement-rates",
            "dairy_breeds": "/api/dairy/breeds",
            "dairy_feed": "/api/dairy/feed-plans",
            "dairy_breeding": "/api/dairy/breeding-guide",
            "dairy_disease": "/api/dairy/disease-advisor",
            "dairy_doctors": "/api/dairy/doctors",
            "dairy_cattle": "/api/dairy/cattle",
            "finance_ledger": "/api/finance/ledger",
            "finance_wealth_allocate": "/api/finance/wealth/allocate",
            "finance_wealth_pan_loans": "/api/finance/wealth/pan-loans",
            "finance_wealth_loans": "/api/finance/wealth/loans",
            "finance_wealth_invest_plan": "/api/finance/wealth/invest-plan",
            "finance_wealth_calculate_returns": "/api/finance/wealth/calculate-returns",
            "help_contacts": "/api/help/contacts",
            "livestock_pets": "/api/livestock-pets",
            "voice": "/api/voice/query",
            "scan": "/api/scan",
            "docs": "/api/docs",
        },
    }
