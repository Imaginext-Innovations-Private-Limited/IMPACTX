import { describe, expect, it, vi } from "vitest";
import { bindLiveCount } from "../../src/ui/sync_logic";
import { Emitter } from "../../src/sync/emitter";

type Listener = (n: number) => void;

/** Hand-rolled source: records the listener and exposes a vi.fn() unsubscribe. */
function fakeSource() {
  const listeners = new Set<Listener>();
  const unsub = vi.fn(() => {
    listeners.clear();
  });
  const source = (l: Listener) => {
    listeners.add(l);
    return unsub;
  };
  const emit = (n: number) => [...listeners].forEach((l) => l(n));
  return { source, unsub, emit, listeners };
}

describe("bindLiveCount", () => {
  it("calls set with each emitted value while alive, from every source", () => {
    const a = fakeSource();
    const b = fakeSource();
    const set = vi.fn();
    bindLiveCount([a.source, b.source], () => true, set);
    a.emit(1);
    b.emit(2);
    a.emit(3);
    expect(set.mock.calls).toEqual([[1], [2], [3]]);
    expect(a.unsub).not.toHaveBeenCalled();
    expect(b.unsub).not.toHaveBeenCalled();
  });

  it("unsubscribes every source once on the first emit after isAlive flips false, without calling set", () => {
    const a = fakeSource();
    const b = fakeSource();
    const set = vi.fn();
    let alive = true;
    bindLiveCount([a.source, b.source], () => alive, set);
    a.emit(1);
    expect(set).toHaveBeenCalledTimes(1);
    alive = false;
    b.emit(2);
    expect(set).toHaveBeenCalledTimes(1);
    expect(a.unsub).toHaveBeenCalledTimes(1);
    expect(b.unsub).toHaveBeenCalledTimes(1);
    a.emit(3);
    b.emit(4);
    expect(set).toHaveBeenCalledTimes(1);
    expect(a.unsub).toHaveBeenCalledTimes(1);
    expect(b.unsub).toHaveBeenCalledTimes(1);
  });

  it("does not unsubscribe anything while still alive, even without emits", () => {
    const a = fakeSource();
    bindLiveCount([a.source], () => false, vi.fn());
    expect(a.unsub).not.toHaveBeenCalled();
  });

  it("returned disposer unsubscribes all sources and is idempotent", () => {
    const a = fakeSource();
    const b = fakeSource();
    const set = vi.fn();
    const dispose = bindLiveCount([a.source, b.source], () => true, set);
    dispose();
    expect(a.unsub).toHaveBeenCalledTimes(1);
    expect(b.unsub).toHaveBeenCalledTimes(1);
    dispose();
    expect(a.unsub).toHaveBeenCalledTimes(1);
    expect(b.unsub).toHaveBeenCalledTimes(1);
  });

  it("disposer after auto-unsubscribe does not unsubscribe a second time", () => {
    const a = fakeSource();
    const b = fakeSource();
    let alive = true;
    const dispose = bindLiveCount([a.source, b.source], () => alive, vi.fn());
    alive = false;
    a.emit(1);
    expect(a.unsub).toHaveBeenCalledTimes(1);
    expect(b.unsub).toHaveBeenCalledTimes(1);
    dispose();
    expect(a.unsub).toHaveBeenCalledTimes(1);
    expect(b.unsub).toHaveBeenCalledTimes(1);
  });

  it("with no sources, returns a harmless disposer", () => {
    const dispose = bindLiveCount([], () => true, vi.fn());
    expect(() => {
      dispose();
      dispose();
    }).not.toThrow();
  });

  describe("with the real Emitter", () => {
    const adapters = (em: Emitter) => [
      (l: Listener) => em.on("status", (s) => l(s.pendingCount)),
      (l: Listener) => em.on("enrichment", (e) => l(e.pending)),
    ];

    it("feeds set from both event types while alive", () => {
      const em = new Emitter();
      const set = vi.fn();
      bindLiveCount(adapters(em), () => true, set);
      em.emit("status", { state: "idle", pendingCount: 4 });
      em.emit("enrichment", { pending: 7 });
      expect(set.mock.calls).toEqual([[4], [7]]);
    });

    it("after auto-unsubscribe, later emits of either type never reach set", () => {
      const em = new Emitter();
      const set = vi.fn();
      let alive = true;
      bindLiveCount(adapters(em), () => alive, set);
      em.emit("status", { state: "syncing", pendingCount: 1 });
      expect(set).toHaveBeenCalledTimes(1);
      alive = false;
      em.emit("status", { state: "idle", pendingCount: 2 });
      em.emit("status", { state: "idle", pendingCount: 3 });
      em.emit("enrichment", { pending: 9 });
      expect(set).toHaveBeenCalledTimes(1);
    });

    it("disposer stops delivery from the real Emitter", () => {
      const em = new Emitter();
      const set = vi.fn();
      const dispose = bindLiveCount(adapters(em), () => true, set);
      dispose();
      em.emit("status", { state: "idle", pendingCount: 1 });
      em.emit("enrichment", { pending: 1 });
      expect(set).not.toHaveBeenCalled();
    });
  });
});
