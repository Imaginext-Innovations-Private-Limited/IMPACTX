"""Contract serialization, JSON Schema Draft 2020-12, and invariant tests."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import jsonschema
import pytest
from jsonschema import Draft202012Validator
from pydantic import ValidationError

from aarogya_contracts import (
    CONTRACT_SCHEMA_VERSION,
    CORE_CONTRACT_MODELS,
    ActionCard,
    ActionCardPriority,
    ActionCardStatus,
    CrdtEvent,
    EnrichmentState,
    EventType,
    ExecutionTarget,
    HardwareCapabilityManifest,
    HlcTimestamp,
    NodeTier,
    PatientRecord,
    SyncEnvelope,
    TriageAssessment,
    TriageSeverity,
    VaccinationDueItem,
    VaccinationStatus,
    WatchMode,
)
from aarogya_contracts.export_schemas import (
    DEFAULT_SCHEMAS_DIR,
    JSON_SCHEMA_DRAFT_2020_12,
    check_exported_schemas,
)

TS_CONTRACT_PATH = Path(__file__).resolve().parents[1] / "ts" / "index.ts"


def _sample_instances() -> dict[str, object]:
    hlc = HlcTimestamp(wall_ms=1732350000000, logical=2, node_id="phone-asha-01")
    manifest = HardwareCapabilityManifest(
        node_id="phone-asha-01",
        tier=NodeTier.TIER_1_PHONE,
        ram_mb=4096,
        cpu_cores=8,
        battery_pct=84,
        has_npu=False,
        installed_models=["imnci-rules-v1"],
        watch_mode=None,
    )
    event = CrdtEvent(
        event_id="evt-001",
        hlc=hlc,
        origin_node_id="phone-asha-01",
        patient_id="pat-101",
        event_type=EventType.VOICE_NOTE_RECORDED,
        payload={"duration_sec": 18, "language": "hi", "audio_sha256": "abc123"},
        enrichment_state=EnrichmentState.PENDING,
        ref_event_id=None,
    )
    patient = PatientRecord(
        patient_id="pat-101",
        full_name="Meera Devi",
        date_of_birth=date(1998, 6, 15),
        age_months=341,
        sex="F",
        village_id="vil-rampur-01",
        household_id="hh-42",
        is_pregnant=True,
        gestational_weeks=28,
        preferred_language="hi",
        registered_by_node="phone-asha-01",
        metadata={"asha_id": "asha-07"},
    )
    triage = TriageAssessment(
        assessment_id="tri-001",
        patient_id="pat-101",
        severity=TriageSeverity.RED_EMERGENCY,
        matched_rules=["ANC_PREECLAMPSIA_SEVERE"],
        immediate_actions=["Immediate referral to PHC", "Monitor airway and BP"],
        referral_required=True,
        rationale="BP >= 140/90 with severe headache and blurred vision.",
        confidence=1.0,
        protocol_source="NHM_ASHA_ANC_DETERMINISTIC",
        execution_target=ExecutionTarget.LOCAL_DETERMINISTIC,
        assessed_at_ms=1732350001000,
    )
    vaccination = VaccinationDueItem(
        vaccine_code="PENTA-1",
        vaccine_name="Pentavalent-1 (DPT+HepB+Hib)",
        dose_label="6 weeks",
        due_date=date(2026, 11, 20),
        status=VaccinationStatus.OVERDUE,
        administered_date=None,
        days_delta=-3,
        reminder_text="Pentavalent-1 dose is overdue by 3 days.",
        schedule_group="UIP_INDIA",
    )
    card = ActionCard(
        card_id="card-001",
        patient_id="pat-101",
        title="Emergency PHC Referral",
        summary="Escort pregnant mother with pre-eclampsia danger signs to PHC immediately.",
        action_steps=["Arrange 108 ambulance", "Carry MCP card"],
        priority=ActionCardPriority.CRITICAL,
        severity=TriageSeverity.RED_EMERGENCY,
        status=ActionCardStatus.OPEN,
        target_tier=NodeTier.TIER_0_WATCH,
        watch_mode=WatchMode.CHW_COMPANION,
        source_event_id="evt-001",
        due_by=date(2026, 11, 23),
        language="en",
    )
    envelope = SyncEnvelope(
        envelope_id="env-001",
        sender_manifest=manifest,
        sender_hlc=hlc,
        since_cursor=None,
        next_cursor=hlc.to_sort_key(),
        events=[event],
        ack_event_ids=["evt-000"],
        schema_version=CONTRACT_SCHEMA_VERSION,
    )
    return {
        "HardwareCapabilityManifest": manifest,
        "HlcTimestamp": hlc,
        "CrdtEvent": event,
        "PatientRecord": patient,
        "TriageAssessment": triage,
        "VaccinationDueItem": vaccination,
        "ActionCard": card,
        "SyncEnvelope": envelope,
    }


def test_round_trip_json_serialization_for_all_core_contracts() -> None:
    samples = _sample_instances()
    assert set(samples.keys()) == set(CORE_CONTRACT_MODELS.keys())
    for name, model_cls in CORE_CONTRACT_MODELS.items():
        instance = samples[name]
        raw_json = instance.model_dump_json()
        restored = model_cls.model_validate_json(raw_json)
        assert restored == instance


def test_exported_schemas_match_pydantic_and_validate_samples() -> None:
    drift_errors = check_exported_schemas(DEFAULT_SCHEMAS_DIR)
    assert drift_errors == [], f"Schema drift detected: {drift_errors}"

    samples = _sample_instances()
    for name, instance in samples.items():
        schema_path = DEFAULT_SCHEMAS_DIR / f"{name}.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        assert schema["$schema"] == JSON_SCHEMA_DRAFT_2020_12
        Draft202012Validator.check_schema(schema)
        jsonschema.validate(
            instance=json.loads(instance.model_dump_json()),
            schema=schema,
            cls=Draft202012Validator,
        )


def test_hlc_total_ordering_and_sort_key() -> None:
    t1 = HlcTimestamp(wall_ms=1000, logical=0, node_id="node-a")
    t2 = HlcTimestamp(wall_ms=1000, logical=0, node_id="node-b")
    t3 = HlcTimestamp(wall_ms=1000, logical=1, node_id="node-a")
    t4 = HlcTimestamp(wall_ms=1001, logical=0, node_id="node-a")

    ordered = [t1, t2, t3, t4]
    assert sorted([t4, t2, t1, t3]) == ordered
    assert [t.to_sort_key() for t in ordered] == sorted(t.to_sort_key() for t in ordered)


def test_watch_mode_manifest_rules() -> None:
    watch = HardwareCapabilityManifest(
        node_id="watch-01",
        tier=NodeTier.TIER_0_WATCH,
        ram_mb=256,
        cpu_cores=2,
        battery_pct=70,
    )
    assert watch.watch_mode == WatchMode.CHW_COMPANION

    family_watch = HardwareCapabilityManifest(
        node_id="watch-02",
        tier=NodeTier.TIER_0_WATCH,
        ram_mb=256,
        cpu_cores=2,
        battery_pct=55,
        watch_mode=WatchMode.PATIENT_FAMILY,
    )
    assert family_watch.watch_mode == WatchMode.PATIENT_FAMILY

    with pytest.raises(ValidationError, match="watch_mode is only valid"):
        HardwareCapabilityManifest(
            node_id="hub-01",
            tier=NodeTier.TIER_2_HUB,
            ram_mb=32768,
            cpu_cores=16,
            watch_mode=WatchMode.CHW_COMPANION,
        )


def test_clinical_safety_red_emergency_requires_referral() -> None:
    with pytest.raises(ValidationError, match="RED_EMERGENCY"):
        TriageAssessment(
            severity=TriageSeverity.RED_EMERGENCY,
            matched_rules=["IMNCI_CONVULSIONS"],
            immediate_actions=["Stabilize airway"],
            referral_required=False,
            rationale="Active convulsions observed.",
        )


def test_enrichment_completed_requires_ref_event_id() -> None:
    hlc = HlcTimestamp(wall_ms=1732350000000, logical=0, node_id="hub-01")
    with pytest.raises(ValidationError, match="ref_event_id"):
        CrdtEvent(
            hlc=hlc,
            origin_node_id="hub-01",
            patient_id="pat-101",
            event_type=EventType.ENRICHMENT_COMPLETED,
            enrichment_state=EnrichmentState.COMPLETED,
        )

    valid = CrdtEvent(
        hlc=hlc,
        origin_node_id="hub-01",
        patient_id="pat-101",
        event_type=EventType.ENRICHMENT_COMPLETED,
        enrichment_state=EnrichmentState.COMPLETED,
        ref_event_id="evt-voice-01",
    )
    assert valid.ref_event_id == "evt-voice-01"


def test_strict_validation_rejects_extra_fields_and_invalid_bounds() -> None:
    with pytest.raises(ValidationError):
        HardwareCapabilityManifest(
            node_id="hub-01",
            tier=NodeTier.TIER_2_HUB,
            ram_mb=32768,
            cpu_cores=16,
            battery_pct=150,
        )

    with pytest.raises(ValidationError):
        PatientRecord(
            patient_id="pat-2",
            full_name="Test",
            village_id="vil-1",
            is_pregnant=False,
            gestational_weeks=12,
        )

    with pytest.raises(ValidationError):
        VaccinationDueItem(
            vaccine_code="BCG",
            vaccine_name="BCG",
            dose_label="Birth",
            due_date=date(2026, 1, 1),
            status=VaccinationStatus.COMPLETED,
            administered_date=None,
        )

    with pytest.raises(ValidationError):
        PatientRecord(
            patient_id="pat-3",
            full_name="Strict Check",
            village_id="vil-1",
            unexpected_field="nope",  # type: ignore[call-arg]
        )


def test_typescript_contracts_declare_all_core_interfaces() -> None:
    ts_source = TS_CONTRACT_PATH.read_text(encoding="utf-8")
    assert f'CONTRACT_SCHEMA_VERSION = "{CONTRACT_SCHEMA_VERSION}"' in ts_source
    for model_name in CORE_CONTRACT_MODELS:
        assert f"export interface {model_name} {{" in ts_source
    for enum_name in (
        "NodeTier",
        "WatchMode",
        "ExecutionTarget",
        "EventType",
        "EnrichmentState",
        "TriageSeverity",
        "VaccinationStatus",
        "ActionCardPriority",
        "ActionCardStatus",
    ):
        assert f"export type {enum_name} =" in ts_source
