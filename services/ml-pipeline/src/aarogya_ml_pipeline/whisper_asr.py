"""Whisper INT8 offline ASR backend for Aarogya Mesh Tier-2 PHC Hub."""

from __future__ import annotations

import logging
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from aarogya_ml_pipeline.interfaces import (
    StubVoiceTranscriber,
    TranscriptionResult,
)

logger = logging.getLogger(__name__)

ENV_WHISPER_MODEL_PATH = "AAROGYA_WHISPER_MODEL_PATH"
ENV_WHISPER_MODEL_SIZE = "AAROGYA_WHISPER_MODEL_SIZE"
DEFAULT_MODEL_SIZE = "tiny"
FALLBACK_BACKEND = "stub-asr-fallback"
DEFAULT_BACKEND = "whisper-int8-cpu"


class WhisperVoiceTranscriber:
    """Offline CPU-only INT8 Whisper ASR adapter conforming to VoiceTranscriber protocol.

    Executes quantized Whisper speech-to-text without network dependencies or GPU bloat.
    Gracefully falls back to StubVoiceTranscriber if faster-whisper/weights are absent.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        model_size: str | None = None,
        *,
        device: str = "cpu",
        compute_type: str = "int8",
        cpu_threads: int = 4,
        num_workers: int = 1,
        local_files_only: bool = True,
        backend: str = DEFAULT_BACKEND,
        model: Any = None,
    ) -> None:
        if not local_files_only:
            raise ValueError("local_files_only must be True to enforce offline edge execution")

        env_path = os.environ.get(ENV_WHISPER_MODEL_PATH)
        self.model_path = str(model_path) if model_path is not None else (env_path or None)
        self.model_size = model_size or os.environ.get(ENV_WHISPER_MODEL_SIZE, DEFAULT_MODEL_SIZE)
        self.device = device
        self.compute_type = compute_type
        self.cpu_threads = cpu_threads
        self.num_workers = num_workers
        self.local_files_only = local_files_only
        self.backend = backend
        self._fallback = StubVoiceTranscriber()

        if model is not None:
            self._model = model
        else:
            self._model = None
            self._load_model()

    @property
    def is_model_loaded(self) -> bool:
        """Return True if local ASR model weights are loaded and ready."""
        return self._model is not None

    def _load_model(self) -> None:
        """Attempt to load faster-whisper or pywhispercpp offline."""

        # Check path existence if path was explicitly specified
        if self.model_path:
            p = Path(self.model_path)
            if not p.exists():
                logger.debug("Whisper model path does not exist: %s", self.model_path)
                self._model = None
                return

        model_source = self.model_path or self.model_size

        # Try faster-whisper first
        try:
            from faster_whisper import WhisperModel

            self._model = WhisperModel(
                model_size_or_path=str(model_source),
                device=self.device,
                compute_type=self.compute_type,
                cpu_threads=self.cpu_threads,
                num_workers=self.num_workers,
                local_files_only=self.local_files_only,
            )
            return
        except ImportError:
            logger.debug("faster-whisper not installed")
        except Exception as exc:
            logger.debug("faster-whisper model load failed: %s", exc)

        # Try pywhispercpp as alternative if available
        try:
            from pywhispercpp.model import Model as PyWhisperModel

            if self.model_path and Path(self.model_path).is_file():
                self._model = PyWhisperModel(
                    self.model_path,
                    n_threads=self.cpu_threads,
                )
                return
        except ImportError:
            logger.debug("pywhispercpp not installed")
        except Exception as exc:
            logger.debug("pywhispercpp model load failed: %s", exc)

        self._model = None

    def _fallback_result(self, audio_bytes: bytes, language_hint: str) -> TranscriptionResult:
        """Return deterministic fallback result annotating stub-asr-fallback."""
        stub_res = self._fallback.transcribe(audio_bytes, language_hint=language_hint)
        return TranscriptionResult(
            transcript=stub_res.transcript,
            language=stub_res.language,
            confidence=stub_res.confidence,
            backend=FALLBACK_BACKEND,
        )

    def _calculate_confidence(self, segments: list[Any], info: Any = None) -> float:
        """Aggregate and clamp segment confidence into 0.0 .. 1.0 range."""
        if not segments:
            if info is not None and hasattr(info, "transcription_confidence"):
                return max(0.0, min(1.0, float(info.transcription_confidence)))
            return 0.90

        confidences: list[float] = []
        for s in segments:
            if hasattr(s, "confidence") and s.confidence is not None:
                confidences.append(float(s.confidence))
            elif hasattr(s, "avg_logprob") and s.avg_logprob is not None:
                # Clamp logprob to avoid overflow/underflow, then exp
                prob = math.exp(max(min(float(s.avg_logprob), 0.0), -20.0))
                confidences.append(prob)
            elif hasattr(s, "no_speech_prob") and s.no_speech_prob is not None:
                confidences.append(1.0 - float(s.no_speech_prob))

        if not confidences:
            raw_conf = 0.90
        else:
            raw_conf = sum(confidences) / len(confidences)

        # Strict clamping to [0.0, 1.0]
        clamped = max(0.0, min(1.0, float(raw_conf)))
        return round(clamped, 4)

    def transcribe(self, audio_bytes: bytes, language_hint: str = "hi") -> TranscriptionResult:
        """Transcribe raw audio bytes into structured TranscriptionResult.

        Writes audio to a temporary file, transcribes via local CPU INT8 engine,
        aggregates segments, and guarantees tempfile cleanup in finally.
        Falls back cleanly to StubVoiceTranscriber if offline model is unavailable.
        """
        # Empty or missing audio falls back cleanly
        if not audio_bytes or not audio_bytes.strip():
            return self._fallback_result(audio_bytes, language_hint)

        # Fallback if engine is missing or weights absent
        if self._model is None:
            return self._fallback_result(audio_bytes, language_hint)

        # Detect suffix from container magic header
        suffix = ".audio"
        if audio_bytes.startswith(b"RIFF"):
            suffix = ".wav"
        elif audio_bytes.startswith(b"OggS"):
            suffix = ".ogg"
        elif audio_bytes.startswith(b"\x1a\x45\xdf\xa3"):
            suffix = ".webm"

        tmp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp.flush()
                tmp_path = Path(tmp.name)

            # Transcribe audio file
            res = self._model.transcribe(str(tmp_path), language=language_hint)
            if isinstance(res, tuple) and len(res) == 2:
                segments_gen, info = res
                segments = list(segments_gen)
            else:
                segments = list(res)
                info = None

            texts: list[str] = []
            for s in segments:
                text_val = getattr(s, "text", None)
                if text_val and isinstance(text_val, str):
                    clean = text_val.strip()
                    if clean:
                        texts.append(clean)

            combined_text = " ".join(texts).strip()
            if not combined_text:
                return self._fallback_result(audio_bytes, language_hint)

            confidence = self._calculate_confidence(segments, info)

            lang = language_hint
            if info is not None and getattr(info, "language", None):
                detected = str(info.language).strip()
                if 2 <= len(detected) <= 16:
                    lang = detected

            return TranscriptionResult(
                transcript=combined_text,
                language=lang,
                confidence=confidence,
                backend=self.backend,
            )

        except Exception as exc:
            logger.warning("Local whisper transcription failed: %s; falling back", exc)
            return self._fallback_result(audio_bytes, language_hint)
        finally:
            if tmp_path is not None:
                try:
                    if tmp_path.exists():
                        tmp_path.unlink()
                except OSError:
                    pass
