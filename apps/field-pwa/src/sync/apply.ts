/** Apply a hub reply envelope to the durable store (mirrors apply_sync_response). */
import type { ActionCard, CrdtEvent, HlcTimestamp, SyncEnvelope } from "../../../../packages/contracts/ts/index";
import type { FieldStore } from "../core";
import { project } from "./project";

const EVENT_TYPES = new Set([
  "PATIENT_REGISTERED", "TRIAGE_COMPLETED", "CHECKLIST_RECORDED", "VACCINATION_LOGGED",
  "VOICE_NOTE_RECORDED", "ENRICHMENT_COMPLETED", "ACTION_CARD_ISSUED", "OUTBREAK_ALERT_RAISED",
]);
const ENRICHMENT_STATES = new Set(["NOT_NEEDED", "PENDING", "COMPLETED", "FAILED"]);
const nullableStr = (v: unknown) => v === null || typeof v === "string";

export function isHlc(v: unknown): v is HlcTimestamp {
  const h = v as HlcTimestamp | null;
  return !!h && Number.isFinite(h.wall_ms) && Number.isInteger(h.logical) && typeof h.node_id === "string";
}

/** Structural check only: payload contents are validated later, per view, in project(). */
export function isCrdtEvent(v: unknown): v is CrdtEvent {
  const e = v as CrdtEvent | null;
  return (
    !!e && typeof e.event_id === "string" && e.event_id.length > 0 && isHlc(e.hlc) &&
    typeof e.origin_node_id === "string" && nullableStr(e.patient_id) &&
    EVENT_TYPES.has(e.event_type) && ENRICHMENT_STATES.has(e.enrichment_state) &&
    nullableStr(e.ref_event_id) && typeof e.payload === "object" && e.payload !== null
  );
}

export function isSyncEnvelope(v: unknown): v is SyncEnvelope {
  const s = v as SyncEnvelope | null;
  return (
    !!s && typeof s === "object" && isHlc(s.sender_hlc) && Array.isArray(s.events) &&
    Array.isArray(s.ack_event_ids) && nullableStr(s.next_cursor ?? null)
  );
}

export interface ApplyResult {
  newEvents: CrdtEvent[];
  rejected: number;
  cards: ActionCard[];
  patientsUpdated: string[];
  pendingEnrichments: number;
}

/** Pending-enrichment count over the whole local log (PENDING with no ENRICHMENT_COMPLETED ref). */
export async function countPendingEnrichments(store: FieldStore): Promise<number> {
  return project(await store.getAllEvents()).pendingEnrichments.length;
}

/** Re-fold the log and write the patient/card views touched by `events` (LWW, like projector.py). */
export async function materialize(
  store: FieldStore,
  events: CrdtEvent[],
): Promise<Pick<ApplyResult, "cards" | "patientsUpdated" | "pendingEnrichments">> {
  const proj = project(await store.getAllEvents());
  const touchedPatients = new Set<string>();
  const touchedCards = new Set<string>();
  for (const e of events) {
    const p = e.payload as Record<string, unknown>;
    if (e.event_type === "PATIENT_REGISTERED") {
      const pid = e.patient_id ?? p.patient_id;
      if (typeof pid === "string") touchedPatients.add(pid);
    } else if (e.event_type === "ACTION_CARD_ISSUED" || e.event_type === "CHECKLIST_RECORDED") {
      touchedCards.add(typeof p.card_id === "string" && p.card_id ? p.card_id : e.event_id);
    }
  }
  const patientsUpdated: string[] = [];
  for (const pid of touchedPatients) {
    const rec = proj.patients.get(pid);
    if (rec) { await store.putPatient(rec); patientsUpdated.push(pid); }
  }
  const cards: ActionCard[] = [];
  for (const cid of touchedCards) {
    const card = proj.cards.get(cid);
    if (card) { await store.putActionCard(card); cards.push(card); }
  }

  return { cards, patientsUpdated, pendingEnrichments: proj.pendingEnrichments.length };
}

/** Re-fold the whole log and write every patient/card view, so views converge even after a crash mid-apply. */
export async function rebuildViews(store: FieldStore): Promise<number> {
  const proj = project(await store.getAllEvents());
  for (const p of proj.patients.values()) await store.putPatient(p);
  for (const c of proj.cards.values()) await store.putActionCard(c);
  return proj.pendingEnrichments.length;
}

/**
 * Order matters for crash safety: events are persisted before the outbox is
 * trimmed and before the cursor advances, so a crash mid-apply just causes a
 * harmless (idempotent) re-delivery next time (views are repaired by rebuildViews).
 *
 * `sentIds`: ids actually sent in the matching envelope; acks for anything else
 * are ignored so a misbehaving hub cannot drop unsent outbox events.
 *
 * Rejected (structurally invalid) events: valid events are still applied and
 * acks still honoured, but the cursor is NOT advanced, so the rejected event is
 * re-offered next sync instead of being silently skipped. This cannot wedge sync:
 * valid events keep flowing (idempotently) and the count is surfaced to the UI.
 */
export async function applyResponse(
  store: FieldStore,
  reply: SyncEnvelope,
  sentIds?: Iterable<string>,
): Promise<ApplyResult> {
  await store.receive(reply.sender_hlc);
  const newEvents: CrdtEvent[] = [];
  let rejected = 0;
  for (const e of reply.events) {
    if (!isCrdtEvent(e)) { rejected++; continue; }
    await store.receive(e.hlc);
    if (await store.appendEvent(e, { outbox: false })) newEvents.push(e);
  }

  const { cards, patientsUpdated, pendingEnrichments } = await materialize(store, newEvents);

  const allowed = sentIds ? new Set(sentIds) : null;
  const acks = reply.ack_event_ids.filter(
    (id): id is string => typeof id === "string" && (!allowed || allowed.has(id)),
  );
  if (acks.length) await store.markAcked(acks);
  if (rejected === 0 && typeof reply.next_cursor === "string") await store.setCursor(reply.next_cursor);

  return { newEvents, rejected, cards, patientsUpdated, pendingEnrichments };
}
