"""Deferred ML enrichment orchestrator for Aarogya Mesh Tier-2 PHC Hub.

Composes ASR transcription, GBNF SLM clinical note structuring, deterministic
WHO IMNCI / NHM ASHA triage evaluation (the hard Clinical Safety Floor),
LightGBM + TreeSHAP risk scoring, and EWMA spatiotemporal outbreak detection.
Emits contract-valid CRDT events (ENRICHMENT_COMPLETED, ACTION_CARD_ISSUED,
and OUTBREAK_ALERT_RAISED) with strictly monotonic HLC ordering.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from aarogya_clinical_engine import evaluate_triage
from aarogya_clinical_engine.triage import PatientCategory, TriageInput
from aarogya_contracts import (
    ActionCard,
    ActionCardPriority,
    CrdtEvent,
    EnrichmentState,
    EventType,
    HlcTimestamp,
    NodeTier,
    TriageAssessment,
    TriageSeverity,
)
from aarogya_ml_pipeline.interfaces import (
    ClinicalSlmStructurer,
    OutbreakDetector,
    OutbreakSignal,
    RiskScorer,
    RiskScoreResult,
    StructuredClinicalNote,
    TranscriptionResult,
    VoiceTranscriber,
)
from aarogya_ml_pipeline.outbreak_detector import EwmaOutbreakDetector
from aarogya_ml_pipeline.risk_scorer import LightGbmRiskScorer, extract_risk_features
from aarogya_ml_pipeline.slm_structurer import LlamaCppSlmStructurer, sanitize_hindi_text
from aarogya_ml_pipeline.whisper_asr import WhisperVoiceTranscriber

logger = logging.getLogger(__name__)

_PRIORITY_MAP: dict[TriageSeverity, ActionCardPriority] = {
    TriageSeverity.RED_EMERGENCY: ActionCardPriority.CRITICAL,
    TriageSeverity.YELLOW_PHC: ActionCardPriority.HIGH,
    TriageSeverity.GREEN_HOME: ActionCardPriority.LOW,
}

_TITLE_MAP: dict[TriageSeverity, str] = {
    TriageSeverity.RED_EMERGENCY: "RED EMERGENCY: Immediate Referral",
    TriageSeverity.YELLOW_PHC: "YELLOW: PHC / ANM Visit Required",
    TriageSeverity.GREEN_HOME: "GREEN: Home Care & Follow-Up",
}

_TITLE_MAP_HI: dict[TriageSeverity, str] = {
    TriageSeverity.RED_EMERGENCY: "रक्त आपातकाल — तत्काल प्राथमिक स्वास्थ्य केन्द्र प्रेषण",
    TriageSeverity.YELLOW_PHC: "पीत चेतावनी — प्राथमिक स्वास्थ्य केन्द्र परामर्श आवश्यक",
    TriageSeverity.GREEN_HOME: "हरित — स्वर टिप्पणी चिकित्सीय सारांश",
}

_RISK_BAND_HI: dict[str, str] = {
    "HIGH": "उच्च",
    "MODERATE": "मध्यम",
    "LOW": "न्यून",
}

_MATERNAL_ONLY_RED_FLAGS: frozenset[str] = frozenset({
    "vaginal_bleeding",
    "severe_headache_or_blurred_vision",
    "reduced_fetal_movement",
    "leaking_fluid_before_labor",
    "high_fever",
    "severe_anemia_signs",
    "severe_abdominal_pain",
    "swelling_face_and_hands",
    "breathing_difficulty_or_chest_pain",
    "convulsions_or_fits",
    "eclampsia",
    "pph",
    "antepartum_bleeding",
    "postpartum_bleeding",
    "puerperal_sepsis_signs",
    "previous_lscs_scar_tenderness",
    "hyperemesis_gravidarum_severe",
    "postpartum_hemorrhage_heavy",
    "antepartum_hemorrhage_painful_or_painless",
    "obstructed_or_prolonged_labor",
    "gestational_diabetes_gdm",
    "rh_negative_mother",
    "twin_or_multiple_gestation",
    "previous_lscs_history",
    "maternal_short_stature_or_malpresentation",
})


class EnrichmentPipeline:
    """Orchestrates deferred edge ML enrichment for recorded voice notes.

    Preserves the Clinical Safety Invariant: deterministic WHO IMNCI / NHM ASHA
    rules are the authoritative safety floor. Local ML/SLM/RiskScorer outputs
    are strictly advisory and MUST NEVER downgrade or override RED_EMERGENCY.
    """

    def __init__(
        self,
        transcriber: VoiceTranscriber | None = None,
        structurer: ClinicalSlmStructurer | None = None,
        risk_scorer: RiskScorer | None = None,
        outbreak_detector: OutbreakDetector | None = None,
    ) -> None:
        self.transcriber: VoiceTranscriber = (
            transcriber if transcriber is not None else WhisperVoiceTranscriber()
        )
        self.structurer: ClinicalSlmStructurer = (
            structurer if structurer is not None else LlamaCppSlmStructurer()
        )
        self.risk_scorer: RiskScorer = (
            risk_scorer if risk_scorer is not None else LightGbmRiskScorer()
        )
        self.outbreak_detector: OutbreakDetector = (
            outbreak_detector if outbreak_detector is not None else EwmaOutbreakDetector()
        )

    def process_voice_note(
        self,
        voice_event: CrdtEvent,
        *,
        hub_node_id: str,
        hlc: HlcTimestamp,
        audio_bytes: bytes | None = None,
        patient_context: dict[str, Any] | None = None,
        village_syndrome_counts: dict[tuple[str, str], list[int]] | None = None,
    ) -> list[CrdtEvent]:
        """Execute deferred enrichment for a VOICE_NOTE_RECORDED CRDT event.

        Args:
            voice_event: The original CRDT event with event_type == VOICE_NOTE_RECORDED.
            hub_node_id: Node identifier of the Tier-2 Hub emitting enrichment events.
            hlc: Base Hybrid Logical Clock timestamp for monotonic event sequencing.
            audio_bytes: Raw audio bytes fetched from local blob storage, or None.
            patient_context: Optional patient vitals, pregnancy, or demographics dict.
            village_syndrome_counts: Optional mapping of (village_id, syndrome) to daily counts.

        Returns:
            List of contract-valid CRDT events:
            [ENRICHMENT_COMPLETED, ACTION_CARD_ISSUED, (optional OUTBREAK_ALERT_RAISED...)]
        """
        if voice_event.event_type != EventType.VOICE_NOTE_RECORDED:
            raise ValueError(
                f"EnrichmentPipeline requires a VOICE_NOTE_RECORDED event, "
                f"got {voice_event.event_type}"
            )

        payload: dict[str, Any] = voice_event.payload or {}
        language = str(payload.get("language", "hi"))

        # Step A (ASR): Transcribe audio_bytes or fall back to payload transcript_hint
        if audio_bytes is not None and len(audio_bytes) > 0:
            asr_result: TranscriptionResult = self.transcriber.transcribe(
                audio_bytes, language_hint=language
            )
        else:
            hint = str(payload.get("transcript_hint", payload.get("audio_text", ""))).strip()
            if hint:
                asr_result = TranscriptionResult(
                    transcript=hint,
                    language=language,
                    confidence=1.0,
                    backend="transcript_hint",
                )
            else:
                asr_result = self.transcriber.transcribe(b"", language_hint=language)

        # Step B (SLM GBNF): Extract StructuredClinicalNote
        structured: StructuredClinicalNote = self.structurer.structure_note(
            asr_result.transcript, language=asr_result.language
        )

        # Step C (CLINICAL SAFETY FLOOR - MANDATORY):
        # Feed candidate_danger_flags + extracted_symptoms + patient_context into evaluate_triage
        triage_input_fields = set(TriageInput.model_fields.keys())
        context_kwargs: dict[str, Any] = {}
        if patient_context:
            for k, v in patient_context.items():
                if k in triage_input_fields and v is not None:
                    context_kwargs[k] = v

        danger_signs = list(structured.candidate_danger_flags)
        if "danger_signs" in context_kwargs:
            extra_ds = context_kwargs.pop("danger_signs")
            if isinstance(extra_ds, (list, tuple, set)):
                for d in extra_ds:
                    if d not in danger_signs:
                        danger_signs.append(d)

        symptoms = list(structured.extracted_symptoms)
        if "symptoms" in context_kwargs:
            extra_sym = context_kwargs.pop("symptoms")
            if isinstance(extra_sym, (list, tuple, set)):
                for s in extra_sym:
                    if s not in symptoms:
                        symptoms.append(s)

        patient_id = voice_event.patient_id or context_kwargs.pop("patient_id", None)
        assessed_at_ms = context_kwargs.pop("assessed_at_ms", hlc.wall_ms)

        normalized_flags = {
            str(f).strip().lower().replace("-", "_").replace(" ", "_")
            for f in (*danger_signs, *symptoms)
            if str(f).strip()
        }

        # Populate structured clinical flags from extracted symptoms when vitals/context omit them
        if not context_kwargs.get("fever_days") and (
            normalized_flags & {"fever", "high_fever", "very_high_fever"}
        ):
            context_kwargs["fever_days"] = 1
        if "has_cough_or_difficult_breathing" not in context_kwargs and (
            normalized_flags
            & {"cough", "fast_breathing", "severe_breathing_difficulty", "chest_indrawing"}
        ):
            context_kwargs["has_cough_or_difficult_breathing"] = True
        if "chest_indrawing" not in context_kwargs and (
            normalized_flags & {"chest_indrawing", "severe_breathing_difficulty"}
        ):
            context_kwargs["chest_indrawing"] = True
        if "has_diarrhea" not in context_kwargs and (
            normalized_flags & {"diarrhea", "blood_in_stool"}
        ):
            context_kwargs["has_diarrhea"] = True
        if "blood_in_stool" not in context_kwargs and "blood_in_stool" in normalized_flags:
            context_kwargs["blood_in_stool"] = True

        # Ensure maternal-only danger flags never silently downgrade to GREEN_HOME
        # when patient_context is omitted (matches Tier-2 Hub enrichment_worker.py).
        if "patient_category" not in context_kwargs and not context_kwargs.get("is_pregnant"):
            age_months = context_kwargs.get("age_months")
            is_pediatric_age = isinstance(age_months, (int, float)) and age_months < 60
            if (normalized_flags & _MATERNAL_ONLY_RED_FLAGS) and not is_pediatric_age:
                context_kwargs["patient_category"] = PatientCategory.MATERNAL

        triage_input = TriageInput(
            patient_id=patient_id,
            danger_signs=danger_signs,
            symptoms=symptoms,
            assessed_at_ms=assessed_at_ms,
            **context_kwargs,
        )
        triage_assessment: TriageAssessment = evaluate_triage(triage_input)

        # Step D (Risk + Outbreak): Compute advisory RiskScoreResult via RiskScorer
        risk_features = extract_risk_features(triage_input)
        if patient_context:
            for k, v in patient_context.items():
                if k not in risk_features and isinstance(v, (int, float, bool)):
                    risk_features[k] = v
        risk_result: RiskScoreResult = self.risk_scorer.score_risk(risk_features)

        # Evaluate OutbreakDetector if village_syndrome_counts is supplied
        outbreak_signals: list[OutbreakSignal] = []
        if village_syndrome_counts:
            for (village_id, syndrome), counts in sorted(village_syndrome_counts.items()):
                signal = self.outbreak_detector.detect_outbreak(village_id, syndrome, counts)
                if signal.alert_triggered:
                    outbreak_signals.append(signal)

        # Step E (Emit Contract-Valid Events with monotonic HlcTimestamp logical increments)
        emitted_events: list[CrdtEvent] = []
        node_id = hub_node_id or hlc.node_id
        current_logical = hlc.logical

        # 1. ENRICHMENT_COMPLETED
        enrichment_hlc = HlcTimestamp(
            wall_ms=hlc.wall_ms,
            logical=current_logical,
            node_id=node_id,
        )
        enrichment_event = CrdtEvent(
            event_id=str(uuid4()),
            hlc=enrichment_hlc,
            origin_node_id=hub_node_id,
            patient_id=voice_event.patient_id,
            event_type=EventType.ENRICHMENT_COMPLETED,
            enrichment_state=EnrichmentState.COMPLETED,
            ref_event_id=voice_event.event_id,
            payload={
                "transcription": asr_result.model_dump(mode="json"),
                "structured_note": structured.model_dump(mode="json"),
                "triage_assessment": triage_assessment.model_dump(mode="json"),
                "risk_score": risk_result.model_dump(mode="json"),
            },
        )
        emitted_events.append(enrichment_event)

        # 2. ACTION_CARD_ISSUED (priority/severity anchored strictly to deterministic TriageAssessment)
        current_logical += 1
        card_hlc = HlcTimestamp(
            wall_ms=hlc.wall_ms,
            logical=current_logical,
            node_id=node_id,
        )
        card_priority = _PRIORITY_MAP.get(
            triage_assessment.severity, ActionCardPriority.MEDIUM
        )
        is_hindi = asr_result.language.strip().lower().startswith("hi")
        if is_hindi:
            card_title = _TITLE_MAP_HI.get(
                triage_assessment.severity, "स्वर टिप्पणी चिकित्सीय सारांश"
            )
            raw_summary = (
                structured.recommended_follow_up
                or triage_assessment.rationale[:1000]
                or "प्राथमिक स्वास्थ्य केन्द्र स्तर पर अनुवर्ती परीक्षण आवश्यक।"
            )
            summary_text = sanitize_hindi_text(raw_summary)
        else:
            card_title = _TITLE_MAP.get(
                triage_assessment.severity, "Voice Note Clinical Summary"
            )
            summary_text = (
                structured.recommended_follow_up
                or triage_assessment.rationale[:1000]
                or "Deterministic triage follow-up required."
            )

        action_steps: list[str] = []
        if triage_assessment.immediate_actions:
            action_steps.extend(triage_assessment.immediate_actions)
        if structured.extracted_symptoms:
            if is_hindi:
                sanitized_symptoms = [sanitize_hindi_text(s) for s in structured.extracted_symptoms]
                action_steps.append(f"लक्षित लक्षण: {', '.join(sanitized_symptoms)}")
            else:
                action_steps.append(
                    f"Observed symptoms: {', '.join(structured.extracted_symptoms)}"
                )
        if is_hindi:
            band_hi = _RISK_BAND_HI.get(risk_result.risk_band, risk_result.risk_band)
            action_steps.append(f"संकट स्तर: {band_hi} ({risk_result.risk_score:.2f})")
        else:
            action_steps.append(
                f"ML risk band: {risk_result.risk_band} ({risk_result.risk_score:.2f})"
            )

        action_card = ActionCard(
            patient_id=voice_event.patient_id,
            title=card_title[:160],
            summary=summary_text[:1000],
            action_steps=action_steps,
            priority=card_priority,
            severity=triage_assessment.severity,
            target_tier=NodeTier.TIER_0_WATCH,
            source_event_id=enrichment_event.event_id,
            language=asr_result.language,
        )

        card_event = CrdtEvent(
            event_id=str(uuid4()),
            hlc=card_hlc,
            origin_node_id=hub_node_id,
            patient_id=voice_event.patient_id,
            event_type=EventType.ACTION_CARD_ISSUED,
            enrichment_state=EnrichmentState.COMPLETED,
            ref_event_id=voice_event.event_id,
            payload=action_card.model_dump(mode="json"),
        )
        emitted_events.append(card_event)

        # 3. OUTBREAK_ALERT_RAISED (only when OutbreakSignal.alert_triggered is True)
        for signal in outbreak_signals:
            current_logical += 1
            outbreak_hlc = HlcTimestamp(
                wall_ms=hlc.wall_ms,
                logical=current_logical,
                node_id=node_id,
            )
            outbreak_event = CrdtEvent(
                event_id=str(uuid4()),
                hlc=outbreak_hlc,
                origin_node_id=hub_node_id,
                patient_id=voice_event.patient_id,
                event_type=EventType.OUTBREAK_ALERT_RAISED,
                enrichment_state=EnrichmentState.COMPLETED,
                ref_event_id=voice_event.event_id,
                payload=signal.model_dump(mode="json"),
            )
            emitted_events.append(outbreak_event)

        return emitted_events
