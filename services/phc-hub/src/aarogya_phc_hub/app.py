"""FastAPI transport and CRDT delta-sync server for the Tier-2 PHC Hub."""

from __future__ import annotations

import os
import tempfile
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError

from aarogya_clinical_engine import TriageInput, evaluate_triage
from aarogya_contracts import (
    ActionCard,
    CrdtEvent,
    EnrichmentState,
    EventType,
    HardwareCapabilityManifest,
    NodeTier,
    PatientRecord,
    SyncEnvelope,
    TriageAssessment,
)
from aarogya_crdt_sync import (
    EventStore,
    HlcClock,
    ProjectedState,
    project_state,
    reconcile_envelopes,
)
from aarogya_phc_hub.blob_store import BlobMetadata, LocalBlobStore
from aarogya_phc_hub.capability_router import WorkloadKind, route_workload
from aarogya_phc_hub.dashboard import create_dashboard_router
from aarogya_phc_hub.demo_scenarios import create_demo_router
from aarogya_phc_hub.discovery import (
    MdnsAdvertiser,
    PeerRegistry,
    create_discovery_router,
)
from aarogya_phc_hub.enrichment_worker import EnrichmentWorker, create_enrichment_router


def _detect_ram_mb() -> int:
    """Read total physical RAM in MiB from /proc/meminfo on Linux with a safe fallback."""
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                parts = line.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    return max(int(parts[1]) // 1024, 1)
    return 8192


def _detect_has_npu() -> bool:
    """Best-effort Linux check for Intel NPU / accel device nodes."""
    return Path("/dev/accel").exists()


def detect_host_manifest(
    node_id: str = "phc-hub-local",
    installed_models: list[str] | None = None,
) -> HardwareCapabilityManifest:
    """Build a live HardwareCapabilityManifest from the host machine."""
    return HardwareCapabilityManifest(
        node_id=node_id,
        tier=NodeTier.TIER_2_HUB,
        ram_mb=_detect_ram_mb(),
        cpu_cores=max(os.cpu_count() or 1, 1),
        battery_pct=100,
        has_npu=_detect_has_npu(),
        installed_models=list(installed_models or []),
        watch_mode=None,
    )


def create_app(
    *,
    db_path: str | Path = ":memory:",
    blob_dir: str | Path | None = None,
    node_id: str = "phc-hub-local",
    installed_models: list[str] | None = None,
    port: int = 8000,
    enable_mdns: bool = False,
    enable_enrichment_worker: bool = False,
    enrichment_interval_sec: float = 5.0,
) -> FastAPI:
    """Create a configured Tier-2 PHC Hub FastAPI application."""
    if str(db_path) != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    if blob_dir is not None:
        resolved_blob_dir = Path(blob_dir)
    elif str(db_path) != ":memory:":
        resolved_blob_dir = Path(db_path).parent / "blobs"
    else:
        resolved_blob_dir = Path(tempfile.mkdtemp(prefix="aarogya-hub-blobs-"))

    store = EventStore(db_path=db_path)
    blob_store = LocalBlobStore(root_dir=resolved_blob_dir)
    clock = HlcClock(node_id=node_id)
    manifest = detect_host_manifest(node_id=node_id, installed_models=installed_models)
    peer_registry = PeerRegistry()
    mdns_advertiser = MdnsAdvertiser(manifest, port=port, enabled=enable_mdns)
    enrichment_worker = EnrichmentWorker(
        store=store,
        blob_store=blob_store,
        clock=clock,
        manifest=manifest,
        poll_interval_sec=enrichment_interval_sec,
    )

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        if enable_mdns:
            mdns_advertiser.start()
        if enable_enrichment_worker:
            await enrichment_worker.start(enrichment_interval_sec)
        try:
            yield
        finally:
            await enrichment_worker.stop()
            mdns_advertiser.stop()

    hub_app = FastAPI(
        title="Aarogya Mesh — Tier-2 PHC Hub",
        version="0.4.0",
        description="Autonomous offline-first Tier-2 PHC Hub with CRDT delta sync and deterministic clinical triage.",
        lifespan=lifespan,
    )
    hub_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    hub_app.state.store = store
    hub_app.state.blob_store = blob_store
    hub_app.state.clock = clock
    hub_app.state.manifest = manifest
    hub_app.state.peer_registry = peer_registry
    hub_app.state.mdns_advertiser = mdns_advertiser
    hub_app.state.enrichment_worker = enrichment_worker

    def _projected() -> ProjectedState:
        return project_state(store.get_all_events())

    @hub_app.get("/health")
    def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "node_id": manifest.node_id,
            "tier": manifest.tier.value,
            "event_count": store.count(),
            "pending_enrichments": len(store.get_pending_enrichments()),
        }

    @hub_app.get("/manifest", response_model=HardwareCapabilityManifest)
    def get_manifest() -> HardwareCapabilityManifest:
        return manifest

    @hub_app.post("/api/v1/triage", response_model=TriageAssessment)
    def run_triage(payload: TriageInput) -> TriageAssessment:
        execution_target = route_workload(manifest, WorkloadKind.DETERMINISTIC_TRIAGE)
        assessment = evaluate_triage(payload)
        assessment = assessment.model_copy(update={"execution_target": execution_target})

        triage_event = CrdtEvent(
            hlc=clock.tick(),
            origin_node_id=manifest.node_id,
            patient_id=assessment.patient_id,
            event_type=EventType.TRIAGE_COMPLETED,
            payload=assessment.model_dump(mode="json"),
        )
        store.append(triage_event)
        return assessment

    def _is_voice_event_ready(event: CrdtEvent) -> bool:
        raw_blob_key = event.payload.get("audio_blob_key")
        if isinstance(raw_blob_key, str) and raw_blob_key.strip():
            try:
                return blob_store.exists(raw_blob_key.strip())
            except ValueError:
                return False
        return True

    @hub_app.post("/api/v1/sync", response_model=SyncEnvelope)
    def sync_envelope(incoming: SyncEnvelope) -> SyncEnvelope:
        peer_registry.record_peer(incoming.sender_manifest, source="sync_http")
        has_pending_triage = any(
            evt.event_type == EventType.TRIAGE_COMPLETED
            and evt.enrichment_state == EnrichmentState.PENDING
            for evt in incoming.events
        )
        has_ready_voice = enable_enrichment_worker and any(
            evt.event_type == EventType.VOICE_NOTE_RECORDED
            and evt.enrichment_state == EnrichmentState.PENDING
            and _is_voice_event_ready(evt)
            for evt in incoming.events
        )
        if has_pending_triage or has_ready_voice:
            clock.receive(incoming.sender_hlc)
            for evt in incoming.events:
                clock.receive(evt.hlc)
            store.apply_remote_events(incoming.events)
            auto_types = None if enable_enrichment_worker else {EventType.TRIAGE_COMPLETED}
            enrichment_worker.run_once(max_jobs=10, event_types=auto_types)
        outcome = reconcile_envelopes(store, clock, manifest, incoming)
        return outcome.response_envelope

    @hub_app.get("/api/v1/patients", response_model=list[PatientRecord])
    def list_patients() -> list[PatientRecord]:
        return list(_projected().patients.values())

    @hub_app.get("/api/v1/action-cards", response_model=list[ActionCard])
    def list_action_cards() -> list[ActionCard]:
        return list(_projected().action_cards.values())

    @hub_app.get("/api/v1/enrichment/pending", response_model=list[CrdtEvent])
    def list_pending_enrichments() -> list[CrdtEvent]:
        return store.get_pending_enrichments()

    @hub_app.put("/api/v1/blobs/{blob_key}", response_model=BlobMetadata)
    async def upload_blob(blob_key: str, request: Request) -> BlobMetadata:
        data = await request.body()
        content_type = request.headers.get("content-type", "application/octet-stream")
        try:
            return blob_store.put(blob_key, data, content_type=content_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @hub_app.head("/api/v1/blobs/{blob_key}")
    def check_blob(blob_key: str) -> Response:
        try:
            exists = blob_store.exists(blob_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if not exists:
            raise HTTPException(status_code=404, detail="Blob not found.")
        return Response(status_code=200)

    @hub_app.get("/api/v1/blobs/{blob_key}")
    def download_blob(blob_key: str) -> Response:
        try:
            result = blob_store.get(blob_key)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Blob not found.")
        data, meta = result
        return Response(
            content=data,
            media_type=meta.content_type,
            headers={"X-Blob-Sha256": meta.sha256},
        )

    @hub_app.websocket("/ws/mesh")
    async def mesh_websocket(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                raw_message = await websocket.receive_json()
                try:
                    incoming = SyncEnvelope.model_validate(raw_message)
                except ValidationError as exc:
                    await websocket.send_json({"error": "invalid_sync_envelope", "detail": exc.errors()})
                    continue
                peer_registry.record_peer(incoming.sender_manifest, source="sync_ws")
                outcome = reconcile_envelopes(store, clock, manifest, incoming)
                await websocket.send_json(outcome.response_envelope.model_dump(mode="json"))
        except WebSocketDisconnect:
            return

    hub_app.include_router(create_enrichment_router(enrichment_worker))
    hub_app.include_router(
        create_discovery_router(
            peer_registry,
            manifest,
            port=port,
            mdns_advertiser=mdns_advertiser,
        )
    )
    hub_app.include_router(
        create_dashboard_router(
            store=store,
            manifest=manifest,
            get_peers=lambda: [
                p.model_dump(mode="json") for p in peer_registry.list_peers()
            ],
            hub_port=port,
        )
    )
    hub_app.include_router(
        create_demo_router(
            store=store,
            blob_store=blob_store,
            clock=clock,
            manifest=manifest,
            registry=peer_registry,
            worker=enrichment_worker,
        )
    )

    repo_root = Path(__file__).resolve().parents[4]
    phone_dir = repo_root / "apps" / "field-pwa"
    if phone_dir.is_dir():
        hub_app.mount(
            "/phone",
            StaticFiles(directory=str(phone_dir), html=True),
            name="field-pwa",
        )
    watch_dir = repo_root / "apps" / "watch-companion"
    if watch_dir.is_dir():
        hub_app.mount(
            "/watch",
            StaticFiles(directory=str(watch_dir), html=True),
            name="watch-companion",
        )
    deck_dir = repo_root / "apps" / "presentation" / "dist"
    hub_app.mount(
        "/deck",
        StaticFiles(directory=str(deck_dir), html=True, check_dir=False),
        name="presentation-deck",
    )

    return hub_app


app = create_app(
    db_path=os.environ.get("AAROGYA_HUB_DB", ".data/phc_hub.db"),
    blob_dir=os.environ.get("AAROGYA_HUB_BLOB_DIR", ".data/blobs"),
    node_id=os.environ.get("AAROGYA_HUB_NODE_ID", "phc-hub-local"),
    port=int(os.environ.get("AAROGYA_HUB_PORT", "8000")),
    enable_mdns=os.environ.get("AAROGYA_HUB_ENABLE_MDNS", "0") == "1",
    enable_enrichment_worker=os.environ.get("AAROGYA_HUB_ENABLE_WORKER", "1") == "1",
    enrichment_interval_sec=float(
        os.environ.get("AAROGYA_HUB_ENRICHMENT_INTERVAL_SEC", "5.0")
    ),
)
