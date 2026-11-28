"""
Phase 6 Comprehensive Test Suite for Sahaaya AI.
Validates Frontend Templates, Web Views, Scheme Catalog API, Static Assets,
Responsive UI Integration, and End-to-End Navigation Workflows.
"""

import sys
import unittest
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from models import db, GovernmentScheme, CitizenProfile


class TestPhase6FrontendAndIntegration(unittest.TestCase):
    """Test suite for Phase 6 Frontend Development & Backend Integration."""

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
    # 1. VIEW ROUTE & TEMPLATE LOADING TESTS
    # =================================================================

    def test_01_home_page_html_loads(self):
        """Test home page renders HTML with proper title, hero section, and updated text."""
        # Test explicit /home route
        response = self.client.get("/home")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertTrue(
            "Your Personal Government Scheme Guide" in html
            or "Your Personal Government Scheme Navigator" in html
        )
        self.assertIn("Welfare Scheme Navigator", html)
        self.assertIn("Track A: Agentic AI for Communities", html)
        self.assertIn("Explore Schemes", html)

        # Verify updated text corrections
        self.assertIn("AI-POWERED SCHEME NAVIGATOR", html)
        self.assertIn("Government Scheme Catalog", html)
        self.assertIn("Source Status Available", html)
        self.assertIn("Rule-based eligibility checks and source-linked information help reduce unsupported answers.", html)
        self.assertNotIn("Verified Scheme Catalog", html)
        self.assertNotIn("Live & Grounded", html)
        self.assertNotIn("prevent AI hallucinations", html)

        # Test root / with Accept: text/html
        response_root = self.client.get("/", headers={"Accept": "text/html"})
        self.assertEqual(response_root.status_code, 200)
        html_root = response_root.get_data(as_text=True)
        self.assertTrue(
            "Your Personal Government Scheme Guide" in html_root
            or "Your Personal Government Scheme Navigator" in html_root
        )
        self.assertIn("AI-POWERED SCHEME NAVIGATOR", html_root)
        self.assertIn("Government Scheme Catalog", html_root)
        self.assertIn("Source Status Available", html_root)

    def test_02_index_json_compatibility_preserved(self):
        """Ensure GET / without text/html continues returning Phase 1 JSON status."""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsNotNone(data)
        self.assertEqual(data.get("status"), "Phase 1 Initialization Complete")
        self.assertIn("health_endpoint", data)

    def test_03_dashboard_page_loads(self):
        """Test citizen dashboard renders metrics, scheme directory, and action shortcuts."""
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Citizen Welfare Dashboard", html)
        self.assertIn("Total Schemes", html)
        self.assertIn("Karnataka State", html)
        self.assertIn("Central Schemes", html)
        self.assertIn("Quick Action Tools", html)

    def test_04_schemes_discovery_page_loads(self):
        """Test scheme discovery page renders search inputs, level/category dropdowns, and grid."""
        response = self.client.get("/schemes")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Explore Government Welfare Schemes", html)
        self.assertIn("schemeSearchInput", html)
        self.assertIn("levelFilterSelect", html)
        self.assertIn("categoryFilterSelect", html)
        self.assertIn("schemesGrid", html)

    def test_05_scheme_detail_page_loads_for_valid_scheme(self):
        """Test scheme detail page renders verified rules, benefits, documents, and badge."""
        response = self.client.get("/schemes/gruha-lakshmi")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Gruha Lakshmi", html)
        self.assertIn("Scheme Benefits", html)
        self.assertIn("Eligibility Criteria", html)
        self.assertIn("Required Documents", html)
        self.assertIn("VERIFIED OFFICIAL DOCUMENT", html)
        self.assertIn("Official Application Procedure", html)

    def test_06_scheme_detail_returns_404_for_unknown_slug(self):
        """Test scheme detail aborts with 404 for nonexistent scheme slug."""
        response = self.client.get("/schemes/unknown-fantasy-scheme")
        self.assertEqual(response.status_code, 404)

    def test_07_eligibility_page_loads(self):
        """Test eligibility checker form loads with non-sensitive demographic fields."""
        response = self.client.get("/eligibility")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Check Your Government Scheme Eligibility", html)
        self.assertIn("applicantAge", html)
        self.assertIn("annualIncome", html)
        self.assertIn("rationCardType", html)
        self.assertIn("Zero Sensitive Data Collection", html)
        self.assertIn("Indicative Assessment Disclaimer", html)

    def test_08_documents_checklist_page_loads(self):
        """Test document checklist loads with privacy notice and scheme selector."""
        response = self.client.get("/documents")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Official Document Preparation Checklist", html)
        self.assertIn("Personal Preparation Only", html)

        # Test pre-selected scheme route
        response_pre = self.client.get("/documents/gruha-lakshmi")
        self.assertEqual(response_pre.status_code, 200)
        html_pre = response_pre.get_data(as_text=True)
        self.assertIn("Gruha Lakshmi", html_pre)

    def test_09_comparison_page_loads(self):
        """Test scheme comparison page loads with multi-select checkboxes."""
        response = self.client.get("/compare")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Compare Government Welfare Schemes", html)
        self.assertIn("Select Schemes to Compare", html)
        self.assertIn("runCompareBtn", html)

    def test_10_assistant_page_loads(self):
        """Test AI Assistant page loads chat window, active agent tools, and safety notice."""
        response = self.client.get("/assistant")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("AI Assistant – Welfare Scheme Navigator", html)
        self.assertIn("chatMessages", html)
        self.assertIn("chatInput", html)
        self.assertIn("Active Agent Tools", html)
        self.assertIn("search_schemes", html)

    # =================================================================
    # 2. SCHEME CATALOG REST API TESTS
    # =================================================================

    def test_11_api_schemes_list_all(self):
        """Test GET /api/schemes returns all seeded active schemes."""
        response = self.client.get("/api/schemes")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("total"), 10)
        schemes = data.get("schemes", [])
        self.assertEqual(len(schemes), 10)
        slugs = [s["slug"] for s in schemes]
        self.assertIn("gruha-lakshmi", slugs)
        self.assertIn("pm-kisan", slugs)

    def test_12_api_schemes_filtering(self):
        """Test GET /api/schemes filters by level, state, and search query."""
        # Filter by State level
        res_state = self.client.get("/api/schemes?level=State")
        data_state = res_state.get_json()
        self.assertTrue(data_state["success"])
        for s in data_state["schemes"]:
            self.assertEqual(s["government_level"], "State")

        # Filter by query keyword
        res_q = self.client.get("/api/schemes?q=farmer")
        data_q = res_q.get_json()
        self.assertTrue(data_q["success"])
        self.assertGreaterEqual(data_q["total"], 1)
        found_slugs = [s["slug"] for s in data_q["schemes"]]
        self.assertIn("pm-kisan", found_slugs)

    def test_13_api_schemes_categories_endpoint(self):
        """Test GET /api/schemes/categories returns metadata for discovery dropdowns."""
        response = self.client.get("/api/schemes/categories")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        self.assertIn("categories", data)
        self.assertIn("levels", data)
        self.assertIn("states", data)
        self.assertIn("Women & Child Development", data["categories"])
        self.assertIn("State", data["levels"])
        self.assertIn("Central", data["levels"])

    def test_14_api_schemes_get_single(self):
        """Test GET /api/schemes/<slug> returns full details with rules and documents."""
        response = self.client.get("/api/schemes/gruha-lakshmi")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data["success"])
        scheme = data["scheme"]
        self.assertEqual(scheme["slug"], "gruha-lakshmi")
        self.assertIn("rules", scheme)
        self.assertIn("documents", scheme)
        self.assertIn("steps", scheme)
        self.assertGreaterEqual(len(scheme["rules"]), 1)
        self.assertGreaterEqual(len(scheme["documents"]), 1)

    def test_15_api_schemes_compare_endpoint(self):
        """Test POST /api/schemes/compare executes comparison of 2 schemes."""
        payload = {"slugs": ["gruha-lakshmi", "yuva-nidhi"]}
        response = self.client.post("/api/schemes/compare", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("total_compared"), 2)
        schemes = data.get("schemes", [])
        self.assertEqual(len(schemes), 2)
        self.assertIn("comparison_notes", data)
        self.assertIn("disclaimer", data)

    def test_16_api_schemes_compare_validation_rejection(self):
        """Test POST /api/schemes/compare rejects payload with fewer than 2 slugs."""
        res_single = self.client.post("/api/schemes/compare", json={"slugs": ["gruha-lakshmi"]})
        self.assertEqual(res_single.status_code, 400)

        res_non_json = self.client.post("/api/schemes/compare", data="not-json")
        self.assertEqual(res_non_json.status_code, 400)

    # =================================================================
    # 3. STATIC ASSETS ACCESSIBILITY TESTS
    # =================================================================

    def test_17_static_css_and_js_files_accessible(self):
        """Verify all Phase 6 custom stylesheets and JavaScript files are served with HTTP 200."""
        assets = [
            "/static/css/style.css",
            "/static/css/responsive.css",
            "/static/js/app.js",
            "/static/js/schemes.js",
            "/static/js/eligibility.js",
            "/static/js/documents.js",
            "/static/js/compare.js",
            "/static/js/assistant.js",
        ]
        for asset_url in assets:
            res = self.client.get(asset_url)
            self.assertEqual(
                res.status_code,
                200,
                f"Static file '{asset_url}' failed to load (HTTP {res.status_code})."
            )
            res.close()

    # =================================================================
    # 4. PRIVACY, PII GUARDS & DETERMINISTIC INTEGRITY
    # =================================================================

    def test_18_pii_guards_strictly_block_aadhaar_and_pan(self):
        """Confirm that CitizenProfile strictly prohibits Aadhaar and PAN numbers."""
        profile = CitizenProfile()
        # Attempt setting a 12-digit Aadhaar number
        with self.assertRaises(ValueError) as ctx:
            profile.district = "1234 5678 9012"
        self.assertIn("PII Violation", str(ctx.exception))

        # Attempt setting a PAN number
        with self.assertRaises(ValueError) as ctx:
            profile.occupation = "ABCDE1234F"
        self.assertIn("PII Violation", str(ctx.exception))

    def test_19_deterministic_eligibility_status_preservation(self):
        """Verify all 4 deterministic statuses are returned correctly through the API."""
        # 1. Potentially eligible for Gruha Lakshmi
        res_eligible = self.client.post("/api/eligibility/check", json={
            "slug": "gruha-lakshmi",
            "profile": {
                "state": "Karnataka",
                "gender": "Female",
                "is_female_head_of_family": True,
                "ration_card_type": "BPL",
                "is_bpl_card_holder": True
            }
        })
        self.assertEqual(res_eligible.status_code, 200)
        self.assertEqual(res_eligible.get_json()["data"]["overall_status"], "potentially_eligible")

        # 2. Not eligible (State != Karnataka)
        res_ineligible = self.client.post("/api/eligibility/check", json={
            "slug": "gruha-lakshmi",
            "profile": {
                "state": "Maharashtra",
                "gender": "Female",
                "is_female_head_of_family": True,
                "ration_card_type": "BPL"
            }
        })
        self.assertEqual(res_ineligible.status_code, 200)
        self.assertEqual(res_ineligible.get_json()["data"]["overall_status"], "not_eligible")

        # 3. Needs more information (Empty profile)
        res_needs_info = self.client.post("/api/eligibility/check", json={
            "slug": "gruha-lakshmi",
            "profile": {}
        })
        self.assertEqual(res_needs_info.status_code, 200)
        self.assertEqual(res_needs_info.get_json()["data"]["overall_status"], "needs_more_information")

    def test_20_clarification_api_structure(self):
        """Verify API returns structured clarification objects with readable question strings."""
        res = self.client.post("/api/eligibility/check", json={
            "slug": "gruha-lakshmi",
            "profile": {}
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()["data"]
        self.assertEqual(data["overall_status"], "needs_more_information")
        questions = data.get("next_recommended_questions", [])
        self.assertGreaterEqual(len(questions), 1)

        for q in questions:
            self.assertIsInstance(q, dict)
            self.assertIn("field_name", q)
            self.assertIn("question", q)
            self.assertTrue(isinstance(q["question"], str) and len(q["question"].strip()) > 0)
            self.assertNotIn("[object Object]", q["question"])
            self.assertNotIn("undefined", q["question"].lower())
            self.assertNotIn("null", q["question"].lower())

    def test_21_frontend_clarification_rendering_node_contract(self):
        """Verify frontend JS extracts human-readable text and never outputs [object Object]."""
        import subprocess
        js_code = """
        const { extractClarificationText, renderFollowUpQuestions } = require('./static/js/eligibility.js');
        const tests = [
          {
            input: [{ field_name: 'gender', question: 'What is your gender?' }],
            expectedHtmlContains: 'What is your gender?',
            mustNotContain: '[object Object]'
          },
          {
            input: ['What is your household income?'],
            expectedHtmlContains: 'What is your household income?',
            mustNotContain: '[object Object]'
          },
          {
            input: [{ field_name: 'annual_household_income' }],
            expectedHtmlContains: 'Please provide details for annual household income.',
            mustNotContain: '[object Object]'
          },
          {
            input: [null, undefined, '[object Object]', { question: '[object Object]' }, {}],
            expectedOutput: ''
          },
          {
            input: [],
            expectedOutput: ''
          }
        ];

        for (const t of tests) {
          const res = renderFollowUpQuestions(t.input);
          if (t.expectedOutput !== undefined && res !== t.expectedOutput) {
            console.error(`Failed empty test: got "${res}" expected "${t.expectedOutput}"`);
            process.exit(1);
          }
          if (t.expectedHtmlContains && !res.includes(t.expectedHtmlContains)) {
            console.error(`Failed contains test: "${res}" does not contain "${t.expectedHtmlContains}"`);
            process.exit(1);
          }
          if (t.mustNotContain && res.includes(t.mustNotContain)) {
            console.error(`Failed must-not-contain: "${res}" contains "${t.mustNotContain}"`);
            process.exit(1);
          }
        }
        console.log('ALL_CLARIFICATION_TESTS_PASSED');
        """
        proc = subprocess.run(
            ["node", "-e", js_code],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True
        )
        self.assertEqual(proc.returncode, 0, f"Node test failed: {proc.stderr}")
        self.assertIn("ALL_CLARIFICATION_TESTS_PASSED", proc.stdout)


if __name__ == "__main__":
    unittest.main()
