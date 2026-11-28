"""
Profile Validation Module for Sahaaya AI.
Performs strict validation of citizen demographic and socio-economic attributes
prior to evaluation by deterministic eligibility engines or agents.
"""

from typing import Dict, Any, Tuple, Optional
import datetime

VALID_GENDERS = {"Female", "Male", "Transgender", "Other"}
VALID_STATES = {
    "Karnataka", "Other", "All India", "Andhra Pradesh", "Arunachal Pradesh",
    "Assam", "Bihar", "Chhattisgarh", "Goa", "Gujarat", "Haryana",
    "Himachal Pradesh", "Jharkhand", "Kerala", "Madhya Pradesh", "Maharashtra",
    "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal", "Delhi", "Jammu and Kashmir"
}
VALID_CASTE_CATEGORIES = {"General", "OBC", "SC", "ST", "Minority"}
VALID_RATION_CARD_TYPES = {"BPL", "AAY", "APL", "None"}
VALID_OCCUPATIONS = {
    "Farmer", "Student", "Unemployed Youth", "Homemaker", "Salaried Employee",
    "Self-Employed", "Daily Wage Laborer", "Other", "Unemployed", "Job Seeker",
    "Agriculture", "Cultivator"
}

MIN_APPLICANT_AGE = 18
MAX_APPLICANT_AGE = 120
CURRENT_YEAR = datetime.datetime.now().year


def validate_citizen_profile(
    profile: Optional[Dict[str, Any]],
    scheme_slug: Optional[str] = None
) -> Tuple[bool, Optional[str], Dict[str, str]]:
    """
    Validate demographic and socio-economic attributes in a citizen profile.
    
    Returns:
        (is_valid, primary_error_message, errors_dict)
    """
    if profile is None:
        return True, None, {}

    if not isinstance(profile, dict):
        return False, "Profile must be a dictionary of attributes.", {"profile": "Must be a dictionary."}

    errors: Dict[str, str] = {}

    # 1. Age Validation
    if "age" in profile and profile["age"] is not None and profile["age"] != "":
        raw_age = profile["age"]
        # Reject booleans (since in Python isinstance(True, int) is True)
        if isinstance(raw_age, bool):
            errors["age"] = "Please enter a valid applicant age."
        elif isinstance(raw_age, float):
            errors["age"] = "Please enter a valid applicant age (whole numbers only)."
        elif isinstance(raw_age, str):
            clean_str = raw_age.strip()
            if "." in clean_str:
                errors["age"] = "Please enter a valid applicant age (whole numbers only)."
            elif not clean_str.lstrip("-").isdigit():
                errors["age"] = "Please enter a valid applicant age."
            else:
                try:
                    parsed_age = int(clean_str)
                    if parsed_age < 0:
                        errors["age"] = "Please enter a valid applicant age (negative ages are not allowed)."
                    elif parsed_age == 0:
                        errors["age"] = "Please enter a valid applicant age (age cannot be zero)."
                    elif parsed_age < MIN_APPLICANT_AGE:
                        errors["age"] = f"Please enter a valid applicant age (must be at least {MIN_APPLICANT_AGE} years)."
                    elif parsed_age > MAX_APPLICANT_AGE:
                        errors["age"] = f"Please enter a valid applicant age (maximum {MAX_APPLICANT_AGE} years)."
                except ValueError:
                    errors["age"] = "Please enter a valid applicant age."
        elif isinstance(raw_age, int):
            if raw_age < 0:
                errors["age"] = "Please enter a valid applicant age (negative ages are not allowed)."
            elif raw_age == 0:
                errors["age"] = "Please enter a valid applicant age (age cannot be zero)."
            elif raw_age < MIN_APPLICANT_AGE:
                errors["age"] = f"Please enter a valid applicant age (must be at least {MIN_APPLICANT_AGE} years)."
            elif raw_age > MAX_APPLICANT_AGE:
                errors["age"] = f"Please enter a valid applicant age (maximum {MAX_APPLICANT_AGE} years)."
        else:
            errors["age"] = "Please enter a valid applicant age."

    # 2. Annual Household Income Validation
    if "annual_household_income" in profile and profile["annual_household_income"] is not None and profile["annual_household_income"] != "":
        raw_income = profile["annual_household_income"]
        if isinstance(raw_income, bool):
            errors["annual_household_income"] = "Annual household income must be numeric."
        elif isinstance(raw_income, (int, float)):
            if raw_income < 0:
                errors["annual_household_income"] = "Annual household income cannot be negative."
        elif isinstance(raw_income, str):
            clean_str = raw_income.strip()
            try:
                parsed_income = float(clean_str)
                if parsed_income < 0:
                    errors["annual_household_income"] = "Annual household income cannot be negative."
            except ValueError:
                errors["annual_household_income"] = "Annual household income must be numeric."
        else:
            errors["annual_household_income"] = "Annual household income must be numeric."

    # 3. Gender Validation
    if "gender" in profile and profile["gender"] is not None and profile["gender"] != "":
        raw_gender = str(profile["gender"]).strip()
        matched_gender = None
        for g in VALID_GENDERS:
            if g.lower() == raw_gender.lower():
                matched_gender = g
                break
        if not matched_gender:
            errors["gender"] = f"Invalid gender option '{raw_gender}'. Allowed: {', '.join(sorted(VALID_GENDERS))}."

    # 4. State Validation
    if "state" in profile and profile["state"] is not None and profile["state"] != "":
        raw_state = str(profile["state"]).strip()
        if not raw_state or len(raw_state) < 2:
            errors["state"] = "Please select a valid permanent state."
        elif raw_state.isdigit():
            errors["state"] = "State cannot be numeric."

    # 5. Social Category Validation
    if "caste_category" in profile and profile["caste_category"] is not None and profile["caste_category"] != "":
        raw_cat = str(profile["caste_category"]).strip()
        matched_cat = None
        for c in VALID_CASTE_CATEGORIES:
            if c.lower() == raw_cat.lower():
                matched_cat = c
                break
        if not matched_cat:
            errors["caste_category"] = f"Invalid social category '{raw_cat}'. Allowed: {', '.join(sorted(VALID_CASTE_CATEGORIES))}."

    # 6. Ration Card Type Validation
    if "ration_card_type" in profile and profile["ration_card_type"] is not None and profile["ration_card_type"] != "":
        raw_rc = str(profile["ration_card_type"]).strip()
        matched_rc = None
        for rc in VALID_RATION_CARD_TYPES:
            if rc.lower() == raw_rc.lower():
                matched_rc = rc
                break
        if not matched_rc:
            errors["ration_card_type"] = f"Invalid ration card type '{raw_rc}'. Allowed: {', '.join(sorted(VALID_RATION_CARD_TYPES))}."

    # 7. Graduation Year Validation
    if "graduation_year" in profile and profile["graduation_year"] is not None and profile["graduation_year"] != "":
        raw_gy = profile["graduation_year"]
        parsed_gy = None
        if isinstance(raw_gy, bool):
            errors["graduation_year"] = "Graduation year must be a whole number."
        elif isinstance(raw_gy, int):
            parsed_gy = raw_gy
        elif isinstance(raw_gy, str) and raw_gy.strip().isdigit():
            parsed_gy = int(raw_gy.strip())
        else:
            errors["graduation_year"] = "Graduation year must be a whole number."

        if parsed_gy is not None:
            max_future_year = CURRENT_YEAR + 1
            if parsed_gy < 1950 or parsed_gy > max_future_year:
                errors["graduation_year"] = f"Graduation year must be between 1950 and {max_future_year}."

    # 8. Landholding Validation
    if "landholding_acres" in profile and profile["landholding_acres"] is not None and profile["landholding_acres"] != "":
        raw_land = profile["landholding_acres"]
        if isinstance(raw_land, bool):
            errors["landholding_acres"] = "Landholding must be a non-negative number."
        elif isinstance(raw_land, (int, float)):
            if raw_land < 0:
                errors["landholding_acres"] = "Landholding acres must be a non-negative number."
        elif isinstance(raw_land, str):
            try:
                val = float(raw_land.strip())
                if val < 0:
                    errors["landholding_acres"] = "Landholding acres must be a non-negative number."
            except ValueError:
                errors["landholding_acres"] = "Landholding acres must be a non-negative number."

    # 9. Monthly Electricity Consumption Validation
    if "monthly_electricity_consumption_units" in profile and profile["monthly_electricity_consumption_units"] is not None and profile["monthly_electricity_consumption_units"] != "":
        raw_units = profile["monthly_electricity_consumption_units"]
        if isinstance(raw_units, bool):
            errors["monthly_electricity_consumption_units"] = "Electricity consumption units must be a non-negative whole number."
        elif isinstance(raw_units, int):
            if raw_units < 0:
                errors["monthly_electricity_consumption_units"] = "Electricity consumption units cannot be negative."
        elif isinstance(raw_units, str) and raw_units.strip().isdigit():
            val = int(raw_units.strip())
            if val < 0:
                errors["monthly_electricity_consumption_units"] = "Electricity consumption units cannot be negative."
        else:
            errors["monthly_electricity_consumption_units"] = "Electricity consumption units must be a whole number."

    # 10. Boolean Fields Validation
    boolean_fields = [
        "is_female_head_of_family", "is_student", "has_disability", "is_bpl_card_holder"
    ]
    for bf in boolean_fields:
        if bf in profile and profile[bf] is not None and profile[bf] != "":
            raw_b = profile[bf]
            if not isinstance(raw_b, bool):
                if isinstance(raw_b, str) and raw_b.strip().lower() in ("true", "false", "1", "0"):
                    pass
                else:
                    errors[bf] = f"Field '{bf}' must be a boolean value (true or false)."

    if errors:
        primary_msg = next(iter(errors.values()))
        return False, primary_msg, errors

    return True, None, {}
