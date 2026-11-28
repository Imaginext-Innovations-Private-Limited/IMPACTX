import { IDBFactory } from "fake-indexeddb";
import { describe, expect, it } from "vitest";
import { openStore } from "../../src/core";
import { SyncEngine, buildEnvelope, postSync, project, readBatteryPct, SyncTransportError } from "../../src/sync";
import { fakeFetch, freshStore, hubEvent, reply } from "./helpers";

const patientPayload = (name: string) => ({
  patient_id: "p1", full_name: name, date_of_birth: null, age_months: 14, sex: "F", village_id: "v1",
  household_id: null, is_pregnant: false, gestational_weeks: null, preferred_language: "hi",
  registered_by_node: "phone-1", metadata: {},
});

describe("SyncEngine (HTTP)", () => {
  it("outbox survives store reopen and is what the envelope carries", async () => {
    const f = new IDBFactory();
    const s = await openStore("phone-1", "reopen", f);
    const e = await new SyncEngine(s).enqueue({ event_type: "PATIENT_REGISTERED", payload: patientPayload("Sita"), patient_id: "p1" });
    s.close();
    const s2 = await openStore("phone-1", "reopen", f);
    const env = await buildEnvelope(s2);
    expect(env.events.map((x) => x.event_id)).toEqual([e.event_id]);
    expect(env.sender_manifest.tier).toBe("TIER_1_PHONE");
    expect(env.schema_version).toBe("1.0.0");
    expect(env.sender_hlc.node_id).toBe("phone-1");
  });

  it("acked events leave the outbox, unacked stay; cursor persisted and sent next time", async () => {
    const s = await freshStore();
    const eng0 = new SyncEngine(s);
    const a = await eng0.enqueue({ event_type: "CHECKLIST_RECORDED", payload: {} });
    const b = await eng0.enqueue({ event_type: "CHECKLIST_RECORDED", payload: {} });
    const { fn, sent } = fakeFetch(() => reply({ ack_event_ids: [a.event_id], next_cursor: "seq:7" }));
    const eng = new SyncEngine(s, { fetchImpl: fn });
    expect(await eng.syncNow()).not.toBeNull();
    expect((await s.getPendingEvents()).map((e) => e.event_id)).toEqual([b.event_id]);
    expect(await s.getAllEvents()).toHaveLength(2);
    expect(await s.getCursor()).toBe("seq:7");
    await eng.syncNow();
    expect(sent[0].since_cursor).toBeNull();
    expect(sent[1].since_cursor).toBe("seq:7");
    expect(sent[1].events.map((e) => e.event_id)).toEqual([b.event_id]);
  });

  it("incoming events are deduped and never land in the outbox", async () => {
    const s = await freshStore();
    const ev = hubEvent("h1", 50);
    const { fn } = fakeFetch(() => reply({ events: [ev, ev] }));
    const eng = new SyncEngine(s, { fetchImpl: fn });
    const r1 = await eng.syncNow();
    const r2 = await eng.syncNow();
    expect(r1!.newEvents).toHaveLength(1);
    expect(r2!.newEvents).toHaveLength(0);
    expect(await s.getAllEvents()).toHaveLength(1);
    expect(await s.getPendingEvents()).toHaveLength(0);
  });

  it("offline / hub errors keep the outbox and report status", async () => {
    const s = await freshStore();
    const states: string[] = [];
    let mode: "throw" | "500" = "throw";
    const { fn } = fakeFetch(() => (mode === "throw" ? new TypeError("Failed to fetch") : 500));
    const eng = new SyncEngine(s, { fetchImpl: fn });
    eng.events.on("status", (st) => states.push(`${st.state}:${st.pendingCount}`));
    await eng.enqueue({ event_type: "CHECKLIST_RECORDED", payload: {} });
    expect(await eng.syncNow()).toBeNull();
    expect(eng.status).toBe("offline");
    mode = "500";
    expect(await eng.syncNow()).toBeNull();
    expect(eng.status).toBe("error");
    expect(await s.getPendingEvents()).toHaveLength(1);
    expect(states).toEqual(["idle:1", "syncing:1", "offline:1", "syncing:1", "error:1"]);
  });

  it("garbage hub reply is an error, not data loss", async () => {
    const s = await freshStore();
    const fn = (async () => new Response('{"error":"x"}', { status: 200 })) as unknown as typeof fetch;
    const eng = new SyncEngine(s, { fetchImpl: fn });
    await eng.enqueue({ event_type: "CHECKLIST_RECORDED", payload: {} });
    expect(await eng.syncNow()).toBeNull();
    expect(eng.status).toBe("error");
    expect(await s.getPendingEvents()).toHaveLength(1);
  });

  it("materializes patients (LWW by HLC) and action cards, emits cards", async () => {
    const s = await freshStore();
    const card = {
      card_id: "k1", patient_id: "p1", title: "Refer to PHC", summary: "Fast breathing", action_steps: ["Go"],
      priority: "HIGH", severity: "YELLOW_PHC", status: "OPEN", target_tier: "TIER_1_PHONE", watch_mode: null,
      source_event_id: null, due_by: null, language: "hi",
    };
    const { fn } = fakeFetch(() =>
      reply({
        events: [
          hubEvent("p-new", 200, { event_type: "PATIENT_REGISTERED", patient_id: "p1", payload: { full_name: "Gita" } }),
          hubEvent("p-old", 100, { event_type: "PATIENT_REGISTERED", patient_id: "p1", payload: patientPayload("Sita") }),
          hubEvent("c1", 300, { event_type: "ACTION_CARD_ISSUED", patient_id: "p1", payload: card }),
        ],
      }),
    );
    const eng = new SyncEngine(s, { fetchImpl: fn });
    const seen: string[] = [];
    eng.events.on("cards", ({ cards }) => seen.push(...cards.map((c) => c.card_id)));
    await eng.syncNow();
    const p = await s.getPatient("p1");
    expect(p?.full_name).toBe("Gita");
    expect(p?.village_id).toBe("v1");
    expect(p?.age_months).toBe(14);
    expect(await s.listActionCards()).toEqual([card]);
    expect(seen).toEqual(["k1"]);
  });

  it("malformed payloads are kept in the log but not materialized as garbage", async () => {
    const s = await freshStore();
    const bad = hubEvent("bad", 10, { event_type: "ACTION_CARD_ISSUED", payload: { card_id: "k2", priority: 42, title: 7 } });
    const { fn } = fakeFetch(() => reply({ events: [bad, { nope: true } as never] }));
    const r = await new SyncEngine(s, { fetchImpl: fn }).syncNow();
    expect(r!.rejected).toBe(1);
    expect(await s.getEvent("bad")).toBeDefined();
    const [c] = await s.listActionCards();
    expect(c.priority).toBe("MEDIUM");
    expect(c.title).toBe("Action Card");
  });

  it("pending-enrichment count drops to 0 after ENRICHMENT_COMPLETED arrives", async () => {
    const s = await freshStore();
    const pend: number[] = [];
    let completed: string | null = null;
    const { fn } = fakeFetch(() =>
      reply({ events: completed ? [hubEvent("enr", 9e12, { event_type: "ENRICHMENT_COMPLETED", ref_event_id: completed })] : [] }),
    );
    const eng = new SyncEngine(s, { fetchImpl: fn });
    eng.events.on("enrichment", ({ pending }) => pend.push(pending));
    const v = await eng.enqueue({
      event_type: "VOICE_NOTE_RECORDED", payload: { transcript_hint: "x" }, patient_id: "p1", enrichment_state: "PENDING",
    });
    expect(await eng.pendingEnrichmentCount()).toBe(1);
    completed = v.event_id;
    await eng.syncNow();
    expect(await eng.pendingEnrichmentCount()).toBe(0);
    expect(pend.at(0)).toBe(1);
    expect(pend.at(-1)).toBe(0);
  });

  it("battery falls back to 100 and reads navigator.getBattery when present", async () => {
    expect(await readBatteryPct(undefined)).toBe(100);
    expect(await readBatteryPct({ getBattery: async () => ({ level: 0.42 }) })).toBe(42);
    expect(await readBatteryPct({ getBattery: async () => { throw new Error("x"); } })).toBe(100);
  });

  it("rebuilds views from the log after a crash between append and materialize", async () => {
    const s = await freshStore();
    await s.appendEvent(hubEvent("p", 10, { event_type: "PATIENT_REGISTERED", patient_id: "p1", payload: patientPayload("Sita") }), { outbox: false });
    await s.appendEvent(hubEvent("c", 11, { event_type: "ACTION_CARD_ISSUED", payload: { card_id: "k9", title: "T", summary: "S" } }), { outbox: false });
    expect(await s.listPatients()).toHaveLength(0);
    const { fn } = fakeFetch(() => new TypeError("offline")); // views repair even when the hub is down
    await new SyncEngine(s, { fetchImpl: fn }).syncNow();
    expect((await s.getPatient("p1"))?.full_name).toBe("Sita");
    expect((await s.listActionCards()).map((c) => c.card_id)).toEqual(["k9"]);
  });

  it("ignores acks for events that were not sent", async () => {
    const s = await freshStore();
    const eng0 = new SyncEngine(s);
    const a = await eng0.enqueue({ event_type: "CHECKLIST_RECORDED", payload: {} });
    let unsent = "";
    // Hub replies acking what it got plus an id it never received (enqueued mid-flight).
    const { fn } = fakeFetch((sent) => reply({ ack_event_ids: [...sent.events.map((e) => e.event_id), unsent] }));
    const midFlight = (async (u: string, init: RequestInit) => {
      unsent = (await eng0.enqueue({ event_type: "CHECKLIST_RECORDED", payload: {} })).event_id;
      return fn(u, init);
    }) as unknown as typeof fetch;
    await new SyncEngine(s, { fetchImpl: midFlight }).syncNow();
    expect((await s.getPendingEvents()).map((e) => e.event_id)).toEqual([unsent]);
    expect(unsent).not.toBe(a.event_id);
  });

  it("holds the cursor when a reply contains a rejected event, but applies and acks the rest", async () => {
    const s = await freshStore();
    const a = await new SyncEngine(s).enqueue({ event_type: "CHECKLIST_RECORDED", payload: {} });
    const { fn } = fakeFetch(() => reply({ events: [hubEvent("ok", 5), { bad: 1 } as never], ack_event_ids: [a.event_id], next_cursor: "seq:9" }));
    const eng = new SyncEngine(s, { fetchImpl: fn });
    const rejected: (number | undefined)[] = [];
    eng.events.on("status", (st) => rejected.push(st.rejected));
    const r = await eng.syncNow();
    expect(r!.rejected).toBe(1);
    expect(await s.getEvent("ok")).toBeDefined();
    expect(await s.getPendingEvents()).toHaveLength(0);
    expect(await s.getCursor()).toBeNull();
    expect(rejected.at(-1)).toBe(1);
  });

  it("times out a stalled response body", async () => {
    const fn = (async (_u: string, init: RequestInit) => ({
      ok: true,
      status: 200,
      json: () => new Promise((_, rej) => init.signal!.addEventListener("abort", () => rej(new Error("aborted")))),
    })) as unknown as typeof fetch;
    const env = await buildEnvelope(await freshStore());
    const err = await postSync("http://hub", env, fn, 20).catch((e) => e);
    expect(err).toBeInstanceOf(SyncTransportError);
    expect(err.kind).toBe("error");
  });

  it("interleaved enqueue + rebuild/apply leaves views equal to the log projection", async () => {
    const s = await freshStore();
    await s.appendEvent(hubEvent("seed", 1, { event_type: "PATIENT_REGISTERED", patient_id: "p1", payload: patientPayload("Old") }), { outbox: false });
    const { fn } = fakeFetch(() => reply({ events: [hubEvent("c", 2, { event_type: "ACTION_CARD_ISSUED", payload: { card_id: "k1", title: "T", summary: "S" } })] }));
    const eng = new SyncEngine(s, { fetchImpl: fn });
    // Fire the sync (rebuild + apply) and local edits without awaiting in between.
    await Promise.all([
      eng.syncNow(),
      eng.enqueue({ event_type: "PATIENT_REGISTERED", patient_id: "p1", payload: { full_name: "New" } }),
      eng.enqueue({ event_type: "CHECKLIST_RECORDED", payload: { card_id: "k1", status: "COMPLETED" } }),
      eng.syncNow(),
    ]);
    const proj = project(await s.getAllEvents());
    expect(await s.listPatients()).toEqual([...proj.patients.values()]);
    expect(await s.listActionCards()).toEqual([...proj.cards.values()]);
    expect((await s.getPatient("p1"))?.full_name).toBe("New");
    expect((await s.listActionCards())[0].status).toBe("COMPLETED");
  });

  it("enqueue is not blocked by a stalled hub request", async () => {
    const s = await freshStore();
    const eng = new SyncEngine(s, { fetchImpl: (() => new Promise(() => {})) as unknown as typeof fetch });
    void eng.syncNow(); // never resolves (timeout is 15s)
    const e = await eng.enqueue({ event_type: "CHECKLIST_RECORDED", payload: {} });
    expect(await s.getEvent(e.event_id)).toBeDefined();
  });
});
