"""End-to-end tests for the Tier-2 PHC Hub real-data demo scenario engine."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aarogya_contracts import (
    ActionCardPriority,
    EventType,
    ExecutionTarget,
    HardwareCapabilityManifest,
    NodeTier,
    TriageAssessment,
    TriageSeverity,
    WatchMode,
)
from aarogya_crdt_sync import EventStore, HlcClock, project_state
from aarogya_phc_hub import demo_scenarios
from aarogya_phc_hub.blob_store import LocalBlobStore
from aarogya_phc_hub.demo_scenarios import (
    DemoLoadResult,
    DemoScenarioInfo,
    create_demo_router,
)
from aarogya_phc_hub.discovery import PeerRegistry
from aarogya_phc_hub.enrichment_worker import EnrichmentWorker

_FORBIDDEN_NUKTA_RE = re.compile(r"[\u093c\u0958-\u095f]")
_FORBIDDEN_LOANWORDS = (
    "मरीज़",
    "मरीज",
    "दवा",
    "इलाज",
    "ख़तरा",
    "खतरा",
    "ज़्यादा",
    "ज़रूरी",
    "फ़ौरन",
    "फौरन",
    "वक़्त",
    "वक्त",
    "जानकारी",
    "मदद",
    "अस्पताल",
    "डॉक्टर",
    "रिपोर्ट",
    "अलर्ट",
    "डैशबोर्ड",
    "सिस्टम",
    "बुखार",
    "दस्त",
    "बच्चा",
    "खून",
    "बीमारी",
)


def _build_demo_harness(
    tmp_path: Path,
) -> tuple[TestClient, EventStore, LocalBlobStore, PeerRegistry, EnrichmentWorker]:
    store = EventStore(db_path=":memory:")
    blob_store = LocalBlobStore(root_dir=tmp_path / "blobs")
    clock = HlcClock(node_id="phc-hub-demo")
    manifest = HardwareCapabilityManifest(
        node_id="phc-hub-demo",
        tier=NodeTier.TIER_2_HUB,
        ram_mb=32768,
        cpu_cores=16,
        battery_pct=100,
        has_npu=True,
        installed_models=["whisper-tiny-int8", "qwen2.5-3b-q4", "risk-lgbm-shap-v1"],
    )
    registry = PeerRegistry()
    worker = EnrichmentWorker(
        store=store,
        blob_store=blob_store,
        clock=clock,
        manifest=manifest,
    )
    app = FastAPI()
    app.include_router(
        create_demo_router(store, blob_store, clock, manifest, registry, worker)
    )
    return TestClient(app), store, blob_store, registry, worker


def test_list_scenarios_returns_all_four_with_metadata(tmp_path: Path) -> None:
    client, _, _, _, _ = _build_demo_harness(tmp_path)

    resp = client.get("/api/v1/demo/scenarios")
    assert resp.status_code == 200
    items = [DemoScenarioInfo.model_validate(item) for item in resp.json()]
    assert [item.id for item in items] == [
        "maternal_sos",
        "pediatric_voice_offload",
        "village_outbreak",
        "crdt_conflict_merge",
    ]
    for item in items:
        assert item.title
        assert item.subtitle
        assert item.persona
        assert len(item.steps) >= 3


def test_unknown_scenario_returns_404(tmp_path: Path) -> None:
    client, store, _, registry, _ = _build_demo_harness(tmp_path)

    resp = client.post("/api/v1/demo/load/does_not_exist")
    assert resp.status_code == 404
    assert "does_not_exist" in resp.json()["detail"]
    assert store.count() == 0
    assert registry.count() == 0


def test_scenario_maternal_sos_watch_to_asha_phone(tmp_path: Path) -> None:
    client, store, blob_store, registry, _ = _build_demo_harness(tmp_path)

    resp = client.post("/api/v1/demo/load/maternal_sos")
    assert resp.status_code == 200
    result = DemoLoadResult.model_validate(resp.json())

    assert result.scenario_id == "maternal_sos"
    assert result.events_added > 0
    assert result.peers_registered == 2
    assert result.patient_count == 1
    assert result.outbreak_count == 0
    assert result.enrichment_summary.processed == 1
    assert result.enrichment_summary.pending_remaining == 0

    # Verify real peers: PATIENT_FAMILY Watch + Tier-1 ASHA Phone
    peers = {peer.node_id: peer for peer in registry.list_peers()}
    assert "watch-family-sunita" in peers
    assert peers["watch-family-sunita"].tier == NodeTier.TIER_0_WATCH
    assert peers["watch-family-sunita"].watch_mode == WatchMode.PATIENT_FAMILY
    assert "phone-asha-rampur-01" in peers
    assert peers["phone-asha-rampur-01"].tier == NodeTier.TIER_1_PHONE

    # Verify uploaded SOS audio blob exists on disk
    assert blob_store.exists("demo-maternal-sos-sunita-audio")

    # Verify projected clinical state
    projected = project_state(store.get_all_events())
    assert "pat-sunita-devi" in projected.patients
    sunita = projected.patients["pat-sunita-devi"]
    assert sunita.full_name == "Sunita Devi"
    assert sunita.village_id == "rampur-01"
    assert sunita.is_pregnant is True
    assert sunita.gestational_weeks == 32
    assert sunita.metadata["sos_triggered"] is True

    triages = projected.triage_for_patient("pat-sunita-devi")
    assert len(triages) >= 2
    assert all(t.severity == TriageSeverity.RED_EMERGENCY for t in triages)
    assert all(t.referral_required is True for t in triages)
    assert all(t.execution_target == ExecutionTarget.LOCAL_DETERMINISTIC for t in triages)
    assert any("MAT_BP_SEVERE_PREECLAMPSIA" in t.matched_rules for t in triages)
    assert any("MAT_RED_01" in t.matched_rules for t in triages)

    # Verify enrichment + SHAP + CRITICAL Action Card targeting ASHA Phone
    assert "demo-mat-sos-watch-voice" in projected.enrichments
    enrichment = projected.enrichments["demo-mat-sos-watch-voice"]
    assert enrichment.payload["audio_source"] == "blob"
    assert enrichment.payload["risk_score"]["risk_band"] == "HIGH"
    shap_attrs = enrichment.payload["risk_score"]["shap_attributions"]
    assert any(shap_attrs.get(k, 0) > 0 for k in ("systolic_bp", "diastolic_bp", "high_bp"))

    cards = projected.action_cards_for_patient("pat-sunita-devi")
    phone_cards = [
        c
        for c in cards
        if c.target_tier == NodeTier.TIER_1_PHONE
        and c.priority == ActionCardPriority.CRITICAL
        and c.severity == TriageSeverity.RED_EMERGENCY
    ]
    assert len(phone_cards) == 1
    assert "Sunita Devi" in phone_cards[0].title


def test_scenario_pediatric_voice_offload_blob_enrichment_and_cards(tmp_path: Path) -> None:
    client, store, blob_store, registry, _ = _build_demo_harness(tmp_path)

    resp = client.post("/api/v1/demo/load/pediatric_voice_offload")
    assert resp.status_code == 200
    result = DemoLoadResult.model_validate(resp.json())

    assert result.scenario_id == "pediatric_voice_offload"
    assert result.events_added >= 5
    assert result.peers_registered == 2
    assert result.patient_count == 1
    assert result.outbreak_count == 0
    assert result.enrichment_summary.processed == 1
    assert result.enrichment_summary.pending_remaining == 0

    assert blob_store.exists("demo-voice-aarav-convulsions")
    assert registry.get_peer("phone-asha-rampur-01") is not None
    assert registry.get_peer("watch-chw-rampur-01") is not None

    projected = project_state(store.get_all_events())
    assert projected.pending_enrichments == []
    assert "pat-aarav-sharma" in projected.patients
    aarav = projected.patients["pat-aarav-sharma"]
    assert aarav.full_name == "Aarav Sharma"
    assert aarav.age_months == 14
    assert aarav.village_id == "rampur-01"

    assert "demo-ped-voice-aarav" in projected.enrichments
    enr = projected.enrichments["demo-ped-voice-aarav"]
    assert enr.event_type == EventType.ENRICHMENT_COMPLETED
    assert enr.payload["audio_source"] == "blob"
    assert enr.payload["audio_blob_key"] == "demo-voice-aarav-convulsions"
    assert "convulsions" in enr.payload["structured_note"]["candidate_danger_flags"]
    assert "fever" in enr.payload["structured_note"]["extracted_symptoms"]

    triage = TriageAssessment.model_validate(enr.payload["triage_assessment"])
    assert triage.severity == TriageSeverity.RED_EMERGENCY
    assert triage.referral_required is True
    assert triage.execution_target == ExecutionTarget.LOCAL_DETERMINISTIC
    assert "IMNCI_GDS_03" in triage.matched_rules

    risk = enr.payload["risk_score"]
    assert risk["risk_band"] == "HIGH"
    assert risk["risk_score"] >= 0.7
    assert risk["shap_attributions"]["has_danger_sign"] > 0

    cards = projected.action_cards_for_patient("pat-aarav-sharma")
    tiers = {card.target_tier for card in cards}
    assert NodeTier.TIER_0_WATCH in tiers
    assert NodeTier.TIER_1_PHONE in tiers
    assert all(card.severity == TriageSeverity.RED_EMERGENCY for card in cards)
    assert all(card.priority == ActionCardPriority.CRITICAL for card in cards)


def test_scenario_village_outbreak_multi_worker_ewma_surge(tmp_path: Path) -> None:
    client, store, _, registry, _ = _build_demo_harness(tmp_path)

    resp = client.post("/api/v1/demo/load/village_outbreak")
    assert resp.status_code == 200
    result = DemoLoadResult.model_validate(resp.json())

    assert result.scenario_id == "village_outbreak"
    assert result.peers_registered == 3
    assert result.patient_count == 13
    assert result.outbreak_count >= 2
    assert result.enrichment_summary.processed == 3
    assert result.enrichment_summary.outbreak_alerts >= 2
    assert result.enrichment_summary.pending_remaining == 0

    # Verify 3 autonomous peers (2 ASHA Phones + 1 CHW Watch)
    peers = {peer.node_id: peer for peer in registry.list_peers()}
    assert set(peers) == {
        "phone-asha-rampur-north",
        "phone-asha-rampur-south",
        "watch-chw-rampur-east",
    }
    assert peers["phone-asha-rampur-north"].tier == NodeTier.TIER_1_PHONE
    assert peers["phone-asha-rampur-south"].tier == NodeTier.TIER_1_PHONE
    assert peers["watch-chw-rampur-east"].tier == NodeTier.TIER_0_WATCH

    projected = project_state(store.get_all_events())
    assert len(projected.outbreak_alerts) >= 2
    alerts_by_syndrome = {
        alert.payload["syndrome"]: alert for alert in projected.outbreak_alerts
    }
    assert "diarrhea" in alerts_by_syndrome
    assert "fever" in alerts_by_syndrome

    for syndrome in ("diarrhea", "fever"):
        alert = alerts_by_syndrome[syndrome]
        assert alert.event_type == EventType.OUTBREAK_ALERT_RAISED
        assert alert.payload["village_id"] == "rampur-01"
        assert alert.payload["alert_triggered"] is True
        assert alert.payload["severity"] == TriageSeverity.RED_EMERGENCY.value
        assert alert.payload["ewma_value"] >= alert.payload["threshold"]


def test_scenario_crdt_conflict_merge_zero_data_loss_and_order_independence(
    tmp_path: Path,
) -> None:
    client, store, _, registry, _ = _build_demo_harness(tmp_path)

    resp = client.post("/api/v1/demo/load/crdt_conflict_merge")
    assert resp.status_code == 200
    result = DemoLoadResult.model_validate(resp.json())

    assert result.scenario_id == "crdt_conflict_merge"
    assert result.peers_registered == 2
    assert result.patient_count == 1
    assert result.outbreak_count == 0

    peers = {peer.node_id: peer for peer in registry.list_peers()}
    assert "phone-asha-kavita-01" in peers
    assert "watch-kavita-01" in peers

    all_events = store.get_all_events()
    projected = project_state(all_events)
    assert "pat-kavita-devi" in projected.patients
    kavita = projected.patients["pat-kavita-devi"]

    # Both concurrent Airplane-Mode edits survived with zero data loss
    assert kavita.full_name == "Kavita Devi"
    assert kavita.village_id == "rampur-01"
    assert kavita.is_pregnant is True
    assert kavita.gestational_weeks == 30
    assert kavita.metadata["anc_visit"] == 3
    assert kavita.metadata["sos_triggered"] is True
    assert kavita.metadata["mcp_card_id"] == "MCP-RMP-009"

    triages = projected.triage_for_patient("pat-kavita-devi")
    assert len(triages) == 1
    assert triages[0].severity == TriageSeverity.RED_EMERGENCY
    assert "MAT_RED_03" in triages[0].matched_rules

    cards = projected.action_cards_for_patient("pat-kavita-devi")
    assert len(cards) == 1
    assert cards[0].priority == ActionCardPriority.CRITICAL

    # Commutativity proof: projecting reversed event order converges identically
    reversed_projected = project_state(list(reversed(all_events)))
    assert reversed_projected.patients["pat-kavita-devi"] == kavita
    assert reversed_projected.triage_for_patient("pat-kavita-devi") == triages


def test_reset_and_reset_first_false_composition(tmp_path: Path) -> None:
    client, store, _, registry, _ = _build_demo_harness(tmp_path)

    # Load maternal_sos, then compose pediatric_voice_offload with reset_first=false
    r1 = client.post("/api/v1/demo/load/maternal_sos")
    assert r1.status_code == 200
    assert r1.json()["patient_count"] == 1

    r2 = client.post("/api/v1/demo/load/pediatric_voice_offload?reset_first=false")
    assert r2.status_code == 200
    data2 = DemoLoadResult.model_validate(r2.json())
    assert data2.patient_count == 2
    assert data2.events_added > 0

    # Reset clears SQLite events, peer_cursors, and PeerRegistry completely
    reset_resp = client.post("/api/v1/demo/reset")
    assert reset_resp.status_code == 200
    assert reset_resp.json() == {"status": "reset"}
    assert store.count() == 0
    assert store.list_peer_cursors() == []
    assert registry.count() == 0
    assert project_state(store.get_all_events()).patients == {}


def test_shuddh_tatsama_hindi_purity_in_demo_scenarios() -> None:
    source = Path(demo_scenarios.__file__).read_text(encoding="utf-8")

    # Verify authentic Shuddh Tatsama Hindi clinical terms are used
    assert "तीव्र शिरोवेदना" in source
    assert "ज्वर" in source
    assert "आक्षेप" in source
    assert "निर्विवाद समन्वय" in source

    # Zero nukta characters anywhere
    assert _FORBIDDEN_NUKTA_RE.search(source) is None

    # Zero Perso-Arabic / Urdu / Hinglish loanwords
    for word in _FORBIDDEN_LOANWORDS:
        assert word not in source, f"Forbidden loanword found in demo_scenarios.py: {word}"
