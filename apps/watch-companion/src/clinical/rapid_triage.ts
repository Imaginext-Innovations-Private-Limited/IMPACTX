/**
 * Deterministic Tier-0 Watch 1-tap WHO IMNCI & NHM Maternal Danger-Sign Screener.
 *
 * Clinical Safety Floor:
 * - Zero network calls; executes 100% locally.
 * - Any single checked pediatric or maternal danger sign deterministically forces:
 *   `severity = "RED_EMERGENCY"`, `referral_required = true`, `confidence = 1.0`,
 *   `execution_target = "LOCAL_DETERMINISTIC"`.
 * - Emits a strict `TriageAssessment`-conformant `TRIAGE_COMPLETED` payload with
 *   ONLY the exact keys allowed by `packages/contracts` (`extra="forbid"`).
 * - On `RED_EMERGENCY`, emits a companion `ACTION_CARD_ISSUED` event
 *   (`priority: "CRITICAL"`, `target_tier: "TIER_0_WATCH"`).
 */

import {
  ActionCard,
  CrdtEvent,
  HlcTimestamp,
  TriageAssessment,
  TriageSeverity,
  WatchMode,
} from "../../../../packages/contracts/ts/index";

export type WatchDangerCategory = "PEDIATRIC" | "MATERNAL";

export type WatchDangerSignFlag =
  | "not_able_to_drink_or_breastfeed"
  | "vomits_everything"
  | "convulsions"
  | "lethargic_or_unconscious"
  | "severe_respiratory_distress"
  | "cyanosis"
  | "stridor_in_calm_child"
  | "stiff_neck"
  | "severe_bleeding"
  | "very_high_fever"
  | "vaginal_bleeding"
  | "severe_headache_or_blurred_vision"
  | "convulsions_or_fits"
  | "reduced_fetal_movement"
  | "high_fever"
  | "severe_anemia_signs"
  | "severe_abdominal_pain"
  | "leaking_fluid_before_labor"
  | "swelling_face_and_hands"
  | "breathing_difficulty_or_chest_pain"
  | "umbilicus_red_or_draining_pus"
  | "poor_feeding_or_weak_cry"
  | "jaundice_palms_or_soles"
  | "grunting_or_apnea"
  | "puerperal_sepsis_signs"
  | "previous_lscs_scar_tenderness"
  | "postpartum_hemorrhage_heavy"
  | "antepartum_hemorrhage_painful_or_painless"
  | "obstructed_or_prolonged_labor";

export interface WatchDangerSignDefinition {
  readonly flag: WatchDangerSignFlag;
  readonly ruleId: string;
  readonly category: WatchDangerCategory;
  readonly labelEn: string;
  readonly labelHi: string;
  readonly labelKn: string;
  readonly labelTa: string;
  readonly immediateActions: readonly string[];
  readonly rationale: string;
}

export const WATCH_PROTOCOL_SOURCE = "WHO_IMNCI_ASHA_WATCH_RAPID" as const;

export const ALLOWED_TRIAGE_ASSESSMENT_KEYS = [
  "assessment_id",
  "patient_id",
  "severity",
  "matched_rules",
  "immediate_actions",
  "referral_required",
  "rationale",
  "confidence",
  "protocol_source",
  "execution_target",
  "assessed_at_ms",
] as const;

export const WATCH_DANGER_SIGNS: readonly WatchDangerSignDefinition[] = [
  {
    flag: "not_able_to_drink_or_breastfeed",
    ruleId: "IMNCI_GDS_01",
    category: "PEDIATRIC",
    labelEn: "Unable to drink or breastfeed",
    labelHi: "पेय अथवा स्तनपान करने में असमर्थ",
    labelKn: "ಕುಡಿಯಲು ಅಥವಾ ಹಾಲುಣಿಸಲು ಆಗುತ್ತಿಲ್ಲ",
    labelTa: "குடிக்க அல்லது தாய்ப்பால் குடிக்க முடியவில்லை",
    immediateActions: [
      "Immediate 108 emergency referral to PHC/FRU",
      "Keep child warm and prevent hypoglycemia during transport",
    ],
    rationale:
      "WHO IMNCI General Danger Sign: inability to drink or breastfeed indicates critical systemic illness.",
  },
  {
    flag: "vomits_everything",
    ruleId: "IMNCI_GDS_02",
    category: "PEDIATRIC",
    labelEn: "Vomits everything",
    labelHi: "प्रत्येक आहार पर वमन",
    labelKn: "ಎಲ್ಲವನ್ನೂ ವಾಂತಿ ಮಾಡುತ್ತಿದೆ",
    labelTa: "எல்லாவற்றையும் வாந்தி எடுக்கிறது",
    immediateActions: [
      "Immediate 108 emergency referral to PHC/FRU",
      "Offer small frequent sips of ORS if conscious during transport",
    ],
    rationale:
      "WHO IMNCI General Danger Sign: persistent vomiting prevents oral rehydration and medication.",
  },
  {
    flag: "convulsions",
    ruleId: "IMNCI_GDS_03",
    category: "PEDIATRIC",
    labelEn: "Convulsions",
    labelHi: "आक्षेप",
    labelKn: "ಸೆಳೆತ / ಫಿಟ್ಸ್",
    labelTa: "வலிப்பு",
    immediateActions: [
      "Place child in left lateral recovery position and keep airway clear",
      "Do NOT put anything in the mouth",
      "Immediate 108 emergency referral to PHC/FRU",
    ],
    rationale:
      "WHO IMNCI General Danger Sign: convulsions indicate possible meningitis, cerebral malaria, or severe metabolic emergency.",
  },
  {
    flag: "lethargic_or_unconscious",
    ruleId: "IMNCI_GDS_04",
    category: "PEDIATRIC",
    labelEn: "Lethargic or unconscious",
    labelHi: "अत्यंत शिथिल अथवा अचेत",
    labelKn: "ತೀವ್ರ ನಿತ್ರಾಣ ಅಥವಾ ಪ್ರಜ್ಞೆ ತಪ್ಪಿದೆ",
    labelTa: "அதிக சோர்வு அல்லது மயக்கம்",
    immediateActions: [
      "Check airway and breathing; position safely on side",
      "Immediate 108 emergency referral to PHC/FRU",
      "Prevent hypothermia with skin-to-skin warmth or blanket",
    ],
    rationale:
      "WHO IMNCI General Danger Sign: altered consciousness indicates critical neurological or circulatory compromise.",
  },
  {
    flag: "severe_respiratory_distress",
    ruleId: "IMNCI_GDS_05",
    category: "PEDIATRIC",
    labelEn: "Severe respiratory distress",
    labelHi: "तीव्र श्वास कष्ट",
    labelKn: "ತೀವ್ರ ಉಸಿರಾಟದ ತೊಂದರೆ",
    labelTa: "கடுமையான மூச்சுத் திணறல்",
    immediateActions: [
      "Keep child calm and upright; clear nasal passages gently",
      "Immediate 108 emergency referral to oxygen-equipped PHC/FRU",
    ],
    rationale:
      "WHO IMNCI Severe Respiratory Distress: high risk of hypoxemia and respiratory failure.",
  },
  {
    flag: "cyanosis",
    ruleId: "IMNCI_GDS_06",
    category: "PEDIATRIC",
    labelEn: "Bluish lips or tongue (cyanosis)",
    labelHi: "ओष्ठ अथवा जिह्वा का नीलवर्ण",
    labelKn: "ತುಟಿ ಅಥವಾ ನಾಲಿಗೆ ನೀಲಿ ಬಣ್ಣ",
    labelTa: "உதடு அல்லது நாக்கு நீல நிறம்",
    immediateActions: [
      "Immediate 108 emergency referral to oxygen-equipped PHC/FRU",
      "Maintain open airway and keep child calm and warm",
    ],
    rationale: "Central cyanosis indicates life-threatening hypoxemia.",
  },
  {
    flag: "stridor_in_calm_child",
    ruleId: "IMNCI_GDS_07",
    category: "PEDIATRIC",
    labelEn: "Stridor in a calm child",
    labelHi: "शांत शिशु में कर्कश श्वास ध्वनि",
    labelKn: "ಶಾಂತ ಮಗುವಿನಲ್ಲಿ ಗೊರಕೆ ಉಸಿರಾಟ",
    labelTa: "அமைதியான குழந்தையில் கரகரப்பு மூச்சு",
    immediateActions: [
      "Keep child calm in caregiver's lap; avoid unnecessary agitation",
      "Immediate 108 emergency referral to PHC/FRU for airway management",
    ],
    rationale:
      "WHO IMNCI Severe Pneumonia / Upper Airway Obstruction: stridor at rest risks acute airway closure.",
  },
  {
    flag: "stiff_neck",
    ruleId: "IMNCI_GDS_08",
    category: "PEDIATRIC",
    labelEn: "Stiff neck or bulging fontanelle",
    labelHi: "ग्रीवा स्तंभता",
    labelKn: "ಕುತ್ತಿಗೆ ಬಿಗಿತ ಅಥವಾ ನೆತ್ತಿ ಉಬ್ಬು",
    labelTa: "கழுத்து இறுக்கம் அல்லது உச்சி வீக்கம்",
    immediateActions: [
      "Immediate 108 emergency referral to FRU/District Hospital for suspected meningitis",
      "Give first pre-referral dose of antibiotic per ANM/MO standing order if available",
    ],
    rationale:
      "WHO IMNCI Very Severe Febrile Disease: stiff neck is a hallmark sign of acute meningitis.",
  },
  {
    flag: "severe_bleeding",
    ruleId: "IMNCI_GDS_09",
    category: "PEDIATRIC",
    labelEn: "Severe bleeding",
    labelHi: "अत्यधिक रक्तस्राव",
    labelKn: "ತೀವ್ರ ರಕ್ತಸ್ರಾವ",
    labelTa: "அதிக ரத்தப்போக்கு",
    immediateActions: [
      "Apply direct clean pressure if external bleeding",
      "Immediate 108 emergency referral to FRU/District Hospital",
    ],
    rationale:
      "Active hemorrhage or hemorrhagic fever requires urgent hospital stabilization.",
  },
  {
    flag: "very_high_fever",
    ruleId: "IMNCI_GDS_10",
    category: "PEDIATRIC",
    labelEn: "Very high fever",
    labelHi: "अति उच्च ज्वर",
    labelKn: "ಅತಿ ಹೆಚ್ಚು ಜ್ವರ",
    labelTa: "அதிகப்படியான காய்ச்சல்",
    immediateActions: [
      "Begin tepid sponging and administer age-appropriate paracetamol if able to swallow",
      "Immediate 108 emergency referral to PHC/FRU for severe febrile illness evaluation",
    ],
    rationale:
      "Hyperpyrexia carries high risk of febrile seizures, sepsis, or cerebral malaria.",
  },
  {
    flag: "vaginal_bleeding",
    ruleId: "MAT_RED_03",
    category: "MATERNAL",
    labelEn: "Vaginal bleeding",
    labelHi: "योनि से रक्तस्राव",
    labelKn: "ಯೋನಿಯಿಂದ ರಕ್ತಸ್ರಾವ",
    labelTa: "பிறப்புறுப்பு ரத்தப்போக்கு",
    immediateActions: [
      "Immediate 108 emergency referral to FRU/District Hospital",
      "Keep mother lying flat on left side with legs elevated; arrange blood donor contact",
      "Do NOT perform vaginal examination in field setting",
    ],
    rationale:
      "Antepartum or postpartum hemorrhage is a leading cause of maternal mortality requiring urgent hospital care.",
  },
  {
    flag: "severe_headache_or_blurred_vision",
    ruleId: "MAT_RED_01",
    category: "MATERNAL",
    labelEn: "Severe headache or blurred vision",
    labelHi: "तीव्र शिरोवेदना अथवा अस्पष्ट दृष्टि",
    labelKn: "ತೀವ್ರ ತಲೆನೋವು ಅಥವಾ ಮಸುಕು ದೃಷ್ಟಿ",
    labelTa: "கடும் தலைவலி அல்லது மங்கலான பார்வை",
    immediateActions: [
      "Suspect Pre-eclampsia / impending Eclampsia — measure BP immediately",
      "Immediate 108 emergency referral to FRU/CHC/District Hospital",
      "Keep mother lying on her left side in a quiet, dimly lit space during transport",
    ],
    rationale:
      "Severe headache or visual disturbance in pregnancy/postpartum is a critical pre-eclampsia danger sign.",
  },
  {
    flag: "convulsions_or_fits",
    ruleId: "MAT_RED_02",
    category: "MATERNAL",
    labelEn: "Maternal convulsions or fits (eclampsia)",
    labelHi: "गर्भावस्था में आक्षेप एवं मूर्च्छा",
    labelKn: "ಗರ್ಭಿಣಿಗೆ ಸೆಳೆತ / ಫಿಟ್ಸ್",
    labelTa: "கர்ப்பிணிக்கு வலிப்பு",
    immediateActions: [
      "Protect airway, turn mother onto left lateral side, do NOT restrain or put anything in mouth",
      "Immediate 108 emergency transfer to FRU for Magnesium Sulfate and emergency obstetric care",
    ],
    rationale:
      "Eclampsia is an immediate maternal and fetal life-threatening emergency.",
  },
  {
    flag: "reduced_fetal_movement",
    ruleId: "MAT_RED_04",
    category: "MATERNAL",
    labelEn: "Reduced or absent fetal movement",
    labelHi: "गर्भस्थ शिशु की गति में न्यूनता",
    labelKn: "ಹೊಟ್ಟೆಯಲ್ಲಿ ಮಗುವಿನ ಚಲನೆ ಕಡಿಮೆ",
    labelTa: "வயிற்றில் குழந்தை அசைவு குறைவு",
    immediateActions: [
      "Immediate 108 emergency referral to FRU/PHC for fetal heart rate and ultrasound assessment",
      "Advise mother to lie on left side while arranging transport",
    ],
    rationale:
      "Reduced or absent fetal movement signals potential fetal distress or compromise.",
  },
  {
    flag: "high_fever",
    ruleId: "MAT_RED_05",
    category: "MATERNAL",
    labelEn: "High maternal fever",
    labelHi: "माता को उच्च ज्वर",
    labelKn: "ತಾಯಿಗೆ ಹೆಚ್ಚು ಜ್ವರ",
    labelTa: "தாய்க்கு அதிக காய்ச்சல்",
    immediateActions: [
      "Immediate 108 emergency referral to FRU/PHC for maternal sepsis management",
      "Give oral fluids and paracetamol if able to swallow during transport",
    ],
    rationale:
      "High maternal fever indicates possible obstetric sepsis requiring parenteral antibiotics.",
  },
  {
    flag: "severe_anemia_signs",
    ruleId: "MAT_RED_06",
    category: "MATERNAL",
    labelEn: "Severe pallor with breathlessness",
    labelHi: "अत्यधिक पांडुता एवं श्वास कष्ट",
    labelKn: "ತೀವ್ರ ರಕ್ತಹೀನತೆ ಮತ್ತು ಉಸಿರಾಟ ಕಷ್ಟ",
    labelTa: "கடும் ரத்தசோகை மற்றும் மூச்சுத் திணறல்",
    immediateActions: [
      "Immediate 108 emergency referral to FRU/CHC for hemoglobin check and possible IV iron or blood transfusion",
      "Keep mother resting upright; avoid exertion",
    ],
    rationale:
      "Severe anemia (Hb < 7 g/dL) increases risk of cardiac failure and fatal postpartum hemorrhage.",
  },
  {
    flag: "severe_abdominal_pain",
    ruleId: "MAT_RED_07",
    category: "MATERNAL",
    labelEn: "Severe abdominal pain",
    labelHi: "तीव्र उदर शूल",
    labelKn: "ತೀವ್ರ ಹೊಟ್ಟೆ ನೋವು",
    labelTa: "கடும் வயிற்று வலி",
    immediateActions: [
      "Immediate 108 emergency referral to FRU/District Hospital (rule out placental abruption, ectopic pregnancy, or HELLP syndrome)",
    ],
    rationale:
      "Severe abdominal or right-upper-quadrant pain in pregnancy is an obstetric red flag.",
  },
  {
    flag: "leaking_fluid_before_labor",
    ruleId: "MAT_RED_08",
    category: "MATERNAL",
    labelEn: "Water breaking / leaking fluid before labor",
    labelHi: "प्रसव पूर्व जलस्राव",
    labelKn: "ಹೆರಿಗೆಗೆ ಮುನ್ನ ನೀರು ಸೋರುವಿಕೆ",
    labelTa: "பிரசவத்திற்கு முன் பனிக்குடம் உடைதல்",
    immediateActions: [
      "Immediate 108 emergency referral to FRU/PHC for PROM/PPROM assessment and infection prophylaxis",
      "Keep clean pad and avoid vaginal insertion",
    ],
    rationale:
      "Premature rupture of membranes carries high risk of ascending infection and cord prolapse.",
  },
  {
    flag: "swelling_face_and_hands",
    ruleId: "MAT_RED_09",
    category: "MATERNAL",
    labelEn: "Sudden swelling of face and hands",
    labelHi: "मुख एवं हस्त पर आकस्मिक शोथ",
    labelKn: "ಮುಖ ಮತ್ತು ಕೈಗಳಲ್ಲಿ ದಿಢೀರ್ ಊತ",
    labelTa: "முகம் மற்றும் கைகளில் திடீர் வீக்கம்",
    immediateActions: [
      "Check BP immediately and refer urgently via 108 to FRU/PHC for pre-eclampsia evaluation",
    ],
    rationale:
      "Facial or hand edema suggests systemic endothelial dysfunction associated with pre-eclampsia.",
  },
  {
    flag: "breathing_difficulty_or_chest_pain",
    ruleId: "MAT_RED_10",
    category: "MATERNAL",
    labelEn: "Maternal breathing difficulty or chest pain",
    labelHi: "तीव्र श्वास कष्ट अथवा वक्ष शूल",
    labelKn: "ಉಸಿರಾಟದ ತೊಂದರೆ ಅಥವಾ ಎದೆ ನೋವು",
    labelTa: "மூச்சுத் திணறல் அல்லது நெஞ்சு வலி",
    immediateActions: [
      "Seat mother upright and arrange immediate 108 emergency transfer to FRU",
    ],
    rationale:
      "Acute dyspnea or chest pain may indicate pulmonary edema, embolism, or peripartum cardiomyopathy.",
  },
  {
    flag: "umbilicus_red_or_draining_pus",
    ruleId: "IMNCI_PSBI_01",
    category: "PEDIATRIC",
    labelEn: "Umbilicus red or draining pus (<2m)",
    labelHi: "नाभि में लालिमा अथवा पूय स्राव",
    labelKn: "ಹೊಕ್ಕುಳ ಕೆಂಪು ಅಥವಾ ಕೀವು (<2 ತಿಂಗಳು)",
    labelTa: "தொப்புள் சிவப்பு அல்லது சீழ் (<2 மாதம்)",
    immediateActions: [
      "Immediate 108 emergency referral to SNCU/FRU for Possible Serious Bacterial Infection (PSBI)",
      "Keep cord clean and dry; do NOT apply oils or ash",
    ],
    rationale:
      "WHO IMNCI Young Infant (<2 months): umbilical redness or pus indicates neonatal sepsis risk.",
  },
  {
    flag: "poor_feeding_or_weak_cry",
    ruleId: "IMNCI_PSBI_03",
    category: "PEDIATRIC",
    labelEn: "Poor feeding or weak cry (<2m)",
    labelHi: "स्तनपान में अक्षमता अथवा क्षीण रुदन",
    labelKn: "ಹಾಲು ಕುಡಿಯದಿರುವುದು / ಕ್ಷೀಣ ಅಳು (<2 ತಿಂಗಳು)",
    labelTa: "பால் குடிக்காமை / பலவீன அழுகை (<2 மாதம்)",
    immediateActions: [
      "Immediate 108 emergency referral to SNCU/FRU",
      "Keep infant warm skin-to-skin during transfer",
    ],
    rationale:
      "WHO IMNCI Young Infant (<2 months): poor feeding or weak cry is a cardinal sign of neonatal sepsis.",
  },
  {
    flag: "jaundice_palms_or_soles",
    ruleId: "IMNCI_PSBI_04",
    category: "PEDIATRIC",
    labelEn: "Yellow palms or soles (<2m jaundice)",
    labelHi: "पीली हथेलियाँ अथवा तलवे (कामला)",
    labelKn: "ಅಂಗೈ ಅಥವಾ ಅಂಗಾಲು ಹಳದಿ (<2 ತಿಂಗಳು)",
    labelTa: "உள்ளங்கை / உள்ளங்கால் மஞ்சள் (<2 மாதம்)",
    immediateActions: [
      "Urgent referral to SNCU/District Hospital for serum bilirubin and phototherapy",
    ],
    rationale:
      "WHO IMNCI Young Infant (<2 months): jaundice reaching palms or soles risks kernicterus.",
  },
  {
    flag: "grunting_or_apnea",
    ruleId: "IMNCI_PSBI_05",
    category: "PEDIATRIC",
    labelEn: "Grunting or breathing pauses (<2m)",
    labelHi: "नवजात में कराहना अथवा श्वास विराम",
    labelKn: "ನರಳಾಟ ಅಥವಾ ಉಸಿರು ನಿಲ್ಲುವುದು (<2 ತಿಂಗಳು)",
    labelTa: "முனகல் அல்லது மூச்சு நிற்றல் (<2 மாதம்)",
    immediateActions: [
      "Immediate 108 emergency transfer to oxygen-equipped SNCU/FRU",
    ],
    rationale:
      "WHO IMNCI Young Infant (<2 months): expiratory grunting or apnea indicates severe neonatal sepsis.",
  },
  {
    flag: "puerperal_sepsis_signs",
    ruleId: "MAT_RED_11",
    category: "MATERNAL",
    labelEn: "Postpartum fever / foul discharge",
    labelHi: "प्रसवोत्तर ज्वर अथवा दुर्गन्धयुक्त स्राव",
    labelKn: "ಹೆರಿಗೆ ನಂತರ ಜ್ವರ / ದುರ್ವಾಸನೆ ಸ್ರಾವ",
    labelTa: "பிரசவத்திற்கு பின் காய்ச்சல் / துர்நாற்ற கசிவு",
    immediateActions: [
      "Immediate 108 emergency referral to FRU/District Hospital for parenteral antibiotics",
    ],
    rationale:
      "NHM HBNC Protocol: puerperal sepsis progresses rapidly to septic shock without IV antibiotics.",
  },
  {
    flag: "previous_lscs_scar_tenderness",
    ruleId: "MAT_RED_12",
    category: "MATERNAL",
    labelEn: "Prior C-section scar pain",
    labelHi: "पूर्व शल्य प्रसव क्षत पर तीव्र शूल",
    labelKn: "ಹಿಂದಿನ ಸಿಜೇರಿಯನ್ ಗಾಯದಲ್ಲಿ ನೋವು",
    labelTa: "முந்தைய சிசேரியன் தழும்பில் வலி",
    immediateActions: [
      "Immediate 108 emergency transfer to FRU/District Hospital with emergency obstetric OT",
    ],
    rationale:
      "Scar tenderness in a previous LSCS pregnancy signals impending uterine rupture.",
  },
  {
    flag: "postpartum_hemorrhage_heavy",
    ruleId: "MAT_RED_14",
    category: "MATERNAL",
    labelEn: "Heavy postpartum bleeding (PPH)",
    labelHi: "प्रसवोत्तर अत्यधिक रक्तस्राव",
    labelKn: "ಹೆರಿಗೆ ನಂತರ ತೀವ್ರ ರಕ್ತಸ್ರಾವ",
    labelTa: "பிரசவத்திற்கு பின் அதிக ரத்தப்போக்கு",
    immediateActions: [
      "Call 108 immediately for emergency transfer to FRU with blood transfusion capability",
      "Keep mother flat with legs elevated and keep warm",
    ],
    rationale:
      "Postpartum hemorrhage (PPH) is the single leading cause of maternal death in rural India.",
  },
  {
    flag: "antepartum_hemorrhage_painful_or_painless",
    ruleId: "MAT_RED_15",
    category: "MATERNAL",
    labelEn: "Late pregnancy bleeding (APH)",
    labelHi: "प्रसवपूर्व योनि रक्तस्राव",
    labelKn: "ಗರ್ಭಾವಸ್ಥೆಯ ಕೊನೆಯಲ್ಲಿ ರಕ್ತಸ್ರಾವ",
    labelTa: "கர்ப்பத்தின் இறுதியில் ரத்தப்போக்கு",
    immediateActions: [
      "Immediate 108 transfer to FRU with surgical and blood bank facility",
      "Strictly NO vaginal examination; keep mother on left lateral side",
    ],
    rationale:
      "Antepartum hemorrhage suggests placenta previa or abruptio placentae requiring immediate hospital care.",
  },
  {
    flag: "obstructed_or_prolonged_labor",
    ruleId: "MAT_RED_16",
    category: "MATERNAL",
    labelEn: "Prolonged / obstructed labor (>12h)",
    labelHi: "अवरुद्ध अथवा विलम्बित प्रसव",
    labelKn: "ದೀರ್ಘ / ತಡೆದ ಹೆರಿಗೆ (>12 ಗಂಟೆ)",
    labelTa: "நீடித்த / தடைபட்ட பிரசவம் (>12 மணி)",
    immediateActions: [
      "Immediate 108 emergency transfer to FRU/CHC for obstetric evaluation",
    ],
    rationale:
      "Obstructed labor risks uterine rupture, fetal asphyxia, and obstetric fistula.",
  },
] as const;

const DANGER_SIGN_BY_FLAG: ReadonlyMap<WatchDangerSignFlag, WatchDangerSignDefinition> =
  new Map(WATCH_DANGER_SIGNS.map((item) => [item.flag, item]));

const FLAG_ALIASES: Readonly<Record<string, WatchDangerSignFlag>> = {
  unable_to_drink: "not_able_to_drink_or_breastfeed",
  unable_to_drink_or_breastfeed: "not_able_to_drink_or_breastfeed",
  cannot_drink: "not_able_to_drink_or_breastfeed",
  cannot_breastfeed: "not_able_to_drink_or_breastfeed",
  vomiting_everything: "vomits_everything",
  persistent_vomiting_all: "vomits_everything",
  seizures: "convulsions",
  fits: "convulsions",
  lethargic: "lethargic_or_unconscious",
  unconscious: "lethargic_or_unconscious",
  abnormally_sleepy: "lethargic_or_unconscious",
  severe_breathing_difficulty: "severe_respiratory_distress",
  severe_chest_indrawing: "severe_respiratory_distress",
  gasping: "severe_respiratory_distress",
  bluish_lips: "cyanosis",
  central_cyanosis: "cyanosis",
  stridor: "stridor_in_calm_child",
  bulging_fontanelle: "stiff_neck",
  severe_headache: "severe_headache_or_blurred_vision",
  blurred_vision: "severe_headache_or_blurred_vision",
  visual_disturbance: "severe_headache_or_blurred_vision",
  eclampsia: "convulsions_or_fits",
  pph: "vaginal_bleeding",
  antepartum_bleeding: "vaginal_bleeding",
  postpartum_bleeding: "vaginal_bleeding",
  absent_fetal_movement: "reduced_fetal_movement",
  decreased_fetal_movement: "reduced_fetal_movement",
  reduced_or_absent_fetal_movement: "reduced_fetal_movement",
  prom: "leaking_fluid_before_labor",
  water_breaking: "leaking_fluid_before_labor",
  epigastric_pain: "severe_abdominal_pain",
  severe_pallor: "severe_anemia_signs",
  facial_swelling: "swelling_face_and_hands",
  chest_pain: "breathing_difficulty_or_chest_pain",
  umbilical_pus: "umbilicus_red_or_draining_pus",
  omphalitis: "umbilicus_red_or_draining_pus",
  poor_feeding: "poor_feeding_or_weak_cry",
  weak_cry: "poor_feeding_or_weak_cry",
  yellow_palms_soles: "jaundice_palms_or_soles",
  grunting: "grunting_or_apnea",
  apnea: "grunting_or_apnea",
  puerperal_sepsis: "puerperal_sepsis_signs",
  foul_lochia: "puerperal_sepsis_signs",
  scar_tenderness: "previous_lscs_scar_tenderness",
  postpartum_hemorrhage: "postpartum_hemorrhage_heavy",
  antepartum_hemorrhage: "antepartum_hemorrhage_painful_or_painless",
  obstructed_labor: "obstructed_or_prolonged_labor",
  prolonged_labor: "obstructed_or_prolonged_labor",
};

export interface WatchDangerScreenInput {
  patientId?: string | null;
  nodeId?: string;
  hlc?: HlcTimestamp;
  tickHlc?: () => HlcTimestamp;
  language?: "en" | "hi" | "kn" | "ta";
  watchMode?: WatchMode | null;
  dangerSigns?: readonly string[];
  unableToDrinkOrBreastfeed?: boolean;
  vomitsEverything?: boolean;
  convulsions?: boolean;
  lethargicOrUnconscious?: boolean;
  severeRespiratoryDistress?: boolean;
  severeBleeding?: boolean;
  vaginalBleeding?: boolean;
  severeHeadacheOrBlurredVision?: boolean;
  convulsionsOrFits?: boolean;
  assessmentId?: string;
  triageEventId?: string;
  cardId?: string;
  actionCardEventId?: string;
  assessedAtMs?: number;
}

export interface WatchDangerScreenResult {
  severity: TriageSeverity;
  assessment: TriageAssessment;
  triageEvent: CrdtEvent;
  actionCard: ActionCard | null;
  actionCardEvent: CrdtEvent | null;
  events: CrdtEvent[];
}

function normalizeFlagToken(rawFlag: string): string {
  return rawFlag.trim().toLowerCase().replace(/[-\s]+/g, "_");
}

function resolveDangerFlag(rawFlag: string): WatchDangerSignFlag | string | null {
  const token = normalizeFlagToken(rawFlag);
  if (!token) {
    return null;
  }
  const canonical = FLAG_ALIASES[token] ?? token;
  return canonical;
}

function dedupePreserveOrder(items: readonly string[]): string[] {
  const seen = new Set<string>();
  const result: string[] = [];
  for (const item of items) {
    if (!seen.has(item)) {
      seen.add(item);
      result.push(item);
    }
  }
  return result;
}

function createId(): string {
  if (typeof globalThis.crypto !== "undefined" && typeof globalThis.crypto.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  const rand = Math.random().toString(36).slice(2, 10);
  return `watch-${Date.now().toString(36)}-${rand}`;
}

function normalizePatientId(patientId: string | null | undefined): string | null {
  if (typeof patientId !== "string") {
    return null;
  }
  const trimmed = patientId.trim();
  return trimmed.length > 0 ? trimmed.slice(0, 128) : null;
}

function collectCheckedFlags(input: WatchDangerScreenInput): string[] {
  const collected: string[] = [];

  if (input.unableToDrinkOrBreastfeed) collected.push("not_able_to_drink_or_breastfeed");
  if (input.vomitsEverything) collected.push("vomits_everything");
  if (input.convulsions) collected.push("convulsions");
  if (input.lethargicOrUnconscious) collected.push("lethargic_or_unconscious");
  if (input.severeRespiratoryDistress) collected.push("severe_respiratory_distress");
  if (input.severeBleeding) collected.push("severe_bleeding");
  if (input.vaginalBleeding) collected.push("vaginal_bleeding");
  if (input.severeHeadacheOrBlurredVision) {
    collected.push("severe_headache_or_blurred_vision");
  }
  if (input.convulsionsOrFits) collected.push("convulsions_or_fits");

  if (input.dangerSigns) {
    for (const raw of input.dangerSigns) {
      const resolved = resolveDangerFlag(raw);
      if (resolved !== null) {
        collected.push(resolved);
      }
    }
  }

  return dedupePreserveOrder(collected);
}

/**
 * Deterministically screens pediatric WHO IMNCI and maternal danger signs on Tier-0 Watch.
 *
 * Any single checked danger sign forces `RED_EMERGENCY`, `referral_required: true`,
 * `confidence: 1.0`, `execution_target: "LOCAL_DETERMINISTIC"`, and emits a companion
 * `CRITICAL` `ACTION_CARD_ISSUED` event for immediate 108 emergency guidance.
 */
export function evaluateWatchDangerScreen(
  input: WatchDangerScreenInput,
): WatchDangerScreenResult {
  const nodeId = input.nodeId && input.nodeId.trim().length > 0 ? input.nodeId.trim() : "watch-local";
  const triageHlc: HlcTimestamp = input.tickHlc
    ? input.tickHlc()
    : input.hlc ?? { wall_ms: Date.now(), logical: 0, node_id: nodeId };

  const normalizedPatientId = normalizePatientId(input.patientId);
  const checkedFlags = collectCheckedFlags(input);
  const hasDangerSign = checkedFlags.length > 0;

  const matchedRules: string[] = [];
  const immediateActions: string[] = [];
  const rationales: string[] = [];
  const labelsHi: string[] = [];
  const labelsKn: string[] = [];
  const labelsTa: string[] = [];

  for (const flag of checkedFlags) {
    const def = DANGER_SIGN_BY_FLAG.get(flag as WatchDangerSignFlag);
    if (def) {
      matchedRules.push(def.ruleId);
      immediateActions.push(...def.immediateActions);
      rationales.push(def.rationale);
      labelsHi.push(def.labelHi);
      labelsKn.push(def.labelKn);
      labelsTa.push(def.labelTa);
    } else {
      matchedRules.push(`WATCH_DANGER_SIGN_${flag.toUpperCase()}`);
      immediateActions.push("Immediate 108 emergency referral to PHC/FRU");
      rationales.push(`Tier-0 Watch danger sign detected (${flag}).`);
      labelsHi.push("आपातकालीन संकट संकेत");
      labelsKn.push("ತುರ್ತು ಅಪಾಯದ ಲಕ್ಷಣ");
      labelsTa.push("அவசர ஆபத்து அறிகுறி");
    }
  }

  const severity: TriageSeverity = hasDangerSign ? "RED_EMERGENCY" : "GREEN_HOME";
  const assessedAtMs = input.assessedAtMs ?? triageHlc.wall_ms;

  const assessment: TriageAssessment = {
    assessment_id: input.assessmentId ?? createId(),
    patient_id: normalizedPatientId,
    severity,
    matched_rules: hasDangerSign
      ? dedupePreserveOrder(matchedRules)
      : ["WATCH_RAPID_NO_DANGER_SIGNS"],
    immediate_actions: hasDangerSign
      ? dedupePreserveOrder([
          "Immediate 108 emergency referral to PHC/FRU",
          ...immediateActions,
        ])
      : ["Continue home monitoring and routine ASHA follow-up"],
    referral_required: hasDangerSign,
    rationale: hasDangerSign
      ? `Tier-0 Watch danger sign detected (${checkedFlags.join(", ")}). ${dedupePreserveOrder(rationales).join(" ")}`
      : "No immediate danger signs detected on Tier-0 Watch screen.",
    confidence: 1.0,
    protocol_source: WATCH_PROTOCOL_SOURCE,
    execution_target: "LOCAL_DETERMINISTIC",
    assessed_at_ms: assessedAtMs,
  };

  const triageEventId = input.triageEventId ?? createId();
  const triageEvent: CrdtEvent = {
    event_id: triageEventId,
    hlc: triageHlc,
    origin_node_id: nodeId,
    patient_id: normalizedPatientId,
    event_type: "TRIAGE_COMPLETED",
    payload: {
      assessment_id: assessment.assessment_id,
      patient_id: assessment.patient_id,
      severity: assessment.severity,
      matched_rules: assessment.matched_rules,
      immediate_actions: assessment.immediate_actions,
      referral_required: assessment.referral_required,
      rationale: assessment.rationale,
      confidence: assessment.confidence,
      protocol_source: assessment.protocol_source,
      execution_target: assessment.execution_target,
      assessed_at_ms: assessment.assessed_at_ms,
    },
    enrichment_state: "NOT_NEEDED",
    ref_event_id: null,
  };

  if (!hasDangerSign) {
    return {
      severity,
      assessment,
      triageEvent,
      actionCard: null,
      actionCardEvent: null,
      events: [triageEvent],
    };
  }

  const language: "en" | "hi" | "kn" | "ta" =
    input.language === "hi"
      ? "hi"
      : input.language === "kn"
        ? "kn"
        : input.language === "ta"
          ? "ta"
          : "en";
  const cardHlc: HlcTimestamp = input.tickHlc
    ? input.tickHlc()
    : {
        wall_ms: triageHlc.wall_ms,
        logical: triageHlc.logical + 1,
        node_id: triageHlc.node_id,
      };

  const uniqueLabelsHi = dedupePreserveOrder(labelsHi);
  const uniqueLabelsKn = dedupePreserveOrder(labelsKn);
  const uniqueLabelsTa = dedupePreserveOrder(labelsTa);
  const actionCard: ActionCard = {
    card_id: input.cardId ?? createId(),
    patient_id: normalizedPatientId,
    title:
      language === "hi"
        ? "गंभीर आपातकाल: तत्काल चिकित्सालय संदर्भ"
        : language === "kn"
          ? "ಕೆಂಪು ತುರ್ತು: ತಕ್ಷಣ 108 ಆಸ್ಪತ್ರೆಗೆ ಕರೆದೊಯ್ಯಿರಿ"
          : language === "ta"
            ? "சிவப்பு அவசரம்: உடனடி 108 மருத்துவமனை பரிந்துரை"
            : "RED EMERGENCY: Immediate 108 Referral",
    summary: (language === "hi"
      ? `आपातकालीन संकट संकेत (${uniqueLabelsHi.join(", ")})। रोगी वाहन 108 से तत्काल चिकित्सालय ले जाएं।`
      : language === "kn"
        ? `ತುರ್ತು ಅಪಾಯದ ಲಕ್ಷಣ (${uniqueLabelsKn.join(", ")}). ತಕ್ಷಣ 108 ಆಂಬ್ಯುಲೆನ್ಸ್ ಕರೆ ಮಾಡಿ ಆಸ್ಪತ್ರೆಗೆ ಕರೆದೊಯ್ಯಿರಿ.`
        : language === "ta"
          ? `அவசர ஆபத்து அறிகுறி (${uniqueLabelsTa.join(", ")}). உடனடியாக 108 ஆம்புலன்ஸ் அழைத்து மருத்துவமனைக்கு அழைத்துச் செல்லவும்.`
          : assessment.rationale
    ).slice(0, 1000),
    action_steps:
      language === "hi"
        ? [
            "रोगी वाहन 108 पर तत्काल संपर्क करें",
            "निकटतम प्राथमिक स्वास्थ्य केंद्र अथवा चिकित्सालय ले जाएं",
            "यात्रा के समय रोगी को शांत एवं सुरक्षित स्थिति में रखें",
          ]
        : language === "kn"
          ? [
              "ತಕ್ಷಣ 108 ತುರ್ತು ಆಂಬ್ಯುಲೆನ್ಸ್‌ಗೆ ಕರೆ ಮಾಡಿ",
              "ಹತ್ತಿರದ ಪ್ರಾಥಮಿಕ ಆರೋಗ್ಯ ಕೇಂದ್ರ (PHC) ಅಥವಾ ಆಸ್ಪತ್ರೆಗೆ ಕರೆದೊಯ್ಯಿರಿ",
              "ಪ್ರಯಾಣದ ಸಮಯದಲ್ಲಿ ರೋಗಿಯನ್ನು ಶಾಂತವಾಗಿ ಮತ್ತು ಸುರಕ್ಷಿತವಾಗಿ ಇರಿಸಿ",
            ]
          : language === "ta"
            ? [
                "உடனடியாக 108 அவசர ஆம்புலன்ஸை அழைக்கவும்",
                "அருகிலுள்ள ஆரம்ப சுகாதார நிலையம் (PHC) அல்லது மருத்துவமனைக்கு அழைத்துச் செல்லவும்",
                "பயணத்தின் போது நோயாளியை அமைதியாகவும் பாதுகாப்பாகவும் வைத்திருக்கவும்",
              ]
            : [...assessment.immediate_actions],
    priority: "CRITICAL",
    severity: "RED_EMERGENCY",
    status: "OPEN",
    target_tier: "TIER_0_WATCH",
    watch_mode: input.watchMode ?? null,
    source_event_id: triageEvent.event_id,
    due_by: null,
    language,
  };

  const actionCardEvent: CrdtEvent = {
    event_id: input.actionCardEventId ?? createId(),
    hlc: cardHlc,
    origin_node_id: nodeId,
    patient_id: normalizedPatientId,
    event_type: "ACTION_CARD_ISSUED",
    payload: {
      card_id: actionCard.card_id,
      patient_id: actionCard.patient_id,
      title: actionCard.title,
      summary: actionCard.summary,
      action_steps: actionCard.action_steps,
      priority: actionCard.priority,
      severity: actionCard.severity,
      status: actionCard.status,
      target_tier: actionCard.target_tier,
      watch_mode: actionCard.watch_mode,
      source_event_id: actionCard.source_event_id,
      due_by: actionCard.due_by,
      language: actionCard.language,
    },
    enrichment_state: "NOT_NEEDED",
    ref_event_id: triageEvent.event_id,
  };

  return {
    severity,
    assessment,
    triageEvent,
    actionCard,
    actionCardEvent,
    events: [triageEvent, actionCardEvent],
  };
}
