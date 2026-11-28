import { describe, expect, it } from "vitest";
import type { CrdtEvent } from "../../../../packages/contracts/ts/index";
import { buildChecklistPayload, evaluate, latestCompletedChecks } from "../../src/ui/checklist_logic";

const T = "anc_trimester_3" as const;
let n = 0;
const ev = (
  items: unknown, hlc: { wall_ms: number; logical: number; node_id: string },
  o: Partial<CrdtEvent> & { type?: string } = {},
): CrdtEvent => ({
  event_id: `e${n++}`, hlc, origin_node_id: hlc.node_id, patient_id: "p1",
  event_type: "CHECKLIST_RECORDED", payload: { checklist_type: T, completed_items: items },
  enrichment_state: "NOT_NEEDED", ref_event_id: null, ...o,
} as CrdtEvent);
const h = (wall_ms: number, logical = 0, node_id = "a") => ({ wall_ms, logical, node_id });

describe("latestCompletedChecks", () => {
  it("returns the highest-HLC event regardless of input order", () => {
    const events = [ev(["b"], h(20)), ev(["c"], h(30)), ev(["a"], h(10))];
    expect([...latestCompletedChecks(events, "p1", T)]).toEqual(["c"]);
    expect([...latestCompletedChecks([...events].reverse(), "p1", T)]).toEqual(["c"]);
  });
  it("tie-breaks on logical, then node_id", () => {
    const l = [ev(["lo"], h(5, 1)), ev(["hi"], h(5, 2)), ev(["mid"], h(5, 0))];
    expect([...latestCompletedChecks(l, "p1", T)]).toEqual(["hi"]);
    expect([...latestCompletedChecks([...l].reverse(), "p1", T)]).toEqual(["hi"]);
    const nd = [ev(["z"], h(5, 1, "node-z")), ev(["a"], h(5, 1, "node-a")), ev(["m"], h(5, 1, "node-m"))];
    expect([...latestCompletedChecks(nd, "p1", T)]).toEqual(["z"]);
    expect([...latestCompletedChecks([...nd].reverse(), "p1", T)]).toEqual(["z"]);
  });
  it("ignores other patients, checklist types and event types", () => {
    const events = [
      ev(["mine"], h(1)),
      ev(["other-patient"], h(99), { patient_id: "p2" }),
      ev(["other-type"], h(98), { payload: { checklist_type: "anc_trimester_1", completed_items: ["other-type"] } }),
      ev(["wrong-event"], h(97), { event_type: "TRIAGE_COMPLETED" }),
    ];
    expect([...latestCompletedChecks(events, "p1", T)]).toEqual(["mine"]);
  });
  it("returns empty set for null or unrecorded patient", () => {
    const events = [ev(["a"], h(1))];
    expect(latestCompletedChecks(events, null, T).size).toBe(0);
    expect(latestCompletedChecks(events, "nobody", T).size).toBe(0);
    expect(latestCompletedChecks([], "p1", T).size).toBe(0);
  });
  it("drops non-string entries and tolerates a non-array", () => {
    expect([...latestCompletedChecks([ev(["a", 1, null, { x: 1 }, "b"], h(1))], "p1", T)]).toEqual(["a", "b"]);
    expect(latestCompletedChecks([ev("nope", h(1))], "p1", T).size).toBe(0);
  });
});

describe("buildChecklistPayload additional_notes", () => {
  it("includes trimmed additional_notes when non-empty and omits when blank", () => {
    const evRes = evaluate("anc_trimester_1", ["anc_t1_bp_check"], "p1");
    expect(buildChecklistPayload(evRes, "  Mother reported mild nausea  ").additional_notes).toBe("Mother reported mild nausea");
    expect(buildChecklistPayload(evRes, "   ")).not.toHaveProperty("additional_notes");
  });
});
