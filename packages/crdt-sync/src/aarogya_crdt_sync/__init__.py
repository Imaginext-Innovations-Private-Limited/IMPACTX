"""Aarogya Mesh Event-Sourced HLC + CRDT Delta Sync Engine."""

from aarogya_crdt_sync.hlc import (
    ClockDriftError,
    HlcClock,
    compare_hlc,
    hlc_sort_key,
    parse_hlc_sort_key,
)
from aarogya_crdt_sync.projector import ProjectedState, project_state
from aarogya_crdt_sync.protocol import (
    ReconcileOutcome,
    apply_sync_response,
    build_sync_envelope,
    reconcile_envelopes,
    select_offloadable_jobs,
    sync_peers,
)
from aarogya_crdt_sync.store import EventStore, PeerCursor, SyncResult

__all__ = [
    "ClockDriftError",
    "EventStore",
    "HlcClock",
    "PeerCursor",
    "ProjectedState",
    "ReconcileOutcome",
    "SyncResult",
    "apply_sync_response",
    "build_sync_envelope",
    "compare_hlc",
    "hlc_sort_key",
    "parse_hlc_sort_key",
    "project_state",
    "reconcile_envelopes",
    "select_offloadable_jobs",
    "sync_peers",
]
