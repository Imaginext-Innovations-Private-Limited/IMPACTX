
from flask import Blueprint, request, jsonify, session
from werkzeug.security import check_password_hash
from database import get_db_connection

admin_auth = Blueprint("admin_auth", __name__)


# ADMIN LOGIN
@admin_auth.route("/login", methods=["POST"])
def admin_login():
    data = request.get_json() or {}

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({
            "message": "Email and password are required"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT admin_id, full_name, email, password_hash
            FROM admins
            WHERE email = %s
        """, (email,))

        admin = cursor.fetchone()

        if not admin or not check_password_hash(
            admin["password_hash"], password
        ):
            return jsonify({
                "message": "Invalid admin email or password"
            }), 401

        session.clear()
        session["admin_id"] = admin["admin_id"]

        return jsonify({
            "status": "success",
            "message": "Admin login successful",
            "admin": {
                "admin_id": admin["admin_id"],
                "full_name": admin["full_name"],
                "email": admin["email"]
            }
        }), 200

    finally:
        cursor.close()
        connection.close()


# CHECK ADMIN SESSION
@admin_auth.route("/me", methods=["GET"])
def get_admin():
    if "admin_id" not in session:
        return jsonify({
            "message": "Admin login required"
        }), 401

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT admin_id, full_name, email
            FROM admins
            WHERE admin_id = %s
        """, (session["admin_id"],))

        admin = cursor.fetchone()

        if not admin:
            session.pop("admin_id", None)
            return jsonify({
                "message": "Admin account not found"
            }), 401

        return jsonify({
            "status": "success",
            "admin": admin
        }), 200

    finally:
        cursor.close()
        connection.close()


# ADMIN LOGOUT
@admin_auth.route("/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_id", None)

    return jsonify({
        "status": "success",
        "message": "Admin logged out successfully"
    }), 200
