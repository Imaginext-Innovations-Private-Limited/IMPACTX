import { describe, expect, it } from "vitest";
import {
  CONTRACT_SCHEMA_VERSION,
  type CrdtEvent,
  type SyncEnvelope,
  type VaccinationDueItem,
} from "../../../../packages/contracts/ts/index";
import { MemoryStorage } from "../../src/core/index";
import { WatchSyncClient, type BrowserLocationLike } from "../../src/sync/index";
import { DEFAULT_HUB_URL_STORAGE_KEY, WatchUiController } from "../../src/ui/state";
import { WatchKernel } from "../../src/watch_kernel";

function makeController(options: {
  storage?: MemoryStorage;
  fetchImpl?: typeof fetch;
  vaccinations?: VaccinationDueItem[];
  location?: BrowserLocationLike | null;
} = {}) {
  const storage = options.storage ?? new MemoryStorage();
  const kernel = new WatchKernel("watch-test-01", "CHW_COMPANION", { storage });
  const syncClient = new WatchSyncClient(kernel.getStore(), {
    hubUrl: "http://127.0.0.1:8000",
    fetchImpl: options.fetchImpl,
  });
  const controller = new WatchUiController({
    kernel,
    syncClient,
    storage,
    initialVaccinations: options.vaccinations,
    location: options.location,
  });
  return { storage, kernel, syncClient, controller };
}

describe("WatchUiController dual-mode state transitions", () => {
  it("toggles CHW_COMPANION <-> PATIENT_FAMILY, updates active tab, and persists across reload", () => {
    const storage = new MemoryStorage();
    const { controller } = makeController({ storage });

    expect(controller.getMode()).toBe("CHW_COMPANION");
    expect(controller.getTab()).toBe("danger");

    controller.setTab("cards");
    expect(controller.getTab()).toBe("cards");

    // Switching to PATIENT_FAMILY resets tab to reminders and persists mode in WatchStore
    expect(controller.toggleMode()).toBe("PATIENT_FAMILY");
    expect(controller.getTab()).toBe("reminders");

    // Invalid CHW tab in PATIENT_FAMILY snaps to reminders
    expect(controller.setTab("danger")).toBe("reminders");
    expect(controller.setTab("sos")).toBe("sos");

    controller.setHubUrl("http://192.168.43.1:8000/");

    // Simulate offline reload from the same storage
    const reloaded = makeController({ storage });
    expect(reloaded.controller.getMode()).toBe("PATIENT_FAMILY");
    expect(reloaded.controller.getTab()).toBe("reminders");
    expect(reloaded.controller.getHubUrl()).toBe("http://192.168.43.1:8000");
  });

  it("1-tap danger screen emits RED_EMERGENCY + CRITICAL ActionCard offline, and 0 signs emits GREEN_HOME", () => {
    const { controller } = makeController();
    controller.setLanguage("en");
    controller.setPatientIdInput("pat-child-01");

    const red = controller.triggerDangerScreen(["convulsions"]);
    expect(red.severity).toBe("RED_EMERGENCY");
    expect(red.assessment.referral_required).toBe(true);
    expect(red.assessment.confidence).toBe(1.0);
    expect(red.assessment.execution_target).toBe("LOCAL_DETERMINISTIC");
    expect(red.actionCard).not.toBeNull();
    expect(red.actionCard?.priority).toBe("CRITICAL");

    // Both TRIAGE_COMPLETED and ACTION_CARD_ISSUED are queued offline
    expect(controller.getOutboxCount()).toBe(2);
    expect(controller.getOpenActionCardCount()).toBe(1);

    // 1-tap acknowledge marks the card ACKNOWLEDGED and queues the status update
    const cardId = red.actionCard!.card_id;
    controller.acknowledgeCard(cardId);
    expect(controller.getOpenActionCardCount()).toBe(0);
    expect(controller.getVisibleActionCards()[0].status).toBe("ACKNOWLEDGED");
    expect(controller.getOutboxCount()).toBe(3);

    controller.resetTriage();
    expect(controller.getLastTriage()).toBeNull();

    const green = controller.triggerDangerScreen([]);
    expect(green.severity).toBe("GREEN_HOME");
    expect(green.assessment.referral_required).toBe(false);
  });

  it("projects PATIENT_FAMILY overdue vaccination and medication reminders in English and Shuddh Tatsama Hindi", () => {
    const overdueVaccine: VaccinationDueItem = {
      vaccine_code: "PENTA_1",
      vaccine_name: "Pentavalent-1",
      dose_label: "6 weeks",
      due_date: "2026-11-10",
      status: "OVERDUE",
      administered_date: null,
      days_delta: -13,
      reminder_text: "Pentavalent-1 overdue by 13 days.",
      schedule_group: "INFANT",
    };

    const { kernel, controller } = makeController({ vaccinations: [overdueVaccine] });
    controller.setMode("PATIENT_FAMILY");

    // Inject a PATIENT_FAMILY medication ActionCard
    const hlc = kernel.tickHlc();
    const medEvent: CrdtEvent = {
      event_id: "evt-med-card-1",
      hlc,
      origin_node_id: "hub-01",
      patient_id: "pat-fam-01",
      event_type: "ACTION_CARD_ISSUED",
      payload: {
        card_id: "card-med-1",
        patient_id: "pat-fam-01",
        title: "Daily IFA Tablet",
        summary: "Take 1 iron folic acid tablet after meal.",
        action_steps: ["Take tablet with water"],
        priority: "HIGH",
        severity: null,
        status: "OPEN",
        target_tier: "TIER_0_WATCH",
        watch_mode: "PATIENT_FAMILY",
        source_event_id: "evt-med-card-1",
        due_by: "2026-11-24",
        language: "en",
      },
      enrichment_state: "NOT_NEEDED",
      ref_event_id: null,
    };
    kernel.getStore().applyRemoteEvents([medEvent]);

    controller.setLanguage("en");
    const enReminders = controller.getReminders();
    expect(enReminders.length).toBe(2);
    expect(enReminders.some((r) => r.category === "VACCINATION")).toBe(true);
    expect(enReminders.some((r) => r.category === "MEDICATION")).toBe(true);

    controller.toggleLanguage();
    expect(controller.getLanguage()).toBe("hi");
    const hiReminders = controller.getReminders();
    const hiVac = hiReminders.find((r) => r.category === "VACCINATION");
    expect(hiVac?.title).toContain("टीकाकरण");
    expect(hiVac?.title.normalize("NFD")).not.toContain("\u093c");
    controller.setLanguage("en");
  });

  it("queues VOICE_NOTE_RECORDED (PENDING) for SOS and handles offline fail-soft then online sync", async () => {
    let online = false;
    const seenMethods: string[] = [];

    const mockFetch: typeof fetch = async (input, init) => {
      const url = typeof input === "string" ? input : input instanceof URL ? input.toString() : input.url;
      const method = init?.method ?? "GET";
      seenMethods.push(`${method} ${new URL(url).pathname}`);

      if (!online) {
        throw new TypeError("Network unreachable");
      }

      if (method === "HEAD" && url.includes("/api/v1/blobs/")) {
        return new Response(null, { status: 404 });
      }
      if (method === "PUT" && url.includes("/api/v1/blobs/")) {
        return new Response(JSON.stringify({ ok: true }), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        });
      }
      if (method === "POST" && url.endsWith("/api/v1/sync")) {
        const reqBody = JSON.parse(String(init?.body)) as SyncEnvelope;
        const reply: SyncEnvelope = {
          envelope_id: "hub-reply-1",
          sender_manifest: {
            node_id: "phc-hub-01",
            tier: "TIER_2_HUB",
            ram_mb: 16384,
            cpu_cores: 8,
            battery_pct: 100,
            has_npu: true,
            installed_models: ["whisper-small-int8"],
            watch_mode: null,
          },
          sender_hlc: { wall_ms: Date.now(), logical: 1, node_id: "phc-hub-01" },
          since_cursor: reqBody.since_cursor,
          next_cursor: "cursor-1",
          events: [],
          ack_event_ids: reqBody.events.map((e) => e.event_id),
          schema_version: CONTRACT_SCHEMA_VERSION,
        };
        return new Response(JSON.stringify(reply), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      }
      return new Response("Not Found", { status: 404 });
    };

    const { controller } = makeController({ fetchImpl: mockFetch });
    controller.setMode("PATIENT_FAMILY");
    controller.setTab("sos");

    const sosEvent = await controller.submitSos({
      transcriptHint: "High fever and breathing difficulty",
      audioBlob: new Uint8Array([1, 2, 3, 4]),
      mimeType: "audio/webm",
      durationMs: 2500,
    });
    expect(sosEvent.event_type).toBe("VOICE_NOTE_RECORDED");
    expect(sosEvent.enrichment_state).toBe("PENDING");
    expect(controller.getOutboxCount()).toBe(1);

    // Offline sync fails soft and preserves outbox
    const offlineRes = await controller.syncNow();
    expect(offlineRes.ok).toBe(false);
    expect(controller.getOutboxCount()).toBe(1);

    // Reconnect and sync -> uploads blob (HEAD -> PUT) + POST /api/v1/sync
    online = true;
    const onlineRes = await controller.syncNow();
    expect(onlineRes.ok).toBe(true);
    expect(controller.getOutboxCount()).toBe(0);
    expect(seenMethods.some((m) => m.startsWith("HEAD /api/v1/blobs/"))).toBe(true);
    expect(seenMethods.some((m) => m.startsWith("PUT /api/v1/blobs/"))).toBe(true);
    expect(seenMethods.some((m) => m === "POST /api/v1/sync")).toBe(true);
  });

  it("blocks empty Text SOS, guards danger signs with 2-tap confirm, and drops stale loopback URLs (T3-05)", async () => {
    const storage = new MemoryStorage();
    storage.setItem(DEFAULT_HUB_URL_STORAGE_KEY, "http://127.0.0.1:8000");

    const { controller } = makeController({
      storage,
      location: {
        protocol: "http:",
        origin: "http://192.168.1.14:8000",
        hostname: "192.168.1.14",
      },
    });
    expect(controller.getHubUrl()).toBe("http://192.168.1.14:8000");

    // 2-tap danger-sign confirm guard
    controller.armDangerSign("convulsions");
    expect(controller.getPendingConfirmFlag()).toBe("convulsions");
    expect(controller.getOutboxCount()).toBe(0);

    controller.cancelArmedDangerSign();
    expect(controller.getPendingConfirmFlag()).toBeNull();
    expect(controller.getOutboxCount()).toBe(0);

    controller.armDangerSign("convulsions");
    const confirmed = controller.confirmArmedDangerSign("pat-guard-1");
    expect(confirmed?.severity).toBe("RED_EMERGENCY");
    expect(controller.getPendingConfirmFlag()).toBeNull();
    expect(controller.getOutboxCount()).toBe(2);

    // Non-empty Text SOS guard
    controller.setMode("PATIENT_FAMILY");
    controller.setTab("sos");
    const blocked = await controller.submitTextSos("   ");
    expect(blocked).toBeNull();
    expect(controller.getSosTextError()).toBe(true);
    expect(controller.getOutboxCount()).toBe(2);

    controller.setSosTextDraft("Need urgent help");
    expect(controller.getSosTextError()).toBe(false);
    const queued = await controller.submitTextSos();
    expect(queued?.event_type).toBe("VOICE_NOTE_RECORDED");
    expect(controller.getSosTextError()).toBe(false);
    expect(controller.getOutboxCount()).toBe(3);
  });

  it("supports custom unlisted danger signs and rejects empty custom symptom input", () => {
    const { controller } = makeController();
    controller.setLanguage("en");

    expect(controller.submitCustomDangerSign("   ")).toBeNull();
    expect(controller.getCustomDangerError()).toBe(true);
    expect(controller.getOutboxCount()).toBe(0);

    controller.setCustomDangerDraft("high fever, stiff neck");
    expect(controller.getCustomDangerError()).toBe(false);

    const res = controller.submitCustomDangerSign(undefined, "pat-custom-1");
    expect(res).not.toBeNull();
    expect(res?.severity).toBe("RED_EMERGENCY");
    expect(res?.assessment.referral_required).toBe(true);
    expect(controller.getCustomDangerDraft()).toBe("");
    expect(controller.getCustomDangerError()).toBe(false);
    expect(controller.getOutboxCount()).toBe(2);
  });

  it("normalizes bare IP:port Hub URLs, rejects invalid URLs, and prevents double-tap races on Sync/SOS/Ack", async () => {
    let syncCalls = 0;
    let resolveSyncFetch!: (res: Response) => void;
    const mockFetch: typeof fetch = (_input, init) => {
      syncCalls += 1;
      const reqBody = JSON.parse(String(init?.body)) as SyncEnvelope;
      return new Promise<Response>((resolve) => {
        resolveSyncFetch = resolve;
        // Keep reference for test resolution; reply built below.
        void reqBody;
      });
    };

    const { controller } = makeController({ fetchImpl: mockFetch });
    controller.setLanguage("en");

    // 1. Bare IP:port normalization & invalid URL rejection
    expect(controller.setHubUrl("  192.168.36.182:8000/  ")).toBe("http://192.168.36.182:8000");
    expect(controller.getHubUrlError()).toBeNull();

    expect(controller.setHubUrl("not a valid url")).toBe("http://192.168.36.182:8000");
    expect(controller.getHubUrlError()).toContain("Invalid Hub address");
    const blockedSync = await controller.syncNow();
    expect(blockedSync.ok).toBe(false);
    expect(syncCalls).toBe(0);

    // Fix URL back to valid
    expect(controller.setHubUrl("192.168.36.182:8000")).toBe("http://192.168.36.182:8000");
    expect(controller.getHubUrlError()).toBeNull();

    // 2. ActionCard double-tap ack guard
    const red = controller.triggerDangerScreen(["convulsions"]);
    const cardId = red.actionCard!.card_id;
    expect(controller.acknowledgeCard(cardId)).not.toBeNull();
    expect(controller.acknowledgeCard(cardId)).toBeNull();
    expect(controller.getOutboxCount()).toBe(3);

    // 3. SOS double-tap guard
    controller.setMode("PATIENT_FAMILY");
    controller.setTab("sos");
    const sosP1 = controller.submitSos({ transcriptHint: "Need help" });
    const sosP2 = controller.submitSos({ transcriptHint: "Need help" });
    const [e1, e2] = await Promise.all([sosP1, sosP2]);
    expect(e1.event_id).toBe(e2.event_id);
    expect(controller.getOutboxCount()).toBe(4);

    // 4. Sync double-tap coalescing
    const p1 = controller.syncNow();
    const p2 = controller.syncNow();
    expect(controller.getIsSyncing()).toBe(true);
    await Promise.resolve();
    await Promise.resolve();
    resolveSyncFetch(
      new Response(
        JSON.stringify({
          envelope_id: "hub-coalesce-1",
          sender_manifest: {
            node_id: "phc-hub-01",
            tier: "TIER_2_HUB",
            ram_mb: 16384,
            cpu_cores: 8,
            battery_pct: 100,
            has_npu: true,
            installed_models: [],
            watch_mode: null,
          },
          sender_hlc: { wall_ms: Date.now(), logical: 1, node_id: "phc-hub-01" },
          since_cursor: null,
          next_cursor: "cursor-coalesce",
          events: [],
          ack_event_ids: [],
          schema_version: CONTRACT_SCHEMA_VERSION,
        } satisfies SyncEnvelope),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    const [r1, r2] = await Promise.all([p1, p2]);
    expect(r1).toBe(r2);
    expect(syncCalls).toBe(1);
    expect(controller.getIsSyncing()).toBe(false);
  });
});
