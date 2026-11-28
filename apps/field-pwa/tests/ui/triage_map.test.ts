import { describe, expect, it } from "vitest";
import { evaluateTriage, evaluateWatchRapidTriage } from "../../src/clinical";
import {
  applyCategory,
  buildTriageInput,
  convertTempDisplay,
  fahrenheitToCelsius,
  hiddenTickedFlags,
  visibleFlags,
  maternalRedOptions,
  maternalYellowOptions,
  parseNum,
  parseTemp,
  patientAgeMonths,
  pediatricDangerOptions,
  dangerOptionsForCategory,
  fastEmergencyOptions,
  FAST_EMERGENCY_FLAGS,
  PEDIATRIC_ONLY_DANGER_FLAGS,
  suggestCategory,
  type TriageFormState,
} from "../../src/ui/triage_map";

const base = (over: Partial<TriageFormState> = {}): TriageFormState => ({
  category: "PEDIATRIC", patientId: null, nums: {}, isPregnant: false, isPostpartum: false,
  dangerFlags: [], symptomFlags: [], dehydrationFlags: [], cough: false, chestIndrawing: false,
  diarrhea: false, bloodInStool: false, edema: false, pallor: false, malariaRdt: false, ...over,
});
const run = (s: TriageFormState) => {
  const r = buildTriageInput(s, 1_700_000_000_000);
  if (!r.ok) throw new Error("build failed");
  return evaluateTriage(r.input);
};

describe("canonical flag options", () => {
  it("every pediatric danger-sign checkbox flag triages RED with no aliasing", () => {
    for (const category of ["PEDIATRIC", "GENERAL"] as const) {
      for (const o of dangerOptionsForCategory(category)) {
        expect(run(base({ category, dangerFlags: [o.flag] })).severity, `${category}:${o.flag}`).toBe("RED_EMERGENCY");
      }
    }
  });
  it("dangerOptionsForCategory hides only child-only signs outside PEDIATRIC", () => {
    const flags = (os: { flag: string }[]) => os.map((o) => o.flag);
    expect(dangerOptionsForCategory("PEDIATRIC")).toEqual(pediatricDangerOptions());
    const expected = flags(pediatricDangerOptions()).filter((f) => !PEDIATRIC_ONLY_DANGER_FLAGS.has(f));
    for (const c of ["MATERNAL", "GENERAL"] as const) expect(flags(dangerOptionsForCategory(c))).toEqual(expected);
    expect(flags(pediatricDangerOptions())).toContain("stridor_in_calm_child");
    expect(flags(pediatricDangerOptions()).length - expected.length).toBe(PEDIATRIC_ONLY_DANGER_FLAGS.size);
  });
  it("every maternal red flag triages RED", () => {
    for (const o of maternalRedOptions()) {
      expect(run(base({ category: "MATERNAL", isPregnant: true, dangerFlags: [o.flag] })).severity, o.flag).toBe("RED_EMERGENCY");
    }
  });
  it("maternal yellow flags are never GREEN", () => {
    for (const o of maternalYellowOptions()) {
      const sev = run(base({ category: "MATERNAL", isPregnant: true, symptomFlags: [o.flag] })).severity;
      expect(sev, o.flag).not.toBe("GREEN_HOME");
    }
  });
  it("options carry non-empty labels", () => {
    for (const o of [...pediatricDangerOptions(), ...maternalRedOptions(), ...maternalYellowOptions()]) expect(o.label.length).toBeGreaterThan(3);
  });
});

describe("buildTriageInput", () => {
  it("rejects out-of-range and non-numeric vitals, with no input produced", () => {
    const r = buildTriageInput(base({ nums: { spo2_pct: "150", temperature_c: "abc", respiratory_rate_bpm: "40.5" } }));
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.map((e) => `${e.field}:${e.reason}`).sort()).toEqual(["respiratory_rate_bpm:integer", "spo2_pct:range", "temperature_c:NaN"]);
  });
  it("blank vitals are omitted (not 0)", () => {
    const r = buildTriageInput(base());
    expect(r.ok && r.input.spo2_pct).toBeUndefined();
  });
  it("parseNum boundaries", () => {
    expect(parseNum("temperature_c", "30")).toBe(30);
    expect(parseNum("temperature_c", "45.1")).toMatchObject({ reason: "range" });
    expect(parseNum("gestational_weeks", "45")).toBe(45);
    expect(parseNum("gestational_weeks", " ")).toBeUndefined();
  });
  it("critical SpO2 alone goes RED through the engine", () => {
    expect(run(base({ nums: { spo2_pct: "85" } })).severity).toBe("RED_EMERGENCY");
  });
  it("maternal severe BP goes RED; gestational weeks only when pregnant", () => {
    const a = run(base({ category: "MATERNAL", isPregnant: true, nums: { systolic_bp: "170", diastolic_bp: "112", gestational_weeks: "30" } }));
    expect(a.severity).toBe("RED_EMERGENCY");
    const r = buildTriageInput(base({ category: "MATERNAL", isPregnant: false, nums: { gestational_weeks: "30" } }));
    expect(r.ok && r.input.gestational_weeks).toBeUndefined();
  });
  it("a healthy child with normal vitals is GREEN", () => {
    expect(run(base({ nums: { age_months: "24", temperature_c: "36.8", spo2_pct: "98" } })).severity).toBe("GREEN_HOME");
  });
  it("converts Fahrenheit inputs to Celsius and validates 86-113 °F bounds", () => {
    expect(fahrenheitToCelsius(98.6)).toBe(37);
    expect(parseTemp("85.9", "F")).toMatchObject({ reason: "range" });
    expect(parseTemp("113.1", "F")).toMatchObject({ reason: "range" });
    expect(parseTemp("100.4", "F")).toBe(38);
    expect(convertTempDisplay("98.6", "C")).toBe("37");
    expect(convertTempDisplay("37", "F")).toBe("98.6");
    const r = buildTriageInput(base({ tempUnit: "F", nums: { age_months: "24", temperature_c: "103.1", spo2_pct: "98" } }));
    expect(r.ok && r.input.temperature_c).toBe(39.5);
    expect(run(base({ tempUnit: "F", nums: { age_months: "24", temperature_c: "103.1", spo2_pct: "98" } })).severity).toBe("RED_EMERGENCY");
  });
  it("merges comma-separated additionalSymptoms into TriageInput.symptoms", () => {
    const r = buildTriageInput(base({ category: "MATERNAL", isPregnant: true, symptomFlags: ["mild_pedal_edema"], additionalSymptoms: "dizziness, mild_pedal_edema, ear pain" }));
    expect(r.ok && r.input.symptoms).toEqual(["mild_pedal_edema", "dizziness", "ear pain"]);
  });
});

describe("fast path and category helpers", () => {
  it("fast path danger sign is RED via the engine", () => {
    const a = evaluateWatchRapidTriage(["lethargic_or_unconscious"], { patient_id: null });
    expect(a.severity).toBe("RED_EMERGENCY");
    expect(a.referral_required).toBe(true);
  });
  it("suggests category and computes age", () => {
    const now = new Date(2026, 10, 23);
    expect(suggestCategory({ age_months: null, date_of_birth: "2025-06-01", is_pregnant: false }, now)).toBe("PEDIATRIC");
    expect(suggestCategory({ age_months: null, date_of_birth: "1990-01-01", is_pregnant: true }, now)).toBe("MATERNAL");
    expect(suggestCategory({ age_months: 400, date_of_birth: null, is_pregnant: false }, now)).toBe("GENERAL");
    expect(patientAgeMonths({ age_months: null, date_of_birth: "2025-11-24" }, now)).toBe(11);
  });
});

describe("category safety (no silent default, no hidden flags)", () => {
  it("(a) no category chosen: nothing is built, so nothing can be evaluated", () => {
    const r = buildTriageInput(base({ category: null, patientId: null, nums: { spo2_pct: "98" } }));
    expect(r).toMatchObject({ ok: false, needsCategory: true });
  });

  it("(b) maternal red flag then category switch: flag is cleared and reported, never silently GREEN", () => {
    const s = base({ category: "MATERNAL", isPregnant: true, dangerFlags: ["vaginal_bleeding"] });
    expect(run(s).severity).toBe("RED_EMERGENCY");
    const { cleared } = applyCategory(s, "PEDIATRIC");
    expect(cleared).toEqual(["vaginal_bleeding"]); // UI shows this in a notice
    expect(hiddenTickedFlags(s)).toEqual([]);
    expect(s.dangerFlags).not.toContain("vaginal_bleeding");
  });

  it("(b) a hidden flag injected into state is refused, not evaluated", () => {
    const s = base({ category: "PEDIATRIC", dangerFlags: ["vaginal_bleeding"] });
    const r = buildTriageInput(s);
    expect(r).toMatchObject({ ok: false, hiddenFlags: ["vaginal_bleeding"] });
  });

  it("(b) universal danger signs survive any category switch", () => {
    const s = base({ category: "PEDIATRIC", dangerFlags: ["convulsions"], dehydrationFlags: ["sunken_eyes"] });
    expect(applyCategory(s, "MATERNAL").cleared).toEqual(["sunken_eyes"]);
    expect(s.dangerFlags).toEqual(["convulsions"]);
    applyCategory(s, "GENERAL");
    expect(run(s).severity).toBe("RED_EMERGENCY");
    expect(applyCategory(s, null).cleared).toEqual(["convulsions"]);
  });

  it("(c) every non-child-only IMNCI general danger sign is offered in maternal and general forms and triages RED", () => {
    for (const category of ["MATERNAL", "GENERAL"] as const) {
      const vis = visibleFlags(category);
      expect(vis.has("stridor_in_calm_child")).toBe(false);
      expect(visibleFlags("PEDIATRIC").has("stridor_in_calm_child")).toBe(true);
      for (const o of dangerOptionsForCategory(category)) {
        expect(vis.has(o.flag), `${category} offers ${o.flag}`).toBe(true);
        const s = base({ category, isPregnant: category === "MATERNAL", dangerFlags: [o.flag] });
        expect(hiddenTickedFlags(s)).toEqual([]);
        expect(run(s).severity, `${category}:${o.flag}`).toBe("RED_EMERGENCY");
      }
    }
  });
});

describe("fast-emergency options and stridor clearing", () => {
  it("fastEmergencyOptions omits vaginal_bleeding only for M", () => {
    expect(fastEmergencyOptions("M")).toEqual(["lethargic_or_unconscious", "convulsions", "severe_breathing_difficulty"]);
    for (const sex of ["F", "O", "U", null, undefined] as const) {
      expect(fastEmergencyOptions(sex), String(sex)).toEqual([...FAST_EMERGENCY_FLAGS]);
    }
  });
  it("every returned option triages RED", () => {
    for (const sex of ["M", "F", "O", "U", null, undefined] as const) {
      for (const flag of fastEmergencyOptions(sex)) {
        const r = evaluateWatchRapidTriage([flag], { patient_id: null, assessed_at_ms: 1_700_000_000_000 });
        expect(r.severity, `${String(sex)}:${flag}`).toBe("RED_EMERGENCY");
      }
    }
  });
  for (const target of ["MATERNAL", "GENERAL"] as const) {
    it(`applyCategory(${target}) clears stridor_in_calm_child and it is not restored`, () => {
      const s = base({ category: "PEDIATRIC", dangerFlags: ["stridor_in_calm_child", "convulsions"] });
      const { cleared } = applyCategory(s, target);
      expect(cleared).toEqual(["stridor_in_calm_child"]);
      expect(s.dangerFlags).toEqual(["convulsions"]);
      expect(hiddenTickedFlags(s)).toEqual([]);
      applyCategory(s, "PEDIATRIC");
      expect(s.dangerFlags).toEqual(["convulsions"]);
    });
  }
});
