import "fake-indexeddb/auto";
import { IDBFactory } from "fake-indexeddb";
import { describe, expect, it } from "vitest";
import { openStore, receive, tick } from "../../src/core";
import type { CrdtEvent } from "../../src/core";

const ev = (id: string, wall: number, logical = 0): CrdtEvent => ({
  event_id: id,
  hlc: { wall_ms: wall, logical, node_id: "n1" },
  origin_node_id: "n1",
  patient_id: "p1",
  event_type: "PATIENT_REGISTERED",
  payload: {},
  enrichment_state: "NOT_NEEDED",
  ref_event_id: null,
});

describe("store", () => {
  it("appends and replays in HLC order across reopen", async () => {
    const f = new IDBFactory();
    const s = await openStore("n1", "t", f);
    await s.appendEvent(ev("b", 20));
    await s.appendEvent(ev("a", 10));
    s.close();
    const s2 = await openStore("n1", "t", f);
    expect((await s2.getAllEvents()).map((e) => e.event_id)).toEqual(["a", "b"]);
  });

  it("is idempotent on duplicate event_id", async () => {
    const s = await openStore("n1", "t", new IDBFactory());
    expect(await s.appendEvent(ev("a", 1))).toBe(true);
    expect(await s.appendEvent(ev("a", 1))).toBe(false);
    expect(await s.getAllEvents()).toHaveLength(1);
    expect(await s.getPendingEvents()).toHaveLength(1);
  });

  it("markAcked removes only acked from outbox, keeps log", async () => {
    const s = await openStore("n1", "t", new IDBFactory());
    for (const [i, id] of ["a", "b", "c"].entries()) await s.appendEvent(ev(id, i + 1));
    await s.markAcked(["b"]);
    expect((await s.getPendingEvents()).map((e) => e.event_id)).toEqual(["a", "c"]);
    expect(await s.getAllEvents()).toHaveLength(3);
  });

  it("remote-origin append skips outbox", async () => {
    const s = await openStore("n1", "t", new IDBFactory());
    await s.appendEvent(ev("r", 1), { outbox: false });
    expect(await s.getPendingEvents()).toHaveLength(0);
    expect(await s.getEvent("r")).toBeDefined();
  });

  it("persists cursor, patients and cards", async () => {
    const f = new IDBFactory();
    const s = await openStore("n1", "t", f);
    expect(await s.getCursor()).toBeNull();
    await s.setCursor("c1");
    await s.putPatient({ patient_id: "p1" } as never);
    await s.putActionCard({ card_id: "k1" } as never);
    s.close();
    const s2 = await openStore("n1", "t", f);
    expect(await s2.getCursor()).toBe("c1");
    expect(await s2.listPatients()).toHaveLength(1);
    expect(await s2.listActionCards()).toHaveLength(1);
  });
});

describe("hlc", () => {
  it("stays monotonic across reload, even if wall clock goes back", async () => {
    const f = new IDBFactory();
    const s = await openStore("n1", "t", f);
    const a = await s.tick(1000);
    const b = await s.tick(1000);
    s.close();
    const s2 = await openStore("n1", "t", f);
    const c = await s2.tick(500);
    expect([a, b, c].map((h) => [h.wall_ms, h.logical])).toEqual([[1000, 0], [1000, 1], [1000, 2]]);
  });

  it("receive merges remote and persists", async () => {
    const f = new IDBFactory();
    const s = await openStore("n1", "t", f);
    await s.tick(100);
    const m = await s.receive({ wall_ms: 500, logical: 7, node_id: "hub" }, 200);
    expect(m).toEqual({ wall_ms: 500, logical: 8, node_id: "n1" });
    s.close();
    const next = await (await openStore("n1", "t", f)).tick(300);
    expect(next).toEqual({ wall_ms: 500, logical: 9, node_id: "n1" });
  });

  it("pure receive rule cases", () => {
    const p = { wall_ms: 10, logical: 3, node_id: "n1" };
    expect(receive(p, { wall_ms: 10, logical: 5, node_id: "h" }, 5).logical).toBe(6);
    expect(receive(p, { wall_ms: 4, logical: 9, node_id: "h" }, 5).logical).toBe(4);
    expect(receive(p, { wall_ms: 4, logical: 9, node_id: "h" }, 50)).toEqual({ wall_ms: 50, logical: 0, node_id: "n1" });
    expect(tick(p, 11)).toEqual({ wall_ms: 11, logical: 0, node_id: "n1" });
  });
});
