import type {
  ActionCard,
  CrdtEvent,
  HlcTimestamp,
  PatientRecord,
} from "../../../../packages/contracts/ts/index";

export type { ActionCard, CrdtEvent, HlcTimestamp, PatientRecord };

/** Durable offline store. All methods resolve with no network dependency. */
export interface FieldStore {
  readonly nodeId: string;
  /** Local HLC tick (persisted). Strictly increasing across reloads. */
  tick(nowMs?: number): Promise<HlcTimestamp>;
  /** Merge a remote HLC (standard HLC receive rule, persisted). */
  receive(remote: HlcTimestamp, nowMs?: number): Promise<HlcTimestamp>;
  /** Append to log, idempotent by event_id. Also enqueues in outbox unless `outbox: false` (use that for remote-origin events). Returns true if newly added. */
  appendEvent(event: CrdtEvent, opts?: { outbox?: boolean }): Promise<boolean>;
  /** All events sorted by HLC (wall_ms, logical, node_id). */
  getAllEvents(): Promise<CrdtEvent[]>;
  getEvent(eventId: string): Promise<CrdtEvent | undefined>;
  /** Unsent events (outbox), HLC-ordered. */
  getPendingEvents(): Promise<CrdtEvent[]>;
  /** Remove only the given ids from the outbox (events stay in the log). */
  markAcked(eventIds: string[]): Promise<void>;
  getCursor(): Promise<string | null>;
  setCursor(cursor: string | null): Promise<void>;
  putPatient(p: PatientRecord): Promise<void>;
  getPatient(patientId: string): Promise<PatientRecord | undefined>;
  listPatients(): Promise<PatientRecord[]>;
  putActionCard(c: ActionCard): Promise<void>;
  listActionCards(): Promise<ActionCard[]>;
  close(): void;
}
