import "fake-indexeddb/auto";
import { IDBFactory } from "fake-indexeddb";
import type { CrdtEvent, SyncEnvelope } from "../../../../packages/contracts/ts/index";
import { openStore } from "../../src/core";

let n = 0;
export const freshStore = (factory = new IDBFactory()) => openStore("phone-1", `sync-test-${n++}`, factory);

export const hubEvent = (id: string, wall: number, over: Partial<CrdtEvent> = {}): CrdtEvent => ({
  event_id: id,
  hlc: { wall_ms: wall, logical: 0, node_id: "hub" },
  origin_node_id: "hub",
  patient_id: null,
  event_type: "OUTBREAK_ALERT_RAISED",
  payload: {},
  enrichment_state: "NOT_NEEDED",
  ref_event_id: null,
  ...over,
});

export const reply = (over: Partial<SyncEnvelope> = {}): SyncEnvelope => ({
  envelope_id: "r",
  sender_manifest: {
    node_id: "hub", tier: "TIER_2_HUB", ram_mb: 32768, cpu_cores: 16, battery_pct: 100,
    has_npu: false, installed_models: [], watch_mode: null,
  },
  sender_hlc: { wall_ms: 1, logical: 0, node_id: "hub" },
  since_cursor: null,
  next_cursor: null,
  events: [],
  ack_event_ids: [],
  schema_version: "1.0.0",
  ...over,
});

/** Fake fetch that records sent envelopes and answers with `respond(sent)`. */
export function fakeFetch(respond: (sent: SyncEnvelope) => SyncEnvelope | Error | number) {
  const sent: SyncEnvelope[] = [];
  const fn = (async (_url: string, init: RequestInit) => {
    const env = JSON.parse(String(init.body)) as SyncEnvelope;
    sent.push(env);
    const r = respond(env);
    if (r instanceof Error) throw r;
    if (typeof r === "number") return new Response("nope", { status: r });
    return new Response(JSON.stringify(r), { status: 200 });
  }) as unknown as typeof fetch;
  return { fn, sent };
}
