"""
Eligibility and Document Checklist API Blueprint for Sahaaya AI.
Exposes deterministic welfare evaluation and document checklists over REST.
"""

from flask import Blueprint, request, jsonify
from models import GovernmentScheme
from engine.eligibility_engine import EligibilityEngine
from engine.document_engine import DocumentEngine
from engine.validator import validate_citizen_profile

eligibility_bp = Blueprint("eligibility_api", __name__)


@eligibility_bp.route("/eligibility/check", methods=["POST"])
def check_single_scheme_eligibility():
    """
    Evaluate citizen profile against a single government scheme.
    Payload:
    {
        "slug": "gruha-lakshmi",
        "profile": { ... demographic & socio-economic attributes ... }
    }
    """
    if not request.is_json:
        return jsonify({
            "error": "Bad Request",
            "message": "Request payload must be valid JSON.",
            "status_code": 400
        }), 400

    payload = request.get_json() or {}
    slug = payload.get("slug")
    profile = payload.get("profile")

    if not slug or not isinstance(slug, str):
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'slug' is required and must be a string.",
            "status_code": 400
        }), 400

    if profile is None or not isinstance(profile, dict):
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'profile' is required and must be a dictionary of attributes.",
            "status_code": 400
        }), 400

    clean_slug = slug.strip().lower()

    # Validate profile attributes before evaluation
    is_valid, error_msg, error_details = validate_citizen_profile(profile, scheme_slug=clean_slug)
    if not is_valid:
        return jsonify({
            "success": False,
            "error": "Validation Error",
            "message": error_msg or "Invalid profile attributes provided.",
            "details": error_details,
            "status_code": 400
        }), 400

    scheme = GovernmentScheme.query.filter_by(slug=clean_slug).first()
    if not scheme:
        return jsonify({
            "error": "Not Found",
            "message": f"Government scheme with slug '{slug}' not found.",
            "status_code": 404
        }), 404

    try:
        evaluation = EligibilityEngine.evaluate_scheme(scheme, profile)
        return jsonify({
            "success": True,
            "data": evaluation
        }), 200
    except Exception as e:
        return jsonify({
            "error": "Internal Error",
            "message": f"Failed to evaluate eligibility: {str(e)}",
            "status_code": 500
        }), 500


@eligibility_bp.route("/eligibility/check-all", methods=["POST"])
def check_all_schemes_eligibility():
    """
    Evaluate citizen profile against all active schemes in the database.
    Payload:
    {
        "profile": { ... citizen attributes ... },
        "state_filter": "Karnataka",   (optional)
        "category_filter": "Women"     (optional)
    }
    """
    if not request.is_json:
        return jsonify({
            "error": "Bad Request",
            "message": "Request payload must be valid JSON.",
            "status_code": 400
        }), 400

    payload = request.get_json() or {}
    profile = payload.get("profile")

    if profile is None or not isinstance(profile, dict):
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'profile' is required and must be a dictionary.",
            "status_code": 400
        }), 400

    # Validate profile attributes before evaluation
    is_valid, error_msg, error_details = validate_citizen_profile(profile)
    if not is_valid:
        return jsonify({
            "success": False,
            "error": "Validation Error",
            "message": error_msg or "Invalid profile attributes provided.",
            "details": error_details,
            "status_code": 400
        }), 400

    state_filter = payload.get("state_filter")
    category_filter = payload.get("category_filter")

    query = GovernmentScheme.query.filter_by(active_status="Active")

    if state_filter and isinstance(state_filter, str):
        # Match schemes for that specific state or Central/All India schemes
        query = query.filter(
            (GovernmentScheme.state == state_filter.strip()) |
            (GovernmentScheme.government_level == "Central") |
            (GovernmentScheme.state == "All India")
        )

    if category_filter and isinstance(category_filter, str):
        query = query.filter(GovernmentScheme.category.ilike(f"%{category_filter.strip()}%"))

    schemes = query.all()

    try:
        results = EligibilityEngine.evaluate_all_schemes(schemes, profile)
        return jsonify({
            "success": True,
            "data": results
        }), 200
    except Exception as e:
        return jsonify({
            "error": "Internal Error",
            "message": f"Failed to evaluate schemes: {str(e)}",
            "status_code": 500
        }), 500


@eligibility_bp.route("/documents/<slug>", methods=["GET", "POST"])
def get_scheme_documents_checklist(slug):
    """
    Retrieve official document checklist for a scheme.
    Supports GET (with optional ?collected=doc1,doc2) or POST (with json body {"collected": [...]}).
    """
    clean_slug = slug.strip().lower()
    scheme = GovernmentScheme.query.filter_by(slug=clean_slug).first()

    if not scheme:
        return jsonify({
            "error": "Not Found",
            "message": f"Government scheme with slug '{slug}' not found.",
            "status_code": 404
        }), 404

    collected_items = []

    # Handle collected list from query string or JSON payload
    if request.method == "POST" and request.is_json:
        payload = request.get_json() or {}
        raw_collected = payload.get("collected", [])
        if isinstance(raw_collected, list):
            collected_items = raw_collected
    elif request.args.get("collected"):
        collected_items = [
            item.strip() for item in request.args.get("collected").split(",") if item.strip()
        ]

    try:
        checklist = DocumentEngine.generate_checklist(scheme, collected_items)
        return jsonify({
            "success": True,
            "data": checklist
        }), 200
    except Exception as e:
        return jsonify({
            "error": "Internal Error",
            "message": f"Failed to generate document checklist: {str(e)}",
            "status_code": 500
        }), 500
