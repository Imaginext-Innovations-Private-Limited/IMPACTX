import type { ActionCard, CrdtEvent, HlcTimestamp, PatientRecord } from "../../../../packages/contracts/ts/index";
import { compareHlc } from "../core/hlc";
import type { SyncState } from "../sync/emitter";

export interface CrdtNodeProof {
  nodeId: string;
  latestHlc: string;
  eventCount: number;
  pendingCount: number;
  status: SyncState;
}

/** Format an HLC timestamp canonically as `wall_ms:logical:node_id`. */
export function formatHlcVector(hlc: HlcTimestamp): string {
  return `${hlc.wall_ms}:${hlc.logical}:${hlc.node_id}`;
}

/** Pure summary of local IndexedDB CRDT event log & causal HLC head for the Sync Proof card. */
export function buildCrdtNodeProof(
  nodeId: string,
  events: readonly CrdtEvent[],
  pendingCount: number,
  status: SyncState,
): CrdtNodeProof {
  let latest: HlcTimestamp | null = null;
  for (const e of events) {
    if (latest === null || compareHlc(e.hlc, latest) > 0) latest = e.hlc;
  }
  return {
    nodeId,
    latestHlc: latest ? formatHlcVector(latest) : `0:0:${nodeId}`,
    eventCount: events.length,
    pendingCount,
    status,
  };
}

const PRIO = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 } as const;

/** Cards for this phone, open first, then by priority. */
export function sortCards(cards: ActionCard[]): ActionCard[] {
  const open = (c: ActionCard) => (c.status === "OPEN" ? 0 : 1);
  return [...cards].sort((a, b) => open(a) - open(b) || PRIO[a.priority] - PRIO[b.priority] || a.card_id.localeCompare(b.card_id));
}

/** Local-first ack: minimal LWW status update, keyed by card_id (the projector merges it). */
export const ackPayload = (card: ActionCard) => ({ card_id: card.card_id, status: "ACKNOWLEDGED" as const });

/** Who a card is about: local name + village when known, else the raw id. */
export function cardPatientLabel(
  patientId: string | null,
  patients: ReadonlyMap<string, Pick<PatientRecord, "full_name" | "village_id">>,
): { name: string; village: string | null } | null {
  if (patientId === null) return null;
  const p = patients.get(patientId);
  return p ? { name: p.full_name, village: p.village_id } : { name: patientId, village: null };
}

/**
 * Wire each source to `set`; the first update that arrives while `isAlive()` is false
 * unsubscribes every source and writes nothing. Returns the unsubscribe-all function.
 */
export function bindLiveCount(
  sources: ReadonlyArray<(listener: (n: number) => void) => () => void>,
  isAlive: () => boolean,
  set: (n: number) => void,
): () => void {
  const offs: Array<() => void> = [];
  const off = () => offs.splice(0).forEach((f) => f());
  const listener = (n: number) => (isAlive() ? set(n) : off());
  for (const s of sources) offs.push(s(listener));
  return off;
}

/** Classify a failed sync into a structured detail token so the UI can show actionable feedback. */
export function classifySyncFailure(kind: SyncState, rawError: string | null | undefined, isOnline: boolean): string {
  if (!isOnline) return "offline:device";
  if (kind === "offline") return "offline:unreachable";
  const httpMatch = rawError?.match(/HTTP (\d{3})/);
  if (httpMatch) return `http:${httpMatch[1]}`;
  return rawError ? rawError.slice(0, 120) : kind;
}

export type ParsedSyncFailure =
  | { kind: "device_offline" }
  | { kind: "unreachable" }
  | { kind: "http"; code: string }
  | { kind: "other"; detail: string };

/** Parse a stored `lastSync.detail` failure token into a typed classification. */
export function parseSyncFailureDetail(detail: string): ParsedSyncFailure {
  if (detail === "offline:device" || detail === "offline") return { kind: "device_offline" };
  if (detail === "offline:unreachable") return { kind: "unreachable" };
  if (detail.startsWith("http:")) return { kind: "http", code: detail.slice(5) };
  return { kind: "other", detail };
}
