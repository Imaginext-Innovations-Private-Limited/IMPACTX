/**
 * SyncEngine: durable outbox <-> Tier-2 hub. Fail-soft: network/hub failures only
 * change status; the outbox stays intact and local actions never wait on the hub.
 *
 * Voice clips: before every push, clips referenced by outbox VOICE_NOTE_RECORDED
 * events are uploaded (HEAD, then PUT if missing) so the hub worker can read them.
 * A note whose clip fails transiently is WITHHELD from the envelope (the hub would
 * otherwise finish it from the typed hint and never revisit the audio). It stays
 * in the outbox and is retried next sync, HEAD first (retry state = outbox + HEAD;
 * nothing new is persisted). Outbox events that reference a withheld event via
 * ref_event_id are withheld with it, so the hub never sees a dependent before its
 * note; they go out together, in HLC order, once the clip lands. Every other event
 * is still sent, and the envelope is POSTed even if empty (pulls remote events and
 * advances the cursor). Acks are honoured only for ids actually sent.
 */
import type { CrdtEvent, SyncEnvelope } from "../../../../packages/contracts/ts/index";
import type { FieldStore } from "../core";
import { applyResponse, countPendingEnrichments, materialize, rebuildViews, type ApplyResult } from "./apply";
import { Emitter, type SyncState } from "./emitter";
import { buildEnvelope, createLocalEvent, type LocalEventInput, type ManifestOptions } from "./envelope";
import { getAudio } from "../ui/audio_store";
import { isValidBlobKey, uploadBlobIfMissing } from "./transport-blobs";
import { postSync, SyncTransportError } from "./transport-http";
import { MeshSocket, type WsFactory } from "./transport-ws";

export interface SyncEngineOptions {
  hubUrl?: string;
  fetchImpl?: typeof fetch;
  wsFactory?: WsFactory;
  manifest?: ManifestOptions;
  wsBaseDelayMs?: number;
  wsMaxDelayMs?: number;
  /** Loads a recorded clip by key; defaults to the UI's IndexedDB audio store. */
  getAudioBlob?: (key: string) => Promise<Blob | undefined>;
  /** Deadline for one clip's whole HEAD+PUT exchange. */
  blobTimeoutMs?: number;
}

export type SyncPhase = "idle" | "uploading_blobs" | "syncing_events";

interface BlobPass {
  /** Voice notes whose clip is still not on the hub: not sent this round. */
  held: Set<string>;
  /** Blob keys that failed transiently and are waiting for retry. */
  heldBlobKeys: Set<string>;
  failure?: SyncTransportError;
}

export class SyncEngine {
  readonly events = new Emitter();
  hubUrl: string;
  private state: SyncState = "idle";
  /** Network queue: one exchange at a time (may be held across a slow fetch). */
  private queue: Promise<unknown> = Promise.resolve();
  /**
   * View lock: every read-log-then-write-views step (enqueue, rebuild, apply) runs
   * here, so a stale fold can never overwrite a fresher view. It is never held
   * across network I/O, so local actions never wait on the hub.
   */
  private viewQueue: Promise<unknown> = Promise.resolve();
  private mesh: MeshSocket | null = null;
  private viewsReady: Promise<void> | null = null;
  /** Event ids sent over WS and not yet acked; WS replies may only ack these. */
  private wsSent = new Set<string>();
  private held = 0;
  private phase: SyncPhase = "idle";
  private uploadingBlobs = new Set<string>();
  private heldBlobs = new Set<string>();
  private errorMsg: string | null = null;

  constructor(readonly store: FieldStore, private readonly opts: SyncEngineOptions = {}) {
    this.hubUrl = opts.hubUrl ?? "http://127.0.0.1:8000";
  }

  get status(): SyncState {
    return this.state;
  }

  get lastError(): string | null {
    return this.errorMsg;
  }

  /** Current network phase within a sync exchange. */
  get syncPhase(): SyncPhase {
    return this.phase;
  }

  /** Audio blob keys currently being uploaded to the hub. */
  get uploadingBlobKeys(): ReadonlySet<string> {
    return this.uploadingBlobs;
  }

  /** Audio blob keys withheld after a transient failure and waiting for retry. */
  get heldBlobKeys(): ReadonlySet<string> {
    return this.heldBlobs;
  }

  /** Voice notes withheld by the last push because their clip has not reached the hub yet. */
  get heldClips(): number {
    return this.held;
  }

  async pendingCount(): Promise<number> {
    return (await this.store.getPendingEvents()).length;
  }

  pendingEnrichmentCount(): Promise<number> {
    return countPendingEnrichments(this.store);
  }

  /** Create + persist a local event (log + outbox), materialize it, and push opportunistically. */
  async enqueue(input: LocalEventInput): Promise<CrdtEvent> {
    const { event, pendingEnrichments, cards } = await this.withViews(async () => {
      const event = await createLocalEvent(this.store, input);
      return { event, ...(await materialize(this.store, [event])) };
    });
    if (cards.length) this.events.emit("cards", { cards });
    this.events.emit("enrichment", { pending: pendingEnrichments });
    await this.setState(this.state);
    if (this.mesh?.connected) void this.pushViaMesh();
    return event;
  }

  /** One HTTP exchange. Never throws; resolves null on failure (status says why). */
  syncNow(): Promise<ApplyResult | null> {
    return this.serial(async () => {
      this.phase = "idle";
      this.uploadingBlobs.clear();
      await this.setState("syncing");
      try {
        await this.ensureViews();
        const { env, failure } = await this.prepareEnvelope();
        const wasUploading = (this.phase as SyncPhase) === "uploading_blobs";
        this.phase = "syncing_events";
        if (wasUploading) await this.setState("syncing");
        const reply = await postSync(this.hubUrl, env, this.fetchImpl);
        this.phase = "idle";
        return await this.applyReply(reply, env.events.map((e) => e.event_id), failure);
      } catch (err) {
        this.phase = "idle";
        this.uploadingBlobs.clear();
        const kind = err instanceof SyncTransportError ? err.kind : "error";
        await this.setState(kind, String(err instanceof Error ? err.message : err));
        return null;
      }
    });
  }

  /** Open WS /ws/mesh; sends the outbox on every (re)connect and applies replies. */
  startMesh(): void {
    if (this.mesh) return;
    this.mesh = new MeshSocket(MeshSocket.urlFor(this.hubUrl), {
      wsFactory: this.opts.wsFactory,
      baseDelayMs: this.opts.wsBaseDelayMs,
      maxDelayMs: this.opts.wsMaxDelayMs,
      onOpen: () => void this.pushViaMesh(),
      onEnvelope: (env) =>
        void this.serial(() => this.applyReply(env, this.wsSent)).catch((err) => this.setState("error", String(err))),
      onDisconnect: () => void this.setState("offline"),
    });
    this.mesh.start();
  }

  stopMesh(): void {
    this.mesh?.stop();
    this.mesh = null;
  }

  private pushViaMesh(): Promise<void> {
    return this.serial(async () => {
      await this.ensureViews();
      if (!this.mesh?.connected) return void (await this.setState("offline"));
      this.phase = "idle";
      this.uploadingBlobs.clear();
      const { env, failure } = await this.prepareEnvelope();
      const wasUploading = (this.phase as SyncPhase) === "uploading_blobs";
      this.phase = "syncing_events";
      if (wasUploading) await this.setState("syncing");
      if (!this.mesh?.send(env)) {
        this.phase = "idle";
        return void (await this.setState("offline"));
      }
      env.events.forEach((e) => this.wsSent.add(e.event_id));
      this.phase = "idle";
      if (failure) await this.setState(failure.kind, blobFailureMessage(failure));
    });
  }

  /** Outbox envelope minus voice notes whose clip is not on the hub (and their dependents). */
  private async prepareEnvelope(): Promise<{ env: SyncEnvelope; failure?: SyncTransportError }> {
    const env = await buildEnvelope(this.store, this.opts.manifest);
    const { held, heldBlobKeys, failure } = await this.uploadPendingBlobs(env.events);
    this.held = held.size;
    this.heldBlobs = heldBlobKeys;
    const withheld = new Set(held);
    // Outbox is HLC-sorted, so a referenced event precedes its dependents: one pass is transitive.
    for (const e of env.events) if (e.ref_event_id && withheld.has(e.ref_event_id)) withheld.add(e.event_id);
    env.events = env.events.filter((e) => !withheld.has(e.event_id));
    return { env, failure };
  }

  /**
   * Once per engine: re-fold the whole log into patient/card views, repairing a
   * crash between appending events and materializing them. Retried if it fails.
   */
  private ensureViews(): Promise<void> {
    this.viewsReady ??= this.withViews(() => rebuildViews(this.store)).then(
      (pending) => this.events.emit("enrichment", { pending }),
      (err) => {
        this.viewsReady = null;
        throw err;
      },
    );
    return this.viewsReady;
  }

  private get fetchImpl(): typeof fetch {
    return this.opts.fetchImpl ?? globalThis.fetch;
  }

  /**
   * Upload clips for outbox voice notes. Runs on the network queue, never under
   * the view lock, and never throws. Transient failures (offline, 5xx/408/429,
   * timeout, unreadable local store) hold the event for retry; after the first
   * "offline" the rest are held without further requests. Permanent outcomes
   * (already present, uploaded, invalid key, hub 4xx, clip gone from this device)
   * release the event so a lost clip can never pin it in the outbox forever.
   */
  private async uploadPendingBlobs(events: CrdtEvent[]): Promise<BlobPass> {
    const pass: BlobPass = { held: new Set(), heldBlobKeys: new Set() };
    const done = new Map<string, boolean>(); // key -> settled (false = transient failure)
    const load = this.opts.getAudioBlob ?? ((key: string) => getAudio(key));
    for (const ev of events) {
      if (ev.event_type !== "VOICE_NOTE_RECORDED") continue;
      const key = (ev.payload as Record<string, unknown> | null)?.audio_blob_key;
      if (!isValidBlobKey(key)) continue; // typed-only (null) or unusable key: nothing to upload
      if (!done.has(key)) {
        if (pass.failure?.kind === "offline") done.set(key, false);
        else {
          this.phase = "uploading_blobs";
          this.uploadingBlobs.add(key);
          await this.setState(this.state);
          try {
            await uploadBlobIfMissing(this.hubUrl, key, () => load(key), this.fetchImpl, this.opts.blobTimeoutMs);
            done.set(key, true);
          } catch (err) {
            done.set(key, false);
            const e = err instanceof SyncTransportError ? err : new SyncTransportError(String(err), "error");
            if (!pass.failure || e.kind === "offline") pass.failure = e;
          } finally {
            this.uploadingBlobs.delete(key);
          }
        }
      }
      if (!done.get(key)) {
        pass.held.add(ev.event_id);
        pass.heldBlobKeys.add(key);
      }
    }
    return pass;
  }

  private async applyReply(reply: SyncEnvelope, sentIds: Iterable<string>, blobFailure?: SyncTransportError): Promise<ApplyResult> {
    const result = await this.withViews(() => applyResponse(this.store, reply, sentIds));
    reply.ack_event_ids.forEach((id) => this.wsSent.delete(id));
    if (result.cards.length) this.events.emit("cards", { cards: result.cards });
    this.events.emit("enrichment", { pending: result.pendingEnrichments });
    if (blobFailure) await this.setState(blobFailure.kind, blobFailureMessage(blobFailure), result.rejected);
    else await this.setState("idle", undefined, result.rejected);
    return result;
  }

  private async setState(state: SyncState, error?: string, rejected = 0): Promise<void> {
    this.state = state;
    this.errorMsg = error ?? null;
    this.events.emit("status", {
      state,
      pendingCount: await this.pendingCount(),
      ...(error ? { error } : {}),
      ...(rejected ? { rejected } : {}),
      ...(this.held ? { heldClips: this.held } : {}),
    });
  }

  private serial<T>(fn: () => Promise<T>): Promise<T> {
    const p = this.queue.then(fn);
    this.queue = p.catch(() => undefined);
    return p;
  }

  private withViews<T>(fn: () => Promise<T>): Promise<T> {
    const p = this.viewQueue.then(fn);
    this.viewQueue = p.catch(() => undefined);
    return p;
  }
}

const blobFailureMessage = (err: SyncTransportError) => `voice clip upload pending (will retry): ${err.message}`;
