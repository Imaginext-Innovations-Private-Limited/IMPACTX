"""Contract-locked ML pipeline protocols and deterministic stubs.

Teammate C implements real CPU/NPU-optimized backends (`faster-whisper` /
`whisper.cpp` INT8, `llama.cpp` Qwen2.5-3B GBNF, `LightGBM` + `SHAP`, and
EWMA outbreak detection) behind these protocols while preserving the Clinical
Safety Invariant: local ML never owns raw triage or overrides deterministic
danger-sign rules in `aarogya_clinical_engine`.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from aarogya_contracts import (
    ActionCard,
    ActionCardPriority,
    CrdtEvent,
    EnrichmentState,
    EventType,
    HlcTimestamp,
    NodeTier,
    TriageSeverity,
)


class TranscriptionResult(BaseModel):
    """Structured output from Indic/English local ASR."""

    model_config = ConfigDict(extra="forbid")

    transcript: str = Field(..., min_length=1)
    language: str = Field(default="hi", min_length=2, max_length=16)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    backend: str = Field(default="stub-asr", min_length=1, max_length=64)


class StructuredClinicalNote(BaseModel):
    """GBNF-constrained clinical extraction fed into deterministic rules.

    Note: The SLM extracts candidate symptom flags and concise summaries only;
    it never outputs a final `TriageSeverity` directly.
    """

    model_config = ConfigDict(extra="forbid")

    extracted_symptoms: list[str] = Field(default_factory=list)
    candidate_danger_flags: list[str] = Field(default_factory=list)
    recommended_follow_up: str = Field(..., min_length=1, max_length=500)
    language: str = Field(default="hi", min_length=2, max_length=16)
    backend: str = Field(default="stub-slm-gbnf", min_length=1, max_length=64)


class RiskScoreResult(BaseModel):
    """Tabular risk estimation with local SHAP feature attributions."""

    model_config = ConfigDict(extra="forbid")

    risk_score: float = Field(..., ge=0.0, le=1.0)
    risk_band: Literal["LOW", "MODERATE", "HIGH"]
    shap_attributions: dict[str, float] = Field(default_factory=dict)
    backend: str = Field(default="stub-lightgbm-shap", min_length=1, max_length=64)


class OutbreakSignal(BaseModel):
    """EWMA spatiotemporal syndrome anomaly detection result."""

    model_config = ConfigDict(extra="forbid")

    village_id: str = Field(..., min_length=1, max_length=128)
    syndrome: str = Field(..., min_length=1, max_length=128)
    alert_triggered: bool
    ewma_value: float = Field(..., ge=0.0)
    baseline_mean: float = Field(..., ge=0.0)
    threshold: float = Field(..., ge=0.0)
    severity: TriageSeverity = TriageSeverity.YELLOW_PHC
    rationale: str = Field(..., min_length=1, max_length=500)


@runtime_checkable
class VoiceTranscriber(Protocol):
    """Protocol for offline speech-to-text (e.g. faster-whisper / whisper.cpp INT8)."""

    def transcribe(self, audio_bytes: bytes, language_hint: str = "hi") -> TranscriptionResult:
        """Transcribe raw PCM/WAV/OGG audio bytes without network access."""


@runtime_checkable
class ClinicalSlmStructurer(Protocol):
    """Protocol for GBNF-constrained local SLM symptom extraction."""

    def structure_note(self, transcript: str, language: str = "hi") -> StructuredClinicalNote:
        """Extract structured clinical signals from a voice-note transcript."""


@runtime_checkable
class RiskScorer(Protocol):
    """Protocol for tabular risk scoring with SHAP attribution (e.g. LightGBM)."""

    def score_risk(self, features: dict[str, float | int | bool]) -> RiskScoreResult:
        """Compute patient risk score and per-feature SHAP contributions."""


@runtime_checkable
class OutbreakDetector(Protocol):
    """Protocol for village-level EWMA syndrome spike detection."""

    def detect_outbreak(
        self,
        village_id: str,
        syndrome: str,
        daily_counts: list[int],
    ) -> OutbreakSignal:
        """Evaluate daily case counts for an anomalous EWMA surge."""


_BINARY_AUDIO_MAGIC_PREFIXES: tuple[bytes, ...] = (
    b"\x1a\x45\xdf\xa3",  # WebM / Matroska
    b"RIFF",  # WAV
    b"OggS",  # OGG / Opus
    b"fLaC",  # FLAC
    b"ID3",  # MP3 with ID3 tag
    b"\xff\xfb",  # MP3 frame sync
)


class StubVoiceTranscriber:
    """Deterministic fallback ASR used when Whisper weights are not present."""

    def transcribe(self, audio_bytes: bytes, language_hint: str = "hi") -> TranscriptionResult:
        if not audio_bytes or not audio_bytes.strip():
            return TranscriptionResult(
                transcript="[stub-audio-0-bytes] No audio or transcript provided.",
                language=language_hint,
                confidence=0.0,
                backend="stub-asr-deterministic",
            )

        is_binary = any(audio_bytes.startswith(prefix) for prefix in _BINARY_AUDIO_MAGIC_PREFIXES)
        if not is_binary:
            try:
                decoded = audio_bytes.decode("utf-8").strip()
            except UnicodeDecodeError:
                decoded = ""
            if decoded and all(ch.isprintable() or ch in "\n\r\t" for ch in decoded):
                return TranscriptionResult(
                    transcript=decoded,
                    language=language_hint,
                    confidence=0.95,
                    backend="stub-asr-deterministic",
                )

        return TranscriptionResult(
            transcript=(
                f"[stub-audio-{len(audio_bytes)}-bytes] "
                "Audio recorded; local Whisper ASR model not loaded."
            ),
            language=language_hint,
            confidence=0.0,
            backend="stub-asr-deterministic",
        )


class StubClinicalSlmStructurer:
    """Deterministic keyword-based fallback for GBNF SLM extraction."""

    _KEYWORD_MAP: dict[str, str] = {
        "fever": "fever",
        "ज्वर": "fever",
        "cough": "cough",
        "fast breathing": "fast_breathing",
        "breathing": "fast_breathing",
        "श्वास": "fast_breathing",
        "convulsion": "convulsions",
        "seizure": "convulsions",
        "lethargic": "lethargy",
        "bleeding": "vaginal_bleeding",
    }

    _DANGER_FLAGS = frozenset({"convulsions", "lethargy", "vaginal_bleeding"})

    def structure_note(self, transcript: str, language: str = "hi") -> StructuredClinicalNote:
        lowered = transcript.lower()
        symptoms: list[str] = []
        danger_flags: list[str] = []

        for phrase, code in self._KEYWORD_MAP.items():
            if phrase in lowered and code not in symptoms:
                symptoms.append(code)
                if code in self._DANGER_FLAGS and code not in danger_flags:
                    danger_flags.append(code)

        if not symptoms:
            symptoms.append("general_checkup")

        follow_up = (
            "Immediate deterministic danger-sign triage required."
            if danger_flags
            else "Review structured symptoms in deterministic IMNCI/ASHA engine."
        )
        return StructuredClinicalNote(
            extracted_symptoms=symptoms,
            candidate_danger_flags=danger_flags,
            recommended_follow_up=follow_up,
            language=language,
            backend="stub-slm-deterministic",
        )


class StubRiskScorer:
    """Deterministic linear risk scorer standing in for LightGBM + SHAP."""

    _WEIGHTS: dict[str, float] = {
        "fever_days": 0.08,
        "respiratory_rate": 0.01,
        "has_danger_sign": 0.45,
        "age_under_2m": 0.20,
        "high_bp": 0.25,
        "temp_excess": 0.09,
        "hypothermia_deficit": 0.25,
        "hypoxia_deficit": 0.05,
        "tachypnea_excess": 0.015,
        "anemia_deficit": 0.06,
        "malnutrition_deficit": 0.14,
        "young_infant_thermal_risk": 0.30,
        "gestational_preeclampsia_risk": 0.32,
        "cardiorespiratory_distress": 0.28,
        "severe_anemia_flag": 0.30,
        "sam_malnutrition_flag": 0.30,
    }

    def score_risk(self, features: dict[str, float | int | bool]) -> RiskScoreResult:
        attributions: dict[str, float] = {}
        raw = 0.05
        for key, value in sorted(features.items()):
            numeric = float(value) if isinstance(value, (int, float, bool)) else 0.0
            weight = self._WEIGHTS.get(key, 0.02)
            contrib = round(min(max(numeric * weight, 0.0), 0.5), 4)
            attributions[key] = contrib
            raw += contrib

        score = round(min(max(raw, 0.0), 1.0), 4)
        if score >= 0.7:
            band: Literal["LOW", "MODERATE", "HIGH"] = "HIGH"
        elif score >= 0.35:
            band = "MODERATE"
        else:
            band = "LOW"

        return RiskScoreResult(
            risk_score=score,
            risk_band=band,
            shap_attributions=attributions,
            backend="stub-lightgbm-shap",
        )


class StubOutbreakDetector:
    """Pure-Python EWMA spike detector with zero heavy numeric dependencies."""

    def __init__(self, alpha: float = 0.35, spike_multiplier: float = 2.0) -> None:
        self._alpha = alpha
        self._spike_multiplier = spike_multiplier

    def detect_outbreak(
        self,
        village_id: str,
        syndrome: str,
        daily_counts: list[int],
    ) -> OutbreakSignal:
        if not daily_counts:
            return OutbreakSignal(
                village_id=village_id,
                syndrome=syndrome,
                alert_triggered=False,
                ewma_value=0.0,
                baseline_mean=0.0,
                threshold=1.0,
                rationale="Insufficient daily counts for EWMA outbreak evaluation.",
            )

        ewma = float(daily_counts[0])
        for count in daily_counts[1:]:
            ewma = self._alpha * float(count) + (1.0 - self._alpha) * ewma

        baseline = sum(daily_counts[:-1]) / max(len(daily_counts) - 1, 1)
        threshold = max(baseline * self._spike_multiplier, 3.0)
        triggered = ewma >= threshold and daily_counts[-1] >= 3

        return OutbreakSignal(
            village_id=village_id,
            syndrome=syndrome,
            alert_triggered=triggered,
            ewma_value=round(ewma, 3),
            baseline_mean=round(baseline, 3),
            threshold=round(threshold, 3),
            severity=TriageSeverity.RED_EMERGENCY if triggered else TriageSeverity.YELLOW_PHC,
            rationale=(
                f"EWMA {ewma:.2f} exceeded threshold {threshold:.2f} for {syndrome} in {village_id}."
                if triggered
                else f"EWMA {ewma:.2f} remains within baseline threshold {threshold:.2f}."
            ),
        )


def enrich_voice_note_event(
    voice_event: CrdtEvent,
    hub_node_id: str,
    hlc: HlcTimestamp,
    *,
    transcriber: VoiceTranscriber | None = None,
    structurer: ClinicalSlmStructurer | None = None,
    risk_scorer: RiskScorer | None = None,
) -> list[CrdtEvent]:
    """Run Tier-2 deferred ML enrichment for a `VOICE_NOTE_RECORDED` event.

    Emits contract-valid `ENRICHMENT_COMPLETED` (referencing `voice_event.event_id`)
    and `ACTION_CARD_ISSUED` events ready to append to the Hub CRDT store.
    """
    if voice_event.event_type != EventType.VOICE_NOTE_RECORDED:
        raise ValueError("enrich_voice_note_event requires a VOICE_NOTE_RECORDED event")

    asr = transcriber or StubVoiceTranscriber()
    slm = structurer or StubClinicalSlmStructurer()
    scorer = risk_scorer or StubRiskScorer()

    payload: dict[str, Any] = voice_event.payload
    language = str(payload.get("language", "hi"))
    transcript_hint = str(payload.get("transcript_hint", "")).strip()
    audio_b64_or_text = str(payload.get("audio_text", transcript_hint)).encode("utf-8")

    asr_result = asr.transcribe(audio_b64_or_text, language_hint=language)
    structured = slm.structure_note(asr_result.transcript, language=asr_result.language)
    risk = scorer.score_risk(
        {
            "has_danger_sign": 1 if structured.candidate_danger_flags else 0,
            "symptom_count": len(structured.extracted_symptoms),
        }
    )

    enrichment_event = CrdtEvent(
        event_id=str(uuid4()),
        hlc=hlc,
        origin_node_id=hub_node_id,
        patient_id=voice_event.patient_id,
        event_type=EventType.ENRICHMENT_COMPLETED,
        enrichment_state=EnrichmentState.COMPLETED,
        ref_event_id=voice_event.event_id,
        payload={
            "transcription": asr_result.model_dump(mode="json"),
            "structured_note": structured.model_dump(mode="json"),
            "risk_score": risk.model_dump(mode="json"),
        },
    )

    next_hlc = HlcTimestamp(
        wall_ms=hlc.wall_ms,
        logical=hlc.logical + 1,
        node_id=hlc.node_id,
    )
    priority = (
        ActionCardPriority.CRITICAL
        if structured.candidate_danger_flags
        else ActionCardPriority.MEDIUM
    )
    card = ActionCard(
        patient_id=voice_event.patient_id,
        title="Voice Note Clinical Summary",
        summary=structured.recommended_follow_up,
        action_steps=[
            f"Observed symptoms: {', '.join(structured.extracted_symptoms)}",
            f"ML risk band: {risk.risk_band} ({risk.risk_score:.2f})",
        ],
        priority=priority,
        severity=TriageSeverity.RED_EMERGENCY if structured.candidate_danger_flags else None,
        target_tier=NodeTier.TIER_0_WATCH,
        source_event_id=enrichment_event.event_id,
        language=asr_result.language,
    )
    card_event = CrdtEvent(
        event_id=str(uuid4()),
        hlc=next_hlc,
        origin_node_id=hub_node_id,
        patient_id=voice_event.patient_id,
        event_type=EventType.ACTION_CARD_ISSUED,
        enrichment_state=EnrichmentState.COMPLETED,
        ref_event_id=voice_event.event_id,
        payload=card.model_dump(mode="json"),
    )
    return [enrichment_event, card_event]
