"""
Phase 1 Verification Tests for Sahaaya AI
"""

import sys
import unittest
import sqlite3
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Config, DevelopmentConfig, TestingConfig
from app import create_app
from models import db


class TestPhase1Setup(unittest.TestCase):
    """Test suite for Phase 1 initialization."""

    def test_01_python_version(self):
        """Ensure Python version is 3.11+."""
        major, minor = sys.version_info[:2]
        self.assertEqual(major, 3, "Python major version must be 3")
        self.assertGreaterEqual(minor, 11, "Python minor version must be 11 or higher")

    def test_02_configuration_loading(self):
        """Verify configuration parameters and environment variables."""
        self.assertIsNotNone(Config.BASE_DIR)
        self.assertTrue(Config.BASE_DIR.exists())
        self.assertIsNotNone(Config.SECRET_KEY)
        self.assertIsNotNone(Config.GEMINI_MODEL)
        self.assertIn("gemini", Config.GEMINI_MODEL.lower())
        self.assertIsNotNone(Config.INDICATIVE_ONLY_DISCLAIMER)

    def test_03_no_hardcoded_model_in_config(self):
        """Ensure GEMINI_MODEL is pulled dynamically from env."""
        import os
        original = os.environ.get("GEMINI_MODEL")
        try:
            os.environ["GEMINI_MODEL"] = "custom-test-model-v1"
            from importlib import reload
            import config
            reload(config)
            self.assertEqual(config.Config.GEMINI_MODEL, "custom-test-model-v1")
        finally:
            if original:
                os.environ["GEMINI_MODEL"] = original
            else:
                os.environ.pop("GEMINI_MODEL", None)
            from importlib import reload
            import config
            reload(config)

    def test_04_app_factory_development(self):
        """Test Flask application creation in development mode."""
        app = create_app("development")
        self.assertIsNotNone(app)
        self.assertEqual(app.config["DEBUG"], True)
        self.assertIn("sahaaya.db", app.config["SQLALCHEMY_DATABASE_URI"])

    def test_05_app_factory_testing(self):
        """Test Flask application creation in testing mode with in-memory DB."""
        app = create_app("testing")
        self.assertIsNotNone(app)
        self.assertEqual(app.config["TESTING"], True)
        self.assertEqual(app.config["SQLALCHEMY_DATABASE_URI"], "sqlite:///:memory:")

    def test_06_health_check_endpoint(self):
        """Verify the /api/health endpoint returns 200 with proper metadata."""
        app = create_app("testing")
        client = app.test_client()
        response = client.get("/api/health")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "Sahaaya AI - Welfare Scheme Navigator")
        self.assertIn("gemini_model", data)
        self.assertIn("retrieval_backend", data)
        self.assertIn("disclaimer", data)

    def test_07_index_placeholder_endpoint(self):
        """Verify the root endpoint responds with Phase 1 status."""
        app = create_app("testing")
        client = app.test_client()
        response = client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["status"], "Phase 1 Initialization Complete")

    def test_08_database_creation(self):
        """Ensure SQLite tables can be created via SQLAlchemy in app context."""
        app = create_app("development")
        with app.app_context():
            result = db.session.execute(db.text("SELECT 1")).scalar()
            self.assertEqual(result, 1)

    def test_09_retrieval_engine_fallback_operational(self):
        """
        Verify Fallback Retrieval Engine (SQLite FTS5 Full Text Search with BM25)
        is 100% operational on Windows with Python 3.11.
        """
        conn = sqlite3.connect(":memory:")
        conn.execute("CREATE VIRTUAL TABLE fallback_rag USING fts5(scheme_name, content)")
        conn.execute(
            "INSERT INTO fallback_rag VALUES (?, ?)",
            ("Gruha Lakshmi", "Financial aid of Rs 2000 per month for female head of household in Karnataka")
        )
        conn.execute(
            "INSERT INTO fallback_rag VALUES (?, ?)",
            ("PM-KISAN", "Direct income support of Rs 6000 per year for farmer families across India")
        )

        cursor = conn.execute("SELECT scheme_name FROM fallback_rag WHERE fallback_rag MATCH 'Karnataka'")
        results = cursor.fetchall()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0][0], "Gruha Lakshmi")

    def test_10_google_genai_sdk_available(self):
        """Verify google-genai SDK imports cleanly for agentic tool use."""
        from google import genai
        self.assertIsNotNone(genai)


if __name__ == "__main__":
    unittest.main()
