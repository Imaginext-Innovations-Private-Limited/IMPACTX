import { describe, expect, it } from "vitest";
import {
  CONTRACT_SCHEMA_VERSION,
  type ActionCard,
  type CrdtEvent,
  type SyncEnvelope,
} from "../../../../packages/contracts/ts/index";
import { MemoryStorage, WatchStore } from "../../src/core";
import {
  DEFAULT_HUB_URL,
  MemoryWatchBlobQueue,
  WatchSyncClient,
  isValidHubUrl,
  normalizeHubUrl,
  resolveDefaultHubUrl,
  uploadWatchBlobIfMissing,
} from "../../src/sync";

function makeHubReply(overrides: Partial<SyncEnvelope> = {}): SyncEnvelope {
  return {
    envelope_id: "env-hub-1",
    sender_manifest: {
      node_id: "phc-hub-local",
      tier: "TIER_2_HUB",
      ram_mb: 16384,
      cpu_cores: 8,
      battery_pct: 100,
      has_npu: true,
      installed_models: ["whisper-small"],
      watch_mode: null,
    },
    sender_hlc: { wall_ms: 1_750_000_005_000, logical: 2, node_id: "phc-hub-local" },
    since_cursor: null,
    next_cursor: "cursor-001",
    events: [],
    ack_event_ids: [],
    schema_version: CONTRACT_SCHEMA_VERSION,
    ...overrides,
  };
}

function makeCardEvent(card: ActionCard, wallMs = 1_750_000_004_000): CrdtEvent {
  return {
    event_id: `evt-${card.card_id}-${wallMs}`,
    hlc: { wall_ms: wallMs, logical: 0, node_id: "phc-hub-local" },
    origin_node_id: "phc-hub-local",
    patient_id: card.patient_id,
    event_type: "ACTION_CARD_ISSUED",
    payload: card as unknown as Record<string, unknown>,
    enrichment_state: "NOT_NEEDED",
    ref_event_id: null,
  };
}

describe("uploadWatchBlobIfMissing", () => {
  it("runs HEAD 404 -> PUT with Content-Type and raw binary body", async () => {
    const calls: Array<{ method: string; url: string; contentType: string | null; bytes: number }> = [];
    const mockFetch: typeof fetch = async (input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      const headers = new Headers(init?.headers);
      if (method === "HEAD") {
        calls.push({ method, url, contentType: null, bytes: 0 });
        return new Response(null, { status: 404 });
      }
      const bodyBytes =
        init?.body instanceof Uint8Array
          ? init.body.byteLength
          : init?.body instanceof Blob
            ? init.body.size
            : 0;
      calls.push({
        method,
        url,
        contentType: headers.get("content-type"),
        bytes: bodyBytes,
      });
      return new Response(
        JSON.stringify({
          blob_key: "sos-clip-1",
          content_type: "audio/webm",
          size_bytes: bodyBytes,
          sha256: "a".repeat(64),
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    };

    const audio = new Uint8Array([0x1a, 0x45, 0xdf, 0xa3, 0x01, 0x02]);
    const result = await uploadWatchBlobIfMissing(
      "http://127.0.0.1:8000/",
      "sos-clip-1",
      audio,
      mockFetch,
      { contentType: "audio/webm;codecs=opus" },
    );

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.status).toBe("uploaded");
      expect(result.metadata?.blob_key).toBe("sos-clip-1");
    }
    expect(calls).toEqual([
      {
        method: "HEAD",
        url: "http://127.0.0.1:8000/api/v1/blobs/sos-clip-1",
        contentType: null,
        bytes: 0,
      },
      {
        method: "PUT",
        url: "http://127.0.0.1:8000/api/v1/blobs/sos-clip-1",
        contentType: "audio/webm",
        bytes: 6,
      },
    ]);
  });

  it("skips PUT when HEAD returns 200 (idempotent deduplication)", async () => {
    const methods: string[] = [];
    const mockFetch: typeof fetch = async (_input, init) => {
      methods.push(init?.method ?? "GET");
      return new Response(null, { status: 200 });
    };

    const result = await uploadWatchBlobIfMissing(
      "http://127.0.0.1:8000",
      "sos-existing-1",
      new Blob(["audio"], { type: "audio/ogg" }),
      mockFetch,
    );

    expect(result).toEqual({
      ok: true,
      status: "already_exists",
      blobKey: "sos-existing-1",
    });
    expect(methods).toEqual(["HEAD"]);
  });

  it("rejects invalid blob keys and empty payloads fail-soft without network calls", async () => {
    let called = false;
    const mockFetch: typeof fetch = async () => {
      called = true;
      return new Response(null, { status: 200 });
    };

    const badKey = await uploadWatchBlobIfMissing(
      "http://127.0.0.1:8000",
      "..badkey",
      new Uint8Array([1, 2]),
      mockFetch,
    );
    expect(badKey.ok).toBe(false);
    if (!badKey.ok) expect(badKey.status).toBe("error");

    const emptyBlob = await uploadWatchBlobIfMissing(
      "http://127.0.0.1:8000",
      "valid-key",
      new Uint8Array([]),
      mockFetch,
    );
    expect(emptyBlob.ok).toBe(false);
    if (!emptyBlob.ok) expect(emptyBlob.status).toBe("error");

    expect(called).toBe(false);
  });

  it("returns offline fail-soft when HEAD or PUT throws network error", async () => {
    const mockFetch: typeof fetch = async () => {
      throw new TypeError("Failed to fetch");
    };

    const res = await uploadWatchBlobIfMissing(
      "http://127.0.0.1:8000",
      "sos-offline-1",
      new Uint8Array([1, 2, 3]),
      mockFetch,
    );
    expect(res).toEqual({
      ok: false,
      status: "offline",
      blobKey: "sos-offline-1",
      reason: "Failed to fetch",
    });
  });
});

describe("WatchSyncClient", () => {
  it("performs full roundtrip sync, merges HLCs, acks outbox, ingests ActionCards, and replays idempotently", async () => {
    let clockMs = 1_750_000_000_000;
    const storage = new MemoryStorage();
    const store = new WatchStore({
      nodeId: "watch-asha-01",
      initialMode: "CHW_COMPANION",
      storage,
      nowMs: () => clockMs,
    });

    const card: ActionCard = {
      card_id: "card-anc-101",
      patient_id: "pat-101",
      title: "High BP Follow-up",
      summary: "Refer Kavita Devi to PHC today.",
      action_steps: ["Check BP", "Arrange 108 transport"],
      priority: "CRITICAL",
      severity: "RED_EMERGENCY",
      status: "OPEN",
      target_tier: "TIER_0_WATCH",
      watch_mode: "CHW_COMPANION",
      source_event_id: "evt-hub-triage-1",
      due_by: "2026-11-24",
      language: "en",
    };
    const hubCardEvent = makeCardEvent(card, 1_750_000_004_000);

    const localEvent: CrdtEvent = {
      event_id: "evt-local-triage-1",
      hlc: store.tickHlc(),
      origin_node_id: "watch-asha-01",
      patient_id: "pat-101",
      event_type: "TRIAGE_COMPLETED",
      payload: {
        assessment_id: "assess-1",
        patient_id: "pat-101",
        severity: "RED_EMERGENCY",
        matched_rules: ["convulsions"],
        immediate_actions: ["Immediate 108 referral"],
        referral_required: true,
        rationale: "Danger sign convulsions",
        confidence: 1.0,
        protocol_source: "WHO_IMNCI_ASHA_WATCH_RAPID",
        execution_target: "LOCAL_DETERMINISTIC",
        assessed_at_ms: clockMs,
      },
      enrichment_state: "NOT_NEEDED",
      ref_event_id: null,
    };
    store.appendEvent(localEvent);

    const capturedEnvelopes: SyncEnvelope[] = [];
    const mockFetch: typeof fetch = async (_input, init) => {
      const sent = JSON.parse(String(init?.body)) as SyncEnvelope;
      capturedEnvelopes.push(sent);

      const reply = makeHubReply({
        since_cursor: sent.next_cursor,
        next_cursor: capturedEnvelopes.length === 1 ? "cursor-001" : "cursor-002",
        events: [hubCardEvent],
        ack_event_ids: sent.events.map((e) => e.event_id),
      });
      return new Response(JSON.stringify(reply), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    };

    const client = new WatchSyncClient(store, "http://127.0.0.1:8000", mockFetch);
    const res1 = await client.syncNow();

    expect(res1.ok).toBe(true);
    if (res1.ok) {
      expect(res1.status).toBe("synced");
      expect(res1.ackedCount).toBe(1);
      expect(res1.appliedCount).toBe(1);
      expect(res1.nextCursor).toBe("cursor-001");
    }

    expect(capturedEnvelopes[0].schema_version).toBe(CONTRACT_SCHEMA_VERSION);
    expect(capturedEnvelopes[0].sender_manifest.tier).toBe("TIER_0_WATCH");
    expect(capturedEnvelopes[0].sender_manifest.watch_mode).toBe("CHW_COMPANION");
    expect(capturedEnvelopes[0].since_cursor).toBeNull();
    expect(capturedEnvelopes[0].events).toHaveLength(1);

    expect(store.getOutboxEvents()).toHaveLength(0);
    expect(store.getSyncCursor()).toBe("cursor-001");
    expect(store.getHlc().wall_ms).toBeGreaterThanOrEqual(1_750_000_005_000);
    expect(store.getVisibleActionCards()).toHaveLength(1);
    expect(store.getVisibleActionCards()[0].card_id).toBe("card-anc-101");

    // Duplicate replay from Hub is idempotent and sends updated since_cursor.
    const res2 = await client.syncNow();
    expect(res2.ok).toBe(true);
    if (res2.ok) {
      expect(res2.ackedCount).toBe(0);
      expect(res2.appliedCount).toBe(0);
      expect(res2.nextCursor).toBe("cursor-002");
    }
    expect(capturedEnvelopes[1].since_cursor).toBe("cursor-001");
    expect(capturedEnvelopes[1].events).toHaveLength(0);
    expect(store.getVisibleActionCards()).toHaveLength(1);
  });

  it("uploads SOS voice blob via HEAD 404 -> PUT before POST /api/v1/sync and clears queued blob on ack", async () => {
    const storage = new MemoryStorage();
    const store = new WatchStore({
      nodeId: "watch-family-01",
      initialMode: "PATIENT_FAMILY",
      storage,
      nowMs: () => 1_750_000_010_000,
    });
    const blobQueue = new MemoryWatchBlobQueue();
    const requests: string[] = [];

    const mockFetch: typeof fetch = async (input, init) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      requests.push(`${method} ${url}`);

      if (url.includes("/api/v1/blobs/")) {
        if (method === "HEAD") {
          return new Response(null, { status: 404 });
        }
        if (method === "PUT") {
          return new Response(
            JSON.stringify({
              blob_key: "sos-audio-01",
              content_type: "audio/webm",
              size_bytes: 5,
              sha256: "b".repeat(64),
            }),
            { status: 200 },
          );
        }
      }

      const sent = JSON.parse(String(init?.body)) as SyncEnvelope;
      expect(sent.sender_manifest.watch_mode).toBe("PATIENT_FAMILY");
      expect(sent.events).toHaveLength(1);
      expect(sent.events[0].event_type).toBe("VOICE_NOTE_RECORDED");
      expect(sent.events[0].enrichment_state).toBe("PENDING");
      expect(sent.events[0].payload.audio_blob_key).toBe("sos-audio-01");

      return new Response(
        JSON.stringify(
          makeHubReply({
            ack_event_ids: sent.events.map((e) => e.event_id),
            next_cursor: "cursor-sos-1",
          }),
        ),
        { status: 200 },
      );
    };

    const client = new WatchSyncClient(store, {
      hubUrl: "http://127.0.0.1:8000",
      fetchImpl: mockFetch,
      blobQueue,
    });

    const sosEvent = await client.enqueueVoiceSos({
      patientId: "pat-child-02",
      transcriptHint: "Child has high fever",
      language: "hi",
      audioBlob: new Uint8Array([1, 2, 3, 4, 5]),
      audioBlobKey: "sos-audio-01",
      mimeType: "audio/webm;codecs=opus",
      durationMs: 3200,
    });

    expect(sosEvent.event_type).toBe("VOICE_NOTE_RECORDED");
    expect(sosEvent.enrichment_state).toBe("PENDING");
    expect(blobQueue.has("sos-audio-01")).toBe(true);

    const result = await client.syncNow();
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.uploadedBlobKeys).toEqual(["sos-audio-01"]);
      expect(result.ackedCount).toBe(1);
    }

    expect(requests).toEqual([
      "HEAD http://127.0.0.1:8000/api/v1/blobs/sos-audio-01",
      "PUT http://127.0.0.1:8000/api/v1/blobs/sos-audio-01",
      "POST http://127.0.0.1:8000/api/v1/sync",
    ]);
    expect(blobQueue.has("sos-audio-01")).toBe(false);
    expect(store.getOutboxEvents()).toHaveLength(0);
  });

  it("makes zero blob HTTP calls for typed-only SOS without audio", async () => {
    const store = new WatchStore({
      nodeId: "watch-family-02",
      initialMode: "PATIENT_FAMILY",
      storage: new MemoryStorage(),
      nowMs: () => 1_750_000_020_000,
    });
    const requests: string[] = [];

    const mockFetch: typeof fetch = async (input, init) => {
      requests.push(`${init?.method ?? "GET"} ${String(input)}`);
      const sent = JSON.parse(String(init?.body)) as SyncEnvelope;
      return new Response(
        JSON.stringify(
          makeHubReply({ ack_event_ids: sent.events.map((e) => e.event_id) }),
        ),
        { status: 200 },
      );
    };

    const client = new WatchSyncClient(store, "http://127.0.0.1:8000", mockFetch);
    const evt = await client.enqueueVoiceSos({ transcriptHint: "Need ASHA help" });
    expect(evt.payload.audio_blob_key).toBeNull();

    const res = await client.syncNow();
    expect(res.ok).toBe(true);
    expect(requests).toEqual(["POST http://127.0.0.1:8000/api/v1/sync"]);
  });

  it("supports offline ackActionCard persistence and syncs ack when Hub returns", async () => {
    const storage = new MemoryStorage();
    const store = new WatchStore({
      nodeId: "watch-asha-02",
      initialMode: "CHW_COMPANION",
      storage,
      nowMs: () => 1_750_000_030_000,
    });

    const openCard: ActionCard = {
      card_id: "card-vacc-09",
      patient_id: "pat-09",
      title: "Penta-2 Due",
      summary: "Administer Pentavalent dose 2.",
      action_steps: ["Verify MCP card"],
      priority: "HIGH",
      severity: null,
      status: "OPEN",
      target_tier: "TIER_0_WATCH",
      watch_mode: "CHW_COMPANION",
      source_event_id: null,
      due_by: "2026-11-25",
      language: "en",
    };
    store.applyRemoteEvents([makeCardEvent(openCard, 1_750_000_029_000)]);

    let online = false;
    const sentAckPayloads: Array<Record<string, unknown>> = [];
    const mockFetch: typeof fetch = async (_input, init) => {
      if (!online) {
        throw new TypeError("NetworkError: Airplane Mode");
      }
      const sent = JSON.parse(String(init?.body)) as SyncEnvelope;
      for (const e of sent.events) {
        sentAckPayloads.push(e.payload);
      }
      return new Response(
        JSON.stringify(
          makeHubReply({
            ack_event_ids: sent.events.map((e) => e.event_id),
            next_cursor: "cursor-ack-1",
          }),
        ),
        { status: 200 },
      );
    };

    const client = new WatchSyncClient(store, "http://127.0.0.1:8000", mockFetch);

    // Acknowledge offline.
    const ackEvt = client.ackActionCard("card-vacc-09");
    expect(ackEvt.event_type).toBe("ACTION_CARD_ISSUED");
    expect(ackEvt.payload).toEqual({ card_id: "card-vacc-09", status: "ACKNOWLEDGED" });
    expect(store.getActionCard("card-vacc-09")?.status).toBe("ACKNOWLEDGED");
    expect(store.getOutboxEvents()).toHaveLength(1);

    // Sync fails soft while offline and preserves outbox.
    const offlineRes = await client.syncNow();
    expect(offlineRes.ok).toBe(false);
    if (!offlineRes.ok) {
      expect(offlineRes.status).toBe("offline");
    }
    expect(store.getOutboxEvents()).toHaveLength(1);

    // Reconstruct WatchStore from persisted storage (simulating watch restart).
    const reloadedStore = new WatchStore({ storage });
    expect(reloadedStore.getActionCard("card-vacc-09")?.status).toBe("ACKNOWLEDGED");
    expect(reloadedStore.getOutboxEvents()).toHaveLength(1);

    // Connectivity returns: ack syncs cleanly.
    online = true;
    const reloadedClient = new WatchSyncClient(reloadedStore, "http://127.0.0.1:8000", mockFetch);
    const onlineRes = await reloadedClient.syncNow();
    expect(onlineRes.ok).toBe(true);
    expect(sentAckPayloads).toEqual([{ card_id: "card-vacc-09", status: "ACKNOWLEDGED" }]);
    expect(reloadedStore.getOutboxEvents()).toHaveLength(0);
    expect(reloadedStore.getSyncCursor()).toBe("cursor-ack-1");
  });

  it("stays fail-soft on 5xx, blob failures, and malformed SyncEnvelope replies", async () => {
    const store = new WatchStore({
      nodeId: "watch-resilient-01",
      initialMode: "CHW_COMPANION",
      storage: new MemoryStorage(),
      nowMs: () => 1_750_000_040_000,
    });
    const blobQueue = new MemoryWatchBlobQueue();

    let mode: "blob_500" | "sync_503" | "malformed" | "bad_schema" = "blob_500";
    let syncPosted = false;

    const mockFetch: typeof fetch = async (input) => {
      const url = String(input);
      if (url.includes("/api/v1/blobs/")) {
        if (mode === "blob_500") {
          return new Response("Internal Server Error", { status: 500 });
        }
        return new Response(null, { status: 200 });
      }
      syncPosted = true;
      if (mode === "sync_503") {
        return new Response("Service Unavailable", { status: 503 });
      }
      if (mode === "malformed") {
        return new Response(JSON.stringify({ unexpected: true }), { status: 200 });
      }
      return new Response(
        JSON.stringify(makeHubReply({ schema_version: "2.0.0" })),
        { status: 200 },
      );
    };

    const client = new WatchSyncClient(store, {
      hubUrl: "http://127.0.0.1:8000",
      fetchImpl: mockFetch,
      blobQueue,
    });
    await client.enqueueVoiceSos({
      audioBlob: new Uint8Array([9, 8, 7]),
      audioBlobKey: "sos-retry-1",
    });

    // 1. Blob upload failure aborts before /api/v1/sync and keeps outbox intact.
    const r1 = await client.syncNow();
    expect(r1).toEqual({
      ok: false,
      status: "error",
      reason: "HEAD /api/v1/blobs/sos-retry-1 failed with HTTP 500.",
    });
    expect(syncPosted).toBe(false);
    expect(store.getOutboxEvents()).toHaveLength(1);

    // 2. Hub 503 fails soft and keeps outbox intact.
    mode = "sync_503";
    const r2 = await client.syncNow();
    expect(r2.ok).toBe(false);
    if (!r2.ok) expect(r2.status).toBe("error");
    expect(syncPosted).toBe(true);
    expect(store.getOutboxEvents()).toHaveLength(1);

    // 3. Malformed reply does not advance cursor or drop outbox.
    mode = "malformed";
    const r3 = await client.syncNow();
    expect(r3.ok).toBe(false);
    if (!r3.ok) expect(r3.status).toBe("error");
    expect(store.getSyncCursor()).toBeNull();
    expect(store.getOutboxEvents()).toHaveLength(1);

    // 4. Unsupported major schema_version is rejected fail-soft.
    mode = "bad_schema";
    const r4 = await client.syncNow();
    expect(r4.ok).toBe(false);
    if (!r4.ok) expect(r4.reason).toContain("schema_version");
    expect(store.getOutboxEvents()).toHaveLength(1);
  });
});

describe("resolveDefaultHubUrl (T3-05)", () => {
  it("resolves LAN origin, loopback origin, stale-loopback override, and non-HTTP fallbacks", () => {
    const lanLoc = {
      protocol: "http:",
      origin: "http://192.168.1.14:8000",
      hostname: "192.168.1.14",
    };

    expect(resolveDefaultHubUrl(lanLoc)).toBe("http://192.168.1.14:8000");
    expect(resolveDefaultHubUrl(lanLoc, "http://127.0.0.1:8000")).toBe("http://192.168.1.14:8000");
    expect(resolveDefaultHubUrl(lanLoc, "http://localhost:8000/")).toBe("http://192.168.1.14:8000");
    expect(resolveDefaultHubUrl(lanLoc, "http://192.168.43.1:8000/")).toBe("http://192.168.43.1:8000");

    const localLoc = {
      protocol: "http:",
      origin: "http://127.0.0.1:5174",
      hostname: "127.0.0.1",
    };
    expect(resolveDefaultHubUrl(localLoc)).toBe("http://127.0.0.1:5174");
    expect(resolveDefaultHubUrl(localLoc, "http://127.0.0.1:8000")).toBe("http://127.0.0.1:8000");

    expect(resolveDefaultHubUrl({ protocol: "file:", origin: "null" })).toBe(DEFAULT_HUB_URL);
    expect(resolveDefaultHubUrl(null)).toBe(DEFAULT_HUB_URL);
  });

  it("uses DEFAULT_HUB_URL inside native Android APK WebView unless savedHubUrl is set", () => {
    const apkLoc = {
      protocol: "http:",
      origin: "http://127.0.0.1:49842",
      hostname: "127.0.0.1",
    };
    const g = globalThis as Record<string, unknown>;
    g.AarogyaNativeBridge = {};
    try {
      expect(resolveDefaultHubUrl(apkLoc)).toBe(DEFAULT_HUB_URL);
      expect(resolveDefaultHubUrl(apkLoc, "http://192.168.1.14:8000/")).toBe(
        "http://192.168.1.14:8000",
      );
    } finally {
      delete g.AarogyaNativeBridge;
    }
  });

  it("normalizes bare IP:port, trims whitespace, strips trailing slashes, and validates Hub URLs", () => {
    expect(normalizeHubUrl("  192.168.36.182:8000/  ")).toBe("http://192.168.36.182:8000");
    expect(normalizeHubUrl("http://192.168.1.5:8000///")).toBe("http://192.168.1.5:8000");
    expect(normalizeHubUrl("https://hub.example.org/")).toBe("https://hub.example.org");
    expect(normalizeHubUrl("   ")).toBe(DEFAULT_HUB_URL);

    expect(isValidHubUrl("192.168.36.182:8000/")).toBe(true);
    expect(isValidHubUrl("https://hub.local:8443")).toBe(true);
    expect(isValidHubUrl("")).toBe(false);
    expect(isValidHubUrl("not a valid url")).toBe(false);
    expect(isValidHubUrl("ftp://192.168.1.5:21")).toBe(false);

    expect(
      resolveDefaultHubUrl(
        { protocol: "http:", origin: "http://192.168.36.182:8000", hostname: "192.168.36.182" },
        "  192.168.36.182:8000/ ",
      ),
    ).toBe("http://192.168.36.182:8000");
  });

  it("replaces cryptic Failed to fetch and AbortError messages with human-readable retry guidance", async () => {
    const store = new WatchStore({
      nodeId: "watch-err-01",
      initialMode: "CHW_COMPANION",
      storage: new MemoryStorage(),
      nowMs: () => 1_750_000_050_000,
    });

    const netFailClient = new WatchSyncClient(
      store,
      " 192.168.36.182:8000/ ",
      async () => {
        throw new TypeError("Failed to fetch");
      },
    );
    expect(netFailClient.getHubUrl()).toBe("http://192.168.36.182:8000");
    const offlineRes = await netFailClient.syncNow();
    expect(offlineRes.ok).toBe(false);
    if (!offlineRes.ok) {
      expect(offlineRes.status).toBe("offline");
      expect(offlineRes.reason).not.toBe("Failed to fetch");
      expect(offlineRes.reason).toContain("http://192.168.36.182:8000");
      expect(offlineRes.reason).toContain("Sync Now");
    }

    const abortClient = new WatchSyncClient(
      store,
      "http://192.168.36.182:8000",
      async () => {
        const err = new Error("The user aborted a request.");
        err.name = "AbortError";
        throw err;
      },
    );
    const timeoutRes = await abortClient.syncNow();
    expect(timeoutRes.ok).toBe(false);
    if (!timeoutRes.ok) {
      expect(timeoutRes.status).toBe("offline");
      expect(timeoutRes.reason).toContain("timed out");
      expect(timeoutRes.reason).toContain("Sync Now");
    }
  });
});
