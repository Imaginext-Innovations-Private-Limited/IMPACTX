
from flask import Blueprint, request, jsonify, session
from flask_bcrypt import Bcrypt
from email_validator import validate_email, EmailNotValidError
from database import get_db_connection

auth = Blueprint("auth", __name__)
bcrypt = Bcrypt()


@auth.route("/register", methods=["POST"])
def register():
    data = request.get_json()

    full_name = data.get("full_name", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    if not full_name or not email or not password:
        return jsonify({"message": "All fields are required"}), 400

    try:
        validate_email(email)
    except EmailNotValidError:
        return jsonify({"message": "Enter a valid email address"}), 400

    if len(password) < 8:
        return jsonify({"message": "Password must contain at least 8 characters"}), 400

    if password != confirm_password:
        return jsonify({"message": "Passwords do not match"}), 400

    connection = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            "SELECT student_id FROM students WHERE email = %s",
            (email,)
        )

        if cursor.fetchone():
            return jsonify({"message": "Email already registered"}), 409

        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

        cursor.execute(
            """
            INSERT INTO students (full_name, email, password_hash)
            VALUES (%s, %s, %s)
            """,
            (full_name, email, password_hash)
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Registration successful! Please log in."
        }), 201

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


@auth.route("/login", methods=["POST"])
def login():
    data = request.get_json()

    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return jsonify({"message": "Email and password are required"}), 400

    connection = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT student_id, full_name, email, password_hash, is_active
            FROM students
            WHERE email = %s
            """,
            (email,)
        )

        student = cursor.fetchone()

        if not student or not student["is_active"]:
            return jsonify({"message": "Invalid email or password"}), 401

        if not bcrypt.check_password_hash(student["password_hash"], password):
            return jsonify({"message": "Invalid email or password"}), 401

        session.clear()
        session.permanent = True
        session["student_id"] = student["student_id"]

        return jsonify({
            "status": "success",
            "message": "Login successful!",
            "student": {
                "student_id": student["student_id"],
                "full_name": student["full_name"],
                "email": student["email"]
            }
        })

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


@auth.route("/me", methods=["GET"])
def current_student():
    if "student_id" not in session:
        return jsonify({"message": "Not logged in"}), 401

    connection = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT student_id, full_name, email
            FROM students
            WHERE student_id = %s AND is_active = TRUE
            """,
            (session["student_id"],)
        )

        student = cursor.fetchone()

        if not student:
            session.clear()
            return jsonify({"message": "Student account not found"}), 404

        return jsonify({
            "status": "success",
            "student": student
        })

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()


@auth.route("/logout", methods=["POST"])
def logout():
    session.clear()

    return jsonify({
        "status": "success",
        "message": "Logged out successfully"
    })
