/**
 * Persistent Tier-0 Watch event store and CRDT ActionCard projection.
 *
 * Zero DOM dependencies: defaults to `globalThis.localStorage` in browsers and
 * falls back to an in-memory `StorageLike` adapter in Node / Vitest.
 */

import type {
  ActionCard,
  ActionCardPriority,
  ActionCardStatus,
  CrdtEvent,
  HlcTimestamp,
  NodeTier,
  SyncEnvelope,
  TriageSeverity,
  WatchMode,
} from "../../../../packages/contracts/ts/index";
import { compareHlc, createHlc, receiveHlc, tickHlc } from "./hlc";

export const DEFAULT_WATCH_STORAGE_KEY = "aarogya.watch.store.v1";

export interface StorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem?(key: string): void;
}

/**
 * In-memory `StorageLike` fallback for Node/Vitest or environments without `localStorage`.
 */
export class MemoryStorage implements StorageLike {
  private readonly data = new Map<string, string>();

  public getItem(key: string): string | null {
    return this.data.get(key) ?? null;
  }

  public setItem(key: string, value: string): void {
    this.data.set(key, value);
  }

  public removeItem(key: string): void {
    this.data.delete(key);
  }

  public clear(): void {
    this.data.clear();
  }
}

export function resolveDefaultStorage(): StorageLike {
  try {
    if (
      typeof globalThis !== "undefined" &&
      "localStorage" in globalThis &&
      globalThis.localStorage != null
    ) {
      return globalThis.localStorage;
    }
  } catch {
    // Restricted environments may throw SecurityError when probing localStorage.
  }
  return new MemoryStorage();
}

export interface WatchStoreOptions {
  nodeId?: string;
  initialMode?: WatchMode;
  storage?: StorageLike;
  storageKey?: string;
  nowMs?: () => number;
}

interface PersistedWatchState {
  version: 1;
  nodeId: string;
  watchMode: WatchMode;
  hlc: HlcTimestamp;
  syncCursor: string | null;
  events: CrdtEvent[];
  outboxEventIds: string[];
}

type OrderKey = [number, number, string, string];
type FieldRegisters = Map<string, { key: OrderKey; value: unknown }>;

const PRIORITY_RANK: Record<ActionCardPriority, number> = {
  CRITICAL: 0,
  HIGH: 1,
  MEDIUM: 2,
  LOW: 3,
};

const STATUS_RANK: Record<ActionCardStatus, number> = {
  OPEN: 0,
  ACKNOWLEDGED: 1,
  COMPLETED: 2,
  DISMISSED: 3,
};

const isNonEmptyStr = (v: unknown): v is string => typeof v === "string" && v.length > 0;
const isStrOrNull = (v: unknown): v is string | null => v === null || isNonEmptyStr(v);
const isStrList = (v: unknown): v is string[] =>
  Array.isArray(v) && v.every((item) => typeof item === "string");
const isOneOf =
  <T extends string>(...allowed: readonly T[]) =>
  (v: unknown): v is T =>
    typeof v === "string" && (allowed as readonly string[]).includes(v);

const isPriority = isOneOf<ActionCardPriority>("LOW", "MEDIUM", "HIGH", "CRITICAL");
const isSeverity = isOneOf<TriageSeverity>("GREEN_HOME", "YELLOW_PHC", "RED_EMERGENCY");
const isCardStatus = isOneOf<ActionCardStatus>("OPEN", "ACKNOWLEDGED", "COMPLETED", "DISMISSED");
const isNodeTier = isOneOf<NodeTier>("TIER_0_WATCH", "TIER_1_PHONE", "TIER_2_HUB");
const isWatchMode = isOneOf<WatchMode>("CHW_COMPANION", "PATIENT_FAMILY");

const ACTION_CARD_VALIDATORS: Record<string, (v: unknown) => boolean> = {
  patient_id: isStrOrNull,
  title: isNonEmptyStr,
  summary: isNonEmptyStr,
  action_steps: isStrList,
  priority: isPriority,
  severity: (v) => v === null || isSeverity(v),
  status: isCardStatus,
  target_tier: isNodeTier,
  watch_mode: (v) => v === null || isWatchMode(v),
  source_event_id: isStrOrNull,
  due_by: isStrOrNull,
  language: isNonEmptyStr,
};

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function makeOrderKey(event: CrdtEvent): OrderKey {
  return [event.hlc.wall_ms, event.hlc.logical, event.hlc.node_id, event.event_id];
}

function compareOrderKeys(a: OrderKey, b: OrderKey): number {
  for (let i = 0; i < 4; i++) {
    if (a[i] !== b[i]) {
      return a[i] < b[i] ? -1 : 1;
    }
  }
  return 0;
}

function lwwSet(
  registers: FieldRegisters,
  field: string,
  key: OrderKey,
  value: unknown,
): void {
  const existing = registers.get(field);
  if (!existing || compareOrderKeys(key, existing.key) >= 0) {
    registers.set(field, { key, value });
  }
}

/**
 * Pure per-field LWW projection of `ActionCard` state from `CrdtEvent[]`.
 * Matches `packages/crdt-sync/src/aarogya_crdt_sync/projector.py`.
 */
export function projectActionCards(events: readonly CrdtEvent[]): Map<string, ActionCard> {
  const seen = new Set<string>();
  const ordered: CrdtEvent[] = [];
  for (const event of events) {
    if (!seen.has(event.event_id)) {
      seen.add(event.event_id);
      ordered.push(event);
    }
  }
  ordered.sort((a, b) => compareOrderKeys(makeOrderKey(a), makeOrderKey(b)));

  const cardRegisters = new Map<string, FieldRegisters>();

  for (const event of ordered) {
    const payload = isRecord(event.payload) ? event.payload : {};
    const isActionCardEvent = event.event_type === "ACTION_CARD_ISSUED";
    const isCardStatusUpdate =
      event.event_type === "CHECKLIST_RECORDED" &&
      isNonEmptyStr(payload.card_id) &&
      "status" in payload;

    if (!isActionCardEvent && !isCardStatusUpdate) {
      continue;
    }

    const cardId = isNonEmptyStr(payload.card_id) ? payload.card_id : event.event_id;
    let registers = cardRegisters.get(cardId);
    if (!registers) {
      registers = new Map();
      cardRegisters.set(cardId, registers);
    }

    const orderKey = makeOrderKey(event);
    if (event.patient_id !== null && !("patient_id" in payload)) {
      lwwSet(registers, "patient_id", orderKey, event.patient_id);
    }

    for (const [field, isValid] of Object.entries(ACTION_CARD_VALIDATORS)) {
      if (field in payload && isValid(payload[field])) {
        lwwSet(registers, field, orderKey, payload[field]);
      }
    }

    if (!registers.has("source_event_id")) {
      registers.set("source_event_id", {
        key: orderKey,
        value: event.ref_event_id ?? event.event_id,
      });
    }
  }

  const cards = new Map<string, ActionCard>();
  for (const [cardId, registers] of cardRegisters) {
    const data: Record<string, unknown> = {};
    for (const [field, entry] of registers) {
      data[field] = entry.value;
    }
    cards.set(cardId, {
      card_id: cardId,
      patient_id: (data.patient_id as string | null) ?? null,
      title: isNonEmptyStr(data.title) ? data.title : "Action Card",
      summary: isNonEmptyStr(data.summary) ? data.summary : "Pending full card details",
      action_steps: (data.action_steps as string[]) ?? [],
      priority: (data.priority as ActionCardPriority) ?? "MEDIUM",
      severity: (data.severity as TriageSeverity | null) ?? null,
      status: (data.status as ActionCardStatus) ?? "OPEN",
      target_tier: (data.target_tier as NodeTier) ?? "TIER_0_WATCH",
      watch_mode: (data.watch_mode as WatchMode | null) ?? null,
      source_event_id: (data.source_event_id as string | null) ?? null,
      due_by: (data.due_by as string | null) ?? null,
      language: isNonEmptyStr(data.language) ? data.language : "en",
    });
  }

  return cards;
}

/**
 * Sort ActionCards with `OPEN` first, then `CRITICAL -> HIGH -> MEDIUM -> LOW`.
 */
export function sortActionCards(cards: readonly ActionCard[]): ActionCard[] {
  return [...cards].sort((a, b) => {
    const aOpen = a.status === "OPEN" ? 0 : 1;
    const bOpen = b.status === "OPEN" ? 0 : 1;
    if (aOpen !== bOpen) {
      return aOpen - bOpen;
    }

    const priorityDelta = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
    if (priorityDelta !== 0) {
      return priorityDelta;
    }

    const statusDelta = STATUS_RANK[a.status] - STATUS_RANK[b.status];
    if (statusDelta !== 0) {
      return statusDelta;
    }

    return a.card_id < b.card_id ? -1 : a.card_id > b.card_id ? 1 : 0;
  });
}

function isValidHlc(v: unknown): v is HlcTimestamp {
  return (
    isRecord(v) &&
    typeof v.wall_ms === "number" &&
    Number.isFinite(v.wall_ms) &&
    v.wall_ms >= 0 &&
    typeof v.logical === "number" &&
    Number.isInteger(v.logical) &&
    v.logical >= 0 &&
    isNonEmptyStr(v.node_id)
  );
}

function isValidEvent(v: unknown): v is CrdtEvent {
  return (
    isRecord(v) &&
    isNonEmptyStr(v.event_id) &&
    isValidHlc(v.hlc) &&
    isNonEmptyStr(v.origin_node_id) &&
    (v.patient_id === null || isNonEmptyStr(v.patient_id)) &&
    isNonEmptyStr(v.event_type) &&
    isRecord(v.payload) &&
    isNonEmptyStr(v.enrichment_state) &&
    (v.ref_event_id === null || isNonEmptyStr(v.ref_event_id))
  );
}

/**
 * Persistent standalone store for the Tier-0 Watch node.
 */
export class WatchStore {
  private readonly storage: StorageLike;
  private readonly storageKey: string;
  private readonly nowMs: () => number;

  private nodeId: string;
  private watchMode: WatchMode;
  private hlc: HlcTimestamp;
  private syncCursor: string | null;
  private events: CrdtEvent[];
  private eventIds: Set<string>;
  private outboxIds: Set<string>;
  private actionCards: Map<string, ActionCard>;

  constructor(options: WatchStoreOptions = {}) {
    this.storage = options.storage ?? resolveDefaultStorage();
    this.storageKey = options.storageKey ?? DEFAULT_WATCH_STORAGE_KEY;
    this.nowMs = options.nowMs ?? (() => Date.now());

    const persisted = this.loadPersistedState();
    if (persisted) {
      this.nodeId = persisted.nodeId;
      this.watchMode = persisted.watchMode;
      this.hlc = { ...persisted.hlc };
      this.syncCursor = persisted.syncCursor;
      this.events = [];
      this.eventIds = new Set();
      for (const evt of persisted.events) {
        if (!this.eventIds.has(evt.event_id)) {
          this.eventIds.add(evt.event_id);
          this.events.push(evt);
        }
      }
      this.outboxIds = new Set(
        persisted.outboxEventIds.filter((id) => this.eventIds.has(id)),
      );
      this.actionCards = projectActionCards(this.events);
    } else {
      this.nodeId = options.nodeId ?? `watch-${crypto.randomUUID().slice(0, 8)}`;
      this.watchMode = options.initialMode ?? "CHW_COMPANION";
      this.hlc = createHlc(this.nodeId, this.nowMs(), 0);
      this.syncCursor = null;
      this.events = [];
      this.eventIds = new Set();
      this.outboxIds = new Set();
      this.actionCards = new Map();
      this.persist();
    }
  }

  public getNodeId(): string {
    return this.nodeId;
  }

  public getWatchMode(): WatchMode {
    return this.watchMode;
  }

  public setWatchMode(mode: WatchMode): WatchMode {
    if (this.watchMode !== mode) {
      this.watchMode = mode;
      this.persist();
    }
    return this.watchMode;
  }

  public toggleWatchMode(): WatchMode {
    return this.setWatchMode(
      this.watchMode === "CHW_COMPANION" ? "PATIENT_FAMILY" : "CHW_COMPANION",
    );
  }

  public getHlc(): HlcTimestamp {
    return { ...this.hlc };
  }

  public tickHlc(): HlcTimestamp {
    this.hlc = tickHlc(this.hlc, this.nowMs());
    this.persist();
    return { ...this.hlc };
  }

  public receiveHlc(remote: HlcTimestamp): HlcTimestamp {
    this.hlc = receiveHlc(this.hlc, remote, this.nowMs());
    this.persist();
    return { ...this.hlc };
  }

  public getSyncCursor(): string | null {
    return this.syncCursor;
  }

  public setSyncCursor(cursor: string | null): void {
    if (this.syncCursor !== cursor) {
      this.syncCursor = cursor;
      this.persist();
    }
  }

  public hasEvent(eventId: string): boolean {
    return this.eventIds.has(eventId);
  }

  public getEvents(): CrdtEvent[] {
    return [...this.events];
  }

  public getOutboxEventIds(): string[] {
    return this.events
      .filter((evt) => this.outboxIds.has(evt.event_id))
      .map((evt) => evt.event_id);
  }

  public getOutboxEvents(): CrdtEvent[] {
    return this.events.filter((evt) => this.outboxIds.has(evt.event_id));
  }

  /**
   * Append a single event to the append-only log (deduplicated by `event_id`).
   * By default (`enqueueOutbox: true`), records the event ID in the pending outbox.
   */
  public appendEvent(
    event: CrdtEvent,
    options: { enqueueOutbox?: boolean } = {},
  ): boolean {
    if (this.eventIds.has(event.event_id)) {
      return false;
    }
    this.eventIds.add(event.event_id);
    this.events.push(event);
    if (options.enqueueOutbox ?? true) {
      this.outboxIds.add(event.event_id);
    }
    if (compareHlc(event.hlc, this.hlc) > 0) {
      this.hlc = receiveHlc(this.hlc, event.hlc, this.nowMs());
    }
    this.actionCards = projectActionCards(this.events);
    this.persist();
    return true;
  }

  /**
   * Apply peer-received events idempotently without adding them to the outbox.
   */
  public applyRemoteEvents(events: readonly CrdtEvent[]): number {
    let applied = 0;
    for (const event of events) {
      if (this.eventIds.has(event.event_id)) {
        continue;
      }
      this.eventIds.add(event.event_id);
      this.events.push(event);
      this.hlc = receiveHlc(this.hlc, event.hlc, this.nowMs());
      applied += 1;
    }
    if (applied > 0) {
      this.actionCards = projectActionCards(this.events);
      this.persist();
    }
    return applied;
  }

  /**
   * Remove acknowledged event IDs from the pending outbox.
   */
  public ackOutbox(eventIds: Iterable<string>): number {
    let acked = 0;
    for (const id of eventIds) {
      if (this.outboxIds.delete(id)) {
        acked += 1;
      }
    }
    if (acked > 0) {
      this.persist();
    }
    return acked;
  }

  /**
   * Apply a peer `SyncEnvelope` response atomically (outbox acks, HLC merge,
   * remote event deduplication, and `next_cursor` advancement).
   */
  public applySyncResponse(delta: SyncEnvelope): {
    ackedCount: number;
    appliedCount: number;
  } {
    let ackedCount = 0;
    for (const id of delta.ack_event_ids) {
      if (this.outboxIds.delete(id)) {
        ackedCount += 1;
      }
    }

    const prevHlc = this.hlc;
    this.hlc = receiveHlc(this.hlc, delta.sender_hlc, this.nowMs());

    let appliedCount = 0;
    for (const event of delta.events) {
      if (this.eventIds.has(event.event_id)) {
        continue;
      }
      this.eventIds.add(event.event_id);
      this.events.push(event);
      this.hlc = receiveHlc(this.hlc, event.hlc, this.nowMs());
      appliedCount += 1;
    }

    if (appliedCount > 0) {
      this.actionCards = projectActionCards(this.events);
    }

    const cursorChanged =
      delta.next_cursor !== null &&
      delta.next_cursor !== undefined &&
      delta.next_cursor !== this.syncCursor;
    if (cursorChanged) {
      this.syncCursor = delta.next_cursor;
    }

    if (
      ackedCount > 0 ||
      appliedCount > 0 ||
      cursorChanged ||
      compareHlc(this.hlc, prevHlc) !== 0
    ) {
      this.persist();
    }

    return { ackedCount, appliedCount };
  }

  public getActionCard(cardId: string): ActionCard | undefined {
    return this.actionCards.get(cardId);
  }

  public getAllActionCards(): ActionCard[] {
    return sortActionCards([...this.actionCards.values()]);
  }

  public getVisibleActionCards(mode: WatchMode = this.watchMode): ActionCard[] {
    return sortActionCards(
      [...this.actionCards.values()].filter(
        (card) => card.watch_mode === null || card.watch_mode === mode,
      ),
    );
  }

  private loadPersistedState(): PersistedWatchState | null {
    const raw = this.storage.getItem(this.storageKey);
    if (!raw) {
      return null;
    }
    try {
      const parsed: unknown = JSON.parse(raw);
      if (!isRecord(parsed) || parsed.version !== 1) {
        return null;
      }
      if (!isNonEmptyStr(parsed.nodeId) || !isWatchMode(parsed.watchMode)) {
        return null;
      }
      if (!isValidHlc(parsed.hlc)) {
        return null;
      }
      const syncCursor =
        parsed.syncCursor === null || typeof parsed.syncCursor === "string"
          ? parsed.syncCursor
          : null;
      const events = Array.isArray(parsed.events)
        ? parsed.events.filter(isValidEvent)
        : [];
      const outboxEventIds = Array.isArray(parsed.outboxEventIds)
        ? parsed.outboxEventIds.filter(isNonEmptyStr)
        : [];

      return {
        version: 1,
        nodeId: parsed.nodeId,
        watchMode: parsed.watchMode,
        hlc: { ...parsed.hlc },
        syncCursor,
        events,
        outboxEventIds,
      };
    } catch {
      return null;
    }
  }

  private persist(): void {
    const snapshot: PersistedWatchState = {
      version: 1,
      nodeId: this.nodeId,
      watchMode: this.watchMode,
      hlc: this.hlc,
      syncCursor: this.syncCursor,
      events: this.events,
      outboxEventIds: this.getOutboxEventIds(),
    };
    this.storage.setItem(this.storageKey, JSON.stringify(snapshot));
  }
}
