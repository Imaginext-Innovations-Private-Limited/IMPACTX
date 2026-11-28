"""
Deterministic Welfare Scheme Eligibility Evaluation Engine for Sahaaya AI.
Evaluates citizen demographic and socio-economic attributes against verified government rules.
Strictly decoupled from LLMs to eliminate hallucinations.
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from models import GovernmentScheme, SchemeEligibilityRule, CitizenProfile

logger = logging.getLogger("eligibility_engine")

# Strict Operator Whitelist
ALLOWED_OPERATORS = {"==", "!=", "<=", ">=", "<", ">", "in", "not_in"}

# Standard human-friendly question prompts for missing profile attributes
FIELD_QUESTION_MAP = {
    "age": "What is the applicant's age in years?",
    "gender": "What is the applicant's gender (Female, Male, Transgender)?",
    "state": "In which state does the applicant permanently reside (e.g., Karnataka)?",
    "district": "In which district does the applicant reside?",
    "caste_category": "Which social category do you belong to (General, OBC, SC, ST, Minority)?",
    "annual_household_income": "What is your approximate annual household income in rupees (INR)?",
    "occupation": "What is the applicant's current primary occupation (e.g., Student, Farmer, Unemployed Youth)?",
    "is_student": "Are you currently enrolled as an active student in a recognized educational institution?",
    "student_degree_level": "What degree or course level are you pursuing or have completed (e.g., Undergraduate, Diploma)?",
    "graduation_year": "In which year did you complete your degree or diploma?",
    "is_bpl_card_holder": "Does your family hold a certified Below Poverty Line (BPL) status?",
    "ration_card_type": "What type of ration card does your family hold (BPL, AAY, APL, or None)?",
    "is_female_head_of_family": "Is the applicant listed as the woman head of the family on the ration card?",
    "has_disability": "Does the applicant have a certified benchmark physical disability?",
    "disability_percentage": "What is the certified disability percentage (e.g., 40%)?",
    "landholding_acres": "How many acres of cultivable agricultural land does the family own?",
    "monthly_electricity_consumption_units": "What is your household's average monthly domestic electricity consumption in units?",
}

DISCLAIMER_TEXT = (
    "Indicative eligibility assessment only based on published government guidelines. "
    "This does not constitute guaranteed government approval. Final approval is subject to "
    "official document verification and eligibility determination by the respective government authority."
)


class EligibilityEngine:
    """
    Deterministic rule evaluation engine for welfare schemes.
    Evaluates profile attributes against database rules without executing arbitrary code.
    """

    @classmethod
    def evaluate_scheme(
        cls,
        scheme: GovernmentScheme,
        profile_data: Union[CitizenProfile, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluate a citizen profile against a single GovernmentScheme.
        Returns structured three-state evaluation result.
        """
        # Convert CitizenProfile model to dict if needed
        if isinstance(profile_data, CitizenProfile):
            profile_dict = profile_data.to_dict()
        elif isinstance(profile_data, dict):
            profile_dict = dict(profile_data)
        else:
            raise TypeError("profile_data must be a CitizenProfile instance or a dictionary.")

        # Guard: If scheme itself is unverified or under review
        if scheme.verification_status != "Verified":
            return {
                "scheme_name": scheme.name,
                "scheme_slug": scheme.slug,
                "overall_status": "unable_to_verify",
                "status_label": "Unable to Verify",
                "rules_passed": [],
                "rules_failed": [],
                "rules_needing_info": [],
                "unverified_rules": [],
                "explanation": (
                    f"Official guidelines for '{scheme.name}' are currently marked as "
                    f"'{scheme.verification_status}' and undergoing review. Eligibility cannot "
                    "be confirmed until official verification is complete."
                ),
                "next_recommended_questions": [],
                "official_url": scheme.official_url,
                "disclaimer": DISCLAIMER_TEXT,
            }

        rules_passed: List[Dict[str, Any]] = []
        rules_failed: List[Dict[str, Any]] = []
        rules_needing_info: List[Dict[str, Any]] = []
        unverified_rules: List[Dict[str, Any]] = []
        missing_fields: List[str] = []

        # Iterate over all rules associated with the scheme
        for rule in scheme.rules:
            # Check if rule itself is marked unverified
            if not rule.is_verified:
                unverified_rules.append({
                    "rule_id": rule.id,
                    "rule_name": rule.rule_name,
                    "field_name": rule.field_name,
                    "description": rule.description,
                    "source_reference": rule.source_reference,
                    "reason": "This specific rule is unverified in published guidelines.",
                })
                continue

            # Evaluate verified rule
            result_code, explanation = cls._evaluate_single_rule(rule, profile_dict)

            rule_detail = {
                "rule_id": rule.id,
                "rule_name": rule.rule_name,
                "field_name": rule.field_name,
                "operator": rule.operator,
                "expected_value": rule.expected_value,
                "citizen_value": profile_dict.get(rule.field_name),
                "description": rule.description,
                "source_reference": rule.source_reference,
                "explanation": explanation,
            }

            if result_code == "PASSED":
                rules_passed.append(rule_detail)
            elif result_code == "FAILED":
                rules_failed.append(rule_detail)
            elif result_code == "NEEDS_INFO":
                rules_needing_info.append(rule_detail)
                if rule.field_name not in missing_fields:
                    missing_fields.append(rule.field_name)

        # Determine overall eligibility status
        # Three-state logic:
        # 1. not_eligible: At least one required verified rule failed
        # 2. needs_more_information: No failures, but missing required attributes
        # 3. potentially_eligible: All verified rules satisfied
        if len(rules_failed) > 0:
            overall_status = "not_eligible"
            status_label = "Not Eligible"
            failed_reasons = "; ".join([r["explanation"] for r in rules_failed])
            explanation = (
                f"Based on published government criteria, you do not currently meet the requirements "
                f"for '{scheme.name}'. Specific condition(s) not met: {failed_reasons}"
            )
        elif len(rules_needing_info) > 0:
            overall_status = "needs_more_information"
            status_label = "Needs More Information"
            missing_names = ", ".join([r["rule_name"] for r in rules_needing_info])
            explanation = (
                f"Additional information is required to determine your eligibility for '{scheme.name}'. "
                f"The following criteria could not be evaluated: {missing_names}."
            )
        else:
            overall_status = "potentially_eligible"
            status_label = "Potentially Eligible"
            explanation = (
                f"Based on published government criteria, you meet all verified eligibility conditions "
                f"for '{scheme.name}'. Final approval requires official document verification."
            )

        # Compile recommended next questions
        next_questions = []
        for field in missing_fields:
            prompt = FIELD_QUESTION_MAP.get(field, f"Please provide your {field.replace('_', ' ')}.")
            next_questions.append({
                "field_name": field,
                "question": prompt,
            })

        return {
            "scheme_name": scheme.name,
            "scheme_slug": scheme.slug,
            "overall_status": overall_status,
            "status_label": status_label,
            "rules_passed": rules_passed,
            "rules_failed": rules_failed,
            "rules_needing_info": rules_needing_info,
            "unverified_rules": unverified_rules,
            "explanation": explanation,
            "next_recommended_questions": next_questions,
            "official_url": scheme.official_url,
            "application_url": scheme.application_url,
            "disclaimer": DISCLAIMER_TEXT,
        }

    @classmethod
    def evaluate_all_schemes(
        cls,
        schemes: List[GovernmentScheme],
        profile_data: Union[CitizenProfile, Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Evaluate a citizen profile across multiple schemes.
        Returns results grouped by eligibility status.
        """
        grouped_results: Dict[str, List[Dict[str, Any]]] = {
            "potentially_eligible": [],
            "needs_more_information": [],
            "not_eligible": [],
            "unable_to_verify": [],
        }

        total_evaluated = 0

        for scheme in schemes:
            eval_result = cls.evaluate_scheme(scheme, profile_data)
            status = eval_result["overall_status"]
            if status in grouped_results:
                grouped_results[status].append(eval_result)
            else:
                grouped_results.setdefault("unable_to_verify", []).append(eval_result)
            total_evaluated += 1

        return {
            "total_schemes_evaluated": total_evaluated,
            "summary": {
                "potentially_eligible_count": len(grouped_results["potentially_eligible"]),
                "needs_more_information_count": len(grouped_results["needs_more_information"]),
                "not_eligible_count": len(grouped_results["not_eligible"]),
                "unable_to_verify_count": len(grouped_results["unable_to_verify"]),
            },
            "results_by_status": grouped_results,
            "disclaimer": DISCLAIMER_TEXT,
        }

    @classmethod
    def _evaluate_single_rule(
        cls, rule: SchemeEligibilityRule, profile: Dict[str, Any]
    ) -> Tuple[str, str]:
        """
        Evaluate a single rule safely without eval/exec.
        Returns tuple: (STATUS_CODE, explanation_text)
        STATUS_CODE is one of: 'PASSED', 'FAILED', 'NEEDS_INFO'
        """
        operator = rule.operator.strip()
        if operator not in ALLOWED_OPERATORS:
            return "NEEDS_INFO", f"Unsupported operator '{operator}'."

        field_name = rule.field_name
        citizen_val = profile.get(field_name)

        # Check for missing, null, or empty string values
        if citizen_val is None or (isinstance(citizen_val, str) and citizen_val.strip() == ""):
            return "NEEDS_INFO", f"Profile attribute '{field_name}' is missing or not provided."

        raw_expected = rule.expected_value
        parsed_expected, parse_error = cls._safe_parse_expected_value(raw_expected)

        if parse_error:
            return "NEEDS_INFO", f"Rule error in '{rule.rule_name}': {parse_error}"

        # Execute comparison based on operator
        try:
            # 1. Equality '=='
            if operator == "==":
                matched = cls._compare_equality(citizen_val, parsed_expected)
                if matched:
                    return "PASSED", f"Requirement met: {rule.description}"
                return "FAILED", f"Requirement not met: Expected {raw_expected}, but your profile is {citizen_val}."

            # 2. Inequality '!='
            if operator == "!=":
                matched = not cls._compare_equality(citizen_val, parsed_expected)
                if matched:
                    return "PASSED", f"Requirement met: {rule.description}"
                return "FAILED", f"Requirement not met: Disallowed value {citizen_val} matches rule restriction."

            # 3. Numeric Comparison '<=', '>=', '<', '>'
            if operator in {"<=", ">=", "<", ">"}:
                return cls._compare_numeric(citizen_val, parsed_expected, operator, rule)

            # 4. Membership 'in'
            if operator == "in":
                return cls._compare_in(citizen_val, parsed_expected, rule)

            # 5. Non-membership 'not_in'
            if operator == "not_in":
                return cls._compare_not_in(citizen_val, parsed_expected, rule)

        except Exception as e:
            logger.warning(f"Error evaluating rule '{rule.rule_name}': {e}")
            return "NEEDS_INFO", f"Could not evaluate rule due to data type mismatch: {str(e)}"

        return "NEEDS_INFO", "Evaluation could not be completed."

    @classmethod
    def _safe_parse_expected_value(cls, raw: str) -> Tuple[Any, Optional[str]]:
        """
        Safely parse rule expected_value string into typed Python object.
        Never uses eval() or exec().
        """
        if not isinstance(raw, str):
            return raw, None

        cleaned = raw.strip()

        # Check JSON list or dict format
        if (cleaned.startswith("[") and cleaned.endswith("]")) or (cleaned.startswith("{") and cleaned.endswith("}")):
            try:
                return json.loads(cleaned), None
            except json.JSONDecodeError as e:
                return None, f"Invalid JSON in rule value: {e}"

        # Boolean strings
        if cleaned.lower() == "true":
            return True, None
        if cleaned.lower() == "false":
            return False, None

        # Integer or Float
        try:
            if "." in cleaned:
                return float(cleaned), None
            return int(cleaned), None
        except ValueError:
            pass

        # Return plain string
        return cleaned, None

    @classmethod
    def _compare_equality(cls, citizen_val: Any, expected_val: Any) -> bool:
        """Type-aware equality comparison."""
        # Boolean comparison
        if isinstance(expected_val, bool) or isinstance(citizen_val, bool):
            # Convert string boolean representation if necessary
            c_bool = cls._coerce_to_bool(citizen_val)
            e_bool = cls._coerce_to_bool(expected_val)
            if c_bool is not None and e_bool is not None:
                return c_bool == e_bool

        # Numeric comparison
        if isinstance(expected_val, (int, float)) and isinstance(citizen_val, (int, float)):
            return float(citizen_val) == float(expected_val)

        # String comparison (case-insensitive and trimmed)
        if isinstance(citizen_val, str) and isinstance(expected_val, str):
            return citizen_val.strip().lower() == expected_val.strip().lower()

        return citizen_val == expected_val

    @classmethod
    def _compare_numeric(
        cls, citizen_val: Any, expected_val: Any, operator: str, rule: SchemeEligibilityRule
    ) -> Tuple[str, str]:
        """Numeric comparison with strict None safety and type validation."""
        # Never compare None with numbers
        if citizen_val is None:
            return "NEEDS_INFO", f"Numeric value for '{rule.field_name}' is missing."

        # Validate citizen value can be converted to float
        try:
            c_num = float(citizen_val)
        except (ValueError, TypeError):
            return "NEEDS_INFO", f"Cannot compare non-numeric profile value '{citizen_val}' with number."

        # Validate expected value
        try:
            e_num = float(expected_val)
        except (ValueError, TypeError):
            return "NEEDS_INFO", f"Rule configuration error: expected value '{expected_val}' is not numeric."

        if operator == "<=":
            passed = c_num <= e_num
        elif operator == ">=":
            passed = c_num >= e_num
        elif operator == "<":
            passed = c_num < e_num
        elif operator == ">":
            passed = c_num > e_num
        else:
            return "NEEDS_INFO", f"Invalid numeric operator '{operator}'."

        if passed:
            return "PASSED", f"Requirement met: {rule.description}"

        return "FAILED", (
            f"Requirement not met: Your {rule.field_name.replace('_', ' ')} is {citizen_val}, "
            f"which does not satisfy {operator} {expected_val}."
        )

    @classmethod
    def _compare_in(
        cls, citizen_val: Any, expected_list: Any, rule: SchemeEligibilityRule
    ) -> Tuple[str, str]:
        """Membership comparison with case-insensitivity."""
        if not isinstance(expected_list, (list, tuple, set)):
            return "NEEDS_INFO", f"Rule error: Expected list for 'in' operator, got {type(expected_list).__name__}."

        # String case-insensitive comparison
        if isinstance(citizen_val, str):
            c_norm = citizen_val.strip().lower()
            matched = any(str(item).strip().lower() == c_norm for item in expected_list)
        else:
            matched = citizen_val in expected_list

        if matched:
            return "PASSED", f"Requirement met: {rule.description}"

        allowed_str = ", ".join([str(x) for x in expected_list])
        return "FAILED", f"Requirement not met: '{citizen_val}' is not among allowed categories: [{allowed_str}]."

    @classmethod
    def _compare_not_in(
        cls, citizen_val: Any, expected_list: Any, rule: SchemeEligibilityRule
    ) -> Tuple[str, str]:
        """Non-membership comparison."""
        if not isinstance(expected_list, (list, tuple, set)):
            return "NEEDS_INFO", f"Rule error: Expected list for 'not_in' operator, got {type(expected_list).__name__}."

        if isinstance(citizen_val, str):
            c_norm = citizen_val.strip().lower()
            contained = any(str(item).strip().lower() == c_norm for item in expected_list)
        else:
            contained = citizen_val in expected_list

        if not contained:
            return "PASSED", f"Requirement met: {rule.description}"

        return "FAILED", f"Requirement not met: Value '{citizen_val}' is disallowed under this rule."

    @staticmethod
    def _coerce_to_bool(val: Any) -> Optional[bool]:
        """Safely coerce boolean representations."""
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            s = val.strip().lower()
            if s in ("true", "1", "yes"):
                return True
            if s in ("false", "0", "no"):
                return False
        if isinstance(val, (int, float)):
            return bool(val)
        return None
