# `aarogya-clinical-engine`

Deterministic, offline-first clinical safety engine for **Aarogya Mesh** (`packages/clinical-engine/`).

## Clinical Safety Invariant

1. **Zero LLM / API Dependency**: Every triage classification, maternal ANC/PNC checklist evaluation, and India UIP vaccination schedule runs 100% deterministically on local JSON rule tables (`confidence = 1.0`, `execution_target = LOCAL_DETERMINISTIC`).
2. **Red-Flag Monotonicity**: Any single WHO IMNCI general danger sign or NHM ASHA maternal emergency red flag **immediately forces `TriageSeverity.RED_EMERGENCY` and `referral_required = True`**, regardless of other normal vitals or benign symptoms.
3. **Inspectable Clinical Rule Tables**: All thresholds and action steps live in human-auditable JSON files under `rules/` (`v2.0.0`):
   - `rules/imnci_pediatric.json` — WHO IMNCI general danger signs (10), Young Infant (`<2 months`) PSBI danger signs (6, plus `<2m` fast breathing `>=60 bpm` -> `RED_EMERGENCY`), expanded 2–59m syndromes (10 symptom rules covering Mastoiditis/Ear infections, Measles complications, Dengue/Malaria hemorrhagic signs, Complicated SAM failed appetite, Severe/Moderate Hb Anemia), age-stratified fast breathing, dehydration, fever, and MUAC/edema malnutrition rules.
   - `rules/maternal_anc.json` — NHM ASHA / PMSMA High-Risk Pregnancy & Postpartum protocols: 16 red flags (Pre-eclampsia `BP>=140/90` & `>=160/110`, Maternal Shock `Systolic BP < 90`, APH/PPH, Puerperal Sepsis `>=38.0°C` postpartum, Previous LSCS scar tenderness, Severe Hyperemesis Gravidarum, Obstructed Labor, Severe Anemia `Hb < 7.0 g/dL`), 10 yellow HRP flags (GDM, Rh-negative sensitization, Twin/Multiple gestation, Previous LSCS history, Short stature/malpresentation), and 5 enriched ANC/HBNC checklists (10 items each, 50 items total).
   - `rules/uip_vaccines.json` — Full India Universal Immunization Programme (UIP) schedule: 30 pediatric/adolescent doses from Birth (`BCG`, `OPV-0`, `HepB-Birth`) through 6w/10w/14w, 9m (`MR-1`, `JE-1`, `PCV-Booster`, `fIPV-3`, `Vitamin-A-1`), 16–24m (`DPT-Booster-1`, `OPV-Booster`, `MR-2`, `JE-2`, `Vitamin-A-2/3`), 5–6y (`DPT-Booster-2`), and 10y/16y (`Td-10y`, `Td-16y`), plus Maternal ANC `Td-1`/`Td-2`/`Td-Booster` via `compute_maternal_td_schedule(...)`.

## Quick API Usage

### 1. Full Triage & Tier-0 Watch Rapid Screening

```python
from aarogya_clinical_engine import (
    TriageInput,
    evaluate_triage,
    evaluate_watch_rapid_triage,
    triage_to_action_card,
)

# Full WHO IMNCI pediatric assessment (Tier-1 Phone / Tier-2 Hub)
assessment = evaluate_triage(
    TriageInput(
        patient_id="pat-child-01",
        age_months=8,
        has_cough_or_difficult_breathing=True,
        respiratory_rate_bpm=54,  # >= 50 bpm threshold for 2-11 months
    )
)
assert assessment.severity == "YELLOW_PHC"

# Rapid 1-tap Tier-0 Watch danger-sign screening
watch_result = evaluate_watch_rapid_triage(
    danger_signs=["convulsions"],
    patient_id="pat-child-01",
)
assert watch_result.severity == "RED_EMERGENCY"
assert watch_result.referral_required is True
card = triage_to_action_card(watch_result)
```

### 2. Maternal ANC & Postnatal Checklists

```python
from aarogya_clinical_engine import ChecklistType, evaluate_checklist

result = evaluate_checklist(
    ChecklistType.ANC_TRIMESTER_2,
    completed_checks=["anc_t2_bp_weight", "anc_t2_ifa_calcium"],
    patient_id="pat-mat-01",
)
print(result.completion_score, result.missing_critical_checks, len(result.action_cards))
```

### 3. India UIP Vaccination Schedule

```python
from datetime import date
from aarogya_clinical_engine import compute_vaccination_schedule

schedule = compute_vaccination_schedule(
    dob=date(2026, 9, 1),
    administered_vaccines={"BCG": date(2026, 9, 1), "OPV-0": date(2026, 9, 1)},
    as_of_date=date(2026, 10, 20),
)
```

## Running Tests

```bash
uv run pytest packages/clinical-engine/tests -v
```
