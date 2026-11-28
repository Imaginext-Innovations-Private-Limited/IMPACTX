"""Integration tests for the Tier-2 PHC Hub FastAPI service and capability router."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from aarogya_clinical_engine import PatientCategory, TriageInput, evaluate_triage
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
    SyncEnvelope,
    TriageAssessment,
    TriageSeverity,
    WatchMode,
)
from aarogya_phc_hub.app import create_app
from aarogya_phc_hub.capability_router import WorkloadKind, route_workload


def test_capability_router_matrix() -> None:
    watch = HardwareCapabilityManifest(
        node_id="watch-01",
        tier=NodeTier.TIER_0_WATCH,
        ram_mb=256,
        cpu_cores=2,
        battery_pct=80,
        watch_mode=WatchMode.CHW_COMPANION,
    )
    phone = HardwareCapabilityManifest(
        node_id="phone-01",
        tier=NodeTier.TIER_1_PHONE,
        ram_mb=4096,
        cpu_cores=8,
        battery_pct=60,
        installed_models=["tiny-risk-v1"],
    )
    hub = HardwareCapabilityManifest(
        node_id="hub-01",
        tier=NodeTier.TIER_2_HUB,
        ram_mb=32768,
        cpu_cores=16,
        battery_pct=100,
    )

    assert route_workload(watch, WorkloadKind.DETERMINISTIC_TRIAGE) == ExecutionTarget.LOCAL_DETERMINISTIC
    assert route_workload(watch, WorkloadKind.VOICE_ASR) == ExecutionTarget.DEFER_TO_HUB
    assert route_workload(phone, WorkloadKind.CLINICAL_SLM_STRUCTURING) == ExecutionTarget.DEFER_TO_HUB
    assert (
        route_workload(phone, WorkloadKind.TINY_RISK_CHECK, required_model="tiny-risk-v1")
        == ExecutionTarget.LOCAL_TINY_ML
    )
    assert route_workload(hub, WorkloadKind.VOICE_ASR) == ExecutionTarget.LOCAL_TINY_ML
    assert route_workload(hub, WorkloadKind.OUTBREAK_DETECTION) == ExecutionTarget.LOCAL_DETERMINISTIC


def test_health_manifest_and_standalone_triage(tmp_path: Path) -> None:
    hub_app = create_app(db_path=tmp_path / "hub.db", node_id="hub-test-01")
    client = TestClient(hub_app)

    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] == "ok"
    assert health_resp.json()["tier"] == "TIER_2_HUB"

    manifest_resp = client.get("/manifest")
    assert manifest_resp.status_code == 200
    manifest = HardwareCapabilityManifest.model_validate(manifest_resp.json())
    assert manifest.node_id == "hub-test-01"
    assert manifest.tier == NodeTier.TIER_2_HUB
    assert manifest.ram_mb >= 1
    assert manifest.cpu_cores >= 1

    triage_resp = client.post(
        "/api/v1/triage",
        json={
            "patient_id": "pat-101",
            "age_months": 14,
            "danger_signs": ["convulsions"],
        },
    )
    assert triage_resp.status_code == 200
    assessment = TriageAssessment.model_validate(triage_resp.json())
    assert assessment.severity == TriageSeverity.RED_EMERGENCY
    assert assessment.referral_required is True
    assert assessment.confidence == 1.0
    assert assessment.execution_target == ExecutionTarget.LOCAL_DETERMINISTIC


def test_crdt_sync_roundtrip_and_websocket(tmp_path: Path) -> None:
    hub_app = create_app(db_path=tmp_path / "hub_sync.db", node_id="hub-sync-01")
    client = TestClient(hub_app)

    phone_manifest = HardwareCapabilityManifest(
        node_id="phone-asha-01",
        tier=NodeTier.TIER_1_PHONE,
        ram_mb=4096,
        cpu_cores=8,
    )
    patient_evt = CrdtEvent(
        event_id="evt-pat-01",
        hlc=HlcTimestamp(wall_ms=1_700_000_000_000, logical=0, node_id="phone-asha-01"),
        origin_node_id="phone-asha-01",
        patient_id="pat-202",
        event_type=EventType.PATIENT_REGISTERED,
        payload={
            "patient_id": "pat-202",
            "full_name": "Kavita Devi",
            "village_id": "rampur-01",
            "sex": "F",
            "is_pregnant": True,
            "gestational_weeks": 28,
        },
    )
    voice_evt = CrdtEvent(
        event_id="evt-voice-01",
        hlc=HlcTimestamp(wall_ms=1_700_000_001_000, logical=0, node_id="phone-asha-01"),
        origin_node_id="phone-asha-01",
        patient_id="pat-202",
        event_type=EventType.VOICE_NOTE_RECORDED,
        enrichment_state=EnrichmentState.PENDING,
        payload={"language": "hi", "transcript_hint": "High fever"},
    )
    card = ActionCard(
        card_id="card-202",
        patient_id="pat-202",
        title="ANC Follow-up",
        summary="Check BP and hemoglobin at PHC.",
        priority=ActionCardPriority.HIGH,
        target_tier=NodeTier.TIER_0_WATCH,
        watch_mode=WatchMode.CHW_COMPANION,
    )
    card_evt = CrdtEvent(
        event_id="evt-card-01",
        hlc=HlcTimestamp(wall_ms=1_700_000_002_000, logical=0, node_id="phone-asha-01"),
        origin_node_id="phone-asha-01",
        patient_id="pat-202",
        event_type=EventType.ACTION_CARD_ISSUED,
        payload=card.model_dump(mode="json"),
    )

    envelope = SyncEnvelope(
        sender_manifest=phone_manifest,
        sender_hlc=HlcTimestamp(wall_ms=1_700_000_003_000, logical=0, node_id="phone-asha-01"),
        events=[patient_evt, voice_evt, card_evt],
    )
    sync_resp = client.post("/api/v1/sync", json=envelope.model_dump(mode="json"))
    assert sync_resp.status_code == 200
    delta = SyncEnvelope.model_validate(sync_resp.json())
    assert set(delta.ack_event_ids) == {"evt-pat-01", "evt-voice-01", "evt-card-01"}

    patients = client.get("/api/v1/patients").json()
    assert len(patients) == 1
    assert patients[0]["full_name"] == "Kavita Devi"

    cards = client.get("/api/v1/action-cards").json()
    assert len(cards) == 1
    assert cards[0]["card_id"] == "card-202"

    pending = client.get("/api/v1/enrichment/pending").json()
    assert len(pending) == 1
    assert pending[0]["event_id"] == "evt-voice-01"

    # WebSocket peer sync should accept a SyncEnvelope and reply with a valid SyncEnvelope.
    watch_manifest = HardwareCapabilityManifest(
        node_id="watch-asha-01",
        tier=NodeTier.TIER_0_WATCH,
        ram_mb=256,
        cpu_cores=2,
        watch_mode=WatchMode.CHW_COMPANION,
    )
    ws_envelope = SyncEnvelope(
        sender_manifest=watch_manifest,
        sender_hlc=HlcTimestamp(wall_ms=1_700_000_004_000, logical=0, node_id="watch-asha-01"),
    )
    with client.websocket_connect("/ws/mesh") as ws:
        ws.send_json(ws_envelope.model_dump(mode="json"))
        ws_reply = SyncEnvelope.model_validate(ws.receive_json())
        assert ws_reply.sender_manifest.node_id == "hub-sync-01"
        assert len(ws_reply.events) >= 3


def test_voice_blob_upload_download_head_and_safety(tmp_path: Path) -> None:
    hub_app = create_app(
        db_path=tmp_path / "hub_blobs.db",
        blob_dir=tmp_path / "blobs",
        node_id="hub-blob-01",
    )
    client = TestClient(hub_app)

    # Missing blob returns 404 on HEAD and GET
    assert client.head("/api/v1/blobs/vn-missing").status_code == 404
    assert client.get("/api/v1/blobs/vn-missing").status_code == 404

    # Empty upload rejected
    assert client.put("/api/v1/blobs/vn-empty", content=b"").status_code == 400

    # Invalid / traversal keys rejected
    assert client.put("/api/v1/blobs/..badkey", content=b"audio").status_code == 400

    # Upload WebM audio clip and verify idempotent PUT + HEAD + GET roundtrip
    sample_audio = b"\x1a\x45\xdf\xa3mock-webm-opus-voice-note"
    put_resp = client.put(
        "/api/v1/blobs/vn-1234-abc",
        content=sample_audio,
        headers={"Content-Type": "audio/webm;codecs=opus"},
    )
    assert put_resp.status_code == 200
    meta = put_resp.json()
    assert meta["blob_key"] == "vn-1234-abc"
    assert meta["content_type"] == "audio/webm"
    assert meta["size_bytes"] == len(sample_audio)
    assert len(meta["sha256"]) == 64

    # Idempotent re-upload succeeds with identical hash
    put_again = client.put(
        "/api/v1/blobs/vn-1234-abc",
        content=sample_audio,
        headers={"Content-Type": "audio/webm"},
    )
    assert put_again.status_code == 200
    assert put_again.json()["sha256"] == meta["sha256"]

    assert client.head("/api/v1/blobs/vn-1234-abc").status_code == 200
    get_resp = client.get("/api/v1/blobs/vn-1234-abc")
    assert get_resp.status_code == 200
    assert get_resp.content == sample_audio
    assert get_resp.headers["content-type"].startswith("audio/webm")
    assert get_resp.headers["x-blob-sha256"] == meta["sha256"]


def test_persistent_db_survives_hub_restart(tmp_path: Path) -> None:
    db_file = tmp_path / "nested" / "phc_hub.db"
    hub_v1 = create_app(db_path=db_file, node_id="hub-persist-01")
    client_v1 = TestClient(hub_v1)

    triage_resp = client_v1.post(
        "/api/v1/triage",
        json={"patient_id": "pat-persist-1", "age_months": 10, "danger_signs": ["convulsions"]},
    )
    assert triage_resp.status_code == 200
    assert client_v1.get("/health").json()["event_count"] == 1

    # Simulate Hub process restart against the same persistent SQLite path
    hub_v2 = create_app(db_path=db_file, node_id="hub-persist-01")
    client_v2 = TestClient(hub_v2)
    assert client_v2.get("/health").json()["event_count"] == 1


def test_unified_hub_enrichment_discovery_and_dashboard_e2e(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys.modules["aarogya_phc_hub.app"], "_detect_ram_mb", lambda: 16384)
    hub_app = create_app(
        db_path=tmp_path / "hub_e2e.db",
        blob_dir=tmp_path / "blobs_e2e",
        node_id="hub-e2e-01",
    )
    client = TestClient(hub_app)

    # 1. Phone uploads voice blob and syncs PATIENT_REGISTERED + PENDING VOICE_NOTE_RECORDED
    blob_key = "vn-e2e-001"
    put_resp = client.put(
        f"/api/v1/blobs/{blob_key}",
        content=b"\x1a\x45\xdf\xa3mock-audio-e2e",
        headers={"Content-Type": "audio/webm"},
    )
    assert put_resp.status_code == 200

    phone_manifest = HardwareCapabilityManifest(
        node_id="phone-e2e-01",
        tier=NodeTier.TIER_1_PHONE,
        ram_mb=4096,
        cpu_cores=8,
    )
    patient_evt = CrdtEvent(
        event_id="evt-e2e-pat-01",
        hlc=HlcTimestamp(wall_ms=1_700_000_010_000, logical=0, node_id="phone-e2e-01"),
        origin_node_id="phone-e2e-01",
        patient_id="pat-e2e-01",
        event_type=EventType.PATIENT_REGISTERED,
        payload={
            "patient_id": "pat-e2e-01",
            "full_name": "Sunita Devi",
            "village_id": "rampur-02",
            "sex": "F",
            "is_pregnant": True,
            "gestational_weeks": 30,
        },
    )
    voice_evt = CrdtEvent(
        event_id="evt-e2e-voice-01",
        hlc=HlcTimestamp(wall_ms=1_700_000_011_000, logical=0, node_id="phone-e2e-01"),
        origin_node_id="phone-e2e-01",
        patient_id="pat-e2e-01",
        event_type=EventType.VOICE_NOTE_RECORDED,
        enrichment_state=EnrichmentState.PENDING,
        payload={
            "audio_blob_key": blob_key,
            "language": "hi",
            "transcript_hint": "High fever and convulsions since morning",
        },
    )
    sync_resp = client.post(
        "/api/v1/sync",
        json=SyncEnvelope(
            sender_manifest=phone_manifest,
            sender_hlc=HlcTimestamp(wall_ms=1_700_000_012_000, logical=0, node_id="phone-e2e-01"),
            events=[patient_evt, voice_evt],
        ).model_dump(mode="json"),
    )
    assert sync_resp.status_code == 200

    peers_http = client.get("/api/v1/peers").json()
    assert any(p["node_id"] == "phone-e2e-01" and p["source"] == "sync_http" for p in peers_http)

    # 2. Run enrichment -> drains pending queue and updates dashboard summary
    run_resp = client.post("/api/v1/enrichment/run")
    assert run_resp.status_code == 200
    assert run_resp.json()["processed"] == 1
    assert client.get("/api/v1/enrichment/pending").json() == []

    summary_resp = client.get("/api/v1/dashboard/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["completed_enrichments"] == 1
    assert summary["pending_enrichments"] == 0
    assert isinstance(summary["enrichments"][0]["risk_score"], float)
    assert len(summary["enrichments"][0]["shap_attributions"]) > 0
    assert sum(summary["triage_counts"].values()) >= 1
    assert len(summary["action_cards"]) >= 1

    # 3. Watch WS sync -> recorded as sync_ws peer and receives Hub-issued ACTION_CARD_ISSUED
    watch_manifest = HardwareCapabilityManifest(
        node_id="watch-e2e-01",
        tier=NodeTier.TIER_0_WATCH,
        ram_mb=256,
        cpu_cores=2,
        watch_mode=WatchMode.CHW_COMPANION,
    )
    ws_env = SyncEnvelope(
        sender_manifest=watch_manifest,
        sender_hlc=HlcTimestamp(wall_ms=1_700_000_013_000, logical=0, node_id="watch-e2e-01"),
    )
    with client.websocket_connect("/ws/mesh") as ws:
        ws.send_json(ws_env.model_dump(mode="json"))
        ws_reply = SyncEnvelope.model_validate(ws.receive_json())
        assert any(evt.event_type == EventType.ACTION_CARD_ISSUED for evt in ws_reply.events)

    peers_all = client.get("/api/v1/peers").json()
    assert any(p["node_id"] == "watch-e2e-01" and p["source"] == "sync_ws" for p in peers_all)

    # 4. Dashboard HTML & discovery connect-info
    index_resp = client.get("/")
    assert index_resp.status_code == 200
    assert "text/html" in index_resp.headers["content-type"]

    connect_resp = client.get("/api/v1/discovery/connect-info")
    assert connect_resp.status_code == 200
    assert connect_resp.json()["hub_node_id"] == "hub-e2e-01"


def test_hub_showcase_mounts_and_demo_router_integration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys.modules["aarogya_phc_hub.app"], "_detect_ram_mb", lambda: 16384)
    hub_app = create_app(
        db_path=tmp_path / "hub_showcase.db",
        blob_dir=tmp_path / "blobs_showcase",
        node_id="hub-showcase-01",
    )
    client = TestClient(hub_app)

    for route in ("/showcase", "/phone/", "/watch/"):
        resp = client.get(route)
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    scenarios_resp = client.get("/api/v1/demo/scenarios")
    assert scenarios_resp.status_code == 200
    assert len(scenarios_resp.json()) == 4

    load_resp = client.post("/api/v1/demo/load/village_outbreak")
    assert load_resp.status_code == 200

    summary = client.get("/api/v1/dashboard/summary").json()
    assert summary["patient_count"] >= 1
    assert len(summary["peers"]) >= 1
    assert len(summary["outbreak_alerts"]) >= 1

    reset_resp = client.post("/api/v1/demo/reset")
    assert reset_resp.status_code == 200
    after_reset = client.get("/api/v1/dashboard/summary").json()
    assert after_reset["event_count"] == 0
    assert after_reset["peers"] == []


def test_triage_sync_auto_enriches_and_returns_ml_insights_in_same_roundtrip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Phone registers patient + runs PENDING triage -> single /api/v1/sync runs Hub GBDT + TreeSHAP
    and returns ENRICHMENT_COMPLETED (risk_score, top_features, recommended_follow_up, severity)
    and ACTION_CARD_ISSUED in the same sync round-trip.
    """
    monkeypatch.setattr(sys.modules["aarogya_phc_hub.app"], "_detect_ram_mb", lambda: 16384)
    hub_app = create_app(
        db_path=tmp_path / "hub_triage_ml.db",
        blob_dir=tmp_path / "blobs_triage_ml",
        node_id="hub-ml-01",
    )
    client = TestClient(hub_app)

    phone_manifest = HardwareCapabilityManifest(
        node_id="phone-asha-ml-01",
        tier=NodeTier.TIER_1_PHONE,
        ram_mb=4096,
        cpu_cores=8,
    )
    patient_evt = CrdtEvent(
        event_id="evt-ml-pat-01",
        hlc=HlcTimestamp(wall_ms=1_700_000_050_000, logical=0, node_id="phone-asha-ml-01"),
        origin_node_id="phone-asha-ml-01",
        patient_id="pat-lakshmi-01",
        event_type=EventType.PATIENT_REGISTERED,
        payload={
            "patient_id": "pat-lakshmi-01",
            "full_name": "Lakshmi Devi",
            "village_id": "rampur-01",
            "sex": "F",
            "is_pregnant": True,
            "gestational_weeks": 28,
            "preferred_language": "en",
        },
    )

    local_triage = evaluate_triage(
        TriageInput(
            patient_id="pat-lakshmi-01",
            patient_category=PatientCategory.MATERNAL,
            is_pregnant=True,
            gestational_weeks=28,
            systolic_bp=156,
            diastolic_bp=102,
            danger_signs=["severe_headache_or_blurred_vision"],
            assessed_at_ms=1_700_000_051_000,
        )
    )
    assert local_triage.severity == TriageSeverity.RED_EMERGENCY

    triage_evt = CrdtEvent(
        event_id="evt-ml-triage-01",
        hlc=HlcTimestamp(wall_ms=1_700_000_051_000, logical=0, node_id="phone-asha-ml-01"),
        origin_node_id="phone-asha-ml-01",
        patient_id="pat-lakshmi-01",
        event_type=EventType.TRIAGE_COMPLETED,
        enrichment_state=EnrichmentState.PENDING,
        payload=local_triage.model_dump(mode="json"),
    )

    sync_resp = client.post(
        "/api/v1/sync",
        json=SyncEnvelope(
            sender_manifest=phone_manifest,
            sender_hlc=HlcTimestamp(wall_ms=1_700_000_052_000, logical=0, node_id="phone-asha-ml-01"),
            events=[patient_evt, triage_evt],
        ).model_dump(mode="json"),
    )
    assert sync_resp.status_code == 200
    delta = SyncEnvelope.model_validate(sync_resp.json())
    assert set(delta.ack_event_ids) == {"evt-ml-pat-01", "evt-ml-triage-01"}

    # Same sync round-trip must return ENRICHMENT_COMPLETED + ACTION_CARD_ISSUED
    enrichment_events = [
        evt for evt in delta.events if evt.event_type == EventType.ENRICHMENT_COMPLETED
    ]
    action_card_events = [
        evt for evt in delta.events if evt.event_type == EventType.ACTION_CARD_ISSUED
    ]
    assert len(enrichment_events) == 1
    assert len(action_card_events) == 1

    enr = enrichment_events[0]
    assert enr.ref_event_id == "evt-ml-triage-01"
    assert enr.patient_id == "pat-lakshmi-01"
    assert enr.enrichment_state == EnrichmentState.COMPLETED
    assert enr.hlc > triage_evt.hlc
    assert enr.payload["source_type"] == "triage"
    assert enr.payload["severity"] == TriageSeverity.RED_EMERGENCY.value

    risk_score_obj = enr.payload["risk_score"]
    assert isinstance(risk_score_obj["risk_score"], float)
    assert 0.0 <= risk_score_obj["risk_score"] <= 1.0
    assert risk_score_obj["risk_band"] in ("LOW", "MODERATE", "HIGH")
    assert len(risk_score_obj["shap_attributions"]) > 0

    top_features = enr.payload["top_features"]
    assert isinstance(top_features, list) and len(top_features) > 0
    for feat in top_features:
        assert isinstance(feat["feature"], str) and feat["feature"]
        assert isinstance(feat["contribution"], float)
        assert feat["direction"] in ("risk", "protective")

    assert isinstance(enr.payload["recommended_follow_up"], str)
    assert len(enr.payload["recommended_follow_up"]) > 0

    provenance = enr.payload["reasoning_provenance"]
    assert provenance["stage"] == "HOST_LAPTOP_ML_ANALYTICS"
    assert provenance["clinical_protocol"] == "NHM ASHA Maternal (NHM_ASHA_MATERNAL_ANC_PNC_2024)"
    assert isinstance(provenance["matched_rule_ids"], list)
    assert len(provenance["matched_rule_ids"]) > 0
    assert isinstance(provenance["clinical_parameters"], str)
    assert len(provenance["clinical_parameters"]) > 0
    assert "28-Tree Monotone GBDT + Exact TreeSHAP" in provenance["ml_engine"]
    assert "AUROC 0.8318" in provenance["ml_engine"]
    assert "Laptop GBDT combined 13 vitals & flags" in provenance["ml_summary"]
    assert "RED_EMERGENCY" in provenance["ml_summary"]

    triage_out = TriageAssessment.model_validate(enr.payload["triage_assessment"])
    assert triage_out.severity == TriageSeverity.RED_EMERGENCY
    assert triage_out.referral_required is True
    assert triage_out.execution_target == ExecutionTarget.LOCAL_DETERMINISTIC

    card_evt = action_card_events[0]
    assert card_evt.ref_event_id == "evt-ml-triage-01"
    card = ActionCard.model_validate(card_evt.payload)
    assert card.patient_id == "pat-lakshmi-01"
    assert card.source_event_id == enr.event_id
    assert card.severity == TriageSeverity.RED_EMERGENCY
    assert card.priority == ActionCardPriority.CRITICAL

    # Pending queue must be drained immediately
    assert client.get("/api/v1/enrichment/pending").json() == []

    # Dashboard summary reflects the completed enrichment with risk score and SHAP bars
    summary = client.get("/api/v1/dashboard/summary").json()
    assert summary["completed_enrichments"] == 1
    assert summary["pending_enrichments"] == 0
    assert isinstance(summary["enrichments"][0]["risk_score"], float)
    assert len(summary["enrichments"][0]["shap_attributions"]) > 0
