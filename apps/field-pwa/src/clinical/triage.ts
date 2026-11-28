/**
 * Offline deterministic clinical triage (WHO IMNCI, NHM ASHA, Watch Tier-0).
 *
 * Faithful port of `packages/clinical-engine/src/aarogya_clinical_engine/triage.py`
 * (commit 53c61b2). Do not invent rules here: change the Python engine first, then
 * re-port and regenerate parity fixtures.
 *
 * Safety invariant: ANY single general danger sign or maternal red flag forces
 * RED_EMERGENCY with referral_required=true, confidence=1.0, LOCAL_DETERMINISTIC.
 */

import type {
  ActionCard,
  ActionCardPriority,
  NodeTier,
  TriageAssessment,
  TriageSeverity,
  WatchMode,
} from "../../../../packages/contracts/ts/index";
import { IMNCI_PEDIATRIC_RULES } from "./rules/imnci_pediatric";
import { MATERNAL_ANC_RULES } from "./rules/maternal_anc";
import type { ImnciPediatricRules, MaternalAncRules } from "./rules/types";
import { normalizeFlag, validateTriageInput } from "./triage_input";
import type { PatientCategory, TriageInput } from "./triage_input";
import { dedupePreserveOrder, pyFixed1, pyStr } from "./pyfmt";
import { uuid } from "../core/uuid";

export { FLAG_ALIASES, normalizeFlag, validateTriageInput } from "./triage_input";
export type { PatientCategory, TriageInput, TriageMode } from "./triage_input";

const SEVERITY_RANK: Record<TriageSeverity, number> = {
  GREEN_HOME: 0,
  YELLOW_PHC: 1,
  RED_EMERGENCY: 2,
};

type Data = Required<TriageInput>;

function normalizeFlagSet(flags: readonly string[]): Set<string> {
  const out = new Set<string>();
  for (const f of flags) if (f && f.trim()) out.add(normalizeFlag(f));
  return out;
}

function union(a: Set<string>, b: Set<string>): Set<string> {
  return new Set([...a, ...b]);
}

function inferCategory(d: Data): PatientCategory {
  if (d.patient_category !== null) return d.patient_category;
  if (d.is_pregnant || d.is_postpartum || d.gestational_weeks !== null) return "MATERNAL";
  if (d.age_months !== null && d.age_months < 60) return "PEDIATRIC";
  return "GENERAL";
}

function fastBreathingThreshold(ageMonths: number | null, imnci: ImnciPediatricRules): number {
  const age = ageMonths === null ? 12 : ageMonths;
  for (const band of imnci.vital_thresholds.fast_breathing_bpm_by_age_months) {
    if (band.min_months <= age && age < band.max_months_exclusive) return Math.trunc(band.threshold_bpm);
  }
  return 40;
}

/** Internal monotonic severity accumulator: severity can only go up. */
class Accumulator {
  severity: TriageSeverity = "GREEN_HOME";
  matchedRules: string[] = [];
  actions: string[] = [];
  rationales: string[] = [];

  record(ruleId: string, severity: TriageSeverity, actions: readonly string[], rationale: string): void {
    if (SEVERITY_RANK[severity] > SEVERITY_RANK[this.severity]) this.severity = severity;
    this.matchedRules.push(ruleId);
    this.actions.push(...actions);
    this.rationales.push(rationale);
  }
}

function applyUniversalDangerSigns(
  flags: Set<string>,
  imnci: ImnciPediatricRules,
  maternal: MaternalAncRules,
  category: PatientCategory,
  acc: Accumulator,
  includeMaternalInRapid: boolean,
): void {
  for (const rule of imnci.general_danger_signs) {
    if (flags.has(rule.flag)) acc.record(rule.id, "RED_EMERGENCY", rule.immediate_actions, rule.rationale);
  }
  if (category === "MATERNAL" || includeMaternalInRapid) {
    for (const rule of maternal.red_flag_symptoms) {
      if (flags.has(rule.flag)) {
        acc.record(rule.id, "RED_EMERGENCY", rule.immediate_actions, rule.rationale);
      } else if (rule.flag === "convulsions_or_fits" && flags.has("convulsions")) {
        acc.record(rule.id, "RED_EMERGENCY", rule.immediate_actions, rule.rationale);
      }
    }
  }
}

function evaluateMaternal(d: Data, flags: Set<string>, maternal: MaternalAncRules, acc: Accumulator): void {
  const vt = maternal.vital_thresholds;
  const sys = d.systolic_bp;
  const dia = d.diastolic_bp;
  const bp = `${pyStr(sys)}/${pyStr(dia)}`;
  const atLeast = (v: number | null, t: number) => v !== null && v >= t;

  if (sys !== null && sys < (vt.bp_shock_systolic_below_mmhg ?? 90)) {
    acc.record(
      "MAT_BP_SHOCK_RED",
      "RED_EMERGENCY",
      [
        "Immediate 108 emergency transfer to FRU/District Hospital with blood bank (suspected hemorrhagic or septic shock)",
        "Keep mother flat on left lateral side with legs elevated and keep warm during transport",
      ],
      `Maternal hypotension (Systolic BP ${sys} mmHg < 90 mmHg) indicates obstetric hemorrhagic or septic shock.`,
    );
  } else if (atLeast(sys, vt.bp_severe_preeclampsia_systolic_mmhg) || atLeast(dia, vt.bp_severe_preeclampsia_diastolic_mmhg)) {
    acc.record(
      "MAT_BP_SEVERE_PREECLAMPSIA",
      "RED_EMERGENCY",
      [
        "Immediate 108 emergency referral to FRU/District Hospital for Severe Pre-eclampsia",
        "Keep mother on left lateral side; monitor for convulsions, headache, or blurred vision",
      ],
      `Critical maternal hypertension (${bp} mmHg >= 160/110): severe pre-eclampsia emergency.`,
    );
  } else if (atLeast(sys, vt.bp_red_systolic_mmhg) || atLeast(dia, vt.bp_red_diastolic_mmhg)) {
    const hasNeuro = flags.has("severe_headache_or_blurred_vision") || flags.has("swelling_face_and_hands");
    acc.record(
      hasNeuro ? "MAT_PREECLAMPSIA_SYMPTOMATIC_RED" : "MAT_BP_PREECLAMPSIA_RED",
      "RED_EMERGENCY",
      [
        "Urgent referral to FRU/PHC for pre-eclampsia evaluation and urine protein check (call 108/102)",
        "Advise left-lateral rest; do not delay transfer if headache or visual changes are present",
      ],
      `Elevated maternal BP (${bp} mmHg >= 140/90) meets NHM ASHA pre-eclampsia red-flag threshold.`,
    );
  } else if (atLeast(sys, vt.bp_yellow_systolic_mmhg) || atLeast(dia, vt.bp_yellow_diastolic_mmhg)) {
    acc.record(
      "MAT_BP_BORDERLINE_YELLOW",
      "YELLOW_PHC",
      [
        "Re-check BP at PHC/ANM within 24-48 hours and test urine albumin",
        "Counsel mother on pre-eclampsia danger signs (headache, blurred vision, sudden swelling)",
      ],
      `Borderline elevated maternal BP (${bp} mmHg) requires close PHC monitoring.`,
    );
  }

  if (d.temperature_c !== null) {
    const t = pyFixed1(d.temperature_c);
    if (d.is_postpartum && d.temperature_c >= (vt.temp_postpartum_sepsis_c ?? 38.0)) {
      acc.record(
        "MAT_PUERPERAL_SEPSIS_FEVER_RED",
        "RED_EMERGENCY",
        [
          "Immediate referral to FRU/District Hospital for suspected puerperal sepsis (parenteral antibiotics)",
          "Assess lochia odor, uterine tenderness, and BP; encourage hydration if conscious",
        ],
        `Postpartum maternal temperature ${t}C >= 38.0C indicates high puerperal sepsis risk.`,
      );
    } else if (d.temperature_c >= vt.temp_red_fever_c) {
      acc.record(
        "MAT_FEVER_HIGH_RED",
        "RED_EMERGENCY",
        [
          "Urgent referral to FRU/PHC for suspected maternal sepsis or obstetric infection",
          "Provide oral fluids and paracetamol if able to swallow during transport",
        ],
        `Maternal temperature ${t}C >= 38.5C indicates high sepsis risk.`,
      );
    } else if (d.temperature_c >= vt.temp_yellow_fever_c) {
      acc.record(
        "MAT_FEVER_MILD_YELLOW",
        "YELLOW_PHC",
        [
          "Refer to PHC/ANM within 24 hours for fever workup (malaria/UTI/infection)",
          "Encourage safe hydration and monitor temperature",
        ],
        `Maternal temperature ${t}C requires timely clinical review.`,
      );
    }
  }

  if (d.hemoglobin_g_dl !== null) {
    const hb = pyFixed1(d.hemoglobin_g_dl);
    if (d.hemoglobin_g_dl < vt.hb_severe_anemia_below_g_dl) {
      acc.record(
        "MAT_ANEMIA_SEVERE_RED",
        "RED_EMERGENCY",
        [
          "Urgent referral to FRU/CHC for severe anemia management (IV iron / transfusion evaluation)",
          "Register as High-Risk Pregnancy (HRP) and avoid physical exertion",
        ],
        `Hemoglobin ${hb} g/dL < 7.0 g/dL defines severe maternal anemia.`,
      );
    } else if (d.hemoglobin_g_dl < vt.hb_moderate_anemia_below_g_dl) {
      acc.record(
        "MAT_ANEMIA_MODERATE_YELLOW",
        "YELLOW_PHC",
        [
          "Refer to PHC/ANM for therapeutic IFA dosing (2 tablets/day) and follow-up Hb check",
          "Counsel on iron-rich indigenous foods and taking IFA separately from tea/calcium",
        ],
        `Hemoglobin ${hb} g/dL indicates moderate maternal anemia.`,
      );
    }
  }

  if (d.spo2_pct !== null && d.spo2_pct < vt.spo2_critical_below_pct) {
    acc.record(
      "MAT_SPO2_CRITICAL_RED",
      "RED_EMERGENCY",
      ["Immediate 108 emergency transfer to oxygen-equipped FRU", "Seat mother upright and monitor breathing continuously"],
      `Maternal SpO2 ${d.spo2_pct}% < 92% indicates acute hypoxemia.`,
    );
  }

  for (const rule of maternal.yellow_flag_symptoms) {
    if (flags.has(rule.flag)) acc.record(rule.id, "YELLOW_PHC", rule.immediate_actions, rule.rationale);
  }
}

function evaluatePediatric(d: Data, flags: Set<string>, imnci: ImnciPediatricRules, acc: Accumulator): void {
  const vt = imnci.vital_thresholds;
  const syn = imnci.syndromes;
  const isYoungInfant = d.age_months !== null && d.age_months < 2;

  // Young Infant (<2 months) PSBI danger signs
  if (isYoungInfant || d.age_months === null) {
    for (const rule of imnci.young_infant_danger_signs ?? []) {
      if (flags.has(rule.flag)) acc.record(rule.id, "RED_EMERGENCY", rule.immediate_actions, rule.rationale);
    }
  }

  // Expanded WHO IMNCI pediatric syndrome symptom rules
  for (const rule of imnci.syndrome_symptom_rules ?? []) {
    if (flags.has(rule.flag)) acc.record(rule.id, rule.severity, rule.immediate_actions, rule.rationale);
  }

  if (d.spo2_pct !== null) {
    if (d.spo2_pct < vt.spo2_critical_below_pct) {
      const r = syn.respiratory.red_rules[0];
      acc.record(r.id, "RED_EMERGENCY", r.immediate_actions, `SpO2 ${d.spo2_pct}% < 90%: ${r.rationale}`);
    } else if (d.spo2_pct < vt.spo2_borderline_below_pct) {
      const r = syn.respiratory.yellow_rules[1];
      acc.record(r.id, "YELLOW_PHC", r.immediate_actions, `SpO2 ${d.spo2_pct}% (90-93%): ${r.rationale}`);
    }
  }

  if (d.temperature_c !== null) {
    const t = pyFixed1(d.temperature_c);
    if (d.temperature_c < vt.temp_hypothermia_below_c) {
      acc.record(
        "IMNCI_VITAL_HYPOTHERMIA_RED",
        "RED_EMERGENCY",
        [
          "Rewarm immediately with skin-to-skin Kangaroo Mother Care and dry warm blankets",
          "Urgent referral to FRU/SNCU (call 108)",
        ],
        `Hypothermia (${t}C < 35.5C) indicates critical neonatal/pediatric illness.`,
      );
    } else if (d.temperature_c >= vt.temp_very_high_fever_c) {
      acc.record(
        "IMNCI_FEVER_HYPERPYREXIA_RED",
        "RED_EMERGENCY",
        syn.fever.red_actions,
        `Hyperpyrexia (${t}C >= 39.5C) requires urgent hospital evaluation.`,
      );
    } else if (isYoungInfant && d.temperature_c >= vt.temp_young_infant_fever_c) {
      acc.record(
        "IMNCI_YOUNG_INFANT_FEVER_RED",
        "RED_EMERGENCY",
        [
          "Urgent referral to SNCU/FRU immediately (suspected neonatal sepsis)",
          "Keep infant breastfeeding if able and prevent chilling during transport",
        ],
        `Fever (${t}C >= 37.5C) in young infant <2 months is a WHO IMNCI emergency.`,
      );
    } else if (d.temperature_c >= vt.temp_moderate_fever_c) {
      acc.record(
        "IMNCI_FEVER_MODERATE_YELLOW",
        "YELLOW_PHC",
        syn.fever.yellow_actions,
        `Fever (${t}C >= 38.0C) requires PHC/ANM evaluation and malaria RDT.`,
      );
    }
  }

  // Respiratory syndrome (WHO IMNCI cough / difficult breathing)
  const rrThreshold = fastBreathingThreshold(d.age_months, imnci);
  const fastBreathing = d.respiratory_rate_bpm !== null && d.respiratory_rate_bpm >= rrThreshold;
  if (isYoungInfant && (fastBreathing || d.chest_indrawing)) {
    const r = syn.respiratory.red_rules[1];
    const detail = fastBreathing
      ? `Young infant (<2m) respiratory rate ${pyStr(d.respiratory_rate_bpm)}/min >= ${rrThreshold}/min`
      : "Young infant (<2m) severe chest indrawing";
    acc.record(r.id, "RED_EMERGENCY", r.immediate_actions, `${detail}: ${r.rationale}`);
  } else if (fastBreathing || d.chest_indrawing) {
    const r = syn.respiratory.yellow_rules[0];
    const detail = fastBreathing
      ? `Respiratory rate ${pyStr(d.respiratory_rate_bpm)}/min >= ${rrThreshold}/min`
      : "Lower chest wall indrawing observed";
    acc.record(r.id, "YELLOW_PHC", r.immediate_actions, `${detail}: ${r.rationale}`);
  } else if (d.has_cough_or_difficult_breathing) {
    const r = syn.respiratory.green_rule;
    acc.record(r.id, "GREEN_HOME", r.immediate_actions, r.rationale);
  }

  // Diarrhea & dehydration syndrome (WHO IMNCI)
  const dehydrationFlags = union(normalizeFlagSet(d.dehydration_signs), flags);
  const diarrheaPresent = d.has_diarrhea || d.diarrhea_days > 0 || d.blood_in_stool || d.dehydration_signs.length > 0;
  if (diarrheaPresent) {
    const cfg = syn.diarrhea;
    const minSigns = Math.trunc(cfg.min_signs_for_classification);
    const severeHits = [...new Set(cfg.severe_dehydration_signs)].filter((s) => dehydrationFlags.has(s)).sort();
    const someHits = [...new Set(cfg.some_dehydration_signs)].filter((s) => dehydrationFlags.has(s)).sort();
    const persistent = d.diarrhea_days >= Math.trunc(cfg.persistent_diarrhea_days);

    if (severeHits.length >= minSigns) {
      acc.record(
        "IMNCI_DIARRHEA_SEVERE_DEHYDRATION_RED",
        "RED_EMERGENCY",
        cfg.red_actions,
        `Severe dehydration (${severeHits.length} WHO IMNCI signs: ${severeHits.join(", ")}).`,
      );
    } else if (persistent && someHits.length >= minSigns) {
      acc.record(
        "IMNCI_DIARRHEA_SEVERE_PERSISTENT_RED",
        "RED_EMERGENCY",
        cfg.red_actions,
        `Severe persistent diarrhea (${d.diarrhea_days} days with dehydration).`,
      );
    } else {
      let matchedYellow = false;
      if (someHits.length >= minSigns) {
        acc.record(
          "IMNCI_DIARRHEA_SOME_DEHYDRATION_YELLOW",
          "YELLOW_PHC",
          cfg.yellow_actions,
          `Some dehydration (${someHits.length} WHO IMNCI signs: ${someHits.join(", ")}).`,
        );
        matchedYellow = true;
      }
      if (d.blood_in_stool) {
        acc.record(
          "IMNCI_DIARRHEA_DYSENTERY_YELLOW",
          "YELLOW_PHC",
          cfg.yellow_actions,
          "Blood in stool (Dysentery) requires PHC/ANM antibiotic evaluation and Zinc/ORS.",
        );
        matchedYellow = true;
      }
      if (persistent) {
        acc.record(
          "IMNCI_DIARRHEA_PERSISTENT_YELLOW",
          "YELLOW_PHC",
          cfg.yellow_actions,
          `Persistent diarrhea (${d.diarrhea_days} days >= 14 days) requires PHC follow-up.`,
        );
        matchedYellow = true;
      }
      if (!matchedYellow) {
        acc.record(
          "IMNCI_DIARRHEA_NO_DEHYDRATION_GREEN",
          "GREEN_HOME",
          cfg.green_actions,
          "Acute diarrhea with no dehydration signs: safe for ORS Plan A and Zinc at home.",
        );
      }
    }
  }

  // Fever duration / malaria RDT
  const fever = syn.fever;
  if (d.malaria_rdt_positive) {
    acc.record(
      "IMNCI_FEVER_MALARIA_POSITIVE_YELLOW",
      "YELLOW_PHC",
      fever.yellow_actions,
      "Positive Malaria RDT requires immediate antimalarial protocol at PHC/ANM.",
    );
  } else if (d.fever_days >= Math.trunc(fever.yellow_duration_days)) {
    acc.record(
      "IMNCI_FEVER_PROLONGED_YELLOW",
      "YELLOW_PHC",
      fever.yellow_actions,
      `Fever persisting for ${d.fever_days} days (>=3 days) requires PHC clinical workup.`,
    );
  } else if (d.fever_days > 0 && (d.temperature_c === null || d.temperature_c < vt.temp_moderate_fever_c)) {
    acc.record(
      "IMNCI_FEVER_LOW_GRADE_GREEN",
      "GREEN_HOME",
      fever.green_actions,
      "Short-duration uncomplicated low-grade fever: home supportive care with close monitoring.",
    );
  }

  // Malnutrition & anemia
  const mal = syn.malnutrition;
  if (d.bilateral_pedal_edema || (d.muac_cm !== null && d.muac_cm < vt.muac_sam_below_cm)) {
    const reason = d.bilateral_pedal_edema
      ? "Bilateral pitting pedal edema (Kwashiorkor/SAM)"
      : `MUAC ${pyFixed1(d.muac_cm as number)} cm < 11.5 cm (Severe Acute Malnutrition)`;
    acc.record("IMNCI_MALNUTRITION_SAM_RED", "RED_EMERGENCY", mal.red_actions, `${reason}: urgent NRC/PHC referral required.`);
  } else if (d.muac_cm !== null && d.muac_cm < vt.muac_mam_below_cm) {
    acc.record(
      "IMNCI_MALNUTRITION_MAM_YELLOW",
      "YELLOW_PHC",
      mal.yellow_actions,
      `MUAC ${pyFixed1(d.muac_cm)} cm (11.5-12.4 cm): Moderate Acute Malnutrition requires PHC/AWC nutrition support.`,
    );
  }
  if (d.palmar_pallor) {
    acc.record(
      "IMNCI_ANEMIA_PALMAR_PALLOR_YELLOW",
      "YELLOW_PHC",
      mal.yellow_actions,
      "Palmar pallor detected: refer to PHC/ANM for anemia assessment and IFA/deworming.",
    );
  }

  if (d.hemoglobin_g_dl !== null) {
    const hb = pyFixed1(d.hemoglobin_g_dl);
    if (d.hemoglobin_g_dl < (vt.hb_severe_anemia_below_g_dl ?? 7.0)) {
      acc.record(
        "IMNCI_ANEMIA_SEVERE_HB_RED",
        "RED_EMERGENCY",
        [
          "Urgent referral to FRU/District Hospital for severe pediatric anemia (transfusion evaluation)",
          "Keep child calm and prevent hypoxia during transport",
        ],
        `Pediatric hemoglobin ${hb} g/dL < 7.0 g/dL defines severe anemia.`,
      );
    } else if (d.hemoglobin_g_dl < (vt.hb_moderate_anemia_below_g_dl ?? 11.0)) {
      acc.record(
        "IMNCI_ANEMIA_MODERATE_HB_YELLOW",
        "YELLOW_PHC",
        mal.yellow_actions,
        `Pediatric hemoglobin ${hb} g/dL (<11.0 g/dL) indicates mild/moderate anemia requiring IFA syrup and PHC follow-up.`,
      );
    }
  }
}

function evaluateGeneral(d: Data, acc: Accumulator): void {
  if (d.spo2_pct !== null) {
    if (d.spo2_pct < 90) {
      acc.record(
        "GEN_SPO2_CRITICAL_RED",
        "RED_EMERGENCY",
        ["Urgent referral to oxygen-equipped PHC/FRU (call 108)"],
        `SpO2 ${d.spo2_pct}% < 90% indicates critical hypoxemia.`,
      );
    } else if (d.spo2_pct < 94) {
      acc.record(
        "GEN_SPO2_BORDERLINE_YELLOW",
        "YELLOW_PHC",
        ["Refer to PHC today for pulse oximetry re-check and respiratory evaluation"],
        `SpO2 ${d.spo2_pct}% (90-93%) warrants clinical review.`,
      );
    }
  }

  if (d.temperature_c !== null) {
    const t = pyFixed1(d.temperature_c);
    if (d.temperature_c >= 39.5 || d.temperature_c < 35.5) {
      acc.record("GEN_TEMP_CRITICAL_RED", "RED_EMERGENCY", ["Urgent referral to PHC/FRU immediately"], `Critical body temperature (${t}C).`);
    } else if (d.temperature_c >= 38.0) {
      acc.record(
        "GEN_FEVER_MODERATE_YELLOW",
        "YELLOW_PHC",
        ["Refer to PHC/ANM for fever evaluation and malaria/dengue testing"],
        `Moderate fever (${t}C) warrants PHC assessment.`,
      );
    }
  }

  if (d.systolic_bp !== null || d.diastolic_bp !== null) {
    const sys = d.systolic_bp || 0;
    const dia = d.diastolic_bp || 0;
    const bp = `${pyStr(d.systolic_bp)}/${pyStr(d.diastolic_bp)}`;
    if (sys >= 180 || dia >= 120 || (d.systolic_bp !== null && d.systolic_bp < 90)) {
      acc.record(
        "GEN_BP_CRISIS_RED",
        "RED_EMERGENCY",
        ["Immediate emergency referral to FRU/Hospital (call 108)"],
        `Critical blood pressure (${bp} mmHg).`,
      );
    } else if (sys >= 140 || dia >= 90) {
      acc.record(
        "GEN_BP_ELEVATED_YELLOW",
        "YELLOW_PHC",
        ["Refer to PHC NCD clinic for hypertension confirmation and management"],
        `Elevated blood pressure (${bp} mmHg >= 140/90).`,
      );
    }
  }
}

/**
 * Execute deterministic clinical triage fully offline and return a contract-valid
 * `TriageAssessment`. Throws on invalid input (mirrors pydantic validation).
 */
export function evaluateTriage(input: TriageInput): TriageAssessment {
  const d = validateTriageInput(input);
  const imnci = IMNCI_PEDIATRIC_RULES;
  const maternal = MATERNAL_ANC_RULES;
  const category = inferCategory(d);
  const allFlags = union(normalizeFlagSet(d.danger_signs), normalizeFlagSet(d.symptoms));
  const acc = new Accumulator();

  // Step 1: hard safety floor. ANY danger sign forces RED_EMERGENCY.
  const isWatchRapid = d.mode === "WATCH_RAPID";
  applyUniversalDangerSigns(allFlags, imnci, maternal, category, acc, isWatchRapid);

  // Step 2: mode-specific evaluation.
  let protocolSource: string;
  if (isWatchRapid) {
    if (category === "MATERNAL") {
      evaluateMaternal(d, allFlags, maternal, acc);
    } else {
      if (d.spo2_pct !== null && d.spo2_pct < 90) {
        acc.record(
          "WATCH_SPO2_CRITICAL_RED",
          "RED_EMERGENCY",
          ["Immediate 108 emergency transfer to oxygen-equipped FRU/PHC"],
          `Watch rapid screen: SpO2 ${d.spo2_pct}% < 90% critical hypoxemia.`,
        );
      }
      if (d.temperature_c !== null && (d.temperature_c >= 39.5 || d.temperature_c < 35.5)) {
        acc.record(
          "WATCH_TEMP_CRITICAL_RED",
          "RED_EMERGENCY",
          ["Urgent referral to PHC/FRU immediately"],
          `Watch rapid screen: critical temperature ${pyFixed1(d.temperature_c)}C.`,
        );
      }
    }
    protocolSource = "WHO_IMNCI_ASHA_WATCH_RAPID";
  } else if (category === "MATERNAL") {
    evaluateMaternal(d, allFlags, maternal, acc);
    protocolSource = "NHM_ASHA_MATERNAL_DETERMINISTIC";
  } else if (category === "PEDIATRIC") {
    evaluatePediatric(d, allFlags, imnci, acc);
    protocolSource = "WHO_IMNCI_PEDIATRIC_DETERMINISTIC";
  } else {
    evaluateGeneral(d, acc);
    protocolSource = "WHO_IMNCI_ASHA_DETERMINISTIC";
  }

  // Step 3: default GREEN_HOME when nothing matched.
  if (acc.matchedRules.length === 0) {
    acc.record(
      isWatchRapid ? "WATCH_RAPID_NO_DANGER_SIGNS" : "CLINICAL_ROUTINE_GREEN",
      "GREEN_HOME",
      [
        isWatchRapid
          ? "No immediate danger signs detected on Watch screen. Continue monitoring or run full Phone assessment if symptoms persist."
          : "No danger signs or urgent criteria detected. Continue home supportive care, hydration, and routine ASHA follow-up.",
      ],
      "All screened danger signs and clinical criteria are within home-care thresholds.",
    );
  }

  return {
    assessment_id: uuid(),
    patient_id: d.patient_id,
    severity: acc.severity,
    matched_rules: dedupePreserveOrder(acc.matchedRules),
    immediate_actions: dedupePreserveOrder(acc.actions),
    referral_required: acc.severity === "RED_EMERGENCY" || acc.severity === "YELLOW_PHC",
    rationale: dedupePreserveOrder(acc.rationales).join(" "),
    confidence: 1.0,
    protocol_source: protocolSource,
    execution_target: "LOCAL_DETERMINISTIC",
    assessed_at_ms: d.assessed_at_ms,
  };
}

/** Convenience entrypoint for Tier-0 Watch 1-tap danger-sign screening. */
export function evaluateWatchRapidTriage(
  dangerSigns: readonly string[],
  opts: Pick<
    TriageInput,
    "patient_id" | "is_pregnant" | "spo2_pct" | "temperature_c" | "systolic_bp" | "diastolic_bp" | "assessed_at_ms"
  > = {},
): TriageAssessment {
  return evaluateTriage({ ...opts, mode: "WATCH_RAPID", danger_signs: [...dangerSigns] });
}

const PRIORITY_MAP: Record<TriageSeverity, ActionCardPriority> = {
  RED_EMERGENCY: "CRITICAL",
  YELLOW_PHC: "HIGH",
  GREEN_HOME: "LOW",
};

const TITLE_MAP: Record<TriageSeverity, string> = {
  RED_EMERGENCY: "RED EMERGENCY: Immediate Referral",
  YELLOW_PHC: "YELLOW: PHC / ANM Visit Required",
  GREEN_HOME: "GREEN: Home Care & Follow-Up",
};

/** Convert a deterministic `TriageAssessment` into a glanceable `ActionCard`. */
export function triageToActionCard(
  assessment: TriageAssessment,
  opts: { target_tier?: NodeTier; watch_mode?: WatchMode | null; source_event_id?: string | null } = {},
): ActionCard {
  const targetTier = opts.target_tier ?? "TIER_0_WATCH";
  const watchMode = opts.watch_mode === undefined ? "CHW_COMPANION" : opts.watch_mode;
  return {
    card_id: uuid(),
    patient_id: assessment.patient_id,
    title: TITLE_MAP[assessment.severity],
    summary: assessment.rationale.slice(0, 1000),
    action_steps: [...assessment.immediate_actions],
    priority: PRIORITY_MAP[assessment.severity],
    severity: assessment.severity,
    status: "OPEN",
    target_tier: targetTier,
    watch_mode: targetTier === "TIER_0_WATCH" ? watchMode : null,
    source_event_id: opts.source_event_id ?? null,
    due_by: null,
    language: "en",
  };
}
