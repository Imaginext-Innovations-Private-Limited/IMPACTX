
from flask import Blueprint, jsonify, request, session
from database import get_db_connection

admin_dashboard = Blueprint("admin_dashboard", __name__)


# Check admin authentication
def is_admin_logged_in():
    return "admin_id" in session


# View all counselling requests
@admin_dashboard.route("/counselling", methods=["GET"])
def get_counselling_requests():

    if not is_admin_logged_in():
        return jsonify({"message": "Admin login required"}), 401

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                ca.appointment_id,
                ca.student_id,
                s.full_name,
                s.email,
                ca.preferred_date,
                ca.preferred_time,
                ca.reason,
                ca.status,
                ca.created_at
            FROM counselling_appointments ca
            JOIN students s
                ON ca.student_id = s.student_id
            ORDER BY ca.created_at DESC
        """)

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


# Approve or reject counselling requests
@admin_dashboard.route(
    "/counselling/<int:appointment_id>",
    methods=["PUT"]
)
def update_counselling_status(appointment_id):

    if not is_admin_logged_in():
        return jsonify({"message": "Admin login required"}), 401

    data = request.get_json() or {}
    new_status = data.get("status")

    if new_status not in ["Approved", "Rejected"]:
        return jsonify({
            "message": "Invalid status"
        }), 400

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        # Get student ID for this pending request
        cursor.execute("""
            SELECT student_id
            FROM counselling_appointments
            WHERE appointment_id = %s
              AND status = 'Pending'
        """, (appointment_id,))

        result = cursor.fetchone()

        if not result:
            return jsonify({
                "message": "Request not found or already processed"
            }), 404

        student_id = result[0]

        # Update counselling request
        cursor.execute("""
            UPDATE counselling_appointments
            SET status = %s
            WHERE appointment_id = %s
              AND status = 'Pending'
        """, (new_status, appointment_id))

        if cursor.rowcount == 0:
            connection.rollback()
            return jsonify({
                "message": "Request could not be updated"
            }), 404

        # Create notification message
        if new_status == "Approved":
            title = "Counselling Request Approved"
            message = (
                "Your counselling request has been approved by the "
                "administrator. Please check your counselling details."
            )
        else:
            title = "Counselling Request Rejected"
            message = (
                "Your counselling request has been rejected by the "
                "administrator. Please contact the administrator "
                "if you need further assistance."
            )

        # Insert notification
        cursor.execute("""
            INSERT INTO notifications
            (student_id, appointment_id, title, message, notification_type)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            student_id,
            appointment_id,
            title,
            message,
            "Counselling"
        ))

        connection.commit()

        return jsonify({
            "status": "success",
            "message": f"Counselling request {new_status.lower()} successfully",
            "notification_created": True
        }), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()
