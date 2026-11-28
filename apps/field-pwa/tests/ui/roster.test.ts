import { describe, expect, it } from "vitest";
import type { CrdtEvent, PatientRecord } from "../../../../packages/contracts/ts/index";
import { buildRoster, filterRoster } from "../../src/ui/screens/home";

const pat = (id: string, o: Partial<PatientRecord> = {}): PatientRecord => ({
  patient_id: id, full_name: `Name ${id}`, date_of_birth: null, age_months: 12, sex: "F", village_id: "V1", household_id: null,
  is_pregnant: false, gestational_weeks: null, preferred_language: "hi", registered_by_node: "n", metadata: {}, ...o,
});
let k = 0;
const ev = (pid: string, wall_ms: number, o: Record<string, unknown> = {}, logical = 0, node_id = "a"): CrdtEvent => ({
  event_id: `e${k++}`, hlc: { wall_ms, logical, node_id }, origin_node_id: node_id, patient_id: pid,
  event_type: "PATIENT_REGISTERED", payload: {}, enrichment_state: "NOT_NEEDED", ref_event_id: null, ...o,
} as CrdtEvent);
const tri = (pid: string, sev: unknown, wall_ms: number, logical = 0, node_id = "a") =>
  ev(pid, wall_ms, { event_type: "TRIAGE_COMPLETED", payload: { severity: sev } }, logical, node_id);
const DAY = 86_400_000;

describe("buildRoster", () => {
  it("keeps old and synced patients and those with no events", () => {
    const rows = buildRoster(
      [pat("old"), pat("synced"), pat("none")],
      [ev("old", Date.now() - 5 * DAY), ev("synced", 1_000, {}, 0, "other-node")],
    );
    expect(rows.map((r) => r.patient.patient_id).sort()).toEqual(["none", "old", "synced"]);
    const none = rows.find((r) => r.patient.patient_id === "none")!;
    expect(none.touched).toBe(0);
    expect(rows[rows.length - 1]).toBe(none);
  });
  it("sorts newest-first by max wall_ms", () => {
    const rows = buildRoster(
      [pat("a"), pat("b"), pat("c")],
      [ev("a", 100), ev("a", 500), ev("b", 300), ev("c", 200)],
    );
    expect(rows.map((r) => [r.patient.patient_id, r.touched])).toEqual([["a", 500], ["b", 300], ["c", 200]]);
  });
  it("severity follows the highest-HLC TRIAGE_COMPLETED", () => {
    const sev = (events: CrdtEvent[]) => buildRoster([pat("p")], events)[0].severity;
    expect(sev([tri("p", "GREEN_HOME", 20), tri("p", "RED_EMERGENCY", 10)])).toBe("GREEN_HOME");
    expect(sev([tri("p", "RED_EMERGENCY", 10), tri("p", "GREEN_HOME", 20)])).toBe("GREEN_HOME");
    expect(sev([tri("p", "GREEN_HOME", 5, 2), tri("p", "RED_EMERGENCY", 5, 1)])).toBe("GREEN_HOME");
    expect(sev([tri("p", "RED_EMERGENCY", 5, 1), tri("p", "GREEN_HOME", 5, 2)])).toBe("GREEN_HOME");
    expect(sev([tri("p", "YELLOW_PHC", 5, 1, "node-b"), tri("p", "RED_EMERGENCY", 5, 1, "node-a")])).toBe("YELLOW_PHC");
    expect(sev([tri("p", "RED_EMERGENCY", 5, 1, "node-a"), tri("p", "YELLOW_PHC", 5, 1, "node-b")])).toBe("YELLOW_PHC");
  });
  it("unknown severity -> null; no triage -> null; other events don't count", () => {
    expect(buildRoster([pat("p")], [tri("p", "PURPLE", 1)])[0].severity).toBeNull();
    expect(buildRoster([pat("p")], [ev("p", 1)])[0].severity).toBeNull();
    expect(buildRoster([pat("p")], [ev("p", 1, { payload: { severity: "RED_EMERGENCY" } })])[0].severity).toBeNull();
  });
});

describe("filterRoster", () => {
  const rows = buildRoster(
    [
      pat("1", { full_name: "Asha Devi", village_id: "Rampur", household_id: "HH-77" }),
      pat("2", { full_name: "Bimla", village_id: "Shivpur", household_id: null }),
    ],
    [],
  );
  const ids = (q: string) => filterRoster(rows, q).map((r) => r.patient.patient_id);
  it("matches name, village and household case-insensitively", () => {
    expect(ids("ASHA")).toEqual(["1"]);
    expect(ids("shiv")).toEqual(["2"]);
    expect(ids("hh-7")).toEqual(["1"]);
    expect(ids("  rampur ")).toEqual(["1"]);
    expect(ids("zzz")).toEqual([]);
  });
  it("is null-safe for household_id", () => {
    expect(() => ids("hh")).not.toThrow();
    expect(ids("hh")).toEqual(["1"]);
  });
  it("blank or whitespace query returns all", () => {
    expect(ids("")).toHaveLength(2);
    expect(ids("   ")).toHaveLength(2);
  });
});
