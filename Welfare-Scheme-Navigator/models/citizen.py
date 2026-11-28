"""
Citizen Profile Model for Sahaaya AI
Strictly non-sensitive eligibility parameters only.
"""

from datetime import datetime, timezone
import re
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Index
from sqlalchemy.orm import validates
from models import db


class CitizenProfile(db.Model):
    """
    Non-sensitive demographic and socio-economic profile used for
    deterministic welfare scheme eligibility assessment.

    COMPLIANCE NOTICE:
    In accordance with privacy guidelines, this model NEVER collects or stores
    Aadhaar numbers, PAN numbers, bank account numbers, passwords, biometric records,
    or other sensitive personal identifiable information (PII).
    """
    __tablename__ = "citizen_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(100), index=True, nullable=True)

    # Demographic attributes (Non-sensitive)
    age = Column(Integer, nullable=True)
    gender = Column(String(20), nullable=True)  # 'Female', 'Male', 'Transgender', 'Other'
    state = Column(String(100), default="Karnataka", nullable=True)
    district = Column(String(100), nullable=True)
    caste_category = Column(String(50), nullable=True)  # 'General', 'OBC', 'SC', 'ST', 'Minority'

    # Socio-economic attributes
    annual_household_income = Column(Integer, nullable=True)  # in INR
    occupation = Column(String(100), nullable=True)  # 'Student', 'Farmer', 'Unemployed Youth', 'Homemaker', etc.

    # Education / Student status
    is_student = Column(Boolean, default=False, nullable=False)
    student_degree_level = Column(String(50), nullable=True)  # 'Pre-Matric', 'Post-Matric', 'Undergraduate', 'Diploma'
    graduation_year = Column(Integer, nullable=True)  # Relevant for Yuva Nidhi 2-year graduation check

    # Ration card / Welfare markers
    is_bpl_card_holder = Column(Boolean, default=False, nullable=False)
    ration_card_type = Column(String(50), nullable=True)  # 'BPL', 'AAY', 'APL', 'None'
    is_female_head_of_family = Column(Boolean, default=False, nullable=False)

    # Special categories
    has_disability = Column(Boolean, default=False, nullable=False)
    disability_percentage = Column(Integer, nullable=True)
    landholding_acres = Column(Float, default=0.0, nullable=False)
    monthly_electricity_consumption_units = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        Index("idx_citizen_state_category", "state", "caste_category"),
        Index("idx_citizen_income_bpl", "annual_household_income", "is_bpl_card_holder"),
    )

    # --- PII Validation Guards ---
    @validates("session_id", "state", "district", "occupation", "ration_card_type")
    def validate_no_pii_in_strings(self, key, value):
        """Guard against accidental transmission of Aadhaar, PAN, or account numbers."""
        if value is None:
            return value

        str_val = str(value).strip()

        # Check 12-digit Aadhaar pattern
        if re.search(r"\b\d{4}\s?\d{4}\s?\d{4}\b", str_val):
            raise ValueError(f"PII Violation: Potential 12-digit Aadhaar number detected in field '{key}'. Storing PII is forbidden.")

        # Check 10-character Indian PAN pattern (5 uppercase letters + 4 digits + 1 uppercase letter)
        if re.search(r"\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b", str_val, re.IGNORECASE):
            raise ValueError(f"PII Violation: Potential PAN number detected in field '{key}'. Storing PII is forbidden.")

        return str_val

    @validates("age")
    def validate_age(self, key, age_value):
        if age_value is not None:
            if not isinstance(age_value, int) or age_value < 0 or age_value > 125:
                raise ValueError(f"Invalid age: {age_value}. Must be an integer between 0 and 125.")
        return age_value

    @validates("annual_household_income")
    def validate_income(self, key, income_value):
        if income_value is not None:
            if not isinstance(income_value, (int, float)) or income_value < 0:
                raise ValueError("Annual household income must be a non-negative number.")
            return int(income_value)
        return income_value

    def to_dict(self):
        """Serialize citizen profile attributes."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "age": self.age,
            "gender": self.gender,
            "state": self.state,
            "district": self.district,
            "caste_category": self.caste_category,
            "annual_household_income": self.annual_household_income,
            "occupation": self.occupation,
            "is_student": self.is_student,
            "student_degree_level": self.student_degree_level,
            "graduation_year": self.graduation_year,
            "is_bpl_card_holder": self.is_bpl_card_holder,
            "ration_card_type": self.ration_card_type,
            "is_female_head_of_family": self.is_female_head_of_family,
            "has_disability": self.has_disability,
            "disability_percentage": self.disability_percentage,
            "landholding_acres": self.landholding_acres,
            "monthly_electricity_consumption_units": self.monthly_electricity_consumption_units,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self):
        return f"<CitizenProfile id={self.id} state='{self.state}' age={self.age} occupation='{self.occupation}'>"
