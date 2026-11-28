/**
 * AUTO-GENERATED exact copy of `packages/clinical-engine/rules/uip_vaccines.json` (v2.0.0).
 * Bundled so clinical rules run fully offline on the phone. DO NOT hand-edit values;
 * regenerate from the source JSON. Parity is enforced by tests/clinical/rules_parity.test.ts.
 */

import type { UipVaccineRules } from "./types";

export const UIP_VACCINE_RULES: UipVaccineRules = {
  "protocol_id": "INDIA_UIP_MOHFW_2024",
  "version": "2.0.0",
  "description": "India Universal Immunization Programme (UIP) full schedule: pediatric birth through 16 years (including fIPV-3, JE-2, DPT-Booster-2, Vitamin A, Adolescent Td) plus Maternal ANC Td.",
  "defaults": {
    "due_soon_window_days": 14
  },
  "vaccines": [
    {
      "code": "BCG",
      "name": "BCG (Bacillus Calmette-Guerin)",
      "milestone": "Birth",
      "due_age_days": 0,
      "due_soon_lead_days": 7,
      "max_catchup_age_days": 365,
      "route": "Intra-dermal (Left upper arm)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Give at birth or as early as possible till 1 year of age (0.05 ml if <1m, 0.1 ml if >=1m).",
      "aliases": ["bcg", "bcg-0", "bcg_birth"]
    },
    {
      "code": "OPV-0",
      "name": "Oral Polio Vaccine (Zero Dose)",
      "milestone": "Birth",
      "due_age_days": 0,
      "due_soon_lead_days": 7,
      "max_catchup_age_days": 15,
      "route": "Oral (2 drops)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Administer at birth or within the first 15 days of life.",
      "aliases": ["opv0", "opv-0", "opv_0", "opv-birth"]
    },
    {
      "code": "HepB-Birth",
      "name": "Hepatitis B (Birth Dose)",
      "milestone": "Birth",
      "due_age_days": 0,
      "due_soon_lead_days": 1,
      "max_catchup_age_days": 1,
      "route": "Intra-muscular (Antero-lateral mid-thigh)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Must be administered within 24 hours of birth for vertical transmission prophylaxis.",
      "aliases": ["hepb", "hepb-0", "hepb-birth", "hepb_birth", "hep-b-0"]
    },
    {
      "code": "OPV-1",
      "name": "Oral Polio Vaccine (Dose 1)",
      "milestone": "6 Weeks",
      "due_age_days": 42,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 1825,
      "route": "Oral (2 drops)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Primary polio series dose 1; catch-up permitted up to 5 years.",
      "aliases": ["opv1", "opv-1", "opv_1"]
    },
    {
      "code": "Pentavalent-1",
      "name": "Pentavalent-1 (DPT + HepB + Hib)",
      "milestone": "6 Weeks",
      "due_age_days": 42,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 365,
      "route": "Intra-muscular (Left mid-thigh)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "First dose must be initiated before 1 year of age.",
      "aliases": ["penta-1", "penta1", "pentavalent-1", "pentavalent_1"]
    },
    {
      "code": "Rotavirus-1",
      "name": "Rotavirus Vaccine (Dose 1)",
      "milestone": "6 Weeks",
      "due_age_days": 42,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 365,
      "route": "Oral",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Oral diarrhea prophylaxis; first dose up to 1 year of age per UIP.",
      "aliases": ["rvv-1", "rvv1", "rotavirus-1", "rotavirus_1"]
    },
    {
      "code": "fIPV-1",
      "name": "Fractional Inactivated Polio Vaccine (Dose 1)",
      "milestone": "6 Weeks",
      "due_age_days": 42,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 365,
      "route": "Intra-dermal (Right upper arm)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "0.1 ml intra-dermal dose at 6 weeks alongside Pentavalent-1.",
      "aliases": ["fipv-1", "fipv1", "ipv-1", "fipv_1"]
    },
    {
      "code": "PCV-1",
      "name": "Pneumococcal Conjugate Vaccine (Dose 1)",
      "milestone": "6 Weeks",
      "due_age_days": 42,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 365,
      "route": "Intra-muscular (Right mid-thigh)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Pneumonia and meningitis protection (2 primary doses + 1 booster under UIP).",
      "aliases": ["pcv-1", "pcv1", "pcv_1"]
    },
    {
      "code": "OPV-2",
      "name": "Oral Polio Vaccine (Dose 2)",
      "milestone": "10 Weeks",
      "due_age_days": 70,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 1825,
      "route": "Oral (2 drops)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Minimum 4-week interval after OPV-1.",
      "aliases": ["opv2", "opv-2", "opv_2"]
    },
    {
      "code": "Pentavalent-2",
      "name": "Pentavalent-2 (DPT + HepB + Hib)",
      "milestone": "10 Weeks",
      "due_age_days": 70,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 365,
      "route": "Intra-muscular (Left mid-thigh)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Minimum 4-week interval after Pentavalent-1.",
      "aliases": ["penta-2", "penta2", "pentavalent-2", "pentavalent_2"]
    },
    {
      "code": "Rotavirus-2",
      "name": "Rotavirus Vaccine (Dose 2)",
      "milestone": "10 Weeks",
      "due_age_days": 70,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 365,
      "route": "Oral",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Minimum 4-week interval after Rotavirus-1.",
      "aliases": ["rvv-2", "rvv2", "rotavirus-2", "rotavirus_2"]
    },
    {
      "code": "OPV-3",
      "name": "Oral Polio Vaccine (Dose 3)",
      "milestone": "14 Weeks",
      "due_age_days": 98,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 1825,
      "route": "Oral (2 drops)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Completes primary OPV series.",
      "aliases": ["opv3", "opv-3", "opv_3"]
    },
    {
      "code": "Pentavalent-3",
      "name": "Pentavalent-3 (DPT + HepB + Hib)",
      "milestone": "14 Weeks",
      "due_age_days": 98,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 365,
      "route": "Intra-muscular (Left mid-thigh)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Completes primary Pentavalent series.",
      "aliases": ["penta-3", "penta3", "pentavalent-3", "pentavalent_3"]
    },
    {
      "code": "Rotavirus-3",
      "name": "Rotavirus Vaccine (Dose 3)",
      "milestone": "14 Weeks",
      "due_age_days": 98,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 365,
      "route": "Oral",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Completes 3-dose Rotavirus series.",
      "aliases": ["rvv-3", "rvv3", "rotavirus-3", "rotavirus_3"]
    },
    {
      "code": "fIPV-2",
      "name": "Fractional Inactivated Polio Vaccine (Dose 2)",
      "milestone": "14 Weeks",
      "due_age_days": 98,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 365,
      "route": "Intra-dermal (Right upper arm)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Second 0.1 ml intra-dermal fIPV dose (8 weeks after fIPV-1).",
      "aliases": ["fipv-2", "fipv2", "ipv-2", "fipv_2"]
    },
    {
      "code": "PCV-2",
      "name": "Pneumococcal Conjugate Vaccine (Dose 2)",
      "milestone": "14 Weeks",
      "due_age_days": 98,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 365,
      "route": "Intra-muscular (Right mid-thigh)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Second primary PCV dose (8 weeks after PCV-1).",
      "aliases": ["pcv-2", "pcv2", "pcv_2"]
    },
    {
      "code": "MR-1",
      "name": "Measles-Rubella (Dose 1)",
      "milestone": "9 Months",
      "due_age_days": 270,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 1825,
      "route": "Sub-cutaneous (Right upper arm)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Administer at 9 completed months (catch-up permitted up to 5 years).",
      "aliases": ["mr-1", "mr1", "mr_1", "measles-1"]
    },
    {
      "code": "JE-1",
      "name": "Japanese Encephalitis (Dose 1, endemic districts)",
      "milestone": "9 Months",
      "due_age_days": 270,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 5475,
      "route": "Sub-cutaneous (Left upper arm)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Applicable in JE-endemic districts under NVBDCP/UIP.",
      "aliases": ["je-1", "je1", "je_1"]
    },
    {
      "code": "PCV-Booster",
      "name": "Pneumococcal Conjugate Vaccine (Booster)",
      "milestone": "9 Months",
      "due_age_days": 270,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 365,
      "route": "Intra-muscular (Right mid-thigh)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Booster dose at 9-12 months (minimum 6 months after PCV-2 if delayed).",
      "aliases": ["pcv-booster", "pcv_booster", "pcv-b"]
    },
    {
      "code": "fIPV-3",
      "name": "Fractional Inactivated Polio Vaccine (Dose 3)",
      "milestone": "9 Months",
      "due_age_days": 270,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 1825,
      "route": "Intra-dermal (Left upper arm)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Updated MoHFW UIP 3rd fractional IPV dose co-administered at 9 months with MR-1.",
      "aliases": ["fipv-3", "fipv3", "ipv-3", "fipv_3"]
    },
    {
      "code": "Vitamin-A-1",
      "name": "Vitamin A Prophylaxis (Dose 1 — 1 Lakh IU)",
      "milestone": "9 Months",
      "due_age_days": 270,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 1825,
      "route": "Oral (1 ml spoon)",
      "schedule_group": "UIP_INDIA_VITAMIN_A",
      "clinical_note": "1,00,000 IU oral prophylaxis given with MR-1 to prevent xerophthalmia and reduce measles mortality.",
      "aliases": ["vit-a-1", "vita-1", "vitamin-a-1", "vitamin_a_1"]
    },
    {
      "code": "DPT-Booster-1",
      "name": "DPT Booster (Dose 1)",
      "milestone": "16-24 Months",
      "due_age_days": 480,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 2555,
      "route": "Intra-muscular (Antero-lateral mid-thigh)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "First DPT booster at 16-24 months (catch-up up to 7 years).",
      "aliases": ["dpt-booster-1", "dpt-b1", "dpt_booster_1", "dpt-booster"]
    },
    {
      "code": "OPV-Booster",
      "name": "Oral Polio Vaccine (Booster)",
      "milestone": "16-24 Months",
      "due_age_days": 480,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 1825,
      "route": "Oral (2 drops)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Oral Polio booster co-administered with DPT-Booster-1.",
      "aliases": ["opv-booster", "opv_booster", "opv-b"]
    },
    {
      "code": "MR-2",
      "name": "Measles-Rubella (Dose 2)",
      "milestone": "16-24 Months",
      "due_age_days": 480,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 1825,
      "route": "Sub-cutaneous (Right upper arm)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Second Measles-Rubella dose ensuring durable immunity.",
      "aliases": ["mr-2", "mr2", "mr_2", "measles-2"]
    },
    {
      "code": "JE-2",
      "name": "Japanese Encephalitis (Dose 2, endemic districts)",
      "milestone": "16-24 Months",
      "due_age_days": 480,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 5475,
      "route": "Sub-cutaneous (Left upper arm)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "Second JE dose in endemic districts (minimum 3 months after JE-1).",
      "aliases": ["je-2", "je2", "je_2"]
    },
    {
      "code": "Vitamin-A-2",
      "name": "Vitamin A Prophylaxis (Dose 2 — 2 Lakh IU)",
      "milestone": "16-18 Months",
      "due_age_days": 480,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 1825,
      "route": "Oral (2 ml spoon)",
      "schedule_group": "UIP_INDIA_VITAMIN_A",
      "clinical_note": "2,00,000 IU oral dose; repeat every 6 months up to 5 years of age (total 9 doses).",
      "aliases": ["vit-a-2", "vita-2", "vitamin-a-2", "vitamin_a_2"]
    },
    {
      "code": "Vitamin-A-3",
      "name": "Vitamin A Prophylaxis (Dose 3 — 2 Lakh IU)",
      "milestone": "24 Months",
      "due_age_days": 730,
      "due_soon_lead_days": 14,
      "max_catchup_age_days": 1825,
      "route": "Oral (2 ml spoon)",
      "schedule_group": "UIP_INDIA_VITAMIN_A",
      "clinical_note": "2,00,000 IU biannual prophylaxis dose at 2 years (continue every 6 months until 5 years).",
      "aliases": ["vit-a-3", "vita-3", "vitamin-a-3", "vitamin_a_3"]
    },
    {
      "code": "DPT-Booster-2",
      "name": "DPT Booster (Dose 2)",
      "milestone": "5-6 Years",
      "due_age_days": 1825,
      "due_soon_lead_days": 30,
      "max_catchup_age_days": 2555,
      "route": "Intra-muscular (Upper arm)",
      "schedule_group": "UIP_INDIA",
      "clinical_note": "School-entry DPT booster at 5-6 years of age.",
      "aliases": ["dpt-booster-2", "dpt-b2", "dpt_booster_2"]
    },
    {
      "code": "Td-10y",
      "name": "Tetanus & Adult Diphtheria (10 Years Booster)",
      "milestone": "10 Years",
      "due_age_days": 3650,
      "due_soon_lead_days": 30,
      "max_catchup_age_days": 5840,
      "route": "Intra-muscular (Upper arm)",
      "schedule_group": "UIP_INDIA_ADOLESCENT",
      "clinical_note": "Adolescent Td booster at 10 years of age.",
      "aliases": ["td-10", "td-10y", "td_10y", "tt-10"]
    },
    {
      "code": "Td-16y",
      "name": "Tetanus & Adult Diphtheria (16 Years Booster)",
      "milestone": "16 Years",
      "due_age_days": 5840,
      "due_soon_lead_days": 30,
      "max_catchup_age_days": 6570,
      "route": "Intra-muscular (Upper arm)",
      "schedule_group": "UIP_INDIA_ADOLESCENT",
      "clinical_note": "Adolescent Td booster at 16 years of age.",
      "aliases": ["td-16", "td-16y", "td_16y", "tt-16"]
    }
  ],
  "maternal_vaccines": [
    {
      "code": "Td-1",
      "name": "Tetanus & Adult Diphtheria (ANC Dose 1)",
      "milestone": "Early Pregnancy (ANC Registration)",
      "due_gestational_weeks": 12,
      "due_soon_lead_days": 14,
      "route": "Intra-muscular (Upper arm)",
      "schedule_group": "UIP_INDIA_MATERNAL",
      "clinical_note": "Administer as early as possible in pregnancy (not needed if Td-Booster applies within 3 years of prior 2-dose pregnancy).",
      "aliases": ["td1", "td-1", "td_1", "tt-1", "tt1"]
    },
    {
      "code": "Td-2",
      "name": "Tetanus & Adult Diphtheria (ANC Dose 2)",
      "milestone": "4 Weeks After Td-1",
      "due_gestational_weeks": 16,
      "due_soon_lead_days": 14,
      "route": "Intra-muscular (Upper arm)",
      "schedule_group": "UIP_INDIA_MATERNAL",
      "clinical_note": "Administer at least 4 weeks after Td-1 for maternal and neonatal tetanus protection.",
      "aliases": ["td2", "td-2", "td_2", "tt-2", "tt2"]
    },
    {
      "code": "Td-Booster",
      "name": "Tetanus & Adult Diphtheria (ANC Booster)",
      "milestone": "Early Pregnancy (Prior 2 Td Doses Within 3 Years)",
      "due_gestational_weeks": 12,
      "due_soon_lead_days": 14,
      "route": "Intra-muscular (Upper arm)",
      "schedule_group": "UIP_INDIA_MATERNAL",
      "clinical_note": "Single booster dose if pregnant mother received 2 Td doses in a previous pregnancy within the last 3 years.",
      "aliases": ["td-booster", "td_booster", "tt-booster", "td-b"]
    }
  ]
};
