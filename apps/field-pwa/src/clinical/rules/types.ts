/**
 * Structural types for the bundled clinical rule tables.
 *
 * Shapes mirror the JSON files in `packages/clinical-engine/rules/` (commit 53c61b2).
 * Values live in the sibling generated modules; never hand-edit them.
 */

import type { TriageSeverity } from "../../../../../packages/contracts/ts/index";

export interface FlagRule {
  id: string;
  flag: string;
  label: string;
  severity: TriageSeverity;
  immediate_actions: string[];
  rationale: string;
}

export interface SyndromeSymptomRule extends FlagRule {
  syndrome: string;
}

export interface ConditionRule {
  id: string;
  label: string;
  severity: TriageSeverity;
  condition?: string;
  immediate_actions: string[];
  rationale: string;
}

export interface ActionSet {
  red_actions: string[];
  yellow_actions: string[];
  green_actions: string[];
}

export interface ImnciPediatricRules {
  protocol_id: string;
  version: string;
  description: string;
  watch_tier0_danger_flags: string[];
  general_danger_signs: FlagRule[];
  young_infant_danger_signs?: FlagRule[];
  syndrome_symptom_rules?: SyndromeSymptomRule[];
  vital_thresholds: {
    spo2_critical_below_pct: number;
    spo2_borderline_below_pct: number;
    temp_hypothermia_below_c: number;
    temp_very_high_fever_c: number;
    temp_young_infant_fever_c: number;
    temp_moderate_fever_c: number;
    hb_severe_anemia_below_g_dl?: number;
    hb_moderate_anemia_below_g_dl?: number;
    fast_breathing_bpm_by_age_months: {
      min_months: number;
      max_months_exclusive: number;
      threshold_bpm: number;
    }[];
    muac_sam_below_cm: number;
    muac_mam_below_cm: number;
  };
  syndromes: {
    respiratory: {
      red_rules: ConditionRule[];
      yellow_rules: ConditionRule[];
      green_rule: ConditionRule;
    };
    diarrhea: ActionSet & {
      severe_dehydration_signs: string[];
      some_dehydration_signs: string[];
      min_signs_for_classification: number;
      persistent_diarrhea_days: number;
    };
    fever: ActionSet & { yellow_duration_days: number };
    malnutrition: ActionSet;
  };
}

export interface ChecklistItemDef {
  id: string;
  label: string;
  critical?: boolean;
  recommended_action: string;
  escalation_severity?: TriageSeverity;
}

export interface ChecklistDef {
  title: string;
  protocol: string;
  items: ChecklistItemDef[];
}

export interface MaternalAncRules {
  protocol_id: string;
  version: string;
  description: string;
  vital_thresholds: {
    bp_shock_systolic_below_mmhg?: number;
    bp_red_systolic_mmhg: number;
    bp_red_diastolic_mmhg: number;
    bp_severe_preeclampsia_systolic_mmhg: number;
    bp_severe_preeclampsia_diastolic_mmhg: number;
    bp_yellow_systolic_mmhg: number;
    bp_yellow_diastolic_mmhg: number;
    temp_red_fever_c: number;
    temp_postpartum_sepsis_c?: number;
    temp_yellow_fever_c: number;
    hb_severe_anemia_below_g_dl: number;
    hb_moderate_anemia_below_g_dl: number;
    spo2_critical_below_pct: number;
  };
  red_flag_symptoms: FlagRule[];
  yellow_flag_symptoms: FlagRule[];
  checklists: Record<string, ChecklistDef>;
}

export interface UipVaccineEntry {
  code: string;
  name: string;
  milestone: string;
  route?: string;
  due_age_days: number;
  due_soon_lead_days?: number;
  max_catchup_age_days?: number;
  schedule_group?: string;
  clinical_note?: string;
  aliases?: string[];
}

export interface MaternalVaccineEntry {
  code: string;
  name: string;
  milestone: string;
  due_gestational_weeks: number;
  due_soon_lead_days?: number;
  route?: string;
  schedule_group?: string;
  clinical_note?: string;
  aliases?: string[];
}

export interface UipVaccineRules {
  protocol_id: string;
  version: string;
  description: string;
  defaults: { due_soon_window_days: number };
  vaccines: UipVaccineEntry[];
  maternal_vaccines?: MaternalVaccineEntry[];
}
