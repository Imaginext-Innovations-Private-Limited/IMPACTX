"""
Phase 2 Test Suite for Sahaaya AI.
Tests database models, relationships, PII guards, seed catalog, idempotency, and verification handling.
"""

import sys
import unittest
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

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
from scripts.seed_schemes import seed_database


class TestPhase2DatabaseAndCatalog(unittest.TestCase):
    """Test suite for Phase 2 implementation."""

    def setUp(self):
        """Set up in-memory testing application context."""
        self.app = create_app("testing")
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """Clean up database session and context."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_01_government_scheme_model_creation(self):
        """Test GovernmentScheme instantiation, fields, and to_dict serialization."""
        scheme = GovernmentScheme(
            name="Test Karnataka Scheme",
            slug="test-karnataka-scheme",
            description="A test welfare scheme description.",
            category="Social Welfare",
            government_level="State",
            state="Karnataka",
            department="Social Welfare Department",
            official_url="https://karnataka.gov.in/test",
            application_url="https://sevasindhu.karnataka.gov.in/test",
            benefits="Direct benefit transfer of ₹1,000 monthly.",
            active_status="Active",
            verification_status="Verified",
            last_verified_at=datetime.now(timezone.utc),
        )
        db.session.add(scheme)
        db.session.commit()

        retrieved = GovernmentScheme.query.filter_by(slug="test-karnataka-scheme").first()
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "Test Karnataka Scheme")
        self.assertEqual(retrieved.government_level, "State")
        self.assertEqual(retrieved.state, "Karnataka")
        self.assertEqual(retrieved.verification_status, "Verified")

        data = retrieved.to_dict(include_relations=False)
        self.assertEqual(data["slug"], "test-karnataka-scheme")
        self.assertEqual(data["category"], "Social Welfare")

    def test_02_relationships_and_cascading_deletes(self):
        """Test relationships between schemes, rules, documents, and steps, plus cascade delete."""
        scheme = GovernmentScheme(
            name="Cascade Test Scheme",
            slug="cascade-test-scheme",
            description="Testing cascading relationships.",
            category="Education",
            government_level="Central",
            state="All India",
            department="Ministry of Education",
            official_url="https://scholarships.gov.in/",
            benefits="Fee waiver.",
            active_status="Active",
            verification_status="Verified",
        )
        db.session.add(scheme)
        db.session.flush()

        # Add rule
        rule = SchemeEligibilityRule(
            scheme_id=scheme.id,
            rule_name="Income Check",
            field_name="annual_household_income",
            operator="<=",
            expected_value="250000",
            description="Income under 2.5 Lakhs",
            source_reference="https://scholarships.gov.in/guidelines",
        )
        # Add document
        doc = SchemeDocument(
            scheme_id=scheme.id,
            document_name="Income Certificate",
            description="Valid certificate issued by revenue authority",
            is_mandatory=True,
            source_reference="https://scholarships.gov.in/guidelines",
        )
        # Add step
        step = SchemeApplicationStep(
            scheme_id=scheme.id,
            step_number=1,
            instruction="Register on NSP portal with mobile number.",
            official_url="https://scholarships.gov.in/",
        )

        db.session.add_all([rule, doc, step])
        db.session.commit()

        # Verify relationships load correctly
        fetched = GovernmentScheme.query.filter_by(slug="cascade-test-scheme").first()
        self.assertEqual(len(fetched.rules), 1)
        self.assertEqual(len(fetched.documents), 1)
        self.assertEqual(len(fetched.steps), 1)
        self.assertEqual(fetched.rules[0].field_name, "annual_household_income")
        self.assertEqual(fetched.documents[0].document_name, "Income Certificate")

        # Test Cascade Delete
        db.session.delete(fetched)
        db.session.commit()

        self.assertEqual(SchemeEligibilityRule.query.count(), 0)
        self.assertEqual(SchemeDocument.query.count(), 0)
        self.assertEqual(SchemeApplicationStep.query.count(), 0)

    def test_03_required_field_and_format_validation(self):
        """Test model validators for slugs, names, and URLs."""
        # Invalid slug (spaces or uppercase)
        with self.assertRaises(ValueError):
            GovernmentScheme(
                name="Invalid Slug Scheme",
                slug="Invalid Slug With Spaces",
                description="desc",
                category="cat",
                government_level="State",
                department="dept",
                official_url="https://gov.in",
                benefits="ben",
            )

        # Empty name
        with self.assertRaises(ValueError):
            GovernmentScheme(
                name="   ",
                slug="valid-slug",
                description="desc",
                category="cat",
                government_level="State",
                department="dept",
                official_url="https://gov.in",
                benefits="ben",
            )

        # Invalid official URL
        with self.assertRaises(ValueError):
            GovernmentScheme(
                name="Valid Name",
                slug="valid-slug-url-test",
                description="desc",
                category="cat",
                government_level="State",
                department="dept",
                official_url="not-a-valid-http-url",
                benefits="ben",
            )

    def test_04_unique_scheme_slug_constraint(self):
        """Test that duplicate slugs violate database uniqueness constraints."""
        s1 = GovernmentScheme(
            name="Scheme One",
            slug="duplicate-slug-test",
            description="desc 1",
            category="Health",
            government_level="Central",
            department="dept",
            official_url="https://nha.gov.in",
            benefits="benefits",
        )
        db.session.add(s1)
        db.session.commit()

        s2 = GovernmentScheme(
            name="Scheme Two",
            slug="duplicate-slug-test",
            description="desc 2",
            category="Health",
            government_level="Central",
            department="dept",
            official_url="https://nha.gov.in",
            benefits="benefits",
        )
        db.session.add(s2)
        with self.assertRaises(IntegrityError):
            db.session.commit()
        db.session.rollback()

    def test_05_citizen_profile_validation_and_pii_guards(self):
        """Test CitizenProfile stores non-sensitive attributes and strictly blocks PII."""
        profile = CitizenProfile(
            age=24,
            gender="Female",
            state="Karnataka",
            district="Bengaluru Urban",
            caste_category="OBC",
            annual_household_income=180000,
            occupation="Student",
            is_student=True,
            student_degree_level="Undergraduate",
            is_bpl_card_holder=True,
            ration_card_type="BPL",
            is_female_head_of_family=False,
            landholding_acres=0.0,
        )
        db.session.add(profile)
        db.session.commit()

        saved = CitizenProfile.query.first()
        self.assertEqual(saved.age, 24)
        self.assertEqual(saved.annual_household_income, 180000)
        self.assertTrue(saved.is_bpl_card_holder)

        # Test PII rejection: 12-digit Aadhaar number pattern in district or session
        with self.assertRaises(ValueError):
            CitizenProfile(district="District with 1234 5678 9012 Aadhaar")

        # Test PII rejection: 10-char PAN format (ABCDE1234F)
        with self.assertRaises(ValueError):
            CitizenProfile(occupation="Farmer ABCDE1234F")

        # Test invalid negative age
        with self.assertRaises(ValueError):
            CitizenProfile(age=-5)

    def test_06_seed_catalog_file_integrity(self):
        """Verify data/schemes_seed.json exists, is valid JSON, and contains all 10 required schemes."""
        import json
        seed_path = PROJECT_ROOT / "data" / "schemes_seed.json"
        self.assertTrue(seed_path.exists(), "schemes_seed.json must exist in data/")

        with open(seed_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        self.assertEqual(len(catalog), 10, "Seed catalog must contain exactly 10 initial schemes.")

        expected_slugs = {
            "gruha-lakshmi",
            "yuva-nidhi",
            "gruha-jyothi",
            "shakti-scheme",
            "anna-bhagya",
            "ssp-post-matric-scholarship",
            "pm-kisan",
            "pmay-housing",
            "ayushman-bharat-pmjay",
            "sukanya-samriddhi-yojana",
        }
        catalog_slugs = {item["slug"] for item in catalog}
        self.assertEqual(expected_slugs, catalog_slugs)

        # Verify each item has required official fields
        for entry in catalog:
            self.assertTrue(entry["official_url"].startswith("http"), f"Invalid official_url in {entry['slug']}")
            self.assertEqual(entry["verification_status"], "Verified")
            self.assertIsNotNone(entry.get("last_verified_at"))
            self.assertGreater(len(entry["rules"]), 0, f"Rules missing in {entry['slug']}")
            self.assertGreater(len(entry["documents"]), 0, f"Documents missing in {entry['slug']}")
            self.assertGreater(len(entry["steps"]), 0, f"Steps missing in {entry['slug']}")

    def test_07_seed_script_execution(self):
        """Test seed_database() execution populating SQLite with all 10 schemes."""
        stats = seed_database(app=self.app)

        self.assertEqual(stats["total_catalog_entries"], 10)
        self.assertEqual(stats["inserted"], 10)
        self.assertEqual(stats["verified"], 10)
        self.assertEqual(stats["unverified"], 0)
        self.assertEqual(len(stats["errors"]), 0)

        # Verify DB counts
        self.assertEqual(GovernmentScheme.query.count(), 10)
        self.assertEqual(SchemeEligibilityRule.query.count(), 25)
        self.assertEqual(SchemeDocument.query.count(), 30)
        self.assertEqual(SchemeApplicationStep.query.count(), 38)

    def test_08_duplicate_prevention_and_idempotency(self):
        """Run seed_database() twice and assert that no duplicate schemes are created."""
        stats1 = seed_database(app=self.app)
        self.assertEqual(stats1["inserted"], 10)

        # Second run
        stats2 = seed_database(app=self.app)
        self.assertEqual(stats2["inserted"], 0)
        self.assertEqual(stats2["updated"], 10)
        self.assertEqual(stats2["total_in_database"], 10)

        # Assert DB count is still strictly 10
        self.assertEqual(GovernmentScheme.query.count(), 10)
        self.assertEqual(SchemeEligibilityRule.query.count(), 25)
        self.assertEqual(SchemeDocument.query.count(), 30)
        self.assertEqual(SchemeApplicationStep.query.count(), 38)

    def test_09_database_persistence_and_queries(self):
        """Verify queries across Karnataka vs Central schemes."""
        seed_database(app=self.app)

        karnataka_schemes = GovernmentScheme.query.filter_by(state="Karnataka").all()
        self.assertEqual(len(karnataka_schemes), 6)

        central_schemes = GovernmentScheme.query.filter_by(government_level="Central").all()
        self.assertEqual(len(central_schemes), 4)

        # Query Gruha Lakshmi and verify loaded relationships
        gl = GovernmentScheme.query.filter_by(slug="gruha-lakshmi").first()
        self.assertIsNotNone(gl)
        self.assertEqual(gl.category, "Women & Child Development")
        rule_fields = [r.field_name for r in gl.rules]
        self.assertIn("is_female_head_of_family", rule_fields)
        self.assertIn("ration_card_type", rule_fields)

    def test_10_unverified_scheme_handling(self):
        """Test that unverified or in-review schemes are explicitly tracked with verification_status."""
        unverified_scheme = GovernmentScheme(
            name="Draft Pilot Scheme",
            slug="draft-pilot-scheme",
            description="A pilot program awaiting official gazette confirmation.",
            category="Skill Development",
            government_level="State",
            state="Karnataka",
            department="Department of Personnel",
            official_url="https://karnataka.gov.in/pilot",
            benefits="Under review.",
            active_status="Needs Review",
            verification_status="Unverified",
            last_verified_at=None,
        )
        db.session.add(unverified_scheme)
        db.session.commit()

        retrieved = GovernmentScheme.query.filter_by(slug="draft-pilot-scheme").first()
        self.assertEqual(retrieved.verification_status, "Unverified")
        self.assertEqual(retrieved.active_status, "Needs Review")
        self.assertIsNone(retrieved.last_verified_at)

        # Query only verified schemes
        verified_count = GovernmentScheme.query.filter_by(verification_status="Verified").count()
        self.assertEqual(verified_count, 0)  # in this clean test setup, only 1 unverified scheme exists


if __name__ == "__main__":
    unittest.main()
