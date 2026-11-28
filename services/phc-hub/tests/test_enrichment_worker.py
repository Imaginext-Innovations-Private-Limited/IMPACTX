"""Unit and API tests for the Tier-2 PHC Hub background enrichment worker."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aarogya_clinical_engine import TriageInput, evaluate_triage
from aarogya_contracts import (
    ActionCard,
    ActionCardPriority,
    CrdtEvent,
    EnrichmentState,
    EventType,
    ExecutionTarget,
    HardwareCapabilityManifest,
    HlcTimestamp,
    NodeTier,
    TriageAssessment,
    TriageSeverity,
    WatchMode,
)
from aarogya_crdt_sync import EventStore, HlcClock, project_state
from aarogya_ml_pipeline import (
    RISK_FEATURE_NAMES,
    EwmaOutbreakDetector,
    LightGbmRiskScorer,
    LlamaCppSlmStructurer,
    RiskScoreResult,
    StructuredClinicalNote,
    TranscriptionResult,
    WhisperVoiceTranscriber,
)
from aarogya_phc_hub.blob_store import LocalBlobStore
from aarogya_phc_hub.enrichment_worker import (
    EnrichmentRunSummary,
    EnrichmentWorker,
    EnrichmentWorkerStatus,
    create_enrichment_router,
)

_BASE_DAY_MS = 1_700_000_000_000  # Fixed deterministic epoch base
_MS_PER_DAY = 86_400_000


def _make_hub_manifest(
    node_id: str = "phc-hub-01",
    *,
    ram_mb: int = 32768,
    cpu_cores: int = 16,
) -> HardwareCapabilityManifest:
    return HardwareCapabilityManifest(
        node_id=node_id,
        tier=NodeTier.TIER_2_HUB,
        ram_mb=ram_mb,
        cpu_cores=cpu_cores,
        battery_pct=100,
    )


def _register_patient(
    store: EventStore,
    *,
    patient_id: str,
    full_name: str = "Aarav Kumar",
    village_id: str = "rampur-01",
    age_months: int | None = 18,
    is_pregnant: bool = False,
    wall_ms: int = _BASE_DAY_MS,
) -> None:
    payload: dict[str, object] = {
        "patient_id": patient_id,
        "full_name": full_name,
        "village_id": village_id,
        "sex": "F" if is_pregnant else "M",
        "is_pregnant": is_pregnant,
        "preferred_language": "en",
    }
    if age_months is not None:
        payload["age_months"] = age_months
    if is_pregnant:
        payload["gestational_weeks"] = 28

    store.append(
        CrdtEvent(
            event_id=f"evt-reg-{patient_id}",
            hlc=HlcTimestamp(wall_ms=wall_ms, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id=patient_id,
            event_type=EventType.PATIENT_REGISTERED,
            payload=payload,
        )
    )


def test_voice_note_with_uploaded_blob_enriches_and_drains_pending(tmp_path: Path) -> None:
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-01")
    manifest = _make_hub_manifest()

    _register_patient(store, patient_id="pat-001", age_months=24)
    blob_store.put(
        "vn-pat-001",
        b"Child has fever and cough for 2 days.",
        content_type="audio/webm",
    )

    voice_evt = CrdtEvent(
        event_id="evt-voice-001",
        hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 1_000, logical=0, node_id="phone-asha-01"),
        origin_node_id="phone-asha-01",
        patient_id="pat-001",
        event_type=EventType.VOICE_NOTE_RECORDED,
        enrichment_state=EnrichmentState.PENDING,
        payload={"audio_blob_key": "vn-pat-001", "language": "en"},
    )
    store.append(voice_evt)
    assert len(store.get_pending_enrichments()) == 1

    worker = EnrichmentWorker(store, blob_store, clock, manifest)
    summary = worker.run_once()

    assert summary.processed == 1
    assert summary.skipped_missing_blob == 0
    assert summary.emitted_events == 2
    assert summary.outbreak_alerts == 0
    assert summary.pending_remaining == 0
    assert summary.processed_event_ids == ["evt-voice-001"]
    assert store.get_pending_enrichments() == []

    projected = project_state(store.get_all_events())
    assert projected.pending_enrichments == []
    assert "evt-voice-001" in projected.enrichments

    enrichment_evt = projected.enrichments["evt-voice-001"]
    assert enrichment_evt.event_type == EventType.ENRICHMENT_COMPLETED
    assert enrichment_evt.enrichment_state == EnrichmentState.COMPLETED
    assert enrichment_evt.ref_event_id == "evt-voice-001"
    assert enrichment_evt.payload["audio_source"] == "blob"
    assert enrichment_evt.payload["audio_blob_key"] == "vn-pat-001"
    assert "fever" in enrichment_evt.payload["structured_note"]["extracted_symptoms"]

    triage = TriageAssessment.model_validate(enrichment_evt.payload["triage_assessment"])
    assert triage.execution_target == ExecutionTarget.LOCAL_DETERMINISTIC
    assert triage.confidence == 1.0

    cards = projected.action_cards_for_patient("pat-001")
    assert len(cards) == 1
    card = ActionCard.model_validate(cards[0].model_dump(mode="json"))
    assert card.source_event_id == enrichment_evt.event_id
    assert card.severity == triage.severity
    assert card.target_tier == NodeTier.TIER_0_WATCH


def test_hinted_voice_note_with_missing_blob_defers_until_audio_arrives(tmp_path: Path) -> None:
    """Issue A regression: hinted note with audio_blob_key waits for real audio instead of
    permanently completing on the preliminary hint; hint-only notes (no blob key) run immediately.
    """
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-01")
    manifest = _make_hub_manifest()

    # 1) Voice note with BOTH audio_blob_key and preliminary transcript_hint (audio not uploaded yet).
    store.append(
        CrdtEvent(
            event_id="evt-voice-hinted-waiting",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 2_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-002",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={
                "audio_blob_key": "vn-arrives-after-sync",
                "transcript_hint": "Preliminary note before audio upload.",
                "language": "en",
            },
        )
    )
    # 2) Typed-only note with NO audio_blob_key — should process transcript_hint immediately.
    store.append(
        CrdtEvent(
            event_id="evt-voice-typed-only",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 2_500, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-002b",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={
                "transcript_hint": "Patient reports mild fever and cough.",
                "language": "en",
            },
        )
    )

    worker = EnrichmentWorker(store, blob_store, clock, manifest)
    first_run = worker.run_once()

    assert first_run.processed == 1
    assert first_run.processed_event_ids == ["evt-voice-typed-only"]
    assert first_run.skipped_missing_blob == 1
    assert first_run.pending_remaining == 1

    state_after_first = project_state(store.get_all_events())
    assert "evt-voice-typed-only" in state_after_first.enrichments
    assert state_after_first.enrichments["evt-voice-typed-only"].payload["audio_source"] == "transcript_hint"
    assert "evt-voice-hinted-waiting" not in state_after_first.enrichments

    # Real audio blob finishes uploading — next sweep must enrich from real audio, NOT the stale hint.
    blob_store.put(
        "vn-arrives-after-sync",
        b"Child had a convulsion and high fever.",
        content_type="audio/webm",
    )
    second_run = worker.run_once()
    assert second_run.processed == 1
    assert second_run.processed_event_ids == ["evt-voice-hinted-waiting"]
    assert second_run.skipped_missing_blob == 0
    assert second_run.pending_remaining == 0

    state_after_second = project_state(store.get_all_events())
    enrichment_evt = state_after_second.enrichments["evt-voice-hinted-waiting"]
    assert enrichment_evt.payload["audio_source"] == "blob"
    assert enrichment_evt.payload["audio_blob_key"] == "vn-arrives-after-sync"
    triage = TriageAssessment.model_validate(enrichment_evt.payload["triage_assessment"])
    assert triage.severity == TriageSeverity.RED_EMERGENCY
    assert triage.referral_required is True


def test_missing_blob_without_hint_defers_gracefully_until_uploaded(tmp_path: Path) -> None:
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-01")
    manifest = _make_hub_manifest()

    voice_evt = CrdtEvent(
        event_id="evt-voice-deferred",
        hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 3_000, logical=0, node_id="phone-asha-01"),
        origin_node_id="phone-asha-01",
        patient_id="pat-003",
        event_type=EventType.VOICE_NOTE_RECORDED,
        enrichment_state=EnrichmentState.PENDING,
        payload={"audio_blob_key": "vn-arrives-later", "language": "en"},
    )
    store.append(voice_evt)

    worker = EnrichmentWorker(store, blob_store, clock, manifest)

    first_run = worker.run_once()
    assert first_run.processed == 0
    assert first_run.skipped_missing_blob == 1
    assert first_run.emitted_events == 0
    assert first_run.pending_remaining == 1
    assert len(store.get_pending_enrichments()) == 1

    # Peer finishes uploading audio blob; next sweep enriches cleanly.
    blob_store.put("vn-arrives-later", b"Child has cough.", content_type="audio/ogg")
    second_run = worker.run_once()
    assert second_run.processed == 1
    assert second_run.skipped_missing_blob == 0
    assert second_run.emitted_events == 2
    assert second_run.pending_remaining == 0


def test_invalid_blob_key_fails_soft_without_crashing(tmp_path: Path) -> None:
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-01")
    manifest = _make_hub_manifest()

    store.append(
        CrdtEvent(
            event_id="evt-bad-blob-key",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 4_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-004",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"audio_blob_key": "../etc/passwd", "language": "en"},
        )
    )

    worker = EnrichmentWorker(store, blob_store, clock, manifest)
    summary = worker.run_once()
    assert summary.processed == 0
    assert summary.skipped_missing_blob == 1
    assert summary.pending_remaining == 1


def test_clinical_safety_floor_forces_red_emergency_on_danger_signs(tmp_path: Path) -> None:
    """Verify deterministic evaluate_triage owns TriageSeverity even if SLM minimizes text."""

    class _DownplayingSlm:
        def structure_note(self, transcript: str, language: str = "en") -> StructuredClinicalNote:
            return StructuredClinicalNote(
                extracted_symptoms=["fever", "convulsions"],
                candidate_danger_flags=["convulsions"],
                recommended_follow_up="Looks minor, rest at home.",
                language=language,
                backend="test-downplaying-slm",
            )

    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-01")
    manifest = _make_hub_manifest()

    _register_patient(store, patient_id="pat-red-1", age_months=12)
    blob_store.put("vn-convulsion", b"Child had a convulsion and high fever", content_type="audio/wav")

    store.append(
        CrdtEvent(
            event_id="evt-voice-red-1",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 5_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-red-1",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"audio_blob_key": "vn-convulsion", "language": "en"},
        )
    )

    # Also test default StubClinicalSlmStructurer with lethargy and maternal bleeding.
    store.append(
        CrdtEvent(
            event_id="evt-voice-red-lethargy",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 6_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-red-2",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"transcript_hint": "Infant is very lethargic and has fever.", "language": "en"},
        )
    )
    store.append(
        CrdtEvent(
            event_id="evt-voice-red-bleeding",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 7_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-red-3",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"transcript_hint": "Mother has heavy bleeding.", "language": "en"},
        )
    )

    # First run only pat-red-1 with the downplaying SLM? Better: test downplaying SLM on its own store,
    # and default stub SLM on lethargy + bleeding!
    store_custom = EventStore(":memory:")
    _register_patient(store_custom, patient_id="pat-red-1", age_months=12)
    store_custom.append(
        CrdtEvent(
            event_id="evt-voice-red-custom",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 5_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-red-1",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"audio_blob_key": "vn-convulsion", "language": "en"},
        )
    )

    custom_worker = EnrichmentWorker(
        store_custom,
        blob_store,
        HlcClock("phc-hub-01"),
        manifest,
        structurer=_DownplayingSlm(),
    )
    custom_summary = custom_worker.run_once()
    assert custom_summary.processed == 1

    custom_state = project_state(store_custom.get_all_events())
    custom_enr = custom_state.enrichments["evt-voice-red-custom"]
    custom_triage = TriageAssessment.model_validate(custom_enr.payload["triage_assessment"])
    assert custom_triage.severity == TriageSeverity.RED_EMERGENCY
    assert custom_triage.referral_required is True
    assert custom_triage.execution_target == ExecutionTarget.LOCAL_DETERMINISTIC
    assert "IMNCI_GDS_03" in custom_triage.matched_rules

    custom_cards = custom_state.action_cards_for_patient("pat-red-1")
    assert len(custom_cards) == 1
    assert custom_cards[0].severity == TriageSeverity.RED_EMERGENCY
    assert custom_cards[0].priority == ActionCardPriority.CRITICAL

    # Now verify default StubClinicalSlmStructurer + evaluate_triage on all 3 danger signs.
    default_worker = EnrichmentWorker(store, blob_store, clock, manifest)
    default_summary = default_worker.run_once()
    assert default_summary.processed == 3

    default_state = project_state(store.get_all_events())
    for evt_id, pid in [
        ("evt-voice-red-1", "pat-red-1"),
        ("evt-voice-red-lethargy", "pat-red-2"),
        ("evt-voice-red-bleeding", "pat-red-3"),
    ]:
        triage = TriageAssessment.model_validate(
            default_state.enrichments[evt_id].payload["triage_assessment"]
        )
        assert triage.severity == TriageSeverity.RED_EMERGENCY
        assert triage.referral_required is True
        cards = default_state.action_cards_for_patient(pid)
        assert len(cards) == 1
        assert cards[0].severity == TriageSeverity.RED_EMERGENCY
        assert cards[0].priority == ActionCardPriority.CRITICAL


def test_idempotency_second_run_emits_zero_duplicates(tmp_path: Path) -> None:
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-01")
    manifest = _make_hub_manifest()

    blob_store.put("vn-idem-1", b"Patient reports cough.", content_type="audio/webm")
    store.append(
        CrdtEvent(
            event_id="evt-voice-idem-1",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 10_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-idem-1",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"audio_blob_key": "vn-idem-1", "language": "en"},
        )
    )

    worker = EnrichmentWorker(store, blob_store, clock, manifest)
    first = worker.run_once()
    count_after_first = store.count()

    second = worker.run_once()
    assert first.processed == 1
    assert first.emitted_events == 2
    assert second.processed == 0
    assert second.skipped_missing_blob == 0
    assert second.emitted_events == 0
    assert second.outbreak_alerts == 0
    assert second.pending_remaining == 0
    assert store.count() == count_after_first


def test_outbreak_alert_emitted_on_village_surge_and_deduplicated(tmp_path: Path) -> None:
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-01")
    manifest = _make_hub_manifest()

    # Days 0, 1, 2: baseline 1 fever case/day; Day 3: sudden spike of 7 fever cases in rampur-01
    # (EWMA = 0.35 * 7 + 0.65 * 1 = 3.10 >= threshold 3.0).
    day_schedule = [0, 1, 2, 3, 3, 3, 3, 3, 3, 3]
    for idx, day_offset in enumerate(day_schedule):
        pid = f"pat-surge-{idx}"
        event_ms = _BASE_DAY_MS + day_offset * _MS_PER_DAY + idx * 1_000
        _register_patient(store, patient_id=pid, village_id="rampur-01", wall_ms=event_ms - 500)
        store.append(
            CrdtEvent(
                event_id=f"evt-voice-surge-{idx}",
                hlc=HlcTimestamp(wall_ms=event_ms, logical=0, node_id="phone-asha-01"),
                origin_node_id="phone-asha-01",
                patient_id=pid,
                event_type=EventType.VOICE_NOTE_RECORDED,
                enrichment_state=EnrichmentState.PENDING,
                payload={"transcript_hint": "Patient has high fever.", "language": "en"},
            )
        )

    worker = EnrichmentWorker(store, blob_store, clock, manifest)
    first = worker.run_once()
    assert first.processed == len(day_schedule)
    assert first.outbreak_alerts == 1
    assert first.pending_remaining == 0

    projected = project_state(store.get_all_events())
    assert len(projected.outbreak_alerts) == 1
    alert = projected.outbreak_alerts[0]
    assert alert.event_type == EventType.OUTBREAK_ALERT_RAISED
    assert alert.payload["village_id"] == "rampur-01"
    assert alert.payload["syndrome"] == "fever"
    assert alert.payload["alert_triggered"] is True
    assert alert.payload["severity"] == TriageSeverity.RED_EMERGENCY.value
    assert alert.payload["daily_counts"] == [1, 1, 1, 7]

    # Second run must NOT emit duplicate outbreak alerts.
    second = worker.run_once()
    assert second.processed == 0
    assert second.outbreak_alerts == 0
    assert second.emitted_events == 0
    assert len(project_state(store.get_all_events()).outbreak_alerts) == 1


def test_capability_router_prevents_watch_or_low_ram_enrichment(tmp_path: Path) -> None:
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("watch-01")
    watch_manifest = HardwareCapabilityManifest(
        node_id="watch-01",
        tier=NodeTier.TIER_0_WATCH,
        ram_mb=256,
        cpu_cores=2,
        watch_mode=WatchMode.CHW_COMPANION,
    )

    store.append(
        CrdtEvent(
            event_id="evt-voice-watch",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS, logical=0, node_id="watch-01"),
            origin_node_id="watch-01",
            patient_id="pat-w1",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"transcript_hint": "Fever and cough", "language": "en"},
        )
    )

    worker = EnrichmentWorker(store, blob_store, clock, watch_manifest)
    summary = worker.run_once()
    assert summary.processed == 0
    assert summary.emitted_events == 0
    assert summary.pending_remaining == 1


def test_enrichment_router_and_background_loop(tmp_path: Path) -> None:
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-api")
    manifest = _make_hub_manifest("phc-hub-api")

    store.append(
        CrdtEvent(
            event_id="evt-voice-api-1",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 20_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-api-1",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"transcript_hint": "Fever and cough", "language": "en"},
        )
    )

    worker = EnrichmentWorker(store, blob_store, clock, manifest, poll_interval_sec=2.0)
    app = FastAPI()
    app.include_router(create_enrichment_router(worker))
    client = TestClient(app)

    status_before = EnrichmentWorkerStatus.model_validate(
        client.get("/api/v1/enrichment/status").json()
    )
    assert status_before.node_id == "phc-hub-api"
    assert status_before.running is False
    assert status_before.pending_enrichments == 1
    assert status_before.total_runs == 0

    run_resp = client.post("/api/v1/enrichment/run")
    assert run_resp.status_code == 200
    run_summary = EnrichmentRunSummary.model_validate(run_resp.json())
    assert run_summary.processed == 1
    assert run_summary.emitted_events == 2
    assert run_summary.pending_remaining == 0

    # Alias endpoint /run-once also works and is idempotent.
    run_once_resp = client.post("/api/v1/enrichment/run-once")
    assert run_once_resp.status_code == 200
    run_once_summary = EnrichmentRunSummary.model_validate(run_once_resp.json())
    assert run_once_summary.processed == 0
    assert run_once_summary.emitted_events == 0

    status_after = EnrichmentWorkerStatus.model_validate(
        client.get("/api/v1/enrichment/status").json()
    )
    assert status_after.pending_enrichments == 0
    assert status_after.total_runs == 2
    assert status_after.total_processed == 1
    assert status_after.last_run is not None

    # Verify async background loop starts, drains newly arrived voice note, and stops cleanly.
    async def _exercise_loop() -> None:
        store.append(
            CrdtEvent(
                event_id="evt-voice-loop-1",
                hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 30_000, logical=0, node_id="phone-asha-01"),
                origin_node_id="phone-asha-01",
                patient_id="pat-loop-1",
                event_type=EventType.VOICE_NOTE_RECORDED,
                enrichment_state=EnrichmentState.PENDING,
                payload={"transcript_hint": "Child has fever.", "language": "en"},
            )
        )
        await worker.start(interval_sec=0.05)
        assert worker.is_running is True
        # Idempotent second start does not spawn duplicate tasks.
        await worker.start(interval_sec=0.05)
        for _ in range(40):
            if len(store.get_pending_enrichments()) == 0:
                break
            await asyncio.sleep(0.025)
        await worker.stop()
        assert worker.is_running is False

    asyncio.run(_exercise_loop())
    assert store.get_pending_enrichments() == []
    assert "evt-voice-loop-1" in project_state(store.get_all_events()).enrichments


def test_voice_enrichment_preserves_existing_red_and_yellow_triage_floor(tmp_path: Path) -> None:
    """Issue B regression: enriching a routine voice note must never emit a GREEN card
    for a patient already triaged RED_EMERGENCY or YELLOW_PHC.
    """
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-01")
    manifest = _make_hub_manifest()

    # Patient 1: Child just triaged RED_EMERGENCY for convulsions.
    _register_patient(store, patient_id="pat-active-red", age_months=14)
    red_triage = evaluate_triage(
        TriageInput(
            patient_id="pat-active-red",
            age_months=14,
            danger_signs=["convulsions"],
            assessed_at_ms=_BASE_DAY_MS + 1_000,
        )
    )
    assert red_triage.severity == TriageSeverity.RED_EMERGENCY
    store.append(
        CrdtEvent(
            event_id="evt-triage-active-red",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 1_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-active-red",
            event_type=EventType.TRIAGE_COMPLETED,
            payload=red_triage.model_dump(mode="json"),
        )
    )
    # Subsequent benign voice note with no danger keywords.
    store.append(
        CrdtEvent(
            event_id="evt-voice-after-red",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 5_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-active-red",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={
                "transcript_hint": "Child resting quietly while waiting for ambulance.",
                "language": "en",
            },
        )
    )

    # Patient 2: Child triaged YELLOW_PHC (fast breathing / pneumonia), followed by routine note.
    _register_patient(store, patient_id="pat-active-yellow", age_months=20)
    yellow_triage = evaluate_triage(
        TriageInput(
            patient_id="pat-active-yellow",
            age_months=20,
            respiratory_rate_bpm=48,
            assessed_at_ms=_BASE_DAY_MS + 2_000,
        )
    )
    assert yellow_triage.severity == TriageSeverity.YELLOW_PHC
    store.append(
        CrdtEvent(
            event_id="evt-triage-active-yellow",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 2_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-active-yellow",
            event_type=EventType.TRIAGE_COMPLETED,
            payload=yellow_triage.model_dump(mode="json"),
        )
    )
    store.append(
        CrdtEvent(
            event_id="evt-voice-after-yellow",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 6_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-active-yellow",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={
                "transcript_hint": "Mother preparing to visit clinic.",
                "language": "en",
            },
        )
    )

    worker = EnrichmentWorker(store, blob_store, clock, manifest)
    summary = worker.run_once()
    assert summary.processed == 2

    projected = project_state(store.get_all_events())

    red_enr = projected.enrichments["evt-voice-after-red"]
    red_enr_triage = TriageAssessment.model_validate(red_enr.payload["triage_assessment"])
    assert red_enr_triage.severity == TriageSeverity.RED_EMERGENCY
    assert red_enr_triage.referral_required is True
    assert "IMNCI_GDS_03" in red_enr_triage.matched_rules
    assert "CLINICAL_ROUTINE_GREEN" not in red_enr_triage.matched_rules

    red_cards = projected.action_cards_for_patient("pat-active-red")
    assert len(red_cards) == 1
    assert red_cards[0].severity == TriageSeverity.RED_EMERGENCY
    assert red_cards[0].priority == ActionCardPriority.CRITICAL
    assert red_cards[0].title.startswith("RED EMERGENCY")
    assert all("No danger signs" not in step for step in red_cards[0].action_steps)

    yellow_cards = projected.action_cards_for_patient("pat-active-yellow")
    assert len(yellow_cards) == 1
    assert yellow_cards[0].severity == TriageSeverity.YELLOW_PHC
    assert yellow_cards[0].priority == ActionCardPriority.HIGH


def test_three_notes_and_stub_binary_audio_do_not_spam_outbreak_alerts(tmp_path: Path) -> None:
    """Issue C regression: 3 routine voice notes (including binary WebM clips hitting
    StubVoiceTranscriber's placeholder text) must NOT trigger false outbreak alerts.
    """
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-01")
    manifest = _make_hub_manifest()

    # Case 1: 3 distinct patients with opaque binary WebM audio on the same day.
    for idx in range(3):
        pid = f"pat-bin-{idx}"
        blob_key = f"vn-bin-{idx}"
        _register_patient(store, patient_id=pid, village_id="demo-village-a", wall_ms=_BASE_DAY_MS)
        blob_store.put(blob_key, b"\x1a\x45\xdf\xa3\x00\xff\xfe\xfd-webm-audio", content_type="audio/webm")
        store.append(
            CrdtEvent(
                event_id=f"evt-voice-bin-{idx}",
                hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + (idx + 1) * 1_000, logical=0, node_id="phone-asha-01"),
                origin_node_id="phone-asha-01",
                patient_id=pid,
                event_type=EventType.VOICE_NOTE_RECORDED,
                enrichment_state=EnrichmentState.PENDING,
                payload={"audio_blob_key": blob_key, "language": "en"},
            )
        )

    # Case 2: 3 distinct patients with real printable text mentioning fever & cough on 1 day.
    for idx in range(3):
        pid = f"pat-txt-{idx}"
        _register_patient(store, patient_id=pid, village_id="demo-village-b", wall_ms=_BASE_DAY_MS)
        store.append(
            CrdtEvent(
                event_id=f"evt-voice-txt-{idx}",
                hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + (idx + 10) * 1_000, logical=0, node_id="phone-asha-01"),
                origin_node_id="phone-asha-01",
                patient_id=pid,
                event_type=EventType.VOICE_NOTE_RECORDED,
                enrichment_state=EnrichmentState.PENDING,
                payload={"transcript_hint": "Patient reports fever and cough.", "language": "en"},
            )
        )

    # Case 3: 5 voice notes for the SAME patient on the same day -> deduplicated to 1 case.
    _register_patient(store, patient_id="pat-repeat", village_id="demo-village-c", wall_ms=_BASE_DAY_MS)
    for idx in range(5):
        store.append(
            CrdtEvent(
                event_id=f"evt-voice-repeat-{idx}",
                hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + (idx + 20) * 1_000, logical=0, node_id="phone-asha-01"),
                origin_node_id="phone-asha-01",
                patient_id="pat-repeat",
                event_type=EventType.VOICE_NOTE_RECORDED,
                enrichment_state=EnrichmentState.PENDING,
                payload={"transcript_hint": "Patient still has fever.", "language": "en"},
            )
        )

    worker = EnrichmentWorker(store, blob_store, clock, manifest)
    summary = worker.run_once()

    assert summary.processed == 11
    assert summary.outbreak_alerts == 0
    assert project_state(store.get_all_events()).outbreak_alerts == []


def test_default_worker_wires_real_ml_pipeline_backends(tmp_path: Path) -> None:
    """T1-04 Part 2: default EnrichmentWorker uses real aarogya_ml_pipeline adapters."""
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-real-ml")
    manifest = _make_hub_manifest("phc-hub-real-ml")

    worker = EnrichmentWorker(store, blob_store, clock, manifest)
    assert isinstance(worker._transcriber, WhisperVoiceTranscriber)
    assert isinstance(worker._structurer, LlamaCppSlmStructurer)
    assert isinstance(worker._risk_scorer, LightGbmRiskScorer)
    assert isinstance(worker._outbreak_detector, EwmaOutbreakDetector)
    assert worker._outbreak_detector.alpha == 0.35
    assert worker._outbreak_detector.min_baseline_days == 3

    _register_patient(store, patient_id="pat-healthy-check", age_months=30)
    store.append(
        CrdtEvent(
            event_id="evt-voice-healthy-check",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 40_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-healthy-check",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={
                "transcript_hint": "Routine child follow-up, child is eating well.",
                "language": "en",
                "temperature_c": 36.8,
                "spo2_pct": 99,
                "respiratory_rate_bpm": 26,
            },
        )
    )

    summary = worker.run_once()
    assert summary.processed == 1
    projected = project_state(store.get_all_events())
    enr = projected.enrichments["evt-voice-healthy-check"]
    assert enr.payload["transcription"]["backend"] in ("whisper-int8-cpu", "stub-asr-fallback")
    assert enr.payload["structured_note"]["backend"] in (
        "llama-cpp-qwen2.5-3b-gbnf",
        "stub-slm-fallback",
    )
    assert enr.payload["risk_score"]["backend"] in ("lightgbm-treeshap", "stub-lightgbm-fallback")
    # Healthy child with normal vitals must not saturate risk score in fallback mode.
    assert enr.payload["risk_score"]["risk_band"] == "LOW"
    assert enr.payload["risk_score"]["risk_score"] < 0.35


def test_risk_features_strictly_conform_to_canonical_risk_feature_names(tmp_path: Path) -> None:
    """T1-04 Part 2: risk scorer receives canonical RISK_FEATURE_NAMES without stray keys."""
    captured_features: list[dict[str, float | int | bool]] = []

    class _SpyRiskScorer:
        def score_risk(self, features: dict[str, float | int | bool]) -> RiskScoreResult:
            captured_features.append(dict(features))
            return RiskScoreResult(
                risk_score=0.42,
                risk_band="MODERATE",
                shap_attributions={"fever_days": 0.16},
                backend="spy-risk-scorer",
            )

    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-features")
    manifest = _make_hub_manifest("phc-hub-features")

    _register_patient(store, patient_id="pat-feat-1", age_months=16)
    store.append(
        CrdtEvent(
            event_id="evt-voice-feat-1",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 50_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-feat-1",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={
                "transcript_hint": "Child has fever and cough.",
                "language": "en",
                "fever_days": 3,
                "temperature_c": 38.6,
                "respiratory_rate_bpm": 44,
                "spo2_pct": 95,
                "systolic_bp": 95,
                "diastolic_bp": 60,
                "hemoglobin_g_dl": 10.2,
                "muac_cm": 12.1,
            },
        )
    )

    worker = EnrichmentWorker(
        store,
        blob_store,
        clock,
        manifest,
        risk_scorer=_SpyRiskScorer(),
    )
    summary = worker.run_once()
    assert summary.processed == 1
    assert len(captured_features) == 1

    feats = captured_features[0]
    assert set(feats.keys()).issubset(set(RISK_FEATURE_NAMES))
    assert feats["age_months"] == 16
    assert feats["fever_days"] == 3
    assert feats["temperature_c"] == 38.6
    assert feats["respiratory_rate_bpm"] == 44
    assert feats["spo2_pct"] == 95
    assert feats["systolic_bp"] == 95
    assert feats["diastolic_bp"] == 60
    assert feats["hemoglobin_g_dl"] == 10.2
    assert feats["muac_cm"] == 12.1
    assert feats["is_pregnant"] is False
    assert feats["has_danger_sign"] is False
    assert feats["symptom_count"] >= 2


def test_active_stages_tracks_progress_and_status_endpoint_while_running(tmp_path: Path) -> None:
    """Verify active_stages updates per stage during enrichment and is readable via GET /status."""
    transcribe_entered = threading.Event()
    transcribe_release = threading.Event()
    structure_entered = threading.Event()
    structure_release = threading.Event()
    risk_entered = threading.Event()
    risk_release = threading.Event()

    class _PausedTranscriber:
        def transcribe(self, audio_bytes: bytes, language_hint: str | None = None) -> TranscriptionResult:
            transcribe_entered.set()
            assert transcribe_release.wait(timeout=5.0)
            return TranscriptionResult(
                transcript="Child has fever and cough.",
                language=language_hint or "en",
                confidence=0.95,
                backend="test-paused-asr",
            )

    class _PausedStructurer:
        def structure_note(self, transcript: str, language: str = "en") -> StructuredClinicalNote:
            structure_entered.set()
            assert structure_release.wait(timeout=5.0)
            return StructuredClinicalNote(
                extracted_symptoms=["fever", "cough"],
                candidate_danger_flags=[],
                recommended_follow_up="Follow up at PHC.",
                language=language,
                backend="test-paused-slm",
            )

    class _PausedRiskScorer:
        def score_risk(self, features: dict[str, float | int | bool]) -> RiskScoreResult:
            risk_entered.set()
            assert risk_release.wait(timeout=5.0)
            return RiskScoreResult(
                risk_score=0.25,
                risk_band="LOW",
                shap_attributions={"fever_days": 0.1},
                backend="test-paused-risk",
            )

    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-stages")
    manifest = _make_hub_manifest("phc-hub-stages")

    _register_patient(store, patient_id="pat-stages-1", age_months=24)
    store.append(
        CrdtEvent(
            event_id="evt-voice-stages-1",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 60_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-stages-1",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"transcript_hint": "Child has fever and cough.", "language": "en"},
        )
    )

    worker = EnrichmentWorker(
        store,
        blob_store,
        clock,
        manifest,
        transcriber=_PausedTranscriber(),
        structurer=_PausedStructurer(),
        risk_scorer=_PausedRiskScorer(),
    )
    app = FastAPI()
    app.include_router(create_enrichment_router(worker))
    client = TestClient(app)

    initial_status = client.get("/api/v1/enrichment/status")
    assert initial_status.status_code == 200
    assert initial_status.json()["active_stages"] == {}

    results: list[EnrichmentRunSummary] = []
    worker_thread = threading.Thread(target=lambda: results.append(worker.run_once()), daemon=True)
    worker_thread.start()

    try:
        assert transcribe_entered.wait(timeout=5.0)
        assert worker.active_stages == {"evt-voice-stages-1": "transcribing_audio"}
        resp = client.get("/api/v1/enrichment/status")
        assert resp.status_code == 200
        assert resp.json()["active_stages"] == {"evt-voice-stages-1": "transcribing_audio"}
        transcribe_release.set()

        assert structure_entered.wait(timeout=5.0)
        assert worker.active_stages == {"evt-voice-stages-1": "structuring_note"}
        resp = client.get("/api/v1/enrichment/status")
        assert resp.status_code == 200
        assert resp.json()["active_stages"] == {"evt-voice-stages-1": "structuring_note"}
        structure_release.set()

        assert risk_entered.wait(timeout=5.0)
        assert worker.active_stages == {"evt-voice-stages-1": "scoring_risk"}
        resp = client.get("/api/v1/enrichment/status")
        assert resp.status_code == 200
        assert resp.json()["active_stages"] == {"evt-voice-stages-1": "scoring_risk"}
        risk_release.set()
    finally:
        transcribe_release.set()
        structure_release.set()
        risk_release.set()
        worker_thread.join(timeout=5.0)

    assert len(results) == 1
    assert results[0].processed == 1
    assert worker.active_stages == {}
    final_status = client.get("/api/v1/enrichment/status")
    assert final_status.status_code == 200
    assert final_status.json()["active_stages"] == {}


def test_active_stages_cleared_on_error_and_skipped_blob(tmp_path: Path) -> None:
    """Verify active_stages is cleared when enrichment is skipped or raises an error."""

    class _FailingTranscriber:
        def transcribe(self, audio_bytes: bytes, language_hint: str | None = None) -> TranscriptionResult:
            raise RuntimeError("asr failure")

    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-err")
    manifest = _make_hub_manifest("phc-hub-err")

    # Missing blob -> skipped before ASR.
    store.append(
        CrdtEvent(
            event_id="evt-voice-skip-stage",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 70_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-skip-1",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"audio_blob_key": "missing-blob", "language": "en"},
        )
    )
    skip_worker = EnrichmentWorker(store, blob_store, clock, manifest)
    skip_summary = skip_worker.run_once()
    assert skip_summary.skipped_missing_blob == 1
    assert skip_worker.active_stages == {}

    # Error during transcribe -> active_stages must be cleared in finally.
    store.append(
        CrdtEvent(
            event_id="evt-voice-err-stage",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 71_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-err-1",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"transcript_hint": "Fever", "language": "en"},
        )
    )
    err_worker = EnrichmentWorker(
        store,
        blob_store,
        clock,
        manifest,
        transcriber=_FailingTranscriber(),
    )
    try:
        err_worker.run_once()
        raise AssertionError("Expected RuntimeError from failing transcriber")
    except RuntimeError:
        pass
    assert err_worker.active_stages == {}
    assert err_worker.get_status().active_stages == {}


def test_voice_note_with_fever_symptom_escalates_to_yellow_without_vitals(tmp_path: Path) -> None:
    """Voice notes reporting fever/diarrhea/breathing symptoms without numeric vitals escalate to YELLOW_PHC."""
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-escalation")
    manifest = _make_hub_manifest("phc-hub-escalation")

    # General adult patient (no age_months, no numeric vitals) with fever voice note
    store.append(
        CrdtEvent(
            event_id="evt-voice-gen-fever",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 80_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-gen-fever",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"transcript_hint": "Patient has fever since yesterday.", "language": "en"},
        )
    )
    # Pediatric patient with fever voice note and no thermometer reading
    _register_patient(store, patient_id="pat-ped-fever", age_months=24)
    store.append(
        CrdtEvent(
            event_id="evt-voice-ped-fever",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 81_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-ped-fever",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"transcript_hint": "Child has fever and cough.", "language": "en"},
        )
    )

    worker = EnrichmentWorker(store, blob_store, clock, manifest)
    summary = worker.run_once()
    assert summary.processed == 2

    projected = project_state(store.get_all_events())
    for evt_id in ("evt-voice-gen-fever", "evt-voice-ped-fever"):
        triage = TriageAssessment.model_validate(
            projected.enrichments[evt_id].payload["triage_assessment"]
        )
        assert triage.severity == TriageSeverity.YELLOW_PHC
        assert triage.referral_required is True


def test_calm_followup_on_red_patient_never_mentions_home_care_thresholds(tmp_path: Path) -> None:
    """Calm follow-up voice note or triage on an existing RED_EMERGENCY patient must replace
    the GREEN_HOME rationale and never leak 'within home-care thresholds' into
    ENRICHMENT_COMPLETED or ACTION_CARD_ISSUED.
    """
    store = EventStore(":memory:")
    blob_store = LocalBlobStore(tmp_path / "blobs")
    clock = HlcClock("phc-hub-floor-rationale")
    manifest = _make_hub_manifest("phc-hub-floor-rationale")

    # Patient 1: Prior RED_EMERGENCY triage followed by a calm VOICE_NOTE_RECORDED.
    _register_patient(store, patient_id="pat-red-voice-calm", age_months=30)
    prior_red = evaluate_triage(
        TriageInput(
            patient_id="pat-red-voice-calm",
            age_months=30,
            danger_signs=["convulsions"],
            assessed_at_ms=_BASE_DAY_MS + 90_000,
        )
    )
    assert prior_red.severity == TriageSeverity.RED_EMERGENCY
    store.append(
        CrdtEvent(
            event_id="evt-prior-red-voice",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 90_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-red-voice-calm",
            event_type=EventType.TRIAGE_COMPLETED,
            payload=prior_red.model_dump(mode="json"),
        )
    )
    store.append(
        CrdtEvent(
            event_id="evt-calm-voice-after-red",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 95_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-red-voice-calm",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={
                "transcript_hint": "Patient is resting comfortably and drinking water.",
                "language": "en",
            },
        )
    )

    # Patient 2: Prior RED_EMERGENCY with empty immediate_actions followed by calm TRIAGE_COMPLETED.
    _register_patient(store, patient_id="pat-red-triage-calm", age_months=36)
    prior_red_minimal = TriageAssessment(
        patient_id="pat-red-triage-calm",
        severity=TriageSeverity.RED_EMERGENCY,
        matched_rules=["WATCH_SOS_EMERGENCY"],
        immediate_actions=[],
        referral_required=True,
        rationale="Watch SOS emergency triggered.",
        assessed_at_ms=_BASE_DAY_MS + 91_000,
    )
    store.append(
        CrdtEvent(
            event_id="evt-prior-red-triage",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 91_000, logical=0, node_id="watch-01"),
            origin_node_id="watch-01",
            patient_id="pat-red-triage-calm",
            event_type=EventType.TRIAGE_COMPLETED,
            payload=prior_red_minimal.model_dump(mode="json"),
        )
    )
    calm_triage = evaluate_triage(
        TriageInput(
            patient_id="pat-red-triage-calm",
            age_months=36,
            temperature_c=36.8,
            spo2_pct=98,
            assessed_at_ms=_BASE_DAY_MS + 96_000,
        )
    )
    assert calm_triage.severity == TriageSeverity.GREEN_HOME
    assert "within home-care thresholds" in calm_triage.rationale.lower()
    store.append(
        CrdtEvent(
            event_id="evt-calm-triage-after-red",
            hlc=HlcTimestamp(wall_ms=_BASE_DAY_MS + 96_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-red-triage-calm",
            event_type=EventType.TRIAGE_COMPLETED,
            enrichment_state=EnrichmentState.PENDING,
            payload=calm_triage.model_dump(mode="json"),
        )
    )

    worker = EnrichmentWorker(store, blob_store, clock, manifest)
    summary = worker.run_once()
    assert summary.processed == 2

    projected = project_state(store.get_all_events())

    for evt_id, patient_id in (
        ("evt-calm-voice-after-red", "pat-red-voice-calm"),
        ("evt-calm-triage-after-red", "pat-red-triage-calm"),
    ):
        enrichment = projected.enrichments[evt_id]
        triage = TriageAssessment.model_validate(enrichment.payload["triage_assessment"])
        assert triage.severity == TriageSeverity.RED_EMERGENCY
        assert triage.referral_required is True
        assert "within home-care thresholds" not in triage.rationale.lower()
        assert "Monotonic clinical safety floor preserved RED_EMERGENCY" in triage.rationale
        assert any(
            any(tok in action.lower() for tok in ("108", "fru", "refer", "emergency"))
            for action in triage.immediate_actions
        )

        cards = projected.action_cards_for_patient(patient_id)
        assert len(cards) == 1
        card = cards[0]
        assert card.severity == TriageSeverity.RED_EMERGENCY
        assert card.priority == ActionCardPriority.CRITICAL
        assert "within home-care thresholds" not in card.summary.lower()
        assert "Monotonic clinical safety floor preserved RED_EMERGENCY" in card.summary




