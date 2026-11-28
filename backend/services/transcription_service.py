from dataclasses import dataclass
from typing import List, Protocol
import requests


ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".mp4", ".mpeg"}


class TranscriptionServiceError(Exception):
    """Raised when audio validation fails or transcription backend is unavailable."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class TranscriptionResult:
    text: str
    segments: List[dict]
    provider: str


class AudioTranscriber(Protocol):
    """Modular protocol so local Whisper or cloud Whisper endpoints can be swapped cleanly."""

    def transcribe(self, filename: str, file_bytes: bytes, content_type: str) -> TranscriptionResult:
        ...


class WhisperCompatibleTranscriber:
    """Calls a configured OpenAI/Whisper-compatible HTTP transcription endpoint."""

    def __init__(self, api_url: str, api_key: str = "", model: str = "whisper-1"):
        self.api_url = (api_url or "").strip()
        self.api_key = (api_key or "").strip()
        self.model = (model or "whisper-1").strip()

    def is_configured(self) -> bool:
        return bool(self.api_url)

    def transcribe(self, filename: str, file_bytes: bytes, content_type: str) -> TranscriptionResult:
        if not self.is_configured():
            raise TranscriptionServiceError(
                "Uploaded audio transcription requires a configured Whisper-compatible service "
                "(set WHISPER_API_URL and WHISPER_API_KEY in backend/.env). "
                "For live microphone captions without a server Whisper endpoint, use the Live Microphone Captions mode in a supported browser.",
                status_code=501,
            )

        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        files = {
            "file": (filename, file_bytes, content_type or "application/octet-stream"),
        }
        data = {
            "model": self.model,
            "response_format": "verbose_json",
        }

        try:
            resp = requests.post(
                self.api_url,
                headers=headers,
                files=files,
                data=data,
                timeout=120,
            )
        except requests.RequestException as exc:
            raise TranscriptionServiceError(
                f"Could not reach the configured Whisper transcription service: {str(exc)}",
                status_code=502,
            ) from exc

        if resp.status_code >= 400:
            raise TranscriptionServiceError(
                f"Whisper transcription service returned HTTP {resp.status_code}: {resp.text[:300]}",
                status_code=502,
            )

        try:
            payload = resp.json()
        except ValueError:
            # Some custom Whisper servers return plain text
            return TranscriptionResult(
                text=resp.text.strip(),
                segments=[],
                provider="whisper-compatible",
            )

        segments = [
            {
                "start": seg.get("start"),
                "end": seg.get("end"),
                "text": str(seg.get("text", "")).strip(),
            }
            for seg in (payload.get("segments") or [])
        ]
        return TranscriptionResult(
            text=str(payload.get("text", "")).strip(),
            segments=segments,
            provider="whisper-compatible",
        )


def validate_audio_upload(filename: str, file_bytes: bytes, max_size_mb: int = 25) -> None:
    if not filename:
        raise TranscriptionServiceError("No audio filename provided.", status_code=400)
    lower = filename.lower()
    if not any(lower.endswith(ext) for ext in ALLOWED_AUDIO_EXTENSIONS):
        raise TranscriptionServiceError(
            f"Unsupported audio format. Supported formats: {', '.join(sorted(ALLOWED_AUDIO_EXTENSIONS))}.",
            status_code=400,
        )
    if not file_bytes:
        raise TranscriptionServiceError("The uploaded audio file is empty.", status_code=400)
    if len(file_bytes) > max_size_mb * 1024 * 1024:
        raise TranscriptionServiceError(
            f"Audio file exceeds the maximum allowed size of {max_size_mb} MB.",
            status_code=400,
        )
