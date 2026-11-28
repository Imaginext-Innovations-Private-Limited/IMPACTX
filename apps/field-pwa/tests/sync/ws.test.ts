import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SyncEnvelope } from "../../../../packages/contracts/ts/index";
import { MeshSocket, SyncEngine, backoffDelay, type WsLike } from "../../src/sync";
import { freshStore, hubEvent, reply } from "./helpers";

class FakeWs implements WsLike {
  static all: FakeWs[] = [];
  readyState = 0;
  sent: SyncEnvelope[] = [];
  onopen: WsLike["onopen"] = null;
  onclose: WsLike["onclose"] = null;
  onerror: WsLike["onerror"] = null;
  onmessage: WsLike["onmessage"] = null;
  constructor(readonly url: string) {
    FakeWs.all.push(this);
  }
  send(d: string) {
    this.sent.push(JSON.parse(d));
  }
  close() {
    if (this.readyState === 3) return;
    this.readyState = 3;
    this.onclose?.({});
  }
  open() {
    this.readyState = 1;
    this.onopen?.({});
  }
  deliver(msg: unknown) {
    this.onmessage?.({ data: JSON.stringify(msg) });
  }
}
const factory = (u: string) => new FakeWs(u);
// Only timers are faked; fake-indexeddb runs on setImmediate, so flushing that drains IDB work.
const fakeTimers = () => vi.useFakeTimers({ toFake: ["setTimeout", "clearTimeout"] });
const { setImmediate: immediate } = globalThis as unknown as { setImmediate: (f: () => void) => void };
const flush = async () => {
  for (let i = 0; i < 30; i++) await new Promise<void>((r) => immediate(r));
};

describe("MeshSocket reconnect/backoff", () => {
  beforeEach(() => {
    fakeTimers();
    FakeWs.all = [];
  });
  afterEach(() => vi.useRealTimers());

  it("computes capped exponential delays", () => {
    expect([0, 1, 2, 3, 10].map((a) => backoffDelay(a, 100, 1000))).toEqual([100, 200, 400, 800, 1000]);
  });

  it("reconnects with growing delay, resets after open, stops on stop()", () => {
    const m = new MeshSocket(MeshSocket.urlFor("http://hub:8000/"), { wsFactory: factory, baseDelayMs: 100, maxDelayMs: 1000, onEnvelope: () => {} });
    m.start();
    expect(FakeWs.all[0].url).toBe("ws://hub:8000/ws/mesh");
    FakeWs.all[0].close();
    vi.advanceTimersByTime(99);
    expect(FakeWs.all).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(FakeWs.all).toHaveLength(2);
    FakeWs.all[1].close();
    vi.advanceTimersByTime(199);
    expect(FakeWs.all).toHaveLength(2);
    vi.advanceTimersByTime(1);
    expect(FakeWs.all).toHaveLength(3);
    FakeWs.all[2].open();
    FakeWs.all[2].close();
    vi.advanceTimersByTime(100);
    expect(FakeWs.all).toHaveLength(4);
    m.stop();
    vi.advanceTimersByTime(10000);
    expect(FakeWs.all).toHaveLength(4);
    expect(m.send(reply())).toBe(false);
  });
});

describe("SyncEngine over WS", () => {
  beforeEach(() => {
    fakeTimers();
    FakeWs.all = [];
  });
  afterEach(() => vi.useRealTimers());

  it("pushes outbox on open, applies reply envelopes, ignores error frames", async () => {
    const s = await freshStore();
    const eng = new SyncEngine(s, { hubUrl: "https://hub", wsFactory: factory, wsBaseDelayMs: 10 });
    const e = await eng.enqueue({ event_type: "CHECKLIST_RECORDED", payload: {} });
    eng.startMesh();
    const ws = FakeWs.all[0];
    expect(ws.url).toBe("wss://hub/ws/mesh");
    ws.open();
    await flush();
    expect(ws.sent[0].events.map((x) => x.event_id)).toEqual([e.event_id]);
    ws.deliver({ error: "invalid_sync_envelope" });
    ws.deliver(reply({ ack_event_ids: [e.event_id], next_cursor: "seq:3", events: [hubEvent("h", 5)] }));
    await flush();
    expect(await s.getPendingEvents()).toHaveLength(0);
    expect(await s.getCursor()).toBe("seq:3");
    expect(await s.getEvent("h")).toBeDefined();

    ws.close();
    await flush();
    expect(eng.status).toBe("offline");
    vi.advanceTimersByTime(10);
    expect(FakeWs.all).toHaveLength(2);
    eng.stopMesh();
  });
});
