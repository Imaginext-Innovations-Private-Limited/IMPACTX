"""Local filesystem audio/binary blob store for Tier-2 PHC Hub voice notes.

Keeps raw audio bytes (WebM/Opus/OGG/WAV) out of the lightweight CRDT event log
while allowing Tier-0/Tier-1 nodes to upload blobs referenced by
``VOICE_NOTE_RECORDED.payload["audio_blob_key"]`` and Tier-2 ML workers
(``VoiceTranscriber``) to read them deterministically offline.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

_BLOB_KEY_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
DEFAULT_MAX_BLOB_BYTES = 25 * 1024 * 1024  # 25 MiB cap per voice clip


class BlobMetadata(BaseModel):
    """Metadata returned by PUT /api/v1/blobs/{blob_key} and stored alongside raw bytes."""

    model_config = ConfigDict(extra="forbid")

    blob_key: str = Field(..., min_length=1, max_length=128)
    content_type: str = Field(default="application/octet-stream", min_length=1, max_length=128)
    size_bytes: int = Field(..., ge=1)
    sha256: str = Field(..., min_length=64, max_length=64)


class LocalBlobStore:
    """Path-traversal-safe, idempotent local disk store for synced audio blobs."""

    def __init__(self, root_dir: str | Path, *, max_bytes: int = DEFAULT_MAX_BLOB_BYTES) -> None:
        self.root_dir = Path(root_dir)
        self.max_bytes = max_bytes
        self.root_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def validate_key(blob_key: str) -> str:
        """Ensure blob_key is a safe flat identifier with no path traversal."""
        if not _BLOB_KEY_RE.fullmatch(blob_key) or ".." in blob_key:
            raise ValueError(
                "Invalid blob_key: must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ without '..'."
            )
        return blob_key

    def _paths(self, blob_key: str) -> tuple[Path, Path]:
        safe_key = self.validate_key(blob_key)
        return (
            self.root_dir / f"{safe_key}.blob",
            self.root_dir / f"{safe_key}.meta.json",
        )

    def put(
        self,
        blob_key: str,
        data: bytes,
        *,
        content_type: str = "application/octet-stream",
    ) -> BlobMetadata:
        """Atomically store blob bytes and metadata (idempotent for identical keys)."""
        blob_path, meta_path = self._paths(blob_key)
        if not data:
            raise ValueError("Blob payload cannot be empty.")
        if len(data) > self.max_bytes:
            raise ValueError(f"Blob exceeds maximum allowed size of {self.max_bytes} bytes.")

        clean_ct = (content_type or "application/octet-stream").split(";")[0].strip()
        if not clean_ct:
            clean_ct = "application/octet-stream"

        digest = hashlib.sha256(data).hexdigest()
        meta = BlobMetadata(
            blob_key=blob_key,
            content_type=clean_ct,
            size_bytes=len(data),
            sha256=digest,
        )

        tmp_blob = blob_path.with_suffix(".blob.tmp")
        tmp_meta = meta_path.with_suffix(".meta.json.tmp")
        tmp_blob.write_bytes(data)
        os.replace(tmp_blob, blob_path)
        tmp_meta.write_text(meta.model_dump_json(indent=2), encoding="utf-8")
        os.replace(tmp_meta, meta_path)
        return meta

    def exists(self, blob_key: str) -> bool:
        """Return True if the blob exists on disk."""
        blob_path, _ = self._paths(blob_key)
        return blob_path.is_file()

    def get(self, blob_key: str) -> tuple[bytes, BlobMetadata] | None:
        """Return (raw_bytes, metadata) or None if not found."""
        blob_path, meta_path = self._paths(blob_key)
        if not blob_path.is_file():
            return None
        data = blob_path.read_bytes()
        if meta_path.is_file():
            meta = BlobMetadata.model_validate(json.loads(meta_path.read_text(encoding="utf-8")))
        else:
            meta = BlobMetadata(
                blob_key=blob_key,
                content_type="application/octet-stream",
                size_bytes=len(data),
                sha256=hashlib.sha256(data).hexdigest(),
            )
        return data, meta
