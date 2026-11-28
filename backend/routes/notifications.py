
from flask import Blueprint, jsonify, request, session
from database import get_db_connection

notifications = Blueprint("notifications", __name__)


# Get notifications for the logged-in student
@notifications.route("/", methods=["GET"])
def get_notifications():

    if "student_id" not in session:
        return jsonify({"message": "Student login required"}), 401

    student_id = session["student_id"]

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                notification_id,
                appointment_id,
                title,
                message,
                notification_type,
                is_read,
                created_at
            FROM notifications
            WHERE student_id = %s
            ORDER BY created_at DESC
        """, (student_id,))

        notification_list = cursor.fetchall()

        for item in notification_list:
            item["created_at"] = str(item["created_at"])
            item["is_read"] = bool(item["is_read"])

        unread_count = sum(
            1 for item in notification_list
            if not item["is_read"]
        )

        return jsonify({
            "status": "success",
            "notifications": notification_list,
            "unread_count": unread_count
        }), 200

    finally:
        cursor.close()
        connection.close()


# Mark one notification as read
@notifications.route("/<int:notification_id>/read", methods=["PUT"])
def mark_notification_read(notification_id):

    if "student_id" not in session:
        return jsonify({"message": "Student login required"}), 401

    student_id = session["student_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE notifications
            SET is_read = TRUE
            WHERE notification_id = %s
              AND student_id = %s
        """, (notification_id, student_id))

        connection.commit()

        if cursor.rowcount == 0:
            return jsonify({
                "message": "Notification not found"
            }), 404

        return jsonify({
            "status": "success",
            "message": "Notification marked as read"
        }), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()


# Mark all notifications as read
@notifications.route("/read-all", methods=["PUT"])
def mark_all_notifications_read():

    if "student_id" not in session:
        return jsonify({"message": "Student login required"}), 401

    student_id = session["student_id"]

    connection = get_db_connection()
    cursor = connection.cursor()

    try:
        cursor.execute("""
            UPDATE notifications
            SET is_read = TRUE
            WHERE student_id = %s
        """, (student_id,))

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "All notifications marked as read"
        }), 200

    except Exception as e:
        connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        cursor.close()
        connection.close()
