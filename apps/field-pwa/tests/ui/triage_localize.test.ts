import { describe, expect, it, vi } from "vitest";
import { HI_TRIAGE_ACTIONS, HI_TRIAGE_RATIONALE } from "../../src/i18n/hi";
import { KN_TRIAGE_ACTIONS, KN_TRIAGE_RATIONALE } from "../../src/i18n/kn";
import { TA_TRIAGE_ACTIONS, TA_TRIAGE_RATIONALE } from "../../src/i18n/ta";
import { IMNCI_PEDIATRIC_RULES, MATERNAL_ANC_RULES } from "../../src/clinical";
import { localizeTriageAction, localizeTriageRationale, vibrateIfEmergency } from "../../src/ui/screens/triage_result";
import fixturesRaw from "../clinical/fixtures/triage_vectors.json";

interface Expected { immediate_actions: string[]; matched_rules: string[]; rationale: string }
const fixtures = fixturesRaw as { vectors: { name: string; expected?: Expected }[]; watch_rapid: { name: string; expected: Expected }[] };
const expectedList: { name: string; e: Expected }[] = [
  ...fixtures.vectors.filter((v) => v.expected).map((v) => ({ name: v.name, e: v.expected as Expected })),
  ...fixtures.watch_rapid.map((v) => ({ name: v.name, e: v.expected })),
];

// Copied from i18n.test.ts (not imported).
const DENY = [
  "अस्पताल", "दवा", "दवाई", "दवाख़ाना", "दवाखाना", "बुख़ार", "बुखार", "तकलीफ़", "तकलीफ", "ख़तरा", "खतरा",
  "मरीज़", "मरीज", "इलाज", "सलाह", "ज़रूरी", "जरूरी", "मदद", "ख़ून", "खून", "कमज़ोरी", "कमजोरी",
  "डॉक्टर", "डाक्टर", "एम्बुलेंस", "एंबुलेंस", "फ़ोन", "फोन", "तारीख", "तारीख़", "वापस", "शुरू", "शुरुआत",
  "बंद", "रद्द", "ज़्यादा", "ज्यादा", "साल", "सिर्फ", "ख़त्म", "खत्म", "इस्तेमाल", "कोशिश", "ज़िला", "जिला",
  "ख़बर", "खबर", "वक़्त", "वक्त", "हफ़्ता", "हफ्ता", "बीमारी", "सेहत", "सुबह", "शाम", "जल्दी", "ज़रा",
  "मोबाइल", "ऑफलाइन", "ऑफ़लाइन", "ऑनलाइन", "बटन", "सिंक", "रिकॉर्ड", "रिकार्ड", "कार्ड", "नेटवर्क", "हब",
  "सर्वर", "ऐप", "एप्प", "ट्राइएज", "ट्रायज", "मेनू", "सेव", "चेकलिस्ट", "वैक्सीन", "टीका-कार्ड", "ऑक्सीजन",
  "हीमोग्लोबिन", "टेम्परेचर", "वॉइस", "नोट", "रजिस्टर", "रजिस्ट्रेशन", "ट्रिपल",
];
const NUKTA = ["ख़", "ग़", "ज़", "फ़", "ड़", "ढ़", "क़"];

// Walk a rule table collecting action strings and rule ids.
function collect(node: unknown, actions: Set<string>, ids: Set<string>): void {
  if (Array.isArray(node)) { node.forEach((n) => collect(n, actions, ids)); return; }
  if (node === null || typeof node !== "object") return;
  const o = node as Record<string, unknown>;
  if (typeof o.id === "string" && typeof o.rationale === "string") ids.add(o.id);
  for (const [k, v] of Object.entries(o)) {
    if (k.endsWith("actions") && Array.isArray(v)) v.forEach((a) => typeof a === "string" && actions.add(a));
    else collect(v, actions, ids);
  }
}

describe("Hindi triage table coverage", () => {
  const ruleActions = new Set<string>();
  const ruleIds = new Set<string>();
  collect(IMNCI_PEDIATRIC_RULES, ruleActions, ruleIds);
  collect(MATERNAL_ANC_RULES, ruleActions, ruleIds);

  it("walks real rule tables", () => {
    expect(ruleActions.size).toBeGreaterThan(20);
    expect(ruleIds.size).toBeGreaterThan(20);
    expect(expectedList.length).toBeGreaterThan(50);
  });
  it("covers every fixture action and rule id", () => {
    const missA = new Set<string>();
    const missR = new Set<string>();
    for (const { e } of expectedList) {
      e.immediate_actions.forEach((a) => { if (!(a in HI_TRIAGE_ACTIONS)) missA.add(a); });
      e.matched_rules.forEach((r) => { if (!(r in HI_TRIAGE_RATIONALE)) missR.add(r); });
    }
    expect([...missA], `missing actions: ${JSON.stringify([...missA])}`).toEqual([]);
    expect([...missR], `missing rule ids: ${JSON.stringify([...missR])}`).toEqual([]);
  });
  it("covers every rule-table action and rule id", () => {
    const missA = [...ruleActions].filter((a) => !(a in HI_TRIAGE_ACTIONS));
    const missR = [...ruleIds].filter((r) => !(r in HI_TRIAGE_RATIONALE));
    expect(missA, `missing actions: ${JSON.stringify(missA)}`).toEqual([]);
    expect(missR, `missing rule ids: ${JSON.stringify(missR)}`).toEqual([]);
  });
});

describe("Hindi localization of fixtures", () => {
  it("localizes every fixture rationale and action", () => {
    for (const { name, e } of expectedList) {
      if (e.matched_rules.length === 0) continue;
      const hi = localizeTriageRationale(e.rationale, e.matched_rules, "hi");
      expect(hi.length, name).toBeGreaterThan(0);
      expect(hi, name).not.toBe(e.rationale);
      for (const a of e.immediate_actions) expect(localizeTriageAction(a, "hi"), name).toBe(HI_TRIAGE_ACTIONS[a]);
    }
  });
});

describe("Kannada triage table coverage and localization", () => {
  const ruleActions = new Set<string>();
  const ruleIds = new Set<string>();
  collect(IMNCI_PEDIATRIC_RULES, ruleActions, ruleIds);
  collect(MATERNAL_ANC_RULES, ruleActions, ruleIds);

  it("matches HI_TRIAGE_ACTIONS and HI_TRIAGE_RATIONALE keys 100%", () => {
    expect(Object.keys(KN_TRIAGE_ACTIONS).sort()).toEqual(Object.keys(HI_TRIAGE_ACTIONS).sort());
    expect(Object.keys(KN_TRIAGE_RATIONALE).sort()).toEqual(Object.keys(HI_TRIAGE_RATIONALE).sort());
  });

  it("covers every fixture and rule-table action and rule id in Kannada", () => {
    const missA = [...ruleActions].filter((a) => !(a in KN_TRIAGE_ACTIONS));
    const missR = [...ruleIds].filter((r) => !(r in KN_TRIAGE_RATIONALE));
    expect(missA, `missing kn actions: ${JSON.stringify(missA)}`).toEqual([]);
    expect(missR, `missing kn rule ids: ${JSON.stringify(missR)}`).toEqual([]);
    for (const { name, e } of expectedList) {
      if (e.matched_rules.length === 0) continue;
      const kn = localizeTriageRationale(e.rationale, e.matched_rules, "kn");
      expect(kn.length, name).toBeGreaterThan(0);
      expect(kn, name).not.toBe(e.rationale);
      expect(kn, name).toMatch(/[\u0C80-\u0CFF]/);
      for (const a of e.immediate_actions) {
        const act = localizeTriageAction(a, "kn");
        expect(act, name).toBe(KN_TRIAGE_ACTIONS[a]);
        expect(act, name).toMatch(/[\u0C80-\u0CFF]/);
      }
    }
  });
});

describe("Tamil triage table coverage and localization", () => {
  const ruleActions = new Set<string>();
  const ruleIds = new Set<string>();
  collect(IMNCI_PEDIATRIC_RULES, ruleActions, ruleIds);
  collect(MATERNAL_ANC_RULES, ruleActions, ruleIds);

  it("matches HI_TRIAGE_ACTIONS and HI_TRIAGE_RATIONALE keys 100%", () => {
    expect(Object.keys(TA_TRIAGE_ACTIONS).sort()).toEqual(Object.keys(HI_TRIAGE_ACTIONS).sort());
    expect(Object.keys(TA_TRIAGE_RATIONALE).sort()).toEqual(Object.keys(HI_TRIAGE_RATIONALE).sort());
  });

  it("covers every fixture and rule-table action and rule id in Tamil", () => {
    const missA = [...ruleActions].filter((a) => !(a in TA_TRIAGE_ACTIONS));
    const missR = [...ruleIds].filter((r) => !(r in TA_TRIAGE_RATIONALE));
    expect(missA, `missing ta actions: ${JSON.stringify(missA)}`).toEqual([]);
    expect(missR, `missing ta rule ids: ${JSON.stringify(missR)}`).toEqual([]);
    for (const { name, e } of expectedList) {
      if (e.matched_rules.length === 0) continue;
      const taText = localizeTriageRationale(e.rationale, e.matched_rules, "ta");
      expect(taText.length, name).toBeGreaterThan(0);
      expect(taText, name).not.toBe(e.rationale);
      expect(taText, name).toMatch(/[\u0B80-\u0BFF]/);
      for (const a of e.immediate_actions) {
        const act = localizeTriageAction(a, "ta");
        expect(act, name).toBe(TA_TRIAGE_ACTIONS[a]);
        expect(act, name).toMatch(/[\u0B80-\u0BFF]/);
      }
    }
  });
});

describe("table purity", () => {
  const entries = [...Object.entries(HI_TRIAGE_ACTIONS), ...Object.entries(HI_TRIAGE_RATIONALE)];
  it("has entries", () => expect(entries.length).toBeGreaterThan(40));
  it("values are non-empty", () => {
    for (const [k, v] of entries) expect(v.trim().length, k).toBeGreaterThan(0);
  });
  it("has no nukta letters in any Unicode form", () => {
    for (const [k, v] of entries) {
      expect(v.normalize("NFD"), k).not.toContain("़");
      for (const n of NUKTA) {
        expect(v, `${k} has ${n}`).not.toContain(n);
        expect(v.normalize("NFC"), `${k} has ${n}`).not.toContain(n.normalize("NFC"));
      }
    }
  });
  it("has no deny-listed words", () => {
    for (const [k, v] of entries) {
      const words = v.split(/[^ऀ-ॿ]+/).filter(Boolean);
      for (const bad of DENY) expect(words, `${k} contains ${bad}`).not.toContain(bad);
    }
  });
  it("has no Latin letters once °C is removed", () => {
    for (const [k, v] of entries) expect(v.replace(/°C/g, ""), k).not.toMatch(/[A-Za-z]/);
  });
});

describe("localization edge cases", () => {
  const knownAction = Object.keys(HI_TRIAGE_ACTIONS)[0] as string;
  const [r1, r2] = Object.keys(HI_TRIAGE_RATIONALE) as [string, string];
  it("English mode returns input unchanged", () => {
    expect(localizeTriageAction(knownAction, "en")).toBe(knownAction);
    expect(localizeTriageRationale("Some English", [r1], "en")).toBe("Some English");
  });
  it("unknown action in hi is unchanged", () => {
    expect(localizeTriageAction("Totally unknown action", "hi")).toBe("Totally unknown action");
  });
  it("unknown rule id keeps the English text", () => {
    expect(localizeTriageRationale("Eng", [r1, "NOPE_ID"], "hi")).toBe("Eng");
    expect(localizeTriageRationale("Eng", ["NOPE_ID", r1], "hi")).toBe("Eng");
  });
  it("empty matched list returns text unchanged", () => {
    expect(localizeTriageRationale("Eng", [], "hi")).toBe("Eng");
  });
  it("duplicate rule ids yield the Hindi sentence once; distinct ids are joined", () => {
    expect(localizeTriageRationale("Eng", [r1, r1], "hi")).toBe(HI_TRIAGE_RATIONALE[r1]);
    expect(localizeTriageRationale("Eng", [r1, r2], "hi")).toBe(`${HI_TRIAGE_RATIONALE[r1]} ${HI_TRIAGE_RATIONALE[r2]}`);
  });
  it("does not mutate inputs", () => {
    const src = expectedList.find((x) => x.e.matched_rules.length > 0)!.e;
    const copy = JSON.parse(JSON.stringify(src)) as Expected;
    src.immediate_actions.forEach((a) => localizeTriageAction(a, "hi"));
    localizeTriageRationale(src.rationale, src.matched_rules, "hi");
    expect(src).toEqual(copy);
  });
});

describe("vibrateIfEmergency", () => {
  it("is safe with no bridge, a bridge without the method, or a throwing bridge", () => {
    expect(() => vibrateIfEmergency("RED_EMERGENCY", {})).not.toThrow();
    expect(() => vibrateIfEmergency("RED_EMERGENCY", { AarogyaNativeBridge: {} })).not.toThrow();
    const bad = { AarogyaNativeBridge: { vibrateEmergency: () => { throw new Error("boom"); } } };
    expect(() => vibrateIfEmergency("RED_EMERGENCY", bad)).not.toThrow();
  });
  it("calls the bridge once for red only", () => {
    const spy = vi.fn();
    const g = { AarogyaNativeBridge: { vibrateEmergency: spy } };
    vibrateIfEmergency("YELLOW_PHC", g);
    vibrateIfEmergency("GREEN_HOME", g);
    expect(spy).not.toHaveBeenCalled();
    vibrateIfEmergency("RED_EMERGENCY", g);
    expect(spy).toHaveBeenCalledTimes(1);
  });
  it("defaults to globalThis without throwing", () => {
    expect(() => vibrateIfEmergency("RED_EMERGENCY")).not.toThrow();
  });
});
