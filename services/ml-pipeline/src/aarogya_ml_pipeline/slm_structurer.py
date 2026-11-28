"""GBNF-constrained local SLM clinical note structurer.

Conforms to ClinicalSlmStructurer protocol using llama.cpp and Qwen2.5-3B GGUF.
Enforces the Clinical Safety Floor: SLMs extract symptoms and candidate danger
flags but strictly NEVER output or override TriageSeverity.
Enforces Pure Indic Vocabulary (Shuddh Tatsama) for Hindi clinical outputs.
"""

from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

from aarogya_ml_pipeline.interfaces import (
    StructuredClinicalNote,
    StubClinicalSlmStructurer,
)

logger = logging.getLogger(__name__)

CANONICAL_DANGER_FLAGS: frozenset[str] = frozenset({
    # WHO IMNCI pediatric general danger signs (imnci_pediatric.json v2.0.0)
    "not_able_to_drink_or_breastfeed",
    "vomits_everything",
    "convulsions",
    "lethargic_or_unconscious",
    "severe_breathing_difficulty",
    "cyanosis",
    "stridor_in_calm_child",
    "stiff_neck",
    "severe_bleeding",
    "very_high_fever",
    # WHO IMNCI young-infant (<2m PSBI) danger signs
    "umbilicus_red_or_draining_pus",
    "skin_pustules_many_or_severe",
    "poor_feeding_or_weak_cry",
    "jaundice_palms_or_soles",
    "grunting_or_apnea",
    "movement_only_when_stimulated",
    # WHO IMNCI pediatric syndrome RED flags (2-59m)
    "mastoiditis_tender_swelling_behind_ear",
    "measles_eye_or_mouth_complications",
    "dengue_warning_signs",
    "severe_malaria_signs",
    "failed_appetite_test_sam",
    "severe_palmar_pallor",
    # NHM ASHA maternal emergency red flags (maternal_anc.json v2.0.0)
    "severe_headache_or_blurred_vision",
    "convulsions_or_fits",
    "vaginal_bleeding",
    "reduced_fetal_movement",
    "high_fever",
    "severe_anemia_signs",
    "severe_abdominal_pain",
    "leaking_fluid_before_labor",
    "swelling_face_and_hands",
    "breathing_difficulty_or_chest_pain",
    "puerperal_sepsis_signs",
    "previous_lscs_scar_tenderness",
    "hyperemesis_gravidarum_severe",
    "postpartum_hemorrhage_heavy",
    "antepartum_hemorrhage_painful_or_painless",
    "obstructed_or_prolonged_labor",
})

DANGER_FLAG_SYNONYMS: dict[str, str] = {
    # Convulsions / Eclampsia
    "convulsion": "convulsions",
    "convulsions": "convulsions",
    "fits": "convulsions",
    "convulsions_or_fits": "convulsions",
    "seizure": "convulsions",
    "seizures": "convulsions",
    "eclampsia": "convulsions",
    "jerking_limbs": "convulsions",
    "rolling_eyes": "convulsions",
    "दौरा": "convulsions",
    "दौरे": "convulsions",
    "आक्षेप": "convulsions",
    "मिर्गी": "convulsions",
    "अंगों में ऐंठन": "convulsions",
    # Unable to drink / breastfeed / poor feeding
    "not_able_to_drink_or_breastfeed": "not_able_to_drink_or_breastfeed",
    "not_able_to_drink": "not_able_to_drink_or_breastfeed",
    "unable_to_drink": "not_able_to_drink_or_breastfeed",
    "cannot_drink": "not_able_to_drink_or_breastfeed",
    "unable_to_breastfeed": "not_able_to_drink_or_breastfeed",
    "cannot_breastfeed": "not_able_to_drink_or_breastfeed",
    "not_drinking": "not_able_to_drink_or_breastfeed",
    "refusing_feeds": "not_able_to_drink_or_breastfeed",
    "unable_to_suck": "not_able_to_drink_or_breastfeed",
    "poor_feeding": "not_able_to_drink_or_breastfeed",
    "स्तनपान_असमर्थ": "not_able_to_drink_or_breastfeed",
    "स्तनपान में असमर्थ": "not_able_to_drink_or_breastfeed",
    "पीने में असमर्थ": "not_able_to_drink_or_breastfeed",
    "दूध नहीं पी रहा": "not_able_to_drink_or_breastfeed",
    "स्तनपान त्याग": "not_able_to_drink_or_breastfeed",
    # Vomits everything
    "vomits_everything": "vomits_everything",
    "vomiting_everything": "vomits_everything",
    "persistent_vomiting_all": "vomits_everything",
    "cannot_keep_fluids_down": "vomits_everything",
    "सब कुछ वमन": "vomits_everything",
    "लगातार वमन": "vomits_everything",
    "अत्यधिक वमन": "vomits_everything",
    # Lethargic / unconscious
    "lethargic_or_unconscious": "lethargic_or_unconscious",
    "lethargic": "lethargic_or_unconscious",
    "lethargy": "lethargic_or_unconscious",
    "unconscious": "lethargic_or_unconscious",
    "abnormally_sleepy": "lethargic_or_unconscious",
    "unresponsive": "lethargic_or_unconscious",
    "not_waking_up": "lethargic_or_unconscious",
    "सुस्त": "lethargic_or_unconscious",
    "अचेत": "lethargic_or_unconscious",
    "चेतनाहीन": "lethargic_or_unconscious",
    "अत्यधिक निद्रा": "lethargic_or_unconscious",
    "निष्क्रिय शिशु": "lethargic_or_unconscious",
    # Severe breathing difficulty / chest indrawing / grunting
    "severe_breathing_difficulty": "severe_breathing_difficulty",
    "severe_chest_indrawing": "severe_breathing_difficulty",
    "gasping": "severe_breathing_difficulty",
    "grunting": "severe_breathing_difficulty",
    "struggling_to_breathe": "severe_breathing_difficulty",
    "severe_respiratory_distress": "severe_breathing_difficulty",
    "तीव्र श्वास कष्ट": "severe_breathing_difficulty",
    "अत्यधिक श्वास कष्ट": "severe_breathing_difficulty",
    "गंभीर श्वास अवरोध": "severe_breathing_difficulty",
    "वक्ष धंसना": "severe_breathing_difficulty",
    # Cyanosis
    "cyanosis": "cyanosis",
    "central_cyanosis": "cyanosis",
    "bluish_lips": "cyanosis",
    "blue_lips": "cyanosis",
    "blue_tongue": "cyanosis",
    "नीलवर्णता": "cyanosis",
    "ओष्ठ नीलापन": "cyanosis",
    "नीला पड़ना": "cyanosis",
    # Stridor in calm child
    "stridor_in_calm_child": "stridor_in_calm_child",
    "stridor": "stridor_in_calm_child",
    "noisy_breathing_at_rest": "stridor_in_calm_child",
    "शांत अवस्था में श्वास ध्वनि": "stridor_in_calm_child",
    "कंठ ध्वनि": "stridor_in_calm_child",
    # Stiff neck / meningitis
    "stiff_neck": "stiff_neck",
    "bulging_fontanelle": "stiff_neck",
    "neck_rigidity": "stiff_neck",
    "ग्रीवा अकड़न": "stiff_neck",
    "गर्दन अकड़न": "stiff_neck",
    "तालु उभार": "stiff_neck",
    # Keep IMNCI severe_bleeding distinct from maternal vaginal_bleeding
    "severe_bleeding": "severe_bleeding",
    "active_bleeding": "severe_bleeding",
    "bleeding": "severe_bleeding",
    "hemorrhage": "severe_bleeding",
    "hematemesis": "severe_bleeding",
    "blood_in_vomit": "severe_bleeding",
    "petechial_rash_with_bleeding": "severe_bleeding",
    "रक्तस्राव": "severe_bleeding",
    "तीव्र रक्तस्राव": "severe_bleeding",
    "अत्यधिक रक्तस्राव": "severe_bleeding",
    "रक्त वमन": "severe_bleeding",
    # Maternal vaginal bleeding / APH / PPH
    "vaginal_bleeding": "vaginal_bleeding",
    "bleeding_in_pregnancy": "vaginal_bleeding",
    "योनि_रक्तस्राव": "vaginal_bleeding",
    "योनि रक्तस्राव": "vaginal_bleeding",
    "गर्भावस्था में रक्तस्राव": "vaginal_bleeding",
    "postpartum_hemorrhage_heavy": "postpartum_hemorrhage_heavy",
    "postpartum_hemorrhage": "postpartum_hemorrhage_heavy",
    "heavy_postpartum_bleeding": "postpartum_hemorrhage_heavy",
    "pph": "postpartum_hemorrhage_heavy",
    "प्रसवोत्तर रक्तस्राव": "postpartum_hemorrhage_heavy",
    "antepartum_hemorrhage_painful_or_painless": "antepartum_hemorrhage_painful_or_painless",
    "antepartum_hemorrhage": "antepartum_hemorrhage_painful_or_painless",
    "aph": "antepartum_hemorrhage_painful_or_painless",
    "प्रसव पूर्व रक्तस्राव": "antepartum_hemorrhage_painful_or_painless",
    # Severe headache / blurred vision (pre-eclampsia)
    "severe_headache_or_blurred_vision": "severe_headache_or_blurred_vision",
    "severe_headache": "severe_headache_or_blurred_vision",
    "blurred_vision": "severe_headache_or_blurred_vision",
    "headache_blurred_vision": "severe_headache_or_blurred_vision",
    "visual_disturbance": "severe_headache_or_blurred_vision",
    "flashing_lights": "severe_headache_or_blurred_vision",
    "तीव्र_सिरदर्द": "severe_headache_or_blurred_vision",
    "तीव्र सिरदर्द": "severe_headache_or_blurred_vision",
    "तीव्र शिरोवेदना": "severe_headache_or_blurred_vision",
    "धुंधली_दृष्टि": "severe_headache_or_blurred_vision",
    "धुंधली दृष्टि": "severe_headache_or_blurred_vision",
    "अस्पष्ट_दृष्टि": "severe_headache_or_blurred_vision",
    "अस्पष्ट दृष्टि": "severe_headache_or_blurred_vision",
    "दृष्टि धुंधलापन": "severe_headache_or_blurred_vision",
    # Reduced fetal movement
    "reduced_fetal_movement": "reduced_fetal_movement",
    "decreased_fetal_movement": "reduced_fetal_movement",
    "absent_fetal_movement": "reduced_fetal_movement",
    "no_fetal_movement": "reduced_fetal_movement",
    "baby_not_moving": "reduced_fetal_movement",
    "गर्भस्थ_शिशु_हलचल_कमी": "reduced_fetal_movement",
    "गर्भस्थ शिशु की गति में कमी": "reduced_fetal_movement",
    "शिशु हलचल बंद": "reduced_fetal_movement",
    # Keep IMNCI very_high_fever distinct from maternal high_fever
    "very_high_fever": "very_high_fever",
    "hyperpyrexia": "very_high_fever",
    "extreme_fever": "very_high_fever",
    "अति तीव्र ज्वर": "very_high_fever",
    "अत्यधिक ज्वर": "very_high_fever",
    # Maternal high fever & puerperal sepsis
    "high_fever": "high_fever",
    "puerperal_sepsis_signs": "puerperal_sepsis_signs",
    "puerperal_sepsis": "puerperal_sepsis_signs",
    "foul_smelling_discharge": "puerperal_sepsis_signs",
    "foul_lochia": "puerperal_sepsis_signs",
    "दुर्गंधयुक्त स्राव": "puerperal_sepsis_signs",
    "प्रसवोत्तर ज्वर": "puerperal_sepsis_signs",
    "प्रसूति संक्रमण": "puerperal_sepsis_signs",
    # Maternal severe anemia signs
    "severe_anemia_signs": "severe_anemia_signs",
    "severe_pallor": "severe_anemia_signs",
    "breathlessness_at_rest": "severe_anemia_signs",
    "तीव्र रक्तअल्पता": "severe_anemia_signs",
    "अत्यधिक पांडुता": "severe_anemia_signs",
    # Severe abdominal / epigastric pain & LSCS scar tenderness
    "severe_abdominal_pain": "severe_abdominal_pain",
    "epigastric_pain": "severe_abdominal_pain",
    "right_upper_quadrant_pain": "severe_abdominal_pain",
    "तीव्र उदर शूल": "severe_abdominal_pain",
    "गंभीर उदर पीड़ा": "severe_abdominal_pain",
    "previous_lscs_scar_tenderness": "previous_lscs_scar_tenderness",
    "lscs_scar_tenderness": "previous_lscs_scar_tenderness",
    "scar_tenderness": "previous_lscs_scar_tenderness",
    "शल्य चिह्न पीड़ा": "previous_lscs_scar_tenderness",
    # Hyperemesis gravidarum & obstructed labor
    "hyperemesis_gravidarum_severe": "hyperemesis_gravidarum_severe",
    "hyperemesis_gravidarum": "hyperemesis_gravidarum_severe",
    "अत्यधिक गर्भावस्था वमन": "hyperemesis_gravidarum_severe",
    "obstructed_or_prolonged_labor": "obstructed_or_prolonged_labor",
    "obstructed_labor": "obstructed_or_prolonged_labor",
    "prolonged_labor": "obstructed_or_prolonged_labor",
    "अवरुद्ध प्रसव": "obstructed_or_prolonged_labor",
    "विलंबित प्रसव": "obstructed_or_prolonged_labor",
    # Premature rupture of membranes
    "leaking_fluid_before_labor": "leaking_fluid_before_labor",
    "water_breaking": "leaking_fluid_before_labor",
    "ruptured_membranes": "leaking_fluid_before_labor",
    "prom": "leaking_fluid_before_labor",
    "pprom": "leaking_fluid_before_labor",
    "प्रसव पूर्व जलस्राव": "leaking_fluid_before_labor",
    "जलस्राव": "leaking_fluid_before_labor",
    # Facial / hand edema (pre-eclampsia)
    "swelling_face_and_hands": "swelling_face_and_hands",
    "facial_swelling": "swelling_face_and_hands",
    "generalized_edema": "swelling_face_and_hands",
    "मुख एवं हस्त शोथ": "swelling_face_and_hands",
    "चेहरे और हाथ में सूजन": "swelling_face_and_hands",
    # Acute dyspnea / chest pain
    "breathing_difficulty_or_chest_pain": "breathing_difficulty_or_chest_pain",
    "chest_pain": "breathing_difficulty_or_chest_pain",
    "acute_dyspnea": "breathing_difficulty_or_chest_pain",
    "वक्ष पीड़ा": "breathing_difficulty_or_chest_pain",
    "छाती में तीव्र पीड़ा": "breathing_difficulty_or_chest_pain",
    # Young-infant (<2m PSBI) danger signs (imnci_pediatric.json v2.0.0)
    "umbilicus_red_or_draining_pus": "umbilicus_red_or_draining_pus",
    "umbilicus_draining_pus": "umbilicus_red_or_draining_pus",
    "umbilical_redness": "umbilicus_red_or_draining_pus",
    "cord_infection": "umbilicus_red_or_draining_pus",
    "नाभि से पूय": "umbilicus_red_or_draining_pus",
    "नाभि संक्रमण": "umbilicus_red_or_draining_pus",
    "skin_pustules_many_or_severe": "skin_pustules_many_or_severe",
    "multiple_skin_pustules": "skin_pustules_many_or_severe",
    "severe_skin_pustules": "skin_pustules_many_or_severe",
    "त्वचा पूयस्फोट": "skin_pustules_many_or_severe",
    "poor_feeding_or_weak_cry": "poor_feeding_or_weak_cry",
    "weak_cry": "poor_feeding_or_weak_cry",
    "दुर्बल क्रंदन": "poor_feeding_or_weak_cry",
    "jaundice_palms_or_soles": "jaundice_palms_or_soles",
    "jaundice_palms_soles": "jaundice_palms_or_soles",
    "yellow_palms_soles": "jaundice_palms_or_soles",
    "हथेली एवं तलवे पीलिया": "jaundice_palms_or_soles",
    "grunting_or_apnea": "grunting_or_apnea",
    "apnea": "grunting_or_apnea",
    "श्वसन विराम": "grunting_or_apnea",
    "movement_only_when_stimulated": "movement_only_when_stimulated",
    "उत्तेजना पर ही गति": "movement_only_when_stimulated",
    # Pediatric syndrome RED signs (2-59m, imnci_pediatric.json v2.0.0)
    "mastoiditis_tender_swelling_behind_ear": "mastoiditis_tender_swelling_behind_ear",
    "mastoiditis": "mastoiditis_tender_swelling_behind_ear",
    "swelling_behind_ear": "mastoiditis_tender_swelling_behind_ear",
    "कर्णमूल शोथ": "mastoiditis_tender_swelling_behind_ear",
    "measles_eye_or_mouth_complications": "measles_eye_or_mouth_complications",
    "corneal_clouding": "measles_eye_or_mouth_complications",
    "रोमांतिका नेत्र जटिलता": "measles_eye_or_mouth_complications",
    "dengue_warning_signs": "dengue_warning_signs",
    "dengue_hemorrhagic_signs": "dengue_warning_signs",
    "डेंगू संकट संकेत": "dengue_warning_signs",
    "severe_malaria_signs": "severe_malaria_signs",
    "cerebral_malaria": "severe_malaria_signs",
    "गंभीर मलेरिया": "severe_malaria_signs",
    "failed_appetite_test_sam": "failed_appetite_test_sam",
    "failed_appetite_test": "failed_appetite_test_sam",
    "क्षुधा परीक्षण असफल": "failed_appetite_test_sam",
    "severe_palmar_pallor": "severe_palmar_pallor",
    "तीव्र करतल पांडुता": "severe_palmar_pallor",
}

SYMPTOM_SYNONYMS: dict[str, str] = {
    # Fever & thermal signs
    "fever": "fever",
    "mild_fever": "fever",
    "low_grade_fever": "fever",
    "chills": "fever",
    "shivering": "fever",
    "ज्वर": "fever",
    "तीव्र ज्वर": "fever",
    "ठंड लगना": "fever",
    "कंपकंपी": "fever",
    "hypothermia": "hypothermia",
    "cold_to_touch": "hypothermia",
    "अल्पताप": "hypothermia",
    "शरीर ठंडा पड़ना": "hypothermia",
    # Respiratory
    "cough": "cough",
    "dry_cough": "cough",
    "productive_cough": "cough",
    "कास": "cough",
    "खांसी": "cough",
    "खाँसी": "cough",
    "fast_breathing": "fast_breathing",
    "rapid_breathing": "fast_breathing",
    "tachypnea": "fast_breathing",
    "breathing_difficulty": "fast_breathing",
    "difficulty_breathing": "fast_breathing",
    "shortness_of_breath": "fast_breathing",
    "breathlessness": "fast_breathing",
    "trouble_breathing": "fast_breathing",
    "hard_to_breathe": "fast_breathing",
    "श्वास कष्ट": "fast_breathing",
    "तीव्र श्वसन": "fast_breathing",
    "श्वास फूलना": "fast_breathing",
    "chest_indrawing": "chest_indrawing",
    "lower_chest_indrawing": "chest_indrawing",
    # Diarrhea & dehydration
    "diarrhea": "diarrhea",
    "diarrhoea": "diarrhea",
    "loose_stools": "diarrhea",
    "watery_stools": "diarrhea",
    "अतिसार": "diarrhea",
    "दस्त": "diarrhea",
    "blood_in_stool": "blood_in_stool",
    "dysentery": "blood_in_stool",
    "रक्तयुक्त अतिसार": "blood_in_stool",
    "sunken_eyes": "sunken_eyes",
    "धंसी आंखें": "sunken_eyes",
    "skin_pinch_slow": "skin_pinch_slow",
    "skin_pinch_very_slow": "skin_pinch_very_slow",
    "restless_or_irritable": "restless_or_irritable",
    "irritable": "restless_or_irritable",
    "चिड़चिड़ापन": "restless_or_irritable",
    "vomiting": "vomiting",
    "persistent_vomiting": "persistent_vomiting",
    "hyperemesis": "persistent_vomiting",
    "वमन": "vomiting",
    "उल्टी": "vomiting",
    # Young infant PSBI / neonatal signs
    "umbilical_redness": "umbilical_redness",
    "umbilicus_draining_pus": "umbilical_redness",
    "cord_infection": "umbilical_redness",
    "नाभि संक्रमण": "umbilical_redness",
    "नाभि से पूय": "umbilical_redness",
    "skin_pustules": "skin_pustules",
    "multiple_skin_pustules": "skin_pustules",
    "त्वचा फोड़े": "skin_pustules",
    "jaundice_palms_soles": "jaundice_palms_soles",
    "yellow_palms_soles": "jaundice_palms_soles",
    "पीलिया": "jaundice",
    "कामला": "jaundice",
    # Ear / measles / malnutrition / anemia (v2.0.0 canonical tokens)
    "acute_ear_pain_or_discharge": "acute_ear_pain_or_discharge",
    "ear_pain": "acute_ear_pain_or_discharge",
    "ear_discharge": "acute_ear_pain_or_discharge",
    "chronic_ear_discharge": "chronic_ear_discharge",
    "कर्ण पीड़ा": "acute_ear_pain_or_discharge",
    "कर्ण स्राव": "acute_ear_pain_or_discharge",
    "measles_uncomplicated_rash": "measles_uncomplicated_rash",
    "measles_rash": "measles_uncomplicated_rash",
    "generalized_rash": "measles_uncomplicated_rash",
    "खसरा": "measles_uncomplicated_rash",
    "रोमांतिका": "measles_uncomplicated_rash",
    "visible_severe_wasting": "visible_severe_wasting",
    "अति कृशता": "visible_severe_wasting",
    "palmar_pallor": "palmar_pallor",
    "moderate_pallor": "moderate_pallor",
    "पांडुता": "palmar_pallor",
    "रक्तअल्पता": "palmar_pallor",
    "bilateral_pedal_edema": "bilateral_pedal_edema",
    "mild_pedal_edema": "mild_pedal_edema",
    "पाद शोथ": "mild_pedal_edema",
    # Maternal / urinary / general (v2.0.0 canonical tokens)
    "burning_micturition": "burning_micturition",
    "painful_urination": "burning_micturition",
    "मूत्र दाह": "burning_micturition",
    "gestational_diabetes_gdm": "gestational_diabetes_gdm",
    "gestational_diabetes": "gestational_diabetes_gdm",
    "gdm": "gestational_diabetes_gdm",
    "गर्भकालीन मधुमेह": "gestational_diabetes_gdm",
    "rh_negative_mother": "rh_negative_mother",
    "rh_negative": "rh_negative_mother",
    "twin_or_multiple_gestation": "twin_or_multiple_gestation",
    "twin_pregnancy": "twin_or_multiple_gestation",
    "जुड़वां गर्भ": "twin_or_multiple_gestation",
    "previous_lscs_history": "previous_lscs_history",
    "previous_lscs": "previous_lscs_history",
    "maternal_short_stature_or_malpresentation": "maternal_short_stature_or_malpresentation",
    "headache": "headache",
    "शिरोवेदना": "headache",
    "high_blood_pressure": "high_blood_pressure",
    "hypertension": "high_blood_pressure",
    "उच्च रक्तचाप": "high_blood_pressure",
    "abdominal_pain": "abdominal_pain",
    "उदर शूल": "abdominal_pain",
    "fatigue": "fatigue",
    "दुर्बलता": "fatigue",
}

_NEGATION_PREFIXES: tuple[str, ...] = (
    "no_",
    "non_",
    "without_",
    "denied_",
    "denies_",
    "negative_for_",
    "नहीं_",
    "बिना_",
    "रहित_",
    "अनुपस्थित_",
)

_SORTED_SYNONYM_ITEMS: tuple[tuple[str, str], ...] = tuple(
    sorted(DANGER_FLAG_SYNONYMS.items(), key=lambda item: len(item[0]), reverse=True)
)

_SORTED_SYMPTOM_ITEMS: tuple[tuple[str, str], ...] = tuple(
    sorted(SYMPTOM_SYNONYMS.items(), key=lambda item: len(item[0]), reverse=True)
)

FORBIDDEN_CLINICAL_KEYS: frozenset[str] = frozenset({
    "severity", "triage_severity", "referral_required", "triage", "triage_status", "priority",
})

HINDI_VOCAB_REPLACEMENTS: list[tuple[str, str]] = [
    ("सांस की तकलीफ", "श्वास कष्ट"), ("साँस की तकलीफ़", "श्वास कष्ट"),
    ("सांस की दिक्कत", "श्वास कष्ट"), ("सांस", "श्वास"), ("साँस", "श्वास"),
    ("तकलीफ", "कष्ट"), ("तकलीफ़", "कष्ट"), ("बुखार", "ज्वर"), ("बुख़ार", "ज्वर"),
    ("अस्पताल में", "प्राथमिक स्वास्थ्य केन्द्र में"), ("अस्पताल", "प्राथमिक स्वास्थ्य केन्द्र"),
    ("दवाखाना", "औषधालय"), ("दवाख़ाना", "औषधालय"), ("इलाज", "उपचार"),
    ("मरीज", "रोगी"), ("मरीज़", "रोगी"), ("जरूरी", "आवश्यक"), ("ज़रूरी", "आवश्यक"),
    ("मदद", "सहायता"), ("खून", "रक्त"), ("ख़ून", "रक्त"), ("फौरन", "तत्काल"),
    ("फ़ौरन", "तत्काल"), ("तेज़", "तीव्र"), ("तेज", "तीव्र"),
    ("एमरजेंसी", "आपातकाल"), ("इमरजेंसी", "आपातकाल"),
    ("हॉस्पिटल", "चिकित्सालय"), ("डॉक्टर", "चिकित्सक"),
    ("आउट" + "पुट", "निर्गत"),
    ("ब्लड प्रेशर", "रक्तचाप"), ("ऑक्सीजन", "प्राणवायु"),
    ("टेंपरेचर", "तापमान"), ("प्रेग्नेंट", "गर्भवती"), ("प्रेगनेंसी", "गर्भावस्था"),
    ("इंजेक्शन", "टीका"), ("चेकअप", "परीक्षण"), ("रिपोर्ट", "प्रतिवेदन"),
    ("सीरियस", "गंभीर"), ("नॉर्मल", "सामान्य"),
    ("कमज़ोरी", "दुर्बलता"), ("कमजोरी", "दुर्बलता"),
    ("बेहोशी", "अचेतनता"), ("उल्टी", "वमन"), ("दस्त", "अतिसार"),
    ("सूजन", "शोथ"), ("दर्द", "पीड़ा"), ("दवाई", "औषधि"),
]


def sanitize_hindi_text(text: str) -> str:
    """Enforce Pure Indic Vocabulary (Shuddh Tatsama) for Hindi strings."""
    result = text
    for old, new in HINDI_VOCAB_REPLACEMENTS:
        result = result.replace(old, new)
    # Strip any stray Unicode nukta (U+093C) while preserving Devanagari matras and anusvara.
    decomposed = unicodedata.normalize("NFD", result).replace("\u093c", "")
    return unicodedata.normalize("NFC", decomposed)


def _word_boundary_pattern(term: str) -> str:
    body = r"[\s_-]+".join(re.escape(part) for part in term.split("_"))
    if term.isascii():
        return rf"(?<![a-z0-9_]){body}(?![a-z0-9_])"
    return rf"(?<![\u0900-\u097f_]){body}(?![\u0900-\u097f_])"


def _is_negated_occurrence(text: str, match_start: int, match_end: int | None = None) -> bool:
    """Return True if a matched phrase is negated before (EN/HI) or immediately after (HI SOV)."""
    prefix = text[:match_start].rstrip()
    if re.search(
        r"(?:^|[\s,;.:/])(?:no|not|without|denies|denied|absent|negative\s+for|बिना|रहित|अनुपस्थित)$",
        prefix,
    ):
        return True
    if match_end is not None:
        suffix = text[match_end:].lstrip()
        if re.match(
            r"^(?:नहीं|रहित|अनुपस्थित|का\s+अभाव|न\s+होना)(?:$|[\s,;.:।/])",
            suffix,
        ):
            return True
    return False


def map_to_canonical_danger_flag(flag: str) -> str:
    """Map extracted danger sign phrase to canonical clinical-engine code."""
    cleaned = flag.strip().lower()
    normalized = cleaned.replace("-", "_").replace(" ", "_")
    if normalized in DANGER_FLAG_SYNONYMS:
        return DANGER_FLAG_SYNONYMS[normalized]
    if cleaned in DANGER_FLAG_SYNONYMS:
        return DANGER_FLAG_SYNONYMS[cleaned]
    # Do not fuzzy-match negated phrases (e.g., "no_bleeding", "no bleeding", "without_fits")
    if normalized.startswith(_NEGATION_PREFIXES):
        return normalized
    for syn_key, canonical in _SORTED_SYNONYM_ITEMS:
        pattern = _word_boundary_pattern(syn_key)
        m_clean = re.search(pattern, cleaned)
        if m_clean and not _is_negated_occurrence(cleaned, m_clean.start(), m_clean.end()):
            return canonical
        m_norm = re.search(pattern, normalized)
        if m_norm and not _is_negated_occurrence(normalized, m_norm.start(), m_norm.end()):
            return canonical
    return normalized


def map_to_canonical_symptom(symptom: str) -> str:
    """Map extracted rural English or Hindi symptom phrase to a canonical clinical token."""
    cleaned = symptom.strip().lower()
    normalized = cleaned.replace("-", "_").replace(" ", "_")
    if normalized in SYMPTOM_SYNONYMS:
        return SYMPTOM_SYNONYMS[normalized]
    if cleaned in SYMPTOM_SYNONYMS:
        return SYMPTOM_SYNONYMS[cleaned]
    if normalized.startswith(_NEGATION_PREFIXES):
        return normalized
    for syn_key, canonical in _SORTED_SYMPTOM_ITEMS:
        pattern = _word_boundary_pattern(syn_key)
        m_clean = re.search(pattern, cleaned)
        if m_clean and not _is_negated_occurrence(cleaned, m_clean.start(), m_clean.end()):
            return canonical
        m_norm = re.search(pattern, normalized)
        if m_norm and not _is_negated_occurrence(normalized, m_norm.start(), m_norm.end()):
            return canonical
    return normalized


def extract_clinical_signals_from_text(
    transcript: str,
) -> tuple[list[str], list[str]]:
    """Extract canonical symptoms and candidate danger flags from free-text transcript.

    Uses longest-first word-boundary matching with inline EN & HI negation guards so
    offline fallback safely detects both English and pure Shuddh Tatsama Hindi
    danger signs (e.g. दौरा, योनि रक्तस्राव, तीव्र श्वास कष्ट, अस्पष्ट दृष्टि) without
    hallucinating flags on negated phrases ("no convulsions, no bleeding", "दौरा नहीं").
    """
    cleaned = sanitize_hindi_text(transcript).strip().lower()
    if not cleaned:
        return [], []

    danger_flags: list[str] = []
    symptoms: list[str] = []
    covered_spans: list[tuple[int, int]] = []

    def _overlaps(start: int, end: int) -> bool:
        return any(not (end <= s or start >= e) for s, e in covered_spans)

    danger_to_syndrome: dict[str, str] = {
        "high_fever": "fever",
        "very_high_fever": "fever",
    }

    for syn_key, canonical in _SORTED_SYNONYM_ITEMS:
        if canonical in danger_flags:
            continue
        pattern = _word_boundary_pattern(syn_key)
        for match in re.finditer(pattern, cleaned):
            if _overlaps(match.start(), match.end()):
                continue
            if _is_negated_occurrence(cleaned, match.start(), match.end()):
                continue
            danger_flags.append(canonical)
            covered_spans.append((match.start(), match.end()))
            sym_token = danger_to_syndrome.get(canonical, canonical)
            if sym_token not in symptoms:
                symptoms.append(sym_token)
            break

    for syn_key, canonical in _SORTED_SYMPTOM_ITEMS:
        if canonical in symptoms:
            continue
        pattern = _word_boundary_pattern(syn_key)
        for match in re.finditer(pattern, cleaned):
            if _overlaps(match.start(), match.end()):
                continue
            if _is_negated_occurrence(cleaned, match.start(), match.end()):
                continue
            symptoms.append(canonical)
            covered_spans.append((match.start(), match.end()))
            break

    return symptoms, danger_flags


def parse_and_validate_slm_json(raw_json_str: str, language: str = "hi") -> StructuredClinicalNote:
    """Parse JSON string from SLM and validate against strict clinical safety contracts."""
    cleaned = raw_json_str.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        cleaned = "\n".join(lines[1:-1] if lines and lines[-1].strip() == "```" else lines[1:]).strip()

    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object from SLM, got {type(data).__name__}")

    # Clinical Safety Floor: Strictly reject any attempt to output or override TriageSeverity
    forbidden_found = FORBIDDEN_CLINICAL_KEYS.intersection(data.keys())
    if forbidden_found:
        raise ValueError(
            f"Clinical Safety Floor Violation: SLM output contains forbidden triage keys: "
            f"{sorted(forbidden_found)}. Local SLM must NEVER output or override TriageSeverity."
        )

    raw_symptoms = data.get("extracted_symptoms", [])
    if not isinstance(raw_symptoms, list):
        raise ValueError("extracted_symptoms must be a list of strings")
    symptoms = [
        sanitize_hindi_text(str(s).strip()) if language == "hi" else str(s).strip()
        for s in raw_symptoms if str(s).strip()
    ]
    # Deduplicate preserving order
    seen_symptoms: set[str] = set()
    deduped_symptoms = [s for s in symptoms if not (s in seen_symptoms or seen_symptoms.add(s))]

    raw_flags = data.get("candidate_danger_flags", [])
    if not isinstance(raw_flags, list):
        raise ValueError("candidate_danger_flags must be a list of strings")
    danger_flags: list[str] = []
    for f in raw_flags:
        canonical = map_to_canonical_danger_flag(str(f))
        if canonical and canonical not in danger_flags:
            danger_flags.append(canonical)

    follow_up = str(data.get("recommended_follow_up", "")).strip()
    if not follow_up:
        raise ValueError("recommended_follow_up must be a non-empty string")
    if language == "hi":
        follow_up = sanitize_hindi_text(follow_up)
    if len(follow_up) > 500:
        follow_up = follow_up[:497] + "..."

    return StructuredClinicalNote(
        extracted_symptoms=deduped_symptoms,
        candidate_danger_flags=danger_flags,
        recommended_follow_up=follow_up,
        language=language,
        backend="llama-cpp-qwen2.5-3b-gbnf",
    )


class LlamaCppSlmStructurer:
    """GBNF-constrained local SLM symptom extractor backed by llama.cpp.

    Conforms to ClinicalSlmStructurer protocol with temperature=0.0 and strict GBNF grammar.
    Falls back cleanly to StubClinicalSlmStructurer if GGUF or library is unavailable.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        grammar_path: str | Path | None = None,
        temperature: float = 0.0,
        n_ctx: int = 2048,
        n_threads: int | None = None,
        verbose: bool = False,
    ) -> None:
        self.temperature = temperature
        self.n_ctx = n_ctx
        self.n_threads = n_threads
        self.verbose = verbose
        self._fallback_stub = StubClinicalSlmStructurer()

        if grammar_path is not None:
            self.grammar_path: Path | None = Path(grammar_path)
        else:
            default_gbnf = Path(__file__).parent / "grammars" / "clinical_note.gbnf"
            self.grammar_path = default_gbnf if default_gbnf.is_file() else None

        env_path = os.environ.get("AAROGYA_SLM_GGUF_PATH")
        resolved = model_path if model_path is not None else env_path
        self.model_path: Path | None = Path(resolved) if resolved else None

        self._llm: Any = None
        self._grammar: Any = None
        self._is_available: bool = False
        self._init_backend()

    def _init_backend(self) -> None:
        if self.model_path is None or not self.model_path.is_file():
            return
        try:
            from llama_cpp import Llama, LlamaGrammar
            self._llm = Llama(
                model_path=str(self.model_path),
                n_ctx=self.n_ctx,
                n_threads=self.n_threads,
                verbose=self.verbose,
            )
            if self.grammar_path and self.grammar_path.is_file():
                self._grammar = LlamaGrammar.from_file(str(self.grammar_path))
            self._is_available = True
        except Exception as exc:
            logger.warning("Failed to initialize llama_cpp (%s); fallback enabled.", exc)
            self._llm = None
            self._grammar = None
            self._is_available = False

    def _fallback(self, transcript: str, language: str = "hi") -> StructuredClinicalNote:
        if transcript.strip().startswith("[stub-audio-"):
            follow_up = (
                "स्थानीय वाक्-से-पाठ प्रतिमान उपलब्ध नहीं; ध्वनि टिप्पणी की प्रत्यक्ष समीक्षा करें।"
                if language == "hi"
                else "Audio recorded without local Whisper ASR model; manual review or transcript required."
            )
            return StructuredClinicalNote(
                extracted_symptoms=[],
                candidate_danger_flags=[],
                recommended_follow_up=follow_up,
                language=language,
                backend="stub-slm-fallback",
            )

        lex_symptoms, lex_flags = extract_clinical_signals_from_text(transcript)
        merged_symptoms = list(lex_symptoms) if lex_symptoms else ["general_checkup"]

        follow_up = (
            "Immediate deterministic danger-sign triage required."
            if lex_flags
            else "Review structured symptoms in deterministic IMNCI/ASHA engine."
        )
        if language == "hi":
            follow_up = (
                "तत्काल निर्धारक संकट-संकेत परीक्षण एवं प्राथमिक स्वास्थ्य केन्द्र संदर्भन आवश्यक।"
                if lex_flags
                else "प्राथमिक स्वास्थ्य केन्द्र स्तर पर लक्षणों की समीक्षा करें।"
            )
        return StructuredClinicalNote(
            extracted_symptoms=merged_symptoms,
            candidate_danger_flags=lex_flags,
            recommended_follow_up=follow_up,
            language=language,
            backend="stub-slm-fallback",
        )

    def _build_prompt(self, transcript: str, language: str = "hi") -> str:
        if language == "hi":
            sys = (
                "आप सामुदायिक स्वास्थ्य कार्यकर्ताओं के लिए एक चिकित्सीय निष्कर्षण सहायक हैं। "
                "लक्षणों और संकट-संकेतों का निष्कर्षण करें। निर्गत केवल JSON कुंजियों के साथ होना चाहिए: "
                "extracted_symptoms, candidate_danger_flags, recommended_follow_up। "
                "कभी भी severity या referral_required निर्गत न करें। केवल शुद्ध तत्सम शब्दावली का प्रयोग करें।"
            )
        else:
            sys = (
                "You are a clinical extraction assistant for Community Health Workers. "
                "Output JSON with ONLY extracted_symptoms, candidate_danger_flags, and recommended_follow_up. "
                "NEVER output severity or triage_severity. Raw triage severity is calculated deterministically."
            )
        return f"<|im_start|>system\n{sys}<|im_end|>\n<|im_start|>user\nTranscript: {transcript}<|im_end|>\n<|im_start|>assistant\n"

    @staticmethod
    def _extract_response_text(response: Any) -> str:
        if isinstance(response, str):
            return response
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices and isinstance(choices[0], dict):
                choice = choices[0]
                if "text" in choice:
                    return str(choice["text"])
                if "message" in choice and isinstance(choice["message"], dict):
                    return str(choice["message"].get("content", ""))
        return str(response)

    def structure_note(self, transcript: str, language: str = "hi") -> StructuredClinicalNote:
        """Extract structured clinical symptoms and candidate danger flags from transcript."""
        if not self._is_available or self._llm is None:
            return self._fallback(transcript, language=language)

        try:
            prompt = self._build_prompt(transcript, language=language)
            kwargs: dict[str, Any] = {
                "prompt": prompt, "temperature": self.temperature, "max_tokens": 512,
                "stop": ["<|im_end|>", "<|endoftext|>", "</s>"],
            }
            if self._grammar is not None:
                kwargs["grammar"] = self._grammar
            response = self._llm(**kwargs)
            raw_text = self._extract_response_text(response)
            return parse_and_validate_slm_json(raw_text, language=language)
        except Exception as exc:
            logger.warning("SLM structuring failed (%s); falling back to stub.", exc)
            return self._fallback(transcript, language=language)
