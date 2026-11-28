/**
 * Pure form-state -> TriageInput mapping. No triage logic here: flags come only
 * from the canonical rule tables and the engine alone classifies severity.
 */
import { tx } from "../i18n";
import { IMNCI_PEDIATRIC_RULES, MATERNAL_ANC_RULES, validateTriageInput } from "../clinical";
import type { PatientCategory, TriageInput } from "../clinical";
import type { PatientSex } from "../../../../packages/contracts/ts/index";

export const FAST_EMERGENCY_FLAGS = ["lethargic_or_unconscious", "convulsions", "severe_breathing_difficulty", "vaginal_bleeding"] as const;

/** Display-only filter for the fast-emergency choices (omits vaginal bleeding for male patients); the engine remains the sole severity authority. */
export function fastEmergencyOptions(sex: PatientSex | null | undefined): string[] {
  return FAST_EMERGENCY_FLAGS.filter((f) => !(sex === "M" && f === "vaginal_bleeding"));
}

export interface FlagOption {
  flag: string;
  label: string;
}

/** Universal IMNCI general danger signs (apply to every patient category). */
export const pediatricDangerOptions = (): FlagOption[] =>
  IMNCI_PEDIATRIC_RULES.general_danger_signs.map(({ flag, label }) => ({ flag, label }));
export const maternalRedOptions = (): FlagOption[] =>
  MATERNAL_ANC_RULES.red_flag_symptoms.map(({ flag, label }) => ({ flag, label }));
export const maternalYellowOptions = (): FlagOption[] =>
  MATERNAL_ANC_RULES.yellow_flag_symptoms.map(({ flag, label }) => ({ flag, label }));

/** IMNCI danger signs that only make sense for a child (hidden for MATERNAL/GENERAL). */
export const PEDIATRIC_ONLY_DANGER_FLAGS: ReadonlySet<string> = new Set(["stridor_in_calm_child"]);

/** Danger-sign options shown for a category: all for PEDIATRIC, minus child-only signs otherwise. */
export function dangerOptionsForCategory(category: PatientCategory): FlagOption[] {
  const all = pediatricDangerOptions();
  return category === "PEDIATRIC" ? all : all.filter((o) => !PEDIATRIC_ONLY_DANGER_FLAGS.has(o.flag));
}

/** Dehydration signs from the diarrhoea table, minus those already shown as danger signs. */
export function dehydrationFlags(): string[] {
  const d = IMNCI_PEDIATRIC_RULES.syndromes.diarrhea;
  const danger = new Set(pediatricDangerOptions().map((o) => o.flag));
  return [...new Set([...d.severe_dehydration_signs, ...d.some_dehydration_signs])].filter((f) => !danger.has(f));
}

/** Ranges mirror validateTriageInput's NULLABLE_NUMS/COUNT_NUMS. */
export const VITAL_SPECS = {
  temperature_c: { min: 30, max: 45, integer: false, step: 0.1 },
  spo2_pct: { min: 0, max: 100, integer: true, step: 1 },
  respiratory_rate_bpm: { min: 0, max: 160, integer: true, step: 1 },
  systolic_bp: { min: 40, max: 300, integer: true, step: 1 },
  diastolic_bp: { min: 20, max: 200, integer: true, step: 1 },
  hemoglobin_g_dl: { min: 1, max: 25, integer: false, step: 0.1 },
  muac_cm: { min: 5, max: 50, integer: false, step: 0.1 },
  age_months: { min: 0, max: 1500, integer: true, step: 1 },
  gestational_weeks: { min: 0, max: 45, integer: true, step: 1 },
  fever_days: { min: 0, max: 365, integer: true, step: 1 },
  diarrhea_days: { min: 0, max: 365, integer: true, step: 1 },
} as const;
export type NumField = keyof typeof VITAL_SPECS;
export type TempUnit = "F" | "C";
export const TEMP_F_BOUNDS = { min: 86, max: 113, step: 0.1 } as const;

export const fahrenheitToCelsius = (f: number): number => Math.round((((f - 32) * 5) / 9) * 100) / 100;
export const celsiusToFahrenheit = (c: number): number => Math.round(((c * 9) / 5 + 32) * 10) / 10;

/** Convert a displayed temperature string when toggling between °F and °C. */
export function convertTempDisplay(raw: string, toUnit: TempUnit): string {
  const s = raw.trim();
  if (s === "") return "";
  const n = Number(s);
  if (!Number.isFinite(n)) return raw;
  return toUnit === "C" ? String(Math.round((((n - 32) * 5) / 9) * 10) / 10) : String(celsiusToFahrenheit(n));
}

export interface TriageFormState {
  /** null until the CHW (or a selected registered patient) chooses one: no silent default. */
  category: PatientCategory | null;
  patientId: string | null;
  /** Raw text of numeric inputs ("" = not measured). */
  nums: Partial<Record<NumField, string>>;
  /** Unit of `nums.temperature_c` when entered in the UI (defaults to "C" for legacy callers). */
  tempUnit?: TempUnit;
  /** Optional comma/newline-separated unlisted symptoms entered by the CHW. */
  additionalSymptoms?: string;
  isPregnant: boolean;
  isPostpartum: boolean;
  dangerFlags: string[];
  symptomFlags: string[];
  dehydrationFlags: string[];
  cough: boolean;
  chestIndrawing: boolean;
  diarrhea: boolean;
  bloodInStool: boolean;
  edema: boolean;
  pallor: boolean;
  malariaRdt: boolean;
}

export type NumError = { field: NumField; reason: "NaN" | "range" | "integer" };
export type BuildResult =
  | { ok: true; input: TriageInput }
  | { ok: false; errors: NumError[]; message?: string; needsCategory?: boolean; hiddenFlags?: string[] };

/**
 * Flags the form actually shows for a category. IMNCI danger signs appear in every
 * category except the child-only ones (PEDIATRIC_ONLY_DANGER_FLAGS), shown for PEDIATRIC only.
 */
export function visibleFlags(category: PatientCategory | null): Set<string> {
  const out = new Set<string>();
  if (category === null) return out;
  for (const o of dangerOptionsForCategory(category)) out.add(o.flag);
  if (category === "MATERNAL") {
    for (const o of [...maternalRedOptions(), ...maternalYellowOptions()]) out.add(o.flag);
  }
  if (category === "PEDIATRIC") for (const f of dehydrationFlags()) out.add(f);
  return out;
}

const allSelected = (s: TriageFormState) => [...s.dangerFlags, ...s.symptomFlags, ...s.dehydrationFlags];

/** Ticked flags the current category does not display. */
export const hiddenTickedFlags = (s: TriageFormState): string[] => {
  const vis = visibleFlags(s.category);
  return allSelected(s).filter((f) => !vis.has(f));
};

export function flagLabel(flag: string): string {
  const all = [...pediatricDangerOptions(), ...maternalRedOptions(), ...maternalYellowOptions()];
  const found = all.find((o) => o.flag === flag);
  if (found) return tx(`flag.${flag}`, found.label);
  return tx(`dehy.${flag}`, flag.replaceAll("_", " "));
}

/**
 * Switch category. Flags that stay visible are kept; flags that would become
 * hidden are removed AND returned so the UI can name them. Never leaves a
 * hidden flag in the state.
 */
export function applyCategory(s: TriageFormState, category: PatientCategory | null): { cleared: string[] } {
  s.category = category;
  const vis = visibleFlags(category);
  const cleared: string[] = [];
  for (const k of ["dangerFlags", "symptomFlags", "dehydrationFlags"] as const) {
    s[k] = s[k].filter((f) => (vis.has(f) ? true : (cleared.push(f), false)));
  }
  return { cleared: [...new Set(cleared)] };
}

/** Parse numeric text; returns undefined for blank, or an error. */
export function parseNum(field: NumField, raw: string | undefined): number | undefined | NumError {
  const s = (raw ?? "").trim();
  if (s === "") return undefined;
  const n = Number(s);
  const spec = VITAL_SPECS[field];
  if (!Number.isFinite(n)) return { field, reason: "NaN" };
  if (spec.integer && !Number.isInteger(n)) return { field, reason: "integer" };
  if (n < spec.min || n > spec.max) return { field, reason: "range" };
  return n;
}

/** Parse temperature text in `unit` (°F or °C), returning Celsius for `TriageInput`. */
export function parseTemp(raw: string | undefined, unit: TempUnit = "C"): number | undefined | NumError {
  if (unit === "C") return parseNum("temperature_c", raw);
  const s = (raw ?? "").trim();
  if (s === "") return undefined;
  const n = Number(s);
  if (!Number.isFinite(n)) return { field: "temperature_c", reason: "NaN" };
  if (n < TEMP_F_BOUNDS.min || n > TEMP_F_BOUNDS.max) return { field: "temperature_c", reason: "range" };
  return fahrenheitToCelsius(n);
}

/** Split comma/semicolon/newline-separated additional symptoms into unique trimmed entries. */
export function parseAdditionalSymptoms(raw: string | undefined): string[] {
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

export function buildTriageInput(s: TriageFormState, nowMs: number = Date.now()): BuildResult {
  if (s.category === null) return { ok: false, errors: [], needsCategory: true };
  const hidden = hiddenTickedFlags(s);
  if (hidden.length) return { ok: false, errors: [], hiddenFlags: hidden };
  const errors: NumError[] = [];
  const num = (f: NumField) => {
    const v = f === "temperature_c" ? parseTemp(s.nums[f], s.tempUnit ?? "C") : parseNum(f, s.nums[f]);
    if (v !== undefined && typeof v === "object") {
      errors.push(v);
      return undefined;
    }
    return v;
  };
  const mergedSymptoms = [...new Set([...s.symptomFlags, ...parseAdditionalSymptoms(s.additionalSymptoms)])];
  const input: TriageInput = {
    patient_id: s.patientId,
    mode: "FULL_ASSESSMENT",
    patient_category: s.category,
    assessed_at_ms: nowMs,
    danger_signs: [...s.dangerFlags],
    symptoms: mergedSymptoms,
  };
  const set = <K extends keyof TriageInput>(k: K, v: TriageInput[K] | undefined) => {
    if (v !== undefined) input[k] = v;
  };
  set("temperature_c", num("temperature_c"));
  set("spo2_pct", num("spo2_pct"));
  set("respiratory_rate_bpm", num("respiratory_rate_bpm"));
  set("systolic_bp", num("systolic_bp"));
  set("diastolic_bp", num("diastolic_bp"));
  set("hemoglobin_g_dl", num("hemoglobin_g_dl"));
  set("muac_cm", num("muac_cm"));
  set("age_months", num("age_months"));
  set("fever_days", num("fever_days"));

  if (s.category === "PEDIATRIC") {
    input.has_cough_or_difficult_breathing = s.cough;
    input.chest_indrawing = s.chestIndrawing;
    input.has_diarrhea = s.diarrhea;
    input.blood_in_stool = s.bloodInStool;
    input.bilateral_pedal_edema = s.edema;
    input.palmar_pallor = s.pallor;
    input.malaria_rdt_positive = s.malariaRdt;
    input.dehydration_signs = [...s.dehydrationFlags];
    set("diarrhea_days", num("diarrhea_days"));
  }
  if (s.category === "MATERNAL") {
    input.is_pregnant = s.isPregnant;
    input.is_postpartum = s.isPostpartum;
    if (s.isPregnant) set("gestational_weeks", num("gestational_weeks"));
  }
  if (errors.length) return { ok: false, errors };
  try {
    validateTriageInput(input); // backstop: engine remains the validation authority
  } catch (e) {
    return { ok: false, errors: [], message: e instanceof Error ? e.message : String(e) };
  }
  return { ok: true, input };
}

/** Suggest category from a registered patient. */
export function suggestCategory(p: { age_months: number | null; date_of_birth: string | null; is_pregnant: boolean }, asOf: Date = new Date()): PatientCategory {
  if (p.is_pregnant) return "MATERNAL";
  const m = patientAgeMonths(p, asOf);
  return m !== null && m < 60 ? "PEDIATRIC" : "GENERAL";
}

export function patientAgeMonths(
  p: { age_months: number | null; date_of_birth: string | null },
  asOf: Date = new Date(),
): number | null {
  if (p.date_of_birth) {
    const [y, mo, d] = p.date_of_birth.split("-").map(Number);
    if (!y || !mo || !d) return p.age_months;
    let m = (asOf.getFullYear() - y) * 12 + (asOf.getMonth() + 1 - mo);
    if (asOf.getDate() < d) m -= 1;
    return Math.max(0, m);
  }
  return p.age_months;
}
