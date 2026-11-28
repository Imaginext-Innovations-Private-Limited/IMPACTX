"""Deterministic offline clinical triage engine (WHO IMNCI, NHM ASHA, Watch Tier-0).

Safety Invariant:
    Any single general danger sign or maternal emergency red flag MUST immediately
    force ``TriageSeverity.RED_EMERGENCY`` and ``referral_required = True`` with
    ``confidence = 1.0`` and ``execution_target = ExecutionTarget.LOCAL_DETERMINISTIC``.
"""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aarogya_clinical_engine.rules_loader import load_imnci_rules, load_maternal_anc_rules
from aarogya_contracts import (
    ActionCard,
    ActionCardPriority,
    ExecutionTarget,
    NodeTier,
    TriageAssessment,
    TriageSeverity,
    WatchMode,
)

_SEVERITY_RANK: dict[TriageSeverity, int] = {
    TriageSeverity.GREEN_HOME: 0,
    TriageSeverity.YELLOW_PHC: 1,
    TriageSeverity.RED_EMERGENCY: 2,
}

_FLAG_ALIASES: dict[str, str] = {
    "unable_to_drink": "not_able_to_drink_or_breastfeed",
    "unable_to_drink_or_breastfeed": "not_able_to_drink_or_breastfeed",
    "cannot_drink": "not_able_to_drink_or_breastfeed",
    "cannot_breastfeed": "not_able_to_drink_or_breastfeed",
    "vomiting_everything": "vomits_everything",
    "persistent_vomiting_all": "vomits_everything",
    "seizures": "convulsions",
    "fits": "convulsions",
    "lethargic": "lethargic_or_unconscious",
    "unconscious": "lethargic_or_unconscious",
    "abnormally_sleepy": "lethargic_or_unconscious",
    "severe_chest_indrawing": "severe_breathing_difficulty",
    "gasping": "severe_breathing_difficulty",
    "bluish_lips": "cyanosis",
    "central_cyanosis": "cyanosis",
    "stridor": "stridor_in_calm_child",
    "bulging_fontanelle": "stiff_neck",
    "severe_headache": "severe_headache_or_blurred_vision",
    "blurred_vision": "severe_headache_or_blurred_vision",
    "visual_disturbance": "severe_headache_or_blurred_vision",
    "eclampsia": "convulsions_or_fits",
    "pph": "vaginal_bleeding",
    "antepartum_bleeding": "vaginal_bleeding",
    "postpartum_bleeding": "vaginal_bleeding",
    "absent_fetal_movement": "reduced_fetal_movement",
    "decreased_fetal_movement": "reduced_fetal_movement",
    "reduced_or_absent_fetal_movement": "reduced_fetal_movement",
    "prom": "leaking_fluid_before_labor",
    "water_breaking": "leaking_fluid_before_labor",
    "epigastric_pain": "severe_abdominal_pain",
    "severe_pallor": "severe_anemia_signs",
    "facial_swelling": "swelling_face_and_hands",
    "chest_pain": "breathing_difficulty_or_chest_pain",
    # Young infant (<2m PSBI) aliases
    "umbilical_pus": "umbilicus_red_or_draining_pus",
    "umbilical_redness": "umbilicus_red_or_draining_pus",
    "omphalitis": "umbilicus_red_or_draining_pus",
    "skin_pustules": "skin_pustules_many_or_severe",
    "neonatal_pustules": "skin_pustules_many_or_severe",
    "poor_feeding": "poor_feeding_or_weak_cry",
    "weak_cry": "poor_feeding_or_weak_cry",
    "stopped_feeding": "poor_feeding_or_weak_cry",
    "yellow_palms_soles": "jaundice_palms_or_soles",
    "neonatal_jaundice_severe": "jaundice_palms_or_soles",
    "grunting": "grunting_or_apnea",
    "apnea": "grunting_or_apnea",
    "no_spontaneous_movement": "movement_only_when_stimulated",
    # Expanded pediatric syndrome aliases
    "mastoiditis": "mastoiditis_tender_swelling_behind_ear",
    "swelling_behind_ear": "mastoiditis_tender_swelling_behind_ear",
    "ear_pain": "acute_ear_pain_or_discharge",
    "ear_discharge": "acute_ear_pain_or_discharge",
    "chronic_ear_infection": "chronic_ear_discharge",
    "measles_complications": "measles_eye_or_mouth_complications",
    "corneal_clouding": "measles_eye_or_mouth_complications",
    "measles": "measles_uncomplicated_rash",
    "measles_rash": "measles_uncomplicated_rash",
    "dengue_hemorrhagic": "dengue_warning_signs",
    "petechial_rash": "dengue_warning_signs",
    "severe_malaria": "severe_malaria_signs",
    "dark_urine": "severe_malaria_signs",
    "failed_appetite_test": "failed_appetite_test_sam",
    "severe_anemia_pediatric": "severe_palmar_pallor",
    "severe_wasting": "visible_severe_wasting",
    # Expanded maternal / PMSMA HRP & postpartum aliases
    "puerperal_sepsis": "puerperal_sepsis_signs",
    "foul_lochia": "puerperal_sepsis_signs",
    "scar_tenderness": "previous_lscs_scar_tenderness",
    "lscs_scar_pain": "previous_lscs_scar_tenderness",
    "hyperemesis_gravidarum": "hyperemesis_gravidarum_severe",
    "postpartum_hemorrhage": "postpartum_hemorrhage_heavy",
    "heavy_postpartum_bleeding": "postpartum_hemorrhage_heavy",
    "antepartum_hemorrhage": "antepartum_hemorrhage_painful_or_painless",
    "obstructed_labor": "obstructed_or_prolonged_labor",
    "prolonged_labor": "obstructed_or_prolonged_labor",
    "gdm": "gestational_diabetes_gdm",
    "gestational_diabetes": "gestational_diabetes_gdm",
    "rh_negative": "rh_negative_mother",
    "rh_sensitization": "rh_negative_mother",
    "twins": "twin_or_multiple_gestation",
    "multiple_pregnancy": "twin_or_multiple_gestation",
    "previous_lscs": "previous_lscs_history",
    "prior_c_section": "previous_lscs_history",
    "short_stature": "maternal_short_stature_or_malpresentation",
    "breech_presentation": "maternal_short_stature_or_malpresentation",
}


class TriageMode(StrEnum):
    """Execution mode for deterministic clinical triage."""

    FULL_ASSESSMENT = "FULL_ASSESSMENT"
    WATCH_RAPID = "WATCH_RAPID"


class PatientCategory(StrEnum):
    """Clinical protocol domain applied to the patient."""

    PEDIATRIC = "PEDIATRIC"
    MATERNAL = "MATERNAL"
    GENERAL = "GENERAL"


class TriageInput(BaseModel):
    """Structured clinical input accepted by ``evaluate_triage``."""

    model_config = ConfigDict(extra="forbid")

    patient_id: str | None = Field(default=None, min_length=1, max_length=128)
    mode: TriageMode = TriageMode.FULL_ASSESSMENT
    patient_category: PatientCategory | None = None
    age_months: int | None = Field(default=None, ge=0, le=1500)
    is_pregnant: bool = False
    is_postpartum: bool = False
    gestational_weeks: int | None = Field(default=None, ge=0, le=45)

    danger_signs: list[str] = Field(default_factory=list)
    symptoms: list[str] = Field(default_factory=list)

    temperature_c: float | None = Field(default=None, ge=30.0, le=45.0)
    respiratory_rate_bpm: int | None = Field(default=None, ge=0, le=160)
    spo2_pct: int | None = Field(default=None, ge=0, le=100)
    systolic_bp: int | None = Field(default=None, ge=40, le=300)
    diastolic_bp: int | None = Field(default=None, ge=20, le=200)
    hemoglobin_g_dl: float | None = Field(default=None, ge=1.0, le=25.0)
    muac_cm: float | None = Field(default=None, ge=5.0, le=50.0)

    has_cough_or_difficult_breathing: bool = False
    chest_indrawing: bool = False
    has_diarrhea: bool = False
    diarrhea_days: int = Field(default=0, ge=0, le=365)
    blood_in_stool: bool = False
    dehydration_signs: list[str] = Field(default_factory=list)
    fever_days: int = Field(default=0, ge=0, le=365)
    bilateral_pedal_edema: bool = False
    palmar_pallor: bool = False
    malaria_rdt_positive: bool = False

    assessed_at_ms: int | None = Field(default=None, ge=0)


def _normalize_flag(flag: str) -> str:
    cleaned = flag.strip().lower().replace("-", "_").replace(" ", "_")
    return _FLAG_ALIASES.get(cleaned, cleaned)


def _normalize_flag_set(flags: Iterable[str]) -> set[str]:
    return {_normalize_flag(f) for f in flags if f and f.strip()}


def _dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _infer_category(data: TriageInput) -> PatientCategory:
    if data.patient_category is not None:
        return data.patient_category
    if data.is_pregnant or data.is_postpartum or data.gestational_weeks is not None:
        return PatientCategory.MATERNAL
    if data.age_months is not None and data.age_months < 60:
        return PatientCategory.PEDIATRIC
    return PatientCategory.GENERAL


def _fast_breathing_threshold(age_months: int | None, imnci_rules: dict[str, Any]) -> int:
    effective_age = 12 if age_months is None else age_months
    for band in imnci_rules["vital_thresholds"]["fast_breathing_bpm_by_age_months"]:
        if band["min_months"] <= effective_age < band["max_months_exclusive"]:
            return int(band["threshold_bpm"])
    return 40


class _EvaluationAccumulator:
    """Internal monotonic severity accumulator."""

    def __init__(self) -> None:
        self.severity: TriageSeverity = TriageSeverity.GREEN_HOME
        self.matched_rules: list[str] = []
        self.actions: list[str] = []
        self.rationales: list[str] = []

    def record(
        self,
        rule_id: str,
        severity: TriageSeverity,
        actions: Iterable[str],
        rationale: str,
    ) -> None:
        if _SEVERITY_RANK[severity] > _SEVERITY_RANK[self.severity]:
            self.severity = severity
        self.matched_rules.append(rule_id)
        self.actions.extend(actions)
        self.rationales.append(rationale)


def _apply_universal_danger_signs(
    flags: set[str],
    imnci_rules: dict[str, Any],
    maternal_rules: dict[str, Any],
    category: PatientCategory,
    acc: _EvaluationAccumulator,
    *,
    include_maternal_in_rapid: bool = False,
) -> None:
    for rule in imnci_rules["general_danger_signs"]:
        if rule["flag"] in flags:
            acc.record(
                rule["id"],
                TriageSeverity.RED_EMERGENCY,
                rule["immediate_actions"],
                rule["rationale"],
            )

    if category == PatientCategory.MATERNAL or include_maternal_in_rapid:
        for rule in maternal_rules["red_flag_symptoms"]:
            if rule["flag"] in flags:
                acc.record(
                    rule["id"],
                    TriageSeverity.RED_EMERGENCY,
                    rule["immediate_actions"],
                    rule["rationale"],
                )
            elif rule["flag"] == "convulsions_or_fits" and "convulsions" in flags:
                acc.record(
                    rule["id"],
                    TriageSeverity.RED_EMERGENCY,
                    rule["immediate_actions"],
                    rule["rationale"],
                )


def _evaluate_maternal(
    data: TriageInput,
    flags: set[str],
    maternal_rules: dict[str, Any],
    acc: _EvaluationAccumulator,
) -> None:
    vt = maternal_rules["vital_thresholds"]

    # Blood Pressure: Hypotensive shock (<90 systolic) & Pre-eclampsia escalation
    sys_bp = data.systolic_bp
    dia_bp = data.diastolic_bp
    if sys_bp is not None and sys_bp < vt.get("bp_shock_systolic_below_mmhg", 90):
        acc.record(
            "MAT_BP_SHOCK_RED",
            TriageSeverity.RED_EMERGENCY,
            [
                "Immediate 108 emergency transfer to FRU/District Hospital with blood bank (suspected hemorrhagic or septic shock)",
                "Keep mother flat on left lateral side with legs elevated and keep warm during transport",
            ],
            f"Maternal hypotension (Systolic BP {sys_bp} mmHg < 90 mmHg) indicates obstetric hemorrhagic or septic shock.",
        )
    elif (
        (sys_bp is not None and sys_bp >= vt["bp_severe_preeclampsia_systolic_mmhg"])
        or (dia_bp is not None and dia_bp >= vt["bp_severe_preeclampsia_diastolic_mmhg"])
    ):
        acc.record(
            "MAT_BP_SEVERE_PREECLAMPSIA",
            TriageSeverity.RED_EMERGENCY,
            [
                "Immediate 108 emergency referral to FRU/District Hospital for Severe Pre-eclampsia",
                "Keep mother on left lateral side; monitor for convulsions, headache, or blurred vision",
            ],
            f"Critical maternal hypertension ({sys_bp}/{dia_bp} mmHg >= 160/110): severe pre-eclampsia emergency.",
        )
    elif (
        (sys_bp is not None and sys_bp >= vt["bp_red_systolic_mmhg"])
        or (dia_bp is not None and dia_bp >= vt["bp_red_diastolic_mmhg"])
    ):
        has_neuro = "severe_headache_or_blurred_vision" in flags or "swelling_face_and_hands" in flags
        rule_id = "MAT_PREECLAMPSIA_SYMPTOMATIC_RED" if has_neuro else "MAT_BP_PREECLAMPSIA_RED"
        acc.record(
            rule_id,
            TriageSeverity.RED_EMERGENCY,
            [
                "Urgent referral to FRU/PHC for pre-eclampsia evaluation and urine protein check (call 108/102)",
                "Advise left-lateral rest; do not delay transfer if headache or visual changes are present",
            ],
            f"Elevated maternal BP ({sys_bp}/{dia_bp} mmHg >= 140/90) meets NHM ASHA pre-eclampsia red-flag threshold.",
        )
    elif (
        (sys_bp is not None and sys_bp >= vt["bp_yellow_systolic_mmhg"])
        or (dia_bp is not None and dia_bp >= vt["bp_yellow_diastolic_mmhg"])
    ):
        acc.record(
            "MAT_BP_BORDERLINE_YELLOW",
            TriageSeverity.YELLOW_PHC,
            [
                "Re-check BP at PHC/ANM within 24-48 hours and test urine albumin",
                "Counsel mother on pre-eclampsia danger signs (headache, blurred vision, sudden swelling)",
            ],
            f"Borderline elevated maternal BP ({sys_bp}/{dia_bp} mmHg) requires close PHC monitoring.",
        )

    # Maternal fever & postpartum puerperal sepsis threshold
    if data.temperature_c is not None:
        if data.is_postpartum and data.temperature_c >= vt.get("temp_postpartum_sepsis_c", 38.0):
            acc.record(
                "MAT_PUERPERAL_SEPSIS_FEVER_RED",
                TriageSeverity.RED_EMERGENCY,
                [
                    "Immediate referral to FRU/District Hospital for suspected puerperal sepsis (parenteral antibiotics)",
                    "Assess lochia odor, uterine tenderness, and BP; encourage hydration if conscious",
                ],
                f"Postpartum maternal temperature {data.temperature_c:.1f}C >= 38.0C indicates high puerperal sepsis risk.",
            )
        elif data.temperature_c >= vt["temp_red_fever_c"]:
            acc.record(
                "MAT_FEVER_HIGH_RED",
                TriageSeverity.RED_EMERGENCY,
                [
                    "Urgent referral to FRU/PHC for suspected maternal sepsis or obstetric infection",
                    "Provide oral fluids and paracetamol if able to swallow during transport",
                ],
                f"Maternal temperature {data.temperature_c:.1f}C >= 38.5C indicates high sepsis risk.",
            )
        elif data.temperature_c >= vt["temp_yellow_fever_c"]:
            acc.record(
                "MAT_FEVER_MILD_YELLOW",
                TriageSeverity.YELLOW_PHC,
                [
                    "Refer to PHC/ANM within 24 hours for fever workup (malaria/UTI/infection)",
                    "Encourage safe hydration and monitor temperature",
                ],
                f"Maternal temperature {data.temperature_c:.1f}C requires timely clinical review.",
            )
    elif "fever" in flags or data.fever_days > 0:
        acc.record(
            "MAT_FEVER_REPORTED_YELLOW",
            TriageSeverity.YELLOW_PHC,
            [
                "Refer to PHC/ANM within 24 hours for fever workup (malaria/UTI/infection)",
                "Encourage safe hydration and monitor temperature",
            ],
            "Reported maternal fever without measured temperature requires timely PHC clinical review.",
        )

    # Maternal anemia (Hemoglobin)
    if data.hemoglobin_g_dl is not None:
        if data.hemoglobin_g_dl < vt["hb_severe_anemia_below_g_dl"]:
            acc.record(
                "MAT_ANEMIA_SEVERE_RED",
                TriageSeverity.RED_EMERGENCY,
                [
                    "Urgent referral to FRU/CHC for severe anemia management (IV iron / transfusion evaluation)",
                    "Register as High-Risk Pregnancy (HRP) and avoid physical exertion",
                ],
                f"Hemoglobin {data.hemoglobin_g_dl:.1f} g/dL < 7.0 g/dL defines severe maternal anemia.",
            )
        elif data.hemoglobin_g_dl < vt["hb_moderate_anemia_below_g_dl"]:
            acc.record(
                "MAT_ANEMIA_MODERATE_YELLOW",
                TriageSeverity.YELLOW_PHC,
                [
                    "Refer to PHC/ANM for therapeutic IFA dosing (2 tablets/day) and follow-up Hb check",
                    "Counsel on iron-rich indigenous foods and taking IFA separately from tea/calcium",
                ],
                f"Hemoglobin {data.hemoglobin_g_dl:.1f} g/dL indicates moderate maternal anemia.",
            )

    # Maternal SpO2
    if data.spo2_pct is not None and data.spo2_pct < vt["spo2_critical_below_pct"]:
        acc.record(
            "MAT_SPO2_CRITICAL_RED",
            TriageSeverity.RED_EMERGENCY,
            [
                "Immediate 108 emergency transfer to oxygen-equipped FRU",
                "Seat mother upright and monitor breathing continuously",
            ],
            f"Maternal SpO2 {data.spo2_pct}% < 92% indicates acute hypoxemia.",
        )

    # Maternal yellow flag symptoms
    for rule in maternal_rules["yellow_flag_symptoms"]:
        if rule["flag"] in flags:
            acc.record(
                rule["id"],
                TriageSeverity.YELLOW_PHC,
                rule["immediate_actions"],
                rule["rationale"],
            )


def _evaluate_pediatric(
    data: TriageInput,
    flags: set[str],
    imnci_rules: dict[str, Any],
    acc: _EvaluationAccumulator,
) -> None:
    vt = imnci_rules["vital_thresholds"]
    syndromes = imnci_rules["syndromes"]
    is_young_infant = data.age_months is not None and data.age_months < 2

    # Young Infant (<2 months) PSBI danger signs
    if is_young_infant or data.age_months is None:
        for rule in imnci_rules.get("young_infant_danger_signs", []):
            if rule["flag"] in flags:
                acc.record(
                    rule["id"],
                    TriageSeverity.RED_EMERGENCY,
                    rule["immediate_actions"],
                    rule["rationale"],
                )

    # Expanded WHO IMNCI pediatric syndrome symptom rules (Ear/Mastoiditis, Measles, Dengue, Malaria, SAM/Anemia)
    for rule in imnci_rules.get("syndrome_symptom_rules", []):
        if rule["flag"] in flags:
            acc.record(
                rule["id"],
                TriageSeverity(rule["severity"]),
                rule["immediate_actions"],
                rule["rationale"],
            )

    # Critical vitals: SpO2 & Temperature
    if data.spo2_pct is not None:
        if data.spo2_pct < vt["spo2_critical_below_pct"]:
            red_rule = syndromes["respiratory"]["red_rules"][0]
            acc.record(
                red_rule["id"],
                TriageSeverity.RED_EMERGENCY,
                red_rule["immediate_actions"],
                f"SpO2 {data.spo2_pct}% < 90%: {red_rule['rationale']}",
            )
        elif data.spo2_pct < vt["spo2_borderline_below_pct"]:
            yellow_rule = syndromes["respiratory"]["yellow_rules"][1]
            acc.record(
                yellow_rule["id"],
                TriageSeverity.YELLOW_PHC,
                yellow_rule["immediate_actions"],
                f"SpO2 {data.spo2_pct}% (90-93%): {yellow_rule['rationale']}",
            )

    if data.temperature_c is not None:
        if data.temperature_c < vt["temp_hypothermia_below_c"]:
            acc.record(
                "IMNCI_VITAL_HYPOTHERMIA_RED",
                TriageSeverity.RED_EMERGENCY,
                [
                    "Rewarm immediately with skin-to-skin Kangaroo Mother Care and dry warm blankets",
                    "Urgent referral to FRU/SNCU (call 108)",
                ],
                f"Hypothermia ({data.temperature_c:.1f}C < 35.5C) indicates critical neonatal/pediatric illness.",
            )
        elif data.temperature_c >= vt["temp_very_high_fever_c"]:
            acc.record(
                "IMNCI_FEVER_HYPERPYREXIA_RED",
                TriageSeverity.RED_EMERGENCY,
                syndromes["fever"]["red_actions"],
                f"Hyperpyrexia ({data.temperature_c:.1f}C >= 39.5C) requires urgent hospital evaluation.",
            )
        elif is_young_infant and data.temperature_c >= vt["temp_young_infant_fever_c"]:
            acc.record(
                "IMNCI_YOUNG_INFANT_FEVER_RED",
                TriageSeverity.RED_EMERGENCY,
                [
                    "Urgent referral to SNCU/FRU immediately (suspected neonatal sepsis)",
                    "Keep infant breastfeeding if able and prevent chilling during transport",
                ],
                f"Fever ({data.temperature_c:.1f}C >= 37.5C) in young infant <2 months is a WHO IMNCI emergency.",
            )
        elif data.temperature_c >= vt["temp_moderate_fever_c"]:
            acc.record(
                "IMNCI_FEVER_MODERATE_YELLOW",
                TriageSeverity.YELLOW_PHC,
                syndromes["fever"]["yellow_actions"],
                f"Fever ({data.temperature_c:.1f}C >= 38.0C) requires PHC/ANM evaluation and malaria RDT.",
            )

    # Respiratory syndrome (WHO IMNCI Cough / Difficult Breathing)
    rr_threshold = _fast_breathing_threshold(data.age_months, imnci_rules)
    fast_breathing = (
        data.respiratory_rate_bpm is not None and data.respiratory_rate_bpm >= rr_threshold
    )
    reported_fast_breathing = bool(
        flags
        & {
            "fast_breathing",
            "breathing_difficulty",
            "difficulty_breathing",
            "shortness_of_breath",
            "breathlessness",
        }
    )
    if is_young_infant and (fast_breathing or data.chest_indrawing):
        young_red = syndromes["respiratory"]["red_rules"][1]
        detail = (
            f"Young infant (<2m) respiratory rate {data.respiratory_rate_bpm}/min >= {rr_threshold}/min"
            if fast_breathing
            else "Young infant (<2m) severe chest indrawing"
        )
        acc.record(
            young_red["id"],
            TriageSeverity.RED_EMERGENCY,
            young_red["immediate_actions"],
            f"{detail}: {young_red['rationale']}",
        )
    elif fast_breathing or data.chest_indrawing or reported_fast_breathing:
        pneumonia_rule = syndromes["respiratory"]["yellow_rules"][0]
        if fast_breathing:
            detail = f"Respiratory rate {data.respiratory_rate_bpm}/min >= {rr_threshold}/min"
        elif data.chest_indrawing:
            detail = "Lower chest wall indrawing observed"
        else:
            detail = "Reported fast or difficult breathing"
        acc.record(
            pneumonia_rule["id"],
            TriageSeverity.YELLOW_PHC,
            pneumonia_rule["immediate_actions"],
            f"{detail}: {pneumonia_rule['rationale']}",
        )
    elif data.has_cough_or_difficult_breathing:
        green_resp = syndromes["respiratory"]["green_rule"]
        acc.record(
            green_resp["id"],
            TriageSeverity.GREEN_HOME,
            green_resp["immediate_actions"],
            green_resp["rationale"],
        )

    # Diarrhea & Dehydration syndrome (WHO IMNCI)
    dehydration_flags = _normalize_flag_set(data.dehydration_signs) | flags
    diarrhea_present = (
        data.has_diarrhea
        or data.diarrhea_days > 0
        or data.blood_in_stool
        or bool(data.dehydration_signs)
    )
    if diarrhea_present:
        diarrhea_cfg = syndromes["diarrhea"]
        min_signs = int(diarrhea_cfg["min_signs_for_classification"])
        severe_hits = dehydration_flags.intersection(diarrhea_cfg["severe_dehydration_signs"])
        some_hits = dehydration_flags.intersection(diarrhea_cfg["some_dehydration_signs"])
        persistent = data.diarrhea_days >= int(diarrhea_cfg["persistent_diarrhea_days"])

        if len(severe_hits) >= min_signs:
            acc.record(
                "IMNCI_DIARRHEA_SEVERE_DEHYDRATION_RED",
                TriageSeverity.RED_EMERGENCY,
                diarrhea_cfg["red_actions"],
                f"Severe dehydration ({len(severe_hits)} WHO IMNCI signs: {', '.join(sorted(severe_hits))}).",
            )
        elif persistent and len(some_hits) >= min_signs:
            acc.record(
                "IMNCI_DIARRHEA_SEVERE_PERSISTENT_RED",
                TriageSeverity.RED_EMERGENCY,
                diarrhea_cfg["red_actions"],
                f"Severe persistent diarrhea ({data.diarrhea_days} days with dehydration).",
            )
        else:
            matched_yellow_diarrhea = False
            if len(some_hits) >= min_signs:
                acc.record(
                    "IMNCI_DIARRHEA_SOME_DEHYDRATION_YELLOW",
                    TriageSeverity.YELLOW_PHC,
                    diarrhea_cfg["yellow_actions"],
                    f"Some dehydration ({len(some_hits)} WHO IMNCI signs: {', '.join(sorted(some_hits))}).",
                )
                matched_yellow_diarrhea = True
            if data.blood_in_stool:
                acc.record(
                    "IMNCI_DIARRHEA_DYSENTERY_YELLOW",
                    TriageSeverity.YELLOW_PHC,
                    diarrhea_cfg["yellow_actions"],
                    "Blood in stool (Dysentery) requires PHC/ANM antibiotic evaluation and Zinc/ORS.",
                )
                matched_yellow_diarrhea = True
            if persistent:
                acc.record(
                    "IMNCI_DIARRHEA_PERSISTENT_YELLOW",
                    TriageSeverity.YELLOW_PHC,
                    diarrhea_cfg["yellow_actions"],
                    f"Persistent diarrhea ({data.diarrhea_days} days >= 14 days) requires PHC follow-up.",
                )
                matched_yellow_diarrhea = True
            if not matched_yellow_diarrhea:
                acc.record(
                    "IMNCI_DIARRHEA_NO_DEHYDRATION_GREEN",
                    TriageSeverity.GREEN_HOME,
                    diarrhea_cfg["green_actions"],
                    "Acute diarrhea with no dehydration signs: safe for ORS Plan A and Zinc at home.",
                )

    # Fever duration / Malaria RDT
    fever_cfg = syndromes["fever"]
    if data.malaria_rdt_positive:
        acc.record(
            "IMNCI_FEVER_MALARIA_POSITIVE_YELLOW",
            TriageSeverity.YELLOW_PHC,
            fever_cfg["yellow_actions"],
            "Positive Malaria RDT requires immediate antimalarial protocol at PHC/ANM.",
        )
    elif data.fever_days >= int(fever_cfg["yellow_duration_days"]):
        acc.record(
            "IMNCI_FEVER_PROLONGED_YELLOW",
            TriageSeverity.YELLOW_PHC,
            fever_cfg["yellow_actions"],
            f"Fever persisting for {data.fever_days} days (>=3 days) requires PHC clinical workup.",
        )
    elif "high_fever" in flags or (
        data.temperature_c is None and (data.fever_days > 0 or "fever" in flags)
    ):
        acc.record(
            "IMNCI_FEVER_REPORTED_YELLOW",
            TriageSeverity.YELLOW_PHC,
            fever_cfg["yellow_actions"],
            "Reported pediatric fever without measured temperature requires PHC/ANM evaluation and malaria RDT.",
        )
    elif data.fever_days > 0 and (
        data.temperature_c is not None and data.temperature_c < vt["temp_moderate_fever_c"]
    ):
        acc.record(
            "IMNCI_FEVER_LOW_GRADE_GREEN",
            TriageSeverity.GREEN_HOME,
            fever_cfg["green_actions"],
            "Short-duration uncomplicated low-grade fever: home supportive care with close monitoring.",
        )

    # Malnutrition & Anemia
    mal_cfg = syndromes["malnutrition"]
    if data.bilateral_pedal_edema or (
        data.muac_cm is not None and data.muac_cm < vt["muac_sam_below_cm"]
    ):
        reason = (
            "Bilateral pitting pedal edema (Kwashiorkor/SAM)"
            if data.bilateral_pedal_edema
            else f"MUAC {data.muac_cm:.1f} cm < 11.5 cm (Severe Acute Malnutrition)"
        )
        acc.record(
            "IMNCI_MALNUTRITION_SAM_RED",
            TriageSeverity.RED_EMERGENCY,
            mal_cfg["red_actions"],
            f"{reason}: urgent NRC/PHC referral required.",
        )
    elif data.muac_cm is not None and data.muac_cm < vt["muac_mam_below_cm"]:
        acc.record(
            "IMNCI_MALNUTRITION_MAM_YELLOW",
            TriageSeverity.YELLOW_PHC,
            mal_cfg["yellow_actions"],
            f"MUAC {data.muac_cm:.1f} cm (11.5-12.4 cm): Moderate Acute Malnutrition requires PHC/AWC nutrition support.",
        )
    if data.palmar_pallor:
        acc.record(
            "IMNCI_ANEMIA_PALMAR_PALLOR_YELLOW",
            TriageSeverity.YELLOW_PHC,
            mal_cfg["yellow_actions"],
            "Palmar pallor detected: refer to PHC/ANM for anemia assessment and IFA/deworming.",
        )

    if data.hemoglobin_g_dl is not None:
        if data.hemoglobin_g_dl < vt.get("hb_severe_anemia_below_g_dl", 7.0):
            acc.record(
                "IMNCI_ANEMIA_SEVERE_HB_RED",
                TriageSeverity.RED_EMERGENCY,
                [
                    "Urgent referral to FRU/District Hospital for severe pediatric anemia (transfusion evaluation)",
                    "Keep child calm and prevent hypoxia during transport",
                ],
                f"Pediatric hemoglobin {data.hemoglobin_g_dl:.1f} g/dL < 7.0 g/dL defines severe anemia.",
            )
        elif data.hemoglobin_g_dl < vt.get("hb_moderate_anemia_below_g_dl", 11.0):
            acc.record(
                "IMNCI_ANEMIA_MODERATE_HB_YELLOW",
                TriageSeverity.YELLOW_PHC,
                mal_cfg["yellow_actions"],
                f"Pediatric hemoglobin {data.hemoglobin_g_dl:.1f} g/dL (<11.0 g/dL) indicates mild/moderate anemia requiring IFA syrup and PHC follow-up.",
            )


_GENERAL_RESPIRATORY_YELLOW_FLAGS = frozenset(
    {
        "chest_indrawing",
        "fast_breathing",
        "breathing_difficulty",
        "difficulty_breathing",
        "shortness_of_breath",
        "breathlessness",
    }
)

_GENERAL_ACUTE_YELLOW_FLAGS = frozenset(
    {
        "dengue",
        "jaundice",
        "rash",
        "measles",
        "measles_uncomplicated_rash",
        "acute_ear_pain_or_discharge",
        "chronic_ear_discharge",
        "anemia",
        "palmar_pallor",
        "bilateral_pedal_edema",
        "vomiting",
        "persistent_vomiting",
    }
)


def _evaluate_general(
    data: TriageInput,
    flags: set[str],
    acc: _EvaluationAccumulator,
) -> None:
    if data.spo2_pct is not None:
        if data.spo2_pct < 90:
            acc.record(
                "GEN_SPO2_CRITICAL_RED",
                TriageSeverity.RED_EMERGENCY,
                ["Urgent referral to oxygen-equipped PHC/FRU (call 108)"],
                f"SpO2 {data.spo2_pct}% < 90% indicates critical hypoxemia.",
            )
        elif data.spo2_pct < 94:
            acc.record(
                "GEN_SPO2_BORDERLINE_YELLOW",
                TriageSeverity.YELLOW_PHC,
                ["Refer to PHC today for pulse oximetry re-check and respiratory evaluation"],
                f"SpO2 {data.spo2_pct}% (90-93%) warrants clinical review.",
            )

    if data.temperature_c is not None:
        if data.temperature_c >= 39.5 or data.temperature_c < 35.5:
            acc.record(
                "GEN_TEMP_CRITICAL_RED",
                TriageSeverity.RED_EMERGENCY,
                ["Urgent referral to PHC/FRU immediately"],
                f"Critical body temperature ({data.temperature_c:.1f}C).",
            )
        elif data.temperature_c >= 38.0:
            acc.record(
                "GEN_FEVER_MODERATE_YELLOW",
                TriageSeverity.YELLOW_PHC,
                ["Refer to PHC/ANM for fever evaluation and malaria/dengue testing"],
                f"Moderate fever ({data.temperature_c:.1f}C) warrants PHC assessment.",
            )

    if data.systolic_bp is not None or data.diastolic_bp is not None:
        sys_bp = data.systolic_bp or 0
        dia_bp = data.diastolic_bp or 0
        if sys_bp >= 180 or dia_bp >= 120 or (data.systolic_bp is not None and data.systolic_bp < 90):
            acc.record(
                "GEN_BP_CRISIS_RED",
                TriageSeverity.RED_EMERGENCY,
                ["Immediate emergency referral to FRU/Hospital (call 108)"],
                f"Critical blood pressure ({data.systolic_bp}/{data.diastolic_bp} mmHg).",
            )
        elif sys_bp >= 140 or dia_bp >= 90:
            acc.record(
                "GEN_BP_ELEVATED_YELLOW",
                TriageSeverity.YELLOW_PHC,
                ["Refer to PHC NCD clinic for hypertension confirmation and management"],
                f"Elevated blood pressure ({data.systolic_bp}/{data.diastolic_bp} mmHg >= 140/90).",
            )

    # Symptom-based escalation when numeric vitals are absent or sub-threshold
    if (
        data.malaria_rdt_positive
        or data.fever_days > 0
        or "fever" in flags
        or "high_fever" in flags
        or "malaria" in flags
    ) and (data.temperature_c is None or data.temperature_c < 38.0):
        acc.record(
            "GEN_FEVER_SYMPTOM_YELLOW",
            TriageSeverity.YELLOW_PHC,
            [
                "Refer to PHC/ANM for fever evaluation and malaria/dengue testing",
                "Ensure oral hydration and monitor temperature",
            ],
            "Reported fever symptom warrants PHC clinical review.",
        )

    if data.chest_indrawing or bool(flags & _GENERAL_RESPIRATORY_YELLOW_FLAGS):
        acc.record(
            "GEN_RESPIRATORY_SYMPTOM_YELLOW",
            TriageSeverity.YELLOW_PHC,
            [
                "Refer to PHC/ANM today for respiratory assessment and pulse oximetry",
                "Monitor breathing rate and oxygen saturation closely",
            ],
            "Reported breathing difficulty or fast breathing warrants PHC clinical review.",
        )

    if (
        data.has_diarrhea
        or data.diarrhea_days > 0
        or data.blood_in_stool
        or bool(flags & {"diarrhea", "blood_in_stool", "dysentery"})
    ):
        acc.record(
            "GEN_DIARRHEA_SYMPTOM_YELLOW",
            TriageSeverity.YELLOW_PHC,
            [
                "Start ORS + Zinc immediately and refer to PHC/ANM for diarrhea assessment",
                "Seek urgent care if blood in stool, inability to drink, or severe dehydration develops",
            ],
            "Reported diarrhea warrants PHC clinical review and hydration management.",
        )

    if data.palmar_pallor or data.bilateral_pedal_edema or bool(flags & _GENERAL_ACUTE_YELLOW_FLAGS):
        acc.record(
            "GEN_ACUTE_SYMPTOM_YELLOW",
            TriageSeverity.YELLOW_PHC,
            [
                "Refer to PHC/ANM for timely clinical evaluation",
                "Monitor for any danger signs and seek immediate care if symptoms worsen",
            ],
            "Reported acute clinical symptoms warrant PHC review.",
        )


def evaluate_triage(
    triage_input: TriageInput | None = None,
    **kwargs: Any,
) -> TriageAssessment:
    """Execute deterministic clinical triage and return a strict ``TriageAssessment``.

    Accepts either a ``TriageInput`` instance or keyword arguments matching ``TriageInput`` fields.
    Supports both full Tier-1/2 assessment (``TriageMode.FULL_ASSESSMENT``) and 1-tap Tier-0 Watch
    rapid danger-sign screening (``TriageMode.WATCH_RAPID``).
    """
    if triage_input is not None and kwargs:
        raise ValueError("Pass either a TriageInput instance or keyword arguments, not both.")
    data = triage_input if triage_input is not None else TriageInput(**kwargs)

    imnci_rules = load_imnci_rules()
    maternal_rules = load_maternal_anc_rules()
    category = _infer_category(data)
    all_flags = _normalize_flag_set(data.danger_signs) | _normalize_flag_set(data.symptoms)

    acc = _EvaluationAccumulator()

    # Step 1: Hard clinical safety floor — ANY danger sign immediately forces RED_EMERGENCY.
    is_watch_rapid = data.mode == TriageMode.WATCH_RAPID
    _apply_universal_danger_signs(
        all_flags,
        imnci_rules,
        maternal_rules,
        category,
        acc,
        include_maternal_in_rapid=is_watch_rapid,
    )

    # Step 2: Mode-specific evaluation.
    if is_watch_rapid:
        # In Watch rapid mode, also honor critical vitals if passed (e.g., BP >= 140/90 in maternal, SpO2 < 90, temp >= 39.5).
        if category == PatientCategory.MATERNAL:
            _evaluate_maternal(data, all_flags, maternal_rules, acc)
        else:
            if data.spo2_pct is not None and data.spo2_pct < 90:
                acc.record(
                    "WATCH_SPO2_CRITICAL_RED",
                    TriageSeverity.RED_EMERGENCY,
                    ["Immediate 108 emergency transfer to oxygen-equipped FRU/PHC"],
                    f"Watch rapid screen: SpO2 {data.spo2_pct}% < 90% critical hypoxemia.",
                )
            if data.temperature_c is not None and (
                data.temperature_c >= 39.5 or data.temperature_c < 35.5
            ):
                acc.record(
                    "WATCH_TEMP_CRITICAL_RED",
                    TriageSeverity.RED_EMERGENCY,
                    ["Urgent referral to PHC/FRU immediately"],
                    f"Watch rapid screen: critical temperature {data.temperature_c:.1f}C.",
                )
        protocol_source = "WHO_IMNCI_ASHA_WATCH_RAPID"
    elif category == PatientCategory.MATERNAL:
        _evaluate_maternal(data, all_flags, maternal_rules, acc)
        protocol_source = "NHM_ASHA_MATERNAL_DETERMINISTIC"
    elif category == PatientCategory.PEDIATRIC:
        _evaluate_pediatric(data, all_flags, imnci_rules, acc)
        protocol_source = "WHO_IMNCI_PEDIATRIC_DETERMINISTIC"
    else:
        _evaluate_general(data, all_flags, acc)
        protocol_source = "WHO_IMNCI_ASHA_DETERMINISTIC"

    # Step 3: Default GREEN_HOME message when no rules matched.
    if not acc.matched_rules:
        default_rule = "WATCH_RAPID_NO_DANGER_SIGNS" if is_watch_rapid else "CLINICAL_ROUTINE_GREEN"
        default_action = (
            "No immediate danger signs detected on Watch screen. Continue monitoring or run full Phone assessment if symptoms persist."
            if is_watch_rapid
            else "No danger signs or urgent criteria detected. Continue home supportive care, hydration, and routine ASHA follow-up."
        )
        acc.record(
            default_rule,
            TriageSeverity.GREEN_HOME,
            [default_action],
            "All screened danger signs and clinical criteria are within home-care thresholds.",
        )

    # Hard safety invariant enforcement: RED_EMERGENCY and YELLOW_PHC require referral/clinical follow-up;
    # RED_EMERGENCY MUST always have referral_required=True.
    referral_required = acc.severity in (
        TriageSeverity.RED_EMERGENCY,
        TriageSeverity.YELLOW_PHC,
    )

    return TriageAssessment(
        patient_id=data.patient_id,
        severity=acc.severity,
        matched_rules=_dedupe_preserve_order(acc.matched_rules),
        immediate_actions=_dedupe_preserve_order(acc.actions),
        referral_required=referral_required,
        rationale=" ".join(_dedupe_preserve_order(acc.rationales)),
        confidence=1.0,
        protocol_source=protocol_source,
        execution_target=ExecutionTarget.LOCAL_DETERMINISTIC,
        assessed_at_ms=data.assessed_at_ms,
    )


def evaluate_watch_rapid_triage(
    danger_signs: Iterable[str],
    *,
    patient_id: str | None = None,
    is_pregnant: bool = False,
    spo2_pct: int | None = None,
    temperature_c: float | None = None,
    systolic_bp: int | None = None,
    diastolic_bp: int | None = None,
    assessed_at_ms: int | None = None,
) -> TriageAssessment:
    """Convenience entrypoint for Tier-0 Watch 1-tap danger-sign screening."""
    return evaluate_triage(
        TriageInput(
            patient_id=patient_id,
            mode=TriageMode.WATCH_RAPID,
            is_pregnant=is_pregnant,
            danger_signs=list(danger_signs),
            spo2_pct=spo2_pct,
            temperature_c=temperature_c,
            systolic_bp=systolic_bp,
            diastolic_bp=diastolic_bp,
            assessed_at_ms=assessed_at_ms,
        )
    )


def triage_to_action_card(
    assessment: TriageAssessment,
    *,
    target_tier: NodeTier = NodeTier.TIER_0_WATCH,
    watch_mode: WatchMode | None = WatchMode.CHW_COMPANION,
    source_event_id: str | None = None,
) -> ActionCard:
    """Convert a deterministic ``TriageAssessment`` into a glanceable ``ActionCard``."""
    priority_map = {
        TriageSeverity.RED_EMERGENCY: ActionCardPriority.CRITICAL,
        TriageSeverity.YELLOW_PHC: ActionCardPriority.HIGH,
        TriageSeverity.GREEN_HOME: ActionCardPriority.LOW,
    }
    title_map = {
        TriageSeverity.RED_EMERGENCY: "RED EMERGENCY: Immediate Referral",
        TriageSeverity.YELLOW_PHC: "YELLOW: PHC / ANM Visit Required",
        TriageSeverity.GREEN_HOME: "GREEN: Home Care & Follow-Up",
    }
    return ActionCard(
        patient_id=assessment.patient_id,
        title=title_map[assessment.severity],
        summary=assessment.rationale[:1000],
        action_steps=list(assessment.immediate_actions),
        priority=priority_map[assessment.severity],
        severity=assessment.severity,
        target_tier=target_tier,
        watch_mode=watch_mode if target_tier == NodeTier.TIER_0_WATCH else None,
        source_event_id=source_event_id,
    )
