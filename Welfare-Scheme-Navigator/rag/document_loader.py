"""
Document Loader for Sahaaya AI RAG Pipeline.
Safely discovers and loads official government PDF documents from data/raw_documents.
Strictly prevents path traversal and calculates file hashes for duplicate detection.
"""

import os
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from config import Config

APPROVED_DOCS_DIR = (Config.DATA_DIR / "raw_documents").resolve()


class DocumentLoader:
    """
    Safely loads and validates official PDF documents from approved project directory.
    Enforces strict filesystem boundary checking to prevent unauthorized file access.
    """

    @staticmethod
    def get_approved_directory() -> Path:
        """Return the absolute approved raw documents directory."""
        APPROVED_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        return APPROVED_DOCS_DIR

    @classmethod
    def validate_safe_path(cls, file_path_or_name: str) -> Path:
        """
        Validate that the requested file resides strictly within data/raw_documents.
        Raises ValueError if path traversal or access outside approved directory is attempted.
        """
        approved_dir = cls.get_approved_directory()
        candidate = Path(file_path_or_name)

        if not candidate.is_absolute():
            candidate = (approved_dir / candidate).resolve()
        else:
            candidate = candidate.resolve()

        # Strict boundary check: candidate must be a subpath of approved_dir
        try:
            candidate.relative_to(approved_dir)
        except ValueError:
            raise PermissionError(
                f"Security Violation: Access to path '{file_path_or_name}' outside approved "
                f"document directory '{approved_dir}' is strictly prohibited."
            )

        if not candidate.exists():
            raise FileNotFoundError(f"Document file does not exist: {candidate.name}")

        if not candidate.is_file():
            raise ValueError(f"Target path is not a file: {candidate.name}")

        if candidate.suffix.lower() != ".pdf":
            raise ValueError(f"Unsupported file format '{candidate.suffix}'. Only .pdf is supported.")

        return candidate

    @staticmethod
    def calculate_file_hash(file_path: Path) -> str:
        """Calculate SHA-256 hash of a file for duplicate identification."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @classmethod
    def list_available_documents(cls) -> List[Dict[str, Any]]:
        """List all valid PDF documents in the approved document directory."""
        approved_dir = cls.get_approved_directory()
        results = []

        for item in approved_dir.glob("*.pdf"):
            if item.is_file():
                f_hash = cls.calculate_file_hash(item)
                stat = item.stat()
                results.append({
                    "filename": item.name,
                    "file_path": str(item),
                    "file_size_bytes": stat.st_size,
                    "file_hash": f_hash,
                    "modified_at": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                })

        return results
