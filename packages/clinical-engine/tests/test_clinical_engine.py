"""Comprehensive pytest suite for aarogya-clinical-engine deterministic protocols."""

from __future__ import annotations

from datetime import date

import pytest

from aarogya_clinical_engine import (
    ChecklistType,
    PatientCategory,
    TriageInput,
    TriageMode,
    compute_maternal_td_schedule,
    compute_vaccination_schedule,
    evaluate_checklist,
    evaluate_triage,
    evaluate_watch_rapid_triage,
    get_checklist_definition,
    list_checklist_types,
    load_imnci_rules,
    load_maternal_anc_rules,
    load_uip_vaccine_rules,
    select_anc_checklist_for_gestational_weeks,
    triage_to_action_card,
    vaccination_items_to_action_cards,
)
from aarogya_contracts import (
    ActionCardPriority,
    ExecutionTarget,
    NodeTier,
    TriageSeverity,
    VaccinationStatus,
    WatchMode,
)


def test_rule_tables_load_and_have_expected_structure() -> None:
    imnci = load_imnci_rules()
    maternal = load_maternal_anc_rules()
    uip = load_uip_vaccine_rules()

    assert len(imnci["general_danger_signs"]) == 10
    assert len(imnci["young_infant_danger_signs"]) == 6
    assert len(imnci["syndrome_symptom_rules"]) == 10
    assert len(maternal["red_flag_symptoms"]) == 16
    assert len(maternal["yellow_flag_symptoms"]) == 10
    assert set(maternal["checklists"].keys()) == {
        "anc_trimester_1",
        "anc_trimester_2",
        "anc_trimester_3",
        "pnc_mother",
        "pnc_newborn",
    }
    for checklist_cfg in maternal["checklists"].values():
        assert 8 <= len(checklist_cfg["items"]) <= 12
    codes = {v["code"] for v in uip["vaccines"]}
    assert {
        "BCG",
        "OPV-0",
        "HepB-Birth",
        "Pentavalent-1",
        "OPV-1",
        "Rotavirus-1",
        "fIPV-1",
        "PCV-1",
        "Pentavalent-2",
        "Pentavalent-3",
        "fIPV-2",
        "PCV-2",
        "MR-1",
        "JE-1",
        "PCV-Booster",
        "fIPV-3",
        "Vitamin-A-1",
        "DPT-Booster-1",
        "OPV-Booster",
        "MR-2",
        "JE-2",
        "Vitamin-A-2",
        "Vitamin-A-3",
        "DPT-Booster-2",
        "Td-10y",
        "Td-16y",
    }.issubset(codes)
    maternal_vax_codes = {v["code"] for v in uip["maternal_vaccines"]}
    assert maternal_vax_codes == {"Td-1", "Td-2", "Td-Booster"}


@pytest.mark.parametrize(
    "danger_sign",
    [rule["flag"] for rule in load_imnci_rules()["general_danger_signs"]],
)
def test_single_imnci_danger_sign_always_forces_red_emergency(danger_sign: str) -> None:
    """Hard safety floor: ONE danger sign MUST force RED_EMERGENCY even with normal vitals."""
    assessment = evaluate_triage(
        TriageInput(
            patient_id="pat-child-red",
            age_months=18,
            danger_signs=[danger_sign],
            temperature_c=36.8,
            respiratory_rate_bpm=28,
            spo2_pct=99,
            muac_cm=14.2,
        )
    )
    assert assessment.severity == TriageSeverity.RED_EMERGENCY
    assert assessment.referral_required is True
    assert assessment.confidence == 1.0
    assert assessment.execution_target == ExecutionTarget.LOCAL_DETERMINISTIC
    assert len(assessment.matched_rules) >= 1
    assert len(assessment.immediate_actions) >= 1


def test_danger_sign_aliases_normalize_and_force_red_emergency() -> None:
    assessment = evaluate_triage(
        patient_id="pat-alias",
        age_months=10,
        symptoms=["Unable-to-Drink"],
        spo2_pct=98,
    )
    assert assessment.severity == TriageSeverity.RED_EMERGENCY
    assert assessment.referral_required is True
    assert "IMNCI_GDS_01" in assessment.matched_rules


@pytest.mark.parametrize(
    ("age_months", "rr_bpm", "expected_severity"),
    [
        # WHO IMNCI Young Infant (<2m): RR >= 60 bpm is PSBI RED_EMERGENCY
        (1, 60, TriageSeverity.RED_EMERGENCY),
        (1, 55, TriageSeverity.GREEN_HOME),
        (6, 50, TriageSeverity.YELLOW_PHC),
        (6, 45, TriageSeverity.GREEN_HOME),
        (24, 40, TriageSeverity.YELLOW_PHC),
        (24, 34, TriageSeverity.GREEN_HOME),
    ],
)
def test_imnci_age_stratified_fast_breathing_thresholds(
    age_months: int,
    rr_bpm: int,
    expected_severity: TriageSeverity,
) -> None:
    assessment = evaluate_triage(
        TriageInput(
            age_months=age_months,
            has_cough_or_difficult_breathing=True,
            respiratory_rate_bpm=rr_bpm,
            temperature_c=37.0,
            spo2_pct=97,
        )
    )
    assert assessment.severity == expected_severity
    assert assessment.referral_required is (expected_severity != TriageSeverity.GREEN_HOME)


def test_imnci_young_infant_emergencies_and_hypoxemia() -> None:
    young_infant_fever = evaluate_triage(
        age_months=1,
        temperature_c=37.8,
        spo2_pct=97,
    )
    assert young_infant_fever.severity == TriageSeverity.RED_EMERGENCY
    assert "IMNCI_YOUNG_INFANT_FEVER_RED" in young_infant_fever.matched_rules

    young_infant_indrawing = evaluate_triage(
        age_months=1,
        chest_indrawing=True,
        spo2_pct=96,
    )
    assert young_infant_indrawing.severity == TriageSeverity.RED_EMERGENCY
    assert "IMNCI_RESP_RED_02" in young_infant_indrawing.matched_rules

    hypoxemia = evaluate_triage(age_months=20, spo2_pct=88)
    assert hypoxemia.severity == TriageSeverity.RED_EMERGENCY
    assert "IMNCI_RESP_RED_01" in hypoxemia.matched_rules

    borderline_spo2 = evaluate_triage(age_months=20, spo2_pct=92)
    assert borderline_spo2.severity == TriageSeverity.YELLOW_PHC


def test_imnci_diarrhea_and_malnutrition_classifications() -> None:
    severe_dehydration = evaluate_triage(
        age_months=14,
        has_diarrhea=True,
        dehydration_signs=["sunken_eyes", "skin_pinch_very_slow"],
    )
    assert severe_dehydration.severity == TriageSeverity.RED_EMERGENCY
    assert "IMNCI_DIARRHEA_SEVERE_DEHYDRATION_RED" in severe_dehydration.matched_rules

    dysentery = evaluate_triage(
        age_months=14,
        has_diarrhea=True,
        blood_in_stool=True,
    )
    assert dysentery.severity == TriageSeverity.YELLOW_PHC
    assert "IMNCI_DIARRHEA_DYSENTERY_YELLOW" in dysentery.matched_rules

    no_dehydration = evaluate_triage(
        age_months=14,
        has_diarrhea=True,
        diarrhea_days=2,
    )
    assert no_dehydration.severity == TriageSeverity.GREEN_HOME
    assert no_dehydration.referral_required is False

    sam_muac = evaluate_triage(age_months=18, muac_cm=11.1)
    assert sam_muac.severity == TriageSeverity.RED_EMERGENCY
    assert "IMNCI_MALNUTRITION_SAM_RED" in sam_muac.matched_rules

    mam_muac = evaluate_triage(age_months=18, muac_cm=12.0, palmar_pallor=True)
    assert mam_muac.severity == TriageSeverity.YELLOW_PHC
    assert "IMNCI_MALNUTRITION_MAM_YELLOW" in mam_muac.matched_rules
    assert "IMNCI_ANEMIA_PALMAR_PALLOR_YELLOW" in mam_muac.matched_rules


def test_maternal_preeclampsia_and_bp_escalation() -> None:
    bp_red = evaluate_triage(
        TriageInput(
            patient_id="pat-mat-01",
            is_pregnant=True,
            gestational_weeks=30,
            systolic_bp=146,
            diastolic_bp=94,
            symptoms=["severe_headache", "blurred_vision"],
        )
    )
    assert bp_red.severity == TriageSeverity.RED_EMERGENCY
    assert bp_red.referral_required is True
    assert "MAT_PREECLAMPSIA_SYMPTOMATIC_RED" in bp_red.matched_rules
    assert "MAT_RED_01" in bp_red.matched_rules

    bp_isolated_140_90 = evaluate_triage(
        is_pregnant=True,
        gestational_weeks=26,
        systolic_bp=140,
        diastolic_bp=90,
    )
    assert bp_isolated_140_90.severity == TriageSeverity.RED_EMERGENCY
    assert "MAT_BP_PREECLAMPSIA_RED" in bp_isolated_140_90.matched_rules

    bp_severe = evaluate_triage(
        is_pregnant=True,
        gestational_weeks=34,
        systolic_bp=164,
        diastolic_bp=112,
    )
    assert bp_severe.severity == TriageSeverity.RED_EMERGENCY
    assert "MAT_BP_SEVERE_PREECLAMPSIA" in bp_severe.matched_rules

    bp_borderline = evaluate_triage(
        is_pregnant=True,
        gestational_weeks=24,
        systolic_bp=134,
        diastolic_bp=86,
    )
    assert bp_borderline.severity == TriageSeverity.YELLOW_PHC
    assert "MAT_BP_BORDERLINE_YELLOW" in bp_borderline.matched_rules


@pytest.mark.parametrize(
    "red_flag",
    [rule["flag"] for rule in load_maternal_anc_rules()["red_flag_symptoms"]],
)
def test_every_maternal_red_flag_forces_red_emergency(red_flag: str) -> None:
    assessment = evaluate_triage(
        TriageInput(
            patient_id="pat-mat-rf",
            is_pregnant=True,
            gestational_weeks=28,
            symptoms=[red_flag],
            systolic_bp=114,
            diastolic_bp=74,
            hemoglobin_g_dl=11.8,
            temperature_c=36.9,
        )
    )
    assert assessment.severity == TriageSeverity.RED_EMERGENCY
    assert assessment.referral_required is True
    assert assessment.confidence == 1.0


def test_maternal_anemia_fever_and_healthy_routine() -> None:
    severe_anemia = evaluate_triage(is_pregnant=True, gestational_weeks=22, hemoglobin_g_dl=6.4)
    assert severe_anemia.severity == TriageSeverity.RED_EMERGENCY
    assert "MAT_ANEMIA_SEVERE_RED" in severe_anemia.matched_rules

    moderate_anemia = evaluate_triage(is_pregnant=True, gestational_weeks=22, hemoglobin_g_dl=8.8)
    assert moderate_anemia.severity == TriageSeverity.YELLOW_PHC
    assert "MAT_ANEMIA_MODERATE_YELLOW" in moderate_anemia.matched_rules

    healthy_anc = evaluate_triage(
        patient_category=PatientCategory.MATERNAL,
        is_pregnant=True,
        gestational_weeks=20,
        systolic_bp=116,
        diastolic_bp=76,
        temperature_c=36.8,
        hemoglobin_g_dl=11.5,
    )
    assert healthy_anc.severity == TriageSeverity.GREEN_HOME
    assert healthy_anc.referral_required is False


def test_watch_tier0_rapid_mode_and_action_card_conversion() -> None:
    watch_red = evaluate_watch_rapid_triage(
        danger_signs=["convulsions"],
        patient_id="pat-watch-1",
        assessed_at_ms=1732350000000,
    )
    assert watch_red.severity == TriageSeverity.RED_EMERGENCY
    assert watch_red.referral_required is True
    assert watch_red.protocol_source == "WHO_IMNCI_ASHA_WATCH_RAPID"
    assert watch_red.confidence == 1.0

    card = triage_to_action_card(
        watch_red,
        target_tier=NodeTier.TIER_0_WATCH,
        watch_mode=WatchMode.CHW_COMPANION,
    )
    assert card.priority == ActionCardPriority.CRITICAL
    assert card.severity == TriageSeverity.RED_EMERGENCY
    assert card.target_tier == NodeTier.TIER_0_WATCH
    assert card.watch_mode == WatchMode.CHW_COMPANION

    watch_maternal_bleed = evaluate_watch_rapid_triage(
        danger_signs=["vaginal_bleeding"],
        is_pregnant=True,
    )
    assert watch_maternal_bleed.severity == TriageSeverity.RED_EMERGENCY
    assert watch_maternal_bleed.referral_required is True

    watch_green = evaluate_watch_rapid_triage(danger_signs=[])
    assert watch_green.severity == TriageSeverity.GREEN_HOME
    assert watch_green.referral_required is False
    assert watch_green.matched_rules == ["WATCH_RAPID_NO_DANGER_SIGNS"]

    # Explicit TriageInput with WATCH_RAPID + critical SpO2
    watch_spo2 = evaluate_triage(
        TriageInput(mode=TriageMode.WATCH_RAPID, spo2_pct=87)
    )
    assert watch_spo2.severity == TriageSeverity.RED_EMERGENCY


def test_anc_and_pnc_checklists_evaluation_and_action_cards() -> None:
    assert len(list_checklist_types()) == 5
    assert select_anc_checklist_for_gestational_weeks(10) == ChecklistType.ANC_TRIMESTER_1
    assert select_anc_checklist_for_gestational_weeks(20) == ChecklistType.ANC_TRIMESTER_2
    assert select_anc_checklist_for_gestational_weeks(34) == ChecklistType.ANC_TRIMESTER_3

    with pytest.raises(ValueError):
        select_anc_checklist_for_gestational_weeks(50)

    partial = evaluate_checklist(
        ChecklistType.ANC_TRIMESTER_1,
        completed_checks={
            "anc_t1_mcp_registration": True,
            "anc_t1_bp_check": True,
            "anc_t1_hb_blood_group": False,
        },
        patient_id="pat-anc-1",
        due_by=date(2026, 12, 1),
    )
    assert partial.total_items == 10
    assert partial.completion_score == 0.2
    assert partial.is_complete is False
    assert partial.has_critical_gaps is True
    assert "anc_t1_hb_blood_group" in partial.missing_critical_checks
    assert any(c.priority == ActionCardPriority.HIGH for c in partial.action_cards)
    assert any(c.priority == ActionCardPriority.LOW for c in partial.action_cards)

    # Complete PNC Newborn checklist -> 1.0 score, no gaps, no action cards
    pnc_nb_all = [item["id"] for item in get_checklist_definition(ChecklistType.PNC_NEWBORN)["items"]]
    done = evaluate_checklist(ChecklistType.PNC_NEWBORN, pnc_nb_all, patient_id="pat-nb-1")
    assert done.total_items == 10
    assert done.completion_score == 1.0
    assert done.is_complete is True
    assert done.has_critical_gaps is False
    assert done.action_cards == []


def test_uip_vaccination_schedule_birth_due_soon_overdue_and_aliases() -> None:
    dob = date(2026, 9, 1)

    # Day 0 (Birth): birth doses DUE_SOON (days_delta == 0), 6w doses UPCOMING
    day0 = {v.vaccine_code: v for v in compute_vaccination_schedule(dob, as_of_date=dob)}
    assert day0["BCG"].status == VaccinationStatus.DUE_SOON
    assert day0["BCG"].days_delta == 0
    assert day0["OPV-0"].status == VaccinationStatus.DUE_SOON
    assert day0["HepB-Birth"].status == VaccinationStatus.DUE_SOON
    assert day0["Pentavalent-1"].status == VaccinationStatus.UPCOMING
    assert day0["Pentavalent-1"].due_date == date(2026, 10, 13)  # +42 days

    # Day 35 (7 days before 6-week milestone): birth doses COMPLETED via aliases, 6w doses DUE_SOON
    day35_items = compute_vaccination_schedule(
        dob=dob,
        administered_vaccines={
            "bcg": date(2026, 9, 1),
            "opv0": date(2026, 9, 1),
            "hepb-0": date(2026, 9, 1),
        },
        as_of_date=date(2026, 10, 6),
    )
    day35 = {v.vaccine_code: v for v in day35_items}
    assert day35["BCG"].status == VaccinationStatus.COMPLETED
    assert day35["BCG"].administered_date == date(2026, 9, 1)
    assert day35["HepB-Birth"].status == VaccinationStatus.COMPLETED
    assert day35["Pentavalent-1"].status == VaccinationStatus.DUE_SOON
    assert day35["Pentavalent-1"].days_delta == 7
    assert day35["OPV-2"].status == VaccinationStatus.UPCOMING

    # Day 45 (3 days past 6-week due date): 6w doses OVERDUE with days_delta == -3;
    # missed HepB-Birth also notes past catch-up window.
    day45_items = compute_vaccination_schedule(
        dob=dob,
        administered_vaccines=["BCG", "OPV-0"],
        as_of_date=date(2026, 10, 16),
    )
    day45 = {v.vaccine_code: v for v in day45_items}
    assert day45["BCG"].status == VaccinationStatus.COMPLETED
    assert day45["BCG"].administered_date == date(2026, 9, 1)
    assert day45["HepB-Birth"].status == VaccinationStatus.OVERDUE
    assert "Medical Officer" in day45["HepB-Birth"].reminder_text
    assert day45["Pentavalent-1"].status == VaccinationStatus.OVERDUE
    assert day45["Pentavalent-1"].days_delta == -3
    assert "overdue by 3 day(s)" in day45["Pentavalent-1"].reminder_text

    # Convert to Watch action cards
    cards = vaccination_items_to_action_cards(day45_items, patient_id="pat-child-vax")
    assert any(c.priority == ActionCardPriority.HIGH for c in cards)
    assert all(c.target_tier == NodeTier.TIER_0_WATCH for c in cards)

    # Guardrail: as_of_date before dob raises ValueError
    with pytest.raises(ValueError, match="cannot precede dob"):
        compute_vaccination_schedule(dob=dob, as_of_date=date(2026, 8, 31))


@pytest.mark.parametrize(
    "psbi_flag",
    [rule["flag"] for rule in load_imnci_rules()["young_infant_danger_signs"]],
)
def test_young_infant_psbi_danger_signs_force_red_emergency(psbi_flag: str) -> None:
    """WHO IMNCI Young Infant (<2m) PSBI danger signs must force RED_EMERGENCY."""
    assessment = evaluate_triage(
        TriageInput(
            patient_id="pat-newborn-psbi",
            age_months=1,
            symptoms=[psbi_flag],
            temperature_c=36.9,
            respiratory_rate_bpm=44,
            spo2_pct=98,
        )
    )
    assert assessment.severity == TriageSeverity.RED_EMERGENCY
    assert assessment.referral_required is True
    assert assessment.confidence == 1.0


def test_expanded_pediatric_syndromes_and_anemia_gradations() -> None:
    mastoiditis = evaluate_triage(age_months=24, symptoms=["mastoiditis"])
    assert mastoiditis.severity == TriageSeverity.RED_EMERGENCY
    assert "IMNCI_EAR_RED_01" in mastoiditis.matched_rules

    acute_ear = evaluate_triage(age_months=24, symptoms=["ear_pain"])
    assert acute_ear.severity == TriageSeverity.YELLOW_PHC
    assert "IMNCI_EAR_YELLOW_01" in acute_ear.matched_rules

    complicated_measles = evaluate_triage(age_months=18, symptoms=["corneal_clouding"])
    assert complicated_measles.severity == TriageSeverity.RED_EMERGENCY
    assert "IMNCI_MEASLES_RED_01" in complicated_measles.matched_rules

    simple_measles = evaluate_triage(age_months=18, symptoms=["measles_rash"])
    assert simple_measles.severity == TriageSeverity.YELLOW_PHC
    assert "IMNCI_MEASLES_YELLOW_01" in simple_measles.matched_rules

    dengue_red = evaluate_triage(age_months=36, symptoms=["dengue_hemorrhagic"])
    assert dengue_red.severity == TriageSeverity.RED_EMERGENCY
    assert "IMNCI_DENGUE_RED_01" in dengue_red.matched_rules

    malaria_red = evaluate_triage(age_months=36, symptoms=["severe_malaria"])
    assert malaria_red.severity == TriageSeverity.RED_EMERGENCY
    assert "IMNCI_MALARIA_RED_01" in malaria_red.matched_rules

    sam_appetite = evaluate_triage(age_months=20, symptoms=["failed_appetite_test"])
    assert sam_appetite.severity == TriageSeverity.RED_EMERGENCY
    assert "IMNCI_MALNUTRITION_APPETITE_RED_01" in sam_appetite.matched_rules

    severe_hb = evaluate_triage(age_months=24, hemoglobin_g_dl=6.2)
    assert severe_hb.severity == TriageSeverity.RED_EMERGENCY
    assert "IMNCI_ANEMIA_SEVERE_HB_RED" in severe_hb.matched_rules

    moderate_hb = evaluate_triage(age_months=24, hemoglobin_g_dl=9.4)
    assert moderate_hb.severity == TriageSeverity.YELLOW_PHC
    assert "IMNCI_ANEMIA_MODERATE_HB_YELLOW" in moderate_hb.matched_rules


def test_maternal_shock_puerperal_sepsis_and_hrp_yellow_flags() -> None:
    shock = evaluate_triage(is_pregnant=True, gestational_weeks=32, systolic_bp=84, diastolic_bp=54)
    assert shock.severity == TriageSeverity.RED_EMERGENCY
    assert "MAT_BP_SHOCK_RED" in shock.matched_rules

    puerperal_fever = evaluate_triage(is_postpartum=True, temperature_c=38.2)
    assert puerperal_fever.severity == TriageSeverity.RED_EMERGENCY
    assert "MAT_PUERPERAL_SEPSIS_FEVER_RED" in puerperal_fever.matched_rules

    scar_pain = evaluate_triage(is_pregnant=True, gestational_weeks=37, symptoms=["scar_tenderness"])
    assert scar_pain.severity == TriageSeverity.RED_EMERGENCY
    assert "MAT_RED_12" in scar_pain.matched_rules

    for rule in load_maternal_anc_rules()["yellow_flag_symptoms"]:
        res = evaluate_triage(
            is_pregnant=True,
            gestational_weeks=24,
            symptoms=[rule["flag"]],
            systolic_bp=114,
            diastolic_bp=74,
            hemoglobin_g_dl=11.5,
        )
        assert res.severity == TriageSeverity.YELLOW_PHC
        assert rule["id"] in res.matched_rules


def test_uip_expanded_boosters_vitamin_a_and_maternal_td_schedule() -> None:
    dob = date(2021, 1, 1)
    # At 5 years + 10 days: DPT-Booster-2 is OVERDUE, Vitamin-A-1/2/3 schedule_group verified, Td-10y UPCOMING
    items = {v.vaccine_code: v for v in compute_vaccination_schedule(dob, as_of_date=date(2026, 1, 10))}
    assert len(items) == 30
    assert items["fIPV-3"].due_date == date(2021, 9, 28)
    assert items["Vitamin-A-1"].schedule_group == "UIP_INDIA_VITAMIN_A"
    assert items["DPT-Booster-2"].status == VaccinationStatus.OVERDUE
    assert items["Td-10y"].schedule_group == "UIP_INDIA_ADOLESCENT"
    assert items["Td-10y"].status == VaccinationStatus.UPCOMING
    assert items["Td-16y"].status == VaccinationStatus.UPCOMING

    # Maternal ANC Td schedule (standard 2-dose)
    lmp = date(2026, 6, 1)
    td1_given = date(2026, 8, 20)
    maternal_std = {
        v.vaccine_code: v
        for v in compute_maternal_td_schedule(
            lmp_date=lmp,
            administered_vaccines={"td1": td1_given},
            as_of_date=date(2026, 9, 10),
        )
    }
    assert set(maternal_std.keys()) == {"Td-1", "Td-2"}
    assert maternal_std["Td-1"].status == VaccinationStatus.COMPLETED
    assert maternal_std["Td-2"].due_date == date(2026, 9, 17)  # 28 days after Td-1
    assert maternal_std["Td-2"].status == VaccinationStatus.DUE_SOON
    assert maternal_std["Td-2"].schedule_group == "UIP_INDIA_MATERNAL"

    # Maternal ANC Td-Booster (prior 2 Td doses within 3 years)
    maternal_booster = compute_maternal_td_schedule(
        lmp_date=lmp,
        as_of_date=date(2026, 8, 24),
        prior_two_td_within_3_years=True,
    )
    assert [v.vaccine_code for v in maternal_booster] == ["Td-Booster"]
    assert maternal_booster[0].status == VaccinationStatus.DUE_SOON

    with pytest.raises(ValueError, match="cannot precede lmp_date"):
        compute_maternal_td_schedule(lmp_date=lmp, as_of_date=date(2026, 5, 1))


def test_symptom_only_voice_triage_escalates_without_numeric_vitals() -> None:
    """Reported fever/diarrhea/respiratory symptoms without numeric vitals must not default to GREEN."""
    gen_fever = evaluate_triage(symptoms=["fever"])
    assert gen_fever.severity == TriageSeverity.YELLOW_PHC
    assert gen_fever.referral_required is True
    assert "GEN_FEVER_SYMPTOM_YELLOW" in gen_fever.matched_rules

    gen_diarrhea = evaluate_triage(symptoms=["diarrhea"])
    assert gen_diarrhea.severity == TriageSeverity.YELLOW_PHC
    assert "GEN_DIARRHEA_SYMPTOM_YELLOW" in gen_diarrhea.matched_rules

    gen_resp = evaluate_triage(symptoms=["fast_breathing"])
    assert gen_resp.severity == TriageSeverity.YELLOW_PHC
    assert "GEN_RESPIRATORY_SYMPTOM_YELLOW" in gen_resp.matched_rules

    ped_unmeasured_fever = evaluate_triage(age_months=24, symptoms=["fever"], fever_days=1)
    assert ped_unmeasured_fever.severity == TriageSeverity.YELLOW_PHC
    assert "IMNCI_FEVER_REPORTED_YELLOW" in ped_unmeasured_fever.matched_rules

    ped_measured_low_fever = evaluate_triage(
        age_months=24, symptoms=["fever"], fever_days=1, temperature_c=37.6
    )
    assert ped_measured_low_fever.severity == TriageSeverity.GREEN_HOME
    assert "IMNCI_FEVER_LOW_GRADE_GREEN" in ped_measured_low_fever.matched_rules

    mat_unmeasured_fever = evaluate_triage(is_pregnant=True, gestational_weeks=20, symptoms=["fever"])
    assert mat_unmeasured_fever.severity == TriageSeverity.YELLOW_PHC
    assert "MAT_FEVER_REPORTED_YELLOW" in mat_unmeasured_fever.matched_rules

    routine_general = evaluate_triage(symptoms=[])
    assert routine_general.severity == TriageSeverity.GREEN_HOME
    assert "CLINICAL_ROUTINE_GREEN" in routine_general.matched_rules

