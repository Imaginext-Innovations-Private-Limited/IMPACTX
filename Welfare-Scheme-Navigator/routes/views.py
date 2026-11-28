"""
Web Frontend Views Blueprint for Sahaaya AI.
Renders responsive HTML templates for citizen interaction and navigation.
"""

from flask import Blueprint, render_template, request, jsonify, abort
from models import GovernmentScheme

views_bp = Blueprint("views", __name__)


@views_bp.route("/home")
def home():
    """Explicit home page route."""
    schemes = GovernmentScheme.query.filter(
        GovernmentScheme.active_status.in_(["Active", "active", "1", "true", "True"])
    ).limit(6).all()
    return render_template("index.html", popular_schemes=schemes)


@views_bp.route("/dashboard")
def dashboard():
    """Citizen welfare dashboard."""
    schemes = GovernmentScheme.query.filter(
        GovernmentScheme.active_status.in_(["Active", "active", "1", "true", "True"])
    ).all()
    karnataka_count = sum(1 for s in schemes if s.government_level == "State" or (s.state and "karnataka" in s.state.lower()))
    central_count = sum(1 for s in schemes if s.government_level == "Central" or (s.state and "all india" in s.state.lower()))
    categories = sorted(list({s.category for s in schemes if s.category}))

    return render_template(
        "dashboard.html",
        total_schemes=len(schemes),
        karnataka_count=karnataka_count,
        central_count=central_count,
        categories=categories,
        schemes=schemes,
    )


@views_bp.route("/schemes")
def schemes_discovery():
    """Search and browse all available schemes."""
    return render_template("schemes.html")


@views_bp.route("/schemes/<slug>")
def scheme_detail(slug):
    """View verified details, rules, documents, and application steps for a scheme."""
    clean_slug = slug.strip().lower()
    scheme = GovernmentScheme.query.filter_by(slug=clean_slug).first()
    if not scheme:
        abort(404)
    return render_template("scheme_detail.html", scheme=scheme)


@views_bp.route("/eligibility")
def eligibility_checker():
    """Citizen-friendly deterministic eligibility assessment tool."""
    schemes = GovernmentScheme.query.filter(
        GovernmentScheme.active_status.in_(["Active", "active", "1", "true", "True"])
    ).all()
    return render_template("eligibility.html", schemes=schemes)


@views_bp.route("/documents")
@views_bp.route("/documents/<slug>")
def document_checklist(slug=None):
    """Document preparation checklist page."""
    schemes = GovernmentScheme.query.filter(
        GovernmentScheme.active_status.in_(["Active", "active", "1", "true", "True"])
    ).all()
    selected_scheme = None
    if slug:
        clean_slug = slug.strip().lower()
        selected_scheme = GovernmentScheme.query.filter_by(slug=clean_slug).first()
        if not selected_scheme:
            abort(404)

    return render_template("documents.html", schemes=schemes, selected_scheme=selected_scheme)


@views_bp.route("/compare")
def compare_schemes_page():
    """Side-by-side scheme comparison page."""
    schemes = GovernmentScheme.query.filter(
        GovernmentScheme.active_status.in_(["Active", "active", "1", "true", "True"])
    ).all()
    return render_template("compare.html", schemes=schemes)


@views_bp.route("/assistant")
def assistant_page():
    """Conversational AI navigator powered by Gemini tool calling."""
    schemes = GovernmentScheme.query.filter(
        GovernmentScheme.active_status.in_(["Active", "active", "1", "true", "True"])
    ).all()
    return render_template("assistant.html", schemes=schemes)
