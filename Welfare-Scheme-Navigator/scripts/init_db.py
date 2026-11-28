"""
Database Initialization Script for Sahaaya AI.
Creates all database tables based on SQLAlchemy models.
"""

import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from models import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("init_db")


def init_database(config_name="development"):
    """Initialize database tables idempotently."""
    app = create_app(config_name)
    with app.app_context():
        logger.info(f"Initializing database at: {app.config['SQLALCHEMY_DATABASE_URI']}")
        db.create_all()
        logger.info("Database tables verified and initialized successfully.")


if __name__ == "__main__":
    init_database()
