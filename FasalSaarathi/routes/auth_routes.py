"""
FasalSaarathi — Module 1: Authentication & Profile Flask Blueprint
"""

import os
from flask import Blueprint, current_app, jsonify, render_template, request, session

from agent.advisor_agent import SUPPORTED_LANGUAGES
from tools.auth_tool import (
    DEFAULT_USERS_DB,
    PICTURE_PIN_ICONS,
    get_guest_profile,
    get_user_profile,
    login_user,
    register_user,
    update_user_profile,
)

auth_bp = Blueprint("auth", __name__)


def _users_db_path() -> str:
    return current_app.config.get("USERS_DB_PATH") or os.getenv("FASAL_USERS_DB") or DEFAULT_USERS_DB


def _parse_coord(val):
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@auth_bp.route("/login", methods=["GET"])
def login_page():
    """Render the Picture-PIN Login & Farmer Onboarding page."""
    return render_template(
        "login.html",
        icons=PICTURE_PIN_ICONS,
        languages=SUPPORTED_LANGUAGES,
    )


@auth_bp.route("/api/auth/icons", methods=["GET"])
def api_auth_icons():
    """Return available Picture-PIN icons and localized labels."""
    return jsonify({"status": "success", "icons": PICTURE_PIN_ICONS})


@auth_bp.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    payload = request.get_json(silent=True) or {}
    res = register_user(
        name=payload.get("name", ""),
        phone=payload.get("phone", ""),
        pin_icons=payload.get("pin_icons"),
        persona=payload.get("persona", "farmer"),
        language=payload.get("language", "en"),
        location_query=payload.get("location_query", ""),
        lat=_parse_coord(payload.get("lat")),
        lon=_parse_coord(payload.get("lon")),
        primary_crop=payload.get("primary_crop", "tomato"),
        db_path=_users_db_path(),
    )
    if res["status"] != "success":
        code = 409 if res["status"] == "duplicate_phone" else 400
        return jsonify(res), code

    session["user_id"] = res["user"]["user_id"]
    return jsonify(res), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    payload = request.get_json(silent=True) or {}
    res = login_user(
        phone=payload.get("phone", ""),
        pin_icons=payload.get("pin_icons"),
        db_path=_users_db_path(),
    )
    if res["status"] != "success":
        code = 401 if res["status"] == "unauthorized" else 400
        return jsonify(res), code

    session["user_id"] = res["user"]["user_id"]
    return jsonify(res)


@auth_bp.route("/api/auth/guest", methods=["POST"])
def api_auth_guest():
    res = get_guest_profile(db_path=_users_db_path())
    session["user_id"] = res["user"]["user_id"]
    return jsonify(res)


@auth_bp.route("/api/auth/me", methods=["GET"])
def api_auth_me():
    user_id = session.get("user_id")
    if user_id:
        user = get_user_profile(user_id, db_path=_users_db_path())
        if user:
            return jsonify({"status": "success", "authenticated": True, "user": user})
        session.pop("user_id", None)

    return jsonify({"status": "success", "authenticated": False, "user": None})


@auth_bp.route("/api/auth/profile", methods=["POST"])
def api_auth_profile():
    user_id = session.get("user_id") or "guest"
    payload = request.get_json(silent=True) or {}
    res = update_user_profile(user_id, payload, db_path=_users_db_path())
    if res["status"] == "not_found":
        return jsonify(res), 404
    session["user_id"] = res["user"]["user_id"]
    return jsonify(res)


@auth_bp.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    session.pop("user_id", None)
    return jsonify({"status": "success", "message": "Logged out successfully."})
