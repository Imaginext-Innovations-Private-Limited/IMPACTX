"""
Sahaaya AI - Welfare Scheme Navigator
Flask Application Factory
"""

import os
from pathlib import Path
from flask import Flask, jsonify, render_template, request
from config import config_by_name, Config
from models import db


def create_app(config_name=None):
    """
    Application factory for Sahaaya AI.
    """
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )

    # Load configuration
    cfg = config_by_name.get(config_name, Config)
    app.config.from_object(cfg)

    # Ensure required directories exist
    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    cfg.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    cfg.FAISS_INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Register API Blueprints
    from routes.api_eligibility import eligibility_bp
    from routes.api_rag import rag_bp
    from routes.api_agent import agent_bp
    from routes.api_schemes import schemes_api_bp
    from routes.views import views_bp
    app.register_blueprint(eligibility_bp, url_prefix="/api")
    app.register_blueprint(rag_bp, url_prefix="/api")
    app.register_blueprint(agent_bp, url_prefix="/api")
    app.register_blueprint(schemes_api_bp, url_prefix="/api")
    app.register_blueprint(views_bp)

    # Health check and basic diagnostics route
    @app.route("/api/health")
    def health_check():
        has_gemini_key = bool(
            app.config.get("GEMINI_API_KEY")
            and app.config.get("GEMINI_API_KEY", "").strip().lower() not in ("your_gemini_api_key_here", "none", "placeholder")
        )
        return jsonify({
            "status": "healthy",
            "service": "Sahaaya AI - Welfare Scheme Navigator",
            "version": "1.0.0",
            "track": "Track A: Agentic AI for Communities",
            "gemini_model": app.config.get("GEMINI_MODEL", "not_configured"),
            "gemini_configured": has_gemini_key,
            "agent_status": "ready" if has_gemini_key else "fallback_mode",
            "retrieval_backend": app.config.get("RETRIEVAL_BACKEND", "sqlite_fts5"),
            "disclaimer": app.config.get("INDICATIVE_ONLY_DISCLAIMER"),
            "database_status": "configured"
        }), 200

    # Landing route (serves HTML for browser clients, JSON for API/tests)
    @app.route("/")
    def index():
        accept = request.headers.get("Accept", "")
        if "text/html" in accept or request.args.get("view") == "html":
            from models import GovernmentScheme
            schemes = GovernmentScheme.query.filter(
                GovernmentScheme.active_status.in_(["Active", "active", "1", "true", "True"])
            ).limit(6).all()
            return render_template("index.html", popular_schemes=schemes)

        return jsonify({
            "platform": "Sahaaya AI - Welfare Scheme Navigator",
            "description": (
                "An Agentic AI-powered welfare scheme navigator helping Indian citizens "
                "discover government welfare schemes, check eligibility, understand required "
                "documents, and receive step-by-step application guidance."
            ),
            "status": "Phase 1 Initialization Complete",
            "health_endpoint": "/api/health"
        }), 200

    # Global Error Handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if "text/html" in request.headers.get("Accept", ""):
            return render_template("404.html"), 404
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource was not found on Sahaaya AI.",
            "status_code": 404
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        if "text/html" in request.headers.get("Accept", ""):
            return render_template("500.html"), 500
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "status_code": 500
        }), 500

    # Create database tables within application context
    with app.app_context():
        db.create_all()
    return app


if __name__ == "__main__":
    app = create_app()
    port = app.config.get("PORT", 8000)
    host = app.config.get("HOST", "127.0.0.1")
    debug = app.config.get("DEBUG", True)
    print(f"\n=======================================================")
    print(f" SAHAAYA AI: WELFARE SCHEME NAVIGATOR")
    print(f" Running on http://{host}:{port}")
    print(f" Gemini Model: {app.config.get('GEMINI_MODEL')}")
    print(f"=======================================================\n")
    app.run(host=host, port=port, debug=debug)
