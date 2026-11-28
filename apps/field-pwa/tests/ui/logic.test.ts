import "fake-indexeddb/auto";
import { IDBFactory } from "fake-indexeddb";
import { describe, expect, it } from "vitest";
import type { ActionCard, CrdtEvent } from "../../../../packages/contracts/ts/index";
import { buildPatient, type RegisterForm } from "../../src/ui/register_logic";
import { administeredFromEvents, buildVaccinationPayload, groupByStatus, scheduleFor } from "../../src/ui/vacc_logic";
import { autoChecklistType, buildChecklistPayload, checklistItems, evaluate } from "../../src/ui/checklist_logic";
import { buildVoicePayload, voiceNoteValid } from "../../src/ui/voice_logic";
import { ackPayload, buildCrdtNodeProof, formatHlcVector, sortCards } from "../../src/ui/sync_logic";
import { buildSafetyFloorProof } from "../../src/ui/screens/triage_result";
import { getAudio, putAudio } from "../../src/ui/audio_store";
import { isValidHubUrl } from "../../src/ui/settings";
import { parseRoute } from "../../src/ui/router";

const form = (o: Partial<RegisterForm> = {}): RegisterForm => ({
  full_name: "Asha Devi", sex: "F", dob: "", age_months: "14", village_id: "V1", household_id: "", is_pregnant: false,
  gestational_weeks: "", preferred_language: "hi", ...o,
});
const now = new Date(2026, 10, 23);

describe("registration", () => {
  it("builds a contract-shaped record", () => {
    const r = buildPatient(form(), "phone-1", () => "pid-1", now);
    expect(r.ok && r.patient).toMatchObject({
      patient_id: "pid-1", full_name: "Asha Devi", age_months: 14, date_of_birth: null, household_id: null,
      is_pregnant: false, gestational_weeks: null, registered_by_node: "phone-1", preferred_language: "hi", metadata: {},
    });
  });
  it("requires name, village and DOB-or-age; rejects bad DOB and pregnancy rules", () => {
    expect(buildPatient(form({ full_name: " ", village_id: "", age_months: "" }), "n", undefined, now)).toEqual({ ok: false, errors: ["name", "village", "age_or_dob"] });
    expect(buildPatient(form({ dob: "2027-01-01" }), "n", undefined, now)).toEqual({ ok: false, errors: ["dob"] });
    expect(buildPatient(form({ dob: "2026-02-30" }), "n", undefined, now)).toEqual({ ok: false, errors: ["dob"] });
    expect(buildPatient(form({ sex: "M", is_pregnant: true }), "n", undefined, now)).toEqual({ ok: false, errors: ["preg_sex"] });
    expect(buildPatient(form({ is_pregnant: true, gestational_weeks: "46" }), "n", undefined, now)).toEqual({ ok: false, errors: ["weeks"] });
    const ok = buildPatient(form({ dob: "2025-01-01", age_months: "99", is_pregnant: true, gestational_weeks: "20" }), "n", () => "x", now);
    expect(ok.ok && ok.patient).toMatchObject({ date_of_birth: "2025-01-01", age_months: null, gestational_weeks: 20 });
  });
});

describe("vaccination logic", () => {
  const ev = (code: string, date: string, pid = "p1"): CrdtEvent => ({
    event_id: `${code}-${pid}`, hlc: { wall_ms: 1, logical: 0, node_id: "n" }, origin_node_id: "n", patient_id: pid,
    event_type: "VACCINATION_LOGGED", payload: { vaccine_code: code, administered_date: date }, enrichment_state: "NOT_NEEDED", ref_event_id: null,
  });
  it("logging a dose marks it COMPLETED on recompute and only for that patient", () => {
    const before = groupByStatus(scheduleFor("2026-01-01", [], "p1", "2026-11-23"));
    expect(before.OVERDUE.length).toBeGreaterThan(0);
    const code = before.OVERDUE[0].vaccine_code;
    const payload = buildVaccinationPayload("2026-01-01", code, "2026-11-20", "2026-11-23")!;
    expect(payload).toMatchObject({ vaccine_code: code, status: "COMPLETED", administered_date: "2026-11-20", days_delta: 0 });
    const events = [ev(code, "2026-11-20"), ev(code, "2026-11-01", "other")];
    expect(administeredFromEvents(events, "p1")).toEqual({ [code]: "2026-11-20" });
    const after = groupByStatus(scheduleFor("2026-01-01", events, "p1", "2026-11-23"));
    expect(after.COMPLETED.map((i) => i.vaccine_code)).toContain(code);
    expect(after.OVERDUE.map((i) => i.vaccine_code)).not.toContain(code);
  });
  it("rejects bad dates and unknown codes", () => {
    expect(buildVaccinationPayload("2026-01-01", "BCG", "2025-12-31", "2026-11-23")).toBeNull();
    expect(buildVaccinationPayload("2026-01-01", "BCG", "2026-12-01", "2026-11-23")).toBeNull();
    expect(buildVaccinationPayload("2026-01-01", "NOPE", "2026-02-01", "2026-11-23")).toBeNull();
  });
});

describe("checklist logic", () => {
  it("auto-selects the ANC trimester", () => {
    expect(autoChecklistType(8)).toBe("anc_trimester_1");
    expect(autoChecklistType(20)).toBe("anc_trimester_2");
    expect(autoChecklistType(34)).toBe("anc_trimester_3");
    expect(autoChecklistType(null)).toBeNull();
    expect(autoChecklistType(99)).toBeNull();
  });
  it("payload has no card_id/status and flags critical gaps", () => {
    const items = checklistItems("anc_trimester_3");
    const ev = evaluate("anc_trimester_3", [items[0].id], "p1");
    const payload = buildChecklistPayload(ev);
    expect(payload).not.toHaveProperty("card_id");
    expect(payload).not.toHaveProperty("status");
    expect(payload.completed_items).toEqual([items[0].id]);
    expect(ev.has_critical_gaps).toBe(items.some((i, idx) => idx > 0 && i.critical));
    const all = evaluate("anc_trimester_3", items.map((i) => i.id), null);
    expect(all.is_complete).toBe(true);
  });
});

describe("voice, audio store, sync helpers", () => {
  it("voice payload shape and validity", () => {
    const p = buildVoicePayload({ hint: "  fever  ", language: "hi", blobKey: "k", mime: "audio/webm", durationMs: 1234.6 });
    expect(p).toEqual({ transcript_hint: "fever", language: "hi", audio_blob_key: "k", mime_type: "audio/webm", duration_ms: 1235 });
    expect(voiceNoteValid(p)).toBe(true);
    expect(voiceNoteValid(buildVoicePayload({ hint: " ", language: "en", blobKey: null, mime: null, durationMs: 0 }))).toBe(false);
    expect(voiceNoteValid(buildVoicePayload({ hint: "typed", language: "en", blobKey: null, mime: null, durationMs: 0 }))).toBe(true);
  });
  it("stores and reads blobs in its own database", async () => {
    const f = new IDBFactory();
    await putAudio("k1", new Blob(["abc"], { type: "audio/webm" }), f);
    const b = await getAudio("k1", f);
    expect(b?.size).toBe(3);
    expect(await getAudio("missing", f)).toBeUndefined();
  });
  it("sorts cards open-first by priority and builds a minimal ack", () => {
    const c = (id: string, priority: ActionCard["priority"], status: ActionCard["status"]): ActionCard => ({
      card_id: id, patient_id: null, title: id, summary: "s", action_steps: [], priority, severity: null, status,
      target_tier: "TIER_1_PHONE", watch_mode: null, source_event_id: null, due_by: null, language: "en",
    });
    const sorted = sortCards([c("a", "LOW", "OPEN"), c("b", "CRITICAL", "ACKNOWLEDGED"), c("c", "HIGH", "OPEN")]);
    expect(sorted.map((x) => x.card_id)).toEqual(["c", "a", "b"]);
    expect(ackPayload(sorted[0])).toEqual({ card_id: "c", status: "ACKNOWLEDGED" });
  });
  it("validates hub urls and parses routes", () => {
    expect(isValidHubUrl("http://127.0.0.1:8000")).toBe(true);
    expect(isValidHubUrl("javascript:alert(1)")).toBe(false);
    expect(isValidHubUrl("nope")).toBe(false);
    expect(parseRoute("")).toEqual({ name: "home", params: [] });
    expect(parseRoute("#/triage/a%20b")).toEqual({ name: "triage", params: ["a b"] });
  });
  it("builds deterministic safety-floor and CRDT HLC proof metadata", () => {
    const proof = buildSafetyFloorProof({
      assessment_id: "a1",
      patient_id: "p1",
      severity: "RED_EMERGENCY",
      matched_rules: ["IMNCI_GDS_03"],
      immediate_actions: ["Immediate 108 referral"],
      referral_required: true,
      rationale: "Convulsions",
      confidence: 1.0,
      protocol_source: "WHO_IMNCI_PEDIATRIC_DETERMINISTIC",
      execution_target: "LOCAL_DETERMINISTIC",
      assessed_at_ms: 1700000000000,
    });
    expect(proof).toEqual({
      executionTarget: "LOCAL_DETERMINISTIC",
      confidence: "1.00",
      matchedRules: ["IMNCI_GDS_03"],
    });

    const e1: CrdtEvent = {
      event_id: "e1",
      hlc: { wall_ms: 1000, logical: 0, node_id: "phone-1" },
      origin_node_id: "phone-1",
      patient_id: "p1",
      event_type: "PATIENT_REGISTERED",
      payload: {},
      enrichment_state: "NOT_NEEDED",
      ref_event_id: null,
    };
    const e2: CrdtEvent = {
      ...e1,
      event_id: "e2",
      hlc: { wall_ms: 2000, logical: 3, node_id: "hub-1" },
      origin_node_id: "hub-1",
    };
    expect(formatHlcVector(e2.hlc)).toBe("2000:3:hub-1");
    expect(buildCrdtNodeProof("phone-1", [e2, e1], 1, "offline")).toEqual({
      nodeId: "phone-1",
      latestHlc: "2000:3:hub-1",
      eventCount: 2,
      pendingCount: 1,
      status: "offline",
    });
    expect(buildCrdtNodeProof("phone-1", [], 0, "idle").latestHlc).toBe("0:0:phone-1");
  });
});
