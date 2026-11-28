from dataclasses import dataclass
from typing import List, Protocol
import fitz  # PyMuPDF


class PDFValidationError(Exception):
    """Raised when an uploaded file fails PDF validation."""


@dataclass
class ExtractedPDFResult:
    extracted_text: str
    pages: List[dict]
    page_count: int
    word_count: int
    status: str  # "ready" or "needs_ocr"
    ocr_recommended: bool
    extraction_method: str
    status_message: str


class TextExtractorProvider(Protocol):
    """Protocol allowing future OCR engines (e.g. Tesseract, Cloud Vision) to plug in."""

    name: str

    def extract(self, file_bytes: bytes) -> ExtractedPDFResult:
        ...


class PyMuPDFExtractor:
    """Primary PDF text extractor built on PyMuPDF with OCR-readiness metadata."""

    name = "pymupdf"

    def extract(self, file_bytes: bytes) -> ExtractedPDFResult:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as exc:
            raise PDFValidationError(
                "Unable to read this file as a valid PDF document."
            ) from exc

        try:
            if doc.is_encrypted:
                raise PDFValidationError(
                    "Password-protected or encrypted PDFs are not supported yet. Please upload an unlocked PDF."
                )

            page_count = len(doc)
            if page_count == 0:
                raise PDFValidationError("The uploaded PDF contains zero pages.")

            pages = []
            full_text_parts = []
            for idx, page in enumerate(doc, start=1):
                raw_text = page.get_text("text") or ""
                cleaned = "\n".join(
                    line.rstrip() for line in raw_text.splitlines()
                ).strip()
                pages.append({"page_number": idx, "text": cleaned})
                if cleaned:
                    full_text_parts.append(cleaned)

            extracted_text = "\n\n".join(full_text_parts).strip()
            word_count = len(extracted_text.split()) if extracted_text else 0

            # Detect scanned or image-only PDFs gracefully so OCR can be plugged in later
            if word_count == 0:
                return ExtractedPDFResult(
                    extracted_text="",
                    pages=pages,
                    page_count=page_count,
                    word_count=0,
                    status="needs_ocr",
                    ocr_recommended=True,
                    extraction_method=self.name,
                    status_message=(
                        "This PDF appears to be scanned or contains no selectable text. "
                        "OCR support is not yet enabled on this server; please upload a text-based PDF."
                    ),
                )

            return ExtractedPDFResult(
                extracted_text=extracted_text,
                pages=pages,
                page_count=page_count,
                word_count=word_count,
                status="ready",
                ocr_recommended=False,
                extraction_method=self.name,
                status_message="Text extracted successfully.",
            )
        finally:
            doc.close()


def validate_pdf_upload(
    filename: str,
    file_bytes: bytes,
    content_type: str = "",
    max_size_mb: int = 15,
) -> None:
    """Validate PDF filename, size, MIME hint, and magic bytes."""
    if not filename or not filename.lower().endswith(".pdf"):
        raise PDFValidationError("Only .pdf files are supported.")

    if not file_bytes:
        raise PDFValidationError("The uploaded file is empty.")

    max_bytes = max_size_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise PDFValidationError(
            f"PDF file exceeds the maximum allowed size of {max_size_mb} MB."
        )

    allowed_mimes = {"", "application/pdf", "application/x-pdf", "application/octet-stream"}
    if content_type and content_type.split(";")[0].strip().lower() not in allowed_mimes:
        raise PDFValidationError(
            f"Unsupported file type '{content_type}'. Please upload a valid PDF document."
        )

    # Check PDF signature header within the first 1024 bytes per PDF spec
    if b"%PDF-" not in file_bytes[:1024]:
        raise PDFValidationError(
            "Invalid PDF file signature. Please upload an authentic PDF document."
        )


def extract_pdf_text(
    file_bytes: bytes,
    extractor: TextExtractorProvider | None = None,
) -> ExtractedPDFResult:
    """Extract text using the configured extractor (PyMuPDF by default, extensible for OCR)."""
    active_extractor = extractor or PyMuPDFExtractor()
    return active_extractor.extract(file_bytes)
