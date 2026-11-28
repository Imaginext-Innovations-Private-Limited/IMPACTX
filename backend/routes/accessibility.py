from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import get_db
from utils.serializers import (
    DEFAULT_ACCESSIBILITY_SETTINGS,
    parse_object_id,
    serialize_user,
    utc_now,
)

accessibility_bp = Blueprint("accessibility", __name__, url_prefix="/api/accessibility")

ALLOWED_MODES = {"dyslexia", "low_vision", "hearing"}
ALLOWED_FONT_STYLES = {"default", "dyslexia", "serif", "mono"}
ALLOWED_THEMES = {"light", "dark"}


@accessibility_bp.route("", methods=["GET"])
@jwt_required()
def get_accessibility():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    db = get_db()
    user_doc = db.users.find_one({"_id": user_oid})
    if not user_doc:
        return jsonify({"error": "User not found."}), 404

    prefs = {**DEFAULT_ACCESSIBILITY_SETTINGS, **(user_doc.get("accessibility") or {})}
    return jsonify({"accessibility": prefs}), 200


@accessibility_bp.route("", methods=["PUT"])
@jwt_required()
def update_accessibility():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    data = request.get_json(silent=True) or {}
    db = get_db()
    user_doc = db.users.find_one({"_id": user_oid})
    if not user_doc:
        return jsonify({"error": "User not found."}), 404

    current = {**DEFAULT_ACCESSIBILITY_SETTINGS, **(user_doc.get("accessibility") or {})}

    if "modes" in data:
        raw_modes = data.get("modes")
        if not isinstance(raw_modes, list):
            return jsonify({"error": "modes must be an array."}), 400
        current["modes"] = [m for m in raw_modes if m in ALLOWED_MODES]

    if "font_size" in data:
        try:
            fs = int(data["font_size"])
            current["font_size"] = max(14, min(32, fs))
        except (ValueError, TypeError):
            return jsonify({"error": "font_size must be a number between 14 and 32."}), 400

    if "font_style" in data:
        style = str(data["font_style"])
        if style not in ALLOWED_FONT_STYLES:
            return jsonify({"error": f"font_style must be one of {sorted(ALLOWED_FONT_STYLES)}."}), 400
        current["font_style"] = style

    if "theme" in data:
        theme = str(data["theme"])
        if theme not in ALLOWED_THEMES:
            return jsonify({"error": f"theme must be one of {sorted(ALLOWED_THEMES)}."}), 400
        current["theme"] = theme

    if "high_contrast" in data:
        current["high_contrast"] = bool(data["high_contrast"])

    if "line_spacing" in data:
        try:
            ls = float(data["line_spacing"])
            current["line_spacing"] = round(max(1.2, min(2.6, ls)), 2)
        except (ValueError, TypeError):
            return jsonify({"error": "line_spacing must be between 1.2 and 2.6."}), 400

    if "letter_spacing" in data:
        try:
            let_s = float(data["letter_spacing"])
            current["letter_spacing"] = round(max(0.0, min(0.16, let_s)), 3)
        except (ValueError, TypeError):
            return jsonify({"error": "letter_spacing must be between 0 and 0.16."}), 400

    if "zoom" in data:
        try:
            zoom = int(data["zoom"])
            current["zoom"] = max(80, min(160, zoom))
        except (ValueError, TypeError):
            return jsonify({"error": "zoom must be between 80 and 160."}), 400

    if "highlight_keywords" in data:
        current["highlight_keywords"] = bool(data["highlight_keywords"])

    if "tts_speed" in data:
        try:
            speed = float(data["tts_speed"])
            current["tts_speed"] = round(max(0.5, min(2.0, speed)), 2)
        except (ValueError, TypeError):
            return jsonify({"error": "tts_speed must be between 0.5 and 2.0."}), 400

    if "tts_voice" in data:
        current["tts_voice"] = str(data["tts_voice"] or "")

    if "onboarding_completed" in data:
        current["onboarding_completed"] = bool(data["onboarding_completed"])

    updated = db.users.find_one_and_update(
        {"_id": user_oid},
        {"$set": {"accessibility": current, "updated_at": utc_now()}},
        return_document=True,
    )

    return (
        jsonify(
            {
                "message": "Accessibility preferences saved.",
                "accessibility": current,
                "user": serialize_user(updated),
            }
        ),
        200,
    )
