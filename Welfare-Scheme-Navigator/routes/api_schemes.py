"""
Scheme Discovery and Comparison API Blueprint for Sahaaya AI.
Exposes scheme listing, filtering, detail retrieval, and comparison over REST.
"""

from flask import Blueprint, request, jsonify
from models import GovernmentScheme, db
from agent.tools import tool_compare_schemes, tool_search_schemes

schemes_api_bp = Blueprint("schemes_api", __name__)


@schemes_api_bp.route("/schemes", methods=["GET"])
def list_schemes():
    """
    List and filter active government welfare schemes.
    Query parameters:
    - q: search query keyword
    - level: 'Central' or 'State'
    - state: 'Karnataka' or 'All India'
    - category: 'Women', 'Youth', 'Education', 'Agriculture', 'Healthcare', 'Housing', 'Social Security'
    """
    q = request.args.get("q", "").strip()
    level = request.args.get("level", "").strip()
    state = request.args.get("state", "").strip()
    category = request.args.get("category", "").strip()

    # Base query for active schemes
    query = GovernmentScheme.query.filter(
        GovernmentScheme.active_status.in_(["Active", "active", "1", "true", "True"])
    )

    if level:
        query = query.filter(GovernmentScheme.government_level.ilike(f"%{level}%"))

    if state:
        query = query.filter(
            (GovernmentScheme.state.ilike(f"%{state}%")) |
            (GovernmentScheme.government_level == "Central") |
            (GovernmentScheme.state == "All India")
        )

    if category:
        query = query.filter(GovernmentScheme.category.ilike(f"%{category}%"))

    schemes = query.all()

    # If keyword query is provided, perform search matching
    if q:
        keywords = [kw.lower() for kw in q.split() if len(kw) > 1]
        matched = []
        for s in schemes:
            corpus = f"{s.name} {s.description} {s.category} {s.department} {s.benefits} {s.slug}".lower()
            if any(kw in corpus for kw in keywords):
                matched.append(s)
        schemes = matched

    data = [s.to_dict(include_relations=False) for s in schemes]
    return jsonify({
        "success": True,
        "total": len(data),
        "schemes": data,
    }), 200


@schemes_api_bp.route("/schemes/<slug>", methods=["GET"])
def get_scheme(slug):
    """
    Retrieve comprehensive details for a specific scheme by slug,
    including rules, documents, and application steps.
    """
    clean_slug = slug.strip().lower()
    scheme = GovernmentScheme.query.filter_by(slug=clean_slug).first()

    if not scheme:
        return jsonify({
            "success": False,
            "error": "Not Found",
            "message": f"Government scheme with slug '{slug}' was not found.",
            "status_code": 404,
        }), 404

    return jsonify({
        "success": True,
        "scheme": scheme.to_dict(include_relations=True),
    }), 200


@schemes_api_bp.route("/schemes/categories", methods=["GET"])
def get_categories():
    """Return distinct scheme categories and government levels for filters."""
    schemes = GovernmentScheme.query.filter(
        GovernmentScheme.active_status.in_(["Active", "active", "1", "true", "True"])
    ).all()

    categories = sorted(list({s.category for s in schemes if s.category}))
    levels = sorted(list({s.government_level for s in schemes if s.government_level}))
    states = sorted(list({s.state for s in schemes if s.state}))

    return jsonify({
        "success": True,
        "categories": categories,
        "levels": levels,
        "states": states,
        "total_schemes": len(schemes),
    }), 200


@schemes_api_bp.route("/schemes/compare", methods=["POST"])
def compare_schemes_endpoint():
    """
    Compare 2 or 3 schemes side-by-side.
    Payload: {"slugs": ["gruha-lakshmi", "yuva-nidhi"]} or {"scheme_slugs": [...]}
    """
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Request body must be a valid JSON object.",
            "status_code": 400,
        }), 400

    payload = request.get_json() or {}
    slugs = payload.get("slugs")
    if slugs is None:
        slugs = payload.get("scheme_slugs")

    if not isinstance(slugs, list):
        return jsonify({
            "success": False,
            "error": "Please provide a list of at least two scheme slugs in 'slugs'.",
            "status_code": 400,
        }), 400

    # Deduplicate while preserving order
    clean_slugs = []
    for s in slugs:
        if isinstance(s, (str, int)):
            clean = str(s).strip().lower()
            if clean and clean not in clean_slugs:
                clean_slugs.append(clean)

    if len(clean_slugs) < 2:
        return jsonify({
            "success": False,
            "error": "Please select at least two distinct schemes to compare.",
            "status_code": 400,
        }), 400

    if len(clean_slugs) > 3:
        return jsonify({
            "success": False,
            "error": "You can compare a maximum of 3 schemes at a time.",
            "status_code": 400,
        }), 400

    result = tool_compare_schemes(clean_slugs)
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code
