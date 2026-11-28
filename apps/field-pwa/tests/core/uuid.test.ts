import "fake-indexeddb/auto";
import { afterEach, describe, expect, it, vi } from "vitest";
import { uuid } from "../../src/core/uuid";
import { evaluateTriage, triageToActionCard } from "../../src/clinical";
import { createLocalEvent } from "../../src/sync/envelope";
import { freshStore } from "../sync/helpers";

const V4 = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const realCrypto = globalThis.crypto;
const insecure = () =>
  vi.stubGlobal("crypto", { getRandomValues: realCrypto.getRandomValues.bind(realCrypto) });

afterEach(() => vi.unstubAllGlobals());

describe("uuid", () => {
  it("native path is used when randomUUID is a function", () => {
    const randomUUID = vi.fn(() => "native-id");
    vi.stubGlobal("crypto", { randomUUID, getRandomValues: realCrypto.getRandomValues.bind(realCrypto) });
    expect(uuid()).toBe("native-id");
    expect(randomUUID).toHaveBeenCalledOnce();
  });

  it("native output matches v4 format", () => {
    expect(uuid()).toMatch(V4);
  });

  it("fallback is used when randomUUID is undefined and yields v4 format", () => {
    const grv = vi.fn(realCrypto.getRandomValues.bind(realCrypto));
    vi.stubGlobal("crypto", { getRandomValues: grv });
    const id = uuid();
    expect(grv).toHaveBeenCalled();
    expect(id).toMatch(V4);
    expect(id[14]).toBe("4");
    expect("89ab").toContain(id[19]);
  });

  it("fallback sets version/variant bits even for all-0xff and all-0x00 bytes", () => {
    for (const fill of [0x00, 0xff]) {
      vi.stubGlobal("crypto", { getRandomValues: (a: Uint8Array) => a.fill(fill) });
      const id = uuid();
      expect(id).toMatch(V4);
    }
    vi.stubGlobal("crypto", { getRandomValues: (a: Uint8Array) => a.fill(0) });
    expect(uuid()).toBe("00000000-0000-4000-8000-000000000000");
  });

  it("1000 fallback ids are unique", () => {
    insecure();
    expect(new Set(Array.from({ length: 1000 }, uuid)).size).toBe(1000);
  });

  it("throws a clear error when no crypto is available", () => {
    vi.stubGlobal("crypto", undefined);
    expect(() => uuid()).toThrow(/no Web Crypto/);
    vi.stubGlobal("crypto", {});
    expect(() => uuid()).toThrow(/no Web Crypto/);
  });
});

describe("insecure-context flows (crypto.randomUUID removed)", () => {
  it("evaluateTriage produces ids", () => {
    insecure();
    const a = evaluateTriage({ danger_signs: ["convulsions"] } as never);
    expect(a.assessment_id).toMatch(V4);
    expect(triageToActionCard(a).card_id).toMatch(V4);
  });

  it("createLocalEvent produces an event id", async () => {
    insecure();
    const store = await freshStore();
    const ev = await createLocalEvent(store, { event_type: "PATIENT_REGISTERED", payload: {} });
    expect(ev.event_id).toMatch(V4);
  });
});
