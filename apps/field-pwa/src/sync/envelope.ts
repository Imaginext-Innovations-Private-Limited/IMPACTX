/** Envelope + local-event construction from the persisted store. */
import {
  CONTRACT_SCHEMA_VERSION,
  type CrdtEvent,
  type EnrichmentState,
  type EventType,
  type HardwareCapabilityManifest,
  type SyncEnvelope,
} from "../../../../packages/contracts/ts/index";
import type { FieldStore } from "../core";
import { uuid } from "../core/uuid";

export interface ManifestOptions {
  ramMb?: number;
  cpuCores?: number;
  installedModels?: string[];
}

type BatteryNav = { getBattery?: () => Promise<{ level: number }> };

/** Battery % via navigator.getBattery when available; 100 otherwise (or on any error). */
export async function readBatteryPct(nav: unknown = globalThis.navigator): Promise<number> {
  try {
    const getBattery = (nav as BatteryNav | undefined)?.getBattery;
    if (typeof getBattery !== "function") return 100;
    const { level } = await getBattery.call(nav);
    return Number.isFinite(level) ? Math.max(0, Math.min(100, Math.round(level * 100))) : 100;
  } catch {
    return 100;
  }
}

export async function buildManifest(nodeId: string, opts: ManifestOptions = {}): Promise<HardwareCapabilityManifest> {
  const nav = globalThis.navigator as { deviceMemory?: number; hardwareConcurrency?: number } | undefined;
  return {
    node_id: nodeId,
    tier: "TIER_1_PHONE",
    ram_mb: opts.ramMb ?? (nav?.deviceMemory ? nav.deviceMemory * 1024 : 4096),
    cpu_cores: opts.cpuCores ?? nav?.hardwareConcurrency ?? 4,
    battery_pct: await readBatteryPct(),
    has_npu: false,
    installed_models: opts.installedModels ?? [],
    watch_mode: null,
  };
}

/** Envelope from the PERSISTED outbox and cursor; sender_hlc is a fresh durable tick. */
export async function buildEnvelope(store: FieldStore, opts: ManifestOptions = {}): Promise<SyncEnvelope> {
  const [events, since_cursor, sender_manifest] = await Promise.all([
    store.getPendingEvents(),
    store.getCursor(),
    buildManifest(store.nodeId, opts),
  ]);
  return {
    envelope_id: uuid(),
    sender_manifest,
    sender_hlc: await store.tick(),
    since_cursor,
    next_cursor: null,
    events,
    ack_event_ids: [],
    schema_version: CONTRACT_SCHEMA_VERSION,
  };
}

export interface LocalEventInput {
  event_type: EventType;
  payload: Record<string, unknown>;
  patient_id?: string | null;
  enrichment_state?: EnrichmentState;
  ref_event_id?: string | null;
}

/** Single place for UI/forms to create local events: durable HLC, persisted to log + outbox. */
export async function createLocalEvent(store: FieldStore, input: LocalEventInput): Promise<CrdtEvent> {
  const event: CrdtEvent = {
    event_id: uuid(),
    hlc: await store.tick(),
    origin_node_id: store.nodeId,
    patient_id: input.patient_id ?? null,
    event_type: input.event_type,
    payload: input.payload,
    enrichment_state: input.enrichment_state ?? "NOT_NEEDED",
    ref_event_id: input.ref_event_id ?? null,
  };
  await store.appendEvent(event, { outbox: true });
  return event;
}
