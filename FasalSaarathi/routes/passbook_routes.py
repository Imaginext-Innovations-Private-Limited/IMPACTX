"""
FasalSaarathi — Module 4: Farm Passbook Flask Blueprint
"""

import os
from flask import Blueprint, current_app, jsonify, request, session

from tools.auth_tool import DEFAULT_USERS_DB
from tools.passbook_tool import (
    build_daily_passbook_briefing,
    clear_passbook_history,
    get_passbook_history,
    handle_passbook_reply,
)

passbook_bp = Blueprint("passbook", __name__)


def _users_db_path() -> str:
    return current_app.config.get("USERS_DB_PATH") or os.getenv("FASAL_USERS_DB") or DEFAULT_USERS_DB


def _parse_coord(val):
    if val is None or str(val).strip() == "":
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


@passbook_bp.route("/api/passbook/daily", methods=["GET"])
def api_passbook_daily():
    uid = session.get("user_id") or "guest"
    loc = request.args.get("location")
    lat = _parse_coord(request.args.get("lat"))
    lon = _parse_coord(request.args.get("lon"))
    commodity = (request.args.get("commodity") or "tomato").strip()
    lang = request.args.get("language")
    save = request.args.get("save", "true").lower() != "false"

    res = build_daily_passbook_briefing(
        user_id=uid,
        location_override=loc,
        lat=lat,
        lon=lon,
        commodity=commodity,
        language=lang,
        save_to_history=save,
        db_path=_users_db_path(),
    )
    return jsonify(res)


@passbook_bp.route("/api/passbook/reply", methods=["POST"])
def api_passbook_reply():
    uid = session.get("user_id") or "guest"
    payload = request.get_json(silent=True) or {}
    res = handle_passbook_reply(
        user_id=uid,
        action=payload.get("action", ""),
        text=payload.get("text", ""),
        location_override=payload.get("location"),
        commodity=payload.get("commodity", "tomato"),
        language=payload.get("language"),
        db_path=_users_db_path(),
    )
    return jsonify(res)


@passbook_bp.route("/api/passbook/history", methods=["GET"])
def api_passbook_history():
    uid = session.get("user_id") or "guest"
    history = get_passbook_history(uid, db_path=_users_db_path())
    return jsonify({"status": "success", "user_id": uid, "messages": history})


@passbook_bp.route("/api/passbook/clear", methods=["POST"])
def api_passbook_clear():
    uid = session.get("user_id") or "guest"
    clear_passbook_history(uid, db_path=_users_db_path())
    return jsonify({"status": "success"})
