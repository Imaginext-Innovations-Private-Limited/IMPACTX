
from flask import Blueprint, request, jsonify, session
from database import get_db_connection

counselling = Blueprint("counselling", __name__)


# Submit counselling request
@counselling.route("/", methods=["POST"])
def create_request():
    if "student_id" not in session:
        return jsonify({"message": "Please login first"}), 401

    data = request.get_json() or {}

    preferred_date = data.get("preferred_date")
    preferred_time = data.get("preferred_time")
    reason = data.get("reason", "").strip()

    if not preferred_date or not preferred_time:
        return jsonify({
            "message": "Preferred date and time are required"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            INSERT INTO counselling_appointments
            (student_id, preferred_date, preferred_time, reason)
            VALUES (%s, %s, %s, %s)
        """, (
            session["student_id"],
            preferred_date,
            preferred_time,
            reason
        ))

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Counselling request submitted successfully"
        }), 201

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


# Get logged-in student's requests
@counselling.route("/", methods=["GET"])
def get_requests():
    if "student_id" not in session:
        return jsonify({"message": "Please login first"}), 401

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT appointment_id, preferred_date,
                   preferred_time, reason, status, created_at
            FROM counselling_appointments
            WHERE student_id = %s
            ORDER BY created_at DESC
        """, (session["student_id"],))

        requests_list = cursor.fetchall()

        for item in requests_list:
            item["preferred_date"] = str(item["preferred_date"])
            item["preferred_time"] = str(item["preferred_time"])
            item["created_at"] = str(item["created_at"])

        return jsonify({
            "status": "success",
            "requests": requests_list
        }), 200

    finally:
        cursor.close()
        connection.close()


# Cancel counselling request
@counselling.route("/<int:appointment_id>", methods=["DELETE"])
def cancel_request(appointment_id):
    if "student_id" not in session:
        return jsonify({"message": "Please login first"}), 401

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE counselling_appointments
            SET status = 'Cancelled'
            WHERE appointment_id = %s
              AND student_id = %s
              AND status = 'Pending'
        """, (appointment_id, session["student_id"]))

        connection.commit()

        if cursor.rowcount == 0:
            return jsonify({
                "message": "Request not found or cannot be cancelled"
            }), 404

        return jsonify({
            "status": "success",
            "message": "Counselling request cancelled successfully"
        }), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()
