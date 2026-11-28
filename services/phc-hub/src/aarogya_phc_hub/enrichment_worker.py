"""Background deferred ML enrichment worker for the Tier-2 PHC Hub.

Consumes ``PENDING`` ``VOICE_NOTE_RECORDED`` CRDT events from :class:`EventStore`,
resolves optional binary audio blobs from :class:`LocalBlobStore`, runs pluggable
offline ML backends (``VoiceTranscriber`` -> ``ClinicalSlmStructurer`` ->
``RiskScorer`` -> ``OutbreakDetector``), and ALWAYS enforces the deterministic
Clinical Safety Floor via ``aarogya_clinical_engine.evaluate_triage`` so local
ML/SLM outputs never dictate or downgrade ``TriageSeverity``.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import threading
from collections import defaultdict
from collections.abc import Collection
from typing import Any
from uuid import uuid4

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from aarogya_clinical_engine import PatientCategory, TriageInput, evaluate_triage
from aarogya_contracts import (
    ActionCard,
    ActionCardPriority,
    CrdtEvent,
    EnrichmentState,
    EventType,
    ExecutionTarget,
    HardwareCapabilityManifest,
    NodeTier,
    PatientRecord,
    TriageAssessment,
    TriageSeverity,
    WatchMode,
)
from aarogya_crdt_sync import (
    EventStore,
    HlcClock,
    ProjectedState,
    project_state,
    select_offloadable_jobs,
)
from aarogya_ml_pipeline import (
    ClinicalSlmStructurer,
    EwmaOutbreakDetector,
    LightGbmRiskScorer,
    LlamaCppSlmStructurer,
    OutbreakDetector,
    RiskScorer,
    StructuredClinicalNote,
    VoiceTranscriber,
    WhisperVoiceTranscriber,
)
from aarogya_ml_pipeline.risk_scorer import extract_risk_features
from aarogya_phc_hub.blob_store import LocalBlobStore
from aarogya_phc_hub.capability_router import WorkloadKind, route_workload

logger = logging.getLogger(__name__)

_MS_PER_DAY = 86_400_000
_OUTBREAK_WINDOW_DAYS = 30
_MIN_OUTBREAK_TOTAL_CASES = 5
_MIN_OUTBREAK_MULTI_DAY_LATEST_CASES = 4
_MIN_OUTBREAK_SINGLE_DAY_CASES = 5
_STUB_BINARY_AUDIO_PREFIX = "[stub-audio-"
_IGNORED_OUTBREAK_SYNDROMES = frozenset({"general_checkup"})

_SEVERITY_RANK: dict[TriageSeverity, int] = {
    TriageSeverity.GREEN_HOME: 0,
    TriageSeverity.YELLOW_PHC: 1,
    TriageSeverity.RED_EMERGENCY: 2,
}

_GREEN_DEFAULT_RULES = frozenset({"CLINICAL_ROUTINE_GREEN", "WATCH_RAPID_NO_DANGER_SIGNS"})

_SLM_FLAG_TO_CLINICAL_FLAG: dict[str, str] = {
    "lethargy": "lethargic_or_unconscious",
    "bleeding": "severe_bleeding",
}

_MATERNAL_ONLY_RED_FLAGS = frozenset(
    {
        "vaginal_bleeding",
        "reduced_fetal_movement",
        "leaking_fluid_before_labor",
        "severe_headache_or_blurred_vision",
        "swelling_face_and_hands",
        "severe_abdominal_pain",
        "convulsions_or_fits",
        "eclampsia",
        "pph",
        "antepartum_bleeding",
        "postpartum_bleeding",
    }
)


class EnrichmentRunSummary(BaseModel):
    """Deterministic summary returned by a single enrichment worker sweep."""

    model_config = ConfigDict(extra="forbid")

    processed: int = Field(default=0, ge=0)
    skipped_missing_blob: int = Field(default=0, ge=0)
    emitted_events: int = Field(default=0, ge=0)
    outbreak_alerts: int = Field(default=0, ge=0)
    pending_remaining: int = Field(default=0, ge=0)
    processed_event_ids: list[str] = Field(default_factory=list)


class EnrichmentWorkerStatus(BaseModel):
    """Operational telemetry snapshot exposed by ``GET /api/v1/enrichment/status``."""

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., min_length=1, max_length=128)
    running: bool = False
    interval_sec: float = Field(..., gt=0.0)
    pending_enrichments: int = Field(default=0, ge=0)
    active_stages: dict[str, str] = Field(default_factory=dict)
    asr_target: ExecutionTarget
    slm_target: ExecutionTarget
    outbreak_target: ExecutionTarget
    total_runs: int = Field(default=0, ge=0)
    total_processed: int = Field(default=0, ge=0)
    total_emitted_events: int = Field(default=0, ge=0)
    total_outbreak_alerts: int = Field(default=0, ge=0)
    last_run: EnrichmentRunSummary | None = None


def _normalize_slm_flags(raw_flags: list[str]) -> list[str]:
    """Map SLM-extracted symptom/flag codes onto canonical clinical engine flag tokens."""
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in raw_flags:
        token = raw.strip().lower().replace("-", "_").replace(" ", "_")
        if not token:
            continue
        mapped = _SLM_FLAG_TO_CLINICAL_FLAG.get(token, token)
        if mapped not in seen:
            seen.add(mapped)
            normalized.append(mapped)
    return normalized


def _safe_int(value: Any, *, min_val: int, max_val: int) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    coerced = int(value)
    return coerced if min_val <= coerced <= max_val else None


def _safe_float(value: Any, *, min_val: float, max_val: float) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    coerced = float(value)
    return coerced if min_val <= coerced <= max_val else None


def _clean_language(raw: Any, default: str = "hi") -> str:
    text = str(raw).strip() if raw is not None else ""
    if 2 <= len(text) <= 16:
        return text
    return default


def _build_triage_input(
    voice_event: CrdtEvent,
    structured: StructuredClinicalNote,
    patient: PatientRecord | None,
) -> tuple[TriageInput, dict[str, float | int | bool]]:
    """Construct a strict ``TriageInput`` and tabular feature dict from SLM + patient context."""
    payload = voice_event.payload
    danger_signs = _normalize_slm_flags(structured.candidate_danger_flags)
    symptoms = _normalize_slm_flags(structured.extracted_symptoms)
    all_flags = set(danger_signs) | set(symptoms)

    age_months = (
        patient.age_months
        if patient is not None and patient.age_months is not None
        else _safe_int(payload.get("age_months"), min_val=0, max_val=1500)
    )
    is_pregnant = bool(
        (patient is not None and patient.is_pregnant) or payload.get("is_pregnant") is True
    )
    gestational_weeks = (
        patient.gestational_weeks
        if patient is not None and patient.gestational_weeks is not None
        else _safe_int(payload.get("gestational_weeks"), min_val=0, max_val=45)
    )

    patient_category: PatientCategory | None = None
    if is_pregnant or (all_flags & _MATERNAL_ONLY_RED_FLAGS):
        patient_category = PatientCategory.MATERNAL

    temperature_c = _safe_float(payload.get("temperature_c"), min_val=30.0, max_val=45.0)
    respiratory_rate_bpm = _safe_int(payload.get("respiratory_rate_bpm"), min_val=0, max_val=160)
    spo2_pct = _safe_int(payload.get("spo2_pct"), min_val=0, max_val=100)
    systolic_bp = _safe_int(payload.get("systolic_bp"), min_val=40, max_val=300)
    diastolic_bp = _safe_int(payload.get("diastolic_bp"), min_val=20, max_val=200)
    hemoglobin_g_dl = _safe_float(payload.get("hemoglobin_g_dl"), min_val=1.0, max_val=25.0)
    muac_cm = _safe_float(payload.get("muac_cm"), min_val=5.0, max_val=50.0)
    fever_days = _safe_int(payload.get("fever_days"), min_val=0, max_val=365) or 0
    if fever_days == 0 and ("fever" in all_flags or "high_fever" in all_flags):
        fever_days = 1

    has_cough_or_breathing = bool(
        payload.get("has_cough_or_difficult_breathing") is True
        or bool(
            all_flags
            & {
                "cough",
                "fast_breathing",
                "breathing_difficulty",
                "difficulty_breathing",
                "shortness_of_breath",
                "breathlessness",
            }
        )
    )

    triage_input = TriageInput(
        patient_id=voice_event.patient_id,
        patient_category=patient_category,
        age_months=age_months,
        is_pregnant=is_pregnant,
        gestational_weeks=gestational_weeks if is_pregnant else None,
        danger_signs=danger_signs,
        symptoms=symptoms,
        temperature_c=temperature_c,
        respiratory_rate_bpm=respiratory_rate_bpm,
        spo2_pct=spo2_pct,
        systolic_bp=systolic_bp,
        diastolic_bp=diastolic_bp,
        hemoglobin_g_dl=hemoglobin_g_dl,
        muac_cm=muac_cm,
        has_cough_or_difficult_breathing=has_cough_or_breathing,
        chest_indrawing=bool(payload.get("chest_indrawing") is True or "chest_indrawing" in all_flags),
        has_diarrhea=bool(
            payload.get("has_diarrhea") is True or "diarrhea" in all_flags or "dysentery" in all_flags
        ),
        diarrhea_days=_safe_int(payload.get("diarrhea_days"), min_val=0, max_val=365) or 0,
        blood_in_stool=bool(
            payload.get("blood_in_stool") is True
            or "blood_in_stool" in all_flags
            or "dysentery" in all_flags
        ),
        fever_days=fever_days,
        assessed_at_ms=voice_event.hlc.wall_ms,
    )

    features = extract_risk_features(triage_input)
    return triage_input, features


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _highest_severity_triage(
    assessments: list[TriageAssessment],
) -> TriageAssessment | None:
    """Return the highest-severity TriageAssessment (ties broken by latest)."""
    best: TriageAssessment | None = None
    best_rank = -1
    for assessment in assessments:
        rank = _SEVERITY_RANK[assessment.severity]
        if rank >= best_rank:
            best = assessment
            best_rank = rank
    return best


def _apply_monotonic_severity_floor(
    new_triage: TriageAssessment,
    existing_triage: TriageAssessment | None,
) -> TriageAssessment:
    """Ensure enrichment never downgrades an active higher-severity patient triage."""
    if existing_triage is None:
        return new_triage
    floor_severity = existing_triage.severity
    if _SEVERITY_RANK[floor_severity] <= _SEVERITY_RANK[new_triage.severity]:
        return new_triage

    merged_rules = _dedupe_preserve_order(
        [
            *existing_triage.matched_rules,
            *[r for r in new_triage.matched_rules if r not in _GREEN_DEFAULT_RULES],
        ]
    )
    if new_triage.severity == TriageSeverity.GREEN_HOME:
        merged_actions = _dedupe_preserve_order(list(existing_triage.immediate_actions))
    else:
        merged_actions = _dedupe_preserve_order(
            [*existing_triage.immediate_actions, *new_triage.immediate_actions]
        )

    if floor_severity == TriageSeverity.RED_EMERGENCY and not any(
        any(tok in action.lower() for tok in ("108", "fru", "refer", "emergency"))
        for action in merged_actions
    ):
        merged_actions.append("Arrange immediate 108 ambulance / FRU emergency referral.")

    is_green_or_home_care = (
        new_triage.severity == TriageSeverity.GREEN_HOME
        or "home-care thresholds" in new_triage.rationale.lower()
    )
    if is_green_or_home_care:
        if floor_severity == TriageSeverity.RED_EMERGENCY:
            merged_rationale = (
                "Monotonic clinical safety floor preserved RED_EMERGENCY from prior "
                "danger-sign/triage assessment; immediate 108/FRU referral remains mandatory."
            )
        else:
            merged_rationale = (
                "Monotonic clinical safety floor preserved YELLOW_PHC from prior "
                "assessment; PHC Medical Officer review remains required."
            )
    else:
        merged_rationale = (
            f"Preserved active {floor_severity.value} triage floor: "
            f"{existing_triage.rationale} (Follow-up screen: {new_triage.rationale})"
        )

    return TriageAssessment.model_validate(
        new_triage.model_copy(
            update={
                "severity": floor_severity,
                "referral_required": True,
                "matched_rules": merged_rules,
                "immediate_actions": merged_actions,
                "rationale": merged_rationale,
            }
        ).model_dump(mode="json")
    )


_BP_PAIR_RE = re.compile(r"\b(\d{2,3})\s*/\s*(\d{2,3})\s*mmHg\b", re.IGNORECASE)
_SYSTOLIC_ONLY_RE = re.compile(r"\bsystolic\s+bp\s+(\d{2,3})\s*mmHg\b", re.IGNORECASE)
_SPO2_RE = re.compile(r"\bSpO2\s+(\d{2,3})\s*%", re.IGNORECASE)
_HB_RE = re.compile(r"\bHemoglobin\s+(\d+(?:\.\d+)?)\s*g/dL\b", re.IGNORECASE)
_MUAC_RE = re.compile(r"\bMUAC\s+(\d+(?:\.\d+)?)\s*cm\b", re.IGNORECASE)
_RR_RE = re.compile(r"\brespiratory\s+rate\s+(\d{1,3})\s*/\s*min\b", re.IGNORECASE)
_TEMP_RE = re.compile(r"\b(3[0-9](?:\.\d+)?|4[0-5](?:\.\d+)?)\s*°?\s*C\b")
_ML_ENGINE_PROVENANCE = (
    "28-Tree Monotone GBDT + Exact TreeSHAP (clinical_gbdt_v1.json, AUROC 0.8318)"
)


def _build_reasoning_provenance(
    *,
    triage: TriageAssessment,
    is_pregnant: bool,
    risk_score: float,
) -> dict[str, Any]:
    """Build explicit reasoning provenance separating WHO/NHM rules from Laptop ML analytics."""
    is_maternal = is_pregnant or any(
        rule.upper().startswith("MAT_") or "MATERNAL" in rule.upper()
        for rule in triage.matched_rules
    )
    clinical_protocol = (
        "NHM ASHA Maternal (NHM_ASHA_MATERNAL_ANC_PNC_2024)"
        if is_maternal
        else "WHO IMNCI (WHO_IMNCI_INDIA_2024)"
    )
    risk_pct = round(risk_score * 100)
    return {
        "stage": "HOST_LAPTOP_ML_ANALYTICS",
        "clinical_protocol": clinical_protocol,
        "matched_rule_ids": list(triage.matched_rules),
        "clinical_parameters": triage.rationale,
        "ml_engine": _ML_ENGINE_PROVENANCE,
        "ml_summary": (
            f"Laptop GBDT combined 13 vitals & flags -> Risk {risk_pct}% "
            f"(WHO {triage.severity.value} safety floor enforced)"
        ),
    }


def _top_shap_features(
    shap_attributions: dict[str, float],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    """Return the top SHAP drivers ordered by absolute contribution magnitude."""
    ranked = sorted(
        ((str(k), float(v)) for k, v in shap_attributions.items()),
        key=lambda item: (-abs(item[1]), item[0]),
    )
    non_zero = [item for item in ranked if abs(item[1]) > 1e-6]
    chosen = non_zero[:limit] if non_zero else ranked[:limit]
    return [
        {
            "feature": name,
            "contribution": round(val, 4),
            "direction": "risk" if val >= 0.0 else "protective",
        }
        for name, val in chosen
    ]


def _extract_embedded_triage(payload: dict[str, Any]) -> TriageAssessment | None:
    """Safely parse a TriageAssessment embedded in a TRIAGE_COMPLETED payload."""
    if "severity" not in payload or "rationale" not in payload:
        return None
    known = {key: payload[key] for key in TriageAssessment.model_fields if key in payload}
    with contextlib.suppress(Exception):
        return TriageAssessment.model_validate(known)
    return None


def _recommended_follow_up_for_triage(triage: TriageAssessment, risk_band: str) -> str:
    """Derive a concise, clinically safe follow-up recommendation for triage enrichment."""
    if triage.severity == TriageSeverity.RED_EMERGENCY:
        if triage.immediate_actions:
            return triage.immediate_actions[0]
        return "Immediate emergency referral to PHC / FRU required."
    if triage.severity == TriageSeverity.YELLOW_PHC:
        if triage.immediate_actions:
            return triage.immediate_actions[0]
        return "Schedule PHC / ANM clinical evaluation today."
    if risk_band == "HIGH":
        return "Elevated ML risk score — schedule close ASHA follow-up within 24 hours."
    if risk_band == "MODERATE":
        return "Monitor symptoms closely and re-assess within 24–48 hours."
    if triage.immediate_actions:
        return triage.immediate_actions[0]
    return "Continue home care and routine ASHA follow-up."


def _build_triage_input_from_triage_event(
    triage_event: CrdtEvent,
    patient: PatientRecord | None,
) -> tuple[TriageInput, dict[str, float | int | bool], TriageAssessment | None]:
    """Build ``TriageInput`` and tabular ML features from a ``TRIAGE_COMPLETED`` event."""
    payload = triage_event.payload
    nested_vitals = (
        payload.get("vitals")
        if isinstance(payload.get("vitals"), dict)
        else (
            payload.get("triage_input")
            if isinstance(payload.get("triage_input"), dict)
            else {}
        )
    )

    def _get(key: str) -> Any:
        if key in payload and payload[key] is not None:
            return payload[key]
        return nested_vitals.get(key)

    incoming_triage = _extract_embedded_triage(payload)
    rationale = str(payload.get("rationale") or (incoming_triage.rationale if incoming_triage else ""))
    raw_matched_rules = payload.get("matched_rules")
    matched_rules = (
        [str(r) for r in raw_matched_rules if isinstance(r, str)]
        if isinstance(raw_matched_rules, list)
        else (list(incoming_triage.matched_rules) if incoming_triage else [])
    )

    raw_danger = _get("danger_signs")
    raw_symptoms = _get("symptoms")
    danger_signs = _normalize_slm_flags(
        [str(x) for x in raw_danger if isinstance(x, str)] if isinstance(raw_danger, list) else []
    )
    symptoms = _normalize_slm_flags(
        [str(x) for x in raw_symptoms if isinstance(x, str)] if isinstance(raw_symptoms, list) else []
    )
    all_flags = set(danger_signs) | set(symptoms)

    age_months = (
        _safe_int(_get("age_months"), min_val=0, max_val=1500)
        if _get("age_months") is not None
        else (patient.age_months if patient is not None else None)
    )
    is_pregnant = bool(
        (patient is not None and patient.is_pregnant) or _get("is_pregnant") is True
    )
    gestational_weeks = (
        _safe_int(_get("gestational_weeks"), min_val=0, max_val=45)
        if _get("gestational_weeks") is not None
        else (patient.gestational_weeks if patient is not None else None)
    )

    temperature_c = _safe_float(_get("temperature_c"), min_val=30.0, max_val=45.0)
    respiratory_rate_bpm = _safe_int(_get("respiratory_rate_bpm"), min_val=0, max_val=160)
    spo2_pct = _safe_int(_get("spo2_pct"), min_val=0, max_val=100)
    systolic_bp = _safe_int(_get("systolic_bp"), min_val=40, max_val=300)
    diastolic_bp = _safe_int(_get("diastolic_bp"), min_val=20, max_val=200)
    hemoglobin_g_dl = _safe_float(_get("hemoglobin_g_dl"), min_val=1.0, max_val=25.0)
    muac_cm = _safe_float(_get("muac_cm"), min_val=5.0, max_val=50.0)

    # Fallback vital extraction from deterministic rationale when phone sends pure TriageAssessment
    if rationale:
        if systolic_bp is None or diastolic_bp is None:
            bp_match = _BP_PAIR_RE.search(rationale)
            if bp_match:
                if systolic_bp is None:
                    systolic_bp = _safe_int(int(bp_match.group(1)), min_val=40, max_val=300)
                if diastolic_bp is None:
                    diastolic_bp = _safe_int(int(bp_match.group(2)), min_val=20, max_val=200)
            elif systolic_bp is None:
                sys_match = _SYSTOLIC_ONLY_RE.search(rationale)
                if sys_match:
                    systolic_bp = _safe_int(int(sys_match.group(1)), min_val=40, max_val=300)
        if spo2_pct is None:
            spo2_match = _SPO2_RE.search(rationale)
            if spo2_match:
                spo2_pct = _safe_int(int(spo2_match.group(1)), min_val=0, max_val=100)
        if hemoglobin_g_dl is None:
            hb_match = _HB_RE.search(rationale)
            if hb_match:
                hemoglobin_g_dl = _safe_float(float(hb_match.group(1)), min_val=1.0, max_val=25.0)
        if muac_cm is None:
            muac_match = _MUAC_RE.search(rationale)
            if muac_match:
                muac_cm = _safe_float(float(muac_match.group(1)), min_val=5.0, max_val=50.0)
        if respiratory_rate_bpm is None:
            rr_match = _RR_RE.search(rationale)
            if rr_match:
                respiratory_rate_bpm = _safe_int(int(rr_match.group(1)), min_val=0, max_val=160)
        if temperature_c is None:
            temp_match = _TEMP_RE.search(rationale)
            if temp_match:
                temperature_c = _safe_float(float(temp_match.group(1)), min_val=30.0, max_val=45.0)

    fever_days = _safe_int(_get("fever_days"), min_val=0, max_val=365) or 0
    if fever_days == 0 and (
        "fever" in all_flags
        or "high_fever" in all_flags
        or any("FEVER" in r.upper() for r in matched_rules)
    ):
        fever_days = 1

    patient_category: PatientCategory | None = None
    if is_pregnant or (all_flags & _MATERNAL_ONLY_RED_FLAGS) or any(
        "MATERNAL" in r.upper() or r.upper().startswith("MAT_") for r in matched_rules
    ):
        patient_category = PatientCategory.MATERNAL

    has_cough_or_breathing = bool(
        _get("has_cough_or_difficult_breathing") is True
        or bool(
            all_flags
            & {
                "cough",
                "fast_breathing",
                "breathing_difficulty",
                "difficulty_breathing",
                "shortness_of_breath",
                "breathlessness",
            }
        )
        or any("RESP" in r.upper() for r in matched_rules)
    )

    triage_input = TriageInput(
        patient_id=triage_event.patient_id,
        patient_category=patient_category,
        age_months=age_months,
        is_pregnant=is_pregnant,
        gestational_weeks=gestational_weeks if is_pregnant else None,
        danger_signs=danger_signs,
        symptoms=symptoms,
        temperature_c=temperature_c,
        respiratory_rate_bpm=respiratory_rate_bpm,
        spo2_pct=spo2_pct,
        systolic_bp=systolic_bp,
        diastolic_bp=diastolic_bp,
        hemoglobin_g_dl=hemoglobin_g_dl,
        muac_cm=muac_cm,
        has_cough_or_difficult_breathing=has_cough_or_breathing,
        chest_indrawing=bool(_get("chest_indrawing") is True or "chest_indrawing" in all_flags),
        has_diarrhea=bool(
            _get("has_diarrhea") is True
            or "diarrhea" in all_flags
            or "dysentery" in all_flags
            or any("DIARRHEA" in r.upper() for r in matched_rules)
        ),
        diarrhea_days=_safe_int(_get("diarrhea_days"), min_val=0, max_val=365) or 0,
        blood_in_stool=bool(
            _get("blood_in_stool") is True
            or "blood_in_stool" in all_flags
            or "dysentery" in all_flags
        ),
        fever_days=fever_days,
        assessed_at_ms=triage_event.hlc.wall_ms,
    )

    features = extract_risk_features(triage_input)
    non_green_rules = [r for r in matched_rules if r not in _GREEN_DEFAULT_RULES]
    if int(features.get("symptom_count", 0)) == 0 and non_green_rules:
        features["symptom_count"] = len(non_green_rules)
    return triage_input, features, incoming_triage


def _card_from_deterministic_triage(
    *,
    patient_id: str | None,
    triage: TriageAssessment,
    structured: StructuredClinicalNote | None = None,
    recommended_follow_up: str | None = None,
    risk_band: str,
    risk_score: float,
    source_event_id: str,
    language: str,
) -> ActionCard:
    """Build an ``ActionCard`` whose severity and floor priority come strictly from ``triage``."""
    green_title = (
        "GREEN: Voice Note Clinical Summary"
        if structured is not None
        else "GREEN: Clinical AI Risk Summary"
    )
    title_map = {
        TriageSeverity.RED_EMERGENCY: "RED EMERGENCY: Immediate Referral",
        TriageSeverity.YELLOW_PHC: "YELLOW: PHC / ANM Visit Required",
        TriageSeverity.GREEN_HOME: green_title,
    }
    if triage.severity == TriageSeverity.RED_EMERGENCY:
        priority = ActionCardPriority.CRITICAL
    elif triage.severity == TriageSeverity.YELLOW_PHC:
        priority = ActionCardPriority.HIGH
    elif risk_band in ("MODERATE", "HIGH"):
        priority = ActionCardPriority.MEDIUM
    else:
        priority = ActionCardPriority.LOW

    steps: list[str] = list(triage.immediate_actions)
    if structured is not None and structured.extracted_symptoms:
        steps.append(f"Observed symptoms: {', '.join(structured.extracted_symptoms)}")
    steps.append(f"ML risk band: {risk_band} ({risk_score:.2f})")
    follow_up = (
        structured.recommended_follow_up if structured is not None else recommended_follow_up
    )
    if follow_up and follow_up not in steps:
        steps.append(follow_up)

    return ActionCard(
        patient_id=patient_id,
        title=title_map[triage.severity],
        summary=triage.rationale[:1000],
        action_steps=steps,
        priority=priority,
        severity=triage.severity,
        target_tier=NodeTier.TIER_0_WATCH,
        watch_mode=WatchMode.CHW_COMPANION,
        source_event_id=source_event_id,
        language=language,
    )


def _syndromes_from_triage_rules(matched_rules: list[str]) -> list[str]:
    """Map deterministic triage rule IDs onto canonical village surveillance syndromes."""
    found: list[str] = []
    for rule_id in matched_rules:
        upper = rule_id.upper()
        if "FEVER" in upper and "fever" not in found:
            found.append("fever")
        if "DIARRHEA" in upper and "diarrhea" not in found:
            found.append("diarrhea")
        if "RESP" in upper and "respiratory" not in found:
            found.append("respiratory")
    return found


class EnrichmentWorker:
    """Offline Tier-2 PHC Hub worker converting pending voice notes into clinical enrichments."""

    def __init__(
        self,
        store: EventStore,
        blob_store: LocalBlobStore,
        clock: HlcClock,
        manifest: HardwareCapabilityManifest,
        *,
        transcriber: VoiceTranscriber | None = None,
        structurer: ClinicalSlmStructurer | None = None,
        risk_scorer: RiskScorer | None = None,
        outbreak_detector: OutbreakDetector | None = None,
        poll_interval_sec: float = 5.0,
    ) -> None:
        if poll_interval_sec <= 0:
            raise ValueError("poll_interval_sec must be strictly positive.")
        self._store = store
        self._blob_store = blob_store
        self._clock = clock
        self._manifest = manifest
        self._transcriber: VoiceTranscriber = transcriber or WhisperVoiceTranscriber()
        self._structurer: ClinicalSlmStructurer = structurer or LlamaCppSlmStructurer()
        self._risk_scorer: RiskScorer = risk_scorer or LightGbmRiskScorer()
        self._outbreak_detector: OutbreakDetector = (
            outbreak_detector or EwmaOutbreakDetector(alpha=0.35, min_baseline_days=3)
        )
        self._poll_interval_sec = float(poll_interval_sec)

        self._run_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._active_stages: dict[str, str] = {}
        self._total_runs = 0
        self._total_processed = 0
        self._total_emitted_events = 0
        self._total_outbreak_alerts = 0
        self._last_run: EnrichmentRunSummary | None = None

        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None

    @property
    def active_stages(self) -> dict[str, str]:
        """Return a thread-safe snapshot of currently active per-event enrichment stages."""
        with self._status_lock:
            return dict(self._active_stages)

    def _set_active_stage(self, event_id: str, stage: str) -> None:
        with self._status_lock:
            self._active_stages[event_id] = stage

    def _clear_active_stage(self, event_id: str) -> None:
        with self._status_lock:
            self._active_stages.pop(event_id, None)

    @property
    def is_running(self) -> bool:
        """Return True when the background asyncio polling loop is active."""
        return self._task is not None and not self._task.done()

    def _resolve_audio_payload(
        self,
        voice_event: CrdtEvent,
    ) -> tuple[bytes, str, str | None] | None:
        """Resolve raw audio bytes from ``LocalBlobStore`` with blob-first deferral.

        - When ``audio_blob_key`` is set and present on disk, returns the raw blob bytes.
        - When ``audio_blob_key`` is set and NOT yet on disk (or invalid), returns ``None``
          so the event remains ``PENDING`` until the real audio blob arrives (never
          permanently completing on a preliminary ``transcript_hint``).
        - When ``audio_blob_key`` is omitted/empty (typed or hint-only note), processes
          ``audio_text`` / ``transcript_hint`` immediately.
        """
        payload = voice_event.payload
        raw_blob_key = payload.get("audio_blob_key")
        audio_text = str(payload.get("audio_text", "")).strip()
        transcript_hint = str(payload.get("transcript_hint", "")).strip()
        fallback_text = audio_text or transcript_hint

        if isinstance(raw_blob_key, str) and raw_blob_key.strip():
            blob_key = raw_blob_key.strip()
            blob_result = None
            try:
                blob_result = self._blob_store.get(blob_key)
            except ValueError:
                logger.warning(
                    "Invalid audio_blob_key %r on event %s; deferring safely.",
                    blob_key,
                    voice_event.event_id,
                )
            if blob_result is not None:
                return blob_result[0], "blob", blob_key
            return None

        return fallback_text.encode("utf-8"), "transcript_hint", None

    @staticmethod
    def _existing_patient_triage(
        patient_id: str | None,
        projected: ProjectedState,
        in_batch_triages: dict[str, TriageAssessment],
    ) -> TriageAssessment | None:
        """Return the highest-severity deterministic triage already recorded for ``patient_id``."""
        if not patient_id:
            return None
        candidates: list[TriageAssessment] = list(projected.triage_for_patient(patient_id))
        for enr_evt in projected.enrichments.values():
            if enr_evt.patient_id != patient_id:
                continue
            raw_triage = enr_evt.payload.get("triage_assessment")
            if isinstance(raw_triage, dict):
                with contextlib.suppress(Exception):
                    candidates.append(TriageAssessment.model_validate(raw_triage))
        batch_triage = in_batch_triages.get(patient_id)
        if batch_triage is not None:
            candidates.append(batch_triage)
        return _highest_severity_triage(candidates)

    def _enrich_single_voice_event(
        self,
        voice_event: CrdtEvent,
        projected: ProjectedState,
        in_batch_triages: dict[str, TriageAssessment],
    ) -> tuple[list[CrdtEvent], TriageAssessment] | None:
        try:
            resolved = self._resolve_audio_payload(voice_event)
            if resolved is None:
                return None
            audio_bytes, audio_source, blob_key = resolved

            patient = (
                projected.patients.get(voice_event.patient_id)
                if voice_event.patient_id is not None
                else None
            )
            default_lang = patient.preferred_language if patient is not None else "hi"
            language_hint = _clean_language(
                voice_event.payload.get("language"), default=default_lang
            )

            self._set_active_stage(voice_event.event_id, "transcribing_audio")
            asr_result = self._transcriber.transcribe(audio_bytes, language_hint=language_hint)

            self._set_active_stage(voice_event.event_id, "structuring_note")
            structured = self._structurer.structure_note(
                asr_result.transcript,
                language=asr_result.language,
            )

            self._set_active_stage(voice_event.event_id, "scoring_risk")
            # Mandatory Clinical Safety Floor: deterministic engine owns TriageSeverity and
            # never downgrades an active higher-severity triage for the same patient.
            triage_input, risk_features = _build_triage_input(voice_event, structured, patient)
            raw_triage = evaluate_triage(triage_input)
            existing_triage = self._existing_patient_triage(
                voice_event.patient_id,
                projected,
                in_batch_triages,
            )
            triage_assessment = _apply_monotonic_severity_floor(raw_triage, existing_triage)

            risk_features["has_danger_sign"] = (
                triage_assessment.severity == TriageSeverity.RED_EMERGENCY
                or bool(structured.candidate_danger_flags)
            )
            risk = self._risk_scorer.score_risk(risk_features)
            top_features = _top_shap_features(risk.shap_attributions)
            reasoning_provenance = _build_reasoning_provenance(
                triage=triage_assessment,
                is_pregnant=triage_input.is_pregnant,
                risk_score=risk.risk_score,
            )

            enrichment_payload: dict[str, Any] = {
                "source_type": "voice_note",
                "severity": triage_assessment.severity.value,
                "audio_source": audio_source,
                "transcription": asr_result.model_dump(mode="json"),
                "structured_note": structured.model_dump(mode="json"),
                "triage_assessment": triage_assessment.model_dump(mode="json"),
                "risk_score": risk.model_dump(mode="json"),
                "risk_band": risk.risk_band,
                "shap_attributions": dict(risk.shap_attributions),
                "top_features": top_features,
                "recommended_follow_up": structured.recommended_follow_up,
                "reasoning_provenance": reasoning_provenance,
            }
            if blob_key is not None:
                enrichment_payload["audio_blob_key"] = blob_key

            enrichment_event = CrdtEvent(
                event_id=str(uuid4()),
                hlc=self._clock.tick(),
                origin_node_id=self._manifest.node_id,
                patient_id=voice_event.patient_id,
                event_type=EventType.ENRICHMENT_COMPLETED,
                enrichment_state=EnrichmentState.COMPLETED,
                ref_event_id=voice_event.event_id,
                payload=enrichment_payload,
            )

            card = _card_from_deterministic_triage(
                patient_id=voice_event.patient_id,
                triage=triage_assessment,
                structured=structured,
                risk_band=risk.risk_band,
                risk_score=risk.risk_score,
                source_event_id=enrichment_event.event_id,
                language=_clean_language(asr_result.language, default=language_hint),
            )
            card_event = CrdtEvent(
                event_id=str(uuid4()),
                hlc=self._clock.tick(),
                origin_node_id=self._manifest.node_id,
                patient_id=voice_event.patient_id,
                event_type=EventType.ACTION_CARD_ISSUED,
                enrichment_state=EnrichmentState.COMPLETED,
                ref_event_id=voice_event.event_id,
                payload=card.model_dump(mode="json"),
            )
            return [enrichment_event, card_event], triage_assessment
        finally:
            self._clear_active_stage(voice_event.event_id)

    def _enrich_single_triage_event(
        self,
        triage_event: CrdtEvent,
        projected: ProjectedState,
        in_batch_triages: dict[str, TriageAssessment],
    ) -> tuple[list[CrdtEvent], TriageAssessment]:
        """Run tabular GBDT + TreeSHAP risk enrichment for a PENDING TRIAGE_COMPLETED event."""
        try:
            self._set_active_stage(triage_event.event_id, "scoring_risk")
            patient = (
                projected.patients.get(triage_event.patient_id)
                if triage_event.patient_id is not None
                else None
            )
            default_lang = patient.preferred_language if patient is not None else "en"
            language_hint = _clean_language(
                triage_event.payload.get("language"), default=default_lang
            )

            triage_input, risk_features, incoming_triage = _build_triage_input_from_triage_event(
                triage_event, patient
            )
            raw_triage = evaluate_triage(triage_input)
            existing_triage = self._existing_patient_triage(
                triage_event.patient_id,
                projected,
                in_batch_triages,
            )
            # Enforce deterministic WHO monotonic severity floor across local + incoming + prior triages.
            floor_triage = _highest_severity_triage(
                [t for t in (incoming_triage, existing_triage) if t is not None]
            )
            triage_assessment = _apply_monotonic_severity_floor(raw_triage, floor_triage)

            risk_features["has_danger_sign"] = (
                triage_assessment.severity == TriageSeverity.RED_EMERGENCY
                or bool(triage_input.danger_signs)
            )
            risk = self._risk_scorer.score_risk(risk_features)
            top_features = _top_shap_features(risk.shap_attributions)
            recommended_follow_up = _recommended_follow_up_for_triage(
                triage_assessment, risk.risk_band
            )
            reasoning_provenance = _build_reasoning_provenance(
                triage=triage_assessment,
                is_pregnant=triage_input.is_pregnant,
                risk_score=risk.risk_score,
            )

            enrichment_payload: dict[str, Any] = {
                "source_type": "triage",
                "severity": triage_assessment.severity.value,
                "triage_assessment": triage_assessment.model_dump(mode="json"),
                "risk_score": risk.model_dump(mode="json"),
                "risk_band": risk.risk_band,
                "shap_attributions": dict(risk.shap_attributions),
                "top_features": top_features,
                "recommended_follow_up": recommended_follow_up,
                "reasoning_provenance": reasoning_provenance,
            }
            enrichment_event = CrdtEvent(
                event_id=str(uuid4()),
                hlc=self._clock.tick(),
                origin_node_id=self._manifest.node_id,
                patient_id=triage_event.patient_id,
                event_type=EventType.ENRICHMENT_COMPLETED,
                enrichment_state=EnrichmentState.COMPLETED,
                ref_event_id=triage_event.event_id,
                payload=enrichment_payload,
            )

            card = _card_from_deterministic_triage(
                patient_id=triage_event.patient_id,
                triage=triage_assessment,
                structured=None,
                recommended_follow_up=recommended_follow_up,
                risk_band=risk.risk_band,
                risk_score=risk.risk_score,
                source_event_id=enrichment_event.event_id,
                language=language_hint,
            )
            card_event = CrdtEvent(
                event_id=str(uuid4()),
                hlc=self._clock.tick(),
                origin_node_id=self._manifest.node_id,
                patient_id=triage_event.patient_id,
                event_type=EventType.ACTION_CARD_ISSUED,
                enrichment_state=EnrichmentState.COMPLETED,
                ref_event_id=triage_event.event_id,
                payload=card.model_dump(mode="json"),
            )
            return [enrichment_event, card_event], triage_assessment
        finally:
            self._clear_active_stage(triage_event.event_id)

    def _run_outbreak_sweep(self) -> list[CrdtEvent]:
        """Aggregate unique village daily syndrome cases and emit deduplicated outbreak alerts."""
        if (
            route_workload(self._manifest, WorkloadKind.OUTBREAK_DETECTION)
            == ExecutionTarget.DEFER_TO_HUB
        ):
            return []

        all_events = self._store.get_all_events()
        if not all_events:
            return []

        projected = project_state(all_events)
        events_by_id = {event.event_id: event for event in all_events}

        existing_alert_keys: set[str] = set()
        for alert_evt in projected.outbreak_alerts:
            dedupe_key = alert_evt.payload.get("dedupe_key")
            if isinstance(dedupe_key, str) and dedupe_key:
                existing_alert_keys.add(dedupe_key)
            else:
                v_id = alert_evt.payload.get("village_id")
                syn = alert_evt.payload.get("syndrome")
                day = alert_evt.payload.get("day_bucket")
                if v_id and syn and day is not None:
                    existing_alert_keys.add(f"{v_id}:{syn}:{day}")

        # Deduplicate cases per (village_id, syndrome, day_bucket) by patient_id so multiple
        # notes or triage+voice pairs for the same patient on one day count as a single case.
        case_keys: dict[tuple[str, str], dict[int, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )

        def _resolve_village(event: CrdtEvent, source_event: CrdtEvent | None = None) -> str | None:
            for candidate in (event, source_event):
                if candidate is not None:
                    raw_village = candidate.payload.get("village_id")
                    if isinstance(raw_village, str) and raw_village.strip():
                        return raw_village.strip()
            pid = event.patient_id or (source_event.patient_id if source_event else None)
            if pid and pid in projected.patients:
                return projected.patients[pid].village_id
            return None

        for event in all_events:
            if event.event_type == EventType.ENRICHMENT_COMPLETED:
                source_evt = (
                    events_by_id.get(event.ref_event_id) if event.ref_event_id else None
                )
                village_id = _resolve_village(event, source_evt)
                if not village_id:
                    continue
                transcription_raw = event.payload.get("transcription")
                if isinstance(transcription_raw, dict):
                    transcript_text = str(transcription_raw.get("transcript", ""))
                    if transcript_text.startswith(_STUB_BINARY_AUDIO_PREFIX):
                        # Placeholder stub-ASR text for opaque binary audio must not fabricate
                        # village-level outbreak clusters before real Whisper ASR is installed.
                        continue
                structured_raw = event.payload.get("structured_note")
                if not isinstance(structured_raw, dict):
                    continue
                extracted = structured_raw.get("extracted_symptoms", [])
                if not isinstance(extracted, list):
                    continue
                event_ms = source_evt.hlc.wall_ms if source_evt is not None else event.hlc.wall_ms
                day_bucket = event_ms // _MS_PER_DAY
                case_id = (
                    event.patient_id
                    or (source_evt.patient_id if source_evt is not None else None)
                    or event.ref_event_id
                    or event.event_id
                )
                for raw_sym in extracted:
                    if not isinstance(raw_sym, str):
                        continue
                    sym = raw_sym.strip().lower()
                    if not sym or sym in _IGNORED_OUTBREAK_SYNDROMES:
                        continue
                    case_keys[(village_id, sym)][day_bucket].add(case_id)

            elif event.event_type == EventType.TRIAGE_COMPLETED:
                village_id = _resolve_village(event)
                if not village_id:
                    continue
                matched_rules = event.payload.get("matched_rules", [])
                if not isinstance(matched_rules, list):
                    continue
                assessed_ms = event.payload.get("assessed_at_ms")
                event_ms = (
                    int(assessed_ms)
                    if isinstance(assessed_ms, int) and assessed_ms >= 0
                    else event.hlc.wall_ms
                )
                day_bucket = event_ms // _MS_PER_DAY
                case_id = event.patient_id or event.event_id
                for sym in _syndromes_from_triage_rules(
                    [r for r in matched_rules if isinstance(r, str)]
                ):
                    case_keys[(village_id, sym)][day_bucket].add(case_id)

        emitted_alerts: list[CrdtEvent] = []
        for village_id, syndrome in sorted(case_keys):
            day_map = case_keys[(village_id, syndrome)]
            latest_day = max(day_map)
            start_day = max(min(day_map), latest_day - (_OUTBREAK_WINDOW_DAYS - 1))
            daily_counts = [
                len(day_map.get(day, ())) for day in range(start_day, latest_day + 1)
            ]

            total_cases = sum(daily_counts)
            min_latest_cases = (
                _MIN_OUTBREAK_SINGLE_DAY_CASES
                if len(daily_counts) == 1
                else _MIN_OUTBREAK_MULTI_DAY_LATEST_CASES
            )
            if total_cases < _MIN_OUTBREAK_TOTAL_CASES or daily_counts[-1] < min_latest_cases:
                continue

            signal = self._outbreak_detector.detect_outbreak(village_id, syndrome, daily_counts)
            if not signal.alert_triggered:
                continue

            if (
                signal.severity != TriageSeverity.RED_EMERGENCY
                and daily_counts[-1] >= 2.0 * signal.threshold
            ):
                signal = signal.model_copy(update={"severity": TriageSeverity.RED_EMERGENCY})

            dedupe_key = f"{village_id}:{syndrome}:{latest_day}"
            if dedupe_key in existing_alert_keys:
                continue

            alert_event = CrdtEvent(
                event_id=str(uuid4()),
                hlc=self._clock.tick(),
                origin_node_id=self._manifest.node_id,
                patient_id=None,
                event_type=EventType.OUTBREAK_ALERT_RAISED,
                enrichment_state=EnrichmentState.COMPLETED,
                payload={
                    **signal.model_dump(mode="json"),
                    "day_bucket": latest_day,
                    "daily_counts": daily_counts,
                    "dedupe_key": dedupe_key,
                },
            )
            if self._store.append(alert_event):
                existing_alert_keys.add(dedupe_key)
                emitted_alerts.append(alert_event)

        return emitted_alerts

    def run_once(
        self,
        *,
        max_jobs: int | None = None,
        event_types: Collection[EventType] | None = None,
    ) -> EnrichmentRunSummary:
        """Execute one synchronous enrichment + outbreak-detection sweep."""
        with self._run_lock:
            processed = 0
            skipped_missing_blob = 0
            emitted_events = 0
            processed_event_ids: list[str] = []

            asr_target = route_workload(self._manifest, WorkloadKind.VOICE_ASR)
            slm_target = route_workload(self._manifest, WorkloadKind.CLINICAL_SLM_STRUCTURING)
            risk_target = route_workload(self._manifest, WorkloadKind.TINY_RISK_CHECK)

            can_enrich_voice = (
                asr_target != ExecutionTarget.DEFER_TO_HUB
                and slm_target != ExecutionTarget.DEFER_TO_HUB
            )
            can_enrich_triage = risk_target != ExecutionTarget.DEFER_TO_HUB
            allowed_types = set(event_types) if event_types is not None else None

            if (can_enrich_voice or can_enrich_triage) and (max_jobs is None or max_jobs > 0):
                pending = self._store.get_pending_enrichments()
                offloadable = select_offloadable_jobs(self._manifest, pending)
                if offloadable:
                    projected = project_state(self._store.get_all_events())
                    in_batch_triages: dict[str, TriageAssessment] = {}
                    for job in offloadable:
                        if max_jobs is not None and processed >= max_jobs:
                            break
                        if allowed_types is not None and job.event_type not in allowed_types:
                            continue

                        enriched: tuple[list[CrdtEvent], TriageAssessment] | None = None
                        if job.event_type == EventType.VOICE_NOTE_RECORDED:
                            if not can_enrich_voice:
                                continue
                            enriched = self._enrich_single_voice_event(
                                job,
                                projected,
                                in_batch_triages,
                            )
                            if enriched is None:
                                skipped_missing_blob += 1
                                continue
                        elif job.event_type == EventType.TRIAGE_COMPLETED:
                            if not can_enrich_triage:
                                continue
                            enriched = self._enrich_single_triage_event(
                                job,
                                projected,
                                in_batch_triages,
                            )
                        else:
                            continue

                        emitted, triage_assessment = enriched
                        for evt in emitted:
                            if self._store.append(evt):
                                emitted_events += 1
                        if job.patient_id is not None:
                            prior = in_batch_triages.get(job.patient_id)
                            if prior is None or (
                                _SEVERITY_RANK[triage_assessment.severity]
                                >= _SEVERITY_RANK[prior.severity]
                            ):
                                in_batch_triages[job.patient_id] = triage_assessment
                        processed += 1
                        processed_event_ids.append(job.event_id)

            outbreak_events = self._run_outbreak_sweep()
            outbreak_alerts = len(outbreak_events)
            emitted_events += outbreak_alerts

            pending_remaining = len(self._store.get_pending_enrichments())
            summary = EnrichmentRunSummary(
                processed=processed,
                skipped_missing_blob=skipped_missing_blob,
                emitted_events=emitted_events,
                outbreak_alerts=outbreak_alerts,
                pending_remaining=pending_remaining,
                processed_event_ids=processed_event_ids,
            )

            with self._status_lock:
                self._total_runs += 1
                self._total_processed += processed
                self._total_emitted_events += emitted_events
                self._total_outbreak_alerts += outbreak_alerts
                self._last_run = summary
            return summary

    def get_status(self) -> EnrichmentWorkerStatus:
        """Return current worker status and cumulative telemetry."""
        with self._status_lock:
            active_stages = dict(self._active_stages)
            total_runs = self._total_runs
            total_processed = self._total_processed
            total_emitted_events = self._total_emitted_events
            total_outbreak_alerts = self._total_outbreak_alerts
            last_run = self._last_run

        return EnrichmentWorkerStatus(
            node_id=self._manifest.node_id,
            running=self.is_running,
            interval_sec=self._poll_interval_sec,
            pending_enrichments=len(self._store.get_pending_enrichments()),
            active_stages=active_stages,
            asr_target=route_workload(self._manifest, WorkloadKind.VOICE_ASR),
            slm_target=route_workload(self._manifest, WorkloadKind.CLINICAL_SLM_STRUCTURING),
            outbreak_target=route_workload(self._manifest, WorkloadKind.OUTBREAK_DETECTION),
            total_runs=total_runs,
            total_processed=total_processed,
            total_emitted_events=total_emitted_events,
            total_outbreak_alerts=total_outbreak_alerts,
            last_run=last_run,
        )

    async def _poll_loop(self, interval_sec: float) -> None:
        assert self._stop_event is not None
        while not self._stop_event.is_set():
            try:
                await asyncio.to_thread(self.run_once)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("EnrichmentWorker poll cycle failed; continuing loop.")
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=interval_sec)
            except TimeoutError:
                continue

    async def start(self, interval_sec: float | None = None) -> None:
        """Start the optional background asyncio polling loop (idempotent)."""
        if self.is_running:
            return
        resolved_interval = (
            float(interval_sec) if interval_sec is not None else self._poll_interval_sec
        )
        if resolved_interval <= 0:
            raise ValueError("interval_sec must be strictly positive.")
        self._poll_interval_sec = resolved_interval
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(
            self._poll_loop(resolved_interval),
            name=f"aarogya-enrichment-worker-{self._manifest.node_id}",
        )

    async def stop(self) -> None:
        """Stop and await the background asyncio polling loop cleanly."""
        if self._stop_event is not None:
            self._stop_event.set()
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        self._stop_event = None


def create_enrichment_router(worker: EnrichmentWorker) -> APIRouter:
    """Create a FastAPI router exposing enrichment trigger and status endpoints."""
    router = APIRouter(tags=["enrichment"])

    @router.post("/api/v1/enrichment/run", response_model=EnrichmentRunSummary)
    def run_enrichment() -> EnrichmentRunSummary:
        return worker.run_once()

    @router.post("/api/v1/enrichment/run-once", response_model=EnrichmentRunSummary)
    def run_enrichment_once() -> EnrichmentRunSummary:
        return worker.run_once()

    @router.get("/api/v1/enrichment/status", response_model=EnrichmentWorkerStatus)
    def get_enrichment_status() -> EnrichmentWorkerStatus:
        return worker.get_status()

    return router
