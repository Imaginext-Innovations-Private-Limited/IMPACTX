/**
 * Fail-soft Tier-0 Watch delta-sync & SOS voice client for Aarogya Mesh.
 *
 * Speaks strict `SyncEnvelope` v1.0.0 (`POST /api/v1/sync`) and idempotent binary
 * voice-blob uploads (`HEAD` -> `PUT /api/v1/blobs/{blob_key}`) against a
 * Tier-2 PHC Hub or compatible Tier-1 relay, while keeping `WatchStore` 100%
 * autonomous offline.
 */

import {
  CONTRACT_SCHEMA_VERSION,
  type CrdtEvent,
  type HardwareCapabilityManifest,
  type SyncEnvelope,
} from "../../../../packages/contracts/ts/index";
import type { WatchStore } from "../core";
import {
  MemoryWatchBlobQueue,
  resolveDefaultBlobQueue,
  type QueuedWatchBlob,
  type WatchBlobQueue,
} from "./blob_queue";
import { isValidBlobKey, uploadWatchBlobIfMissing } from "./blobs";
import { validateSyncEnvelope } from "./validate";

export const DEFAULT_HUB_URL = "http://127.0.0.1:8000";

export interface BrowserLocationLike {
  protocol: string;
  origin: string;
  hostname?: string;
}

function isLoopbackHost(hostname: string): boolean {
  const host = hostname.trim().toLowerCase();
  return (
    host === "localhost" ||
    host === "127.0.0.1" ||
    host === "::1" ||
    host === "[::1]" ||
    host.startsWith("127.")
  );
}

function extractHostname(urlString: string): string {
  try {
    return new URL(urlString).hostname;
  } catch {
    return "";
  }
}

/**
 * Normalize a Hub URL: trim whitespace, strip trailing slashes, and prepend
 * `http://` when given a bare `host:port` or `IP:port`.
 */
export function normalizeHubUrl(
  rawUrl: string,
  fallback: string = DEFAULT_HUB_URL,
): string {
  const trimmed = rawUrl.trim().replace(/\/+$/, "");
  if (trimmed.length === 0) {
    return fallback.trim().replace(/\/+$/, "") || DEFAULT_HUB_URL;
  }
  if (!trimmed.includes("://")) {
    return `http://${trimmed}`;
  }
  return trimmed;
}

/**
 * Validate that a Hub URL (after normalization) is a well-formed `http:` or `https:` URL.
 */
export function isValidHubUrl(rawUrl: string): boolean {
  const trimmed = rawUrl.trim();
  if (trimmed.length === 0) {
    return false;
  }
  const normalized = normalizeHubUrl(trimmed, "");
  if (normalized.length === 0) {
    return false;
  }
  try {
    const parsed = new URL(normalized);
    return (
      (parsed.protocol === "http:" || parsed.protocol === "https:") &&
      parsed.hostname.length > 0
    );
  } catch {
    return false;
  }
}

function formatSyncNetworkError(
  err: unknown,
  timedOut: boolean,
  hubUrl: string,
): string {
  if (timedOut || (err instanceof Error && err.name === "AbortError")) {
    return `Hub timed out at ${hubUrl}. Check Wi-Fi/hotspot and tap Sync Now to retry.`;
  }
  const msg = err instanceof Error ? err.message : String(err);
  if (
    err instanceof TypeError ||
    /failed to fetch|networkerror|load failed|fetch failed|econnrefused|enotfound/i.test(msg)
  ) {
    return `Hub unreachable at ${hubUrl}. Check Hub address & Wi-Fi, then tap Sync Now to retry.`;
  }
  return msg || `Hub unreachable at ${hubUrl}. Tap Sync Now to retry.`;
}

/**
 * Resolve the Hub URL for the current browser/WebView origin while guarding
 * against stale `localhost`/`127.*` overrides when opened from a LAN IP.
 */
export function resolveDefaultHubUrl(
  loc?: BrowserLocationLike | null,
  savedHubUrl?: string | null,
): string {
  const hasHttpOrigin =
    loc != null &&
    (loc.protocol === "http:" || loc.protocol === "https:") &&
    typeof loc.origin === "string" &&
    loc.origin.trim().length > 0 &&
    loc.origin !== "null";

  const isAndroidApk =
    typeof globalThis !== "undefined" && "AarogyaNativeBridge" in globalThis;
  const autoOrigin =
    hasHttpOrigin && !isAndroidApk
      ? normalizeHubUrl(loc.origin, DEFAULT_HUB_URL)
      : DEFAULT_HUB_URL;
  const locHostname =
    hasHttpOrigin && !isAndroidApk
      ? (loc.hostname?.trim() || extractHostname(autoOrigin))
      : "";

  const trimmedSaved = savedHubUrl?.trim() ?? "";
  if (trimmedSaved.length > 0) {
    const normalizedSaved = normalizeHubUrl(trimmedSaved, "");
    if (normalizedSaved.length > 0) {
      const savedHost = extractHostname(normalizedSaved);
      if (
        savedHost &&
        isLoopbackHost(savedHost) &&
        locHostname.length > 0 &&
        !isLoopbackHost(locHostname)
      ) {
        return autoOrigin;
      }
      return normalizedSaved;
    }
  }

  return autoOrigin;
}

export {
  MemoryWatchBlobQueue,
  type QueuedWatchBlob,
  type WatchBlobQueue,
};

export interface WatchSyncClientOptions {
  hubUrl?: string;
  fetchImpl?: typeof fetch;
  batteryPct?: () => number;
  ramMb?: number;
  cpuCores?: number;
  timeoutMs?: number;
  blobQueue?: WatchBlobQueue;
}

export interface VoiceSosInput {
  patientId?: string | null;
  transcriptHint?: string;
  language?: string;
  audioBlob?: Blob | Uint8Array | null;
  audioBlobKey?: string;
  mimeType?: string | null;
  durationMs?: number;
}

export type WatchSyncResult =
  | {
      ok: true;
      status: "synced";
      ackedCount: number;
      appliedCount: number;
      uploadedBlobKeys: string[];
      nextCursor: string | null;
      envelope: SyncEnvelope;
    }
  | {
      ok: false;
      status: "offline" | "error";
      reason: string;
    };

function clampBattery(value: number): number {
  if (!Number.isFinite(value)) return 100;
  return Math.max(0, Math.min(100, Math.round(value)));
}

function getByteSize(blob: Blob | Uint8Array): number {
  return blob instanceof Uint8Array ? blob.byteLength : blob.size;
}

function inferMimeType(blob: Blob | Uint8Array, explicit?: string | null): string {
  if (explicit && explicit.trim().length > 0) {
    return explicit.split(";")[0].trim();
  }
  if (!(blob instanceof Uint8Array) && blob.type) {
    return blob.type.split(";")[0].trim() || "audio/webm";
  }
  return "audio/webm";
}

export class WatchSyncClient {
  private hubUrl: string;
  private readonly fetchImpl: typeof fetch;
  private readonly batteryPctProvider: () => number;
  private readonly ramMb: number;
  private readonly cpuCores: number;
  private readonly timeoutMs: number;
  private readonly blobQueue: WatchBlobQueue;
  private syncQueue: Promise<WatchSyncResult> = Promise.resolve({
    ok: true,
    status: "synced",
    ackedCount: 0,
    appliedCount: 0,
    uploadedBlobKeys: [],
    nextCursor: null,
    envelope: {
      envelope_id: "init",
      sender_manifest: {
        node_id: "init",
        tier: "TIER_0_WATCH",
        ram_mb: 256,
        cpu_cores: 2,
        battery_pct: 100,
        has_npu: false,
        installed_models: [],
        watch_mode: "CHW_COMPANION",
      },
      sender_hlc: { wall_ms: 0, logical: 0, node_id: "init" },
      since_cursor: null,
      next_cursor: null,
      events: [],
      ack_event_ids: [],
      schema_version: CONTRACT_SCHEMA_VERSION,
    },
  });

  constructor(
    private readonly store: WatchStore,
    hubUrlOrOptions: string | WatchSyncClientOptions = resolveDefaultHubUrl(
      typeof window !== "undefined" ? window.location : null,
    ),
    fetchImpl?: typeof fetch,
  ) {
    const opts: WatchSyncClientOptions =
      typeof hubUrlOrOptions === "string"
        ? { hubUrl: hubUrlOrOptions, fetchImpl }
        : hubUrlOrOptions;

    const fallbackHubUrl = resolveDefaultHubUrl(
      typeof window !== "undefined" ? window.location : null,
    );
    this.hubUrl = normalizeHubUrl(opts.hubUrl ?? fallbackHubUrl, fallbackHubUrl);
    const rawFetch = opts.fetchImpl ?? fetchImpl ?? globalThis.fetch;
    this.fetchImpl =
      rawFetch === globalThis.fetch && typeof globalThis.fetch === "function"
        ? globalThis.fetch.bind(globalThis)
        : rawFetch;
    this.batteryPctProvider = opts.batteryPct ?? (() => 100);
    this.ramMb = opts.ramMb ?? 256;
    this.cpuCores = opts.cpuCores ?? 2;
    this.timeoutMs = opts.timeoutMs ?? 15_000;
    this.blobQueue = opts.blobQueue ?? resolveDefaultBlobQueue(store.getNodeId());
  }

  public getHubUrl(): string {
    return this.hubUrl;
  }

  public setHubUrl(hubUrl: string): string {
    this.hubUrl = normalizeHubUrl(hubUrl, DEFAULT_HUB_URL);
    return this.hubUrl;
  }

  public getStore(): WatchStore {
    return this.store;
  }

  /**
   * Build a `TIER_0_WATCH` `HardwareCapabilityManifest` with non-null `watch_mode`.
   */
  public getManifest(): HardwareCapabilityManifest {
    return {
      node_id: this.store.getNodeId(),
      tier: "TIER_0_WATCH",
      ram_mb: this.ramMb,
      cpu_cores: this.cpuCores,
      battery_pct: clampBattery(this.batteryPctProvider()),
      has_npu: false,
      installed_models: [],
      watch_mode: this.store.getWatchMode(),
    };
  }

  /**
   * Build a contract-compliant outbound `SyncEnvelope` from `WatchStore`.
   */
  public buildSyncEnvelope(): SyncEnvelope {
    return {
      envelope_id: crypto.randomUUID(),
      sender_manifest: this.getManifest(),
      sender_hlc: this.store.tickHlc(),
      since_cursor: this.store.getSyncCursor(),
      next_cursor: null,
      events: this.store.getOutboxEvents(),
      ack_event_ids: [],
      schema_version: CONTRACT_SCHEMA_VERSION,
    };
  }

  /**
   * Register raw audio bytes for an outbox `VOICE_NOTE_RECORDED` event so the
   * next `syncNow()` uploads them idempotently before posting the envelope.
   */
  public async registerPendingBlob(
    blobKey: string,
    blob: Blob | Uint8Array,
    contentType?: string,
  ): Promise<void> {
    if (!isValidBlobKey(blobKey)) {
      throw new Error(
        "Invalid blob_key: must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ without '..'.",
      );
    }
    await this.blobQueue.set(blobKey, {
      blob,
      contentType: inferMimeType(blob, contentType),
    });
  }

  /**
   * Acknowledge an `ActionCard` offline by appending an `ACTION_CARD_ISSUED`
   * LWW status update (`{ card_id, status: "ACKNOWLEDGED" }`) to `WatchStore`.
   */
  public ackActionCard(cardId: string): CrdtEvent {
    const existing = this.store.getActionCard(cardId);
    const hlc = this.store.tickHlc();
    const event: CrdtEvent = {
      event_id: crypto.randomUUID(),
      hlc,
      origin_node_id: this.store.getNodeId(),
      patient_id: existing?.patient_id ?? null,
      event_type: "ACTION_CARD_ISSUED",
      payload: {
        card_id: cardId,
        status: "ACKNOWLEDGED",
      },
      enrichment_state: "NOT_NEEDED",
      ref_event_id: null,
    };
    this.store.appendEvent(event, { enqueueOutbox: true });
    return event;
  }

  /**
   * Queue an offline SOS voice/text event (`VOICE_NOTE_RECORDED`, `PENDING`)
   * and store any accompanying audio blob for idempotent upload during `syncNow()`.
   */
  public async enqueueVoiceSos(input: VoiceSosInput = {}): Promise<CrdtEvent> {
    const hasAudio = input.audioBlob != null && getByteSize(input.audioBlob) > 0;
    let blobKey: string | null = null;
    let mimeType: string | null = null;

    if (hasAudio && input.audioBlob) {
      blobKey =
        input.audioBlobKey ??
        `watch-sos-${crypto.randomUUID().replace(/[^A-Za-z0-9._-]/g, "")}`;
      if (!isValidBlobKey(blobKey)) {
        throw new Error(
          "Invalid audioBlobKey: must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$ without '..'.",
        );
      }
      mimeType = inferMimeType(input.audioBlob, input.mimeType);
      await this.blobQueue.set(blobKey, {
        blob: input.audioBlob,
        contentType: mimeType,
      });
    }

    const transcriptHint = input.transcriptHint?.trim() || "Emergency SOS voice alert";
    const language = input.language?.trim() || "hi";
    const hlc = this.store.tickHlc();

    const event: CrdtEvent = {
      event_id: crypto.randomUUID(),
      hlc,
      origin_node_id: this.store.getNodeId(),
      patient_id: input.patientId ?? null,
      event_type: "VOICE_NOTE_RECORDED",
      payload: {
        transcript_hint: transcriptHint,
        language,
        audio_blob_key: blobKey,
        mime_type: mimeType,
        duration_ms: Math.max(0, Math.round(input.durationMs ?? 0)),
        sos: true,
      },
      enrichment_state: "PENDING",
      ref_event_id: null,
    };
    this.store.appendEvent(event, { enqueueOutbox: true });
    return event;
  }

  /**
   * Execute one fail-soft delta sync roundtrip:
   * 1. Upload any pending SOS voice blobs via `HEAD` -> `PUT /api/v1/blobs/{key}`.
   * 2. `POST /api/v1/sync` with strict `SyncEnvelope` v1.0.0.
   * 3. Validate reply, merge HLCs, ack synced outbox items, apply incoming events,
   *    and persist `next_cursor`.
   *
   * Never throws on offline/timeout/5xx/malformed replies.
   */
  public syncNow(): Promise<WatchSyncResult> {
    const run = this.syncQueue.then(() => this.performSync());
    this.syncQueue = run.catch((): WatchSyncResult => ({
      ok: false,
      status: "error",
      reason: "Unexpected sync failure.",
    }));
    return run;
  }

  private async performSync(): Promise<WatchSyncResult> {
    if (!isValidHubUrl(this.hubUrl)) {
      return {
        ok: false,
        status: "error",
        reason: `Invalid Hub address "${this.hubUrl}". Use http://IP:port (e.g. http://192.168.1.10:8000).`,
      };
    }

    if (typeof this.fetchImpl !== "function") {
      return {
        ok: false,
        status: "offline",
        reason: "Network fetch unavailable in this browser. Saved locally; tap Sync Now when online.",
      };
    }

    const uploadedBlobKeys: string[] = [];
    const checkedBlobKeys = new Set<string>();
    const blobEventByKey = new Map<string, string[]>();

    for (const event of this.store.getOutboxEvents()) {
      if (event.event_type !== "VOICE_NOTE_RECORDED") {
        continue;
      }
      const rawKey = event.payload.audio_blob_key;
      if (typeof rawKey !== "string" || rawKey.length === 0) {
        continue;
      }

      const eventIdsForKey = blobEventByKey.get(rawKey) ?? [];
      eventIdsForKey.push(event.event_id);
      blobEventByKey.set(rawKey, eventIdsForKey);

      if (checkedBlobKeys.has(rawKey)) {
        continue;
      }
      checkedBlobKeys.add(rawKey);

      const queued = await this.blobQueue.get(rawKey);
      if (!queued) {
        continue;
      }

      const uploadRes = await uploadWatchBlobIfMissing(
        this.hubUrl,
        rawKey,
        queued.blob,
        this.fetchImpl,
        {
          contentType: queued.contentType,
          timeoutMs: this.timeoutMs,
        },
      );
      if (!uploadRes.ok) {
        return {
          ok: false,
          status: uploadRes.status,
          reason:
            uploadRes.status === "offline"
              ? formatSyncNetworkError(
                  new TypeError(uploadRes.reason),
                  false,
                  this.hubUrl,
                )
              : uploadRes.reason,
        };
      }
      if (uploadRes.status === "uploaded") {
        uploadedBlobKeys.push(rawKey);
      }
    }

    const envelope = this.buildSyncEnvelope();
    const sentEventIds = new Set(envelope.events.map((evt) => evt.event_id));
    const url = `${this.hubUrl}/api/v1/sync`;

    let timedOut = false;
    const ctrl = typeof AbortController === "function" ? new AbortController() : undefined;
    const timer = ctrl
      ? setTimeout(() => {
          timedOut = true;
          ctrl.abort();
        }, this.timeoutMs)
      : undefined;

    let res: Response;
    try {
      const fetchFn = this.fetchImpl;
      res = await fetchFn(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(envelope),
        cache: "no-store",
        signal: ctrl?.signal,
      });
    } catch (err) {
      if (timer !== undefined) clearTimeout(timer);
      return {
        ok: false,
        status: "offline",
        reason: formatSyncNetworkError(err, timedOut, this.hubUrl),
      };
    }

    let rawBody: unknown;
    try {
      if (!res.ok) {
        return {
          ok: false,
          status: "error",
          reason: `Hub returned HTTP ${res.status} on /api/v1/sync. Tap Sync Now to retry.`,
        };
      }
      rawBody = await res.json();
    } catch (err) {
      const aborted = timedOut || ctrl?.signal.aborted === true;
      return {
        ok: false,
        status: aborted ? "offline" : "error",
        reason: aborted
          ? formatSyncNetworkError(err, true, this.hubUrl)
          : err instanceof Error
            ? `Invalid Hub sync response: ${err.message}`
            : "Failed to parse Hub sync JSON reply.",
      };
    } finally {
      if (timer !== undefined) clearTimeout(timer);
    }

    const validation = validateSyncEnvelope(rawBody);
    if (!validation.ok) {
      return {
        ok: false,
        status: "error",
        reason: validation.reason,
      };
    }

    const safeReply: SyncEnvelope = {
      ...validation.envelope,
      ack_event_ids: validation.envelope.ack_event_ids.filter((id) => sentEventIds.has(id)),
    };

    const { ackedCount, appliedCount } = this.store.applySyncResponse(safeReply);

    // Delete queued blobs only after all outbox events referencing them are synced.
    const remainingOutboxKeys = new Set<string>();
    for (const evt of this.store.getOutboxEvents()) {
      if (evt.event_type === "VOICE_NOTE_RECORDED" && typeof evt.payload.audio_blob_key === "string") {
        remainingOutboxKeys.add(evt.payload.audio_blob_key);
      }
    }
    for (const key of blobEventByKey.keys()) {
      if (!remainingOutboxKeys.has(key)) {
        await this.blobQueue.delete(key);
      }
    }

    return {
      ok: true,
      status: "synced",
      ackedCount,
      appliedCount,
      uploadedBlobKeys,
      nextCursor: this.store.getSyncCursor(),
      envelope: safeReply,
    };
  }
}
