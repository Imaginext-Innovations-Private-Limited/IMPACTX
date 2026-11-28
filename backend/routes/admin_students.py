
from flask import Blueprint, jsonify, session
from database import get_db_connection

admin_students = Blueprint("admin_students", __name__)


@admin_students.route("/", methods=["GET"])
def get_students():

    # Check admin login
    if "admin_id" not in session:
        return jsonify({
            "message": "Admin login required"
        }), 401

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT student_id, full_name, email
            FROM students
            ORDER BY student_id DESC
        """)

        students = cursor.fetchall()

        return jsonify({
            "status": "success",
            "total_students": len(students),
            "students": students
        }), 200

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        cursor.close()
        connection.close()
