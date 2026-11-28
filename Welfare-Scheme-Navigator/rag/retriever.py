"""
Document Passage Retriever for Sahaaya AI RAG Pipeline.
Queries SQLite FTS5 virtual table with BM25 ranking and builds verifiable citations.
Accurately operates as keyword-based full-text retrieval, not vector search.
"""

import re
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from config import Config
from rag.citation import CitationBuilder

logger = logging.getLogger("rag_retriever")

# Common English stop words that shouldn't dominate search
STOP_WORDS = {
    "a", "an", "the", "and", "or", "of", "to", "in", "is", "for", "on", "at", "by", "with"
}


class DocumentRetriever:
    """
    Retrieves grounded passages from indexed official scheme documents using SQLite FTS5 BM25.
    Guarantees strict attribution and explicit handling of insufficient evidence.
    """

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            self.db_path = Config.DATA_DIR / "sahaaya.db"
        else:
            self.db_path = Path(db_path)

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def search(
        self,
        query: str,
        scheme_slug: Optional[str] = None,
        top_k: int = 5,
    ) -> Dict[str, Any]:
        """
        Execute full-text search against indexed document chunks.
        Optionally filter by scheme_slug.
        """
        top_k = max(1, min(20, top_k))  # Clamp between 1 and 20

        # Handle empty or whitespace queries
        if not query or not query.strip():
            return {
                "query": query,
                "scheme_filter": scheme_slug,
                "total_results": 0,
                "query_status": "empty_query",
                "message": "Query string is empty. Please provide search keywords.",
                "citations": [],
                "system_description": "SQLite FTS5 BM25 keyword-based retrieval engine",
            }

        fts_query = self._sanitize_fts_query(query)
        if not fts_query:
            return {
                "query": query,
                "scheme_filter": scheme_slug,
                "total_results": 0,
                "query_status": "insufficient_evidence",
                "message": (
                    "No meaningful search terms found in query. "
                    "Sahaaya AI does not fabricate unverified scheme information."
                ),
                "citations": [],
                "system_description": "SQLite FTS5 BM25 keyword-based retrieval engine",
            }

        # Check if FTS5 table exists
        try:
            with self._get_connection() as conn:
                if scheme_slug and scheme_slug.strip():
                    sql = """
                        SELECT chunk_id, doc_id, scheme_slug, document_title, page_number,
                               chunk_index, official_source_url, verification_status, content,
                               bm25(rag_chunks_fts) as rank
                        FROM rag_chunks_fts
                        WHERE rag_chunks_fts MATCH ? AND scheme_slug = ?
                        ORDER BY rank ASC
                        LIMIT ?
                    """
                    params = (fts_query, scheme_slug.strip().lower(), top_k)
                else:
                    sql = """
                        SELECT chunk_id, doc_id, scheme_slug, document_title, page_number,
                               chunk_index, official_source_url, verification_status, content,
                               bm25(rag_chunks_fts) as rank
                        FROM rag_chunks_fts
                        WHERE rag_chunks_fts MATCH ?
                        ORDER BY rank ASC
                        LIMIT ?
                    """
                    params = (fts_query, top_k)

                cursor = conn.execute(sql, params)
                rows = cursor.fetchall()
        except sqlite3.OperationalError as e:
            # Table might not exist yet or query syntax error
            logger.warning(f"FTS5 Query error: {e}")
            return {
                "query": query,
                "scheme_filter": scheme_slug,
                "total_results": 0,
                "query_status": "insufficient_evidence",
                "message": "The document index is currently empty or unavailable.",
                "citations": [],
                "system_description": "SQLite FTS5 BM25 keyword-based retrieval engine",
            }

        # If no results found, return explicit insufficient-evidence response
        if not rows:
            return {
                "query": query,
                "scheme_filter": scheme_slug,
                "total_results": 0,
                "query_status": "insufficient_evidence",
                "message": (
                    f"No reliable official source passage was found matching '{query}' "
                    f"{f'for scheme {scheme_slug}' if scheme_slug else ''} in the verified document index. "
                    "Sahaaya AI does not invent or fabricate unverified scheme facts."
                ),
                "citations": [],
                "system_description": "SQLite FTS5 BM25 keyword-based retrieval engine",
            }

        # Build citations
        citations = []
        for idx, row in enumerate(rows, start=1):
            citation = CitationBuilder.build_citation(dict(row), citation_number=idx)
            citations.append(citation)

        return {
            "query": query,
            "scheme_filter": scheme_slug,
            "total_results": len(citations),
            "query_status": "success",
            "message": f"Retrieved {len(citations)} official document passage(s) matching your query.",
            "citations": citations,
            "system_description": "SQLite FTS5 BM25 keyword-based retrieval engine",
        }

    @staticmethod
    def _sanitize_fts_query(query: str) -> Optional[str]:
        """
        Safely sanitize query into FTS5-compatible search expression.
        Extracts alphanumeric keywords, strips special FTS characters, and joins with OR.
        """
        # Extract word tokens (allowing letters, digits, and underscores)
        tokens = re.findall(r"\b[a-zA-Z0-9_\u0900-\u0D7F]+\b", query)

        # Filter out common stop words if we have enough substantive tokens
        substantive = [t for t in tokens if t.lower() not in STOP_WORDS]
        chosen_tokens = substantive if substantive else tokens

        if not chosen_tokens:
            return None

        # Build quoted terms connected by OR for broad keyword matching
        # e.g., "gruha" OR "lakshmi" OR "ration"
        fts_terms = [f'"{token}"' for token in chosen_tokens]
        return " OR ".join(fts_terms)
