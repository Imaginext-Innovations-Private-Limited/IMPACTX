"""
Repeatable, Idempotent Scheme Catalog Seeder for Sahaaya AI.
Populates the database with verified Central and Karnataka State Government welfare schemes.
"""

import sys
import json
import logging
from datetime import datetime, timezone
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
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_schemes")


def seed_database(app=None, json_path=None):
    """
    Seed or update government welfare schemes from JSON seed file.
    Idempotent: Re-running this script updates existing schemes without creating duplicates.
    """
    if app is None:
        app = create_app()

    if json_path is None:
        json_path = PROJECT_ROOT / "data" / "schemes_seed.json"
    else:
        json_path = Path(json_path)

    if not json_path.exists():
        raise FileNotFoundError(f"Scheme catalog seed file not found: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    stats = {
        "total_catalog_entries": len(catalog),
        "inserted": 0,
        "updated": 0,
        "verified": 0,
        "unverified": 0,
        "total_rules": 0,
        "total_documents": 0,
        "total_steps": 0,
        "errors": []
    }

    with app.app_context():
        # Ensure database tables exist
        db.create_all()

        for entry in catalog:
            try:
                slug = entry.get("slug")
                if not slug:
                    raise ValueError(f"Scheme entry missing 'slug': {entry.get('name')}")

                verification_status = entry.get("verification_status", "Verified")
                if verification_status == "Verified":
                    stats["verified"] += 1
                else:
                    stats["unverified"] += 1

                # Parse verified timestamp if available
                last_verified_str = entry.get("last_verified_at")
                last_verified_dt = None
                if last_verified_str:
                    try:
                        last_verified_dt = datetime.fromisoformat(last_verified_str.replace("Z", "+00:00"))
                    except Exception:
                        last_verified_dt = datetime.now(timezone.utc)

                existing_scheme = GovernmentScheme.query.filter_by(slug=slug).first()

                if existing_scheme:
                    # Update existing scheme attributes
                    existing_scheme.name = entry["name"]
                    existing_scheme.description = entry["description"]
                    existing_scheme.category = entry["category"]
                    existing_scheme.government_level = entry["government_level"]
                    existing_scheme.state = entry.get("state")
                    existing_scheme.department = entry["department"]
                    existing_scheme.official_url = entry["official_url"]
                    existing_scheme.application_url = entry.get("application_url")
                    existing_scheme.benefits = entry["benefits"]
                    existing_scheme.active_status = entry.get("active_status", "Active")
                    existing_scheme.verification_status = verification_status
                    existing_scheme.last_verified_at = last_verified_dt
                    scheme_obj = existing_scheme
                    stats["updated"] += 1
                    logger.info(f"Updating existing scheme: {slug}")
                else:
                    # Insert new scheme
                    scheme_obj = GovernmentScheme(
                        name=entry["name"],
                        slug=slug,
                        description=entry["description"],
                        category=entry["category"],
                        government_level=entry["government_level"],
                        state=entry.get("state"),
                        department=entry["department"],
                        official_url=entry["official_url"],
                        application_url=entry.get("application_url"),
                        benefits=entry["benefits"],
                        active_status=entry.get("active_status", "Active"),
                        verification_status=verification_status,
                        last_verified_at=last_verified_dt,
                    )
                    db.session.add(scheme_obj)
                    db.session.flush()  # Generate primary key ID
                    stats["inserted"] += 1
                    logger.info(f"Inserting new scheme: {slug}")

                # Refresh related items idempotently
                # 1. Eligibility Rules
                SchemeEligibilityRule.query.filter_by(scheme_id=scheme_obj.id).delete()
                for rule_data in entry.get("rules", []):
                    rule = SchemeEligibilityRule(
                        scheme_id=scheme_obj.id,
                        rule_name=rule_data["rule_name"],
                        field_name=rule_data["field_name"],
                        operator=rule_data["operator"],
                        expected_value=str(rule_data["expected_value"]),
                        description=rule_data["description"],
                        source_reference=rule_data["source_reference"],
                        is_verified=rule_data.get("is_verified", True),
                    )
                    db.session.add(rule)
                    stats["total_rules"] += 1

                # 2. Scheme Documents
                SchemeDocument.query.filter_by(scheme_id=scheme_obj.id).delete()
                for doc_data in entry.get("documents", []):
                    doc = SchemeDocument(
                        scheme_id=scheme_obj.id,
                        document_name=doc_data["document_name"],
                        description=doc_data.get("description"),
                        is_mandatory=doc_data.get("is_mandatory", True),
                        source_reference=doc_data["source_reference"],
                    )
                    db.session.add(doc)
                    stats["total_documents"] += 1

                # 3. Application Steps
                SchemeApplicationStep.query.filter_by(scheme_id=scheme_obj.id).delete()
                for step_data in entry.get("steps", []):
                    step = SchemeApplicationStep(
                        scheme_id=scheme_obj.id,
                        step_number=step_data["step_number"],
                        instruction=step_data["instruction"],
                        official_url=step_data.get("official_url"),
                    )
                    db.session.add(step)
                    stats["total_steps"] += 1

            except Exception as e:
                logger.error(f"Error processing scheme '{entry.get('name')}': {e}")
                stats["errors"].append({"scheme": entry.get("name"), "error": str(e)})

        db.session.commit()

        # Final verification count
        total_in_db = GovernmentScheme.query.count()
        stats["total_in_database"] = total_in_db

    logger.info("=" * 60)
    logger.info(" SCHEME SEED PROCESS COMPLETED")
    logger.info(f"  Total Entries in Catalog: {stats['total_catalog_entries']}")
    logger.info(f"  Inserted:                 {stats['inserted']}")
    logger.info(f"  Updated:                  {stats['updated']}")
    logger.info(f"  Verified Schemes:         {stats['verified']}")
    logger.info(f"  Unverified / In Review:   {stats['unverified']}")
    logger.info(f"  Total Rules Seeded:       {stats['total_rules']}")
    logger.info(f"  Total Documents Seeded:   {stats['total_documents']}")
    logger.info(f"  Total Steps Seeded:       {stats['total_steps']}")
    logger.info(f"  Total Schemes in DB:      {stats['total_in_database']}")
    logger.info("=" * 60)

    return stats


if __name__ == "__main__":
    result = seed_database()
    print(json.dumps(result, indent=2))
