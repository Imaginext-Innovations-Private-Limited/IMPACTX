"""
RAG Search and Ingestion API Blueprint for Sahaaya AI.
Exposes full-text keyword retrieval, document catalog, and safe ingestion endpoints over REST.
"""

from pathlib import Path
from flask import Blueprint, request, jsonify
from rag.document_loader import DocumentLoader
from rag.text_extractor import TextExtractor
from rag.chunker import DocumentChunker
from rag.indexer import RAGIndexer
from rag.retriever import DocumentRetriever

rag_bp = Blueprint("rag_api", __name__)


@rag_bp.route("/rag/search", methods=["POST"])
def search_scheme_documents():
    """
    Search official document passages using SQLite FTS5 BM25 retrieval.
    Payload:
    {
        "query": "Gruha Lakshmi ration card requirements",
        "scheme_slug": "gruha-lakshmi",  (optional)
        "top_k": 5                       (optional, default 5)
    }
    """
    if not request.is_json:
        return jsonify({
            "error": "Bad Request",
            "message": "Request payload must be valid JSON.",
            "status_code": 400
        }), 400

    payload = request.get_json() or {}
    query = payload.get("query")
    scheme_slug = payload.get("scheme_slug")
    top_k = payload.get("top_k", 5)

    if query is None or not isinstance(query, str) or not query.strip():
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'query' is required and must be a non-empty string.",
            "status_code": 400
        }), 400

    try:
        top_k = int(top_k)
    except (ValueError, TypeError):
        top_k = 5

    retriever = DocumentRetriever()
    results = retriever.search(query=query, scheme_slug=scheme_slug, top_k=top_k)

    return jsonify({
        "success": True,
        "data": results
    }), 200


@rag_bp.route("/rag/documents", methods=["GET"])
def list_indexed_documents():
    """List all official documents currently indexed in the RAG pipeline."""
    indexer = RAGIndexer()
    docs = indexer.list_indexed_documents()
    total_chunks = indexer.count_indexed_chunks()

    return jsonify({
        "success": True,
        "data": {
            "total_documents": len(docs),
            "total_chunks_indexed": total_chunks,
            "documents": docs,
            "system_description": "SQLite FTS5 BM25 keyword-based retrieval engine",
        }
    }), 200


@rag_bp.route("/rag/ingest", methods=["POST"])
def ingest_document():
    """
    Ingest a PDF from data/raw_documents into the RAG index.
    Security guard: Strictly prohibits arbitrary filesystem paths.
    Payload:
    {
        "filename": "gruha_lakshmi_guidelines.pdf",
        "metadata": {
            "document_title": "Official Gruha Lakshmi Guidelines",
            "scheme_slug": "gruha-lakshmi",
            "department": "Women & Child Development Dept",
            "government_level": "State",
            "official_source_url": "https://sevasindhu.karnataka.gov.in/",
            "publication_date": "2023-06-15",
            "verification_status": "Verified"
        }
    }
    """
    if not request.is_json:
        return jsonify({
            "error": "Bad Request",
            "message": "Request payload must be valid JSON.",
            "status_code": 400
        }), 400

    payload = request.get_json() or {}
    filename = payload.get("filename")
    meta = payload.get("metadata", {})

    if not filename or not isinstance(filename, str):
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'filename' is required.",
            "status_code": 400
        }), 400

    if not isinstance(meta, dict):
        return jsonify({
            "error": "Bad Request",
            "message": "Field 'metadata' must be a dictionary.",
            "status_code": 400
        }), 400

    # 1. Enforce strict filesystem boundary check
    try:
        safe_path = DocumentLoader.validate_safe_path(filename)
    except PermissionError as pe:
        return jsonify({
            "error": "Forbidden",
            "message": str(pe),
            "status_code": 403
        }), 403
    except (FileNotFoundError, ValueError) as ve:
        return jsonify({
            "error": "Not Found",
            "message": str(ve),
            "status_code": 404
        }), 404

    # 2. Calculate file hash
    file_hash = DocumentLoader.calculate_file_hash(safe_path)

    # 3. Extract text page-by-page
    try:
        extraction = TextExtractor.extract_from_pdf(safe_path)
    except Exception as ee:
        return jsonify({
            "error": "Extraction Error",
            "message": f"Failed to extract text from PDF: {str(ee)}",
            "status_code": 500
        }), 500

    # Check for scanned image PDF requiring OCR
    if extraction.get("ocr_required"):
        return jsonify({
            "error": "OCR Required",
            "message": extraction.get("message"),
            "status_code": 422,
            "extraction_details": extraction
        }), 422

    # 4. Prepare metadata
    doc_id = meta.get("doc_id") or f"doc_{file_hash[:12]}"
    doc_metadata = {
        "doc_id": doc_id,
        "document_title": meta.get("document_title", safe_path.stem.replace("_", " ").title()),
        "scheme_slug": meta.get("scheme_slug", ""),
        "department": meta.get("department", "Government Department"),
        "government_level": meta.get("government_level", "State"),
        "official_source_url": meta.get("official_source_url", ""),
        "publication_date": meta.get("publication_date"),
        "retrieval_date": meta.get("retrieval_date"),
        "verification_status": meta.get("verification_status", "Unverified"),
        "file_hash": file_hash,
        "file_name": safe_path.name,
        "page_count": extraction.get("page_count", 0),
    }

    # 5. Chunk pages
    chunker = DocumentChunker(chunk_size=900, chunk_overlap=120)
    chunks = chunker.chunk_document(doc_metadata, extraction.get("pages", []))

    # 6. Index into SQLite FTS5
    indexer = RAGIndexer()
    index_result = indexer.index_document(doc_metadata, chunks)

    return jsonify({
        "success": True,
        "data": {
            "message": f"Document '{doc_metadata['document_title']}' indexed successfully.",
            "doc_id": doc_id,
            "file_name": safe_path.name,
            "file_hash": file_hash,
            "pages_processed": doc_metadata["page_count"],
            "chunks_indexed": len(chunks),
            "verification_status": doc_metadata["verification_status"],
            "index_action": index_result.get("action"),
        }
    }), 200
