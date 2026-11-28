"""Comprehensive test suite for aarogya-crdt-sync."""

from __future__ import annotations

import itertools
from datetime import date
from pathlib import Path

import pytest

from aarogya_contracts import (
    ActionCardPriority,
    ActionCardStatus,
    CrdtEvent,
    EnrichmentState,
    EventType,
    HardwareCapabilityManifest,
    HlcTimestamp,
    NodeTier,
    TriageSeverity,
    VaccinationStatus,
    WatchMode,
)
from aarogya_crdt_sync import (
    ClockDriftError,
    EventStore,
    HlcClock,
    apply_sync_response,
    build_sync_envelope,
    compare_hlc,
    hlc_sort_key,
    parse_hlc_sort_key,
    project_state,
    reconcile_envelopes,
    select_offloadable_jobs,
    sync_peers,
)


def _watch_manifest(node_id: str = "watch-01") -> HardwareCapabilityManifest:
    return HardwareCapabilityManifest(
        node_id=node_id,
        tier=NodeTier.TIER_0_WATCH,
        ram_mb=256,
        cpu_cores=2,
        battery_pct=80,
        watch_mode=WatchMode.CHW_COMPANION,
    )


def _phone_manifest(
    node_id: str = "phone-01",
    *,
    ram_mb: int = 3072,
    battery_pct: int = 75,
    installed_models: list[str] | None = None,
) -> HardwareCapabilityManifest:
    return HardwareCapabilityManifest(
        node_id=node_id,
        tier=NodeTier.TIER_1_PHONE,
        ram_mb=ram_mb,
        cpu_cores=8,
        battery_pct=battery_pct,
        installed_models=installed_models or [],
    )


def _hub_manifest(
    node_id: str = "hub-01",
    *,
    ram_mb: int = 32768,
    battery_pct: int = 100,
    installed_models: list[str] | None = None,
) -> HardwareCapabilityManifest:
    return HardwareCapabilityManifest(
        node_id=node_id,
        tier=NodeTier.TIER_2_HUB,
        ram_mb=ram_mb,
        cpu_cores=16,
        battery_pct=battery_pct,
        has_npu=True,
        installed_models=installed_models or ["whisper-int8", "qwen2.5-3b-gbnf"],
    )


# ---------------------------------------------------------------------------
# 1. Hybrid Logical Clock tests
# ---------------------------------------------------------------------------


def test_hlc_monotonic_tick_with_frozen_and_regressing_wall_clock() -> None:
    times = iter([1_000, 1_000, 900, 1_000, 1_500])
    clock = HlcClock("phone-01", time_fn=lambda: next(times))

    t1 = clock.tick()
    t2 = clock.tick()
    t3 = clock.tick()
    t4 = clock.tick()
    t5 = clock.tick()

    assert (t1.wall_ms, t1.logical) == (1_000, 0)
    assert (t2.wall_ms, t2.logical) == (1_000, 1)
    assert (t3.wall_ms, t3.logical) == (1_000, 2)
    assert (t4.wall_ms, t4.logical) == (1_000, 3)
    assert (t5.wall_ms, t5.logical) == (1_500, 0)
    assert t1 < t2 < t3 < t4 < t5


def test_hlc_receive_merges_remote_and_breaks_ties_deterministically() -> None:
    clock = HlcClock("node-b", time_fn=lambda: 1_000)
    local = clock.tick()  # (1000, 0, node-b)

    # Remote ahead in physical time
    remote_ahead = HlcTimestamp(wall_ms=2_000, logical=5, node_id="node-a")
    merged = clock.receive(remote_ahead, now_ms=1_100)
    assert merged == HlcTimestamp(wall_ms=2_000, logical=6, node_id="node-b")
    assert merged > local
    assert merged > remote_ahead

    # Equal wall_ms -> max logical + 1
    remote_same_wall = HlcTimestamp(wall_ms=2_000, logical=9, node_id="node-c")
    merged2 = clock.receive(remote_same_wall, now_ms=1_500)
    assert merged2 == HlcTimestamp(wall_ms=2_000, logical=10, node_id="node-b")

    # Physical time overtakes both -> logical resets to 0
    merged3 = clock.receive(remote_same_wall, now_ms=5_000)
    assert merged3 == HlcTimestamp(wall_ms=5_000, logical=0, node_id="node-b")

    # Total ordering tie-breaker on node_id
    a = HlcTimestamp(wall_ms=2_000, logical=3, node_id="hub-01")
    b = HlcTimestamp(wall_ms=2_000, logical=3, node_id="phone-01")
    assert compare_hlc(a, b) == -1
    assert compare_hlc(b, a) == 1
    assert compare_hlc(a, a) == 0


def test_hlc_sort_key_roundtrip_and_drift_guard() -> None:
    ts = HlcTimestamp(wall_ms=1_732_350_000_123, logical=42, node_id="tier2:hub:01")
    key = hlc_sort_key(ts)
    assert parse_hlc_sort_key(key) == ts

    guarded = HlcClock("phone-01", time_fn=lambda: 10_000, max_drift_ms=5_000)
    far_future = HlcTimestamp(wall_ms=20_000, logical=0, node_id="bad-node")
    with pytest.raises(ClockDriftError):
        guarded.receive(far_future)


# ---------------------------------------------------------------------------
# 2. SQLite Event Store tests
# ---------------------------------------------------------------------------


def test_event_store_persistence_dedup_and_cursors(tmp_path: Path) -> None:
    db_file = tmp_path / "mesh.db"
    clock = HlcClock("phone-01", time_fn=lambda: 10_000)

    ev1 = CrdtEvent(
        event_id="ev-1",
        hlc=clock.tick(),
        origin_node_id="phone-01",
        patient_id="pat-1",
        event_type=EventType.PATIENT_REGISTERED,
        payload={"full_name": "Kavita Devi", "village_id": "V-101"},
    )
    ev2 = CrdtEvent(
        event_id="ev-2",
        hlc=clock.tick(),
        origin_node_id="phone-01",
        patient_id="pat-1",
        event_type=EventType.VOICE_NOTE_RECORDED,
        payload={"audio_uri": "local://note-1.opus", "language": "hi"},
        enrichment_state=EnrichmentState.PENDING,
    )

    with EventStore(db_file) as store:
        assert store.append(ev1) is True
        assert store.append(ev1) is False  # Idempotent duplicate
        res = store.apply_remote_events([ev1, ev2, ev2])
        assert res.inserted == 1
        assert res.duplicates == 2
        assert res.pending_enrichment_count == 1
        assert [e.event_id for e in res.pending_enrichments] == ["ev-2"]

        # HLC cursor query works
        delta_hlc = store.get_delta_since(ev1.hlc.to_sort_key())
        assert [e.event_id for e in delta_hlc] == ["ev-2"]

        # Sequence cursor query works
        store.set_peer_cursor("hub-01", last_sent_cursor=store.get_latest_cursor())
        pc = store.get_peer_cursor("hub-01")
        assert pc is not None
        assert pc.last_sent_cursor is not None
        assert store.get_delta_since(pc.last_sent_cursor) == []

    # Reopen from disk to confirm durability
    with EventStore(db_file) as reopened:
        assert reopened.count() == 2
        assert reopened.get_event("ev-2") == ev2
        assert reopened.get_peer_cursor("hub-01") is not None


# ---------------------------------------------------------------------------
# 3. Three autonomous offline nodes -> Strong Eventual Consistency in any order
# ---------------------------------------------------------------------------


def _build_diverged_three_node_mesh() -> dict[
    str, tuple[EventStore, HlcClock, HardwareCapabilityManifest]
]:
    """Create Watch, Phone, and Hub operating 100% offline on the same patient."""
    watch_store = EventStore()
    phone_store = EventStore()
    hub_store = EventStore()

    watch_clock = HlcClock("watch-01", time_fn=lambda: 1_000)
    phone_clock = HlcClock("phone-01", time_fn=lambda: 2_000)
    hub_clock = HlcClock("hub-01", time_fn=lambda: 3_000)

    watch_manifest = _watch_manifest("watch-01")
    phone_manifest = _phone_manifest("phone-01")
    hub_manifest = _hub_manifest("hub-01")

    # Watch (offline at t=1000): registers patient + records quick triage + metadata tag
    watch_store.append(
        CrdtEvent(
            event_id="ev-watch-reg",
            hlc=watch_clock.tick(),
            origin_node_id="watch-01",
            patient_id="pat-meera",
            event_type=EventType.PATIENT_REGISTERED,
            payload={
                "full_name": "Meera",
                "village_id": "V-KASHI-01",
                "sex": "F",
                "age_months": 300,
                "metadata": {"watch_checked": True},
            },
        )
    )
    watch_store.append(
        CrdtEvent(
            event_id="ev-watch-triage",
            hlc=watch_clock.tick(),
            origin_node_id="watch-01",
            patient_id="pat-meera",
            event_type=EventType.TRIAGE_COMPLETED,
            payload={
                "severity": TriageSeverity.YELLOW_PHC.value,
                "matched_rules": ["ANC_MODERATE_ANEMIA"],
                "immediate_actions": ["Refer to PHC within 24h"],
                "referral_required": True,
                "rationale": "Pallor and fatigue flagged on watch screening",
            },
        )
    )

    # Phone (offline at t=2000): updates pregnancy + full_name (collides with Watch!) + logs vaccine due
    phone_store.append(
        CrdtEvent(
            event_id="ev-phone-update",
            hlc=phone_clock.tick(),
            origin_node_id="phone-01",
            patient_id="pat-meera",
            event_type=EventType.PATIENT_REGISTERED,
            payload={
                "full_name": "Meera Devi",
                "is_pregnant": True,
                "gestational_weeks": 28,
                "preferred_language": "hi",
                "metadata": {"asha_visit_count": 3},
            },
        )
    )
    phone_store.append(
        CrdtEvent(
            event_id="ev-phone-vax",
            hlc=phone_clock.tick(),
            origin_node_id="phone-01",
            patient_id="pat-meera",
            event_type=EventType.VACCINATION_LOGGED,
            payload={
                "vaccine_code": "TT2",
                "vaccine_name": "Tetanus Toxoid 2",
                "dose_label": "Dose 2",
                "due_date": "2026-12-01",
                "status": VaccinationStatus.DUE_SOON.value,
            },
        )
    )

    # Hub (offline at t=3000): adds household_id, completes TT2 vaccination, issues ActionCard
    hub_store.append(
        CrdtEvent(
            event_id="ev-hub-update",
            hlc=hub_clock.tick(),
            origin_node_id="hub-01",
            patient_id="pat-meera",
            event_type=EventType.PATIENT_REGISTERED,
            payload={
                "household_id": "HH-42",
                "metadata": {"phc_verified": True},
            },
        )
    )
    hub_store.append(
        CrdtEvent(
            event_id="ev-hub-vax-done",
            hlc=hub_clock.tick(),
            origin_node_id="hub-01",
            patient_id="pat-meera",
            event_type=EventType.VACCINATION_LOGGED,
            payload={
                "vaccine_code": "TT2",
                "vaccine_name": "Tetanus Toxoid 2",
                "dose_label": "Dose 2",
                "due_date": "2026-12-01",
                "status": VaccinationStatus.COMPLETED.value,
                "administered_date": "2026-11-23",
            },
        )
    )
    hub_store.append(
        CrdtEvent(
            event_id="ev-hub-card",
            hlc=hub_clock.tick(),
            origin_node_id="hub-01",
            patient_id="pat-meera",
            event_type=EventType.ACTION_CARD_ISSUED,
            payload={
                "card_id": "card-anc-01",
                "title": "गर्भवती माता जाँच",
                "summary": "प्राथमिक स्वास्थ्य केन्द्र में रक्तचाप एवं हीमोग्लोबिन जाँच कराएँ।",
                "action_steps": ["रक्तचाप जाँच", "आयरन गोली वितरण"],
                "priority": ActionCardPriority.HIGH.value,
                "severity": TriageSeverity.YELLOW_PHC.value,
                "status": ActionCardStatus.OPEN.value,
                "language": "hi",
            },
        )
    )

    # Watch acknowledges card at t=4000 (even before Watch receives the original card!)
    watch_store.append(
        CrdtEvent(
            event_id="ev-watch-card-ack",
            hlc=watch_clock.tick(now_ms=4_000),
            origin_node_id="watch-01",
            patient_id="pat-meera",
            event_type=EventType.ACTION_CARD_ISSUED,
            payload={
                "card_id": "card-anc-01",
                "status": ActionCardStatus.ACKNOWLEDGED.value,
            },
        )
    )

    return {
        "watch": (watch_store, watch_clock, watch_manifest),
        "phone": (phone_store, phone_clock, phone_manifest),
        "hub": (hub_store, hub_clock, hub_manifest),
    }


@pytest.mark.parametrize(
    "sync_schedule",
    [
        # Classic multi-hop where Phone<->Hub happens BEFORE Watch's older-HLC events arrive!
        [("phone", "hub"), ("watch", "phone"), ("phone", "hub"), ("watch", "phone")],
        # Hub-centric star sync
        [("watch", "hub"), ("phone", "hub"), ("watch", "hub")],
        # Ring sync in reverse order
        [("hub", "phone"), ("hub", "watch"), ("phone", "watch"), ("phone", "hub")],
        # Watch-first chain
        [("watch", "phone"), ("watch", "hub"), ("phone", "hub")],
    ],
)
def test_three_node_strong_eventual_consistency_in_any_sync_order(
    sync_schedule: list[tuple[str, str]],
) -> None:
    nodes = _build_diverged_three_node_mesh()
    try:
        for left, right in sync_schedule:
            s_a, c_a, m_a = nodes[left]
            s_b, c_b, m_b = nodes[right]
            sync_peers(s_a, c_a, m_a, s_b, c_b, m_b)

        state_watch = project_state(nodes["watch"][0].get_all_events())
        state_phone = project_state(nodes["phone"][0].get_all_events())
        state_hub = project_state(nodes["hub"][0].get_all_events())

        # Strong eventual consistency: exact identical state on all 3 autonomous nodes
        assert state_watch == state_phone == state_hub
        assert state_hub.event_count == 8

        # Verify conflict-free per-field LWW merge on patient record
        patient = state_hub.patients["pat-meera"]
        assert patient.full_name == "Meera Devi"  # Phone (t=2000) beat Watch (t=1000)
        assert patient.village_id == "V-KASHI-01"  # Preserved from Watch
        assert patient.age_months == 300  # Preserved from Watch
        assert patient.sex == "F"  # Preserved from Watch
        assert patient.is_pregnant is True  # Merged from Phone
        assert patient.gestational_weeks == 28  # Merged from Phone
        assert patient.preferred_language == "hi"  # Merged from Phone
        assert patient.household_id == "HH-42"  # Merged from Hub
        assert patient.metadata == {
            "asha_visit_count": 3,
            "phc_verified": True,
            "watch_checked": True,
        }

        # Verify vaccination LWW progression (DUE_SOON -> COMPLETED)
        vax = state_hub.vaccinations["pat-meera"]
        assert len(vax) == 1
        assert vax[0].vaccine_code == "TT2"
        assert vax[0].status == VaccinationStatus.COMPLETED
        assert vax[0].administered_date == date(2026, 11, 23)

        # Verify ActionCard merged Hub details with Watch's newer ACKNOWLEDGED status
        card = state_hub.action_cards["card-anc-01"]
        assert card.title == "गर्भवती माता जाँच"
        assert card.status == ActionCardStatus.ACKNOWLEDGED
        assert card.priority == ActionCardPriority.HIGH
    finally:
        for store, _, _ in nodes.values():
            store.close()


def test_projector_is_order_independent_for_all_permutations() -> None:
    clock_a = HlcClock("hub-01", time_fn=lambda: 1_000)
    clock_b = HlcClock("watch-01", time_fn=lambda: 2_000)
    clock_c = HlcClock("phone-01", time_fn=lambda: 3_000)

    events = [
        CrdtEvent(
            event_id="card-open",
            hlc=clock_a.tick(),
            origin_node_id="hub-01",
            patient_id="pat-1",
            event_type=EventType.ACTION_CARD_ISSUED,
            payload={
                "card_id": "c-1",
                "title": "ORS Follow-up",
                "summary": "Check hydration",
                "status": ActionCardStatus.OPEN.value,
            },
        ),
        CrdtEvent(
            event_id="card-ack",
            hlc=clock_b.tick(),
            origin_node_id="watch-01",
            patient_id="pat-1",
            event_type=EventType.ACTION_CARD_ISSUED,
            payload={"card_id": "c-1", "status": ActionCardStatus.ACKNOWLEDGED.value},
        ),
        CrdtEvent(
            event_id="card-done",
            hlc=clock_c.tick(),
            origin_node_id="phone-01",
            patient_id="pat-1",
            event_type=EventType.ACTION_CARD_ISSUED,
            payload={"card_id": "c-1", "status": ActionCardStatus.COMPLETED.value},
        ),
    ]

    expected = project_state(events)
    assert expected.action_cards["c-1"].status == ActionCardStatus.COMPLETED
    assert expected.action_cards["c-1"].title == "ORS Follow-up"

    for perm in itertools.permutations(events):
        assert project_state(perm) == expected


# ---------------------------------------------------------------------------
# 4. Idempotent duplicate replay
# ---------------------------------------------------------------------------


def test_idempotent_duplicate_envelope_replay() -> None:
    phone_store = EventStore()
    hub_store = EventStore()
    phone_clock = HlcClock("phone-01", time_fn=lambda: 5_000)
    hub_clock = HlcClock("hub-01", time_fn=lambda: 5_000)
    phone_manifest = _phone_manifest()
    hub_manifest = _hub_manifest()

    for i in range(3):
        phone_store.append(
            CrdtEvent(
                event_id=f"ev-{i}",
                hlc=phone_clock.tick(),
                origin_node_id="phone-01",
                patient_id="pat-1",
                event_type=EventType.PATIENT_REGISTERED,
                payload={"full_name": f"Patient {i}", "village_id": "V-1"},
            )
        )

    envelope = build_sync_envelope(phone_store, phone_clock, phone_manifest, peer_node_id="hub-01")

    first = reconcile_envelopes(hub_store, hub_clock, hub_manifest, envelope)
    assert first.sync_result.inserted == 3
    assert first.sync_result.duplicates == 0
    state_after_first = project_state(hub_store.get_all_events())

    # Replay exact same envelope twice more (simulating flaky rural Wi-Fi retries)
    second = reconcile_envelopes(hub_store, hub_clock, hub_manifest, envelope)
    third = reconcile_envelopes(hub_store, hub_clock, hub_manifest, envelope)

    assert second.sync_result.inserted == 0
    assert second.sync_result.duplicates == 3
    assert third.sync_result.inserted == 0
    assert third.sync_result.duplicates == 3
    assert hub_store.count() == 3
    assert project_state(hub_store.get_all_events()) == state_after_first


# ---------------------------------------------------------------------------
# 5. Deferred Enrichment Lifecycle (Zero-RPC Offload)
# ---------------------------------------------------------------------------


def test_deferred_enrichment_lifecycle_phone_to_hub_to_phone_and_watch() -> None:
    watch_store = EventStore()
    phone_store = EventStore()
    hub_store = EventStore()

    watch_clock = HlcClock("watch-01", time_fn=lambda: 10_000)
    phone_clock = HlcClock("phone-01", time_fn=lambda: 10_000)
    hub_clock = HlcClock("hub-01", time_fn=lambda: 10_000)

    watch_manifest = _watch_manifest()
    phone_manifest = _phone_manifest()
    hub_manifest = _hub_manifest()

    # Step 1: Phone operates offline and logs VOICE_NOTE_RECORDED (PENDING)
    voice_event = CrdtEvent(
        event_id="ev-voice-001",
        hlc=phone_clock.tick(),
        origin_node_id="phone-01",
        patient_id="pat-child-7",
        event_type=EventType.VOICE_NOTE_RECORDED,
        payload={
            "audio_uri": "local://voice-001.opus",
            "duration_sec": 18,
            "language": "hi",
            "severity": TriageSeverity.RED_EMERGENCY.value,
        },
        enrichment_state=EnrichmentState.PENDING,
    )
    phone_store.append(voice_event)

    # Confirm capability-aware selection: Watch & Phone defer, Hub claims
    assert select_offloadable_jobs(watch_manifest, phone_store.get_pending_enrichments()) == []
    assert select_offloadable_jobs(phone_manifest, phone_store.get_pending_enrichments()) == []
    assert [e.event_id for e in project_state(phone_store.get_all_events()).pending_enrichments] == [
        "ev-voice-001"
    ]

    # Step 2: Phone syncs to Hub -> Hub automatically discovers offloadable job
    hub_outcome, _ = sync_peers(
        phone_store,
        phone_clock,
        phone_manifest,
        hub_store,
        hub_clock,
        hub_manifest,
    )
    assert hub_outcome.sync_result.inserted == 1
    assert [job.event_id for job in hub_outcome.offloadable_jobs] == ["ev-voice-001"]

    # Step 3: Hub runs local ML worker and appends ENRICHMENT_COMPLETED + ACTION_CARD_ISSUED
    enrichment_event = CrdtEvent(
        event_id="ev-enrich-001",
        hlc=hub_clock.tick(now_ms=12_000),
        origin_node_id="hub-01",
        patient_id="pat-child-7",
        event_type=EventType.ENRICHMENT_COMPLETED,
        payload={
            "transcript": "शिशु को तीव्र ज्वर एवं श्वास कष्ट है।",
            "extracted_symptoms": ["high_fever", "fast_breathing"],
            "model": "whisper-int8+qwen2.5-3b-gbnf",
        },
        enrichment_state=EnrichmentState.COMPLETED,
        ref_event_id=voice_event.event_id,
    )
    action_card_event = CrdtEvent(
        event_id="ev-card-001",
        hlc=hub_clock.tick(now_ms=12_001),
        origin_node_id="hub-01",
        patient_id="pat-child-7",
        event_type=EventType.ACTION_CARD_ISSUED,
        payload={
            "card_id": "card-red-001",
            "title": "आपातकाल: श्वसन कष्ट",
            "summary": "शिशु को तत्काल प्राथमिक स्वास्थ्य केन्द्र भेजें।",
            "action_steps": ["तत्काल चिकित्सालय प्रेषण", "श्वास गति की निगरानी"],
            "priority": ActionCardPriority.CRITICAL.value,
            "severity": TriageSeverity.RED_EMERGENCY.value,
            "status": ActionCardStatus.OPEN.value,
            "target_tier": NodeTier.TIER_0_WATCH.value,
            "watch_mode": WatchMode.CHW_COMPANION.value,
            "source_event_id": enrichment_event.event_id,
            "language": "hi",
        },
        ref_event_id=voice_event.event_id,
    )
    hub_store.append(enrichment_event)
    hub_store.append(action_card_event)

    # On Hub, pending_enrichments immediately drops to 0
    assert hub_store.get_pending_enrichments() == []
    assert project_state(hub_store.get_all_events()).pending_enrichments == []

    # Step 4: Hub syncs back to Phone, and Phone relays to Watch
    sync_peers(phone_store, phone_clock, phone_manifest, hub_store, hub_clock, hub_manifest)
    sync_peers(watch_store, watch_clock, watch_manifest, phone_store, phone_clock, phone_manifest)

    phone_state = project_state(phone_store.get_all_events())
    watch_state = project_state(watch_store.get_all_events())
    hub_state = project_state(hub_store.get_all_events())

    assert phone_state == watch_state == hub_state
    assert len(phone_state.pending_enrichments) == 0
    assert len(watch_state.pending_enrichments) == 0
    assert "ev-voice-001" in watch_state.enrichments
    assert "card-red-001" in watch_state.action_cards
    assert watch_state.action_cards["card-red-001"].severity == TriageSeverity.RED_EMERGENCY
    assert watch_state.action_cards["card-red-001"].target_tier == NodeTier.TIER_0_WATCH


def test_select_offloadable_jobs_respects_capabilities_and_urgency() -> None:
    clock = HlcClock("phone-01", time_fn=lambda: 1_000)
    routine_voice = CrdtEvent(
        event_id="ev-routine",
        hlc=clock.tick(),
        origin_node_id="phone-01",
        event_type=EventType.VOICE_NOTE_RECORDED,
        payload={"language": "hi"},
        enrichment_state=EnrichmentState.PENDING,
    )
    urgent_voice = CrdtEvent(
        event_id="ev-urgent",
        hlc=clock.tick(),
        origin_node_id="phone-01",
        event_type=EventType.VOICE_NOTE_RECORDED,
        payload={"language": "hi", "severity": TriageSeverity.RED_EMERGENCY.value},
        enrichment_state=EnrichmentState.PENDING,
    )
    specific_model_job = CrdtEvent(
        event_id="ev-special",
        hlc=clock.tick(),
        origin_node_id="phone-01",
        event_type=EventType.CHECKLIST_RECORDED,
        payload={"required_model": "custom-slm-v2"},
        enrichment_state=EnrichmentState.PENDING,
    )
    pending = [routine_voice, urgent_voice, specific_model_job]

    # Hub prioritizes RED_EMERGENCY first and skips jobs whose required_model isn't installed
    hub_jobs = select_offloadable_jobs(_hub_manifest(), pending)
    assert [j.event_id for j in hub_jobs] == ["ev-urgent", "ev-routine"]

    # High-spec Phone with whisper model + healthy battery can process voice notes
    capable_phone = _phone_manifest(ram_mb=6144, battery_pct=60, installed_models=["whisper-tiny"])
    assert [j.event_id for j in select_offloadable_jobs(capable_phone, pending)] == [
        "ev-urgent",
        "ev-routine",
    ]

    # Low-battery Phone skips all ML offload jobs
    low_batt_phone = _phone_manifest(ram_mb=6144, battery_pct=15, installed_models=["whisper-tiny"])
    assert select_offloadable_jobs(low_batt_phone, pending) == []


def test_patient_pregnancy_delivery_clears_gestational_weeks_safely() -> None:
    clock = HlcClock("phone-01", time_fn=lambda: 1_000)
    ev1 = CrdtEvent(
        event_id="ev-preg",
        hlc=clock.tick(),
        origin_node_id="phone-01",
        patient_id="pat-2",
        event_type=EventType.PATIENT_REGISTERED,
        payload={
            "full_name": "Sunita Devi",
            "village_id": "V-2",
            "is_pregnant": True,
            "gestational_weeks": 38,
        },
    )
    ev2 = CrdtEvent(
        event_id="ev-delivered",
        hlc=clock.tick(now_ms=2_000),
        origin_node_id="hub-01",
        patient_id="pat-2",
        event_type=EventType.PATIENT_REGISTERED,
        payload={"is_pregnant": False},
    )

    state = project_state([ev2, ev1])  # Deliberately out of order
    pat = state.patients["pat-2"]
    assert pat.is_pregnant is False
    assert pat.gestational_weeks is None


def test_apply_sync_response_handles_empty_envelope_gracefully() -> None:
    store_a = EventStore()
    store_b = EventStore()
    clock_a = HlcClock("phone-01", time_fn=lambda: 1_000)
    clock_b = HlcClock("hub-01", time_fn=lambda: 1_000)

    outbound = build_sync_envelope(store_a, clock_a, _phone_manifest(), peer_node_id="hub-01")
    outcome = reconcile_envelopes(store_b, clock_b, _hub_manifest(), outbound)
    result = apply_sync_response(store_a, clock_a, outcome.response_envelope)

    assert result.inserted == 0
    assert result.duplicates == 0
    assert store_a.count() == 0
    assert store_b.count() == 0
