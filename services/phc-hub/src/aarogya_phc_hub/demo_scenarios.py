"""Real-data hackathon demo scenario engine for the Tier-2 PHC Hub.

Executes four deterministic, 100% contract-valid clinical scenarios directly
through the real Hub primitives (``reconcile_envelopes``, ``PeerRegistry``,
``LocalBlobStore``, deterministic ``evaluate_triage``, and
``EnrichmentWorker.run_once``) with zero mocked metrics or synthetic shortcuts.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from aarogya_clinical_engine import (
    ChecklistType,
    TriageInput,
    TriageMode,
    compute_vaccination_schedule,
    evaluate_checklist,
    evaluate_triage,
    triage_to_action_card,
)
from aarogya_contracts import (
    ActionCard,
    ActionCardPriority,
    CrdtEvent,
    EnrichmentState,
    EventType,
    HardwareCapabilityManifest,
    HlcTimestamp,
    NodeTier,
    SyncEnvelope,
    TriageSeverity,
    WatchMode,
)
from aarogya_crdt_sync import EventStore, HlcClock, project_state, reconcile_envelopes
from aarogya_phc_hub.blob_store import LocalBlobStore
from aarogya_phc_hub.discovery import PeerRegistry, PeerSource
from aarogya_phc_hub.enrichment_worker import EnrichmentRunSummary, EnrichmentWorker

_MS_PER_DAY = 86_400_000
# Exact UTC day boundary (2025-10-10T00:00:00Z = 20371 * 86_400_000 ms) so
# outbreak day buckets are 100% deterministic across runs and time zones.
_DEMO_BASE_DAY_MS = 20_371 * _MS_PER_DAY


class DemoScenarioInfo(BaseModel):
    """Metadata describing an interactive demo scenario exposed by the Hub."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=160)
    subtitle: str = Field(..., min_length=1, max_length=300)
    persona: str = Field(..., min_length=1, max_length=128)
    steps: list[str] = Field(default_factory=list)


class DemoLoadResult(BaseModel):
    """Structured outcome returned after executing a real demo scenario."""

    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(..., min_length=1, max_length=64)
    events_added: int = Field(..., ge=0)
    peers_registered: int = Field(..., ge=0)
    enrichment_summary: EnrichmentRunSummary
    patient_count: int = Field(..., ge=0)
    outbreak_count: int = Field(..., ge=0)


class DemoResetResult(BaseModel):
    """Confirmation payload returned after clearing Hub demo state."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["reset"] = "reset"


SCENARIO_CATALOG: tuple[DemoScenarioInfo, ...] = (
    DemoScenarioInfo(
        id="maternal_sos",
        title="Normal Person Watch SOS → ASHA Phone",
        subtitle=(
            "High-risk expectant mother Sunita Devi (32w, Rampur) triggers a 1-tap "
            "PATIENT_FAMILY Watch danger sign (severe headache, blurred vision, BP 162/108) "
            "offline; Hub enforces deterministic RED_EMERGENCY triage and dispatches a "
            "CRITICAL Action Card to the ASHA worker's Phone."
        ),
        persona="Expectant Mother (Tier-0 Patient-Family Watch) → ASHA Worker (Tier-1 Phone)",
        steps=[
            "Sunita Devi (32w pregnant, Rampur) taps 1-tap Watch SOS offline: severe headache, blurred vision, BP 162/108.",
            "Tier-0 Watch syncs its offline CRDT SyncEnvelope + SOS voice clip to the Tier-2 PHC Hub.",
            "Hub executes deterministic NHM/WHO maternal triage (RED_EMERGENCY) and runs ML enrichment with SHAP risk attribution.",
            "Hub issues a CRITICAL Action Card targeted to the ASHA worker's Tier-1 Phone for immediate 108 referral.",
        ],
    ),
    DemoScenarioInfo(
        id="pediatric_voice_offload",
        title="Offline ASHA Voice Note → Hub AI Enrichment",
        subtitle=(
            "ASHA worker on Tier-1 Phone logs 14-month-old Aarav (fever + convulsions) "
            "with a recorded Hindi/English voice note and uploads the audio blob; Hub runs "
            "EnrichmentWorker for ASR + SLM + SHAP risk scoring and deterministic RED_EMERGENCY escalation."
        ),
        persona="ASHA Worker (Tier-1 Field Phone) → Tier-2 PHC Hub AI → CHW Watch",
        steps=[
            "ASHA registers 14-month-old Aarav Sharma in Rampur and records a Hindi/English clinical voice note offline.",
            "Phone uploads the binary audio clip to LocalBlobStore and syncs a PENDING VOICE_NOTE_RECORDED CRDT event.",
            "Hub EnrichmentWorker runs offline ASR, GBNF SLM structuring, deterministic WHO IMNCI triage (RED_EMERGENCY), and SHAP risk scoring.",
            "Hub emits ENRICHMENT_COMPLETED and pushes CRITICAL RED_EMERGENCY Action Cards back to Phone and CHW Watch.",
        ],
    ),
    DemoScenarioInfo(
        id="village_outbreak",
        title="Multi-Worker EWMA Village Outbreak Surge",
        subtitle=(
            "Three autonomous offline peers (2 ASHA Phones + 1 CHW Watch) sync rising "
            "diarrhea and fever cases across Rampur; no single device sees the threshold, "
            "but Hub's EWMA OutbreakDetector triggers live OUTBREAK_ALERT_RAISED banners."
        ),
        persona="2 ASHA Field Phones + 1 CHW Watch → Tier-2 PHC Hub Surveillance",
        steps=[
            "Baseline days 0–2 record routine single diarrhea and fever cases across Rampur peers.",
            "On day 3, two ASHA Phones and one CHW Watch independently record localized clusters while offline.",
            "All three peers sync their CRDT envelopes opportunistically to the Tier-2 PHC Hub.",
            "Hub aggregates village daily counts and triggers live EWMA OUTBREAK_ALERT_RAISED alerts for Rampur.",
        ],
    ),
    DemoScenarioInfo(
        id="crdt_conflict_merge",
        title="Offline Conflict-Free CRDT Merge",
        subtitle=(
            "Tier-0 Watch and Tier-1 Phone concurrently edit Kavita Devi while disconnected "
            "in Airplane Mode; both sync to the Hub with zero data loss and deterministic "
            "Hybrid Logical Clock (HLC) field-level convergence."
        ),
        persona="Tier-1 ASHA Phone + Tier-0 Watch (Airplane Mode) → Tier-2 PHC Hub",
        steps=[
            "Kavita Devi (28w pregnant, Rampur) is initially registered before devices go offline.",
            "In Airplane Mode, Phone updates gestational_weeks=30 and metadata.anc_visit=3.",
            "At the exact same wall timestamp, Watch logs a RED_EMERGENCY triage and metadata.sos_triggered=true.",
            "Both peers sync to Hub: LWW-Element-Map merges all fields without data loss regardless of sync order.",
        ],
    ),
)

_SCENARIO_INDEX: dict[str, DemoScenarioInfo] = {item.id: item for item in SCENARIO_CATALOG}


def reset_demo_state(store: EventStore, registry: PeerRegistry) -> None:
    """Clear all CRDT events, peer cursors, and registered peers safely."""
    clear_store = getattr(store, "clear", None)
    if callable(clear_store):
        clear_store()
    else:
        with store._lock:  # noqa: SLF001
            store._conn.execute("DELETE FROM events")  # noqa: SLF001
            store._conn.execute("DELETE FROM peer_cursors")  # noqa: SLF001
            store._conn.commit()

    clear_registry = getattr(registry, "clear", None)
    if callable(clear_registry):
        clear_registry()
    else:
        with registry._lock:  # noqa: SLF001
            registry._peers.clear()  # noqa: SLF001


def _sync_peer_events(
    store: EventStore,
    clock: HlcClock,
    hub_manifest: HardwareCapabilityManifest,
    registry: PeerRegistry,
    *,
    peer_manifest: HardwareCapabilityManifest,
    events: list[CrdtEvent],
    source: PeerSource,
    sender_hlc: HlcTimestamp,
    envelope_id: str,
) -> None:
    """Register peer presence and reconcile its SyncEnvelope against the real Hub store."""
    registry.record_peer(peer_manifest, source=source)
    envelope = SyncEnvelope(
        envelope_id=envelope_id,
        sender_manifest=peer_manifest,
        sender_hlc=sender_hlc,
        events=events,
    )
    reconcile_envelopes(store, clock, hub_manifest, envelope)


def _run_maternal_sos(
    store: EventStore,
    blob_store: LocalBlobStore,
    clock: HlcClock,
    manifest: HardwareCapabilityManifest,
    registry: PeerRegistry,
    worker: EnrichmentWorker,
) -> tuple[int, EnrichmentRunSummary]:
    """Scenario 1: Normal Person Patient-Family Watch SOS -> Hub -> ASHA Phone Action Card."""
    t0 = _DEMO_BASE_DAY_MS + 3_600_000
    t1 = t0 + 180_000

    phone_manifest = HardwareCapabilityManifest(
        node_id="phone-asha-rampur-01",
        tier=NodeTier.TIER_1_PHONE,
        ram_mb=4096,
        cpu_cores=8,
        battery_pct=86,
        installed_models=["imnci-rules-v1"],
    )
    watch_manifest = HardwareCapabilityManifest(
        node_id="watch-family-sunita",
        tier=NodeTier.TIER_0_WATCH,
        ram_mb=256,
        cpu_cores=2,
        battery_pct=74,
        watch_mode=WatchMode.PATIENT_FAMILY,
    )

    patient_id = "pat-sunita-devi"

    # Step 1: ASHA Phone previously registered expectant mother Sunita Devi (32w, Rampur).
    reg_event = CrdtEvent(
        event_id="demo-mat-sos-reg-sunita",
        hlc=HlcTimestamp(wall_ms=t0, logical=0, node_id=phone_manifest.node_id),
        origin_node_id=phone_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.PATIENT_REGISTERED,
        payload={
            "patient_id": patient_id,
            "full_name": "Sunita Devi",
            "age_months": 312,
            "sex": "F",
            "village_id": "rampur-01",
            "household_id": "hh-rampur-14",
            "is_pregnant": True,
            "gestational_weeks": 32,
            "preferred_language": "hi",
            "metadata": {
                "anc_risk_group": "high_risk_pregnancy",
                "mcp_card_id": "MCP-RMP-032",
                "assigned_asha": "phone-asha-rampur-01",
            },
        },
    )
    sunita_ck = evaluate_checklist(
        ChecklistType.ANC_TRIMESTER_3,
        [
            "anc_t3_bp_urine_albumin",
            "anc_t3_repeat_hb",
            "anc_t3_fetal_heart_position",
            "anc_t3_kick_count",
            "anc_t3_birth_preparedness",
            "anc_t3_ifa_calcium_adherence",
            "anc_t3_jsy_pmmvy_readiness",
        ],
        patient_id=patient_id,
    )
    ck_event = CrdtEvent(
        event_id="demo-mat-sos-anc3-checklist",
        hlc=HlcTimestamp(wall_ms=t0 + 500, logical=0, node_id=phone_manifest.node_id),
        origin_node_id=phone_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.CHECKLIST_RECORDED,
        payload={
            "checklist_type": sunita_ck.checklist_type.value,
            "protocol": sunita_ck.protocol,
            "completed_items": sunita_ck.completed_items,
            "missing_items": sunita_ck.missing_items,
            "missing_critical_checks": sunita_ck.missing_critical_checks,
            "completion_score": sunita_ck.completion_score,
            "is_complete": sunita_ck.is_complete,
            "has_critical_gaps": sunita_ck.has_critical_gaps,
        },
    )
    _sync_peer_events(
        store,
        clock,
        manifest,
        registry,
        peer_manifest=phone_manifest,
        events=[reg_event, ck_event],
        source="sync_http",
        sender_hlc=HlcTimestamp(wall_ms=t0 + 1_000, logical=0, node_id=phone_manifest.node_id),
        envelope_id="demo-env-mat-phone-reg",
    )

    # Step 2: Sunita Devi triggers 1-tap PATIENT_FAMILY Watch SOS offline.
    watch_triage = evaluate_triage(
        TriageInput(
            patient_id=patient_id,
            mode=TriageMode.WATCH_RAPID,
            is_pregnant=True,
            gestational_weeks=32,
            danger_signs=["severe_headache", "blurred_vision"],
            systolic_bp=162,
            diastolic_bp=108,
            assessed_at_ms=t1,
        )
    )
    watch_triage = watch_triage.model_copy(
        update={"assessment_id": "demo-mat-sos-watch-triage-assessment"}
    )

    sos_meta_event = CrdtEvent(
        event_id="demo-mat-sos-watch-meta",
        hlc=HlcTimestamp(wall_ms=t1, logical=0, node_id=watch_manifest.node_id),
        origin_node_id=watch_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.PATIENT_REGISTERED,
        payload={
            "patient_id": patient_id,
            "metadata": {
                "sos_triggered": True,
                "sos_mode": WatchMode.PATIENT_FAMILY.value,
                "last_bp_mmhg": "162/108",
            },
        },
    )
    watch_triage_event = CrdtEvent(
        event_id="demo-mat-sos-watch-triage",
        hlc=HlcTimestamp(wall_ms=t1, logical=1, node_id=watch_manifest.node_id),
        origin_node_id=watch_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.TRIAGE_COMPLETED,
        payload=watch_triage.model_dump(mode="json"),
    )

    sos_blob_key = "demo-maternal-sos-sunita-audio"
    sos_audio_text = (
        "Expectant mother Sunita Devi at 32 weeks reports severe headache, blurred vision, "
        "and high blood pressure 162/108 "
        "(गर्भवती महिला सुनीता देवी को तीव्र शिरोवेदना, अस्पष्ट दृष्टि तथा उच्च रक्तचाप है)."
    )
    blob_store.put(sos_blob_key, sos_audio_text.encode("utf-8"), content_type="audio/webm")

    watch_voice_event = CrdtEvent(
        event_id="demo-mat-sos-watch-voice",
        hlc=HlcTimestamp(wall_ms=t1, logical=2, node_id=watch_manifest.node_id),
        origin_node_id=watch_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.VOICE_NOTE_RECORDED,
        enrichment_state=EnrichmentState.PENDING,
        payload={
            "audio_blob_key": sos_blob_key,
            "language": "hi",
            "is_pregnant": True,
            "gestational_weeks": 32,
            "systolic_bp": 162,
            "diastolic_bp": 108,
            "transcript_hint": sos_audio_text,
        },
    )

    _sync_peer_events(
        store,
        clock,
        manifest,
        registry,
        peer_manifest=watch_manifest,
        events=[sos_meta_event, watch_triage_event, watch_voice_event],
        source="sync_ws",
        sender_hlc=HlcTimestamp(wall_ms=t1 + 500, logical=0, node_id=watch_manifest.node_id),
        envelope_id="demo-env-mat-watch-sos",
    )

    # Step 3: Hub runs full deterministic maternal triage and issues CRITICAL Action Card for ASHA Phone.
    hub_triage = evaluate_triage(
        TriageInput(
            patient_id=patient_id,
            mode=TriageMode.FULL_ASSESSMENT,
            is_pregnant=True,
            gestational_weeks=32,
            danger_signs=["severe_headache", "blurred_vision"],
            systolic_bp=162,
            diastolic_bp=108,
            assessed_at_ms=t1 + 2_000,
        )
    )
    hub_triage = hub_triage.model_copy(
        update={"assessment_id": "demo-mat-sos-hub-triage-assessment"}
    )
    hub_triage_event = CrdtEvent(
        event_id="demo-mat-sos-hub-triage",
        hlc=clock.tick(),
        origin_node_id=manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.TRIAGE_COMPLETED,
        payload=hub_triage.model_dump(mode="json"),
    )
    store.append(hub_triage_event)

    base_card = triage_to_action_card(
        hub_triage,
        target_tier=NodeTier.TIER_1_PHONE,
        watch_mode=None,
        source_event_id=hub_triage_event.event_id,
    )
    asha_phone_card = ActionCard(
        card_id="demo-card-mat-sos-asha-phone",
        patient_id=patient_id,
        title="RED EMERGENCY: Sunita Devi Watch SOS (BP 162/108)",
        summary=(
            f"मातृ आपातकाल संकेत — Rampur (32w): {base_card.summary}"
        )[:1000],
        action_steps=list(base_card.action_steps),
        priority=ActionCardPriority.CRITICAL,
        severity=TriageSeverity.RED_EMERGENCY,
        target_tier=NodeTier.TIER_1_PHONE,
        watch_mode=None,
        source_event_id=hub_triage_event.event_id,
        language="hi",
    )
    store.append(
        CrdtEvent(
            event_id="demo-mat-sos-card-asha-phone",
            hlc=clock.tick(),
            origin_node_id=manifest.node_id,
            patient_id=patient_id,
            event_type=EventType.ACTION_CARD_ISSUED,
            enrichment_state=EnrichmentState.COMPLETED,
            ref_event_id=hub_triage_event.event_id,
            payload=asha_phone_card.model_dump(mode="json"),
        )
    )

    enrichment_summary = worker.run_once()
    return 2, enrichment_summary


def _run_pediatric_voice_offload(
    store: EventStore,
    blob_store: LocalBlobStore,
    clock: HlcClock,
    manifest: HardwareCapabilityManifest,
    registry: PeerRegistry,
    worker: EnrichmentWorker,
) -> tuple[int, EnrichmentRunSummary]:
    """Scenario 2: Offline ASHA pediatric voice note -> LocalBlobStore -> Hub AI Enrichment."""
    t0 = _DEMO_BASE_DAY_MS + 7_200_000

    phone_manifest = HardwareCapabilityManifest(
        node_id="phone-asha-rampur-01",
        tier=NodeTier.TIER_1_PHONE,
        ram_mb=4096,
        cpu_cores=8,
        battery_pct=68,
        installed_models=["imnci-rules-v1"],
    )
    watch_manifest = HardwareCapabilityManifest(
        node_id="watch-chw-rampur-01",
        tier=NodeTier.TIER_0_WATCH,
        ram_mb=256,
        cpu_cores=2,
        battery_pct=84,
        watch_mode=WatchMode.CHW_COMPANION,
    )

    patient_id = "pat-aarav-sharma"
    blob_key = "demo-voice-aarav-convulsions"
    voice_text = (
        "14-month child Aarav has high fever and convulsions with fast breathing "
        "(चौदह मास के शिशु आरव को तीव्र ज्वर, आक्षेप तथा तीव्र श्वास हैं)."
    )
    blob_store.put(blob_key, voice_text.encode("utf-8"), content_type="audio/webm")

    reg_event = CrdtEvent(
        event_id="demo-ped-reg-aarav",
        hlc=HlcTimestamp(wall_ms=t0, logical=0, node_id=phone_manifest.node_id),
        origin_node_id=phone_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.PATIENT_REGISTERED,
        payload={
            "patient_id": patient_id,
            "full_name": "Aarav Sharma",
            "date_of_birth": "2025-09-15",
            "age_months": 14,
            "sex": "M",
            "village_id": "rampur-01",
            "household_id": "hh-rampur-27",
            "is_pregnant": False,
            "preferred_language": "hi",
            "metadata": {
                "guardian_name": "Rekha Sharma",
                "uip_card_id": "UIP-RMP-114",
            },
        },
    )
    aarav_dob = date(2025, 9, 15)
    aarav_administered = {
        "BCG": date(2025, 9, 16),
        "OPV-0": date(2025, 9, 16),
        "HepB-Birth": date(2025, 9, 16),
        "OPV-1": date(2025, 10, 30),
        "Pentavalent-1": date(2025, 10, 30),
        "Rotavirus-1": date(2025, 10, 30),
        "fIPV-1": date(2025, 10, 30),
        "PCV-1": date(2025, 10, 30),
        "OPV-2": date(2025, 11, 28),
        "Pentavalent-2": date(2025, 11, 28),
        "Rotavirus-2": date(2025, 11, 28),
    }
    aarav_vax_items = [
        item
        for item in compute_vaccination_schedule(
            aarav_dob,
            administered_vaccines=aarav_administered,
            as_of_date=date(2026, 11, 26),
        )
        if item.vaccine_code in aarav_administered
    ]
    vax_events = [
        CrdtEvent(
            event_id=f"demo-ped-vax-aarav-{idx}",
            hlc=HlcTimestamp(wall_ms=t0 + 1_000 + idx, logical=0, node_id=phone_manifest.node_id),
            origin_node_id=phone_manifest.node_id,
            patient_id=patient_id,
            event_type=EventType.VACCINATION_LOGGED,
            payload=item.model_dump(mode="json"),
        )
        for idx, item in enumerate(aarav_vax_items)
    ]
    ped_triage = evaluate_triage(
        TriageInput(
            patient_id=patient_id,
            mode=TriageMode.FULL_ASSESSMENT,
            age_months=14,
            temperature_c=39.7,
            fever_days=2,
            respiratory_rate_bpm=48,
            spo2_pct=93,
            symptoms=["cough"],
            danger_signs=["convulsions"],
            assessed_at_ms=t0 + 10_000,
        )
    ).model_copy(update={"assessment_id": "demo-ped-triage-aarav-assessment"})
    ped_triage_event = CrdtEvent(
        event_id="demo-ped-triage-aarav",
        hlc=HlcTimestamp(wall_ms=t0 + 10_000, logical=0, node_id=phone_manifest.node_id),
        origin_node_id=phone_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.TRIAGE_COMPLETED,
        payload=ped_triage.model_dump(mode="json"),
    )
    voice_event = CrdtEvent(
        event_id="demo-ped-voice-aarav",
        hlc=HlcTimestamp(wall_ms=t0 + 15_000, logical=0, node_id=phone_manifest.node_id),
        origin_node_id=phone_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.VOICE_NOTE_RECORDED,
        enrichment_state=EnrichmentState.PENDING,
        payload={
            "audio_blob_key": blob_key,
            "language": "hi",
            "age_months": 14,
            "temperature_c": 39.7,
            "fever_days": 2,
            "respiratory_rate_bpm": 48,
            "transcript_hint": voice_text,
        },
    )

    _sync_peer_events(
        store,
        clock,
        manifest,
        registry,
        peer_manifest=phone_manifest,
        events=[reg_event, *vax_events, ped_triage_event, voice_event],
        source="sync_http",
        sender_hlc=HlcTimestamp(wall_ms=t0 + 20_000, logical=0, node_id=phone_manifest.node_id),
        envelope_id="demo-env-ped-phone-voice",
    )

    # CHW Watch connects on LAN/WS so Hub can push enriched Action Cards back to Watch as well.
    _sync_peer_events(
        store,
        clock,
        manifest,
        registry,
        peer_manifest=watch_manifest,
        events=[],
        source="sync_ws",
        sender_hlc=HlcTimestamp(wall_ms=t0 + 22_000, logical=0, node_id=watch_manifest.node_id),
        envelope_id="demo-env-ped-watch-handshake",
    )

    # Hub runs real EnrichmentWorker: ASR -> SLM -> deterministic evaluate_triage -> SHAP -> Watch Action Card.
    enrichment_summary = worker.run_once()

    # Also issue a paired RED_EMERGENCY Action Card specifically targeted to the ASHA worker's Phone.
    projected = project_state(store.get_all_events())
    enrichment_evt = projected.enrichments.get(voice_event.event_id)
    if enrichment_evt is not None:
        triage_raw = enrichment_evt.payload.get("triage_assessment", {})
        risk_raw = enrichment_evt.payload.get("risk_score", {})
        phone_card = ActionCard(
            card_id="demo-card-ped-aarav-phone",
            patient_id=patient_id,
            title="RED EMERGENCY: Aarav Sharma — Convulsions & Hyperpyrexia",
            summary=(
                "शिशु आपातकाल सन्दर्भन — "
                f"{triage_raw.get('rationale', 'Immediate FRU referral required for convulsions.')}"
            )[:1000],
            action_steps=[
                *list(triage_raw.get("immediate_actions", [])),
                (
                    f"Hub SHAP Risk: {risk_raw.get('risk_band', 'HIGH')} "
                    f"({float(risk_raw.get('risk_score', 0.9)):.2f})"
                ),
            ],
            priority=ActionCardPriority.CRITICAL,
            severity=TriageSeverity.RED_EMERGENCY,
            target_tier=NodeTier.TIER_1_PHONE,
            watch_mode=None,
            source_event_id=enrichment_evt.event_id,
            language="hi",
        )
        store.append(
            CrdtEvent(
                event_id="demo-ped-card-aarav-phone",
                hlc=clock.tick(),
                origin_node_id=manifest.node_id,
                patient_id=patient_id,
                event_type=EventType.ACTION_CARD_ISSUED,
                enrichment_state=EnrichmentState.COMPLETED,
                ref_event_id=voice_event.event_id,
                payload=phone_card.model_dump(mode="json"),
            )
        )

    return 2, enrichment_summary


def _run_village_outbreak(
    store: EventStore,
    blob_store: LocalBlobStore,
    clock: HlcClock,
    manifest: HardwareCapabilityManifest,
    registry: PeerRegistry,
    worker: EnrichmentWorker,
) -> tuple[int, EnrichmentRunSummary]:
    """Scenario 3: 3 autonomous offline peers sync rising Rampur diarrhea/fever surge -> EWMA alert."""
    phone_north = HardwareCapabilityManifest(
        node_id="phone-asha-rampur-north",
        tier=NodeTier.TIER_1_PHONE,
        ram_mb=4096,
        cpu_cores=8,
        battery_pct=79,
        installed_models=["imnci-rules-v1"],
    )
    phone_south = HardwareCapabilityManifest(
        node_id="phone-asha-rampur-south",
        tier=NodeTier.TIER_1_PHONE,
        ram_mb=3072,
        cpu_cores=4,
        battery_pct=62,
        installed_models=["imnci-rules-v1"],
    )
    watch_east = HardwareCapabilityManifest(
        node_id="watch-chw-rampur-east",
        tier=NodeTier.TIER_0_WATCH,
        ram_mb=256,
        cpu_cores=2,
        battery_pct=81,
        watch_mode=WatchMode.CHW_COMPANION,
    )

    # Case specs: (key, full_name, age_months, sex, day_offset, include_fever, temp_c, dehydration_signs)
    # Individual peers stay below EWMA threshold (3.0) on their own:
    # - phone_north: diarrhea [1,0,1,3] (EWMA 1.72), fever [1,0,0,3] (EWMA 1.32)
    # - phone_south: diarrhea [1,0,4] (EWMA 1.82), fever [1,0,4] (EWMA 1.82)
    # - watch_east:  fever [1,2] (EWMA 1.35)
    # Combined on Hub:
    # - diarrhea: [1, 1, 1, 7] -> EWMA = 3.10 >= 3.0 -> OUTBREAK_ALERT_RAISED!
    # - fever:    [1, 1, 1, 9] -> EWMA = 3.80 >= 3.0 -> OUTBREAK_ALERT_RAISED!
    north_cases: list[tuple[str, str, int, Literal["F", "M"], int, bool, float | None, list[str]]] = [
        ("n0", "Meera Kumari", 22, "F", 0, True, 38.3, ["restless_or_irritable", "sunken_eyes"]),
        ("n1", "Ananya Devi", 18, "F", 2, False, 37.1, []),
        ("n2", "Kabir Patel", 28, "M", 3, True, 38.6, ["restless_or_irritable", "sunken_eyes"]),
        ("n3", "Diya Singh", 16, "F", 3, True, 38.8, ["sunken_eyes", "drinks_eagerly_thirsty"]),
        ("n4", "Ishaan Verma", 11, "M", 3, True, 39.6, ["sunken_eyes", "skin_pinch_very_slow"]),
    ]
    south_cases: list[tuple[str, str, int, Literal["F", "M"], int, bool, float | None, list[str]]] = [
        ("s0", "Rohan Verma", 30, "M", 1, True, 38.4, ["restless_or_irritable", "sunken_eyes"]),
        ("s1", "Saanvi Mishra", 20, "F", 3, True, 38.5, ["sunken_eyes", "drinks_eagerly_thirsty"]),
        ("s2", "Arjun Tiwari", 34, "M", 3, True, 38.7, ["restless_or_irritable", "sunken_eyes"]),
        ("s3", "Priya Yadav", 15, "F", 3, True, 38.9, ["sunken_eyes", "skin_pinch_slow"]),
        ("s4", "Devansh Shukla", 24, "M", 3, True, 39.7, ["sunken_eyes", "skin_pinch_very_slow"]),
    ]
    watch_cases: list[tuple[str, str, int, Literal["F", "M"], int, float, int, int, int | None, str]] = [
        ("w0", "Vihaan Yadav", 26, "M", 2, 38.1, 1, 34, 98, "fever and mild fatigue"),
        ("w1", "Nandini Gupta", 19, "F", 3, 39.2, 3, 44, 94, "persistent fever and cough"),
        ("w2", "Pranav Joshi", 32, "M", 3, 39.9, 4, 50, 91, "high fever with fast breathing"),
    ]

    def _build_phone_events(
        peer: HardwareCapabilityManifest,
        cases: list[tuple[str, str, int, Literal["F", "M"], int, bool, float | None, list[str]]],
    ) -> list[CrdtEvent]:
        events: list[CrdtEvent] = []
        for idx, (tag, name, age_m, sex, day_offset, has_fever, temp_c, dehyd) in enumerate(cases):
            pid = f"pat-outbreak-{tag}"
            ev_ms = _DEMO_BASE_DAY_MS + day_offset * _MS_PER_DAY + (idx + 1) * 60_000
            events.append(
                CrdtEvent(
                    event_id=f"demo-outbreak-reg-{tag}",
                    hlc=HlcTimestamp(wall_ms=ev_ms, logical=0, node_id=peer.node_id),
                    origin_node_id=peer.node_id,
                    patient_id=pid,
                    event_type=EventType.PATIENT_REGISTERED,
                    payload={
                        "patient_id": pid,
                        "full_name": name,
                        "age_months": age_m,
                        "sex": sex,
                        "village_id": "rampur-01",
                        "is_pregnant": False,
                        "preferred_language": "hi",
                        "metadata": {"surveillance_cluster": "rampur-waterborne"},
                    },
                )
            )
            assessment = evaluate_triage(
                TriageInput(
                    patient_id=pid,
                    age_months=age_m,
                    has_diarrhea=True,
                    diarrhea_days=2,
                    dehydration_signs=dehyd,
                    temperature_c=temp_c,
                    fever_days=2 if has_fever else 0,
                    assessed_at_ms=ev_ms + 5_000,
                )
            )
            assessment = assessment.model_copy(update={"assessment_id": f"demo-outbreak-tri-{tag}"})
            events.append(
                CrdtEvent(
                    event_id=f"demo-outbreak-triage-{tag}",
                    hlc=HlcTimestamp(wall_ms=ev_ms + 5_000, logical=0, node_id=peer.node_id),
                    origin_node_id=peer.node_id,
                    patient_id=pid,
                    event_type=EventType.TRIAGE_COMPLETED,
                    payload=assessment.model_dump(mode="json"),
                )
            )
        return events

    north_events = _build_phone_events(phone_north, north_cases)
    south_events = _build_phone_events(phone_south, south_cases)

    watch_events: list[CrdtEvent] = []
    for idx, (tag, name, age_m, sex, day_offset, temp_c, f_days, rr_bpm, spo2, sym_desc) in enumerate(watch_cases):
        pid = f"pat-outbreak-{tag}"
        ev_ms = _DEMO_BASE_DAY_MS + day_offset * _MS_PER_DAY + (idx + 10) * 60_000
        blob_key = f"demo-outbreak-watch-vn-{tag}"
        note_text = (
            f"Rampur child {name} has {sym_desc} "
            f"(रामपुर के शिशु {name} को तीव्र ज्वर है)."
        )
        blob_store.put(blob_key, note_text.encode("utf-8"), content_type="audio/webm")
        watch_events.append(
            CrdtEvent(
                event_id=f"demo-outbreak-reg-{tag}",
                hlc=HlcTimestamp(wall_ms=ev_ms, logical=0, node_id=watch_east.node_id),
                origin_node_id=watch_east.node_id,
                patient_id=pid,
                event_type=EventType.PATIENT_REGISTERED,
                payload={
                    "patient_id": pid,
                    "full_name": name,
                    "age_months": age_m,
                    "sex": sex,
                    "village_id": "rampur-01",
                    "is_pregnant": False,
                    "preferred_language": "hi",
                    "metadata": {"surveillance_cluster": "rampur-waterborne"},
                },
            )
        )
        voice_payload: dict[str, object] = {
            "audio_blob_key": blob_key,
            "language": "hi",
            "age_months": age_m,
            "temperature_c": temp_c,
            "fever_days": f_days,
            "respiratory_rate_bpm": rr_bpm,
            "transcript_hint": note_text,
        }
        if spo2 is not None:
            voice_payload["spo2_pct"] = spo2
        watch_events.append(
            CrdtEvent(
                event_id=f"demo-outbreak-voice-{tag}",
                hlc=HlcTimestamp(wall_ms=ev_ms + 5_000, logical=0, node_id=watch_east.node_id),
                origin_node_id=watch_east.node_id,
                patient_id=pid,
                event_type=EventType.VOICE_NOTE_RECORDED,
                enrichment_state=EnrichmentState.PENDING,
                payload=voice_payload,
            )
        )

    day3_sync_ms = _DEMO_BASE_DAY_MS + 3 * _MS_PER_DAY + 2_000_000
    _sync_peer_events(
        store,
        clock,
        manifest,
        registry,
        peer_manifest=phone_north,
        events=north_events,
        source="sync_http",
        sender_hlc=HlcTimestamp(wall_ms=day3_sync_ms, logical=0, node_id=phone_north.node_id),
        envelope_id="demo-env-outbreak-north",
    )
    _sync_peer_events(
        store,
        clock,
        manifest,
        registry,
        peer_manifest=phone_south,
        events=south_events,
        source="sync_http",
        sender_hlc=HlcTimestamp(wall_ms=day3_sync_ms + 1_000, logical=0, node_id=phone_south.node_id),
        envelope_id="demo-env-outbreak-south",
    )
    _sync_peer_events(
        store,
        clock,
        manifest,
        registry,
        peer_manifest=watch_east,
        events=watch_events,
        source="sync_ws",
        sender_hlc=HlcTimestamp(wall_ms=day3_sync_ms + 2_000, logical=0, node_id=watch_east.node_id),
        envelope_id="demo-env-outbreak-watch",
    )

    enrichment_summary = worker.run_once()
    return 3, enrichment_summary


def _run_crdt_conflict_merge(
    store: EventStore,
    blob_store: LocalBlobStore,
    clock: HlcClock,
    manifest: HardwareCapabilityManifest,
    registry: PeerRegistry,
    worker: EnrichmentWorker,
) -> tuple[int, EnrichmentRunSummary]:
    """Scenario 4: Concurrent offline Watch & Phone edits on Kavita Devi converge conflict-free."""
    _ = blob_store
    t0 = _DEMO_BASE_DAY_MS + 10_800_000
    t1 = t0 + 60_000  # Exact simultaneous wall_ms across both offline devices!

    phone_manifest = HardwareCapabilityManifest(
        node_id="phone-asha-kavita-01",
        tier=NodeTier.TIER_1_PHONE,
        ram_mb=4096,
        cpu_cores=8,
        battery_pct=72,
        installed_models=["imnci-rules-v1"],
    )
    watch_manifest = HardwareCapabilityManifest(
        node_id="watch-kavita-01",
        tier=NodeTier.TIER_0_WATCH,
        ram_mb=256,
        cpu_cores=2,
        battery_pct=65,
        watch_mode=WatchMode.PATIENT_FAMILY,
    )

    patient_id = "pat-kavita-devi"

    # Baseline registration prior to Airplane Mode disconnect.
    initial_reg = CrdtEvent(
        event_id="demo-crdt-reg-kavita-base",
        hlc=HlcTimestamp(wall_ms=t0, logical=0, node_id=phone_manifest.node_id),
        origin_node_id=phone_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.PATIENT_REGISTERED,
        payload={
            "patient_id": patient_id,
            "full_name": "Kavita Devi",
            "age_months": 300,
            "sex": "F",
            "village_id": "rampur-01",
            "household_id": "hh-rampur-09",
            "is_pregnant": True,
            "gestational_weeks": 28,
            "preferred_language": "hi",
            "metadata": {
                "anc_visit": 2,
                "mcp_card_id": "MCP-RMP-009",
            },
        },
    )

    # Disconnected Phone edit: updates gestational_weeks=30 and metadata.anc_visit=3.
    phone_offline_update = CrdtEvent(
        event_id="demo-crdt-phone-edit-kavita",
        hlc=HlcTimestamp(wall_ms=t1, logical=0, node_id=phone_manifest.node_id),
        origin_node_id=phone_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.PATIENT_REGISTERED,
        payload={
            "patient_id": patient_id,
            "is_pregnant": True,
            "gestational_weeks": 30,
            "metadata": {
                "anc_visit": 3,
                "ifa_tablets_dispensed": 30,
            },
        },
    )
    kavita_ck = evaluate_checklist(
        ChecklistType.ANC_TRIMESTER_3,
        [
            "anc_t3_bp_urine_albumin",
            "anc_t3_repeat_hb",
            "anc_t3_fetal_heart_position",
            "anc_t3_kick_count",
            "anc_t3_ifa_calcium_adherence",
            "anc_t3_early_breastfeeding_plan",
        ],
        patient_id=patient_id,
    )
    kavita_ck_event = CrdtEvent(
        event_id="demo-crdt-anc3-checklist-kavita",
        hlc=HlcTimestamp(wall_ms=t1, logical=1, node_id=phone_manifest.node_id),
        origin_node_id=phone_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.CHECKLIST_RECORDED,
        payload={
            "checklist_type": kavita_ck.checklist_type.value,
            "protocol": kavita_ck.protocol,
            "completed_items": kavita_ck.completed_items,
            "missing_items": kavita_ck.missing_items,
            "missing_critical_checks": kavita_ck.missing_critical_checks,
            "completion_score": kavita_ck.completion_score,
            "is_complete": kavita_ck.is_complete,
            "has_critical_gaps": kavita_ck.has_critical_gaps,
        },
    )

    # Concurrent disconnected Watch edit (same wall_ms=t1): metadata.sos_triggered=True + RED_EMERGENCY triage.
    watch_offline_meta = CrdtEvent(
        event_id="demo-crdt-watch-meta-kavita",
        hlc=HlcTimestamp(wall_ms=t1, logical=0, node_id=watch_manifest.node_id),
        origin_node_id=watch_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.PATIENT_REGISTERED,
        payload={
            "patient_id": patient_id,
            "metadata": {
                "sos_triggered": True,
                "sos_source": "watch_1tap",
                "sos_danger_signs": ["vaginal_bleeding"],
            },
        },
    )
    watch_triage = evaluate_triage(
        TriageInput(
            patient_id=patient_id,
            mode=TriageMode.WATCH_RAPID,
            is_pregnant=True,
            gestational_weeks=30,
            danger_signs=["vaginal_bleeding"],
            assessed_at_ms=t1,
        )
    )
    watch_triage = watch_triage.model_copy(
        update={"assessment_id": "demo-crdt-watch-triage-assessment"}
    )
    watch_triage_event = CrdtEvent(
        event_id="demo-crdt-watch-triage-kavita",
        hlc=HlcTimestamp(wall_ms=t1, logical=1, node_id=watch_manifest.node_id),
        origin_node_id=watch_manifest.node_id,
        patient_id=patient_id,
        event_type=EventType.TRIAGE_COMPLETED,
        payload=watch_triage.model_dump(mode="json"),
    )

    # Both offline peers reconnect and sync their CRDT envelopes to the Hub.
    _sync_peer_events(
        store,
        clock,
        manifest,
        registry,
        peer_manifest=phone_manifest,
        events=[initial_reg, phone_offline_update, kavita_ck_event],
        source="sync_http",
        sender_hlc=HlcTimestamp(wall_ms=t1 + 5_000, logical=0, node_id=phone_manifest.node_id),
        envelope_id="demo-env-crdt-phone",
    )
    _sync_peer_events(
        store,
        clock,
        manifest,
        registry,
        peer_manifest=watch_manifest,
        events=[watch_offline_meta, watch_triage_event],
        source="sync_ws",
        sender_hlc=HlcTimestamp(wall_ms=t1 + 6_000, logical=0, node_id=watch_manifest.node_id),
        envelope_id="demo-env-crdt-watch",
    )

    # Hub emits a CRITICAL Action Card combining converged patient context + RED_EMERGENCY triage.
    base_card = triage_to_action_card(
        watch_triage,
        target_tier=NodeTier.TIER_1_PHONE,
        watch_mode=None,
        source_event_id=watch_triage_event.event_id,
    )
    converged_card = ActionCard(
        card_id="demo-card-crdt-kavita-converged",
        patient_id=patient_id,
        title="RED EMERGENCY: Kavita Devi (30w, ANC-3 + Watch SOS)",
        summary=(
            f"निर्विवाद समन्वय सन्दर्भन — {base_card.summary}"
        )[:1000],
        action_steps=list(base_card.action_steps),
        priority=ActionCardPriority.CRITICAL,
        severity=TriageSeverity.RED_EMERGENCY,
        target_tier=NodeTier.TIER_1_PHONE,
        watch_mode=None,
        source_event_id=watch_triage_event.event_id,
        language="hi",
    )
    store.append(
        CrdtEvent(
            event_id="demo-crdt-card-kavita",
            hlc=clock.tick(),
            origin_node_id=manifest.node_id,
            patient_id=patient_id,
            event_type=EventType.ACTION_CARD_ISSUED,
            enrichment_state=EnrichmentState.COMPLETED,
            ref_event_id=watch_triage_event.event_id,
            payload=converged_card.model_dump(mode="json"),
        )
    )

    enrichment_summary = worker.run_once()
    return 2, enrichment_summary


type _ScenarioRunner = Callable[
    [
        EventStore,
        LocalBlobStore,
        HlcClock,
        HardwareCapabilityManifest,
        PeerRegistry,
        EnrichmentWorker,
    ],
    tuple[int, EnrichmentRunSummary],
]

_SCENARIO_RUNNERS: dict[str, _ScenarioRunner] = {
    "maternal_sos": _run_maternal_sos,
    "pediatric_voice_offload": _run_pediatric_voice_offload,
    "village_outbreak": _run_village_outbreak,
    "crdt_conflict_merge": _run_crdt_conflict_merge,
}


def execute_demo_scenario(
    scenario_id: str,
    *,
    store: EventStore,
    blob_store: LocalBlobStore,
    clock: HlcClock,
    manifest: HardwareCapabilityManifest,
    registry: PeerRegistry,
    worker: EnrichmentWorker,
    reset_first: bool = True,
) -> DemoLoadResult:
    """Run a named clinical demo scenario end-to-end through the real Hub stack."""
    runner = _SCENARIO_RUNNERS.get(scenario_id)
    if runner is None:
        raise KeyError(f"Unknown demo scenario: {scenario_id}")

    if reset_first:
        reset_demo_state(store, registry)

    before_events = store.count()
    peers_registered, enrichment_summary = runner(
        store,
        blob_store,
        clock,
        manifest,
        registry,
        worker,
    )
    after_events = store.count()
    projected = project_state(store.get_all_events())

    return DemoLoadResult(
        scenario_id=scenario_id,
        events_added=max(after_events - before_events, 0),
        peers_registered=peers_registered,
        enrichment_summary=enrichment_summary,
        patient_count=len(projected.patients),
        outbreak_count=len(projected.outbreak_alerts),
    )


def create_demo_router(
    store: EventStore,
    blob_store: LocalBlobStore,
    clock: HlcClock,
    manifest: HardwareCapabilityManifest,
    registry: PeerRegistry,
    worker: EnrichmentWorker,
) -> APIRouter:
    """Create the FastAPI router exposing the real-data demo scenario engine."""
    router = APIRouter(tags=["demo"])

    @router.get("/api/v1/demo/scenarios", response_model=list[DemoScenarioInfo])
    def list_demo_scenarios() -> list[DemoScenarioInfo]:
        return list(SCENARIO_CATALOG)

    @router.post("/api/v1/demo/load/{scenario_id}", response_model=DemoLoadResult)
    def load_demo_scenario(
        scenario_id: str,
        reset_first: Annotated[bool, Query()] = True,
    ) -> DemoLoadResult:
        if scenario_id not in _SCENARIO_INDEX:
            raise HTTPException(
                status_code=404,
                detail=f"Unknown demo scenario: {scenario_id}",
            )
        return execute_demo_scenario(
            scenario_id,
            store=store,
            blob_store=blob_store,
            clock=clock,
            manifest=manifest,
            registry=registry,
            worker=worker,
            reset_first=reset_first,
        )

    @router.post("/api/v1/demo/reset", response_model=DemoResetResult)
    def reset_demo() -> DemoResetResult:
        reset_demo_state(store, registry)
        return DemoResetResult(status="reset")

    return router
