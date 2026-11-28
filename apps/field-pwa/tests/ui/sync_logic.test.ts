import { describe, expect, it } from "vitest";
import { cardPatientLabel, classifySyncFailure, parseSyncFailureDetail } from "../../src/ui/sync_logic";

describe("cardPatientLabel", () => {
  const patients = new Map([["p1", { full_name: "Asha Devi", village_id: "V1" }]]);
  it("returns null for a null patient id", () => {
    expect(cardPatientLabel(null, patients)).toBeNull();
  });
  it("resolves a known patient to name and village", () => {
    expect(cardPatientLabel("p1", patients)).toEqual({ name: "Asha Devi", village: "V1" });
  });
  it("falls back to the raw id for an unknown patient", () => {
    expect(cardPatientLabel("p2", patients)).toEqual({ name: "p2", village: null });
  });
  it("falls back to the raw id with an empty map", () => {
    expect(cardPatientLabel("p1", new Map())).toEqual({ name: "p1", village: null });
  });
});

describe("classifySyncFailure & parseSyncFailureDetail", () => {
  it("distinguishes device offline, unreachable hub, and HTTP 4xx/5xx", () => {
    expect(classifySyncFailure("offline", "hub unreachable: TypeError: Failed to fetch", false)).toBe("offline:device");
    expect(classifySyncFailure("offline", "hub unreachable: TypeError: Failed to fetch", true)).toBe("offline:unreachable");
    expect(classifySyncFailure("error", "hub sync failed: HTTP 502", true)).toBe("http:502");
    expect(classifySyncFailure("error", "hub sync failed: HTTP 404", true)).toBe("http:404");
    expect(classifySyncFailure("error", "hub reply is not a SyncEnvelope", true)).toBe("hub reply is not a SyncEnvelope");
  });

  it("parses stored lastSync failure tokens", () => {
    expect(parseSyncFailureDetail("offline:device")).toEqual({ kind: "device_offline" });
    expect(parseSyncFailureDetail("offline")).toEqual({ kind: "device_offline" });
    expect(parseSyncFailureDetail("offline:unreachable")).toEqual({ kind: "unreachable" });
    expect(parseSyncFailureDetail("http:500")).toEqual({ kind: "http", code: "500" });
    expect(parseSyncFailureDetail("custom error")).toEqual({ kind: "other", detail: "custom error" });
  });
});
