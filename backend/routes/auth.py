import re
from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token, get_jwt, get_jwt_identity, jwt_required
from pymongo.errors import DuplicateKeyError
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import get_db
from utils.serializers import (
    DEFAULT_ACCESSIBILITY_SETTINGS,
    parse_object_id,
    serialize_user,
    utc_now,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    if len(full_name) < 2:
        return jsonify({"error": "Full name must be at least 2 characters."}), 400
    if not EMAIL_REGEX.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters long."}), 400
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    db = get_db()
    now = utc_now()
    user_doc = {
        "full_name": full_name,
        "email": email,
        "password_hash": generate_password_hash(password),
        "accessibility": dict(DEFAULT_ACCESSIBILITY_SETTINGS),
        "created_at": now,
        "updated_at": now,
    }

    try:
        result = db.users.insert_one(user_doc)
    except DuplicateKeyError:
        return jsonify({"error": "An account with this email already exists."}), 409

    user_doc["_id"] = result.inserted_id
    access_token = create_access_token(identity=str(result.inserted_id))

    return (
        jsonify(
            {
                "message": "Registration successful.",
                "access_token": access_token,
                "user": serialize_user(user_doc),
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    db = get_db()
    user_doc = db.users.find_one({"email": email})
    if not user_doc or not check_password_hash(user_doc.get("password_hash", ""), password):
        return jsonify({"error": "Invalid email or password."}), 401

    access_token = create_access_token(identity=str(user_doc["_id"]))
    return (
        jsonify(
            {
                "message": "Login successful.",
                "access_token": access_token,
                "user": serialize_user(user_doc),
            }
        ),
        200,
    )


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt().get("jti")
    if jti:
        db = get_db()
        db.revoked_tokens.update_one(
            {"jti": jti},
            {"$set": {"jti": jti, "revoked_at": utc_now()}},
            upsert=True,
        )
    return jsonify({"message": "Logged out successfully."}), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_me():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid authentication token."}), 401

    db = get_db()
    user_doc = db.users.find_one({"_id": user_oid})
    if not user_doc:
        return jsonify({"error": "User account not found."}), 404

    return jsonify({"user": serialize_user(user_doc)}), 200


@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid authentication token."}), 401

    data = request.get_json(silent=True) or {}
    full_name = (data.get("full_name") or "").strip()
    if len(full_name) < 2:
        return jsonify({"error": "Full name must be at least 2 characters."}), 400

    db = get_db()
    result = db.users.find_one_and_update(
        {"_id": user_oid},
        {"$set": {"full_name": full_name, "updated_at": utc_now()}},
        return_document=True,
    )
    if not result:
        return jsonify({"error": "User account not found."}), 404

    return jsonify({"message": "Profile updated.", "user": serialize_user(result)}), 200
