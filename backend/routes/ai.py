from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import get_db
from services.gemini_service import AIServiceError, GeminiService
from utils.serializers import parse_object_id, to_iso, utc_now

ai_bp = Blueprint("ai", __name__, url_prefix="/api/ai")


def _build_gemini() -> GeminiService:
    return GeminiService(
        api_key=current_app.config.get("GEMINI_API_KEY", ""),
        model=current_app.config.get("GEMINI_MODEL", "gemini-2.5-flash"),
    )


@ai_bp.route("/simplify", methods=["POST"])
@jwt_required()
def simplify_text():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    data = request.get_json(silent=True) or {}
    doc_id = data.get("document_id")
    custom_text = (data.get("text") or "").strip()

    db = get_db()
    user_doc = db.users.find_one({"_id": user_oid})
    modes = ((user_doc or {}).get("accessibility") or {}).get("modes") or []

    doc = None
    doc_oid = None
    if doc_id:
        doc_oid = parse_object_id(doc_id)
        if not doc_oid:
            return jsonify({"error": "Invalid document ID."}), 400
        doc = db.documents.find_one({"_id": doc_oid, "user_id": user_oid})
        if not doc:
            return jsonify({"error": "Document not found."}), 404

    source_text = custom_text or (doc.get("extracted_text", "").strip() if doc else "")
    if not source_text:
        return jsonify({"error": "No text available to simplify. Please select text or upload a text-based PDF."}), 400

    try:
        result = _build_gemini().simplify_text(source_text, accessibility_modes=modes)
    except AIServiceError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

    now = utc_now()
    record = {
        "user_id": user_oid,
        "document_id": doc_oid,
        "document_filename": doc.get("filename") if doc else "Custom Passage",
        "source_text": source_text,
        "simplified_text": result["simplified_text"],
        "reading_summary": result["reading_summary"],
        "difficult_words": result["difficult_words"],
        "key_concepts": result["key_concepts"],
        "created_at": now,
    }
    inserted = db.simplifications.insert_one(record)

    latest_payload = {
        "simplification_id": str(inserted.inserted_id),
        "source_text": source_text,
        "simplified_text": result["simplified_text"],
        "reading_summary": result["reading_summary"],
        "difficult_words": result["difficult_words"],
        "key_concepts": result["key_concepts"],
        "created_at": to_iso(now),
    }

    if doc_oid:
        db.documents.update_one(
            {"_id": doc_oid, "user_id": user_oid},
            {"$set": {"latest_simplification": latest_payload, "updated_at": now}},
        )

    return jsonify({"simplification": latest_payload}), 200


@ai_bp.route("/simplifications/<doc_id>", methods=["GET"])
@jwt_required()
def list_document_simplifications(doc_id: str):
    user_oid = parse_object_id(get_jwt_identity())
    doc_oid = parse_object_id(doc_id)
    if not user_oid or not doc_oid:
        return jsonify({"error": "Invalid document ID."}), 400

    db = get_db()
    items = list(
        db.simplifications.find({"user_id": user_oid, "document_id": doc_oid}).sort(
            "created_at", -1
        )
    )
    serialized = [
        {
            "simplification_id": str(item["_id"]),
            "document_id": str(item["document_id"]),
            "source_text": item.get("source_text", ""),
            "simplified_text": item.get("simplified_text", ""),
            "reading_summary": item.get("reading_summary", ""),
            "difficult_words": item.get("difficult_words", []),
            "key_concepts": item.get("key_concepts", []),
            "created_at": to_iso(item.get("created_at")),
        }
        for item in items
    ]
    return jsonify({"simplifications": serialized}), 200


@ai_bp.route("/explain-word", methods=["POST"])
@jwt_required()
def explain_word():
    data = request.get_json(silent=True) or {}
    word = (data.get("word") or "").strip()
    context = (data.get("context") or "").strip()
    if not word:
        return jsonify({"error": "Please provide a word or term to explain."}), 400

    try:
        explanation = _build_gemini().explain_word(word, context)
    except AIServiceError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

    return jsonify({"explanation": explanation}), 200


@ai_bp.route("/revision-plan", methods=["POST"])
@jwt_required()
def generate_revision_plan():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    db = get_db()
    user_doc = db.users.find_one({"_id": user_oid})
    modes = ((user_doc or {}).get("accessibility") or {}).get("modes") or []

    docs = list(db.documents.find({"user_id": user_oid}).sort("created_at", -1).limit(10))
    attempts = list(
        db.practice_attempts.find({"user_id": user_oid}).sort("created_at", -1).limit(10)
    )

    docs_summary = [
        {
            "filename": d.get("filename", ""),
            "word_count": d.get("word_count", 0),
            "has_simplification": bool(d.get("latest_simplification")),
            "key_concepts": (d.get("latest_simplification") or {}).get("key_concepts", [])[:6],
        }
        for d in docs
    ]
    attempts_summary = [
        {
            "title": a.get("title", ""),
            "score_percent": a.get("score_percent", 0),
            "total_questions": a.get("total_questions", 0),
            "correct_count": a.get("correct_count", 0),
        }
        for a in attempts
    ]

    try:
        plan = _build_gemini().generate_revision_plan(modes, docs_summary, attempts_summary)
    except AIServiceError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

    now = utc_now()
    plan_record = {
        "user_id": user_oid,
        **plan,
        "created_at": now,
    }
    inserted = db.revision_plans.insert_one(plan_record)
    plan["id"] = str(inserted.inserted_id)
    plan["created_at"] = to_iso(now)

    return jsonify({"revision_plan": plan}), 201
