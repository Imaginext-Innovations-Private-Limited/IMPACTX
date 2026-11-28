import { describe, expect, it } from "vitest";
import type { NodeTier, WatchMode } from "../../../../packages/contracts/ts/index";
import {
  evaluateChecklist,
  listChecklistTypes,
  selectAncChecklistForGestationalWeeks,
} from "../../src/clinical";
import type { ChecklistEvaluation } from "../../src/clinical";
import fixturesRaw from "./fixtures/checklist_vectors.json";

interface Case {
  name: string;
  checklist_type: string;
  completed: string[] | Record<string, boolean>;
  opts: { patient_id?: string; due_by?: string; target_tier?: NodeTier; watch_mode?: WatchMode };
  expected: Omit<ChecklistEvaluation, "action_cards"> & { action_cards: object[] };
}
const fixtures = fixturesRaw as {
  cases: Case[];
  select_anc: { weeks: number; expected?: string; error?: boolean }[];
};

describe("ANC/PNC checklist parity with packages/clinical-engine (Python)", () => {
  it("covers all checklist types", () => {
    expect(new Set(fixtures.cases.map((c) => c.checklist_type))).toEqual(new Set(listChecklistTypes()));
  });

  it.each(fixtures.cases.map((c) => [c.name, c] as const))("%s", (_name, c) => {
    const got = evaluateChecklist(c.checklist_type, c.completed, c.opts);
    const { action_cards, ...rest } = got;
    const { action_cards: expectedCards, ...expectedRest } = c.expected;
    expect(rest).toEqual(expectedRest);
    expect(action_cards.map(({ card_id: _id, ...card }) => card)).toEqual(expectedCards);
  });

  it.each(fixtures.select_anc.map((s) => [s.weeks, s] as const))("select ANC checklist for %s weeks", (_w, s) => {
    if (s.error) {
      expect(() => selectAncChecklistForGestationalWeeks(s.weeks)).toThrow();
    } else {
      expect(selectAncChecklistForGestationalWeeks(s.weeks)).toBe(s.expected);
    }
  });

  it("rejects unknown checklist types", () => {
    expect(() => evaluateChecklist("anc_trimester_4", [])).toThrow(/not a valid ChecklistType/);
  });
});
