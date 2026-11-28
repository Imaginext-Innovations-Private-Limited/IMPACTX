"""
Phase 3 Test Suite for Sahaaya AI.
Comprehensive tests for Deterministic EligibilityEngine, DocumentEngine, and REST API Blueprints.
"""

import sys
import unittest
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from models import (
    db,
    GovernmentScheme,
    SchemeEligibilityRule,
    SchemeDocument,
    SchemeApplicationStep,
    CitizenProfile,
)
from engine.eligibility_engine import EligibilityEngine
from engine.document_engine import DocumentEngine
from scripts.seed_schemes import seed_database


class TestPhase3EligibilityAndDocuments(unittest.TestCase):
    """Test suite for Phase 3 Deterministic Eligibility and Document Checklist Engines."""

    @classmethod
    def setUpClass(cls):
        """Set up in-memory app and seed the verified catalog once for the test suite."""
        cls.app = create_app("testing")
        with cls.app.app_context():
            db.create_all()
            seed_database(app=cls.app)

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()

    def tearDown(self):
        self.app_context.pop()

    # --- 1. Operator Tests ---
    def test_01_all_supported_operators(self):
        """Verify each of the 8 supported operators (==, !=, <=, >=, <, >, in, not_in)."""
        scheme = GovernmentScheme(
            name="Operator Test Scheme",
            slug="op-test-scheme",
            description="Testing all comparison operators.",
            category="Testing",
            government_level="State",
            state="Karnataka",
            department="Dept of Testing",
            official_url="https://karnataka.gov.in/test",
            benefits="Test benefits.",
            active_status="Active",
            verification_status="Verified",
        )
        db.session.add(scheme)
        db.session.flush()

        try:
            rules = [
                SchemeEligibilityRule(
                    scheme_id=scheme.id,
                    rule_name="Equality Test",
                    field_name="gender",
                    operator="==",
                    expected_value="Female",
                    description="Must be Female",
                    source_reference="GO 1",
                ),
                SchemeEligibilityRule(
                    scheme_id=scheme.id,
                    rule_name="Inequality Test",
                    field_name="occupation",
                    operator="!=",
                    expected_value="Government Employee",
                    description="Must not be a Government Employee",
                    source_reference="GO 2",
                ),
                SchemeEligibilityRule(
                    scheme_id=scheme.id,
                    rule_name="Less Than Equal",
                    field_name="annual_household_income",
                    operator="<=",
                    expected_value="200000",
                    description="Income <= 200,000",
                    source_reference="GO 3",
                ),
                SchemeEligibilityRule(
                    scheme_id=scheme.id,
                    rule_name="Greater Than Equal",
                    field_name="age",
                    operator=">=",
                    expected_value="18",
                    description="Age >= 18",
                    source_reference="GO 4",
                ),
                SchemeEligibilityRule(
                    scheme_id=scheme.id,
                    rule_name="Less Than",
                    field_name="monthly_electricity_consumption_units",
                    operator="<",
                    expected_value="200",
                    description="Electricity units < 200",
                    source_reference="GO 5",
                ),
                SchemeEligibilityRule(
                    scheme_id=scheme.id,
                    rule_name="Greater Than",
                    field_name="landholding_acres",
                    operator=">",
                    expected_value="0.0",
                    description="Land > 0 acres",
                    source_reference="GO 6",
                ),
                SchemeEligibilityRule(
                    scheme_id=scheme.id,
                    rule_name="In List",
                    field_name="ration_card_type",
                    operator="in",
                    expected_value='["BPL", "AAY"]',
                    description="Must hold BPL or AAY ration card",
                    source_reference="GO 7",
                ),
                SchemeEligibilityRule(
                    scheme_id=scheme.id,
                    rule_name="Not In List",
                    field_name="caste_category",
                    operator="not_in",
                    expected_value='["ExcludedCategory"]',
                    description="Must not be in excluded category",
                    source_reference="GO 8",
                ),
            ]
            db.session.add_all(rules)
            db.session.commit()

            # Profile satisfying all 8 operators
            passing_profile = {
                "gender": "Female",
                "occupation": "Farmer",
                "annual_household_income": 150000,
                "age": 25,
                "monthly_electricity_consumption_units": 120,
                "landholding_acres": 2.5,
                "ration_card_type": "BPL",
                "caste_category": "OBC",
            }

            res = EligibilityEngine.evaluate_scheme(scheme, passing_profile)
            self.assertEqual(res["overall_status"], "potentially_eligible")
            self.assertEqual(len(res["rules_passed"]), 8)
            self.assertEqual(len(res["rules_failed"]), 0)
            self.assertEqual(len(res["rules_needing_info"]), 0)
        finally:
            db.session.delete(scheme)
            db.session.commit()

    # --- 2. Three-State Logic Tests ---
    def test_02_status_potentially_eligible(self):
        """Test Gruha Lakshmi evaluation where citizen meets all criteria."""
        gl = GovernmentScheme.query.filter_by(slug="gruha-lakshmi").first()
        self.assertIsNotNone(gl)

        profile = {
            "state": "Karnataka",
            "gender": "Female",
            "is_female_head_of_family": True,
            "ration_card_type": "BPL",
        }

        res = EligibilityEngine.evaluate_scheme(gl, profile)
        self.assertEqual(res["overall_status"], "potentially_eligible")
        self.assertEqual(res["status_label"], "Potentially Eligible")
        self.assertIn("Gruha Lakshmi", res["explanation"])
        self.assertIn("disclaimer", res)

    def test_03_status_not_eligible(self):
        """Test Yuva Nidhi evaluation failing due to employed occupation."""
        yn = GovernmentScheme.query.filter_by(slug="yuva-nidhi").first()
        self.assertIsNotNone(yn)

        profile = {
            "state": "Karnataka",
            "student_degree_level": "Undergraduate",
            "occupation": "Salaried Software Engineer",  # Fails unemployment rule
        }

        res = EligibilityEngine.evaluate_scheme(yn, profile)
        self.assertEqual(res["overall_status"], "not_eligible")
        self.assertEqual(res["status_label"], "Not Eligible")
        self.assertGreater(len(res["rules_failed"]), 0)
        self.assertIn("Salaried Software Engineer", res["rules_failed"][0]["explanation"])

    def test_04_status_needs_more_information(self):
        """Test evaluation when required attributes are missing or None."""
        gl = GovernmentScheme.query.filter_by(slug="gruha-lakshmi").first()
        self.assertIsNotNone(gl)

        # Profile with missing ration_card_type and is_female_head_of_family
        sparse_profile = {
            "state": "Karnataka",
            "gender": "Female",
        }

        res = EligibilityEngine.evaluate_scheme(gl, sparse_profile)
        self.assertEqual(res["overall_status"], "needs_more_information")
        self.assertEqual(res["status_label"], "Needs More Information")
        self.assertGreater(len(res["rules_needing_info"]), 0)
        self.assertGreater(len(res["next_recommended_questions"]), 0)

        missing_fields = [q["field_name"] for q in res["next_recommended_questions"]]
        self.assertIn("is_female_head_of_family", missing_fields)
        self.assertIn("ration_card_type", missing_fields)

    def test_05_status_unable_to_verify(self):
        """Test that unverified schemes return 'unable_to_verify'."""
        unverified = GovernmentScheme(
            name="Unverified Pilot",
            slug="unverified-pilot",
            description="desc",
            category="cat",
            government_level="State",
            department="dept",
            official_url="https://gov.in",
            benefits="ben",
            verification_status="Unverified",
        )
        db.session.add(unverified)
        db.session.commit()

        try:
            res = EligibilityEngine.evaluate_scheme(unverified, {"state": "Karnataka"})
            self.assertEqual(res["overall_status"], "unable_to_verify")
            self.assertEqual(res["status_label"], "Unable to Verify")
        finally:
            db.session.delete(unverified)
            db.session.commit()

    # --- 3. Safety, Null Handling, and Type Validation ---
    def test_06_never_compare_none_with_numeric_values(self):
        """Ensure missing or None age/income never crashes or evaluates as True."""
        pm_kisan = GovernmentScheme.query.filter_by(slug="pm-kisan").first()
        self.assertIsNotNone(pm_kisan)

        # Profile with None landholding
        profile_with_null = {
            "occupation": "Farmer",
            "landholding_acres": None,
        }

        res = EligibilityEngine.evaluate_scheme(pm_kisan, profile_with_null)
        self.assertEqual(res["overall_status"], "needs_more_information")
        needing_info_fields = [r["field_name"] for r in res["rules_needing_info"]]
        self.assertIn("landholding_acres", needing_info_fields)

    def test_07_invalid_data_types_handled_safely(self):
        """Ensure passing string to numeric operator does not crash."""
        ssp = GovernmentScheme.query.filter_by(slug="ssp-post-matric-scholarship").first()
        self.assertIsNotNone(ssp)

        # Passing non-numeric string for income
        bad_profile = {
            "state": "Karnataka",
            "is_student": True,
            "caste_category": "OBC",
            "annual_household_income": "Not An Income Number",
        }

        res = EligibilityEngine.evaluate_scheme(ssp, bad_profile)
        # Should not crash, and mark income as needing info
        self.assertEqual(res["overall_status"], "needs_more_information")
        needing_fields = [r["field_name"] for r in res["rules_needing_info"]]
        self.assertIn("annual_household_income", needing_fields)

    def test_08_no_arbitrary_code_execution_security(self):
        """Ensure malicious code strings in rule values are treated as literals and NEVER executed."""
        malicious_scheme = GovernmentScheme(
            name="Security Test Scheme",
            slug="security-test-scheme",
            description="Testing arbitrary code execution resistance.",
            category="Security",
            government_level="State",
            department="Cyber Cell",
            official_url="https://gov.in",
            benefits="Security check.",
            active_status="Active",
            verification_status="Verified",
        )
        db.session.add(malicious_scheme)
        db.session.flush()

        malicious_rule = SchemeEligibilityRule(
            scheme_id=malicious_scheme.id,
            rule_name="Injection Attack Attempt",
            field_name="occupation",
            operator="==",
            expected_value="__import__('os').system('echo hacked')",
            description="Test malicious string",
            source_reference="Test",
        )
        db.session.add(malicious_rule)
        db.session.commit()

        try:
            # Evaluation should compare as a string literal and fail cleanly
            res = EligibilityEngine.evaluate_scheme(malicious_scheme, {"occupation": "Farmer"})
            self.assertEqual(res["overall_status"], "not_eligible")
            self.assertEqual(len(res["rules_failed"]), 1)
            self.assertIn("__import__", res["rules_failed"][0]["expected_value"])
        finally:
            db.session.delete(malicious_scheme)
            db.session.commit()

    # --- 4. Document Checklist Engine Tests ---
    def test_09_document_checklist_generation(self):
        """Test document checklist generation from official SchemeDocument records."""
        gl = GovernmentScheme.query.filter_by(slug="gruha-lakshmi").first()
        self.assertIsNotNone(gl)

        checklist = DocumentEngine.generate_checklist(gl)
        self.assertEqual(checklist["scheme_slug"], "gruha-lakshmi")
        self.assertEqual(checklist["total_documents"], 3)
        self.assertEqual(checklist["statistics"]["total_mandatory"], 3)
        self.assertEqual(checklist["statistics"]["mandatory_collected"], 0)
        self.assertFalse(checklist["is_ready_to_apply"])
        self.assertIn("guidance_note", checklist)

    def test_10_document_marking_collected_and_readiness(self):
        """Test marking checklist documents as collected without uploads or PII."""
        gl = GovernmentScheme.query.filter_by(slug="gruha-lakshmi").first()
        self.assertIsNotNone(gl)

        # Partially collected
        partial_collected = ["Aadhaar Card", "Ration Card (AAY / BPL / APL)"]
        chk_partial = DocumentEngine.generate_checklist(gl, partial_collected)
        self.assertEqual(chk_partial["statistics"]["mandatory_collected"], 2)
        self.assertFalse(chk_partial["is_ready_to_apply"])

        # Fully collected all 3 mandatory documents
        all_collected = [
            "Aadhaar Card",
            "Ration Card (AAY / BPL / APL)",
            "Aadhaar-Linked Bank Account Passbook",
        ]
        chk_full = DocumentEngine.generate_checklist(gl, all_collected)
        self.assertEqual(chk_full["statistics"]["mandatory_collected"], 3)
        self.assertTrue(chk_full["is_ready_to_apply"])
        self.assertIn("ready to proceed", chk_full["readiness_summary"].lower())

    # --- 5. API Endpoint Tests ---
    def test_11_api_eligibility_check_single_success(self):
        """Test POST /api/eligibility/check endpoint with valid payload."""
        payload = {
            "slug": "gruha-jyothi",
            "profile": {
                "state": "Karnataka",
                "monthly_electricity_consumption_units": 150,
            },
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["overall_status"], "potentially_eligible")
        self.assertEqual(data["data"]["scheme_slug"], "gruha-jyothi")

    def test_12_api_eligibility_check_single_errors(self):
        """Test POST /api/eligibility/check error cases (missing slug, bad profile, 404)."""
        # Missing slug
        res1 = self.client.post("/api/eligibility/check", json={"profile": {}})
        self.assertEqual(res1.status_code, 400)

        # Missing profile
        res2 = self.client.post("/api/eligibility/check", json={"slug": "gruha-lakshmi"})
        self.assertEqual(res2.status_code, 400)

        # Non-existent scheme slug
        res3 = self.client.post(
            "/api/eligibility/check",
            json={"slug": "non-existent-scheme", "profile": {"age": 20}},
        )
        self.assertEqual(res3.status_code, 404)

        # Non-JSON payload
        res4 = self.client.post("/api/eligibility/check", data="not json")
        self.assertEqual(res4.status_code, 400)

    def test_13_api_eligibility_check_all(self):
        """Test POST /api/eligibility/check-all evaluating entire catalog."""
        # Citizen profile: Low-income female farmer in Karnataka with BPL card
        citizen = {
            "state": "Karnataka",
            "gender": "Female",
            "is_female_head_of_family": True,
            "ration_card_type": "BPL",
            "is_bpl_card_holder": True,
            "occupation": "Farmer",
            "landholding_acres": 1.5,
            "annual_household_income": 95000,
            "monthly_electricity_consumption_units": 90,
        }

        res = self.client.post("/api/eligibility/check-all", json={"profile": citizen})
        self.assertEqual(res.status_code, 200)

        data = res.get_json()
        self.assertTrue(data["success"])
        summary = data["data"]["summary"]
        self.assertGreater(summary["potentially_eligible_count"], 0)
        self.assertEqual(data["data"]["total_schemes_evaluated"], 10)

        # Results grouped by status
        results_by_status = data["data"]["results_by_status"]
        self.assertIn("potentially_eligible", results_by_status)
        self.assertIn("needs_more_information", results_by_status)
        self.assertIn("not_eligible", results_by_status)

        # Check that Gruha Lakshmi, Shakti, PM-KISAN, and Anna Bhagya are potentially eligible
        eligible_slugs = [s["scheme_slug"] for s in results_by_status["potentially_eligible"]]
        self.assertIn("gruha-lakshmi", eligible_slugs)
        self.assertIn("shakti-scheme", eligible_slugs)
        self.assertIn("anna-bhagya", eligible_slugs)
        self.assertIn("pm-kisan", eligible_slugs)

    def test_14_api_documents_endpoint(self):
        """Test GET /api/documents/<slug> and POST with collected items."""
        # GET basic checklist
        res1 = self.client.get("/api/documents/yuva-nidhi")
        self.assertEqual(res1.status_code, 200)
        data1 = res1.get_json()
        self.assertTrue(data1["success"])
        self.assertEqual(data1["data"]["scheme_slug"], "yuva-nidhi")
        self.assertEqual(data1["data"]["total_documents"], 4)

        # GET with ?collected=
        res2 = self.client.get("/api/documents/yuva-nidhi?collected=Aadhaar%20Card")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.get_json()
        self.assertEqual(data2["data"]["statistics"]["mandatory_collected"], 1)

        # 404 for unknown slug
        res3 = self.client.get("/api/documents/unknown-slug")
        self.assertEqual(res3.status_code, 404)


if __name__ == "__main__":
    unittest.main()
