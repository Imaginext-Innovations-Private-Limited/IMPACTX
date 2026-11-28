"""
SQLite FTS5 Full-Text Indexer for Sahaaya AI RAG Pipeline.
Indexes document chunks and metadata using native SQLite FTS5 with BM25 ranking.
Provides update and removal capabilities while preventing duplicate indexing.
"""

import sqlite3
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from config import Config
from rag.citation import CitationBuilder

logger = logging.getLogger("rag_indexer")


class RAGIndexer:
    """
    Manages SQLite FTS5 full-text indexing for scheme guideline chunks and document metadata.
    Operates without native C++ binary dependencies (such as FAISS/Torch).
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            self.db_path = Config.DATA_DIR / "sahaaya.db"
        else:
            self.db_path = Path(db_path)

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Establish connection with SQLite enabling row factory."""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_schema(self):
        """Create metadata table and FTS5 full-text search table if they do not exist."""
        with self._get_connection() as conn:
            # 1. Metadata table for indexed documents
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rag_documents (
                    doc_id TEXT PRIMARY KEY,
                    document_title TEXT NOT NULL,
                    scheme_slug TEXT NOT NULL,
                    department TEXT,
                    government_level TEXT,
                    official_source_url TEXT,
                    publication_date TEXT,
                    retrieval_date TEXT,
                    verification_status TEXT DEFAULT 'Unverified',
                    file_hash TEXT UNIQUE,
                    file_name TEXT,
                    page_count INTEGER DEFAULT 0,
                    total_chunks INTEGER DEFAULT 0,
                    created_at TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_rag_doc_scheme ON rag_documents(scheme_slug)")

            # 2. Virtual FTS5 table for chunks
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS rag_chunks_fts USING fts5(
                    chunk_id UNINDEXED,
                    doc_id UNINDEXED,
                    scheme_slug UNINDEXED,
                    document_title UNINDEXED,
                    page_number UNINDEXED,
                    chunk_index UNINDEXED,
                    official_source_url UNINDEXED,
                    verification_status UNINDEXED,
                    content
                )
            """)
            conn.commit()

    def index_document(
        self,
        doc_metadata: Dict[str, Any],
        chunks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Index a document and its chunks.
        Idempotent: If file_hash or doc_id already exists, updates the document and replaces chunks.
        """
        doc_id = doc_metadata["doc_id"]
        file_hash = doc_metadata["file_hash"]
        title = doc_metadata.get("document_title", "Official Document")
        scheme_slug = doc_metadata.get("scheme_slug", "")
        dept = doc_metadata.get("department", "")
        gov_level = doc_metadata.get("government_level", "State")
        source_url = doc_metadata.get("official_source_url", "")
        pub_date = doc_metadata.get("publication_date")
        ret_date = doc_metadata.get("retrieval_date", datetime.now(timezone.utc).isoformat())
        raw_status = doc_metadata.get("verification_status", "unverified")
        ver_status = CitationBuilder.normalize_verification_status(raw_status)
        file_name = doc_metadata.get("file_name", "")
        page_count = doc_metadata.get("page_count", 0)
        total_chunks = len(chunks)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            # Check if document with same hash or doc_id already exists
            cursor = conn.execute(
                "SELECT doc_id FROM rag_documents WHERE file_hash = ? OR doc_id = ?",
                (file_hash, doc_id),
            )
            existing = cursor.fetchone()

            if existing:
                existing_doc_id = existing["doc_id"]
                logger.info(f"Document already indexed (doc_id={existing_doc_id}). Replacing chunks.")
                # Delete old chunks
                conn.execute("DELETE FROM rag_chunks_fts WHERE doc_id = ?", (existing_doc_id,))
                # Update document metadata
                conn.execute("""
                    UPDATE rag_documents SET
                        document_title = ?, scheme_slug = ?, department = ?, government_level = ?,
                        official_source_url = ?, publication_date = ?, retrieval_date = ?,
                        verification_status = ?, file_name = ?, page_count = ?, total_chunks = ?,
                        created_at = ?
                    WHERE doc_id = ?
                """, (
                    title, scheme_slug, dept, gov_level, source_url, pub_date, ret_date,
                    ver_status, file_name, page_count, total_chunks, now_iso, existing_doc_id
                ))
                target_doc_id = existing_doc_id
                action = "updated"
            else:
                # Insert new document metadata
                conn.execute("""
                    INSERT INTO rag_documents (
                        doc_id, document_title, scheme_slug, department, government_level,
                        official_source_url, publication_date, retrieval_date, verification_status,
                        file_hash, file_name, page_count, total_chunks, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    doc_id, title, scheme_slug, dept, gov_level, source_url, pub_date, ret_date,
                    ver_status, file_hash, file_name, page_count, total_chunks, now_iso
                ))
                target_doc_id = doc_id
                action = "inserted"

            # Insert chunks into FTS5 virtual table
            for chunk in chunks:
                conn.execute("""
                    INSERT INTO rag_chunks_fts (
                        chunk_id, doc_id, scheme_slug, document_title, page_number,
                        chunk_index, official_source_url, verification_status, content
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chunk["chunk_id"],
                    target_doc_id,
                    chunk["scheme_slug"],
                    chunk["document_title"],
                    chunk["page_number"],
                    chunk["chunk_index"],
                    chunk["official_source_url"],
                    ver_status,
                    chunk["content"],
                ))

            conn.commit()

        return {
            "action": action,
            "doc_id": target_doc_id,
            "document_title": title,
            "scheme_slug": scheme_slug,
            "page_count": page_count,
            "chunks_indexed": total_chunks,
            "verification_status": ver_status,
        }

    def remove_document(self, doc_id: str) -> bool:
        """Remove a document and its chunks from the index."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM rag_chunks_fts WHERE doc_id = ?", (doc_id,))
            cursor = conn.execute("DELETE FROM rag_documents WHERE doc_id = ?", (doc_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_index(self):
        """Clear all documents and chunks from the FTS5 index."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM rag_chunks_fts")
            conn.execute("DELETE FROM rag_documents")
            conn.commit()

    def list_indexed_documents(self) -> List[Dict[str, Any]]:
        """List all indexed documents with metadata."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT doc_id, document_title, scheme_slug, department, government_level,
                       official_source_url, publication_date, retrieval_date, verification_status,
                       file_hash, file_name, page_count, total_chunks, created_at
                FROM rag_documents
                ORDER BY created_at DESC
            """)
            return [dict(row) for row in cursor.fetchall()]

    def count_indexed_chunks(self) -> int:
        """Return total number of chunks in the FTS5 index."""
        with self._get_connection() as conn:
            cursor = conn.execute("SELECT count(*) as count FROM rag_chunks_fts")
            return cursor.fetchone()["count"]
