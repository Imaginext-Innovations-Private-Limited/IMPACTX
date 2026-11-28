
"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Urban Flood & Heatwave Early-Warning System"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./flood_warning.db"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # OpenWeatherMap API
    OPENWEATHER_API_KEY: str = ""
    OPENWEATHER_BASE_URL: str = "https://api.openweathermap.org/data/2.5"

    # Google Maps / OSRM for routing
    MAPS_API_KEY: str = ""
    OSRM_BASE_URL: str = "http://router.project-osrm.org"

    # Redis (for real-time pub/sub alerts)
    REDIS_URL: str = "redis://localhost:6379"

    # Gemini / Vision AI for citizen photo analysis
    GEMINI_API_KEY: str = ""

    # Email notifications (SMTP)
    EMAIL_ENABLED: bool = False
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_USE_TLS: bool = True

    # Alert thresholds
    FLOOD_RISK_THRESHOLD: float = 0.6
    HEATWAVE_TEMP_THRESHOLD: float = 40.0
    RAINFALL_HIGH_MM: float = 50.0

    # Scheduler interval (seconds)
    FORECAST_REFRESH_SECONDS: int = 1800

    class Config:
        env_file = ".env"


settings = Settings()
