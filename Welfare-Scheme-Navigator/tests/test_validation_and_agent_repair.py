"""
Comprehensive Test Suite for Input Validation Improvements and AI Assistant Repair in Sahaaya AI.
Validates:
1. Citizen profile validation engine (engine/validator.py).
2. Endpoint-level HTTP 400 validation rejection and error structures (/api/eligibility/check, /api/eligibility/check-all).
3. Clear distinction between invalid input (HTTP 400) and criteria failure (HTTP 200 not_eligible).
4. Graceful handling of missing information (needs_more_information).
5. AI Assistant tools, execution safety, app context push, and response formatting aliases.
6. Multi-turn session management, PII protection, and graceful fallback mode.
"""

import sys
import unittest
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app
from models import db, GovernmentScheme
from engine.validator import validate_citizen_profile
from agent.tools import execute_tool, tool_check_eligibility, tool_search_schemes, tool_get_required_documents
from agent.response_formatter import ResponseFormatter
from agent.conversation_manager import ConversationManager
from agent.agent_orchestrator import AgentOrchestrator
from agent.gemini_client import GeminiClient


class TestValidationAndAgentRepair(unittest.TestCase):
    """Regression test suite for Input Validation Improvements and AI Assistant Repair."""

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
    # PART 1: DIRECT VALIDATOR UNIT TESTS
    # =================================================================

    def test_01_validator_rejects_age_2(self):
        """Test validator rejects toddler age = 2 as implausibly low applicant age."""
        is_valid, msg, errors = validate_citizen_profile({"age": 2})
        self.assertFalse(is_valid)
        self.assertIn("age", errors)
        self.assertIn("at least 18 years", errors["age"])

    def test_02_validator_rejects_negative_age(self):
        """Test validator rejects negative age = -5."""
        is_valid, msg, errors = validate_citizen_profile({"age": -5})
        self.assertFalse(is_valid)
        self.assertIn("age", errors)
        self.assertIn("negative", errors["age"])

    def test_03_validator_rejects_zero_age(self):
        """Test validator rejects zero age = 0."""
        is_valid, msg, errors = validate_citizen_profile({"age": 0})
        self.assertFalse(is_valid)
        self.assertIn("age", errors)
        self.assertIn("cannot be zero", errors["age"])

    def test_04_validator_accepts_valid_age_28(self):
        """Test validator accepts normal valid applicant age = 28."""
        is_valid, msg, errors = validate_citizen_profile({"age": 28})
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)

    def test_05_validator_rejects_age_above_120(self):
        """Test validator rejects age outside human range = 150."""
        is_valid, msg, errors = validate_citizen_profile({"age": 150})
        self.assertFalse(is_valid)
        self.assertIn("age", errors)
        self.assertIn("maximum 120 years", errors["age"])

    def test_06_validator_rejects_decimal_age(self):
        """Test validator rejects decimal age = 25.5."""
        is_valid, msg, errors = validate_citizen_profile({"age": 25.5})
        self.assertFalse(is_valid)
        self.assertIn("age", errors)
        self.assertIn("whole numbers only", errors["age"])

    def test_07_validator_rejects_negative_income(self):
        """Test validator rejects negative annual household income."""
        is_valid, msg, errors = validate_citizen_profile({"annual_household_income": -5000})
        self.assertFalse(is_valid)
        self.assertIn("annual_household_income", errors)
        self.assertIn("cannot be negative", errors["annual_household_income"])

    def test_08_validator_rejects_text_in_numeric_field(self):
        """Test validator rejects non-numeric string in age field."""
        is_valid, msg, errors = validate_citizen_profile({"age": "abc"})
        self.assertFalse(is_valid)
        self.assertIn("age", errors)

    def test_09_validator_rejects_invalid_gender_and_ration_card(self):
        """Test validator rejects invalid categorical options."""
        is_valid_gender, _, errors_g = validate_citizen_profile({"gender": "Alien"})
        self.assertFalse(is_valid_gender)
        self.assertIn("gender", errors_g)

        is_valid_rc, _, errors_rc = validate_citizen_profile({"ration_card_type": "VIP_CARD"})
        self.assertFalse(is_valid_rc)
        self.assertIn("ration_card_type", errors_rc)

    def test_10_validator_rejects_impossible_graduation_year(self):
        """Test validator rejects graduation years far in the future or too far in past."""
        is_valid, _, errors = validate_citizen_profile({"graduation_year": 2045})
        self.assertFalse(is_valid)
        self.assertIn("graduation_year", errors)

    # =================================================================
    # PART 2: API ENDPOINT VALIDATION & ERROR HANDLING
    # =================================================================

    def test_11_api_check_rejects_age_2_with_http_400(self):
        """API /api/eligibility/check rejects age=2 with structured HTTP 400."""
        payload = {
            "slug": "gruha-lakshmi",
            "profile": {"age": 2, "gender": "Female"}
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("error"), "Validation Error")
        self.assertIn("details", data)
        self.assertIn("age", data["details"])

    def test_12_api_check_rejects_negative_age_with_http_400(self):
        """API /api/eligibility/check rejects negative age with HTTP 400."""
        payload = {
            "slug": "gruha-lakshmi",
            "profile": {"age": -5}
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("error"), "Validation Error")

    def test_13_api_check_rejects_zero_age_with_http_400(self):
        """API /api/eligibility/check rejects zero age with HTTP 400."""
        payload = {
            "slug": "gruha-lakshmi",
            "profile": {"age": 0}
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("error"), "Validation Error")

    def test_14_api_check_accepts_valid_age_28(self):
        """API /api/eligibility/check accepts valid age=28 and returns HTTP 200."""
        payload = {
            "slug": "gruha-lakshmi",
            "profile": {
                "age": 28,
                "gender": "Female",
                "state": "Karnataka",
                "is_female_head_of_family": True,
                "ration_card_type": "BPL",
                "is_bpl_card_holder": True
            }
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["data"]["overall_status"], "potentially_eligible")

    def test_15_api_check_rejects_age_150_with_http_400(self):
        """API /api/eligibility/check rejects age=150 with HTTP 400."""
        payload = {
            "slug": "gruha-lakshmi",
            "profile": {"age": 150}
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 400)

    def test_16_api_check_rejects_decimal_age_with_http_400(self):
        """API /api/eligibility/check rejects decimal age=25.5 with HTTP 400."""
        payload = {
            "slug": "gruha-lakshmi",
            "profile": {"age": 25.5}
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 400)

    def test_17_api_check_rejects_negative_income_with_http_400(self):
        """API /api/eligibility/check rejects negative income with HTTP 400."""
        payload = {
            "slug": "pm-kisan",
            "profile": {"annual_household_income": -100}
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 400)

    def test_18_api_check_all_rejects_invalid_profile(self):
        """API /api/eligibility/check-all rejects invalid profile with HTTP 400."""
        payload = {
            "profile": {"age": 2}
        }
        res = self.client.post("/api/eligibility/check-all", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertEqual(data.get("error"), "Validation Error")

    def test_19_distinguish_invalid_input_from_criteria_failure(self):
        """
        Crucial requirement: Distinguish invalid input from a valid attribute that fails criteria.
        Income = 500000 is a valid positive income, but exceeds SSP Post-Matric Scholarship's max limit of 250000.
        Must return HTTP 200 with status 'not_eligible', NOT HTTP 400.
        """
        payload = {
            "slug": "ssp-post-matric-scholarship",
            "profile": {
                "annual_household_income": 500000,
                "state": "Karnataka",
                "is_student": True,
                "caste_category": "General"
            }
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["data"]["overall_status"], "not_eligible")
        failed_rules = data["data"]["rules_failed"]
        self.assertTrue(any("annual_household_income" in r["field_name"] for r in failed_rules))

    def test_20_missing_information_handled_gracefully(self):
        """Missing information returns HTTP 200 with needs_more_information, not 400."""
        payload = {
            "slug": "yuva-nidhi",
            "profile": {}  # Empty profile is valid, but missing required attributes
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["data"]["overall_status"], "needs_more_information")
        self.assertTrue(len(data["data"]["rules_needing_info"]) > 0)

    # =================================================================
    # PART 3: AI ASSISTANT REPAIR & TOOL EXECUTION TESTS
    # =================================================================

    def test_21_agent_status_endpoint(self):
        """GET /api/agent/status returns 200 and reports all 6 supported tools."""
        res = self.client.get("/api/agent/status")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))
        self.assertIn("supported_tools", data)
        self.assertEqual(len(data["supported_tools"]), 6)
        self.assertIn("search_schemes", data["supported_tools"])
        self.assertIn("check_eligibility", data["supported_tools"])

    def test_22_response_formatter_aliases(self):
        """ResponseFormatter produces both 'response' and 'tools_executed' aliases for backward compatibility."""
        tools = [{"tool_name": "search_schemes", "status": "success", "args_summary": ["query"]}]
        formatted = ResponseFormatter.format_agent_response(
            assistant_message="Here are the schemes matching your request.",
            conversation_id="conv_123",
            tools_invoked=tools,
        )
        self.assertTrue(formatted["success"])
        # Both keys must be present
        self.assertIn("assistant_message", formatted)
        self.assertIn("response", formatted)
        self.assertEqual(formatted["assistant_message"], formatted["response"])
        self.assertIn("tools_invoked", formatted)
        self.assertIn("tools_executed", formatted)
        self.assertEqual(formatted["tools_executed"], ["search_schemes"])

    def test_23_tool_check_eligibility_rejects_invalid_profile(self):
        """Tool check_eligibility safely rejects invalid profile (age=2) with unable_to_verify."""
        result = tool_check_eligibility(
            scheme_slug="gruha-lakshmi",
            citizen_profile={"age": 2}
        )
        self.assertFalse(result["success"])
        self.assertEqual(result["overall_status"], "unable_to_verify")
        self.assertIn("details", result)
        self.assertIn("age", result["details"])

    def test_24_tool_check_eligibility_evaluates_valid_profile(self):
        """Tool check_eligibility evaluates valid profile deterministically."""
        result = tool_check_eligibility(
            scheme_slug="gruha-lakshmi",
            citizen_profile={
                "age": 30,
                "gender": "Female",
                "state": "Karnataka",
                "is_female_head_of_family": True,
                "ration_card_type": "BPL",
                "is_bpl_card_holder": True
            }
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["overall_status"], "potentially_eligible")

    def test_25_tool_search_schemes(self):
        """Tool search_schemes executes correctly and finds registered schemes."""
        result = tool_search_schemes(query="women financial assistance")
        self.assertTrue(result["success"])
        self.assertGreater(result["total_found"], 0)
        slugs = [s["scheme_slug"] for s in result["schemes"]]
        self.assertIn("gruha-lakshmi", slugs)

    def test_26_tool_get_required_documents(self):
        """Tool get_required_documents returns official checklist without asking for uploads."""
        result = tool_get_required_documents(scheme_slug="gruha-lakshmi")
        self.assertTrue(result["success"])
        self.assertGreaterEqual(len(result["mandatory_documents"]), 1)

    def test_27_execute_tool_app_context_safety(self):
        """execute_tool pushes Flask context safely even when called without prior context."""
        # Test calling execute_tool inside a detached context
        res = execute_tool("search_schemes", {"query": "farmer"})
        self.assertTrue(res.get("success"))

    def test_28_execute_tool_rejects_disallowed_name(self):
        """execute_tool strictly rejects names not on the 6-tool whitelist."""
        res = execute_tool("execute_shell_command", {"command": "dir"})
        self.assertFalse(res.get("success"))
        self.assertIn("Disallowed tool", res.get("error", ""))

    def test_29_session_manager_and_reset(self):
        """ConversationManager preserves history and resets cleanly via API."""
        conv_mgr = ConversationManager()
        session = conv_mgr.get_or_create_session("test_sess_001")
        session.add_message("user", "Hello Sahaaya")
        session.add_message("model", "Namaste!")
        self.assertEqual(len(session.messages), 2)

        # Test reset via API
        res = self.client.post("/api/agent/reset", json={"conversation_id": "test_sess_001"})
        self.assertEqual(res.status_code, 200)

    def test_30_pii_warning_on_sensitive_submission(self):
        """Orchestrator attaches privacy warning when citizen inputs Aadhaar or PAN."""
        orchestrator = AgentOrchestrator()
        # Message with valid 12-digit UIDAI Aadhaar number pattern (starts 2-9)
        res = orchestrator.process_message(
            message="My Aadhaar number is 2345 6789 0123, am I eligible for Gruha Lakshmi?",
            conversation_id="pii_test_session"
        )
        self.assertTrue(res.get("success"))
        # Must contain privacy notice
        message = res.get("assistant_message", "")
        self.assertIn("Privacy Notice", message)
        self.assertIn("never collects or requires", message)

    # =================================================================
    # PART 4: ANNUAL HOUSEHOLD INCOME VALIDATION TESTS
    # =================================================================

    def test_31_validator_income_zero_is_valid(self):
        """Income = 0 is a valid income value and is not rejected."""
        is_valid_int, msg_int, errors_int = validate_citizen_profile({"annual_household_income": 0})
        self.assertTrue(is_valid_int)
        self.assertNotIn("annual_household_income", errors_int)

        is_valid_str, msg_str, errors_str = validate_citizen_profile({"annual_household_income": "0"})
        self.assertTrue(is_valid_str)
        self.assertNotIn("annual_household_income", errors_str)

    def test_32_validator_income_positive_values_accepted(self):
        """Normal positive income values (10000, 40000) are accepted."""
        is_valid_10k, _, errors_10k = validate_citizen_profile({"annual_household_income": 10000})
        self.assertTrue(is_valid_10k)
        self.assertNotIn("annual_household_income", errors_10k)

        is_valid_40k, _, errors_40k = validate_citizen_profile({"annual_household_income": 40000})
        self.assertTrue(is_valid_40k)
        self.assertNotIn("annual_household_income", errors_40k)

        is_valid_10k_str, _, errors_10k_str = validate_citizen_profile({"annual_household_income": "10000"})
        self.assertTrue(is_valid_10k_str)
        self.assertNotIn("annual_household_income", errors_10k_str)

        is_valid_40k_str, _, errors_40k_str = validate_citizen_profile({"annual_household_income": "40000"})
        self.assertTrue(is_valid_40k_str)
        self.assertNotIn("annual_household_income", errors_40k_str)

    def test_33_validator_income_negative_1000_rejected(self):
        """Negative income (-1000) is rejected with exact requested error message."""
        is_valid_neg, _, errors_neg = validate_citizen_profile({"annual_household_income": -1000})
        self.assertFalse(is_valid_neg)
        self.assertEqual(errors_neg.get("annual_household_income"), "Annual household income cannot be negative.")

        is_valid_str_neg, _, errors_str_neg = validate_citizen_profile({"annual_household_income": "-1000"})
        self.assertFalse(is_valid_str_neg)
        self.assertEqual(errors_str_neg.get("annual_household_income"), "Annual household income cannot be negative.")

    def test_34_validator_income_text_rejected(self):
        """Non-numeric string values and invalid types in income field are rejected."""
        is_valid_text, _, errors_text = validate_citizen_profile({"annual_household_income": "text"})
        self.assertFalse(is_valid_text)
        self.assertEqual(errors_text.get("annual_household_income"), "Annual household income must be numeric.")

        is_valid_abc, _, errors_abc = validate_citizen_profile({"annual_household_income": "abc"})
        self.assertFalse(is_valid_abc)
        self.assertEqual(errors_abc.get("annual_household_income"), "Annual household income must be numeric.")

        is_valid_bool, _, errors_bool = validate_citizen_profile({"annual_household_income": True})
        self.assertFalse(is_valid_bool)
        self.assertEqual(errors_bool.get("annual_household_income"), "Annual household income must be numeric.")

    def test_35_validator_income_empty_allowed(self):
        """Empty or omitted income is handled according to existing rules (not required)."""
        is_valid_empty_dict, _, errors_empty_dict = validate_citizen_profile({})
        self.assertTrue(is_valid_empty_dict)
        self.assertNotIn("annual_household_income", errors_empty_dict)

        is_valid_none, _, errors_none = validate_citizen_profile({"annual_household_income": None})
        self.assertTrue(is_valid_none)
        self.assertNotIn("annual_household_income", errors_none)

        is_valid_empty_str, _, errors_empty_str = validate_citizen_profile({"annual_household_income": ""})
        self.assertTrue(is_valid_empty_str)
        self.assertNotIn("annual_household_income", errors_empty_str)

    def test_36_api_income_zero_accepted(self):
        """API /api/eligibility/check accepts annual_household_income = 0 with HTTP 200."""
        payload = {
            "slug": "pm-kisan",
            "profile": {
                "annual_household_income": 0,
                "landholding_acres": 1.5,
                "is_farmer": True
            }
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get("success"))

    def test_37_api_income_positive_values_accepted(self):
        """API /api/eligibility/check accepts income = 10000 and 40000 with HTTP 200."""
        res_10k = self.client.post("/api/eligibility/check", json={
            "slug": "pm-kisan",
            "profile": {"annual_household_income": 10000}
        })
        self.assertEqual(res_10k.status_code, 200)

        res_40k = self.client.post("/api/eligibility/check", json={
            "slug": "pm-kisan",
            "profile": {"annual_household_income": 40000}
        })
        self.assertEqual(res_40k.status_code, 200)

    def test_38_api_income_negative_1000_rejected(self):
        """API /api/eligibility/check rejects income = -1000 with HTTP 400 and exact error message."""
        payload = {
            "slug": "pm-kisan",
            "profile": {"annual_household_income": -1000}
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertEqual(data.get("error"), "Validation Error")
        self.assertEqual(data["details"].get("annual_household_income"), "Annual household income cannot be negative.")

    def test_39_api_income_text_rejected(self):
        """API /api/eligibility/check rejects income = 'text' with HTTP 400 and exact error message."""
        payload = {
            "slug": "pm-kisan",
            "profile": {"annual_household_income": "text"}
        }
        res = self.client.post("/api/eligibility/check", json=payload)
        self.assertEqual(res.status_code, 400)
        data = res.get_json()
        self.assertFalse(data.get("success"))
        self.assertEqual(data["details"].get("annual_household_income"), "Annual household income must be numeric.")

    def test_40_eligibility_page_contains_zero_income_confirmation_elements(self):
        """Eligibility Checker template renders confirmation banner and checkbox for ₹0 income."""
        response = self.client.get("/eligibility")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('id="zeroIncomeConfirmation"', html)
        self.assertIn('id="confirmZeroIncomeCheckbox"', html)
        self.assertIn("Your annual household income is entered as ₹0. Please confirm that this is correct.", html)
        self.assertIn("Annual household income cannot be negative.", html)


if __name__ == "__main__":
    unittest.main()
