import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-insecure-jwt-secret-change-me")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-insecure-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=7)

    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/learnable_ai")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "")

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
        ).split(",")
        if origin.strip()
    ]

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip()

    WHISPER_API_URL = os.getenv("WHISPER_API_URL", "").strip()
    WHISPER_API_KEY = os.getenv("WHISPER_API_KEY", "").strip()
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-1").strip()

    MAX_PDF_SIZE_MB = int(os.getenv("MAX_PDF_SIZE_MB", "15"))
    MAX_AUDIO_SIZE_MB = int(os.getenv("MAX_AUDIO_SIZE_MB", "25"))
    MAX_CONTENT_LENGTH = max(MAX_PDF_SIZE_MB, MAX_AUDIO_SIZE_MB) * 1024 * 1024

    UPLOAD_FOLDER = os.getenv(
        "UPLOAD_FOLDER",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "uploads"),
    )
