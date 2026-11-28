/**
 * AUTO-GENERATED exact copy of `packages/clinical-engine/rules/maternal_anc.json` (v2.0.0).
 * Bundled so clinical rules run fully offline on the phone. DO NOT hand-edit values;
 * regenerate from the source JSON. Parity is enforced by tests/clinical/rules_parity.test.ts.
 */

import type { MaternalAncRules } from "./types";

export const MATERNAL_ANC_RULES: MaternalAncRules = {
  "protocol_id": "NHM_ASHA_MATERNAL_ANC_PNC_2024",
  "version": "2.0.0",
  "description": "Deterministic NHM ASHA / PMSMA Antenatal (ANC), High-Risk Pregnancy (HRP), and Postnatal (HBNC/PNC) red-flag triage and checklist rules.",
  "vital_thresholds": {
    "bp_shock_systolic_below_mmhg": 90,
    "bp_red_systolic_mmhg": 140,
    "bp_red_diastolic_mmhg": 90,
    "bp_severe_preeclampsia_systolic_mmhg": 160,
    "bp_severe_preeclampsia_diastolic_mmhg": 110,
    "bp_yellow_systolic_mmhg": 130,
    "bp_yellow_diastolic_mmhg": 85,
    "temp_red_fever_c": 38.5,
    "temp_postpartum_sepsis_c": 38.0,
    "temp_yellow_fever_c": 37.5,
    "hb_severe_anemia_below_g_dl": 7.0,
    "hb_moderate_anemia_below_g_dl": 10.0,
    "spo2_critical_below_pct": 92
  },
  "red_flag_symptoms": [
    {
      "id": "MAT_RED_01",
      "flag": "severe_headache_or_blurred_vision",
      "label": "Severe persistent headache or blurred vision",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Suspect Pre-eclampsia / impending Eclampsia — measure BP immediately",
        "Urgent referral to FRU/CHC/District Hospital via 108/102 ambulance",
        "Keep mother lying on her left side in a quiet, dimly lit space during transport"
      ],
      "rationale": "Severe headache or visual disturbance in pregnancy/postpartum is a critical pre-eclampsia danger sign."
    },
    {
      "id": "MAT_RED_02",
      "flag": "convulsions_or_fits",
      "label": "Convulsions or fits (Eclampsia)",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Protect airway, turn mother onto left lateral side, do NOT restrain or put anything in mouth",
        "Immediate 108 emergency transfer to FRU for Magnesium Sulfate and emergency obstetric care"
      ],
      "rationale": "Eclampsia is an immediate maternal and fetal life-threatening emergency."
    },
    {
      "id": "MAT_RED_03",
      "flag": "vaginal_bleeding",
      "label": "Vaginal bleeding in pregnancy or heavy postpartum bleeding",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Immediate emergency referral to FRU/District Hospital (call 108)",
        "Keep mother lying flat on left side with legs elevated; arrange blood donor contact",
        "Do NOT perform vaginal examination in field setting"
      ],
      "rationale": "Antepartum or postpartum hemorrhage is a leading cause of maternal mortality requiring urgent hospital care."
    },
    {
      "id": "MAT_RED_04",
      "flag": "reduced_fetal_movement",
      "label": "Reduced or absent fetal movements",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Immediate same-day referral to FRU/PHC for fetal heart rate and ultrasound assessment",
        "Advise mother to lie on left side while arranging transport"
      ],
      "rationale": "Reduced or absent fetal movement signals potential fetal distress or compromise."
    },
    {
      "id": "MAT_RED_05",
      "flag": "high_fever",
      "label": "High fever (>=38.5C) or foul-smelling discharge",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Urgent referral to FRU/PHC for maternal sepsis / chorioamnionitis / puerperal infection management",
        "Give oral fluids and paracetamol if able to swallow during transport"
      ],
      "rationale": "High maternal fever indicates possible obstetric sepsis requiring parenteral antibiotics."
    },
    {
      "id": "MAT_RED_06",
      "flag": "severe_anemia_signs",
      "label": "Severe pallor with breathlessness at rest or fatigue",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Urgent referral to FRU/CHC for hemoglobin check and possible IV iron or blood transfusion",
        "Keep mother resting upright; avoid exertion"
      ],
      "rationale": "Severe anemia (Hb < 7 g/dL) increases risk of cardiac failure and fatal postpartum hemorrhage."
    },
    {
      "id": "MAT_RED_07",
      "flag": "severe_abdominal_pain",
      "label": "Severe persistent abdominal or epigastric pain",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Urgent referral to FRU/District Hospital (rule out placental abruption, ectopic pregnancy, or HELLP syndrome)"
      ],
      "rationale": "Severe abdominal or right-upper-quadrant pain in pregnancy is an obstetric red flag."
    },
    {
      "id": "MAT_RED_08",
      "flag": "leaking_fluid_before_labor",
      "label": "Water breaking / leaking fluid before contractions",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Urgent referral to FRU/PHC for PROM/PPROM assessment and infection prophylaxis",
        "Keep clean pad and avoid vaginal insertion"
      ],
      "rationale": "Premature rupture of membranes carries high risk of ascending infection and cord prolapse."
    },
    {
      "id": "MAT_RED_09",
      "flag": "swelling_face_and_hands",
      "label": "Sudden swelling of face, hands, or generalized edema",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Check BP immediately and refer urgently to FRU/PHC for pre-eclampsia evaluation"
      ],
      "rationale": "Facial or hand edema suggests systemic endothelial dysfunction associated with pre-eclampsia."
    },
    {
      "id": "MAT_RED_10",
      "flag": "breathing_difficulty_or_chest_pain",
      "label": "Severe breathing difficulty or chest pain",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Seat mother upright and arrange immediate 108 emergency transfer to FRU"
      ],
      "rationale": "Acute dyspnea or chest pain may indicate pulmonary edema, embolism, or peripartum cardiomyopathy."
    },
    {
      "id": "MAT_RED_11",
      "flag": "puerperal_sepsis_signs",
      "label": "Puerperal sepsis signs (Foul-smelling lochia, uterine tenderness, chills, or postpartum fever)",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Immediate referral to FRU/District Hospital for parenteral broad-spectrum antibiotics (call 108)",
        "Monitor maternal pulse, BP, and temperature; encourage oral hydration if conscious"
      ],
      "rationale": "NHM HBNC/Dakshata Protocol: puerperal sepsis progresses rapidly to septic shock without IV antibiotics."
    },
    {
      "id": "MAT_RED_12",
      "flag": "previous_lscs_scar_tenderness",
      "label": "Previous C-section (LSCS) scar tenderness or acute suprapubic pain",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Immediate emergency transfer to FRU/District Hospital with emergency obstetric OT and blood bank (call 108)",
        "Keep mother nil by mouth (NPO) and lying on left lateral side during transfer"
      ],
      "rationale": "Scar tenderness in a previous LSCS pregnancy signals impending uterine rupture."
    },
    {
      "id": "MAT_RED_13",
      "flag": "hyperemesis_gravidarum_severe",
      "label": "Severe Hyperemesis Gravidarum (Intractable vomiting with dehydration or inability to retain fluids)",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Urgent referral to FRU/PHC for IV fluid resuscitation, thiamine, and electrolyte correction",
        "Offer small sips of ORS if tolerated during transport"
      ],
      "rationale": "Intractable hyperemesis gravidarum causes severe dehydration, ketosis, and Wernicke encephalopathy risk."
    },
    {
      "id": "MAT_RED_14",
      "flag": "postpartum_hemorrhage_heavy",
      "label": "Postpartum Hemorrhage (Soaking >1 pad/hour, large clots, or postpartum dizziness/syncope)",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Call 108 immediately for emergency transfer to FRU with blood transfusion capability",
        "Keep mother flat with legs elevated, keep warm, and initiate gentle uterine fundal massage if trained"
      ],
      "rationale": "Postpartum hemorrhage (PPH) is the single leading cause of maternal death in rural India."
    },
    {
      "id": "MAT_RED_15",
      "flag": "antepartum_hemorrhage_painful_or_painless",
      "label": "Antepartum Hemorrhage (Second/third trimester vaginal bleeding — painful or painless)",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Immediate 108 transfer to FRU with surgical and blood bank facility",
        "Strictly NO vaginal examination; keep mother resting on left lateral side"
      ],
      "rationale": "Antepartum hemorrhage suggests placenta previa or abruptio placentae requiring immediate hospital care."
    },
    {
      "id": "MAT_RED_16",
      "flag": "obstructed_or_prolonged_labor",
      "label": "Prolonged or obstructed labor (>12 hours active contractions without progress)",
      "severity": "RED_EMERGENCY",
      "immediate_actions": [
        "Immediate emergency transfer to FRU/CHC for obstetric evaluation and C-section readiness (call 108)",
        "Avoid unprescribed uterotonics or fundal pressure in the community"
      ],
      "rationale": "Obstructed labor risks uterine rupture, fetal asphyxia, and obstetric fistula."
    }
  ],
  "yellow_flag_symptoms": [
    {
      "id": "MAT_YELLOW_01",
      "flag": "mild_pedal_edema",
      "label": "Mild ankle/foot swelling without high BP or headache",
      "severity": "YELLOW_PHC",
      "immediate_actions": [
        "Check BP and urine albumin at PHC/ANM within 48 hours",
        "Advise left-lateral rest and foot elevation"
      ],
      "rationale": "Isolated pedal edema requires BP and urine protein verification to exclude early pre-eclampsia."
    },
    {
      "id": "MAT_YELLOW_02",
      "flag": "persistent_vomiting",
      "label": "Persistent vomiting (unable to retain regular meals)",
      "severity": "YELLOW_PHC",
      "immediate_actions": [
        "Refer to PHC/ANM for hydration assessment and safe antiemetic guidance",
        "Encourage small frequent sips of ORS and bland meals"
      ],
      "rationale": "Persistent vomiting risks dehydration and electrolyte imbalance."
    },
    {
      "id": "MAT_YELLOW_03",
      "flag": "burning_micturition",
      "label": "Burning or painful urination",
      "severity": "YELLOW_PHC",
      "immediate_actions": [
        "Refer to PHC/ANM for urine routine exam and pregnancy-safe antibiotic treatment",
        "Encourage adequate safe drinking water"
      ],
      "rationale": "Untreated UTI in pregnancy increases risk of pyelonephritis and preterm labor."
    },
    {
      "id": "MAT_YELLOW_04",
      "flag": "high_risk_obstetric_history",
      "label": "High-risk obstetric history (prior C-section, stillbirth, twins, age <18 or >35)",
      "severity": "YELLOW_PHC",
      "immediate_actions": [
        "Tag MCP card as High-Risk Pregnancy (HRP) and register for PMSMA specialist checkup on 9th of month",
        "Plan institutional delivery at FRU/CHC"
      ],
      "rationale": "NHM PMSMA guidelines mandate medical officer review and FRU delivery planning for high-risk pregnancies."
    },
    {
      "id": "MAT_YELLOW_05",
      "flag": "moderate_pallor",
      "label": "Visible mild/moderate palmar or conjunctival pallor",
      "severity": "YELLOW_PHC",
      "immediate_actions": [
        "Arrange hemoglobin testing at PHC/ANM",
        "Ensure therapeutic IFA supplementation and iron-rich diet counseling"
      ],
      "rationale": "Clinical pallor requires laboratory confirmation and targeted anemia management."
    },
    {
      "id": "MAT_YELLOW_06",
      "flag": "gestational_diabetes_gdm",
      "label": "Gestational Diabetes Mellitus (75g OGTT 2-hour glucose >=140 mg/dL or diagnosed GDM)",
      "severity": "YELLOW_PHC",
      "immediate_actions": [
        "Tag MCP card as High-Risk Pregnancy (HRP) and refer to PMSMA Medical Officer for medical nutrition therapy / insulin plan",
        "Schedule fortnightly blood glucose monitoring and plan FRU institutional delivery"
      ],
      "rationale": "NHM GDM Guidelines: uncontrolled gestational hyperglycemia increases risk of macrosomia, pre-eclampsia, and neonatal hypoglycemia."
    },
    {
      "id": "MAT_YELLOW_07",
      "flag": "rh_negative_mother",
      "label": "Rh-negative maternal blood group (Sensitization / Anti-D prophylaxis required)",
      "severity": "YELLOW_PHC",
      "immediate_actions": [
        "Tag MCP card as HRP and refer to PHC/FRU for husband blood group and Indirect Coombs Test (ICT)",
        "Plan Anti-D immunoglobulin prophylaxis at 28 weeks and within 72 hours after delivery"
      ],
      "rationale": "NHM PMSMA HRP Protocol: Rh-negative mothers require timely Anti-D prophylaxis to prevent hemolytic disease of the newborn."
    },
    {
      "id": "MAT_YELLOW_08",
      "flag": "twin_or_multiple_gestation",
      "label": "Twin or multiple pregnancy",
      "severity": "YELLOW_PHC",
      "immediate_actions": [
        "Tag MCP card as HRP and schedule monthly PMSMA obstetrician checkups",
        "Mandate institutional delivery at FRU/District Hospital with SNCU support"
      ],
      "rationale": "Multiple gestation carries elevated risk of preterm birth, anemia, pre-eclampsia, and PPH."
    },
    {
      "id": "MAT_YELLOW_09",
      "flag": "previous_lscs_history",
      "label": "Previous Caesarean section (LSCS) history without acute scar pain",
      "severity": "YELLOW_PHC",
      "immediate_actions": [
        "Tag MCP card as HRP and enroll in PMSMA specialist clinic",
        "Pre-arrange institutional delivery at FRU equipped with surgical OT and blood bank; counsel on scar-pain emergency signs"
      ],
      "rationale": "NHM HRP guidelines mandate FRU delivery planning for all previous LSCS pregnancies."
    },
    {
      "id": "MAT_YELLOW_10",
      "flag": "maternal_short_stature_or_malpresentation",
      "label": "Maternal height <145 cm or abnormal fetal lie (breech/transverse after 32 weeks)",
      "severity": "YELLOW_PHC",
      "immediate_actions": [
        "Tag MCP card as HRP and refer to PMSMA Medical Officer for cephalopelvic / presentation assessment",
        "Plan institutional delivery at FRU with C-section readiness"
      ],
      "rationale": "Short stature (<145 cm) and malpresentation elevate risk of obstructed labor."
    }
  ],
  "checklists": {
    "anc_trimester_1": {
      "title": "ANC Trimester 1 Checklist (0-12 Weeks)",
      "protocol": "NHM_ANC_T1",
      "items": [
        {
          "id": "anc_t1_mcp_registration",
          "label": "Early pregnancy registration and MCP Card issued",
          "critical": true,
          "recommended_action": "Register pregnancy at Sub-Centre/AWC and issue Mother & Child Protection (MCP) Card immediately.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t1_bp_check",
          "label": "Baseline blood pressure measured",
          "critical": true,
          "recommended_action": "Measure baseline BP at PHC/ANM to establish pre-eclampsia reference.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t1_hb_blood_group",
          "label": "Hemoglobin, blood group, and Rh typing completed",
          "critical": true,
          "recommended_action": "Refer to PHC/ANM for baseline Hb and blood group/Rh typing.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t1_urine_test",
          "label": "Urine albumin and sugar tested",
          "critical": false,
          "recommended_action": "Complete dipstick urine albumin and sugar test at next ANM clinic.",
          "escalation_severity": "GREEN_HOME"
        },
        {
          "id": "anc_t1_folic_acid",
          "label": "Daily Folic Acid (400 mcg) started",
          "critical": true,
          "recommended_action": "Provide Folic Acid 400 mcg daily supply to prevent neural tube defects.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t1_td1_vaccine",
          "label": "Td-1 (or Td-Booster) vaccination administered",
          "critical": true,
          "recommended_action": "Schedule Td-1 or Td-Booster dose at VHND/Sub-Centre.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t1_infection_screen",
          "label": "HIV, Syphilis, and HBsAg screening completed",
          "critical": false,
          "recommended_action": "Complete mandatory antenatal infection screening at PHC.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t1_danger_signs_counseling",
          "label": "Maternal danger signs and nutrition counseling given",
          "critical": false,
          "recommended_action": "Counsel mother and family on emergency warning signs and 108 transport.",
          "escalation_severity": "GREEN_HOME"
        },
        {
          "id": "anc_t1_weight_height_bmi",
          "label": "Baseline weight, maternal height (<145 cm check), and obstetric history logged",
          "critical": true,
          "recommended_action": "Record baseline weight, height, and prior LSCS/obstetric history to flag High-Risk Pregnancy early.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t1_thyroid_gdm_baseline",
          "label": "First-trimester blood glucose (OGTT) and TSH screening assessed",
          "critical": false,
          "recommended_action": "Refer to PHC for early GDM/hypothyroidism screening per NHM PMSMA protocol.",
          "escalation_severity": "YELLOW_PHC"
        }
      ]
    },
    "anc_trimester_2": {
      "title": "ANC Trimester 2 Checklist (13-27 Weeks)",
      "protocol": "NHM_ANC_T2",
      "items": [
        {
          "id": "anc_t2_bp_weight",
          "label": "Blood pressure and maternal weight gain recorded",
          "critical": true,
          "recommended_action": "Record BP and weight at PHC/VHND to monitor for hypertension and growth.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t2_repeat_hb",
          "label": "Second-trimester Hemoglobin check completed",
          "critical": true,
          "recommended_action": "Arrange repeat Hb test at PHC/ANM to screen for mid-pregnancy anemia.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t2_ifa_calcium",
          "label": "Daily IFA (Iron-Folic Acid) and Calcium tablets active",
          "critical": true,
          "recommended_action": "Dispense IFA and Calcium tablets (taken separately from tea/coffee/calcium) and verify adherence.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t2_td2_vaccine",
          "label": "Td-2 dose administered (4 weeks after Td-1)",
          "critical": true,
          "recommended_action": "Schedule Td-2 immunization at next VHND/ANM session.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t2_deworming",
          "label": "Single-dose Albendazole (400 mg) after 1st trimester",
          "critical": false,
          "recommended_action": "Provide single-dose Albendazole 400 mg under ANM guidance.",
          "escalation_severity": "GREEN_HOME"
        },
        {
          "id": "anc_t2_gdm_ogtt",
          "label": "Gestational Diabetes (75g OGTT) screening done",
          "critical": true,
          "recommended_action": "Refer to PHC/PMSMA clinic for 75g oral glucose tolerance test.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t2_fetal_movement",
          "label": "Fundal height checked and fetal movement awareness counseled",
          "critical": false,
          "recommended_action": "Counsel mother to monitor daily fetal movements after 20 weeks and report any reduction immediately.",
          "escalation_severity": "GREEN_HOME"
        },
        {
          "id": "anc_t2_usg_anomaly_scan",
          "label": "Second-trimester ultrasound (18-20w anomaly, twins, and placental site) completed",
          "critical": true,
          "recommended_action": "Arrange second-trimester USG at CHC/FRU/PMSMA clinic to detect twins, anomalies, or placenta previa.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t2_pmsma_hrp_review",
          "label": "PMSMA 9th-of-month doctor checkup and High-Risk Pregnancy (HRP) screening done",
          "critical": true,
          "recommended_action": "Ensure mother attends PMSMA clinic on the 9th of the month for Medical Officer HRP evaluation.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t2_rh_anti_d_plan",
          "label": "Rh-negative ICT / Anti-D prophylaxis status verified",
          "critical": false,
          "recommended_action": "If mother is Rh-negative, schedule Indirect Coombs Test and plan Anti-D dose at 28 weeks.",
          "escalation_severity": "YELLOW_PHC"
        }
      ]
    },
    "anc_trimester_3": {
      "title": "ANC Trimester 3 Checklist (28-40 Weeks)",
      "protocol": "NHM_ANC_T3",
      "items": [
        {
          "id": "anc_t3_bp_urine_albumin",
          "label": "Blood pressure and urine albumin checked",
          "critical": true,
          "recommended_action": "Perform urgent BP and urine albumin check at PHC/ANM to rule out late-onset pre-eclampsia.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t3_repeat_hb",
          "label": "Third-trimester Hemoglobin verified",
          "critical": true,
          "recommended_action": "Test Hemoglobin at PHC to ensure mother is safe for delivery.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t3_fetal_heart_position",
          "label": "Fetal presentation and fetal heart sound assessed",
          "critical": true,
          "recommended_action": "Arrange ANM/MO abdominal examination for fetal lie and heart rate.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t3_kick_count",
          "label": "Daily fetal movement monitoring confirmed",
          "critical": true,
          "recommended_action": "Instruct mother on daily kick-count check and immediate escalation if movements decrease.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t3_birth_preparedness",
          "label": "Institutional delivery facility, 108 transport, and blood donor identified",
          "critical": true,
          "recommended_action": "Finalize micro-birth plan with family: identified FRU/PHC, emergency 108 contact, and emergency funds.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t3_ifa_calcium_adherence",
          "label": "IFA and Calcium adherence confirmed",
          "critical": false,
          "recommended_action": "Verify remaining IFA/Calcium tablet stock and counsel daily adherence.",
          "escalation_severity": "GREEN_HOME"
        },
        {
          "id": "anc_t3_early_breastfeeding_plan",
          "label": "Early breastfeeding (within 1 hour) and newborn warmth counseled",
          "critical": false,
          "recommended_action": "Counsel family on initiating breastfeeding within 1 hour of birth and delaying first bath.",
          "escalation_severity": "GREEN_HOME"
        },
        {
          "id": "anc_t3_gdm_repeat_ogtt",
          "label": "Repeat 75g OGTT / glycemic control reviewed at 28-32 weeks",
          "critical": true,
          "recommended_action": "Complete repeat GDM screening or glycemic review at PHC/PMSMA clinic.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t3_usg_growth_liquor",
          "label": "Third-trimester fetal growth, amniotic fluid, and placental position reviewed",
          "critical": false,
          "recommended_action": "Review third-trimester growth scan or refer HRP cases for FRU ultrasound.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "anc_t3_jsy_pmmvy_readiness",
          "label": "JSY/PMMVY institutional delivery benefits and clean delivery bag verified",
          "critical": false,
          "recommended_action": "Verify MCP card, Aadhaar/bank linkage for JSY/PMMVY, and family readiness for hospital stay.",
          "escalation_severity": "GREEN_HOME"
        }
      ]
    },
    "pnc_mother": {
      "title": "Postnatal Maternal Home Visit Checklist (HBNC)",
      "protocol": "NHM_HBNC_MOTHER",
      "items": [
        {
          "id": "pnc_m_bleeding_check",
          "label": "Checked for excessive vaginal bleeding / foul-smelling lochia",
          "critical": true,
          "recommended_action": "Assess pad soakage immediately; escalate as RED_EMERGENCY if heavy bleeding or foul odor.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_m_temp_bp",
          "label": "Maternal temperature and blood pressure recorded",
          "critical": true,
          "recommended_action": "Record temperature and BP to screen for postpartum sepsis or postpartum pre-eclampsia.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_m_breast_check",
          "label": "Checked breasts for engorgement, cracked nipples, or mastitis",
          "critical": false,
          "recommended_action": "Support correct latching position and refer if fever or red tender breast lump.",
          "escalation_severity": "GREEN_HOME"
        },
        {
          "id": "pnc_m_wound_check",
          "label": "Perineal or C-section incision inspected for infection",
          "critical": true,
          "recommended_action": "Inspect incision site; refer to PHC if redness, pus, or wound opening.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_m_ifa_calcium",
          "label": "Postpartum IFA and Calcium continuation verified",
          "critical": false,
          "recommended_action": "Ensure mother continues IFA and Calcium for 6 months postpartum.",
          "escalation_severity": "GREEN_HOME"
        },
        {
          "id": "pnc_m_family_planning",
          "label": "Postpartum nutrition and spacing counseling provided",
          "critical": false,
          "recommended_action": "Counsel on extra nutritious meals, rest, and postpartum spacing options.",
          "escalation_severity": "GREEN_HOME"
        },
        {
          "id": "pnc_m_anemia_hb_recheck",
          "label": "Postpartum pallor / hemoglobin recovery assessed",
          "critical": true,
          "recommended_action": "Screen for pallor and breathlessness; arrange Hb re-check at PHC especially after PPH or antenatal anemia.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_m_danger_signs_recall",
          "label": "Mother and family counseled on postpartum sepsis, PPH, and eclampsia red flags",
          "critical": true,
          "recommended_action": "Review emergency signs requiring immediate 108 call: heavy bleeding, fever, fits, severe headache, foul discharge.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_m_urine_bowel_check",
          "label": "Normal urination and bowel function verified (no dysuria or leakage)",
          "critical": false,
          "recommended_action": "Ask about burning urination or urine leakage; refer to PHC if UTI or fistula signs present.",
          "escalation_severity": "GREEN_HOME"
        },
        {
          "id": "pnc_m_emotional_support",
          "label": "Postpartum emotional wellbeing and family support checked",
          "critical": false,
          "recommended_action": "Screen for persistent sadness, anxiety, or inability to care for self/baby; link to PHC counselor if needed.",
          "escalation_severity": "GREEN_HOME"
        }
      ]
    },
    "pnc_newborn": {
      "title": "Postnatal Newborn Home Visit Checklist (HBNC)",
      "protocol": "NHM_HBNC_NEWBORN",
      "items": [
        {
          "id": "pnc_nb_temperature_warmth",
          "label": "Newborn temperature checked (36.5-37.4C) and warmth/KMC verified",
          "critical": true,
          "recommended_action": "Measure axillary temperature; initiate Kangaroo Mother Care if cold and escalate if <35.5C or >=37.5C.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_nb_breastfeeding",
          "label": "Exclusive breastfeeding and effective latch observed",
          "critical": true,
          "recommended_action": "Observe a full feed; assist positioning and refer if infant feeds poorly or cannot suck.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_nb_respiratory_rate",
          "label": "Respiratory rate (<60/min) and no severe chest indrawing verified",
          "critical": true,
          "recommended_action": "Count breaths for 1 full minute; refer urgently if >=60/min or severe chest indrawing.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_nb_cord_stump",
          "label": "Umbilical cord stump dry with no redness or pus",
          "critical": true,
          "recommended_action": "Advise keeping cord dry (no oils/ash); refer to PHC if umbilical redness or discharge.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_nb_weight_lbw",
          "label": "Birth/visit weight recorded and LBW (<2.5 kg) flagged",
          "critical": true,
          "recommended_action": "Weigh newborn; if <2.5 kg initiate KMC + frequent feeds + extra HBNC visits; if <1.8 kg refer to SNCU.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_nb_jaundice_activity",
          "label": "Checked for yellow palms/soles (jaundice) and normal limb activity",
          "critical": true,
          "recommended_action": "Examine newborn in daylight; refer urgently if jaundice extends to palms/soles or baby is lethargic.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_nb_birth_vaccines",
          "label": "Birth doses (BCG, OPV-0, HepB-Birth) verified on MCP card",
          "critical": false,
          "recommended_action": "Verify birth vaccines on MCP card and schedule missed BCG/OPV-0 promptly.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_nb_eye_skin_infection",
          "label": "Eyes checked for purulent discharge and skin for >=10 pustules",
          "critical": true,
          "recommended_action": "Inspect eyes and skin folds; escalate urgently if >=10 skin pustules or red swollen draining eyes.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_nb_urine_stool_output",
          "label": "Adequate urine (>=6 wet nappies/day after day 4) and stool output verified",
          "critical": true,
          "recommended_action": "Confirm hydration and feeding adequacy via daily wet cloth count; support breastfeeding if <6/day.",
          "escalation_severity": "YELLOW_PHC"
        },
        {
          "id": "pnc_nb_hbnc_visit_log",
          "label": "HBNC home-visit schedule (Days 1, 3, 7, 14, 21, 28, 42) updated on MCP card",
          "critical": false,
          "recommended_action": "Log visit findings on MCP card and confirm date of next HBNC home visit with family.",
          "escalation_severity": "GREEN_HOME"
        }
      ]
    }
  }
};
