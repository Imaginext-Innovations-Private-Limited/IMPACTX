import type { PatientRecord, PatientSex } from "../../../../packages/contracts/ts/index";
import { isoToDayNumber } from "../clinical";
import { uuid } from "../core/uuid";

export const BASELINE_SYMPTOM_TAGS = ["fever", "cough", "weakness", "body_ache", "loss_of_appetite"] as const;

export function parseCustomList(raw: string | undefined): string[] {
  if (!raw) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const part of raw.split(/[,;\n]+/)) {
    const t = part.trim();
    if (t && !seen.has(t)) {
      seen.add(t);
      out.push(t);
    }
  }
  return out;
}

export interface RegisterForm {
  full_name: string;
  sex: PatientSex;
  dob: string; // ISO or ""
  age_months: string; // "" or integer text (in `age_unit`)
  age_unit?: "months" | "years"; // default "months"
  village_id: string;
  household_id: string;
  is_pregnant: boolean;
  gestational_weeks: string;
  preferred_language: string;
  initial_symptoms?: string[];
  other_symptoms?: string;
  clinical_notes?: string;
}

export type RegErr = "name" | "village" | "age_or_dob" | "dob" | "age" | "preg_sex" | "weeks";
export type RegResult = { ok: true; patient: PatientRecord } | { ok: false; errors: RegErr[] };

const todayIso = (now: Date) =>
  `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;

/**
 * Derive age + best unit (`months` if < 24 months, otherwise `years`) from an ISO DOB.
 * Returns null for empty, invalid, or future dates.
 */
export function ageFromDob(
  dobIso: string,
  now: Date = new Date(),
): { value: number; unit: "months" | "years" } | null {
  if (!dobIso) return null;
  try {
    isoToDayNumber(dobIso);
    if (dobIso > todayIso(now)) return null;
  } catch {
    return null;
  }
  const [y, m, d] = dobIso.split("-").map(Number);
  let months = (now.getFullYear() - y) * 12 + (now.getMonth() + 1 - m);
  if (now.getDate() < d) months -= 1;
  months = Math.max(0, months);
  if (months < 24) return { value: months, unit: "months" };
  return { value: Math.min(125, Math.floor(months / 12)), unit: "years" };
}

/** Build a contract-shaped PatientRecord from raw form text, or list the errors. */
export function buildPatient(
  f: RegisterForm,
  nodeId: string,
  newId: () => string = () => uuid(),
  now: Date = new Date(),
): RegResult {
  const errors: RegErr[] = [];
  const name = f.full_name.trim();
  if (!name || name.length > 200) errors.push("name");
  const village = f.village_id.trim();
  if (!village || village.length > 128) errors.push("village");

  let dob: string | null = null;
  let age: number | null = null;
  if (f.dob) {
    try {
      isoToDayNumber(f.dob);
      if (f.dob > todayIso(now)) throw new Error("future");
      dob = f.dob;
    } catch {
      errors.push("dob");
    }
  } else if (f.age_months.trim() !== "") {
    const n = Number(f.age_months);
    const years = f.age_unit === "years";
    if (!Number.isInteger(n) || n < 0 || n > (years ? 125 : 1500)) errors.push("age");
    else age = years ? n * 12 : n;
  } else errors.push("age_or_dob");

  let weeks: number | null = null;
  if (f.is_pregnant) {
    if (f.sex !== "F") errors.push("preg_sex");
    if (f.gestational_weeks.trim() !== "") {
      const w = Number(f.gestational_weeks);
      if (!Number.isInteger(w) || w < 0 || w > 45) errors.push("weeks");
      else weeks = w;
    }
  }
  if (errors.length) return { ok: false, errors };
  const hh = f.household_id.trim();
  const metadata: Record<string, unknown> = {};
  const mergedSymptoms = [...new Set([...(f.initial_symptoms ?? []), ...parseCustomList(f.other_symptoms)])];
  if (mergedSymptoms.length > 0) metadata.initial_symptoms = mergedSymptoms;
  const notes = f.clinical_notes?.trim();
  if (notes) metadata.clinical_notes = notes;
  return {
    ok: true,
    patient: {
      patient_id: newId(),
      full_name: name,
      date_of_birth: dob,
      age_months: age,
      sex: f.sex,
      village_id: village,
      household_id: hh || null,
      is_pregnant: f.is_pregnant,
      gestational_weeks: weeks,
      preferred_language: f.preferred_language,
      registered_by_node: nodeId,
      metadata,
    },
  };
}
