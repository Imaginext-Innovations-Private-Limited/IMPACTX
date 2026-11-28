"""Append-only SQLite Event Store with idempotent deduplication and peer cursors."""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aarogya_contracts import CrdtEvent, EnrichmentState, EventType, HlcTimestamp
from aarogya_crdt_sync.hlc import default_wall_ms

SEQ_CURSOR_PREFIX = "seq:"
_UNSET: Any = object()


class PeerCursor(BaseModel):
    """Persisted bidirectional sync watermark tracked per remote peer node."""

    model_config = ConfigDict(extra="forbid")

    peer_node_id: str = Field(..., min_length=1, max_length=128)
    last_received_cursor: str | None = Field(default=None, max_length=256)
    last_sent_cursor: str | None = Field(default=None, max_length=256)
    last_sync_ms: int = Field(..., ge=0)


class SyncResult(BaseModel):
    """Outcome of applying a batch of remote CRDT events to a local EventStore."""

    model_config = ConfigDict(extra="forbid")

    inserted: int = Field(..., ge=0)
    duplicates: int = Field(..., ge=0)
    pending_enrichments: list[CrdtEvent] = Field(default_factory=list)
    inserted_event_ids: list[str] = Field(default_factory=list)
    latest_cursor: str | None = Field(default=None, max_length=256)

    @property
    def pending_enrichment_count(self) -> int:
        """Convenience count of unresolved pending enrichment events."""
        return len(self.pending_enrichments)


def format_seq_cursor(seq: int) -> str:
    """Format a local SQLite append sequence number as a cursor string."""
    if seq < 0:
        raise ValueError("Sequence number must be non-negative")
    return f"{SEQ_CURSOR_PREFIX}{seq:016d}"


def parse_seq_cursor(cursor: str) -> int:
    """Parse a ``seq:<digits>`` cursor into its integer sequence number."""
    if not cursor.startswith(SEQ_CURSOR_PREFIX):
        raise ValueError(f"Not a sequence cursor: {cursor!r}")
    raw = cursor[len(SEQ_CURSOR_PREFIX) :]
    try:
        seq = int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid sequence cursor: {cursor!r}") from exc
    if seq < 0:
        raise ValueError(f"Sequence cursor cannot be negative: {cursor!r}")
    return seq


class EventStore:
    """Local append-only SQLite event store for autonomous edge mesh nodes.

    Guarantees:
    - Append-only immutable storage of :class:`CrdtEvent` records.
    - Idempotent deduplication by ``event_id`` (replaying identical events is a no-op).
    - Fast cursor-based delta queries supporting both local arrival sequence cursors
      (``seq:...``, safe under multi-hop transitive sync with late-arriving older HLCs)
      and HLC sort-key cursors (``wall_ms:logical:node_id``).
    - Persisted ``peer_cursors`` table for tracking bidirectional sync progress per peer.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = str(db_path)
        self._lock = threading.RLock()
        if self._db_path != ":memory:":
            Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._configure_and_init()

    def _configure_and_init(self) -> None:
        with self._lock:
            if self._db_path != ":memory:":
                self._conn.execute("PRAGMA journal_mode=WAL;")
                self._conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn.execute("PRAGMA foreign_keys=ON;")
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS events (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_id TEXT NOT NULL UNIQUE,
                    hlc_sort_key TEXT NOT NULL,
                    hlc_wall_ms INTEGER NOT NULL,
                    hlc_logical INTEGER NOT NULL,
                    hlc_node_id TEXT NOT NULL,
                    origin_node_id TEXT NOT NULL,
                    patient_id TEXT,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    enrichment_state TEXT NOT NULL,
                    ref_event_id TEXT,
                    received_at_ms INTEGER NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_events_hlc_sort_key
                    ON events (hlc_sort_key, event_id);
                CREATE INDEX IF NOT EXISTS idx_events_patient_id
                    ON events (patient_id);
                CREATE INDEX IF NOT EXISTS idx_events_enrichment
                    ON events (enrichment_state, event_type);
                CREATE INDEX IF NOT EXISTS idx_events_ref_event_id
                    ON events (ref_event_id);

                CREATE TABLE IF NOT EXISTS peer_cursors (
                    peer_node_id TEXT PRIMARY KEY,
                    last_received_cursor TEXT,
                    last_sent_cursor TEXT,
                    last_sync_ms INTEGER NOT NULL
                );
                """
            )
            self._conn.commit()

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        with self._lock:
            self._conn.close()

    def __enter__(self) -> EventStore:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.close()

    @staticmethod
    def _row_to_event(row: sqlite3.Row) -> CrdtEvent:
        return CrdtEvent(
            event_id=row["event_id"],
            hlc=HlcTimestamp(
                wall_ms=row["hlc_wall_ms"],
                logical=row["hlc_logical"],
                node_id=row["hlc_node_id"],
            ),
            origin_node_id=row["origin_node_id"],
            patient_id=row["patient_id"],
            event_type=EventType(row["event_type"]),
            payload=json.loads(row["payload_json"]),
            enrichment_state=EnrichmentState(row["enrichment_state"]),
            ref_event_id=row["ref_event_id"],
        )

    def _insert_event_cursor(
        self,
        cur: sqlite3.Cursor,
        event: CrdtEvent,
        received_at_ms: int,
    ) -> bool:
        cur.execute(
            """
            INSERT OR IGNORE INTO events (
                event_id,
                hlc_sort_key,
                hlc_wall_ms,
                hlc_logical,
                hlc_node_id,
                origin_node_id,
                patient_id,
                event_type,
                payload_json,
                enrichment_state,
                ref_event_id,
                received_at_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.event_id,
                event.hlc.to_sort_key(),
                event.hlc.wall_ms,
                event.hlc.logical,
                event.hlc.node_id,
                event.origin_node_id,
                event.patient_id,
                event.event_type.value,
                json.dumps(event.payload, sort_keys=True, separators=(",", ":")),
                event.enrichment_state.value,
                event.ref_event_id,
                received_at_ms,
            ),
        )
        return cur.rowcount == 1

    def append(self, event: CrdtEvent, *, received_at_ms: int | None = None) -> bool:
        """Append a single local or remote event idempotently.

        Returns:
            ``True`` if inserted, ``False`` if ``event.event_id`` already existed.
        """
        ts = default_wall_ms() if received_at_ms is None else received_at_ms
        with self._lock:
            cur = self._conn.cursor()
            inserted = self._insert_event_cursor(cur, event, ts)
            self._conn.commit()
            return inserted

    def apply_remote_events(
        self,
        events: Iterable[CrdtEvent],
        *,
        received_at_ms: int | None = None,
    ) -> SyncResult:
        """Apply a batch of remote events atomically with idempotent deduplication."""
        ts = default_wall_ms() if received_at_ms is None else received_at_ms
        inserted = 0
        duplicates = 0
        inserted_ids: list[str] = []

        with self._lock:
            cur = self._conn.cursor()
            try:
                for event in events:
                    if self._insert_event_cursor(cur, event, ts):
                        inserted += 1
                        inserted_ids.append(event.event_id)
                    else:
                        duplicates += 1
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

            pending = self.get_pending_enrichments()
            latest_cursor = self.get_latest_cursor()

        return SyncResult(
            inserted=inserted,
            duplicates=duplicates,
            pending_enrichments=pending,
            inserted_event_ids=inserted_ids,
            latest_cursor=latest_cursor,
        )

    def get_delta_since(
        self,
        cursor: str | None = None,
        *,
        limit: int | None = None,
        exclude_origin_node: str | None = None,
        exclude_event_ids: Iterable[str] | None = None,
    ) -> list[CrdtEvent]:
        """Return events strictly newer than ``cursor``.

        Cursor modes:
        - ``None`` or ``""``: all events ordered by ``(hlc_sort_key, event_id)``.
        - ``"seq:<16-digit-int>"``: events with local arrival ``seq > <int>`` ordered by ``seq``.
        - ``"<wall_ms>:<logical>:<node_id>"``: events with ``hlc_sort_key > cursor`` ordered by
          ``(hlc_sort_key, event_id)``.
        """
        if limit is not None and limit <= 0:
            return []

        excluded_set = set(exclude_event_ids) if exclude_event_ids else set()
        clauses: list[str] = []
        params: list[Any] = []
        order_by = "hlc_sort_key ASC, event_id ASC"

        if cursor:
            if cursor.startswith(SEQ_CURSOR_PREFIX):
                seq_num = parse_seq_cursor(cursor)
                clauses.append("seq > ?")
                params.append(seq_num)
                order_by = "seq ASC"
            else:
                clauses.append("hlc_sort_key > ?")
                params.append(cursor)

        if exclude_origin_node is not None:
            clauses.append("origin_node_id != ?")
            params.append(exclude_origin_node)

        where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        sql = f"SELECT * FROM events {where_sql} ORDER BY {order_by}"

        if limit is not None and not excluded_set:
            sql += " LIMIT ?"
            params.append(limit)

        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()

        events: list[CrdtEvent] = []
        for row in rows:
            if row["event_id"] in excluded_set:
                continue
            events.append(self._row_to_event(row))
            if limit is not None and len(events) >= limit:
                break
        return events

    def get_all_events(self) -> list[CrdtEvent]:
        """Return every stored event in canonical HLC total order."""
        return self.get_delta_since(None)

    def get_events_for_patient(self, patient_id: str) -> list[CrdtEvent]:
        """Return all events referencing ``patient_id`` in canonical HLC order."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT * FROM events
                WHERE patient_id = ?
                ORDER BY hlc_sort_key ASC, event_id ASC
                """,
                (patient_id,),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_event(self, event_id: str) -> CrdtEvent | None:
        """Fetch a single event by ``event_id``, or ``None`` if absent."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM events WHERE event_id = ?",
                (event_id,),
            ).fetchone()
        return self._row_to_event(row) if row is not None else None

    def get_pending_enrichments(self) -> list[CrdtEvent]:
        """Return ``PENDING`` events lacking a corresponding ``ENRICHMENT_COMPLETED`` event."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT e.*
                FROM events AS e
                WHERE e.enrichment_state = ?
                  AND NOT EXISTS (
                      SELECT 1
                      FROM events AS c
                      WHERE c.event_type = ?
                        AND c.ref_event_id = e.event_id
                  )
                ORDER BY e.hlc_sort_key ASC, e.event_id ASC
                """,
                (
                    EnrichmentState.PENDING.value,
                    EventType.ENRICHMENT_COMPLETED.value,
                ),
            ).fetchall()
        return [self._row_to_event(row) for row in rows]

    def get_latest_cursor(self) -> str | None:
        """Return the latest local append sequence cursor (``seq:...``), or ``None`` if empty."""
        with self._lock:
            row = self._conn.execute("SELECT MAX(seq) AS max_seq FROM events").fetchone()
        if row is None or row["max_seq"] is None:
            return None
        return format_seq_cursor(int(row["max_seq"]))

    def get_latest_hlc(self) -> HlcTimestamp | None:
        """Return the highest HLC timestamp currently stored, or ``None`` if empty."""
        with self._lock:
            row = self._conn.execute(
                """
                SELECT hlc_wall_ms, hlc_logical, hlc_node_id
                FROM events
                ORDER BY hlc_sort_key DESC, event_id DESC
                LIMIT 1
                """
            ).fetchone()
        if row is None:
            return None
        return HlcTimestamp(
            wall_ms=row["hlc_wall_ms"],
            logical=row["hlc_logical"],
            node_id=row["hlc_node_id"],
        )

    def count(self) -> int:
        """Return total number of unique events persisted in this store."""
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS cnt FROM events").fetchone()
        return int(row["cnt"]) if row is not None else 0

    def get_peer_cursor(self, peer_node_id: str) -> PeerCursor | None:
        """Fetch stored sync cursor metadata for ``peer_node_id``."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM peer_cursors WHERE peer_node_id = ?",
                (peer_node_id,),
            ).fetchone()
        if row is None:
            return None
        return PeerCursor(
            peer_node_id=row["peer_node_id"],
            last_received_cursor=row["last_received_cursor"],
            last_sent_cursor=row["last_sent_cursor"],
            last_sync_ms=row["last_sync_ms"],
        )

    def set_peer_cursor(
        self,
        peer_node_id: str,
        *,
        last_received_cursor: str | None = _UNSET,
        last_sent_cursor: str | None = _UNSET,
        synced_at_ms: int | None = None,
    ) -> PeerCursor:
        """Upsert sync cursors for ``peer_node_id``, preserving omitted cursor fields."""
        ts = default_wall_ms() if synced_at_ms is None else synced_at_ms
        with self._lock:
            existing = self.get_peer_cursor(peer_node_id)
            next_received = (
                existing.last_received_cursor if existing is not None else None
            ) if last_received_cursor is _UNSET else last_received_cursor
            next_sent = (
                existing.last_sent_cursor if existing is not None else None
            ) if last_sent_cursor is _UNSET else last_sent_cursor

            self._conn.execute(
                """
                INSERT INTO peer_cursors (
                    peer_node_id,
                    last_received_cursor,
                    last_sent_cursor,
                    last_sync_ms
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(peer_node_id) DO UPDATE SET
                    last_received_cursor = excluded.last_received_cursor,
                    last_sent_cursor = excluded.last_sent_cursor,
                    last_sync_ms = excluded.last_sync_ms
                """,
                (peer_node_id, next_received, next_sent, ts),
            )
            self._conn.commit()
            return PeerCursor(
                peer_node_id=peer_node_id,
                last_received_cursor=next_received,
                last_sent_cursor=next_sent,
                last_sync_ms=ts,
            )

    def list_peer_cursors(self) -> list[PeerCursor]:
        """Return all persisted peer cursors ordered by ``peer_node_id``."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM peer_cursors ORDER BY peer_node_id ASC"
            ).fetchall()
        return [
            PeerCursor(
                peer_node_id=row["peer_node_id"],
                last_received_cursor=row["last_received_cursor"],
                last_sent_cursor=row["last_sent_cursor"],
                last_sync_ms=row["last_sync_ms"],
            )
            for row in rows
        ]
