"""Peer-to-peer delta sync protocol and capability-aware enrichment job selector.

Nodes exchange :class:`SyncEnvelope` payloads opportunistically over local LAN,
Wi-Fi Hotspot, WebSocket, or BLE without central coordination or synchronous RPC.
"""

from __future__ import annotations

from collections.abc import Iterable

from pydantic import BaseModel, ConfigDict, Field

from aarogya_contracts import (
    CrdtEvent,
    EnrichmentState,
    EventType,
    HardwareCapabilityManifest,
    NodeTier,
    SyncEnvelope,
)
from aarogya_crdt_sync.hlc import HlcClock
from aarogya_crdt_sync.store import EventStore, SyncResult

_HUB_MIN_RAM_MB = 4096
_HUB_MIN_BATTERY_PCT = 15
_PHONE_MIN_RAM_MB = 2048
_PHONE_ASR_MIN_RAM_MB = 4096
_PHONE_MIN_BATTERY_PCT = 20
_ASR_MODEL_HINTS = ("whisper", "asr", "stt")


class ReconcileOutcome(BaseModel):
    """Result of reconciling an incoming peer SyncEnvelope against local node state."""

    model_config = ConfigDict(extra="forbid")

    sync_result: SyncResult
    response_envelope: SyncEnvelope
    offloadable_jobs: list[CrdtEvent] = Field(default_factory=list)


def _advance_clock_from_envelope(clock: HlcClock, envelope: SyncEnvelope) -> None:
    clock.receive(envelope.sender_hlc)
    for event in envelope.events:
        clock.receive(event.hlc)


def _has_installed_asr_model(manifest: HardwareCapabilityManifest) -> bool:
    for model_name in manifest.installed_models:
        lower = model_name.lower()
        if any(hint in lower for hint in _ASR_MODEL_HINTS):
            return True
    return False


def _job_priority_key(event: CrdtEvent) -> tuple[int, int, int, str, str]:
    severity = str(event.payload.get("severity", "")).upper()
    priority = str(event.payload.get("priority", "")).upper()
    urgent_rank = 0 if (severity == "RED_EMERGENCY" or priority == "CRITICAL") else 1
    return (
        urgent_rank,
        event.hlc.wall_ms,
        event.hlc.logical,
        event.hlc.node_id,
        event.event_id,
    )


def select_offloadable_jobs(
    manifest: HardwareCapabilityManifest,
    pending_events: Iterable[CrdtEvent],
) -> list[CrdtEvent]:
    """Select pending enrichment events that ``manifest`` is capable of executing locally.

    Follows the Capability-Proportional Execution Matrix:
    - ``TIER_0_WATCH``: Never claims heavy deferred ML enrichment jobs.
    - ``TIER_1_PHONE``: Only claims jobs when battery >= 20%, RAM meets threshold,
      and a matching local tiny model (or ASR model for voice notes) is installed.
    - ``TIER_2_HUB``: Primary opportunistic enrichment worker (RAM >= 4096 MiB,
      battery >= 15%); respects explicit ``payload["required_model"]`` if requested.

    Urgent jobs (``RED_EMERGENCY`` / ``CRITICAL``) are prioritized ahead of routine
    pending jobs while maintaining deterministic HLC order within each tier.
    """
    candidates = [
        event
        for event in pending_events
        if event.enrichment_state == EnrichmentState.PENDING
    ]
    if not candidates or manifest.tier == NodeTier.TIER_0_WATCH:
        return []

    selected: list[CrdtEvent] = []
    for event in candidates:
        required_model = event.payload.get("required_model")
        if (
            isinstance(required_model, str)
            and required_model
            and required_model not in manifest.installed_models
        ):
            continue

        if manifest.tier == NodeTier.TIER_2_HUB:
            if manifest.ram_mb >= _HUB_MIN_RAM_MB and manifest.battery_pct >= _HUB_MIN_BATTERY_PCT:
                selected.append(event)
            continue

        if manifest.tier == NodeTier.TIER_1_PHONE:
            if manifest.battery_pct < _PHONE_MIN_BATTERY_PCT:
                continue
            if event.event_type == EventType.VOICE_NOTE_RECORDED:
                if manifest.ram_mb >= _PHONE_ASR_MIN_RAM_MB and _has_installed_asr_model(manifest):
                    selected.append(event)
            elif manifest.ram_mb >= _PHONE_MIN_RAM_MB and (
                manifest.has_npu or bool(manifest.installed_models)
            ):
                selected.append(event)

    selected.sort(key=_job_priority_key)
    return selected


def build_sync_envelope(
    store: EventStore,
    clock: HlcClock,
    local_manifest: HardwareCapabilityManifest,
    *,
    peer_node_id: str | None = None,
    since_cursor: str | None = None,
    ack_event_ids: list[str] | None = None,
    max_events: int | None = None,
) -> SyncEnvelope:
    """Build an outbound ``SyncEnvelope`` containing unseen local delta events.

    When ``peer_node_id`` is provided, the local ``peer_cursors`` table supplies:
    - the outgoing watermark (``last_sent_cursor``) to avoid resending old events, and
    - the peer's watermark (``last_received_cursor``) placed into ``since_cursor``
      so the peer returns only its unseen delta in response.
    """
    peer_cursor = store.get_peer_cursor(peer_node_id) if peer_node_id else None
    outbound_from = (
        since_cursor
        if since_cursor is not None
        else (peer_cursor.last_sent_cursor if peer_cursor is not None else None)
    )
    requested_peer_cursor = (
        peer_cursor.last_received_cursor if peer_cursor is not None else None
    )

    events = store.get_delta_since(
        outbound_from,
        limit=max_events,
        exclude_origin_node=peer_node_id,
    )
    next_cursor = store.get_latest_cursor()
    sender_hlc = clock.tick()

    return SyncEnvelope(
        sender_manifest=local_manifest,
        sender_hlc=sender_hlc,
        since_cursor=requested_peer_cursor,
        next_cursor=next_cursor,
        events=events,
        ack_event_ids=list(ack_event_ids or []),
    )


def reconcile_envelopes(
    store: EventStore,
    clock: HlcClock,
    local_manifest: HardwareCapabilityManifest,
    incoming: SyncEnvelope,
    *,
    max_response_events: int | None = None,
) -> ReconcileOutcome:
    """Reconcile an incoming peer ``SyncEnvelope`` and produce the reply delta envelope.

    Steps:
    1. Merge remote HLC timestamps into ``clock`` to preserve causal order.
    2. Apply ``incoming.events`` to ``store`` idempotently.
    3. Compute outbound delta events since the peer's requested ``since_cursor``
       (excluding events originated by the peer or just delivered in ``incoming``).
    4. Persist updated ``peer_cursors`` for the sender node.
    5. Select capability-appropriate pending enrichment jobs via
       :func:`select_offloadable_jobs`.
    """
    peer_id = incoming.sender_manifest.node_id
    _advance_clock_from_envelope(clock, incoming)

    sync_result = store.apply_remote_events(incoming.events)
    incoming_ids = {event.event_id for event in incoming.events}

    existing_peer_cursor = store.get_peer_cursor(peer_id)
    # Honor incoming.since_cursor literally: when a cleared/fresh peer sends None,
    # replay from the beginning instead of skipping events via stale last_sent_cursor.
    peer_wanted_cursor = incoming.since_cursor

    outgoing_events = store.get_delta_since(
        peer_wanted_cursor,
        limit=max_response_events,
        exclude_origin_node=peer_id,
        exclude_event_ids=incoming_ids,
    )
    local_latest_cursor = store.get_latest_cursor()

    store.set_peer_cursor(
        peer_id,
        last_received_cursor=incoming.next_cursor
        if incoming.next_cursor is not None
        else (existing_peer_cursor.last_received_cursor if existing_peer_cursor else None),
        last_sent_cursor=local_latest_cursor,
    )

    response_envelope = SyncEnvelope(
        sender_manifest=local_manifest,
        sender_hlc=clock.tick(),
        since_cursor=incoming.next_cursor,
        next_cursor=local_latest_cursor,
        events=outgoing_events,
        ack_event_ids=[event.event_id for event in incoming.events],
    )

    offloadable_jobs = select_offloadable_jobs(local_manifest, sync_result.pending_enrichments)

    return ReconcileOutcome(
        sync_result=sync_result,
        response_envelope=response_envelope,
        offloadable_jobs=offloadable_jobs,
    )


def apply_sync_response(
    store: EventStore,
    clock: HlcClock,
    response: SyncEnvelope,
) -> SyncResult:
    """Apply a peer's reply ``SyncEnvelope`` on the initiating node and advance cursors."""
    peer_id = response.sender_manifest.node_id
    _advance_clock_from_envelope(clock, response)

    sync_result = store.apply_remote_events(response.events)
    existing_peer_cursor = store.get_peer_cursor(peer_id)
    store.set_peer_cursor(
        peer_id,
        last_received_cursor=response.next_cursor
        if response.next_cursor is not None
        else (existing_peer_cursor.last_received_cursor if existing_peer_cursor else None),
        last_sent_cursor=response.since_cursor
        if response.since_cursor is not None
        else (existing_peer_cursor.last_sent_cursor if existing_peer_cursor else None),
    )
    return sync_result


def sync_peers(
    store_a: EventStore,
    clock_a: HlcClock,
    manifest_a: HardwareCapabilityManifest,
    store_b: EventStore,
    clock_b: HlcClock,
    manifest_b: HardwareCapabilityManifest,
) -> tuple[ReconcileOutcome, SyncResult]:
    """Perform one complete bidirectional delta-sync roundtrip between Node A and Node B."""
    outbound = build_sync_envelope(
        store_a,
        clock_a,
        manifest_a,
        peer_node_id=manifest_b.node_id,
    )
    outcome_on_b = reconcile_envelopes(store_b, clock_b, manifest_b, outbound)
    result_on_a = apply_sync_response(store_a, clock_a, outcome_on_b.response_envelope)
    return outcome_on_b, result_on_a
