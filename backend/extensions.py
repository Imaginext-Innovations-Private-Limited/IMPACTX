from urllib.parse import urlparse
from flask_jwt_extended import JWTManager
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

jwt = JWTManager()

_mongo_client = None
_db = None


def _extract_db_name(mongo_uri: str, explicit_name: str = "") -> str:
    if explicit_name:
        return explicit_name
    parsed = urlparse(mongo_uri)
    path = (parsed.path or "").lstrip("/")
    if path:
        return path.split("/")[0]
    return "learnable_ai"


def init_db(app, client_override=None):
    """Initialize MongoDB client, database handle, and indexes."""
    global _mongo_client, _db

    if client_override is not None:
        _mongo_client = client_override
    else:
        _mongo_client = MongoClient(
            app.config["MONGO_URI"],
            serverSelectionTimeoutMS=5000,
        )

    db_name = _extract_db_name(
        app.config["MONGO_URI"], app.config.get("MONGO_DB_NAME", "")
    )
    _db = _mongo_client[db_name]

    try:
        _db.users.create_index([("email", ASCENDING)], unique=True)
        _db.documents.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        _db.simplifications.create_index(
            [("user_id", ASCENDING), ("document_id", ASCENDING), ("created_at", DESCENDING)]
        )
        _db.practice_sets.create_index(
            [("user_id", ASCENDING), ("document_id", ASCENDING), ("created_at", DESCENDING)]
        )
        _db.practice_attempts.create_index(
            [("user_id", ASCENDING), ("created_at", DESCENDING)]
        )
        _db.transcripts.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        _db.revoked_tokens.create_index([("jti", ASCENDING)], unique=True)
    except PyMongoError as exc:
        app.logger.warning(f"MongoDB index setup deferred/failed: {exc}")

    return _db


def get_db():
    """Return active database instance."""
    if _db is None:
        raise RuntimeError("Database has not been initialized.")
    return _db


def check_db_connection():
    """Verify MongoDB connectivity with a lightweight ping."""
    if _mongo_client is None:
        return False, "Database client not initialized"
    try:
        _mongo_client.admin.command("ping")
        return True, "connected"
    except PyMongoError as exc:
        return False, str(exc)
