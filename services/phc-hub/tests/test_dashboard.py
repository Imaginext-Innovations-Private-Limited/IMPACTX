"""Tests for the offline Tier-2 PHC Command Center Dashboard router and static UI."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aarogya_contracts import (
    ActionCard,
    ActionCardPriority,
    CrdtEvent,
    EnrichmentState,
    EventType,
    HardwareCapabilityManifest,
    HlcTimestamp,
    NodeTier,
    TriageAssessment,
    TriageSeverity,
    WatchMode,
)
from aarogya_crdt_sync import EventStore
from aarogya_phc_hub.dashboard import STATIC_DIR, create_dashboard_router

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
)


def _build_test_client(
    peers: list[dict[str, Any]] | None = None,
) -> tuple[TestClient, EventStore]:
    store = EventStore(db_path=":memory:")
    manifest = HardwareCapabilityManifest(
        node_id="phc-hub-test",
        tier=NodeTier.TIER_2_HUB,
        ram_mb=16384,
        cpu_cores=8,
        battery_pct=100,
        has_npu=True,
        installed_models=["whisper-tiny-int8", "risk-xgb-v1"],
    )
    peer_list = list(peers or [])
    app = FastAPI()
    app.include_router(
        create_dashboard_router(
            store=store,
            manifest=manifest,
            get_peers=lambda: peer_list,
        )
    )
    return TestClient(app), store


def test_dashboard_static_assets_and_zero_cdn() -> None:
    client, _ = _build_test_client()

    index_resp = client.get("/")
    assert index_resp.status_code == 200
    assert "text/html" in index_resp.headers["content-type"]
    html = index_resp.text
    assert "/static/app.css" in html
    assert "/static/app.js" in html
    assert 'href="/showcase"' in html
    assert 'id="scenario-narrative-card"' in html
    assert 'id="engineering-proof-strip"' in html
    assert 'id="crdt-merge-proof-section"' in html
    for scenario_id in (
        "maternal_sos",
        "pediatric_voice_offload",
        "village_outbreak",
        "crdt_conflict_merge",
    ):
        assert scenario_id in html
    assert "http://" not in html.lower()
    assert "https://" not in html.lower()

    css_resp = client.get("/static/app.css")
    assert css_resp.status_code == 200
    assert "text/css" in css_resp.headers["content-type"]
    assert ".scenario-narrative" in css_resp.text
    assert ".more-counter" in css_resp.text
    assert ".payload-toggle" in css_resp.text
    assert "http://" not in css_resp.text.lower()
    assert "https://" not in css_resp.text.lower()

    js_resp = client.get("/static/app.js")
    assert js_resp.status_code == 200
    assert "javascript" in js_resp.headers["content-type"]
    js_text = js_resp.text
    assert "aarogya.lang" in js_text
    assert "aarogya.theme" in js_text
    assert "buildPatientNameMap" in js_text
    assert "formatPatientLabel" in js_text
    assert "/api/v1/demo/scenarios" in js_text
    assert "more-counter" in js_text
    assert "payload-toggle" in js_text
    assert "state.eventsExpanded = true" in js_text
    assert "http://" not in js_text.lower()
    assert "https://" not in js_text.lower()
    assert "innerHTML" not in js_text
    assert "outerHTML" not in js_text
    assert "insertAdjacentHTML" not in js_text


def test_showcase_stage_and_static_assets_zero_cdn() -> None:
    client, _ = _build_test_client()

    stage_resp = client.get("/showcase")
    assert stage_resp.status_code == 200
    assert "text/html" in stage_resp.headers["content-type"]
    html = stage_resp.text
    assert "/static/showcase.css" in html
    assert "/static/showcase.js" in html
    assert 'src="/watch/?embed=1"' in html
    assert 'src="/phone/"' in html
    assert 'href="/"' in html
    assert 'id="btn-stage-theme"' in html
    assert 'id="stage-proof-strip"' in html
    assert 'id="hub-crdt-proof-alerts"' in html
    assert 'id="hub-crdt-proof-stream"' in html
    for tab_id in ("alerts", "shap", "stream"):
        assert f'data-hub-tab="{tab_id}"' in html
    for scenario_id in (
        "maternal_sos",
        "pediatric_voice_offload",
        "village_outbreak",
        "crdt_conflict_merge",
    ):
        assert scenario_id in html
    assert "http://" not in html.lower()
    assert "https://" not in html.lower()

    static_html_resp = client.get("/static/showcase.html")
    assert static_html_resp.status_code == 200
    assert "text/html" in static_html_resp.headers["content-type"]

    css_resp = client.get("/static/showcase.css")
    assert css_resp.status_code == 200
    assert "text/css" in css_resp.headers["content-type"]
    assert '[data-theme="light"]' in css_resp.text
    assert "http://" not in css_resp.text.lower()
    assert "https://" not in css_resp.text.lower()

    js_resp = client.get("/static/showcase.js")
    assert js_resp.status_code == 200
    assert "javascript" in js_resp.headers["content-type"]
    js_text = js_resp.text
    assert "aarogya.theme" in js_text
    assert "aarogya.lang" in js_text
    assert "crdt_merge_proofs" in js_text
    assert "engineering_proof" in js_text
    assert "contentWindow.location.reload()" in js_text
    assert "http://" not in js_text.lower()
    assert "https://" not in js_text.lower()
    assert "innerHTML" not in js_text
    assert "outerHTML" not in js_text
    assert "insertAdjacentHTML" not in js_text


def test_static_path_traversal_rejected() -> None:
    client, _ = _build_test_client()

    for bad_path in (
        "/static/%2e%2e/app.py",
        "/static/..%2fapp.py",
        "/static/..%5capp.py",
        "/static/nested/app.js",
    ):
        resp = client.get(bad_path)
        assert resp.status_code in (400, 404), f"Unexpected status for {bad_path}: {resp.status_code}"
        assert "create_app" not in resp.text

    missing = client.get("/static/nonexistent.css")
    assert missing.status_code == 404


def test_dashboard_summary_aggregates_mesh_clinical_state() -> None:
    peers = [
        {
            "node_id": "phone-asha-01",
            "tier": NodeTier.TIER_1_PHONE.value,
            "battery_pct": 76,
            "last_seen_ms": 1_700_000_050_000,
        },
        {
            "node_id": "watch-chw-01",
            "tier": NodeTier.TIER_0_WATCH.value,
            "watch_mode": WatchMode.CHW_COMPANION.value,
            "battery_pct": 88,
            "last_seen_ms": 1_700_000_051_000,
        },
    ]
    client, store = _build_test_client(peers=peers)

    store.append(
        CrdtEvent(
            event_id="evt-pat-1",
            hlc=HlcTimestamp(wall_ms=1_700_000_001_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-001",
            event_type=EventType.PATIENT_REGISTERED,
            payload={
                "patient_id": "pat-001",
                "full_name": "Meera Devi",
                "village_id": "rampur-01",
                "sex": "F",
                "is_pregnant": True,
                "gestational_weeks": 30,
            },
        )
    )
    red_triage = TriageAssessment(
        assessment_id="tri-red-1",
        patient_id="pat-001",
        severity=TriageSeverity.RED_EMERGENCY,
        matched_rules=["DANGER_CONVULSIONS"],
        immediate_actions=["Immediate PHC referral"],
        referral_required=True,
        rationale="Convulsions reported.",
    )
    yellow_triage = TriageAssessment(
        assessment_id="tri-yel-1",
        patient_id="pat-001",
        severity=TriageSeverity.YELLOW_PHC,
        matched_rules=["HIGH_FEVER"],
        immediate_actions=["PHC evaluation within 24h"],
        referral_required=False,
        rationale="Persistent fever.",
    )
    green_triage = TriageAssessment(
        assessment_id="tri-grn-1",
        patient_id="pat-001",
        severity=TriageSeverity.GREEN_HOME,
        matched_rules=["ROUTINE_ANC"],
        immediate_actions=["Continue home care"],
        referral_required=False,
        rationale="Stable vitals.",
    )
    for idx, triage in enumerate((red_triage, yellow_triage, green_triage), start=2):
        store.append(
            CrdtEvent(
                event_id=f"evt-tri-{idx}",
                hlc=HlcTimestamp(
                    wall_ms=1_700_000_000_000 + idx * 1000,
                    logical=0,
                    node_id="phone-asha-01",
                ),
                origin_node_id="phone-asha-01",
                patient_id="pat-001",
                event_type=EventType.TRIAGE_COMPLETED,
                payload=triage.model_dump(mode="json"),
            )
        )

    # One pending enrichment and one completed enrichment with SHAP attributions
    store.append(
        CrdtEvent(
            event_id="evt-voice-pending",
            hlc=HlcTimestamp(wall_ms=1_700_000_010_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-001",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"language": "hi", "blob_key": "vn-001"},
        )
    )
    store.append(
        CrdtEvent(
            event_id="evt-voice-done-src",
            hlc=HlcTimestamp(wall_ms=1_700_000_011_000, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-001",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"language": "hi", "blob_key": "vn-002"},
        )
    )
    store.append(
        CrdtEvent(
            event_id="evt-enr-done",
            hlc=HlcTimestamp(wall_ms=1_700_000_012_000, logical=0, node_id="phc-hub-test"),
            origin_node_id="phc-hub-test",
            patient_id="pat-001",
            event_type=EventType.ENRICHMENT_COMPLETED,
            enrichment_state=EnrichmentState.COMPLETED,
            ref_event_id="evt-voice-done-src",
            payload={
                "risk_score": 0.87,
                "risk_band": "HIGH",
                "shap_attributions": [
                    {"feature": "gestational_weeks", "contribution": 0.34},
                    {"feature": "systolic_bp", "contribution": 0.28},
                ],
                "summary": "Elevated maternal preeclampsia risk.",
            },
        )
    )

    card = ActionCard(
        card_id="card-001",
        patient_id="pat-001",
        title="Urgent PHC Transfer",
        summary="Escort patient to PHC immediately.",
        priority=ActionCardPriority.CRITICAL,
        target_tier=NodeTier.TIER_0_WATCH,
        watch_mode=WatchMode.CHW_COMPANION,
    )
    store.append(
        CrdtEvent(
            event_id="evt-card-1",
            hlc=HlcTimestamp(wall_ms=1_700_000_013_000, logical=0, node_id="phc-hub-test"),
            origin_node_id="phc-hub-test",
            patient_id="pat-001",
            event_type=EventType.ACTION_CARD_ISSUED,
            payload=card.model_dump(mode="json"),
        )
    )
    store.append(
        CrdtEvent(
            event_id="evt-outbreak-1",
            hlc=HlcTimestamp(wall_ms=1_700_000_014_000, logical=0, node_id="phc-hub-test"),
            origin_node_id="phc-hub-test",
            event_type=EventType.OUTBREAK_ALERT_RAISED,
            payload={
                "village_id": "rampur-01",
                "syndrome": "febrile_illness",
                "message": "EWMA spike detected in rampur-01",
            },
        )
    )

    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()

    assert data["manifest"]["node_id"] == "phc-hub-test"
    assert data["manifest"]["has_npu"] is True
    assert len(data["peers"]) == 2
    assert data["patient_count"] == 1
    assert data["triage_counts"] == {
        "RED_EMERGENCY": 1,
        "YELLOW_PHC": 1,
        "GREEN_HOME": 1,
    }
    assert data["pending_enrichments"] == 1
    assert data["completed_enrichments"] == 1
    assert len(data["enrichments"]) == 1
    assert data["enrichments"][0]["risk_score"] == 0.87
    assert len(data["enrichments"][0]["shap_attributions"]) == 2
    assert len(data["action_cards"]) == 1
    assert data["action_cards"][0]["card_id"] == "card-001"
    assert len(data["outbreak_alerts"]) == 1
    assert data["outbreak_alerts"][0]["payload"]["village_id"] == "rampur-01"
    assert data["event_count"] == 9


def test_events_endpoint_sorted_newest_first_and_filterable() -> None:
    client, store = _build_test_client()

    store.append(
        CrdtEvent(
            event_id="evt-old",
            hlc=HlcTimestamp(wall_ms=1_700_000_001_000, logical=0, node_id="n1"),
            origin_node_id="n1",
            patient_id="p1",
            event_type=EventType.PATIENT_REGISTERED,
            payload={"full_name": "Asha", "village_id": "v1"},
        )
    )
    store.append(
        CrdtEvent(
            event_id="evt-mid",
            hlc=HlcTimestamp(wall_ms=1_700_000_002_000, logical=0, node_id="n1"),
            origin_node_id="n1",
            patient_id="p1",
            event_type=EventType.VOICE_NOTE_RECORDED,
            enrichment_state=EnrichmentState.PENDING,
            payload={"blob_key": "vn-1"},
        )
    )
    store.append(
        CrdtEvent(
            event_id="evt-new",
            hlc=HlcTimestamp(wall_ms=1_700_000_003_000, logical=1, node_id="n2"),
            origin_node_id="n2",
            event_type=EventType.OUTBREAK_ALERT_RAISED,
            payload={"village_id": "v1"},
        )
    )

    resp = client.get("/api/v1/events?limit=2")
    assert resp.status_code == 200
    events = resp.json()
    assert [evt["event_id"] for evt in events] == ["evt-new", "evt-mid"]

    filtered = client.get("/api/v1/events?event_type=VOICE_NOTE_RECORDED")
    assert filtered.status_code == 200
    filtered_events = filtered.json()
    assert [evt["event_id"] for evt in filtered_events] == ["evt-mid"]


def test_shuddh_tatsama_hindi_purity() -> None:
    asset_names = ("index.html", "app.js", "showcase.html", "showcase.js")
    combined = "\n".join(
        (STATIC_DIR / name).read_text(encoding="utf-8") for name in asset_names
    )

    # Verify authentic Shuddh Tatsama Hindi strings exist across dashboard and showcase
    assert "प्राथमिक स्वास्थ्य केन्द्र" in combined
    assert "आपातकाल" in combined
    assert "संक्रमण प्रकोप चेतावनी" in combined
    assert "त्रि-स्तरीय जीवन्त मंच" in combined
    assert "अतिरिक्त" in combined
    assert "अति गम्भीर" in combined
    assert "ग्राम:" in combined

    # Zero nukta characters anywhere in static assets (including NFD-decomposed forms)
    normalized = unicodedata.normalize("NFD", combined)
    assert _FORBIDDEN_NUKTA_RE.search(combined) is None
    assert _FORBIDDEN_NUKTA_RE.search(normalized) is None

    # Zero Perso-Arabic / Urdu / Hinglish loanwords
    for word in _FORBIDDEN_LOANWORDS:
        assert word not in combined, f"Forbidden loanword found: {word}"


def test_dashboard_summary_exposes_crdt_merge_proofs_and_engineering_proof() -> None:
    client, store = _build_test_client()
    t0 = 1_700_000_000_000
    t1 = t0 + 60_000

    store.append(
        CrdtEvent(
            event_id="evt-kavita-base",
            hlc=HlcTimestamp(wall_ms=t0, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-kavita",
            event_type=EventType.PATIENT_REGISTERED,
            payload={
                "patient_id": "pat-kavita",
                "full_name": "Kavita Devi",
                "village_id": "rampur-01",
                "is_pregnant": True,
                "gestational_weeks": 28,
                "metadata": {"anc_visit": 2},
            },
        )
    )
    store.append(
        CrdtEvent(
            event_id="evt-kavita-phone",
            hlc=HlcTimestamp(wall_ms=t1, logical=0, node_id="phone-asha-01"),
            origin_node_id="phone-asha-01",
            patient_id="pat-kavita",
            event_type=EventType.PATIENT_REGISTERED,
            payload={
                "patient_id": "pat-kavita",
                "is_pregnant": True,
                "gestational_weeks": 30,
                "metadata": {"anc_visit": 3, "ifa_tablets_dispensed": 30},
            },
        )
    )
    store.append(
        CrdtEvent(
            event_id="evt-kavita-watch",
            hlc=HlcTimestamp(wall_ms=t1, logical=0, node_id="watch-kavita-01"),
            origin_node_id="watch-kavita-01",
            patient_id="pat-kavita",
            event_type=EventType.PATIENT_REGISTERED,
            payload={
                "patient_id": "pat-kavita",
                "metadata": {"sos_triggered": True, "sos_danger_signs": ["vaginal_bleeding"]},
            },
        )
    )
    store.append(
        CrdtEvent(
            event_id="evt-kavita-enr",
            hlc=HlcTimestamp(wall_ms=t1 + 5000, logical=0, node_id="phc-hub-test"),
            origin_node_id="phc-hub-test",
            patient_id="pat-kavita",
            event_type=EventType.ENRICHMENT_COMPLETED,
            enrichment_state=EnrichmentState.COMPLETED,
            ref_event_id="evt-kavita-watch",
            payload={
                "audio_source": "blob",
                "transcription": {"transcript": "severe headache and blurred vision", "backend": "stub"},
                "structured_note": {
                    "extracted_symptoms": ["headache", "blurred_vision"],
                    "candidate_danger_flags": ["severe_headache", "blurred_vision"],
                    "backend": "stub",
                },
                "triage_assessment": {
                    "severity": "RED_EMERGENCY",
                    "confidence": 1.0,
                    "execution_target": "LOCAL_DETERMINISTIC",
                    "rationale": "Severe maternal danger signs.",
                },
                "risk_score": {
                    "risk_score": 0.91,
                    "risk_band": "HIGH",
                    "shap_attributions": {"high_bp": 0.35, "spo2_normal": -0.08},
                },
            },
        )
    )

    resp = client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 200
    data = resp.json()

    ep = data["engineering_proof"]
    assert ep["cloud_rpcs"] == 0
    assert ep["safety_floor_confidence"] == 1.0
    assert ep["deterministic_triage_count"] == 1
    assert ep["multi_origin_merges"] == 1
    assert ep["zero_heavy_ml_bloat"] is True

    proofs = data["crdt_merge_proofs"]
    assert len(proofs) == 1
    proof = proofs[0]
    assert proof["patient_id"] == "pat-kavita"
    assert proof["full_name"] == "Kavita Devi"
    assert proof["simultaneous_wall_ms"] is True
    assert proof["zero_data_loss"] is True
    assert set(proof["origin_nodes"]) == {"phone-asha-01", "watch-kavita-01"}
    assert proof["converged_fields"]["gestational_weeks"] == 30
    assert proof["converged_fields"]["metadata.anc_visit"] == 3
    assert proof["converged_fields"]["metadata.sos_triggered"] is True

    enr = data["enrichments"][0]
    assert enr["audio_source"] == "blob"
    assert enr["transcript"] == "severe headache and blurred vision"
    assert enr["extracted_symptoms"] == ["headache", "blurred_vision"]
    assert enr["candidate_danger_flags"] == ["severe_headache", "blurred_vision"]
    assert enr["triage_severity"] == "RED_EMERGENCY"
    assert enr["triage_confidence"] == 1.0
    assert enr["shap_attributions"]["high_bp"] > 0
    assert enr["shap_attributions"]["spo2_normal"] < 0


def test_hub_lan_url_info_and_offline_qr_svg() -> None:
    """Verify hub_lan_url, /api/v1/hub-info, /api/v1/hub-qr.svg, and connect UI elements."""
    from aarogya_phc_hub.qr_svg import build_qr_matrix

    client, _ = _build_test_client()

    summary_resp = client.get("/api/v1/dashboard/summary")
    assert summary_resp.status_code == 200
    summary = summary_resp.json()
    assert summary["hub_lan_url"].startswith("http://")
    assert summary["hub_lan_url"].endswith(":8000")

    info_resp = client.get("/api/v1/hub-info")
    assert info_resp.status_code == 200
    info = info_resp.json()
    assert info["node_id"] == "phc-hub-test"
    assert info["port"] == 8000
    assert info["hub_lan_url"] == f"http://{info['lan_ip']}:8000"

    qr_resp = client.get("/api/v1/hub-qr.svg", params={"text": "http://192.168.36.182:8000"})
    assert qr_resp.status_code == 200
    assert "image/svg+xml" in qr_resp.headers["content-type"]
    assert "<svg" in qr_resp.text
    assert "<rect" in qr_resp.text

    # Verify top-left 7x7 finder pattern on generated QR matrix
    matrix = build_qr_matrix("http://192.168.36.182:8000")
    size = len(matrix)
    assert size in (21, 25, 29, 33, 37, 41)
    assert matrix[0][:7] == [1, 1, 1, 1, 1, 1, 1]
    assert matrix[1][:7] == [1, 0, 0, 0, 0, 0, 1]
    assert matrix[3][:7] == [1, 0, 1, 1, 1, 0, 1]

    html = client.get("/").text
    assert 'id="hub-connect-card"' in html
    assert 'id="hub-lan-url"' in html
    assert 'id="btn-copy-hub-url"' in html
    assert 'id="btn-toggle-qr"' in html
    assert 'id="hub-qr-panel"' in html


def test_dashboard_and_showcase_connectivity_feedback_and_i18n_parity() -> None:
    """Verify Reconnecting.../Refreshing.../clipboard fallback and 4-language keys."""
    client, _ = _build_test_client()
    app_js = client.get("/static/app.js").text
    showcase_js = client.get("/static/showcase.js").text

    for key in ("reconnecting", "refreshing", "copyFailed"):
        assert app_js.count(f"      {key}:") == 4, f"Expected 4 translations for {key} in app.js"

    for key in ("reconnecting", "resetting"):
        assert showcase_js.count(f"      {key}:") == 4, (
            f"Expected 4 translations for {key} in showcase.js"
        )

    assert "preferred_url" in app_js
    assert 'execCommand("copy")' in app_js
    assert "state.reconnecting" in app_js
    assert "state.reconnecting" in showcase_js

