"""
Urban Flood & Heatwave Early-Warning System
FastAPI Backend Entry Point
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn

from app.api import flood, heatwave, alerts, routes, reports, auth
from app.services.scheduler import start_scheduler, stop_scheduler
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    await init_db()
    await start_scheduler()
    yield
    await stop_scheduler()


app = FastAPI(
    title="Urban Flood & Heatwave Early-Warning API",
    description="Multimodal early-warning system combining rainfall forecasts, drainage data, citizen photos, and AI predictions.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (citizen-uploaded photos)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Routers
app.include_router(auth.router,     prefix="/api/auth",     tags=["Auth"])
app.include_router(flood.router,    prefix="/api/flood",    tags=["Flood"])
app.include_router(heatwave.router, prefix="/api/heatwave", tags=["Heatwave"])
app.include_router(alerts.router,   prefix="/api/alerts",   tags=["Alerts"])
app.include_router(routes.router,   prefix="/api/routes",   tags=["Safe Routes"])
app.include_router(reports.router,  prefix="/api/reports",  tags=["Citizen Reports"])


@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "system": "Urban Flood & Heatwave Early-Warning System"}


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
