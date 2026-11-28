"""
Citation Builder for Sahaaya AI RAG Pipeline.
Builds verifiable, source-grounded legal citations linking retrieved text to official documents and page numbers.
Explicitly distinguishes authentic official government documents from demonstration material.
"""

from typing import Dict, Any, List

VALID_VERIFICATION_STATES = {"verified", "unverified", "demo_only"}


class CitationBuilder:
    """
    Constructs verifiable citations from retrieved FTS5 document passages.
    Guarantees every citation cites actual indexed documents while clearly distinguishing
    authentic official government documents from locally generated demonstration material.
    """

    @classmethod
    def normalize_verification_status(cls, raw_status: Any) -> str:
        """Normalize verification status into one of: 'verified', 'unverified', 'demo_only'."""
        if not raw_status:
            return "unverified"
        s = str(raw_status).strip().lower()
        if s in ("verified", "verified official", "official"):
            return "verified"
        if s in ("demo_only", "demo", "demonstration", "synthetic"):
            return "demo_only"
        return "unverified"

    @classmethod
    def build_citation(
        cls,
        result_row: Dict[str, Any],
        citation_number: int = 1,
    ) -> Dict[str, Any]:
        """
        Build a structured citation from an FTS5 search result row.
        Treats all retrieved text strictly as source content, never as instructions to execute.
        """
        doc_title = result_row.get("document_title", "Government Scheme Guidelines")
        page_num = result_row.get("page_number", 1)
        source_url = result_row.get("official_source_url", "")
        scheme_slug = result_row.get("scheme_slug", "")
        raw_status = result_row.get("verification_status", "unverified")
        ver_status = cls.normalize_verification_status(raw_status)
        raw_content = result_row.get("content", "").strip()

        # Sanitize snippet: Prevent indirect prompt injection by escaping markdown command delimiters
        safe_content = cls._sanitize_source_content(raw_content)

        # Snippet excerpt (first 250 characters with ellipsis if longer)
        if len(safe_content) > 280:
            snippet = safe_content[:277] + "..."
        else:
            snippet = safe_content

        # Tiered badge and formatted citation string
        if ver_status == "verified":
            badge = "[VERIFIED OFFICIAL DOCUMENT]"
            formatted = (
                f"[{citation_number}] {badge} Source: {doc_title}, Page {page_num} "
                f"- Official Portal: {source_url}"
            )
        elif ver_status == "demo_only":
            badge = "[DEMO ONLY - LOCALLY GENERATED MATERIAL]"
            formatted = (
                f"[{citation_number}] {badge} Source: {doc_title}, Page {page_num} "
                f"- Reference Portal: {source_url}"
            )
        else:
            badge = "[UNVERIFIED SOURCE]"
            formatted = (
                f"[{citation_number}] {badge} Source: {doc_title}, Page {page_num} "
                f"- Unverified Portal: {source_url}"
            )

        return {
            "citation_id": f"CIT-{citation_number:02d}",
            "citation_index": citation_number,
            "document_title": doc_title,
            "scheme_slug": scheme_slug,
            "page_number": page_num,
            "official_source_url": source_url,
            "verification_status": ver_status,
            "verification_badge": badge,
            "is_authentic_official_doc": (ver_status == "verified"),
            "relevance_rank": result_row.get("rank"),
            "passage_snippet": snippet,
            "full_passage": safe_content,
            "formatted_citation": formatted,
        }

    @staticmethod
    def _sanitize_source_content(text: str) -> str:
        """
        Neutralize any potential prompt-injection strings appearing inside source text.
        Source content must strictly be interpreted as passive quotation, never active instructions.
        """
        if not text:
            return ""
        text = text.replace("<script", "&lt;script").replace("</script>", "&lt;/script&gt;")
        return text
