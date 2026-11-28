# `aarogya-crdt-sync`

Event-Sourced **Hybrid Logical Clock (HLC) + CRDT Delta Sync Engine** for **Aarogya Mesh**.

## 1. The Autonomy Invariant

Every node tier — **Tier-0 Watch** (`TIER_0_WATCH`), **Tier-1 CHW Phone** (`TIER_1_PHONE`), and **Tier-2 PHC Hub** (`TIER_2_HUB`) — operates **100% standalone indefinitely with zero synchronous RPC coupling**.

- Clinical intake, deterministic triage, vaccination logging, and voice-note capture append immutable `CrdtEvent` records directly to the node's local SQLite `EventStore`.
- When two peers happen to enter local range (Wi-Fi Hotspot, LAN, mDNS, WebSocket, or BLE — zero internet), they exchange `SyncEnvelope` deltas and deterministically converge to identical materialized state (**strong eventual consistency**).
- Heavy ML workloads (Indic ASR, clinical note structuring) are never remote procedure calls: a Watch or Phone simply appends an event with `enrichment_state=PENDING`. When a Tier-2 Hub eventually receives that event, it selects the job locally via `select_offloadable_jobs(...)`, appends `ENRICHMENT_COMPLETED(ref_event_id=...)` + `ACTION_CARD_ISSUED`, and those new events flow back on the next sync.

## 2. HLC Ordering & Replication Cursors

### Total Ordering & Tie-Breaking (`hlc.py`)
`HlcClock` implements Kulkarni et al.'s Hybrid Logical Clock using `aarogya_contracts.HlcTimestamp`:

- `tick()` advances `(wall_ms, logical)` monotonically against local physical time.
- `receive(remote_hlc)` advances local time strictly past `max(local, remote, physical)` so causal chains are always preserved across disconnected nodes.
- Ties on identical `(wall_ms, logical)` are broken deterministically by `node_id` (`(wall_ms, logical, node_id)`), with `event_id` as final canonical tie-breaker in the projector.

### Why Local Sequence Cursors (`seq:...`) Matter (`store.py`)
In a 3-node mesh (Watch ↔ Phone ↔ Hub), Watch may create an event at `t=1000` while offline, sync with Phone *after* Phone already synced with Hub at `t=3000`. If Phone tracked Hub's watermark using raw HLC timestamps (`> 3000`), Watch's late-arriving `t=1000` event would be skipped!

`EventStore` solves this cleanly:
- Peer replication cursors use local append sequence watermarks (`seq:0000000000000042`), ensuring multi-hop transitive sync **never** misses older-HLC events that arrive later.
- `get_delta_since(cursor)` also accepts raw `HlcTimestamp.to_sort_key()` cursors for direct HLC-range queries.

## 3. CRDT Merge Semantics (`projector.py`)

`project_state(events)` deduplicates by `event_id`, sorts canonically by `(hlc, event_id)`, and folds into `ProjectedState`:

| View | CRDT Strategy | Conflict Resolution |
| :--- | :--- | :--- |
| `patients` | Per-field **LWW-Element-Map** (including per-key `metadata`) | Concurrent offline edits to different fields merge without data loss; same-field conflicts resolve deterministically by HLC. |
| `triage_history` | **Add-Wins Set** (deduplicated by `assessment_id`) | Preserves all assessments in HLC order. |
| `vaccinations` | Per-patient **Add-Wins Set** keyed by `(vaccine_code, dose_label)` | Latest HLC wins for dose status progression (`DUE_SOON` → `COMPLETED`). |
| `action_cards` | **Add-Wins Set** with **per-field LWW** | Watch/Phone `ACKNOWLEDGED`/`COMPLETED` status updates are never clobbered by replayed `OPEN` creation events. |
| `pending_enrichments` | Set difference (`PENDING` minus `ENRICHMENT_COMPLETED.ref_event_id`) | Automatically drops to `0` across all nodes once Hub's completion event syncs back. |

## 4. Teammate Integration Guide

### `services/phc-hub` (FastAPI `POST /api/v1/sync`)
```python
from aarogya_contracts import SyncEnvelope
from aarogya_crdt_sync import (
    EventStore,
    HlcClock,
    project_state,
    reconcile_envelopes,
)

store = EventStore("data/hub_events.db")
clock = HlcClock(node_id=hub_manifest.node_id)

# Inside POST /api/v1/sync:
outcome = reconcile_envelopes(store, clock, hub_manifest, incoming_envelope)
# outcome.offloadable_jobs -> hand off to services/ml-pipeline worker
# return outcome.response_envelope

# Inside GET /api/v1/patients or GET /api/v1/action-cards:
state = project_state(store.get_all_events())
```

### `services/ml-pipeline` (Deferred Enrichment Worker)
```python
from aarogya_contracts import CrdtEvent, EnrichmentState, EventType
from aarogya_crdt_sync import select_offloadable_jobs

jobs = select_offloadable_jobs(hub_manifest, store.get_pending_enrichments())
for job in jobs:
    # 1. Run local ASR / GBNF structurer on job.payload
    # 2. Append ENRICHMENT_COMPLETED referencing ref_event_id=job.event_id
    store.append(
        CrdtEvent(
            hlc=clock.tick(),
            origin_node_id=hub_manifest.node_id,
            patient_id=job.patient_id,
            event_type=EventType.ENRICHMENT_COMPLETED,
            payload={"transcript": "..."},
            enrichment_state=EnrichmentState.COMPLETED,
            ref_event_id=job.event_id,
        )
    )
```

### `apps/field-pwa` & `apps/watch-companion`
Exchange JSON-serialized `SyncEnvelope` objects matching `packages/contracts/ts/index.ts` with `POST /api/v1/sync` or `WS /ws/mesh`. Persist `response.next_cursor` locally and pass it as `since_cursor` on subsequent reconnects.
