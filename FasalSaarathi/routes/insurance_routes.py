"""
FasalSaarathi — Module 3: PMFBY Crop Insurance Flask Blueprint
"""

import os
import uuid
from flask import Blueprint, current_app, jsonify, request, session
from PIL import Image
from werkzeug.utils import secure_filename

from tools.auth_tool import DEFAULT_USERS_DB, get_user_profile
from tools.insurance_tool import (
    calculate_pmfby_quote,
    create_claim_dossier,
    delete_insurance_policy,
    evaluate_weather_claim_alert,
    list_claim_dossiers,
    list_insurance_policies,
    save_insurance_policy,
)

insurance_bp = Blueprint("insurance", __name__)
ALLOWED_IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}


def _users_db_path() -> str:
    return current_app.config.get("USERS_DB_PATH") or os.getenv("FASAL_USERS_DB") or DEFAULT_USERS_DB


def _parse_coord(val):
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@insurance_bp.route("/api/insurance/quote", methods=["GET"])
def api_insurance_quote():
    crop = (request.args.get("crop") or "paddy").strip()
    season = (request.args.get("season") or "").strip()
    acres = request.args.get("acres") or 1.0
    custom_sum = request.args.get("custom_sum_per_acre")
    lang = (request.args.get("language") or "en").strip().lower()

    res = calculate_pmfby_quote(
        crop=crop,
        season=season,
        acres=acres,
        custom_sum_per_acre=custom_sum,
        language=lang,
    )
    if res.get("status") != "success":
        return jsonify(res), 400
    return jsonify(res)


@insurance_bp.route("/api/insurance/policies", methods=["GET"])
def api_list_policies():
    uid = session.get("user_id") or "guest"
    policies = list_insurance_policies(uid, db_path=_users_db_path())
    return jsonify({"status": "success", "user_id": uid, "policies": policies})


@insurance_bp.route("/api/insurance/policy", methods=["POST"])
def api_save_policy():
    uid = session.get("user_id") or "guest"
    payload = request.get_json(silent=True) or {}
    res = save_insurance_policy(
        user_id=uid,
        crop=payload.get("crop", "paddy"),
        season=payload.get("season", ""),
        acres=payload.get("acres", 1.0),
        language=payload.get("language", "en"),
        db_path=_users_db_path(),
    )
    if res.get("status") != "success":
        return jsonify(res), 400
    return jsonify(res), 201


@insurance_bp.route("/api/insurance/policy/<policy_id>", methods=["DELETE"])
def api_delete_policy(policy_id: str):
    uid = session.get("user_id") or "guest"
    res = delete_insurance_policy(uid, policy_id, db_path=_users_db_path())
    if res.get("status") == "not_found":
        return jsonify(res), 404
    return jsonify(res)


@insurance_bp.route("/api/insurance/weather-alert", methods=["GET"])
def api_weather_alert():
    loc = (request.args.get("location") or "").strip()
    lat = _parse_coord(request.args.get("lat"))
    lon = _parse_coord(request.args.get("lon"))
    lang = (request.args.get("language") or "en").strip().lower()

    # Fallback to logged-in user's saved location if omitted
    if not loc and (lat is None or lon is None):
        uid = session.get("user_id")
        if uid:
            user = get_user_profile(uid, db_path=_users_db_path())
            if user:
                loc = user.get("location_query") or ""
                if lat is None and lon is None:
                    lat = user.get("lat")
                    lon = user.get("lon")

    res = evaluate_weather_claim_alert(
        location_query=loc or None,
        lat=lat,
        lon=lon,
        language=lang,
    )
    if res.get("status") == "missing_location":
        return jsonify(res), 400
    return jsonify(res)


@insurance_bp.route("/api/insurance/claims", methods=["GET"])
def api_list_claims():
    uid = session.get("user_id") or "guest"
    claims = list_claim_dossiers(uid, db_path=_users_db_path())
    return jsonify({"status": "success", "user_id": uid, "claims": claims})


@insurance_bp.route("/api/insurance/claim-dossier", methods=["POST"])
def api_create_claim_dossier():
    uid = session.get("user_id") or "guest"
    photo_url = ""

    if request.content_type and "multipart/form-data" in request.content_type:
        loc = (request.form.get("location") or "").strip()
        lat = _parse_coord(request.form.get("lat"))
        lon = _parse_coord(request.form.get("lon"))
        policy_id = (request.form.get("policy_id") or "").strip() or None
        notes = (request.form.get("notes") or "").strip()
        lang = (request.form.get("language") or "en").strip().lower()

        file = request.files.get("photo")
        if file and file.filename:
            ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
            if ext not in ALLOWED_IMAGE_EXTS:
                return jsonify({
                    "status": "error",
                    "message": f"Invalid photo file type. Allowed: {', '.join(sorted(ALLOWED_IMAGE_EXTS))}",
                }), 400

            upload_dir = current_app.config.get("UPLOAD_FOLDER")
            os.makedirs(upload_dir, exist_ok=True)
            safe_name = f"claim_{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
            save_path = os.path.join(upload_dir, safe_name)
            file.save(save_path)
            try:
                with Image.open(save_path) as img:
                    img.verify()
            except Exception:
                os.remove(save_path)
                return jsonify({"status": "error", "message": "Invalid or corrupted image file."}), 400
            photo_url = f"/static/uploads/{safe_name}"
    else:
        payload = request.get_json(silent=True) or {}
        loc = (payload.get("location") or "").strip()
        lat = _parse_coord(payload.get("lat"))
        lon = _parse_coord(payload.get("lon"))
        policy_id = (payload.get("policy_id") or "").strip() or None
        notes = (payload.get("notes") or "").strip()
        lang = (payload.get("language") or "en").strip().lower()

    res = create_claim_dossier(
        user_id=uid,
        location_query=loc,
        lat=lat,
        lon=lon,
        policy_id=policy_id,
        photo_url=photo_url,
        notes=notes,
        language=lang,
        db_path=_users_db_path(),
    )
    return jsonify(res), 201
