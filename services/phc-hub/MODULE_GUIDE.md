# `services/phc-hub` — Module Guide (Tier-2 PHC Hub)

**Track**: Tier-2 PHC Laptop Hub Transport, Capability Router & Delta-Sync Server  
**Package**: `aarogya-phc-hub` (importable as `aarogya_phc_hub`)


---

## 1. Responsibilities

`services/phc-hub` is the Tier-2 local hub running at a Primary Health Centre (PHC) laptop or mini-PC over local Wi-Fi Hotspot / LAN (zero internet required):

- **Host Manifest Detection (`GET /manifest`)**: Inspects host CPU cores, physical RAM, and installed ML models to advertise a live `HardwareCapabilityManifest` (`NodeTier.TIER_2_HUB`).
- **Capability-Proportional Routing (`capability_router.py`)**: Maps workloads (`DETERMINISTIC_TRIAGE`, `VACCINE_SCHEDULE`, `TINY_RISK_CHECK`, `VOICE_ASR`, `CLINICAL_SLM_STRUCTURING`, `OUTBREAK_DETECTION`) to `LOCAL_DETERMINISTIC`, `LOCAL_TINY_ML`, or `DEFER_TO_HUB`.
- **Local Deterministic Triage (`POST /api/v1/triage`)**: Runs `aarogya_clinical_engine` locally without network calls.
- **CRDT Delta Sync (`POST /api/v1/sync` & `WS /ws/mesh`)**: Accepts a `SyncEnvelope` from Tier-0 Watch or Tier-1 CHW Phone, reconciles events via `aarogya_crdt_sync` (HLC + SQLite `EventStore`), and returns delta events + acknowledgements.
- **Materialized Views & Enrichment Queue**:
  - `GET /api/v1/patients` — CRDT-projected patient roster
  - `GET /api/v1/action-cards` — CRDT-projected action cards for Phone/Watch
  - `GET /api/v1/enrichment/pending` — Pending `VOICE_NOTE_RECORDED` events queued for `services/ml-pipeline`
- **Background Enrichment Worker (`enrichment_worker.py`)**:
  - `POST /api/v1/enrichment/run` (and `POST /api/v1/enrichment/run-once` alias) — Drains pending voice notes through `Stub*` / local ML backends + deterministic `evaluate_triage` Clinical Safety Floor, emitting `ENRICHMENT_COMPLETED`, `ACTION_CARD_ISSUED`, and deduplicated EWMA `OUTBREAK_ALERT_RAISED` events
  - `GET /api/v1/enrichment/status` — Worker running state, last run summary, and cumulative processed count
- **mDNS Peer Discovery & Offline Connect Info (`discovery.py`)**:
  - `GET /api/v1/peers` — Live Tier-0 Watch & Tier-1 Phone peers seen via `sync_http`, `sync_ws`, or `mdns`
  - `GET /api/v1/discovery/connect-info` — Offline LAN IPv4 URL, WebSocket URL, and `_aarogya-mesh._tcp.local.` mDNS status
- **PHC Command Center Dashboard (`dashboard.py` & `static/`)**:
  - `GET /` & `GET /static/{filename}` — 100% offline, zero-CDN clinical dashboard with English / pure *Shuddh Tatsama* Hindi toggle
  - `GET /showcase` — 3-Tier Live Interactive Showcase Stage embedding `/watch/` (Tier-0 Watch), `/phone/` (Tier-1 Phone), and live Tier-2 PHC Hub Brain side-by-side
  - `GET /api/v1/dashboard/summary` — Hub manifest, connected peers, patient/triage KPIs, enrichment risk/SHAP summaries, action cards, and outbreak alerts
  - `GET /api/v1/events` — Newest-first HLC CRDT event log inspector
- **Interactive Demo Scenario Engine (`demo_scenarios.py`) & Unified Static Mounts**:
  - `GET /api/v1/demo/scenarios` — Lists 4 real-data CRDT/enrichment scenarios (`maternal_sos`, `pediatric_voice_offload`, `village_outbreak`, `crdt_conflict_merge`)
  - `POST /api/v1/demo/load/{scenario_id}` — Loads a real scenario through `reconcile_envelopes`, `PeerRegistry`, `LocalBlobStore`, and `EnrichmentWorker`
  - `POST /api/v1/demo/reset` — Resets Hub SQLite events, blobs, and peer registry
  - `GET /phone/` & `GET /watch/` — Read-only static mounts for `apps/field-pwa` and `apps/watch-companion` when present on disk
- **Voice Blob Transport (`blob_store.py`)**:
  - `PUT /api/v1/blobs/{blob_key}` — Idempotent raw audio upload (`audio/webm`, `audio/ogg`, `audio/wav`, max 25 MiB) referenced by `VOICE_NOTE_RECORDED.payload["audio_blob_key"]`
  - `HEAD /api/v1/blobs/{blob_key}` — Fast existence check so Watch/Phone skip re-uploading synced audio
  - `GET /api/v1/blobs/{blob_key}` — Raw audio retrieval for Hub playback and `services/ml-pipeline` (`VoiceTranscriber`)
- **Persistent Local State & Environment Variables**:
  - `AAROGYA_HUB_DB` defaults to `.data/phc_hub.db` (survives restarts; gitignored).
  - `AAROGYA_HUB_BLOB_DIR` defaults to `.data/blobs` (gitignored).
  - `AAROGYA_HUB_NODE_ID` defaults to `phc-hub-local`.
  - `AAROGYA_HUB_PORT` defaults to `8000`.
  - `AAROGYA_HUB_ENABLE_MDNS` defaults to `0` (`1` enables `_aarogya-mesh._tcp.local.` mDNS advertising).
  - `AAROGYA_HUB_ENABLE_WORKER` defaults to `1` (`0` disables background enrichment loop).
  - `AAROGYA_HUB_ENRICHMENT_INTERVAL_SEC` defaults to `5.0`.

---

## 2. Running Locally

From the repo root (`aarogya-mesh/`):

```bash
# Sync workspace dependencies
uv sync

# Start the Hub server on port 8000 (matching README.md and apps/field-pwa)
make run-hub
```

Inspect OpenAPI docs at `http://127.0.0.1:8000/docs`.

---

## 3. Running Hub Integration Tests

```bash
uv run pytest -v services/phc-hub/tests/
uv run ruff check services/phc-hub/
```
