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
    """Idempotently add missing columns and tables to existing SQLite database."""
    table_column_specs = {
        "user_locations": {
            "language_code": "VARCHAR(20)",
            "awaiting_language_choice": "BOOLEAN DEFAULT 0",
        },
        "mandi_price_cache": {
            "commodity_id": "INTEGER",
            "category": "VARCHAR(50)",
            "unit": "VARCHAR(20) DEFAULT 'quintal'",
            "previous_price": "FLOAT",
        },
        "two_week_history": {
            "state": "VARCHAR(50) DEFAULT 'Karnataka'",
        },
        "seasonal_historical_prices": {
            "state": "VARCHAR(50) DEFAULT 'Karnataka'",
        },
    }
    try:
        with engine.begin() as conn:
            # Create dairy_cache table if it doesn't exist
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS dairy_cache (
                    cache_key VARCHAR(150) PRIMARY KEY,
                    endpoint VARCHAR(50),
                    state VARCHAR(60),
                    language VARCHAR(20),
                    data_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP
                )
            """))
            for table_name, col_dict in table_column_specs.items():
                rows = conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
                if not rows:
                    continue
                existing_cols = {row[1] for row in rows}
                for col_name, col_type in col_dict.items():
                    if col_name not in existing_cols:
                        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"))
                        logger.info("[DB Migration] Added column %s.%s (%s)", table_name, col_name, col_type)
    except Exception as exc:
        logger.error("[DB Migration] Failed ensuring SQLite columns: %s", exc, exc_info=True)
