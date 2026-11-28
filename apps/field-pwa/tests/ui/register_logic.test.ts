import { describe, expect, it } from "vitest";
import { ageFromDob, buildPatient, type RegisterForm } from "../../src/ui/register_logic";

const form = (o: Partial<RegisterForm> = {}): RegisterForm => ({
  full_name: "Asha Devi", sex: "F", dob: "", age_months: "14", village_id: "V1", household_id: "", is_pregnant: false,
  gestational_weeks: "", preferred_language: "hi", ...o,
});
const now = new Date(2026, 10, 23);
const build = (o: Partial<RegisterForm>) => buildPatient(form(o), "n", () => "pid", now);

describe("buildPatient age_unit", () => {
  it("converts years to months", () => {
    const r = build({ age_months: "25", age_unit: "years" });
    expect(r.ok && r.patient.age_months).toBe(300);
    const max = build({ age_months: "125", age_unit: "years" });
    expect(max.ok && max.patient.age_months).toBe(1500);
  });
  it("rejects years over 125, non-integers and negatives", () => {
    expect(build({ age_months: "126", age_unit: "years" })).toEqual({ ok: false, errors: ["age"] });
    expect(build({ age_months: "2.5", age_unit: "years" })).toEqual({ ok: false, errors: ["age"] });
    expect(build({ age_months: "-1", age_unit: "years" })).toEqual({ ok: false, errors: ["age"] });
    expect(build({ age_months: "abc", age_unit: "years" })).toEqual({ ok: false, errors: ["age"] });
  });
  it("dob still wins over age when unit is years", () => {
    const r = build({ dob: "2000-01-01", age_months: "25", age_unit: "years" });
    expect(r.ok && r.patient).toMatchObject({ date_of_birth: "2000-01-01", age_months: null });
  });
  it("missing or months unit behaves as before", () => {
    for (const age_unit of [undefined, "months" as const]) {
      const r = build({ age_months: "14", age_unit });
      expect(r.ok && r.patient.age_months).toBe(14);
      expect(build({ age_months: "1501", age_unit })).toEqual({ ok: false, errors: ["age"] });
    }
    const edge = build({ age_months: "1500", age_unit: "months" });
    expect(edge.ok && edge.patient.age_months).toBe(1500);
  });
});

describe("ageFromDob", () => {
  it("returns months when age is under 24 months", () => {
    expect(ageFromDob("2025-11-23", now)).toEqual({ value: 12, unit: "months" });
    expect(ageFromDob("2026-11-23", now)).toEqual({ value: 0, unit: "months" });
    expect(ageFromDob("2024-12-23", now)).toEqual({ value: 23, unit: "months" });
  });
  it("returns years when age is 24 months or more", () => {
    expect(ageFromDob("2024-11-23", now)).toEqual({ value: 2, unit: "years" });
    expect(ageFromDob("2000-01-01", now)).toEqual({ value: 26, unit: "years" });
  });
  it("returns null for empty, invalid, or future dates", () => {
    expect(ageFromDob("", now)).toBeNull();
    expect(ageFromDob("not-a-date", now)).toBeNull();
    expect(ageFromDob("2026-11-24", now)).toBeNull();
  });
});

describe("buildPatient initial_symptoms & clinical_notes", () => {
  it("merges quick-select tags and comma-separated other symptoms into metadata", () => {
    const r = build({
      initial_symptoms: ["fever", "cough"],
      other_symptoms: "rash, cough, joint pain ",
      clinical_notes: "  mild chills since yesterday  ",
    });
    expect(r.ok && r.patient.metadata).toEqual({
      initial_symptoms: ["fever", "cough", "rash", "joint pain"],
      clinical_notes: "mild chills since yesterday",
    });
  });
  it("keeps metadata empty when optional notes and symptoms are blank", () => {
    const r = build({ initial_symptoms: [], other_symptoms: " , ", clinical_notes: "   " });
    expect(r.ok && r.patient.metadata).toEqual({});
  });
});
