
from flask import Blueprint, jsonify, request, session
from database import get_db_connection

reminders = Blueprint("reminders", __name__)


# GET ALL REMINDERS
@reminders.route("/", methods=["GET"])
def get_reminders():

    if "student_id" not in session:
        return jsonify({"message": "Not logged in"}), 401

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute("""
            SELECT reminder_id, title, description,
                   reminder_datetime, is_completed
            FROM reminders
            WHERE student_id = %s
            ORDER BY reminder_datetime ASC
        """, (session["student_id"],))

        data = cursor.fetchall()

        for item in data:
            if item["reminder_datetime"]:
                item["reminder_datetime"] = (
                    item["reminder_datetime"].isoformat()
                )

        return jsonify({
            "status": "success",
            "reminders": data
        })

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# ADD REMINDER
@reminders.route("/", methods=["POST"])
def add_reminder():

    if "student_id" not in session:
        return jsonify({"message": "Not logged in"}), 401

    data = request.get_json() or {}

    title = data.get("title", "").strip()
    description = data.get("description", "")
    reminder_datetime = data.get("reminder_datetime")

    if not title or not reminder_datetime:
        return jsonify({
            "message": "Title and reminder date/time are required."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            INSERT INTO reminders
            (student_id, title, description, reminder_datetime)
            VALUES (%s, %s, %s, %s)
        """, (
            session["student_id"],
            title,
            description,
            reminder_datetime
        ))

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Reminder added successfully!",
            "reminder_id": cursor.lastrowid
        }), 201

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# UPDATE REMINDER STATUS
@reminders.route("/<int:reminder_id>", methods=["PUT"])
def update_reminder(reminder_id):

    if "student_id" not in session:
        return jsonify({"message": "Not logged in"}), 401

    data = request.get_json() or {}
    is_completed = data.get("is_completed")

    if not isinstance(is_completed, bool):
        return jsonify({
            "message": "A valid completion status is required."
        }), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            UPDATE reminders
            SET is_completed = %s
            WHERE reminder_id = %s AND student_id = %s
        """, (
            is_completed,
            reminder_id,
            session["student_id"]
        ))

        connection.commit()

        if cursor.rowcount == 0:
            return jsonify({"message": "Reminder not found."}), 404

        return jsonify({
            "status": "success",
            "message": "Reminder updated successfully!"
        })

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


# DELETE REMINDER
@reminders.route("/<int:reminder_id>", methods=["DELETE"])
def delete_reminder(reminder_id):

    if "student_id" not in session:
        return jsonify({"message": "Not logged in"}), 401

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute("""
            DELETE FROM reminders
            WHERE reminder_id = %s AND student_id = %s
        """, (
            reminder_id,
            session["student_id"]
        ))

        connection.commit()

        if cursor.rowcount == 0:
            return jsonify({"message": "Reminder not found."}), 404

        return jsonify({
            "status": "success",
            "message": "Reminder deleted successfully!"
        })

    except Exception as e:
        if connection:
            connection.rollback()
        return jsonify({"message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
