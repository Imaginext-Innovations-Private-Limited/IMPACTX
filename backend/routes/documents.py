from flask import Blueprint, current_app, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from werkzeug.utils import secure_filename

from extensions import get_db
from services.pdf_service import PDFValidationError, extract_pdf_text, validate_pdf_upload
from utils.serializers import parse_object_id, serialize_document, utc_now

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")


@documents_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_document():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    if "file" not in request.files:
        return jsonify({"error": "No PDF file was included in the request."}), 400

    file = request.files["file"]
    raw_filename = (file.filename or "").strip()
    safe_name = secure_filename(raw_filename) or raw_filename
    file_bytes = file.read()
    max_mb = current_app.config.get("MAX_PDF_SIZE_MB", 15)

    try:
        validate_pdf_upload(
            filename=raw_filename,
            file_bytes=file_bytes,
            content_type=file.mimetype or "",
            max_size_mb=max_mb,
        )
        extraction = extract_pdf_text(file_bytes)
    except PDFValidationError as exc:
        return jsonify({"error": str(exc)}), 400

    db = get_db()
    now = utc_now()
    doc_record = {
        "user_id": user_oid,
        "filename": raw_filename if raw_filename.lower().endswith(".pdf") else safe_name,
        "file_size": len(file_bytes),
        "page_count": extraction.page_count,
        "word_count": extraction.word_count,
        "status": extraction.status,
        "ocr_recommended": extraction.ocr_recommended,
        "extraction_method": extraction.extraction_method,
        "status_message": extraction.status_message,
        "extracted_text": extraction.extracted_text,
        "pages": extraction.pages,
        "latest_simplification": None,
        "created_at": now,
        "updated_at": now,
    }
    inserted = db.documents.insert_one(doc_record)
    doc_record["_id"] = inserted.inserted_id

    return (
        jsonify(
            {
                "message": extraction.status_message,
                "document": serialize_document(doc_record, include_text=True),
            }
        ),
        201,
    )


@documents_bp.route("", methods=["GET"])
@jwt_required()
def list_documents():
    user_oid = parse_object_id(get_jwt_identity())
    if not user_oid:
        return jsonify({"error": "Invalid user identity."}), 401

    db = get_db()
    docs = list(db.documents.find({"user_id": user_oid}).sort("created_at", -1))
    return (
        jsonify(
            {
                "documents": [serialize_document(doc, include_text=False) for doc in docs],
            }
        ),
        200,
    )


@documents_bp.route("/<doc_id>", methods=["GET"])
@jwt_required()
def get_document(doc_id: str):
    user_oid = parse_object_id(get_jwt_identity())
    doc_oid = parse_object_id(doc_id)
    if not user_oid or not doc_oid:
        return jsonify({"error": "Invalid document ID."}), 400

    db = get_db()
    doc = db.documents.find_one({"_id": doc_oid, "user_id": user_oid})
    if not doc:
        return jsonify({"error": "Document not found."}), 404

    return jsonify({"document": serialize_document(doc, include_text=True)}), 200


@documents_bp.route("/<doc_id>", methods=["DELETE"])
@jwt_required()
def delete_document(doc_id: str):
    user_oid = parse_object_id(get_jwt_identity())
    doc_oid = parse_object_id(doc_id)
    if not user_oid or not doc_oid:
        return jsonify({"error": "Invalid document ID."}), 400

    db = get_db()
    result = db.documents.delete_one({"_id": doc_oid, "user_id": user_oid})
    if result.deleted_count == 0:
        return jsonify({"error": "Document not found."}), 404

    db.simplifications.delete_many({"document_id": doc_oid, "user_id": user_oid})
    db.practice_sets.delete_many({"document_id": doc_oid, "user_id": user_oid})

    return jsonify({"message": "Document deleted successfully."}), 200
