import { afterEach, describe, expect, it, vi } from "vitest";
import { deriveVoiceStage, formatDurationMmSs, recordingUnavailableReason } from "../../src/ui/voice_logic";

afterEach(() => vi.unstubAllGlobals());

describe("formatDurationMmSs", () => {
  it("formats MM:SS and lets minutes grow past 59", () => {
    expect(formatDurationMmSs(0)).toBe("00:00");
    expect(formatDurationMmSs(999)).toBe("00:00");
    expect(formatDurationMmSs(65_000)).toBe("01:05");
    expect(formatDurationMmSs(3_600_000)).toBe("60:00");
    expect(formatDurationMmSs(3_725_000)).toBe("62:05");
  });
  it("clamps negative and non-finite input to 00:00", () => {
    expect(formatDurationMmSs(-5)).toBe("00:00");
    expect(formatDurationMmSs(Number.NaN)).toBe("00:00");
    expect(formatDurationMmSs(Number.POSITIVE_INFINITY)).toBe("00:00");
  });
});

describe("recordingUnavailableReason", () => {
  const rec = () => undefined;
  const apis = { MediaRecorder: rec, navigator: { mediaDevices: { getUserMedia: rec } } };

  it("insecure context wins even when the APIs exist", () => {
    expect(recordingUnavailableReason({ isSecureContext: false, ...apis })).toBe("insecure_context");
  });
  it("insecure context with nothing else is insecure_context", () => {
    expect(recordingUnavailableReason({ isSecureContext: false })).toBe("insecure_context");
  });
  it("secure without MediaRecorder is unsupported", () => {
    expect(recordingUnavailableReason({ isSecureContext: true, navigator: apis.navigator })).toBe("unsupported");
  });
  it("secure with MediaRecorder but no mediaDevices is unsupported", () => {
    expect(recordingUnavailableReason({ isSecureContext: true, MediaRecorder: rec, navigator: {} })).toBe("unsupported");
  });
  it("all present is null", () => {
    expect(recordingUnavailableReason({ isSecureContext: true, ...apis })).toBeNull();
  });
  it("undefined isSecureContext with all APIs is null", () => {
    expect(recordingUnavailableReason({ ...apis })).toBeNull();
  });
  it("defaults to globalThis", () => {
    vi.stubGlobal("isSecureContext", false);
    expect(recordingUnavailableReason()).toBe("insecure_context");
  });
});

describe("deriveVoiceStage", () => {
  const baseItem = { eventId: "ev-1", status: "PENDING" as const, blobKey: "vn-1" };

  it("returns completed (step 5/5) when ENRICHMENT_COMPLETED was received", () => {
    const info = deriveVoiceStage(
      { ...baseItem, status: "COMPLETED" },
      { outboxIds: new Set(["ev-1"]), isOnline: false, syncStatus: "offline", syncPhase: "idle" },
    );
    expect(info).toEqual({
      stage: "completed",
      step: 5,
      totalSteps: 5,
      hubSubStage: null,
      isHeldClip: false,
      hasAudio: true,
    });
  });

  it("returns hub_processing (step 4/5) with exact sub-stage when synced and active on Hub", () => {
    for (const sub of ["transcribing_audio", "structuring_note", "scoring_risk"] as const) {
      const info = deriveVoiceStage(baseItem, {
        outboxIds: new Set(),
        isOnline: true,
        syncStatus: "idle",
        syncPhase: "idle",
        hubStatus: { pending_enrichments: 1, running: true, active_stages: { "ev-1": sub } },
      });
      expect(info.stage).toBe("hub_processing");
      expect(info.step).toBe(4);
      expect(info.hubSubStage).toBe(sub);
    }
  });

  it("returns hub_processing with null hubSubStage for unknown non-empty Hub sub-stage", () => {
    const info = deriveVoiceStage(baseItem, {
      outboxIds: new Set(),
      isOnline: true,
      syncStatus: "idle",
      syncPhase: "idle",
      hubStatus: { active_stages: { "ev-1": "custom_stage" } },
    });
    expect(info.stage).toBe("hub_processing");
    expect(info.step).toBe(4);
    expect(info.hubSubStage).toBeNull();
  });

  it("returns queued_on_hub (step 3/5) when synced (not in outbox) and not actively processing", () => {
    const info = deriveVoiceStage(baseItem, {
      outboxIds: new Set(),
      isOnline: true,
      syncStatus: "idle",
      syncPhase: "idle",
      hubStatus: { pending_enrichments: 1, running: false, active_stages: {} },
    });
    expect(info.stage).toBe("queued_on_hub");
    expect(info.step).toBe(3);
  });

  it("returns uploading_audio (step 2/5) when in outbox and actively uploading or syncing", () => {
    const uploading = deriveVoiceStage(baseItem, {
      outboxIds: new Set(["ev-1"]),
      isOnline: true,
      syncStatus: "syncing",
      syncPhase: "uploading_blobs",
      uploadingBlobKeys: new Set(["vn-1"]),
    });
    expect(uploading.stage).toBe("uploading_audio");
    expect(uploading.step).toBe(2);

    const syncingTyped = deriveVoiceStage(
      { eventId: "ev-2", status: "PENDING", blobKey: null },
      {
        outboxIds: new Set(["ev-2"]),
        isOnline: true,
        syncStatus: "syncing",
        syncPhase: "syncing_events",
      },
    );
    expect(syncingTyped.stage).toBe("uploading_audio");
    expect(syncingTyped.step).toBe(2);
    expect(syncingTyped.hasAudio).toBe(false);
  });

  it("returns waiting_connection (step 1/5) when in outbox and offline, errored, or held for retry", () => {
    const offline = deriveVoiceStage(baseItem, {
      outboxIds: new Set(["ev-1"]),
      isOnline: false,
      syncStatus: "offline",
      syncPhase: "idle",
    });
    expect(offline.stage).toBe("waiting_connection");
    expect(offline.step).toBe(1);
    expect(offline.isHeldClip).toBe(false);

    const held = deriveVoiceStage(baseItem, {
      outboxIds: new Set(["ev-1"]),
      isOnline: true,
      syncStatus: "error",
      syncPhase: "idle",
      heldBlobKeys: new Set(["vn-1"]),
    });
    expect(held.stage).toBe("waiting_connection");
    expect(held.step).toBe(1);
    expect(held.isHeldClip).toBe(true);
  });
});
