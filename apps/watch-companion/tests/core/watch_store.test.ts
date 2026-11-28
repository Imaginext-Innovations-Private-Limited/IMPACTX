import { describe, expect, it } from "vitest";
import type {
  ActionCard,
  CrdtEvent,
  HlcTimestamp,
  SyncEnvelope,
} from "../../../../packages/contracts/ts/index";
import {
  MemoryStorage,
  WatchStore,
  compareHlc,
  createHlc,
  receiveHlc,
  tickHlc,
} from "../../src/core/index";
import { WatchKernel } from "../../src/watch_kernel";

function makeCardEvent(params: {
  eventId: string;
  hlc: HlcTimestamp;
  originNodeId?: string;
  eventType?: "ACTION_CARD_ISSUED" | "CHECKLIST_RECORDED";
  cardId: string;
  payload: Record<string, unknown>;
  patientId?: string | null;
}): CrdtEvent {
  return {
    event_id: params.eventId,
    hlc: params.hlc,
    origin_node_id: params.originNodeId ?? params.hlc.node_id,
    patient_id: params.patientId ?? "patient-1",
    event_type: params.eventType ?? "ACTION_CARD_ISSUED",
    payload: {
      card_id: params.cardId,
      ...params.payload,
    },
    enrichment_state: "NOT_NEEDED",
    ref_event_id: null,
  };
}

describe("HLC (tickHlc, receiveHlc, compareHlc)", () => {
  it("enforces strict monotonicity on tickHlc even when wall clock stalls or regresses", () => {
    const t0 = createHlc("watch-01", 1_000, 0);
    const t1 = tickHlc(t0, 1_000);
    expect(t1).toEqual({ wall_ms: 1_000, logical: 1, node_id: "watch-01" });
    expect(compareHlc(t1, t0)).toBe(1);

    // Physical clock regresses to 900 -> keeps wall_ms=1000, increments logical
    const t2 = tickHlc(t1, 900);
    expect(t2).toEqual({ wall_ms: 1_000, logical: 2, node_id: "watch-01" });
    expect(compareHlc(t2, t1)).toBe(1);

    // Physical clock advances -> resets logical to 0
    const t3 = tickHlc(t2, 1_500);
    expect(t3).toEqual({ wall_ms: 1_500, logical: 0, node_id: "watch-01" });
    expect(compareHlc(t3, t2)).toBe(1);
  });

  it("merges remote HLC strictly ahead of both local and remote across all branches", () => {
    const local = createHlc("watch-01", 2_000, 3);

    // Remote has same wall_ms and higher logical, physical clock behind
    const remoteEqualWall = createHlc("phone-01", 2_000, 5);
    const m1 = receiveHlc(local, remoteEqualWall, 1_800);
    expect(m1).toEqual({ wall_ms: 2_000, logical: 6, node_id: "watch-01" });
    expect(compareHlc(m1, local)).toBe(1);
    expect(compareHlc(m1, remoteEqualWall)).toBe(1);

    // Remote wall_ms ahead of both local and physical time
    const remoteAhead = createHlc("hub-01", 5_000, 4);
    const m2 = receiveHlc(m1, remoteAhead, 2_500);
    expect(m2).toEqual({ wall_ms: 5_000, logical: 5, node_id: "watch-01" });
    expect(compareHlc(m2, m1)).toBe(1);
    expect(compareHlc(m2, remoteAhead)).toBe(1);

    // Physical clock ahead of both local and remote
    const m3 = receiveHlc(m2, remoteAhead, 6_000);
    expect(m3).toEqual({ wall_ms: 6_000, logical: 0, node_id: "watch-01" });
    expect(compareHlc(m3, m2)).toBe(1);
  });

  it("orders ties deterministically by (wall_ms, logical, node_id)", () => {
    const a = createHlc("node-a", 1_000, 2);
    const b = createHlc("node-b", 1_000, 2);
    expect(compareHlc(a, b)).toBe(-1);
    expect(compareHlc(b, a)).toBe(1);
    expect(compareHlc(a, { ...a })).toBe(0);
  });
});

describe("WatchStore persistence, deduplication, and outbox", () => {
  it("persists events, outbox, syncCursor, watchMode, nodeId, and HLC across reloads", () => {
    const storage = new MemoryStorage();
    let clock = 10_000;

    const store1 = new WatchStore({
      nodeId: "watch-alpha",
      initialMode: "CHW_COMPANION",
      storage,
      nowMs: () => clock,
    });

    store1.setWatchMode("PATIENT_FAMILY");
    const hlc1 = store1.tickHlc();
    const localEvt: CrdtEvent = {
      event_id: "evt-local-1",
      hlc: hlc1,
      origin_node_id: "watch-alpha",
      patient_id: "pat-1",
      event_type: "VOICE_NOTE_RECORDED",
      payload: { blob_hash: "abc123", duration_s: 4 },
      enrichment_state: "PENDING",
      ref_event_id: null,
    };
    expect(store1.appendEvent(localEvt)).toBe(true);
    store1.setSyncCursor("cursor-42");

    // Simulate reload on same storage adapter with initialMode defaulted differently
    clock = 9_000; // Even if wall clock regresses on reload, HLC stays monotonic
    const store2 = new WatchStore({
      nodeId: "watch-alpha",
      initialMode: "CHW_COMPANION",
      storage,
      nowMs: () => clock,
    });

    expect(store2.getNodeId()).toBe("watch-alpha");
    expect(store2.getWatchMode()).toBe("PATIENT_FAMILY");
    expect(store2.getSyncCursor()).toBe("cursor-42");
    expect(store2.getEvents()).toHaveLength(1);
    expect(store2.getOutboxEventIds()).toEqual(["evt-local-1"]);

    const hlcAfterReload = store2.tickHlc();
    expect(compareHlc(hlcAfterReload, hlc1)).toBe(1);
  });

  it("deduplicates local and remote events idempotently without polluting outbox", () => {
    const storage = new MemoryStorage();
    const store = new WatchStore({
      nodeId: "watch-01",
      storage,
      nowMs: () => 5_000,
    });

    const localEvt: CrdtEvent = {
      event_id: "evt-dup-1",
      hlc: store.tickHlc(),
      origin_node_id: "watch-01",
      patient_id: "pat-1",
      event_type: "CHECKLIST_RECORDED",
      payload: { ok: true },
      enrichment_state: "NOT_NEEDED",
      ref_event_id: null,
    };

    expect(store.appendEvent(localEvt)).toBe(true);
    expect(store.appendEvent(localEvt)).toBe(false);
    expect(store.getEvents()).toHaveLength(1);
    expect(store.getOutboxEventIds()).toEqual(["evt-dup-1"]);

    const remoteEvt = makeCardEvent({
      eventId: "evt-remote-1",
      hlc: createHlc("hub-01", 6_000, 0),
      cardId: "card-1",
      payload: {
        title: "PHC Follow-up",
        summary: "Visit PHC today",
        priority: "HIGH",
        status: "OPEN",
        watch_mode: null,
      },
    });

    expect(store.applyRemoteEvents([remoteEvt, remoteEvt])).toBe(1);
    expect(store.applyRemoteEvents([remoteEvt])).toBe(0);
    expect(store.getEvents()).toHaveLength(2);
    // Remote events must not enter local outbox
    expect(store.getOutboxEventIds()).toEqual(["evt-dup-1"]);

    expect(store.ackOutbox(["evt-dup-1"])).toBe(1);
    expect(store.getOutboxEventIds()).toEqual([]);
  });
});

describe("ActionCard LWW merge, watch_mode filtering, and sorting", () => {
  it("never regresses ACKNOWLEDGED or COMPLETED status back to OPEN on out-of-order replay", () => {
    const storage = new MemoryStorage();
    const store = new WatchStore({
      nodeId: "watch-01",
      storage,
      nowMs: () => 10_000,
    });

    // Newer acknowledgement arrives FIRST
    const ackLater = makeCardEvent({
      eventId: "evt-ack",
      hlc: createHlc("watch-01", 2_000, 1),
      eventType: "CHECKLIST_RECORDED",
      cardId: "card-emergency",
      payload: {
        status: "ACKNOWLEDGED",
      },
    });

    // Older card issuance arrives AFTER (replay / out-of-order sync)
    const issuedEarlier = makeCardEvent({
      eventId: "evt-issue",
      hlc: createHlc("hub-01", 1_000, 0),
      cardId: "card-emergency",
      payload: {
        title: "Immediate 108 Referral",
        summary: "Severe danger sign detected",
        priority: "CRITICAL",
        severity: "RED_EMERGENCY",
        status: "OPEN",
        target_tier: "TIER_0_WATCH",
        watch_mode: "CHW_COMPANION",
      },
    });

    store.applyRemoteEvents([ackLater]);
    store.applyRemoteEvents([issuedEarlier]);

    const card = store.getActionCard("card-emergency");
    expect(card).toBeDefined();
    expect(card?.status).toBe("ACKNOWLEDGED");
    expect(card?.title).toBe("Immediate 108 Referral");
    expect(card?.priority).toBe("CRITICAL");
    expect(card?.severity).toBe("RED_EMERGENCY");

    // Even newer completion from another node advances status to COMPLETED
    const completedLater = makeCardEvent({
      eventId: "evt-complete",
      hlc: createHlc("phone-01", 3_000, 0),
      eventType: "CHECKLIST_RECORDED",
      cardId: "card-emergency",
      payload: {
        status: "COMPLETED",
      },
    });
    store.applyRemoteEvents([completedLater]);
    expect(store.getActionCard("card-emergency")?.status).toBe("COMPLETED");

    // Replaying the OPEN issuance again changes nothing
    expect(store.applyRemoteEvents([issuedEarlier])).toBe(0);
    expect(store.getActionCard("card-emergency")?.status).toBe("COMPLETED");
  });

  it("filters by watch_mode (including null) and sorts OPEN first then CRITICAL -> LOW", () => {
    const storage = new MemoryStorage();
    const store = new WatchStore({
      nodeId: "watch-01",
      initialMode: "CHW_COMPANION",
      storage,
    });

    const events: CrdtEvent[] = [
      makeCardEvent({
        eventId: "e1",
        hlc: createHlc("hub", 100, 0),
        cardId: "card-open-low",
        payload: {
          title: "Routine check",
          summary: "Low priority shared card",
          priority: "LOW",
          status: "OPEN",
          watch_mode: null,
        },
      }),
      makeCardEvent({
        eventId: "e2",
        hlc: createHlc("hub", 101, 0),
        cardId: "card-ack-critical",
        payload: {
          title: "Acked critical",
          summary: "Already acknowledged",
          priority: "CRITICAL",
          status: "ACKNOWLEDGED",
          watch_mode: "CHW_COMPANION",
        },
      }),
      makeCardEvent({
        eventId: "e3",
        hlc: createHlc("hub", 102, 0),
        cardId: "card-open-high-chw",
        payload: {
          title: "CHW referral",
          summary: "High priority CHW card",
          priority: "HIGH",
          status: "OPEN",
          watch_mode: "CHW_COMPANION",
        },
      }),
      makeCardEvent({
        eventId: "e4",
        hlc: createHlc("hub", 103, 0),
        cardId: "card-open-critical-patient",
        payload: {
          title: "Vaccine due today",
          summary: "Patient-family critical card",
          priority: "CRITICAL",
          status: "OPEN",
          watch_mode: "PATIENT_FAMILY",
        },
      }),
      makeCardEvent({
        eventId: "e5",
        hlc: createHlc("hub", 104, 0),
        cardId: "card-open-medium-shared",
        payload: {
          title: "Hydration reminder",
          summary: "Shared medium card",
          priority: "MEDIUM",
          status: "OPEN",
          watch_mode: null,
        },
      }),
    ];

    store.applyRemoteEvents(events);

    const chwCards = store.getVisibleActionCards().map((c: ActionCard) => c.card_id);
    expect(chwCards).toEqual([
      "card-open-high-chw",
      "card-open-medium-shared",
      "card-open-low",
      "card-ack-critical",
    ]);

    store.setWatchMode("PATIENT_FAMILY");
    const patientCards = store.getVisibleActionCards().map((c: ActionCard) => c.card_id);
    expect(patientCards).toEqual([
      "card-open-critical-patient",
      "card-open-medium-shared",
      "card-open-low",
    ]);
  });
});

describe("WatchKernel delegation to WatchStore", () => {
  it("delegates danger screening, sync envelope outbox/cursor, and reload state", () => {
    const storage = new MemoryStorage();
    let clock = 50_000;

    const kernel1 = new WatchKernel("watch-k1", "CHW_COMPANION", {
      storage,
      nowMs: () => clock,
    });

    const result = kernel1.screenDangerSigns({
      patientId: "pat-99",
      unableToDrinkOrBreastfeed: false,
      vomitsEverything: false,
      convulsions: true,
      lethargicOrUnconscious: false,
    });
    expect(result.severity).toBe("RED_EMERGENCY");
    expect(result.event.payload.referral_required).toBe(true);
    expect(result.event.payload.confidence).toBe(1.0);
    expect(result.event.payload.execution_target).toBe("LOCAL_DETERMINISTIC");

    kernel1.toggleWatchMode();
    expect(kernel1.getManifest(88).watch_mode).toBe("PATIENT_FAMILY");
    expect(kernel1.getManifest(88).tier).toBe("TIER_0_WATCH");

    const env = kernel1.buildSyncEnvelope();
    expect(env.events).toHaveLength(1);
    expect(env.events[0].event_id).toBe(result.event.event_id);

    clock = 51_000;
    const response: SyncEnvelope = {
      envelope_id: "resp-1",
      sender_manifest: {
        node_id: "hub-01",
        tier: "TIER_2_HUB",
        ram_mb: 32768,
        cpu_cores: 16,
        battery_pct: 100,
        has_npu: true,
        installed_models: [],
        watch_mode: null,
      },
      sender_hlc: createHlc("hub-01", 52_000, 0),
      since_cursor: null,
      next_cursor: "hub-cursor-7",
      events: [
        makeCardEvent({
          eventId: "hub-card-evt-1",
          hlc: createHlc("hub-01", 52_000, 1),
          cardId: "card-hub-1",
          payload: {
            title: "Emergency 108",
            summary: "Convulsions flagged",
            priority: "CRITICAL",
            status: "OPEN",
            watch_mode: "PATIENT_FAMILY",
          },
        }),
      ],
      ack_event_ids: [result.event.event_id],
      schema_version: "1.0.0",
    };

    kernel1.applySyncResponse(response);

    // Reload WatchKernel on same storage
    const kernel2 = new WatchKernel("watch-k1", "CHW_COMPANION", { storage });
    expect(kernel2.getWatchMode()).toBe("PATIENT_FAMILY");
    expect(kernel2.getStore().getSyncCursor()).toBe("hub-cursor-7");
    expect(kernel2.getStore().getOutboxEvents()).toHaveLength(0);
    expect(kernel2.getVisibleActionCards().map((c) => c.card_id)).toEqual(["card-hub-1"]);
    expect(kernel2.buildSyncEnvelope().since_cursor).toBe("hub-cursor-7");
  });
});
