"""
Page-Aware Document Chunker for Sahaaya AI RAG Pipeline.
Splits extracted document pages into coherent passages with character overlap.
Maintains exact page numbering, section headings, and scheme identifiers.
"""

import re
from typing import Dict, Any, List, Optional


class DocumentChunker:
    """
    Splits page-level extracted text into bounded chunks with character overlap.
    Preserves page numbers and metadata for accurate legal citations.
    """

    def __init__(
        self,
        chunk_size: int = 900,
        chunk_overlap: int = 120,
    ):
        if chunk_size <= chunk_overlap:
            raise ValueError("chunk_size must be strictly greater than chunk_overlap.")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(
        self,
        doc_metadata: Dict[str, Any],
        extracted_pages: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Produce page-aware chunks for a single document.
        Never merges pages from different documents.
        """
        doc_id = doc_metadata.get("doc_id", "doc")
        scheme_slug = doc_metadata.get("scheme_slug", "")
        document_title = doc_metadata.get("document_title", "Official Document")
        official_source_url = doc_metadata.get("official_source_url", "")
        verification_status = doc_metadata.get("verification_status", "Unverified")

        all_chunks: List[Dict[str, Any]] = []
        global_chunk_idx = 0

        for page_data in extracted_pages:
            page_num = page_data.get("page_number", 1)
            page_text = page_data.get("text", "").strip()

            if not page_text:
                continue

            # Split page text into chunks
            page_chunks = self._chunk_page_text(
                page_text=page_text,
                page_number=page_num,
                doc_id=doc_id,
                scheme_slug=scheme_slug,
                document_title=document_title,
                official_source_url=official_source_url,
                verification_status=verification_status,
                start_index=global_chunk_idx,
            )

            all_chunks.extend(page_chunks)
            global_chunk_idx += len(page_chunks)

        return all_chunks

    def _chunk_page_text(
        self,
        page_text: str,
        page_number: int,
        doc_id: str,
        scheme_slug: str,
        document_title: str,
        official_source_url: str,
        verification_status: str,
        start_index: int,
    ) -> List[Dict[str, Any]]:
        """Split a single page's text into overlapping segments."""
        chunks: List[Dict[str, Any]] = []

        # If page text is within chunk size, keep it as a single coherent chunk
        if len(page_text) <= self.chunk_size:
            heading = self._detect_section_heading(page_text)
            chunk_id = f"{doc_id}_p{page_number}_c{start_index}"
            return [{
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "scheme_slug": scheme_slug,
                "document_title": document_title,
                "page_number": page_number,
                "chunk_index": start_index,
                "content": page_text,
                "char_count": len(page_text),
                "section_heading": heading,
                "official_source_url": official_source_url,
                "verification_status": verification_status,
            }]

        # Segment page into overlapping chunks
        start_pos = 0
        local_idx = 0
        text_len = len(page_text)

        while start_pos < text_len:
            end_pos = min(start_pos + self.chunk_size, text_len)

            # Try to break at a paragraph or sentence boundary if not at end of text
            if end_pos < text_len:
                boundary = self._find_natural_break(page_text, start_pos, end_pos)
                if boundary > start_pos + (self.chunk_size // 2):
                    end_pos = boundary

            chunk_text = page_text[start_pos:end_pos].strip()

            if chunk_text:
                heading = self._detect_section_heading(chunk_text)
                chunk_id = f"{doc_id}_p{page_number}_c{start_index + local_idx}"

                chunks.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "scheme_slug": scheme_slug,
                    "document_title": document_title,
                    "page_number": page_number,
                    "chunk_index": start_index + local_idx,
                    "content": chunk_text,
                    "char_count": len(chunk_text),
                    "section_heading": heading,
                    "official_source_url": official_source_url,
                    "verification_status": verification_status,
                })
                local_idx += 1

            # Advance with overlap
            if end_pos >= text_len:
                break
            start_pos = end_pos - self.chunk_overlap

        return chunks

    @staticmethod
    def _find_natural_break(text: str, start: int, end: int) -> int:
        """Find the nearest paragraph break (\n\n) or sentence period (.) before end."""
        sub = text[start:end]

        # Check for paragraph break in the last 200 characters of window
        last_para = sub.rfind("\n\n")
        if last_para != -1 and (end - (start + last_para)) < 250:
            return start + last_para + 2

        # Check for single newline in the last 150 characters
        last_nl = sub.rfind("\n")
        if last_nl != -1 and (end - (start + last_nl)) < 150:
            return start + last_nl + 1

        # Check for period followed by space
        last_dot = sub.rfind(". ")
        if last_dot != -1 and (end - (start + last_dot)) < 150:
            return start + last_dot + 2

        return end

    @staticmethod
    def _detect_section_heading(text: str) -> Optional[str]:
        """Detect if the chunk begins with an apparent section heading or title."""
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        if not lines:
            return None

        first_line = lines[0]
        # Check if first line looks like a heading (short, title-cased, numbered, or uppercase)
        if len(first_line) <= 80 and (
            first_line.isupper()
            or re.match(r"^(?:Section|Chapter|Rule|Clause|\d+[\.\)])", first_line, re.IGNORECASE)
            or (first_line.istitle() and len(first_line.split()) <= 8)
        ):
            return first_line

        return None
