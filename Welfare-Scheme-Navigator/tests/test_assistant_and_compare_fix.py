"""
Regression Test Suite for Assistant Fallback Message & Scheme Comparison Fixes in Sahaaya AI.

Validates:
1. AI Assistant Fallback Messaging:
   - Removal of long technical diagnostic messages ("Operating in Fallback Mode...", "SQLite FTS5...", "deterministic tool dispatcher...").
   - Display of user-friendly notification ("AI assistance is temporarily limited...").
   - Preservation of deterministic fallback functionality (retrieving documents, eligibility assessment, citations).
   - Accurate reporting of Gemini API status via /api/agent/status.
   - Normal rendering of live/mocked Gemini responses without fallback warnings.

2. Scheme Comparison Workflow:
   - Successful comparison of two schemes.
   - Successful comparison of three schemes with all attributes.
   - Clear validation error when only one scheme is selected.
   - Rejection of empty selections.
   - Safe error handling for invalid scheme identifiers.
   - Correct deduplication of duplicate selections.
   - Rejection when more than three schemes are submitted.
   - Presence of in-page comparison error containers in compare.html.
   - Safe definition of getComparedSlugs() in static assets to prevent ReferenceError.
"""

import sys
import unittest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from models import db, GovernmentScheme
from agent.tools import tool_compare_schemes, execute_tool
from agent.agent_orchestrator import AgentOrchestrator


class TestAssistantAndCompareFix(unittest.TestCase):
    """Test suite for AI Assistant UI Fallback fixes and Scheme Comparison workflow."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app("testing")
        with cls.app.app_context():
            db.create_all()
            from scripts.seed_schemes import seed_database
            seed_database(app=cls.app)

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    # =================================================================
    # PART 1: AI ASSISTANT FALLBACK UI & MESSAGING TESTS
    # =================================================================

    def test_01_fallback_mode_no_long_technical_diagnostic_message(self):
        """Orchestrator in fallback mode must not output technical diagnostic messages in user prose."""
        orchestrator = AgentOrchestrator()
        # Force a query that routes through fallback handler
        res = orchestrator.process_message(
            message="What are the required documents for Gruha Lakshmi?",
            conversation_id="test_fallback_msg_session"
        )
        self.assertTrue(res.get("success"))
        msg = res.get("assistant_message", "")

        # Verify old technical strings are NOT present
        self.assertNotIn("Operating in Fallback Mode", msg)
        self.assertNotIn("deterministic tool dispatcher", msg)
        self.assertNotIn("SQLite FTS5", msg)
        self.assertNotIn("Live Gemini cloud synthesis is currently operating in offline fallback mode", msg)
        self.assertNotIn("ConnectError", msg)
        self.assertNotIn("gaierror", msg)
        self.assertNotIn("RESOURCE_EXHAUSTED", msg)

        # Verify friendly notification is present
        self.assertIn("AI assistance is temporarily limited", msg)
        self.assertIn("You can still explore schemes and access available scheme information", msg)

    def test_02_assistant_page_html_no_technical_message(self):
        """GET /assistant HTML must not render the old technical diagnostic banner."""
        res = self.client.get("/assistant")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertNotIn("Operating in Fallback Mode: The conversational agent is answering", html)
        self.assertNotIn("SQLite FTS5 index", html)
        self.assertNotIn("deterministic tool dispatcher", html)
        self.assertIn("AI assistance is temporarily limited", html)

    def test_03_fallback_response_remains_functional(self):
        """Fallback mode must remain completely functional for welfare scheme navigation."""
        orchestrator = AgentOrchestrator()
        res = orchestrator.process_message(
            message="What documents are needed for Gruha Lakshmi?",
            conversation_id="test_fallback_func_session"
        )
        self.assertTrue(res.get("success"))
        self.assertTrue(res.get("is_fallback_mode"))
        msg = res.get("assistant_message", "")
        # Must still return actual document checklist
        self.assertIn("Gruha Lakshmi", msg)
        self.assertIn("Mandatory Documents Checklist", msg)
        self.assertIn("Ration Card", msg)

    def test_04_api_status_accurately_reports_gemini_availability(self):
        """GET /api/agent/status accurately returns internal diagnostic status."""
        res = self.client.get("/api/agent/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("gemini_status", data)
        gs = data["gemini_status"]
        self.assertIn("available", gs)
        self.assertIn("api_key_configured", gs)
        self.assertIn("configured_model", gs)
        self.assertIn("supported_tools", data)
        self.assertEqual(len(data["supported_tools"]), 6)

    def test_05_mocked_live_gemini_response_rendered_correctly(self):
        """When Gemini generates content successfully, it is rendered without fallback notices."""
        orchestrator = AgentOrchestrator()
        mock_response = MagicMock()
        mock_response.function_calls = None
        mock_response.text = "Here is the verified information for your requested scheme."
        mock_response.candidates = [MagicMock(content=MagicMock())]

        with patch.object(orchestrator.gemini_client, "is_available", return_value=True), \
             patch.object(orchestrator.gemini_client, "generate_content", return_value=mock_response):
            res = orchestrator.process_message(
                message="Tell me about PM-KISAN",
                conversation_id="test_live_gemini_session"
            )
            self.assertTrue(res.get("success"))
            self.assertFalse(res.get("is_fallback_mode"))
            msg = res.get("assistant_message", "")
            self.assertIn("Here is the verified information", msg)
            self.assertNotIn("AI assistance is temporarily limited", msg)
            self.assertNotIn("Operating in Fallback Mode", msg)

    # =================================================================
    # PART 2: SCHEME COMPARISON WORKFLOW TESTS
    # =================================================================

    def test_06_scheme_compare_two_schemes_success(self):
        """POST /api/schemes/compare successfully compares two valid schemes."""
        payload = {"slugs": ["gruha-lakshmi", "yuva-nidhi"]}
        res = self.client.post("/api/schemes/compare", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("total_compared"), 2)
        self.assertEqual(len(data.get("schemes", [])), 2)

        # Verify attributes exist for each scheme
        for s in data["schemes"]:
            self.assertIn("scheme_name", s)
            self.assertIn("department", s)
            self.assertIn("benefits", s)
            self.assertIn("key_eligibility_criteria", s)
            self.assertIn("mandatory_documents", s)
            self.assertIn("official_portal_url", s)

    def test_07_scheme_compare_three_schemes_success(self):
        """POST /api/schemes/compare successfully compares three valid schemes."""
        payload = {"slugs": ["gruha-lakshmi", "yuva-nidhi", "pm-kisan"]}
        res = self.client.post("/api/schemes/compare", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("total_compared"), 3)
        self.assertEqual(len(data.get("schemes", [])), 3)

        slugs = [s["scheme_slug"] for s in data["schemes"]]
        self.assertIn("gruha-lakshmi", slugs)
        self.assertIn("yuva-nidhi", slugs)
        self.assertIn("pm-kisan", slugs)

    def test_08_scheme_compare_one_scheme_validation_error(self):
        """POST /api/schemes/compare rejects a single scheme selection with HTTP 400."""
        payload = {"slugs": ["gruha-lakshmi"]}
        res = self.client.post("/api/schemes/compare", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("at least two distinct schemes", data.get("error", ""))

    def test_09_scheme_compare_empty_selection_rejected(self):
        """POST /api/schemes/compare rejects empty scheme list with HTTP 400."""
        payload = {"slugs": []}
        res = self.client.post("/api/schemes/compare", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))

    def test_10_scheme_compare_invalid_scheme_identifiers(self):
        """POST /api/schemes/compare returns clear error when non-existent scheme is requested."""
        payload = {"slugs": ["gruha-lakshmi", "nonexistent-scheme-xyz"]}
        res = self.client.post("/api/schemes/compare", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("could not be found", data.get("error", ""))
        self.assertIn("nonexistent-scheme-xyz", data.get("error", ""))

    def test_11_scheme_compare_duplicate_selections_handled(self):
        """POST /api/schemes/compare deduplicates identical schemes."""
        # Duplicates resulting in < 2 unique schemes
        payload_dup1 = {"slugs": ["gruha-lakshmi", "gruha-lakshmi"]}
        res1 = self.client.post("/api/schemes/compare", json=payload_dup1)
        self.assertEqual(res1.status_code, 400)
        data1 = res1.get_json()
        self.assertIn("at least two distinct schemes", data1.get("error", ""))

        # Duplicates with 2 distinct schemes total
        payload_dup2 = {"slugs": ["gruha-lakshmi", "yuva-nidhi", "gruha-lakshmi"]}
        res2 = self.client.post("/api/schemes/compare", json=payload_dup2)
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2.get("total_compared"), 2)

    def test_12_scheme_compare_more_than_three_rejected(self):
        """POST /api/schemes/compare rejects comparing more than 3 schemes."""
        payload = {"slugs": ["gruha-lakshmi", "yuva-nidhi", "pm-kisan", "anna-bhagya"]}
        res = self.client.post("/api/schemes/compare", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("maximum of 3 schemes", data.get("error", ""))

    def test_13_compare_page_html_renders_controls_and_alert(self):
        """GET /compare renders comparison page with error alert container and checkboxes."""
        res = self.client.get("/compare")
        self.assertEqual(res.status_code, 200)
        html = res.get_data(as_text=True)

        self.assertIn("Compare Government Welfare Schemes", html)
        self.assertIn("id=\"comparisonAlert\"", html)
        self.assertIn("id=\"runCompareBtn\"", html)
        self.assertIn("id=\"schemeCheckboxesContainer\"", html)
        self.assertIn("cmp_gruha-lakshmi", html)
        self.assertIn("cmp_yuva-nidhi", html)
        self.assertIn("cmp_pm-kisan", html)

    def test_14_compare_js_assets_contain_safe_getComparedSlugs(self):
        """Verify that getComparedSlugs() is defined in compare.js and app.js to prevent ReferenceError."""
        compare_js_path = PROJECT_ROOT / "static" / "js" / "compare.js"
        app_js_path = PROJECT_ROOT / "static" / "js" / "app.js"

        self.assertTrue(compare_js_path.exists())
        self.assertTrue(app_js_path.exists())

        compare_js = compare_js_path.read_text(encoding="utf-8")
        app_js = app_js_path.read_text(encoding="utf-8")

        self.assertIn("function getComparedSlugs", compare_js)
        self.assertIn("function getComparedSlugs", app_js)


if __name__ == "__main__":
    unittest.main()
