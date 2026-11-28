"""
Sahaaya AI - Configuration Module
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory is Sahaaya_AI root
BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(BASE_DIR / ".env")


def _resolve_database_uri():
    """Resolve SQLite URI to an absolute path on Windows to avoid CWD ambiguity."""
    data_dir = BASE_DIR / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    default_db_file = data_dir / "sahaaya.db"

    env_uri = os.getenv("DATABASE_URL")
    if not env_uri:
        return f"sqlite:///{default_db_file.as_posix()}"

    if env_uri.startswith("sqlite:///") and not (":" in env_uri[10:] or env_uri.startswith("sqlite:////")):
        rel_path = env_uri.replace("sqlite:///", "")
        abs_file = (BASE_DIR / rel_path).resolve()
        abs_file.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{abs_file.as_posix()}"

    return env_uri


class Config:
    """Base application configuration."""

    # Project directories
    BASE_DIR = BASE_DIR
    DATA_DIR = BASE_DIR / "data"
    DOCUMENTS_DIR = DATA_DIR / "raw_documents"
    FAISS_INDEX_DIR = DATA_DIR / "faiss_index"

    # Flask Core
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
     raise RuntimeError("SECRET_KEY is not configured. Set it in your .env file.")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "1").lower() in ("1", "true", "yes")

    # Database Configuration (SQLite)
    DATABASE_FILE = DATA_DIR / "sahaaya.db"
    SQLALCHEMY_DATABASE_URI = _resolve_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Gemini Agent Configuration (via google-genai)
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    # Configurable model - never hardcoded
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Retrieval Engine (FAISS with SQLite FTS5 fallback capability)
    RETRIEVAL_BACKEND = os.getenv("RETRIEVAL_BACKEND", "sqlite_fts5")
    EMBEDDING_MODEL_NAME = os.getenv(
        "EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2"
    )

    # Server settings
    PORT = int(os.getenv("PORT", "8000"))
    HOST = os.getenv("HOST", "127.0.0.1")

    # Policy and Compliance
    STRICT_NO_PII = True
    INDICATIVE_ONLY_DISCLAIMER = (
        "Sahaaya AI provides indicative eligibility assessment only based on "
        "published guidelines. It does not constitute guaranteed government approval. "
        "Final approval is subject to document verification by competent government authorities."
    )


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False


# Map of configuration environments
config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
