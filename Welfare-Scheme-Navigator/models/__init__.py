"""
Models package for Sahaaya AI.
Exposes database instance and all entities.
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models so they are registered with SQLAlchemy metadata
from models.scheme import (
    GovernmentScheme,
    SchemeEligibilityRule,
    SchemeDocument,
    SchemeApplicationStep,
)
from models.citizen import CitizenProfile

__all__ = [
    "db",
    "GovernmentScheme",
    "SchemeEligibilityRule",
    "SchemeDocument",
    "SchemeApplicationStep",
    "CitizenProfile",
]
