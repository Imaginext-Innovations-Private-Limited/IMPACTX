/**
 * Runtime structural validators for `SyncEnvelope` and nested contracts.
 *
 * Ensures malformed Hub or relay payloads are rejected fail-soft before
 * mutating `WatchStore`.
 */

import {
  CONTRACT_SCHEMA_VERSION,
  type CrdtEvent,
  type EnrichmentState,
  type EventType,
  type HardwareCapabilityManifest,
  type HlcTimestamp,
  type NodeTier,
  type SyncEnvelope,
  type WatchMode,
} from "../../../../packages/contracts/ts/index";

const NODE_TIERS = new Set<NodeTier>(["TIER_0_WATCH", "TIER_1_PHONE", "TIER_2_HUB"]);
const WATCH_MODES = new Set<WatchMode>(["CHW_COMPANION", "PATIENT_FAMILY"]);
const EVENT_TYPES = new Set<EventType>([
  "PATIENT_REGISTERED",
  "TRIAGE_COMPLETED",
  "CHECKLIST_RECORDED",
  "VACCINATION_LOGGED",
  "VOICE_NOTE_RECORDED",
  "ENRICHMENT_COMPLETED",
  "ACTION_CARD_ISSUED",
  "OUTBREAK_ALERT_RAISED",
]);
const ENRICHMENT_STATES = new Set<EnrichmentState>([
  "NOT_NEEDED",
  "PENDING",
  "COMPLETED",
  "FAILED",
]);

function isNonEmptyString(value: unknown, maxLen = 256): value is string {
  return typeof value === "string" && value.length >= 1 && value.length <= maxLen;
}

function isNullableString(value: unknown, maxLen = 256): value is string | null {
  return value === null || isNonEmptyString(value, maxLen);
}

function isPlainRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isValidHlcTimestamp(value: unknown): value is HlcTimestamp {
  if (!isPlainRecord(value)) return false;
  return (
    typeof value.wall_ms === "number" &&
    Number.isInteger(value.wall_ms) &&
    value.wall_ms >= 0 &&
    typeof value.logical === "number" &&
    Number.isInteger(value.logical) &&
    value.logical >= 0 &&
    isNonEmptyString(value.node_id, 128)
  );
}

export function isValidManifest(value: unknown): value is HardwareCapabilityManifest {
  if (!isPlainRecord(value)) return false;
  if (!isNonEmptyString(value.node_id, 128)) return false;
  if (!NODE_TIERS.has(value.tier as NodeTier)) return false;
  if (typeof value.ram_mb !== "number" || !Number.isInteger(value.ram_mb) || value.ram_mb < 1) {
    return false;
  }
  if (
    typeof value.cpu_cores !== "number" ||
    !Number.isInteger(value.cpu_cores) ||
    value.cpu_cores < 1
  ) {
    return false;
  }
  if (
    typeof value.battery_pct !== "number" ||
    !Number.isFinite(value.battery_pct) ||
    value.battery_pct < 0 ||
    value.battery_pct > 100
  ) {
    return false;
  }
  if (typeof value.has_npu !== "boolean") return false;
  if (
    !Array.isArray(value.installed_models) ||
    !value.installed_models.every((m) => typeof m === "string")
  ) {
    return false;
  }
  if (value.tier === "TIER_0_WATCH") {
    if (!WATCH_MODES.has(value.watch_mode as WatchMode)) return false;
  } else if (value.watch_mode !== null && value.watch_mode !== undefined) {
    return false;
  }
  return true;
}

export function isValidCrdtEvent(value: unknown): value is CrdtEvent {
  if (!isPlainRecord(value)) return false;
  if (!isNonEmptyString(value.event_id, 128)) return false;
  if (!isValidHlcTimestamp(value.hlc)) return false;
  if (!isNonEmptyString(value.origin_node_id, 128)) return false;
  if (!isNullableString(value.patient_id, 128)) return false;
  if (!EVENT_TYPES.has(value.event_type as EventType)) return false;
  if (!isPlainRecord(value.payload)) return false;
  if (!ENRICHMENT_STATES.has(value.enrichment_state as EnrichmentState)) return false;
  if (!isNullableString(value.ref_event_id, 128)) return false;
  if (value.event_type === "ENRICHMENT_COMPLETED" && value.ref_event_id === null) {
    return false;
  }
  return true;
}

export function validateSyncEnvelope(
  value: unknown,
): { ok: true; envelope: SyncEnvelope } | { ok: false; reason: string } {
  if (!isPlainRecord(value)) {
    return { ok: false, reason: "SyncEnvelope reply must be a JSON object." };
  }
  if (!isNonEmptyString(value.envelope_id, 128)) {
    return { ok: false, reason: "SyncEnvelope missing valid envelope_id." };
  }
  if (!isValidManifest(value.sender_manifest)) {
    return { ok: false, reason: "SyncEnvelope missing valid sender_manifest." };
  }
  if (!isValidHlcTimestamp(value.sender_hlc)) {
    return { ok: false, reason: "SyncEnvelope missing valid sender_hlc." };
  }
  if (value.since_cursor !== undefined && !isNullableString(value.since_cursor, 256)) {
    return { ok: false, reason: "SyncEnvelope has invalid since_cursor." };
  }
  if (value.next_cursor !== undefined && !isNullableString(value.next_cursor, 256)) {
    return { ok: false, reason: "SyncEnvelope has invalid next_cursor." };
  }
  if (!Array.isArray(value.events) || !value.events.every(isValidCrdtEvent)) {
    return { ok: false, reason: "SyncEnvelope contains invalid events." };
  }
  if (
    !Array.isArray(value.ack_event_ids) ||
    !value.ack_event_ids.every((id) => isNonEmptyString(id, 128))
  ) {
    return { ok: false, reason: "SyncEnvelope contains invalid ack_event_ids." };
  }
  if (!isNonEmptyString(value.schema_version, 32)) {
    return { ok: false, reason: "SyncEnvelope missing valid schema_version." };
  }
  const major = value.schema_version.split(".")[0];
  const expectedMajor = CONTRACT_SCHEMA_VERSION.split(".")[0];
  if (major !== expectedMajor) {
    return {
      ok: false,
      reason: `Unsupported SyncEnvelope schema_version '${value.schema_version}'.`,
    };
  }
  return { ok: true, envelope: value as unknown as SyncEnvelope };
}
