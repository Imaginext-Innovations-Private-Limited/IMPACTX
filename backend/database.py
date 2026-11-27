"""Database configuration and session management."""
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger("database")

SQLALCHEMY_DATABASE_URL = "sqlite:///./farm_advisor.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_sqlite_columns():
    """Idempotently add missing columns to existing SQLite tables (e.g., user_locations)."""
    required_columns = {
        "language_code": "VARCHAR(20)",
        "awaiting_language_choice": "BOOLEAN DEFAULT 0",
    }
    try:
        with engine.begin() as conn:
            rows = conn.execute(text("PRAGMA table_info(user_locations)")).fetchall()
            if not rows:
                return
            existing_cols = {row[1] for row in rows}
            for col_name, col_type in required_columns.items():
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE user_locations ADD COLUMN {col_name} {col_type}"))
                    logger.info("[DB Migration] Added column user_locations.%s (%s)", col_name, col_type)
    except Exception as exc:
        logger.error("[DB Migration] Failed ensuring SQLite columns: %s", exc, exc_info=True)
