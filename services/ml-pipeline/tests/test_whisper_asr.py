"""Unit tests for WhisperVoiceTranscriber (T4-01 Whisper INT8 Offline ASR Backend)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from aarogya_ml_pipeline.interfaces import (
    TranscriptionResult,
    VoiceTranscriber,
)
from aarogya_ml_pipeline.whisper_asr import (
    DEFAULT_BACKEND,
    ENV_WHISPER_MODEL_PATH,
    ENV_WHISPER_MODEL_SIZE,
    FALLBACK_BACKEND,
    WhisperVoiceTranscriber,
)


class DummySegment:
    """Mock faster-whisper segment."""

    def __init__(
        self,
        text: str,
        avg_logprob: float | None = -0.15,
        confidence: float | None = None,
        no_speech_prob: float | None = 0.02,
    ) -> None:
        self.text = text
        self.avg_logprob = avg_logprob
        self.confidence = confidence
        self.no_speech_prob = no_speech_prob


class DummyInfo:
    """Mock faster-whisper transcription info."""

    def __init__(self, language: str = "hi", language_probability: float = 0.98) -> None:
        self.language = language
        self.language_probability = language_probability


def test_protocol_conformance() -> None:
    """WhisperVoiceTranscriber must conform to runtime-checkable VoiceTranscriber."""
    transcriber = WhisperVoiceTranscriber()
    assert isinstance(transcriber, VoiceTranscriber)


def test_missing_weights_fallback() -> None:
    """Missing model weights or missing faster-whisper must fall back to stub-asr-fallback."""
    transcriber = WhisperVoiceTranscriber(model_path="/tmp/nonexistent_model_weights_path")
    assert transcriber.is_model_loaded is False

    result = transcriber.transcribe(b"patient has high fever", language_hint="hi")
    assert isinstance(result, TranscriptionResult)
    assert result.backend == FALLBACK_BACKEND
    assert result.language == "hi"
    assert "patient has high fever" in result.transcript
    assert 0.0 <= result.confidence <= 1.0


def test_empty_audio_bytes_fallback() -> None:
    """Empty or whitespace-only audio bytes must fall back cleanly without error."""
    transcriber = WhisperVoiceTranscriber()
    result_empty = transcriber.transcribe(b"", language_hint="en")
    assert result_empty.backend == FALLBACK_BACKEND
    assert result_empty.language == "en"
    assert len(result_empty.transcript) > 0

    result_spaces = transcriber.transcribe(b"   ", language_hint="hi")
    assert result_spaces.backend == FALLBACK_BACKEND
    assert result_spaces.language == "hi"


def test_offline_local_files_only_enforcement() -> None:
    """Instantiating with local_files_only=False must raise ValueError for offline safety."""
    with pytest.raises(ValueError, match="local_files_only"):
        WhisperVoiceTranscriber(local_files_only=False)

    # When faster_whisper is initialized, local_files_only=True must be passed
    mock_model_cls = MagicMock()
    with patch.dict("sys.modules", {"faster_whisper": MagicMock(WhisperModel=mock_model_cls)}):
        transcriber = WhisperVoiceTranscriber(model_size="tiny")
        assert transcriber.local_files_only is True
        mock_model_cls.assert_called_once()
        _, kwargs = mock_model_cls.call_args
        assert kwargs.get("local_files_only") is True
        assert kwargs.get("device") == "cpu"
        assert kwargs.get("compute_type") == "int8"


def test_env_var_configuration(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Model path and size must be read from environment variables when not passed."""
    dummy_model_dir = tmp_path / "whisper_model"
    dummy_model_dir.mkdir()

    monkeypatch.setenv(ENV_WHISPER_MODEL_PATH, str(dummy_model_dir))
    monkeypatch.setenv(ENV_WHISPER_MODEL_SIZE, "small")

    mock_model_cls = MagicMock()
    with patch.dict("sys.modules", {"faster_whisper": MagicMock(WhisperModel=mock_model_cls)}):
        transcriber = WhisperVoiceTranscriber()
        assert transcriber.model_path == str(dummy_model_dir)
        assert transcriber.model_size == "small"
        mock_model_cls.assert_called_once()
        assert mock_model_cls.call_args[1]["model_size_or_path"] == str(dummy_model_dir)


def test_mocked_segment_aggregation() -> None:
    """Multiple segments must be joined cleanly into transcript with language preserved."""
    segments = [
        DummySegment(text="रोगी को दो दिन से", avg_logprob=-0.10),
        DummySegment(text="तीव्र ज्वर और श्वास कष्ट है", avg_logprob=-0.05),
    ]
    info = DummyInfo(language="hi")

    mock_model = MagicMock()
    mock_model.transcribe.return_value = (iter(segments), info)

    transcriber = WhisperVoiceTranscriber(model=mock_model)
    assert transcriber.is_model_loaded is True

    audio_bytes = b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00"  # mock wav header
    result = transcriber.transcribe(audio_bytes, language_hint="hi")

    assert result.transcript == "रोगी को दो दिन से तीव्र ज्वर और श्वास कष्ट है"
    assert result.language == "hi"
    assert result.backend == DEFAULT_BACKEND
    assert 0.0 <= result.confidence <= 1.0


def test_confidence_clamping() -> None:
    """Confidence must be strictly clamped to [0.0, 1.0] across various segment outputs."""
    mock_model = MagicMock()
    transcriber = WhisperVoiceTranscriber(model=mock_model)

    # 1. Over-confidence (> 1.0) must clamp to 1.0
    mock_model.transcribe.return_value = (
        iter([DummySegment(text="High confidence test", confidence=1.8)]),
        DummyInfo(),
    )
    res_high = transcriber.transcribe(b"RIFFdummydata", language_hint="en")
    assert res_high.confidence == 1.0

    # 2. Negative confidence (< 0.0) must clamp to 0.0
    mock_model.transcribe.return_value = (
        iter([DummySegment(text="Negative confidence test", confidence=-0.5)]),
        DummyInfo(),
    )
    res_neg = transcriber.transcribe(b"RIFFdummydata", language_hint="en")
    assert res_neg.confidence == 0.0

    # 3. Logprob 0.0 -> probability 1.0
    mock_model.transcribe.return_value = (
        iter([DummySegment(text="Zero logprob test", avg_logprob=0.0)]),
        DummyInfo(),
    )
    res_zero_logp = transcriber.transcribe(b"RIFFdummydata", language_hint="en")
    assert res_zero_logp.confidence == 1.0

    # 4. Extreme negative logprob -> probability near 0.0, never negative
    mock_model.transcribe.return_value = (
        iter([DummySegment(text="Very low logprob test", avg_logprob=-999.0)]),
        DummyInfo(),
    )
    res_low_logp = transcriber.transcribe(b"RIFFdummydata", language_hint="en")
    assert 0.0 <= res_low_logp.confidence <= 0.01


def test_temp_file_cleanup_on_success_and_error() -> None:
    """Temporary audio file must be unlinked in finally on both success and exception."""
    recorded_paths: list[str] = []

    def mock_transcribe_success(file_path: str, **kwargs: object) -> tuple[list[DummySegment], DummyInfo]:
        recorded_paths.append(file_path)
        assert os.path.exists(file_path)
        return [DummySegment(text="Success text", avg_logprob=-0.1)], DummyInfo()

    mock_model = MagicMock()
    mock_model.transcribe.side_effect = mock_transcribe_success

    transcriber = WhisperVoiceTranscriber(model=mock_model)
    transcriber.transcribe(b"RIFFtestaudio", language_hint="hi")

    assert len(recorded_paths) == 1
    assert not os.path.exists(recorded_paths[0]), "Temp file was not cleaned up on success"

    def mock_transcribe_failure(file_path: str, **kwargs: object) -> None:
        recorded_paths.append(file_path)
        assert os.path.exists(file_path)
        raise RuntimeError("Decoder crashed")

    mock_model.transcribe.side_effect = mock_transcribe_failure
    result = transcriber.transcribe(b"RIFFtestaudio", language_hint="hi")

    # Should fall back cleanly without raising
    assert result.backend == FALLBACK_BACKEND
    assert len(recorded_paths) == 2
    assert not os.path.exists(recorded_paths[1]), "Temp file was not cleaned up on error"


def test_zero_bloat_no_torch_imports() -> None:
    """WhisperVoiceTranscriber module must strictly avoid importing heavy bloat libraries."""
    import aarogya_ml_pipeline.whisper_asr as whisper_mod

    forbidden_modules = ["torch", "torchvision", "torchaudio", "tensorflow", "nvidia"]
    for forbidden in forbidden_modules:
        assert forbidden not in whisper_mod.__dict__, f"Forbidden module {forbidden} found in module dict"


def test_binary_webm_and_empty_audio_never_fabricate_symptoms() -> None:
    """Binary WebM/WAV/OGG or empty audio in fallback mode must not fabricate fever/cough."""
    transcriber = WhisperVoiceTranscriber(model_path="/tmp/nonexistent_model_weights_path")
    assert transcriber.is_model_loaded is False

    samples = [
        b"\x1a\x45\xdf\xa3\x9f\x42\x86\x81\x01\x42\xf7\x81\x01webm-binary-payload",
        b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x00\xff\xfe",
        b"OggS\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00opus-binary",
        b"",
        b"   ",
    ]
    for sample in samples:
        res = transcriber.transcribe(sample, language_hint="en")
        assert res.backend == FALLBACK_BACKEND
        assert res.transcript.startswith(f"[stub-audio-{len(sample.strip()) if not sample.strip() else len(sample)}-bytes]")
        assert res.confidence == 0.0
        lowered = res.transcript.lower()
        assert "fever" not in lowered
        assert "cough" not in lowered
