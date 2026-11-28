import { describe, expect, it } from "vitest";
import type { SyncEnvelope } from "../../../../packages/contracts/ts/index";
import { SyncEngine, isValidBlobKey, uploadBlobIfMissing, type WsLike } from "../../src/sync";
import { freshStore, reply } from "./helpers";

type Call = { method: string; url: string; contentType?: string; body?: Uint8Array };
type Mode = "ok" | "offline" | 500 | 400;

/** Fake hub: blob store + /api/v1/sync that acks everything it receives. */
function fakeHub(initial: Record<string, Uint8Array> = {}) {
  const blobs = new Map(Object.entries(initial));
  const calls: Call[] = [];
  const syncs: SyncEnvelope[] = [];
  const hub = { blobs, calls, syncs, blobMode: "ok" as Mode, syncMode: "ok" as Mode, fn: null as unknown as typeof fetch };
  hub.fn = (async (url: string, init: RequestInit = {}) => {
    const method = init.method ?? "GET";
    const call: Call = { method, url };
    calls.push(call);
    if (url.endsWith("/api/v1/sync")) {
      if (hub.syncMode === "offline") throw new TypeError("Failed to fetch");
      if (typeof hub.syncMode === "number") return new Response("x", { status: hub.syncMode });
      const env = JSON.parse(String(init.body)) as SyncEnvelope;
      syncs.push(env);
      return new Response(JSON.stringify(reply({ ack_event_ids: env.events.map((e) => e.event_id) })), { status: 200 });
    }
    if (hub.blobMode === "offline") throw new TypeError("Failed to fetch");
    const key = decodeURIComponent(url.split("/api/v1/blobs/")[1]);
    if (method === "HEAD") return new Response(null, { status: blobs.has(key) ? 200 : 404 });
    call.contentType = new Headers(init.headers).get("content-type") ?? undefined;
    call.body = new Uint8Array(await (init.body as Blob).arrayBuffer());
    if (typeof hub.blobMode === "number") return new Response("x", { status: hub.blobMode });
    blobs.set(key, call.body);
    return new Response(JSON.stringify({ blob_key: key }), { status: 200 });
  }) as unknown as typeof fetch;
  return hub;
}

class Ws implements WsLike {
  readyState = 0;
  sent: SyncEnvelope[] = [];
  onopen: WsLike["onopen"] = null;
  onclose: WsLike["onclose"] = null;
  onerror: WsLike["onerror"] = null;
  onmessage: WsLike["onmessage"] = null;
  send(d: string) {
    this.sent.push(JSON.parse(d));
  }
  close() {
    this.readyState = 3;
  }
  open() {
    this.readyState = 1;
    this.onopen?.({});
  }
}
const { setImmediate: immediate } = globalThis as unknown as { setImmediate: (f: () => void) => void };
const flush = async () => {
  for (let i = 0; i < 50; i++) await new Promise<void>((r) => immediate(r));
};

const blobCalls = (calls: Call[]) => calls.filter((c) => c.url.includes("/blobs/")).map((c) => c.method);
const bytes = new Uint8Array([1, 2, 3, 250]);
const clip = () => new Blob([bytes], { type: "audio/webm" });
const voice = (eng: SyncEngine, key: string | null) =>
  eng.enqueue({
    event_type: "VOICE_NOTE_RECORDED",
    payload: { audio_blob_key: key, mime_type: "audio/webm", transcript_hint: "" },
    enrichment_state: "PENDING",
  });

describe("uploadBlobIfMissing", () => {
  it("HEAD 404 -> PUT uploads exact bytes + Content-Type, no-store", async () => {
    const hub = fakeHub();
    let init: RequestInit | undefined;
    const spy = ((u: string, i: RequestInit) => ((init = i), hub.fn(u, i))) as unknown as typeof fetch;
    expect(await uploadBlobIfMissing("http://hub/", "vn-1", async () => clip(), spy)).toBe("uploaded");
    expect(hub.calls.map((c) => `${c.method} ${c.url}`)).toEqual(["HEAD http://hub/api/v1/blobs/vn-1", "PUT http://hub/api/v1/blobs/vn-1"]);
    expect(hub.calls[1].contentType).toBe("audio/webm");
    expect([...hub.blobs.get("vn-1")!]).toEqual([...bytes]);
    expect(init?.cache).toBe("no-store");
  });

  it("HEAD 200 skips the PUT and never loads the local clip", async () => {
    const hub = fakeHub({ "vn-1": bytes });
    let loaded = false;
    expect(await uploadBlobIfMissing("http://hub", "vn-1", async () => ((loaded = true), clip()), hub.fn)).toBe("present");
    expect(blobCalls(hub.calls)).toEqual(["HEAD"]);
    expect(loaded).toBe(false);
  });

  it("defaults Content-Type to application/octet-stream", async () => {
    const hub = fakeHub();
    await uploadBlobIfMissing("http://hub", "vn-2", async () => new Blob([bytes]), hub.fn);
    expect(hub.calls[1].contentType).toBe("application/octet-stream");
  });

  it("rejects invalid keys without any request", async () => {
    const hub = fakeHub();
    for (const k of ["", "../etc", "a..b", "-x", "a/b", "a b", "x".repeat(129)]) {
      expect(isValidBlobKey(k)).toBe(false);
      expect(await uploadBlobIfMissing("http://hub", k, async () => clip(), hub.fn)).toBe("rejected");
    }
    expect(hub.calls).toHaveLength(0);
    expect(isValidBlobKey("vn-0f3a.webm_1")).toBe(true);
  });

  it("classifies offline / 5xx as transient errors and 4xx as rejected", async () => {
    const hub = fakeHub();
    hub.blobMode = "offline";
    await expect(uploadBlobIfMissing("http://hub", "vn-1", async () => clip(), hub.fn)).rejects.toMatchObject({ kind: "offline" });
    hub.blobMode = 500;
    await expect(uploadBlobIfMissing("http://hub", "vn-1", async () => clip(), hub.fn)).rejects.toMatchObject({ kind: "error" });
    hub.blobMode = 400;
    expect(await uploadBlobIfMissing("http://hub", "vn-1", async () => clip(), hub.fn)).toBe("rejected");
  });

  it("one deadline covers the whole exchange (stalled PUT body times out)", async () => {
    const fn = (async (_u: string, init: RequestInit) =>
      init.method === "HEAD"
        ? new Response(null, { status: 404 })
        : { ok: true, status: 200, text: () => new Promise((_, rej) => init.signal!.addEventListener("abort", () => rej(new Error("aborted")))) }) as unknown as typeof fetch;
    await expect(uploadBlobIfMissing("http://hub", "vn-1", async () => clip(), fn, 20)).rejects.toMatchObject({ kind: "error" });
  });
});

describe("SyncEngine voice blob sync", () => {
  it("uploads the clip before the envelope push", async () => {
    const s = await freshStore();
    const hub = fakeHub();
    const eng = new SyncEngine(s, { fetchImpl: hub.fn, getAudioBlob: async (k) => (k === "vn-a" ? clip() : undefined) });
    await voice(eng, "vn-a");
    expect(await eng.syncNow()).not.toBeNull();
    expect(hub.calls.map((c) => c.method)).toEqual(["HEAD", "PUT", "POST"]);
    expect([...hub.blobs.get("vn-a")!]).toEqual([...bytes]);
    expect(await s.getPendingEvents()).toHaveLength(0);
    expect(eng.status).toBe("idle");
  });

  it("typed-only notes (audio_blob_key: null) make zero blob calls", async () => {
    const s = await freshStore();
    const hub = fakeHub();
    let loads = 0;
    const eng = new SyncEngine(s, { fetchImpl: hub.fn, getAudioBlob: async () => (loads++, clip()) });
    await voice(eng, null);
    await eng.syncNow();
    expect(blobCalls(hub.calls)).toEqual([]);
    expect(loads).toBe(0);
    expect(await s.getPendingEvents()).toHaveLength(0);
  });

  it("blob already on hub: HEAD only, no PUT", async () => {
    const s = await freshStore();
    const hub = fakeHub({ "vn-a": bytes });
    const eng = new SyncEngine(s, { fetchImpl: hub.fn, getAudioBlob: async () => clip() });
    await voice(eng, "vn-a");
    await eng.syncNow();
    expect(hub.calls.map((c) => c.method)).toEqual(["HEAD", "POST"]);
  });

  it("transient clip failure withholds the voice event from the POST, sends the rest, retries until the clip lands", async () => {
    const s = await freshStore();
    const hub = fakeHub();
    const eng = new SyncEngine(s, { fetchImpl: hub.fn, getAudioBlob: async () => clip() });
    const v = await voice(eng, "vn-a");
    const other = await eng.enqueue({ event_type: "CHECKLIST_RECORDED", payload: {} });
    const held: number[] = [];
    eng.events.on("status", (st) => held.push(st.heldClips ?? 0));
    for (const mode of ["offline", 500] as const) {
      hub.blobMode = mode;
      hub.calls.length = 0;
      expect(await eng.syncNow()).not.toBeNull(); // never throws, other events not blocked
      expect(eng.status).toBe(mode === "offline" ? "offline" : "error");
      expect(eng.heldClips).toBe(1);
      expect(hub.calls.at(-1)!.method).toBe("POST"); // still POSTs (pull + cursor), even if empty
      expect(hub.syncs.at(-1)!.events.map((e) => e.event_id)).not.toContain(v.event_id); // old code sent it
      expect((await s.getPendingEvents()).map((e) => e.event_id)).toEqual([v.event_id]);
    }
    expect(hub.syncs[0].events.map((e) => e.event_id)).toEqual([other.event_id]);
    expect(hub.syncs[1].events).toEqual([]);
    expect(held.at(-1)).toBe(1);
    hub.blobMode = "ok";
    hub.calls.length = 0;
    await eng.syncNow();
    expect(hub.calls.map((c) => c.method)).toEqual(["HEAD", "PUT", "POST"]);
    expect(hub.syncs.at(-1)!.events.map((e) => e.event_id)).toEqual([v.event_id]);
    expect(hub.blobs.has("vn-a")).toBe(true);
    expect(await s.getPendingEvents()).toHaveLength(0);
    expect(eng.status).toBe("idle");
    expect(eng.heldClips).toBe(0);
    expect(held.at(-1)).toBe(0);
    // Every event reached the hub exactly once.
    expect(hub.syncs.flatMap((e) => e.events.map((x) => x.event_id)).sort()).toEqual([v.event_id, other.event_id].sort());
  });

  it("acks are honoured only for ids actually sent (a hub acking a withheld id is ignored)", async () => {
    const s = await freshStore();
    const hub = fakeHub();
    hub.blobMode = 500;
    const v = { id: "" };
    const fn = (async (url: string, init: RequestInit = {}) => {
      if (!url.endsWith("/api/v1/sync")) return hub.fn(url, init);
      const env = JSON.parse(String(init.body)) as SyncEnvelope;
      hub.syncs.push(env);
      return new Response(JSON.stringify(reply({ ack_event_ids: [v.id, ...env.events.map((e) => e.event_id)], next_cursor: "c1" })), { status: 200 });
    }) as unknown as typeof fetch;
    const eng = new SyncEngine(s, { fetchImpl: fn, getAudioBlob: async () => clip() });
    v.id = (await voice(eng, "vn-a")).event_id;
    await eng.syncNow();
    expect((await s.getPendingEvents()).map((e) => e.event_id)).toEqual([v.id]);
    expect(await s.getCursor()).toBe("c1"); // cursor still advances on the (empty) exchange
  });

  it("dependents of a withheld note wait with it and are sent after it; unrelated events go now", async () => {
    const s = await freshStore();
    const hub = fakeHub();
    hub.blobMode = 500;
    const eng = new SyncEngine(s, { fetchImpl: hub.fn, getAudioBlob: async () => clip() });
    const v = await voice(eng, "vn-a");
    const dep = await eng.enqueue({ event_type: "ENRICHMENT_COMPLETED", payload: {}, ref_event_id: v.event_id });
    const dep2 = await eng.enqueue({ event_type: "ACTION_CARD_ISSUED", payload: {}, ref_event_id: dep.event_id });
    const free = await eng.enqueue({ event_type: "ENRICHMENT_COMPLETED", payload: {}, ref_event_id: "acked-elsewhere" });
    await eng.syncNow();
    expect(hub.syncs[0].events.map((e) => e.event_id)).toEqual([free.event_id]);
    expect(eng.heldClips).toBe(1); // only voice notes count as waiting clips
    expect((await s.getPendingEvents()).map((e) => e.event_id)).toEqual([v.event_id, dep.event_id, dep2.event_id]);
    hub.blobMode = "ok";
    await eng.syncNow();
    expect(hub.syncs[1].events.map((e) => e.event_id)).toEqual([v.event_id, dep.event_id, dep2.event_id]);
    expect(await s.getPendingEvents()).toHaveLength(0);
  });

  it("permanent outcomes (hub 4xx) still release the note in the same push", async () => {
    const s = await freshStore();
    const hub = fakeHub();
    hub.blobMode = 400;
    const eng = new SyncEngine(s, { fetchImpl: hub.fn, getAudioBlob: async () => clip() });
    const v = await voice(eng, "vn-a");
    await eng.syncNow();
    expect(hub.syncs[0].events.map((e) => e.event_id)).toEqual([v.event_id]);
    expect(await s.getPendingEvents()).toHaveLength(0);
    expect(eng.heldClips).toBe(0);
  });

  it("offline hub: blob + sync both fail soft, outbox intact", async () => {
    const s = await freshStore();
    const hub = fakeHub();
    hub.blobMode = hub.syncMode = "offline";
    const eng = new SyncEngine(s, { fetchImpl: hub.fn, getAudioBlob: async () => clip() });
    await voice(eng, "vn-a");
    await voice(eng, "vn-b");
    expect(await eng.syncNow()).toBeNull();
    expect(eng.status).toBe("offline");
    expect(blobCalls(hub.calls)).toEqual(["HEAD"]); // first offline short-circuits the rest
    expect(await s.getPendingEvents()).toHaveLength(2);
  });

  it("clip missing on device or invalid key does not pin the event", async () => {
    const s = await freshStore();
    const hub = fakeHub();
    const eng = new SyncEngine(s, { fetchImpl: hub.fn, getAudioBlob: async () => undefined });
    const a = await voice(eng, "vn-gone");
    const b = await voice(eng, "../bad");
    expect(await eng.syncNow()).not.toBeNull();
    expect(blobCalls(hub.calls)).toEqual(["HEAD"]);
    expect(hub.syncs[0].events.map((e) => e.event_id)).toEqual([a.event_id, b.event_id]);
    expect(await s.getPendingEvents()).toHaveLength(0);
    expect(eng.status).toBe("idle");
  });

  it("a throwing local audio store is transient and does not throw out of syncNow", async () => {
    const s = await freshStore();
    const hub = fakeHub();
    let fail = true;
    const eng = new SyncEngine(s, {
      fetchImpl: hub.fn,
      getAudioBlob: async () => {
        if (fail) throw new Error("idb broke");
        return clip();
      },
    });
    const v = await voice(eng, "vn-a");
    expect(await eng.syncNow()).not.toBeNull();
    expect(hub.syncs[0].events).toEqual([]);
    expect((await s.getPendingEvents()).map((e) => e.event_id)).toEqual([v.event_id]);
    fail = false;
    await eng.syncNow();
    expect(await s.getPendingEvents()).toHaveLength(0);
  });

  it("enqueue is not blocked while a blob upload stalls", async () => {
    const s = await freshStore();
    const eng = new SyncEngine(s, { fetchImpl: (() => new Promise(() => {})) as unknown as typeof fetch, getAudioBlob: async () => clip() });
    await voice(eng, "vn-a");
    void eng.syncNow();
    const e = await eng.enqueue({ event_type: "CHECKLIST_RECORDED", payload: {} });
    expect(await s.getEvent(e.event_id)).toBeDefined();
  });

  it("mesh push uploads clips first, withholds notes whose clip failed, and tracks acks only for sent ids", async () => {
    const s = await freshStore();
    const hub = fakeHub();
    hub.blobMode = 500;
    const sockets: Ws[] = [];
    const wsFactory = () => {
      const ws = new Ws();
      sockets.push(ws);
      return ws;
    };
    const eng = new SyncEngine(s, { fetchImpl: hub.fn, wsFactory, wsBaseDelayMs: 1, getAudioBlob: async () => clip() });
    const v = await voice(eng, "vn-a");
    const other = await eng.enqueue({ event_type: "CHECKLIST_RECORDED", payload: {} });
    eng.startMesh();
    sockets[0].open();
    await flush();
    expect(sockets[0].sent).toHaveLength(1);
    expect(sockets[0].sent[0].events.map((e) => e.event_id)).toEqual([other.event_id]); // old code also sent v
    expect(hub.calls.map((c) => c.method)).toEqual(["HEAD", "PUT"]); // before the WS send
    expect(eng.status).toBe("error");
    expect(eng.heldClips).toBe(1);
    sockets[0].onmessage?.({ data: JSON.stringify(reply({ ack_event_ids: [v.event_id, other.event_id] })) });
    await flush();
    expect((await s.getPendingEvents()).map((e) => e.event_id)).toEqual([v.event_id]); // never sent: ack ignored
    hub.blobMode = "ok";
    sockets[0].close();
    sockets[0].onclose?.({});
    await new Promise((r) => setTimeout(r, 30));
    sockets.at(-1)!.open();
    await flush();
    expect(sockets.at(-1)!.sent.at(-1)!.events.map((e) => e.event_id)).toEqual([v.event_id]);
    expect(hub.calls.map((c) => c.method).slice(-2)).toEqual(["HEAD", "PUT"]);
    expect(eng.heldClips).toBe(0);
    sockets.at(-1)!.onmessage?.({ data: JSON.stringify(reply({ ack_event_ids: [v.event_id] })) });
    await flush();
    expect(await s.getPendingEvents()).toHaveLength(0);
    eng.stopMesh();
  });
});

describe("runSync last-sync record", () => {
  it("records held clips as not-ok (not plain success) and clears once they land", async () => {
    const mem = new Map<string, string>();
    (globalThis as { localStorage?: unknown }).localStorage = {
      getItem: (k: string) => mem.get(k) ?? null,
      setItem: (k: string, v: string) => void mem.set(k, v),
    };
    const { runSync, heldClipsFromDetail } = await import("../../src/ui/app_state");
    const { getLastSync } = await import("../../src/ui/settings");
    const s = await freshStore();
    const hub = fakeHub();
    hub.blobMode = 500;
    const eng = new SyncEngine(s, { fetchImpl: hub.fn, getAudioBlob: async () => clip() });
    await voice(eng, "vn-a");
    await voice(eng, "vn-b");
    await runSync(eng);
    const last = getLastSync()!;
    expect(last.ok).toBe(false);
    expect(heldClipsFromDetail(last.detail)).toBe(2);
    hub.blobMode = "ok";
    await runSync(eng);
    expect(getLastSync()).toMatchObject({ ok: true, detail: "ok" });
    delete (globalThis as { localStorage?: unknown }).localStorage;
  });
});
