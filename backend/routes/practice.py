from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import get_db
from services.gemini_service import AIServiceError, GeminiService
from utils.serializers import parse_object_id, to_iso, utc_now

practice_bp = Blueprint("practice", __name__, url_prefix="/api")


def _build_gemini() -> GeminiService:
    return GeminiService(
        api_key=current_app.config.get("GEMINI_API_KEY", ""),
        model=current_app.config.get("GEMINI_MODEL", "gemini-2.5-flash"),
    )


def _serialize_practice_set(ps: dict) -> dict:
    return {
        "id": str(ps["_id"]),
        "document_id": str(ps["document_id"]),
        "document_filename": ps.get("document_filename", ""),
        "title": ps.get("title", ""),
        "difficulty": ps.get("difficulty", "mixed"),
        "questions": ps.get("questions", []),
        "created_at": to_iso(ps.get("created_at")),
    }


def _serialize_attempt(attempt: dict) -> dict:
    return {
        "id": str(attempt["_id"]),
        "practice_set_id": str(attempt["practice_set_id"]),
        "document_id": str(attempt["document_id"]),
        "document_filename": attempt.get("document_filename", ""),
        "title": attempt.get("title", ""),
        "total_questions": attempt.get("total_questions", 0),
        "correct_count": attempt.get("correct_count", 0),
        "score_percent": attempt.get("score_percent", 0),
        "results": attempt.get("results", []),
        "created_at": to_iso(attempt.get("created_at")),
    }


@practice_bp.route("/practice/generate", methods=["POST"])
@jwt_required()
def generate_practice():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    data = request.get_json(silent=True) or {}
    doc_oid = parse_object_id(data.get("document_id"))
    if not doc_oid:
        return jsonify({"error": "Please select a valid uploaded document."}), 400

    db = get_db()
    doc = db.documents.find_one({"_id": doc_oid, "user_id": user_oid})
    if not doc:
        return jsonify({"error": "Document not found."}), 404

    source_text = (doc.get("extracted_text") or "").strip()
    if not source_text:
        return jsonify({"error": "Selected document has no extracted text to generate questions from."}), 400

    try:
        question_count = max(1, min(12, int(data.get("question_count", 5))))
    except (ValueError, TypeError):
        question_count = 5

    allowed_types = {"multiple_choice", "short_answer", "concept"}
    requested_types = data.get("question_types") or ["multiple_choice", "short_answer", "concept"]
    question_types = [qt for qt in requested_types if qt in allowed_types] or [
        "multiple_choice",
        "short_answer",
        "concept",
    ]
    difficulty = str(data.get("difficulty") or "mixed")
    if difficulty not in {"easy", "medium", "hard", "mixed"}:
        difficulty = "mixed"

    try:
        generated = _build_gemini().generate_practice(
            document_title=doc.get("filename", "Document"),
            text=source_text,
            question_count=question_count,
            question_types=question_types,
            difficulty=difficulty,
        )
    except AIServiceError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

    now = utc_now()
    practice_doc = {
        "user_id": user_oid,
        "document_id": doc_oid,
        "document_filename": doc.get("filename", ""),
        "title": generated["title"],
        "difficulty": difficulty,
        "questions": generated["questions"],
        "created_at": now,
    }
    inserted = db.practice_sets.insert_one(practice_doc)
    practice_doc["_id"] = inserted.inserted_id

    return jsonify({"practice_set": _serialize_practice_set(practice_doc)}), 201


@practice_bp.route("/practice/sets", methods=["GET"])
@jwt_required()
def list_practice_sets():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    db = get_db()
    sets = list(db.practice_sets.find({"user_id": user_oid}).sort("created_at", -1))
    return jsonify({"practice_sets": [_serialize_practice_set(s) for s in sets]}), 200


@practice_bp.route("/practice/sets/<set_id>", methods=["GET"])
@jwt_required()
def get_practice_set(set_id: str):
    user_oid = parse_object_id(get_jwt_identity())
    set_oid = parse_object_id(set_id)
    if not user_oid or not set_oid:
        return jsonify({"error": "Invalid practice set ID."}), 400

    db = get_db()
    ps = db.practice_sets.find_one({"_id": set_oid, "user_id": user_oid})
    if not ps:
        return jsonify({"error": "Practice set not found."}), 404

    return jsonify({"practice_set": _serialize_practice_set(ps)}), 200


@practice_bp.route("/practice/submit", methods=["POST"])
@jwt_required()
def submit_practice():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    data = request.get_json(silent=True) or {}
    set_oid = parse_object_id(data.get("practice_set_id"))
    answers = data.get("answers") or {}
    if not set_oid or not isinstance(answers, dict):
        return jsonify({"error": "Valid practice_set_id and answers map are required."}), 400

    db = get_db()
    ps = db.practice_sets.find_one({"_id": set_oid, "user_id": user_oid})
    if not ps:
        return jsonify({"error": "Practice set not found."}), 404

    questions = ps.get("questions", [])
    open_items = []
    for q in questions:
        qid = q["id"]
        user_ans = str(answers.get(qid, "")).strip()
        if q.get("question_type") != "multiple_choice" and user_ans:
            open_items.append(
                {
                    "id": qid,
                    "question": q.get("question_text", ""),
                    "expected_answer": q.get("correct_answer", ""),
                    "student_answer": user_ans,
                }
            )

    ai_eval = {}
    if open_items and current_app.config.get("GEMINI_API_KEY"):
        try:
            ai_eval = _build_gemini().evaluate_open_answers(open_items)
        except AIServiceError:
            ai_eval = {}

    results = []
    correct_count = 0
    for q in questions:
        qid = q["id"]
        user_ans = str(answers.get(qid, "")).strip()
        expected = str(q.get("correct_answer", "")).strip()

        if q.get("question_type") == "multiple_choice":
            is_correct = bool(user_ans) and user_ans.lower() == expected.lower()
            feedback = (
                "Correct!"
                if is_correct
                else f"The correct option is: {expected}."
            )
        elif qid in ai_eval:
            is_correct = ai_eval[qid]["is_correct"]
            feedback = ai_eval[qid]["feedback"]
        else:
            # Deterministic keyword overlap fallback if open answer was empty or Gemini eval unavailable
            if not user_ans:
                is_correct = False
                feedback = "No answer provided."
            else:
                expected_tokens = {w.lower() for w in expected.split() if len(w) > 3}
                user_tokens = {w.lower() for w in user_ans.split() if len(w) > 3}
                overlap = len(expected_tokens & user_tokens)
                threshold = max(1, len(expected_tokens) // 3) if expected_tokens else 1
                is_correct = overlap >= threshold or user_ans.lower() in expected.lower()
                feedback = (
                    "Your answer covers key points from the expected response."
                    if is_correct
                    else "Compare your answer with the model answer and explanation below."
                )

        if is_correct:
            correct_count += 1

        results.append(
            {
                "id": qid,
                "question_type": q.get("question_type"),
                "difficulty": q.get("difficulty"),
                "question_text": q.get("question_text"),
                "user_answer": user_ans,
                "correct_answer": expected,
                "is_correct": is_correct,
                "feedback": feedback,
                "explanation": q.get("explanation", ""),
            }
        )

    total = len(questions)
    score_percent = round((correct_count / total) * 100) if total > 0 else 0

    now = utc_now()
    attempt_doc = {
        "user_id": user_oid,
        "practice_set_id": set_oid,
        "document_id": ps["document_id"],
        "document_filename": ps.get("document_filename", ""),
        "title": ps.get("title", ""),
        "total_questions": total,
        "correct_count": correct_count,
        "score_percent": score_percent,
        "results": results,
        "created_at": now,
    }
    inserted = db.practice_attempts.insert_one(attempt_doc)
    attempt_doc["_id"] = inserted.inserted_id

    return jsonify({"attempt": _serialize_attempt(attempt_doc)}), 201


@practice_bp.route("/practice/attempts", methods=["GET"])
@jwt_required()
def list_attempts():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    db = get_db()
    attempts = list(
        db.practice_attempts.find({"user_id": user_oid}).sort("created_at", -1)
    )
    return jsonify({"attempts": [_serialize_attempt(a) for a in attempts]}), 200


@practice_bp.route("/progress", methods=["GET"])
@jwt_required()
def get_progress():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    db = get_db()
    doc_count = db.documents.count_documents({"user_id": user_oid})
    simplified_count = db.documents.count_documents(
        {"user_id": user_oid, "latest_simplification": {"$ne": None}}
    )
    transcript_count = db.transcripts.count_documents({"user_id": user_oid})
    attempts = list(
        db.practice_attempts.find({"user_id": user_oid}).sort("created_at", -1)
    )
    recent_docs = list(
        db.documents.find({"user_id": user_oid}).sort("created_at", -1).limit(5)
    )
    latest_plan = db.revision_plans.find_one(
        {"user_id": user_oid}, sort=[("created_at", -1)]
    )

    total_attempts = len(attempts)
    avg_score = (
        round(sum(a.get("score_percent", 0) for a in attempts) / total_attempts)
        if total_attempts > 0
        else 0
    )

    serialized_plan = None
    if latest_plan:
        serialized_plan = {
            "id": str(latest_plan["_id"]),
            "plan_title": latest_plan.get("plan_title", ""),
            "summary": latest_plan.get("summary", ""),
            "focus_areas": latest_plan.get("focus_areas", []),
            "daily_steps": latest_plan.get("daily_steps", []),
            "accessibility_tips": latest_plan.get("accessibility_tips", []),
            "created_at": to_iso(latest_plan.get("created_at")),
        }

    return (
        jsonify(
            {
                "stats": {
                    "documents_uploaded": doc_count,
                    "documents_simplified": simplified_count,
                    "transcripts_saved": transcript_count,
                    "practice_attempts": total_attempts,
                    "average_score": avg_score,
                },
                "recent_documents": [
                    {
                        "id": str(d["_id"]),
                        "filename": d.get("filename", ""),
                        "status": d.get("status", "ready"),
                        "word_count": d.get("word_count", 0),
                        "has_simplification": bool(d.get("latest_simplification")),
                        "created_at": to_iso(d.get("created_at")),
                    }
                    for d in recent_docs
                ],
                "recent_attempts": [_serialize_attempt(a) for a in attempts[:5]],
                "latest_revision_plan": serialized_plan,
            }
        ),
        200,
    )
