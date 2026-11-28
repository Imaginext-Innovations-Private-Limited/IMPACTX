
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config
from database import get_db_connection
from routes.auth import auth, bcrypt
from routes.mood import mood
from routes.study import study
from routes.reminders import reminders
from routes.ai_assistant import ai_assistant
from routes.peer_support import peer_support
from routes.counselling import counselling
from routes.admin_auth import admin_auth
from routes.admin_dashboard import admin_dashboard
from routes.notifications import notifications
from routes.admin_students import admin_students

app = Flask(__name__)
app.config.from_object(Config)

bcrypt.init_app(app)
CORS(
    app,
    resources={
        r"/api/*": {
            "origins": [
                "http://localhost:5173",
                "http://127.0.0.1:5173"
            ]
        }
    },
    supports_credentials=True
)

app.register_blueprint(auth, url_prefix="/api/auth")
app.register_blueprint(mood, url_prefix="/api/mood")
app.register_blueprint(study, url_prefix="/api/study")
app.register_blueprint(reminders, url_prefix="/api/reminders")
app.register_blueprint(ai_assistant, url_prefix="/api/ai")
app.register_blueprint(peer_support, url_prefix="/api/peer")
app.register_blueprint(counselling, url_prefix="/api/counselling")
app.register_blueprint(admin_auth, url_prefix="/api/admin")
app.register_blueprint(
    admin_dashboard,
    url_prefix="/api/admin"
)
app.register_blueprint(notifications, url_prefix="/api/notifications")
app.register_blueprint(admin_students, url_prefix="/api/admin/students")


@app.route("/")
def home():
    return jsonify({
        "message": "Serenify Backend is running!"
    })


@app.route("/api/health")
def health():
    return jsonify({
        "status": "success",
        "message": "Backend is working!"
    })


@app.route("/api/database-check")
def database_check():
    connection = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        cursor.execute("SELECT DATABASE()")
        result = cursor.fetchone()
        cursor.close()

        return jsonify({
            "status": "success",
            "database": result[0],
            "message": "MySQL connected successfully!"
        })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

    finally:
        if connection and connection.is_connected():
            connection.close()


if __name__ == "__main__":
    app.run(debug=True, port=5000)
