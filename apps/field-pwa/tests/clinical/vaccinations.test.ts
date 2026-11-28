import { describe, expect, it } from "vitest";
import type { ActionCard, VaccinationDueItem } from "../../../../packages/contracts/ts/index";
import { computeVaccinationSchedule, vaccinationItemsToActionCards } from "../../src/clinical";
import fixturesRaw from "./fixtures/vaccination_vectors.json";

type CardFields = Omit<ActionCard, "card_id">;
interface Case {
  name: string;
  dob: string;
  administered: Record<string, string | null> | string[] | null;
  as_of_date: string;
  due_soon_window_days: number | null;
  expected: VaccinationDueItem[];
  cards_watch: CardFields[];
  cards_phone: CardFields[];
}
const fixtures = fixturesRaw as {
  cases: Case[];
  error_case: { dob: string; as_of_date: string; message: string };
};

const withoutCardId = (cards: ActionCard[]): CardFields[] =>
  cards.map(({ card_id: _id, ...rest }) => rest);

describe("UIP vaccination parity with packages/clinical-engine (Python)", () => {
  it("fixtures exercise every status", () => {
    const statuses = new Set(fixtures.cases.flatMap((c) => c.expected.map((i) => i.status)));
    expect([...statuses].sort()).toEqual(["COMPLETED", "DUE_SOON", "OVERDUE", "UPCOMING"]);
  });

  it.each(fixtures.cases.map((c) => [c.name, c] as const))("%s", (_name, c) => {
    const items = computeVaccinationSchedule(c.dob, c.administered, c.as_of_date, {
      dueSoonWindowDays: c.due_soon_window_days,
    });
    expect(items).toEqual(c.expected);

    const watch = vaccinationItemsToActionCards(items, { patient_id: "child-7" });
    expect(withoutCardId(watch)).toEqual(c.cards_watch);
    const phone = vaccinationItemsToActionCards(items, { target_tier: "TIER_1_PHONE", watch_mode: "CHW_COMPANION" });
    expect(withoutCardId(phone)).toEqual(c.cards_phone);
  });

  it("accepts a Map of administered dates", () => {
    const viaMap = computeVaccinationSchedule("2026-01-01", new Map([["bcg", "2026-01-02"]]), "2026-01-10");
    expect(viaMap[0]).toMatchObject({ vaccine_code: "BCG", status: "COMPLETED", administered_date: "2026-01-02" });
  });

  it("rejects as_of_date before dob with the Python message", () => {
    const e = fixtures.error_case;
    expect(() => computeVaccinationSchedule(e.dob, null, e.as_of_date)).toThrow(e.message);
  });

  it("rejects malformed ISO dates", () => {
    expect(() => computeVaccinationSchedule("2026-02-30", null, "2026-03-01")).toThrow(/Invalid ISO date/);
  });
});
