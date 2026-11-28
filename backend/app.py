import os
from flask import Flask, jsonify
from flask_cors import CORS
from pymongo.errors import PyMongoError

from config import Config
from extensions import check_db_connection, get_db, init_db, jwt
from routes.accessibility import accessibility_bp
from routes.ai import ai_bp
from routes.auth import auth_bp
from routes.documents import documents_bp
from routes.practice import practice_bp
from routes.transcripts import transcripts_bp


def create_app(config_overrides: dict | None = None, mongo_client_override=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config_overrides:
        app.config.update(config_overrides)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    CORS(
        app,
        resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}},
        supports_credentials=True,
    )

    jwt.init_app(app)
    init_db(app, client_override=mongo_client_override)

    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(_jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        if not jti:
            return False
        try:
            return get_db().revoked_tokens.find_one({"jti": jti}) is not None
        except PyMongoError:
            return False

    @jwt.unauthorized_loader
    def handle_missing_token(reason):
        return jsonify({"error": "Authentication required. Please log in."}), 401

    @jwt.invalid_token_loader
    def handle_invalid_token(reason):
        return jsonify({"error": "Invalid authentication token. Please log in again."}), 401

    @jwt.expired_token_loader
    def handle_expired_token(_jwt_header, _jwt_payload):
        return jsonify({"error": "Your session has expired. Please log in again."}), 401

    @app.errorhandler(413)
    def handle_file_too_large(_err):
        return jsonify({"error": "Uploaded file exceeds the maximum allowed size limit."}), 413

    @app.errorhandler(PyMongoError)
    def handle_db_error(err):
        app.logger.error(f"Database error: {err}")
        return (
            jsonify(
                {
                    "error": "Database connection unavailable. Verify MongoDB is running and MONGO_URI is configured."
                }
            ),
            503,
        )

    @app.route("/api/health", methods=["GET"])
    def health():
        db_ok, db_msg = check_db_connection()
        return (
            jsonify(
                {
                    "status": "ok" if db_ok else "degraded",
                    "database": db_msg,
                    "gemini_configured": bool(app.config.get("GEMINI_API_KEY")),
                    "whisper_configured": bool(app.config.get("WHISPER_API_URL")),
                }
            ),
            200 if db_ok else 503,
        )

    app.register_blueprint(auth_bp)
    app.register_blueprint(accessibility_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(ai_bp)
    app.register_blueprint(practice_bp)
    app.register_blueprint(transcripts_bp)

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))
