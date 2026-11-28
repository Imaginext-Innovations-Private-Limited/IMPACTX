
from flask import Blueprint, request, jsonify, session
from database import get_db_connection

study = Blueprint("study", __name__)


@study.route("/", methods=["POST"])
def add_task():
    if "student_id" not in session:
        return jsonify({"message": "Please log in first"}), 401

    data = request.get_json() or {}

    title = data.get("title", "").strip()
    task_date = data.get("task_date")
    task_time = data.get("task_time")

    if not title or not task_date or not task_time:
        return jsonify({"message": "All fields are required"}), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            INSERT INTO study_tasks
            (student_id, title, task_date, task_time)
            VALUES (%s, %s, %s, %s)
            """,
            (session["student_id"], title, task_date, task_time)
        )

        connection.commit()

        return jsonify({
            "status": "success",
            "message": "Study task added successfully!"
        }), 201

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@study.route("/", methods=["GET"])
def get_tasks():
    if "student_id" not in session:
        return jsonify({"message": "Please log in first"}), 401

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT task_id, title, task_date, task_time, is_completed
            FROM study_tasks
            WHERE student_id = %s
            ORDER BY task_date ASC, task_time ASC
            """,
            (session["student_id"],)
        )

        tasks = cursor.fetchall()

        for task in tasks:
            task["task_date"] = str(task["task_date"])
            task["task_time"] = str(task["task_time"])

        return jsonify({
            "status": "success",
            "tasks": tasks
        })

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@study.route("/<int:task_id>", methods=["PUT"])
def update_task(task_id):
    if "student_id" not in session:
        return jsonify({"message": "Please log in first"}), 401

    data = request.get_json() or {}
    is_completed = data.get("is_completed")

    if not isinstance(is_completed, bool):
        return jsonify({"message": "Invalid completion status"}), 400

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            UPDATE study_tasks
            SET is_completed = %s
            WHERE task_id = %s AND student_id = %s
            """,
            (is_completed, task_id, session["student_id"])
        )

        connection.commit()

        if cursor.rowcount == 0:
            return jsonify({"message": "Task not found"}), 404

        return jsonify({
            "status": "success",
            "message": "Task updated successfully!"
        })

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()


@study.route("/<int:task_id>", methods=["DELETE"])
def delete_task(task_id):
    if "student_id" not in session:
        return jsonify({"message": "Please log in first"}), 401

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            DELETE FROM study_tasks
            WHERE task_id = %s AND student_id = %s
            """,
            (task_id, session["student_id"])
        )

        connection.commit()

        if cursor.rowcount == 0:
            return jsonify({"message": "Task not found"}), 404

        return jsonify({
            "status": "success",
            "message": "Task deleted successfully!"
        })

    except Exception as e:
        return jsonify({"message": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
