
from flask import Blueprint, request, jsonify, session
from database import get_db_connection
from datetime import date

mood = Blueprint("mood", __name__)


@mood.route("/", methods=["POST"])
def save_mood():

    if "student_id" not in session:
        return jsonify({"message": "Please log in first"}), 401

    data = request.get_json() or {}
    selected_mood = data.get("mood", "").strip()

    allowed_moods = [
        "Amazing", "Good", "Okay", "Stressed", "Low"
    ]

    if selected_mood not in allowed_moods:
        return jsonify({"message": "Invalid mood selection"}), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO mood_logs (student_id, mood, checkin_date)
            VALUES (%s, %s, %s)
            """,
            (session["student_id"], selected_mood, date.today())
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Your mood check-in was saved!"
        }), 201

    except Exception as e:
        return jsonify({"message": "Unable to save mood"}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@mood.route("/", methods=["GET"])
def get_moods():

    if "student_id" not in session:
        return jsonify({"message": "Please log in first"}), 401

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT mood_id, mood, checkin_date, created_at
            FROM mood_logs
            WHERE student_id = %s
            ORDER BY created_at DESC
            """,
            (session["student_id"],)
        )

        records = cursor.fetchall()

        for record in records:
            record["checkin_date"] = str(record["checkin_date"])
            record["created_at"] = str(record["created_at"])

        return jsonify({
            "status": "success",
            "moods": records
        })

    except Exception:
        return jsonify({"message": "Unable to retrieve mood history"}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
