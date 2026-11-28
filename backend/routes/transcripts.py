from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required

from extensions import get_db
from services.transcription_service import (
    TranscriptionServiceError,
    WhisperCompatibleTranscriber,
    validate_audio_upload,
)
from utils.serializers import parse_object_id, to_iso, utc_now

transcripts_bp = Blueprint("transcripts", __name__, url_prefix="/api/transcripts")


def _serialize_transcript(item: dict) -> dict:
    return {
        "id": str(item["_id"]),
        "title": item.get("title", "Untitled Transcript"),
        "source_type": item.get("source_type", "live_speech"),
        "provider": item.get("provider", "web_speech_api"),
        "audio_filename": item.get("audio_filename", ""),
        "text": item.get("text", ""),
        "segments": item.get("segments", []),
        "created_at": to_iso(item.get("created_at")),
        "updated_at": to_iso(item.get("updated_at")),
    }


@transcripts_bp.route("/capabilities", methods=["GET"])
@jwt_required()
def get_capabilities():
    whisper_configured = bool(current_app.config.get("WHISPER_API_URL"))
    return (
        jsonify(
            {
                "whisper_configured": whisper_configured,
                "max_audio_size_mb": current_app.config.get("MAX_AUDIO_SIZE_MB", 25),
            }
        ),
        200,
    )


@transcripts_bp.route("/transcribe", methods=["POST"])
@jwt_required()
def transcribe_audio_upload():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    if "file" not in request.files:
        return jsonify({"error": "No audio file was provided."}), 400

    file = request.files["file"]
    filename = (file.filename or "").strip()
    file_bytes = file.read()
    max_mb = current_app.config.get("MAX_AUDIO_SIZE_MB", 25)

    try:
        validate_audio_upload(filename, file_bytes, max_size_mb=max_mb)
        transcriber = WhisperCompatibleTranscriber(
            api_url=current_app.config.get("WHISPER_API_URL", ""),
            api_key=current_app.config.get("WHISPER_API_KEY", ""),
            model=current_app.config.get("WHISPER_MODEL", "whisper-1"),
        )
        result = transcriber.transcribe(
            filename=filename,
            file_bytes=file_bytes,
            content_type=file.mimetype or "application/octet-stream",
        )
    except TranscriptionServiceError as exc:
        return jsonify({"error": str(exc)}), exc.status_code

    title = (request.form.get("title") or "").strip() or filename
    now = utc_now()
    record = {
        "user_id": user_oid,
        "title": title,
        "source_type": "uploaded_audio",
        "provider": result.provider,
        "audio_filename": filename,
        "text": result.text,
        "segments": result.segments,
        "created_at": now,
        "updated_at": now,
    }
    inserted = get_db().transcripts.insert_one(record)
    record["_id"] = inserted.inserted_id

    return jsonify({"transcript": _serialize_transcript(record)}), 201


@transcripts_bp.route("", methods=["POST"])
@jwt_required()
def save_transcript():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    data = request.get_json(silent=True) or {}
    title = (data.get("title") or "").strip() or "Live Class Transcript"
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "Transcript text cannot be empty."}), 400

    now = utc_now()
    record = {
        "user_id": user_oid,
        "title": title,
        "source_type": str(data.get("source_type") or "live_speech"),
        "provider": str(data.get("provider") or "web_speech_api"),
        "audio_filename": str(data.get("audio_filename") or ""),
        "text": text,
        "segments": data.get("segments") or [],
        "created_at": now,
        "updated_at": now,
    }
    inserted = get_db().transcripts.insert_one(record)
    record["_id"] = inserted.inserted_id

    return jsonify({"transcript": _serialize_transcript(record)}), 201


@transcripts_bp.route("", methods=["GET"])
@jwt_required()
def list_transcripts():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    items = list(
        get_db().transcripts.find({"user_id": user_oid}).sort("created_at", -1)
    )
    return jsonify({"transcripts": [_serialize_transcript(t) for t in items]}), 200


@transcripts_bp.route("/<transcript_id>", methods=["PUT"])
@jwt_required()
def update_transcript(transcript_id: str):
    user_oid = parse_object_id(get_jwt_identity())
    t_oid = parse_object_id(transcript_id)
    if not user_oid or not t_oid:
        return jsonify({"error": "Invalid transcript ID."}), 400

    data = request.get_json(silent=True) or {}
    updates = {"updated_at": utc_now()}
    if "title" in data:
        title = (data.get("title") or "").strip()
        if not title:
            return jsonify({"error": "Title cannot be empty."}), 400
        updates["title"] = title
    if "text" in data:
        text = (data.get("text") or "").strip()
        if not text:
            return jsonify({"error": "Transcript text cannot be empty."}), 400
        updates["text"] = text

    updated = get_db().transcripts.find_one_and_update(
        {"_id": t_oid, "user_id": user_oid},
        {"$set": updates},
        return_document=True,
    )
    if not updated:
        return jsonify({"error": "Transcript not found."}), 404

    return jsonify({"transcript": _serialize_transcript(updated)}), 200


@transcripts_bp.route("/<transcript_id>", methods=["DELETE"])
@jwt_required()
def delete_transcript(transcript_id: str):
    user_oid = parse_object_id(get_jwt_identity())
    t_oid = parse_object_id(transcript_id)
    if not user_oid or not t_oid:
        return jsonify({"error": "Invalid transcript ID."}), 400

    res = get_db().transcripts.delete_one({"_id": t_oid, "user_id": user_oid})
    if res.deleted_count == 0:
        return jsonify({"error": "Transcript not found."}), 404

    return jsonify({"message": "Transcript deleted."}), 200
