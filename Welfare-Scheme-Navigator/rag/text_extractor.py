"""
PDF Text Extractor for Sahaaya AI RAG Pipeline.
Extracts text page-by-page using PyPDF while preserving page numbers and metadata.
Handles scanned PDFs gracefully by flagging when OCR is required.
"""

import re
import logging
from pathlib import Path
from typing import Dict, Any, List
import pypdf

logger = logging.getLogger("text_extractor")


class TextExtractor:
    """
    Extracts text and page-level metadata from official government PDF files.
    """

    @classmethod
    def extract_from_pdf(cls, file_path: Path) -> Dict[str, Any]:
        """
        Extract text from a PDF file page-by-page.
        Returns structured extraction dictionary.
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            reader = pypdf.PdfReader(str(file_path))
        except Exception as e:
            raise ValueError(f"Failed to parse PDF file '{file_path.name}': {str(e)}")

        page_count = len(reader.pages)
        if page_count == 0:
            return {
                "file_name": file_path.name,
                "page_count": 0,
                "pages": [],
                "total_characters": 0,
                "ocr_required": False,
                "extraction_status": "empty_document",
                "message": "The PDF document contains 0 pages.",
            }

        extracted_pages: List[Dict[str, Any]] = []
        total_chars = 0

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            try:
                raw_text = page.extract_text() or ""
            except Exception as pe:
                logger.warning(f"Error extracting text from page {page_num} of {file_path.name}: {pe}")
                raw_text = ""

            cleaned_text = cls._clean_text(raw_text)
            char_count = len(cleaned_text)
            total_chars += char_count

            extracted_pages.append({
                "page_number": page_num,
                "text": cleaned_text,
                "char_count": char_count,
            })

        # Check if the document appears to be a scanned image PDF
        # If total characters across all pages is under 20 chars per page on average
        average_chars_per_page = total_chars / max(1, page_count)
        is_scanned = total_chars < 50 or average_chars_per_page < 20

        if is_scanned:
            return {
                "file_name": file_path.name,
                "page_count": page_count,
                "pages": extracted_pages,
                "total_characters": total_chars,
                "ocr_required": True,
                "extraction_status": "ocr_required",
                "message": (
                    f"Document '{file_path.name}' contains little or no extractable text "
                    f"({total_chars} total characters across {page_count} pages). "
                    "This appears to be a scanned image PDF. Optical Character Recognition (OCR) "
                    "is required to extract readable text."
                ),
            }

        return {
            "file_name": file_path.name,
            "page_count": page_count,
            "pages": extracted_pages,
            "total_characters": total_chars,
            "ocr_required": False,
            "extraction_status": "success",
            "message": f"Successfully extracted {total_chars} characters across {page_count} page(s).",
        }

    @staticmethod
    def _clean_text(text: str) -> str:
        """Normalize whitespace and remove unprintable characters."""
        if not text:
            return ""
        # Replace non-breaking spaces with standard space
        text = text.replace("\u00a0", " ").replace("\ufeff", "")
        # Normalize carriage returns
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        # Replace multiple spaces with single space
        text = re.sub(r"[ \t]+", " ", text)
        # Replace more than 2 consecutive newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()
