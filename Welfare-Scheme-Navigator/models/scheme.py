"""
Government Scheme Models for Sahaaya AI
"""

from datetime import datetime, timezone
import re
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship, validates
from models import db


class GovernmentScheme(db.Model):
    """
    Core Government Welfare Scheme entity.
    Stores verified metadata for Central and Karnataka state schemes.
    """
    __tablename__ = "government_schemes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    category = Column(String(100), nullable=False, index=True)
    government_level = Column(String(50), nullable=False, index=True)  # 'Central' or 'State'
    state = Column(String(100), nullable=True, index=True)  # 'Karnataka', 'All India', etc.
    department = Column(String(255), nullable=False)
    official_url = Column(String(500), nullable=False)
    application_url = Column(String(500), nullable=True)
    benefits = Column(Text, nullable=False)
    active_status = Column(String(50), default="Active", nullable=False)  # 'Active', 'Discontinued', 'Needs Review'
    verification_status = Column(String(50), default="Verified", nullable=False)  # 'Verified', 'Unverified', 'Needs Review'
    last_verified_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships with cascading deletes
    rules = relationship(
        "SchemeEligibilityRule",
        backref="scheme",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SchemeEligibilityRule.id"
    )

    documents = relationship(
        "SchemeDocument",
        backref="scheme",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SchemeDocument.id"
    )

    steps = relationship(
        "SchemeApplicationStep",
        backref="scheme",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SchemeApplicationStep.step_number"
    )

    __table_args__ = (
        Index("idx_scheme_level_state", "government_level", "state"),
        Index("idx_scheme_category", "category"),
    )

    @validates("slug")
    def validate_slug(self, key, slug_value):
        if not slug_value or not isinstance(slug_value, str):
            raise ValueError("Scheme slug must be a non-empty string.")
        cleaned = slug_value.strip().lower()
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", cleaned):
            raise ValueError(f"Invalid slug format '{slug_value}'. Must be lowercase alphanumeric with hyphens.")
        return cleaned

    @validates("name")
    def validate_name(self, key, name_value):
        if not name_value or not name_value.strip():
            raise ValueError("Scheme name cannot be empty.")
        return name_value.strip()

    @validates("official_url")
    def validate_official_url(self, key, url_value):
        if not url_value or not url_value.strip():
            raise ValueError("Scheme official_url cannot be empty.")
        if not (url_value.startswith("http://") or url_value.startswith("https://")):
            raise ValueError(f"Invalid official URL: '{url_value}'. Must start with http:// or https://")
        return url_value.strip()

    def to_dict(self, include_relations=True):
        """Serialize scheme to dictionary."""
        data = {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "description": self.description,
            "category": self.category,
            "government_level": self.government_level,
            "state": self.state,
            "department": self.department,
            "official_url": self.official_url,
            "application_url": self.application_url,
            "benefits": self.benefits,
            "active_status": self.active_status,
            "verification_status": self.verification_status,
            "last_verified_at": self.last_verified_at.isoformat() if self.last_verified_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_relations:
            data["rules"] = [r.to_dict() for r in self.rules]
            data["documents"] = [d.to_dict() for d in self.documents]
            data["steps"] = [s.to_dict() for s in self.steps]
        return data

    def __repr__(self):
        return f"<GovernmentScheme id={self.id} slug='{self.slug}' name='{self.name}'>"


class SchemeEligibilityRule(db.Model):
    """
    Formal, verifiable eligibility criteria for a government scheme.
    Used by the deterministic Python evaluation engine.
    """
    __tablename__ = "scheme_eligibility_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scheme_id = Column(Integer, ForeignKey("government_schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_name = Column(String(100), nullable=False)
    field_name = Column(String(100), nullable=False, index=True)
    operator = Column(String(20), nullable=False)  # '==', '!=', '<=', '>=', '<', '>', 'in', 'not_in'
    expected_value = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    source_reference = Column(String(500), nullable=False)
    is_verified = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_rule_field_scheme", "field_name", "scheme_id"),
    )

    @validates("operator")
    def validate_operator(self, key, op_value):
        allowed = {"==", "!=", "<=", ">=", "<", ">", "in", "not_in"}
        if op_value not in allowed:
            raise ValueError(f"Invalid operator '{op_value}'. Allowed: {allowed}")
        return op_value

    def to_dict(self):
        return {
            "id": self.id,
            "scheme_id": self.scheme_id,
            "rule_name": self.rule_name,
            "field_name": self.field_name,
            "operator": self.operator,
            "expected_value": self.expected_value,
            "description": self.description,
            "source_reference": self.source_reference,
            "is_verified": self.is_verified,
        }

    def __repr__(self):
        return f"<SchemeEligibilityRule id={self.id} field='{self.field_name}' op='{self.operator}'>"


class SchemeDocument(db.Model):
    """
    Official required or optional document for a scheme application.
    """
    __tablename__ = "scheme_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scheme_id = Column(Integer, ForeignKey("government_schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    document_name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    source_reference = Column(String(500), nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "scheme_id": self.scheme_id,
            "document_name": self.document_name,
            "description": self.description,
            "is_mandatory": self.is_mandatory,
            "source_reference": self.source_reference,
        }

    def __repr__(self):
        return f"<SchemeDocument id={self.id} name='{self.document_name}' mandatory={self.is_mandatory}>"


class SchemeApplicationStep(db.Model):
    """
    Step-by-step verified official application procedure for a scheme.
    """
    __tablename__ = "scheme_application_steps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scheme_id = Column(Integer, ForeignKey("government_schemes.id", ondelete="CASCADE"), nullable=False, index=True)
    step_number = Column(Integer, nullable=False)
    instruction = Column(Text, nullable=False)
    official_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_step_scheme_order", "scheme_id", "step_number"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "scheme_id": self.scheme_id,
            "step_number": self.step_number,
            "instruction": self.instruction,
            "official_url": self.official_url,
        }

    def __repr__(self):
        return f"<SchemeApplicationStep scheme_id={self.scheme_id} step={self.step_number}>"
