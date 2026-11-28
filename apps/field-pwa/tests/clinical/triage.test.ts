import { describe, expect, it } from "vitest";
import type { ActionCard, TriageAssessment } from "../../../../packages/contracts/ts/index";
import {
  evaluateTriage,
  evaluateWatchRapidTriage,
  triageToActionCard,
  IMNCI_PEDIATRIC_RULES,
  MATERNAL_ANC_RULES,
  FLAG_ALIASES,
} from "../../src/clinical";
import type { TriageInput } from "../../src/clinical";
import { pyFixed1 } from "../../src/clinical/pyfmt";
import fixturesRaw from "./fixtures/triage_vectors.json";

type CardFields = Omit<ActionCard, "card_id">;
interface Vector {
  name: string;
  input: TriageInput;
  error?: boolean;
  expected?: Omit<TriageAssessment, "assessment_id">;
  action_card_watch?: CardFields;
  action_card_phone?: CardFields;
}
const fixtures = fixturesRaw as {
  vectors: Vector[];
  watch_rapid: { name: string; danger_signs: string[]; opts: TriageInput; expected: Omit<TriageAssessment, "assessment_id"> }[];
};

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/;
const stripId = <T extends object>(o: T, key: keyof T): Omit<T, typeof key> => {
  const { [key]: _drop, ...rest } = o;
  return rest;
};

describe("triage parity with packages/clinical-engine (Python)", () => {
  const valid = fixtures.vectors.filter((v) => !v.error);
  const invalid = fixtures.vectors.filter((v) => v.error);

  it("fixture set is non-trivial", () => {
    expect(valid.length).toBeGreaterThan(250);
    expect(invalid.length).toBeGreaterThan(0);
  });

  it.each(valid.map((v) => [v.name, v] as const))("%s", (_name, v) => {
    const got = evaluateTriage(v.input);
    expect(got.assessment_id).toMatch(UUID);
    expect(stripId(got, "assessment_id")).toEqual(v.expected);

    const watchCard = triageToActionCard(got);
    expect(watchCard.card_id).toMatch(UUID);
    expect(stripId(watchCard, "card_id")).toEqual(v.action_card_watch);
    const phoneCard = triageToActionCard(got, { target_tier: "TIER_1_PHONE", source_event_id: "evt-1" });
    expect(stripId(phoneCard, "card_id")).toEqual(v.action_card_phone);
  });

  it.each(invalid.map((v) => [v.name, v] as const))("rejects invalid input: %s", (_name, v) => {
    expect(() => evaluateTriage(v.input)).toThrow(/Invalid TriageInput/);
  });

  it.each(fixtures.watch_rapid.map((v) => [v.name, v] as const))("watch rapid entrypoint: %s", (_name, v) => {
    const got = evaluateWatchRapidTriage(v.danger_signs, v.opts);
    expect(stripId(got, "assessment_id")).toEqual(v.expected);
  });

  it("covers every rule id declared in the bundled rule tables", () => {
    const seen = new Set(valid.flatMap((v) => v.expected!.matched_rules));
    const declared = [
      ...IMNCI_PEDIATRIC_RULES.general_danger_signs.map((r) => r.id),
      ...(IMNCI_PEDIATRIC_RULES.young_infant_danger_signs ?? []).map((r) => r.id),
      ...(IMNCI_PEDIATRIC_RULES.syndrome_symptom_rules ?? []).map((r) => r.id),
      ...IMNCI_PEDIATRIC_RULES.syndromes.respiratory.red_rules.map((r) => r.id),
      ...IMNCI_PEDIATRIC_RULES.syndromes.respiratory.yellow_rules.map((r) => r.id),
      IMNCI_PEDIATRIC_RULES.syndromes.respiratory.green_rule.id,
      ...MATERNAL_ANC_RULES.red_flag_symptoms.map((r) => r.id),
      ...MATERNAL_ANC_RULES.yellow_flag_symptoms.map((r) => r.id),
    ];
    for (const id of declared) expect(seen, id).toContain(id);
    expect(seen.size).toBeGreaterThanOrEqual(85);
  });
});

describe("safety floor invariants", () => {
  it("a single general danger sign alone yields RED_EMERGENCY with referral and confidence 1.0", () => {
    const a = evaluateTriage({ age_months: 18, danger_signs: ["convulsions"], assessed_at_ms: 1 });
    expect(a.severity).toBe("RED_EMERGENCY");
    expect(a.referral_required).toBe(true);
    expect(a.confidence).toBe(1.0);
    expect(a.execution_target).toBe("LOCAL_DETERMINISTIC");
    expect(a.matched_rules).toEqual(["IMNCI_GDS_03"]);
  });

  const redGeneralFlags = new Set(IMNCI_PEDIATRIC_RULES.general_danger_signs.map((r) => r.flag));
  const redYoungInfantFlags = new Set((IMNCI_PEDIATRIC_RULES.young_infant_danger_signs ?? []).map((r) => r.flag));
  const redSyndromeFlags = new Set(
    (IMNCI_PEDIATRIC_RULES.syndrome_symptom_rules ?? []).filter((r) => r.severity === "RED_EMERGENCY").map((r) => r.flag),
  );
  const redMaternalFlags = new Set(MATERNAL_ANC_RULES.red_flag_symptoms.map((r) => r.flag));

  const aliasRedCases: { flag: string; input: TriageInput }[] = Object.entries(FLAG_ALIASES).flatMap(
    ([alias, target]): { flag: string; input: TriageInput }[] => {
      if (redGeneralFlags.has(target) || redMaternalFlags.has(target)) return [{ flag: alias, input: { is_pregnant: true } }];
      if (redYoungInfantFlags.has(target)) return [{ flag: alias, input: { age_months: 1 } }];
      if (redSyndromeFlags.has(target)) return [{ flag: alias, input: { age_months: 24 } }];
      return [];
    },
  );

  const allFlags: { flag: string; input: TriageInput }[] = [
    ...IMNCI_PEDIATRIC_RULES.general_danger_signs.map((r) => ({ flag: r.flag, input: { age_months: 30 } })),
    ...IMNCI_PEDIATRIC_RULES.general_danger_signs.map((r) => ({ flag: r.flag, input: { age_months: 400 } })),
    ...(IMNCI_PEDIATRIC_RULES.young_infant_danger_signs ?? []).map((r) => ({ flag: r.flag, input: { age_months: 1 } })),
    ...(IMNCI_PEDIATRIC_RULES.syndrome_symptom_rules ?? [])
      .filter((r) => r.severity === "RED_EMERGENCY")
      .map((r) => ({ flag: r.flag, input: { age_months: 24 } })),
    ...MATERNAL_ANC_RULES.red_flag_symptoms.map((r) => ({ flag: r.flag, input: { is_pregnant: true } })),
    ...aliasRedCases,
  ];

  it.each(allFlags.map((f) => [f.flag, f] as const))(
    "single sign %s => RED even alongside benign vitals",
    (_flag, f) => {
      const a = evaluateTriage({
        ...f.input,
        danger_signs: [f.flag],
        spo2_pct: 99,
        temperature_c: 36.8,
        has_cough_or_difficult_breathing: true,
      });
      expect(a.severity).toBe("RED_EMERGENCY");
      expect(a.referral_required).toBe(true);
      expect(a.confidence).toBe(1.0);
    },
  );

  it("severity is monotonic: adding GREEN findings never downgrades RED", () => {
    const a = evaluateTriage({ age_months: 24, danger_signs: ["cyanosis"], has_diarrhea: true, fever_days: 1 });
    expect(a.matched_rules).toContain("IMNCI_DIARRHEA_NO_DEHYDRATION_GREEN");
    expect(a.severity).toBe("RED_EMERGENCY");
  });
});

describe("python float formatting", () => {
  it("rounds exact ties half-to-even like Python", () => {
    expect(pyFixed1(38.25)).toBe("38.2");
    expect(pyFixed1(38.75)).toBe("38.8");
    expect(pyFixed1(38.05)).toBe("38.0"); // binary value is just below .05
    expect(pyFixed1(38)).toBe("38.0");
  });
});
