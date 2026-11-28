"""Tests for GBNF-constrained Local SLM Structurer (slice T4-02)."""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aarogya_ml_pipeline.interfaces import (
    ClinicalSlmStructurer,
    StructuredClinicalNote,
)
from aarogya_ml_pipeline.slm_structurer import (
    CANONICAL_DANGER_FLAGS,
    DANGER_FLAG_SYNONYMS,
    SYMPTOM_SYNONYMS,
    LlamaCppSlmStructurer,
    extract_clinical_signals_from_text,
    map_to_canonical_danger_flag,
    map_to_canonical_symptom,
    parse_and_validate_slm_json,
    sanitize_hindi_text,
)


def test_protocol_conformance() -> None:
    """LlamaCppSlmStructurer must conform to ClinicalSlmStructurer protocol."""
    structurer = LlamaCppSlmStructurer()
    assert isinstance(structurer, ClinicalSlmStructurer)
    assert structurer.temperature == 0.0


def test_gbnf_grammar_presence_and_clinical_safety() -> None:
    """GBNF grammar file must exist and forbid any triage severity keys."""
    grammar_file = (
        Path(__file__).parents[1]
        / "src"
        / "aarogya_ml_pipeline"
        / "grammars"
        / "clinical_note.gbnf"
    )
    assert grammar_file.is_file(), f"Missing GBNF grammar at {grammar_file}"

    content = grammar_file.read_text(encoding="utf-8")

    # Required JSON schema keys must be constrained by grammar
    assert "extracted_symptoms" in content
    assert "candidate_danger_flags" in content
    assert "recommended_follow_up" in content

    # Clinical Safety Floor: MUST NOT contain triage severity fields
    content_lower = content.lower()
    assert "severity" not in content_lower
    assert "triage_severity" not in content_lower
    assert "referral_required" not in content_lower
    assert "triage" not in content_lower


def test_missing_gguf_fallback() -> None:
    """Missing or invalid GGUF model path falls back cleanly to StubClinicalSlmStructurer."""
    structurer = LlamaCppSlmStructurer(model_path="/nonexistent/model.gguf")
    note = structurer.structure_note("Child has fever and convulsions", language="en")

    assert isinstance(note, StructuredClinicalNote)
    assert note.backend == "stub-slm-fallback"
    assert "fever" in note.extracted_symptoms
    assert "convulsions" in note.candidate_danger_flags


def test_missing_gguf_hindi_fallback_pure_indic() -> None:
    """Fallback in Hindi uses pure Shuddh Tatsama vocabulary."""
    structurer = LlamaCppSlmStructurer(model_path=None)
    note = structurer.structure_note("शिशु को ज्वर और श्वास कष्ट है", language="hi")

    assert isinstance(note, StructuredClinicalNote)
    assert note.backend == "stub-slm-fallback"
    assert note.language == "hi"
    # Ensure zero Perso-Arabic terms in fallback output
    assert "अस्पताल" not in note.recommended_follow_up
    assert "दवाखाना" not in note.recommended_follow_up
    assert "इलाज" not in note.recommended_follow_up
    assert "प्राथमिक स्वास्थ्य केन्द्र" in note.recommended_follow_up or "निर्धारक" in note.recommended_follow_up


def test_canonical_danger_flag_mapping() -> None:
    """Danger flags must normalize to canonical clinical-engine codes."""
    assert map_to_canonical_danger_flag("convulsion") == "convulsions"
    assert map_to_canonical_danger_flag("seizures") == "convulsions"
    assert map_to_canonical_danger_flag("दौरा") == "convulsions"
    assert map_to_canonical_danger_flag("unable to drink") == "not_able_to_drink_or_breastfeed"
    assert map_to_canonical_danger_flag("cannot_breastfeed") == "not_able_to_drink_or_breastfeed"
    assert map_to_canonical_danger_flag("lethargy") == "lethargic_or_unconscious"
    assert map_to_canonical_danger_flag("abnormally_sleepy") == "lethargic_or_unconscious"
    assert map_to_canonical_danger_flag("bleeding") == "severe_bleeding"
    assert map_to_canonical_danger_flag("severe_bleeding") == "severe_bleeding"
    assert map_to_canonical_danger_flag("रक्तस्राव") == "severe_bleeding"
    assert map_to_canonical_danger_flag("vaginal_bleeding") == "vaginal_bleeding"
    assert map_to_canonical_danger_flag("योनि रक्तस्राव") == "vaginal_bleeding"
    assert map_to_canonical_danger_flag("very_high_fever") == "very_high_fever"
    assert map_to_canonical_danger_flag("high_fever") == "high_fever"
    assert map_to_canonical_danger_flag("severe headache") == "severe_headache_or_blurred_vision"
    assert map_to_canonical_danger_flag("धुंधली दृष्टि") == "severe_headache_or_blurred_vision"
    assert map_to_canonical_danger_flag("reduced_fetal_movement") == "reduced_fetal_movement"

    # All primary IMNCI and Maternal canonical flags must be present in canonical set
    expected_flags = {
        "convulsions",
        "not_able_to_drink_or_breastfeed",
        "lethargic_or_unconscious",
        "severe_bleeding",
        "very_high_fever",
        "vaginal_bleeding",
        "high_fever",
        "severe_headache_or_blurred_vision",
        "reduced_fetal_movement",
        "swelling_face_and_hands",
        "breathing_difficulty_or_chest_pain",
        "convulsions_or_fits",
    }
    assert expected_flags.issubset(CANONICAL_DANGER_FLAGS)


def test_danger_flag_word_boundary_and_negation_safety() -> None:
    """Word-boundary matching must prevent substring/negation false positives."""
    assert map_to_canonical_danger_flag("benefits") == "benefits"
    assert map_to_canonical_danger_flag("no_bleeding") == "no_bleeding"
    assert map_to_canonical_danger_flag("no bleeding") == "no_bleeding"
    assert map_to_canonical_danger_flag("nose_bleeding") == "nose_bleeding"
    assert map_to_canonical_danger_flag("without_fits") == "without_fits"


def test_sanitize_hindi_text_pure_indic() -> None:
    """Sanitizer replaces Perso-Arabic and Hinglish loanwords with Shuddh Tatsama."""
    raw = "मरीज को तेज बुखार और सांस की तकलीफ है। अस्पताल ले जाना जरूरी है।"
    sanitized = sanitize_hindi_text(raw)

    assert "मरीज" not in sanitized
    assert "बुखार" not in sanitized
    assert "सांस की तकलीफ" not in sanitized
    assert "अस्पताल" not in sanitized
    assert "जरूरी" not in sanitized

    assert "रोगी" in sanitized
    assert "ज्वर" in sanitized
    assert "श्वास कष्ट" in sanitized
    assert "प्राथमिक स्वास्थ्य केन्द्र" in sanitized
    assert "आवश्यक" in sanitized


def test_mocked_llm_json_parsing() -> None:
    """Mocked LLM completion correctly parses into StructuredClinicalNote."""
    structurer = LlamaCppSlmStructurer(model_path=None)

    llm_payload = {
        "extracted_symptoms": ["fever", "cough"],
        "candidate_danger_flags": ["convulsion", "unable to drink"],
        "recommended_follow_up": "Refer to Primary Health Centre immediately.",
    }
    mock_llm = MagicMock()
    mock_llm.return_value = {
        "choices": [{"text": json.dumps(llm_payload)}],
    }

    structurer._llm = mock_llm
    structurer._is_available = True

    note = structurer.structure_note("Child has fever, cough, and fits", language="en")

    assert note.backend == "llama-cpp-qwen2.5-3b-gbnf"
    assert "fever" in note.extracted_symptoms
    assert "cough" in note.extracted_symptoms
    # Canonical mapped flags
    assert note.candidate_danger_flags == ["convulsions", "not_able_to_drink_or_breastfeed"]
    assert note.recommended_follow_up == "Refer to Primary Health Centre immediately."


def test_mocked_llm_hindi_structuring() -> None:
    """Mocked LLM completion in Hindi applies Pure Indic vocabulary sanitation."""
    structurer = LlamaCppSlmStructurer(model_path=None)

    llm_payload = {
        "extracted_symptoms": ["तेज बुखार", "सांस की तकलीफ"],
        "candidate_danger_flags": ["दौरा"],
        "recommended_follow_up": "मरीज को तुरंत अस्पताल में भर्ती कराएं।",
    }
    mock_llm = MagicMock()
    mock_llm.return_value = {
        "choices": [{"text": json.dumps(llm_payload)}],
    }

    structurer._llm = mock_llm
    structurer._is_available = True

    note = structurer.structure_note("शिशु को तेज बुखार और दौरा है", language="hi")

    assert note.backend == "llama-cpp-qwen2.5-3b-gbnf"
    assert note.language == "hi"
    assert "तीव्र ज्वर" in note.extracted_symptoms
    assert "श्वास कष्ट" in note.extracted_symptoms
    assert note.candidate_danger_flags == ["convulsions"]
    assert "रोगी" in note.recommended_follow_up
    assert "प्राथमिक स्वास्थ्य केन्द्र" in note.recommended_follow_up
    assert "अस्पताल" not in note.recommended_follow_up
    assert "\u093c" not in unicodedata.normalize("NFD", note.recommended_follow_up)


def test_rejection_of_extra_severity_keys_in_json() -> None:
    """Direct JSON parser rejects any forbidden triage severity keys."""
    payload_with_severity = json.dumps({
        "extracted_symptoms": ["fever"],
        "candidate_danger_flags": ["convulsions"],
        "recommended_follow_up": "Follow up immediately",
        "severity": "RED_EMERGENCY",
    })
    with pytest.raises(ValueError, match="Clinical Safety Floor Violation"):
        parse_and_validate_slm_json(payload_with_severity)

    payload_with_triage = json.dumps({
        "extracted_symptoms": ["fever"],
        "candidate_danger_flags": [],
        "recommended_follow_up": "Follow up",
        "triage_severity": "YELLOW_PHC",
    })
    with pytest.raises(ValueError, match="Clinical Safety Floor Violation"):
        parse_and_validate_slm_json(payload_with_triage)

    payload_with_referral = json.dumps({
        "extracted_symptoms": ["cough"],
        "candidate_danger_flags": [],
        "recommended_follow_up": "Follow up",
        "referral_required": True,
    })
    with pytest.raises(ValueError, match="Clinical Safety Floor Violation"):
        parse_and_validate_slm_json(payload_with_referral)


def test_structure_note_safely_rejects_llm_severity_override() -> None:
    """When LLM attempts to output severity, structure_note falls back cleanly."""
    structurer = LlamaCppSlmStructurer(model_path=None)

    llm_payload = {
        "extracted_symptoms": ["fever"],
        "candidate_danger_flags": ["convulsions"],
        "recommended_follow_up": "Immediate triage",
        "severity": "RED_EMERGENCY",
    }
    mock_llm = MagicMock()
    mock_llm.return_value = {
        "choices": [{"text": json.dumps(llm_payload)}],
    }

    structurer._llm = mock_llm
    structurer._is_available = True

    note = structurer.structure_note("Child has fever and convulsions")

    # The unauthorized severity override must be rejected, falling back to deterministic stub
    assert note.backend == "stub-slm-fallback"
    assert not hasattr(note, "severity")
    assert "severity" not in note.model_dump()


def test_env_var_model_path_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """Structurer respects AAROGYA_SLM_GGUF_PATH environment variable."""
    fake_path = "/tmp/fake_qwen_model.gguf"
    monkeypatch.setenv("AAROGYA_SLM_GGUF_PATH", fake_path)

    structurer = LlamaCppSlmStructurer()
    assert structurer.model_path == Path(fake_path)


def test_hindi_system_prompt_uses_pure_tatsama_no_hinglish() -> None:
    """Hindi SLM prompt must use pure Shuddh Tatsama (निर्गत) with zero Hinglish or nukta."""
    structurer = LlamaCppSlmStructurer(model_path=None)
    prompt = structurer._build_prompt("शिशु को तीव्र ज्वर है।", language="hi")

    assert "निर्गत" in prompt
    assert "आउटपुट" not in prompt
    assert "\u093c" not in unicodedata.normalize("NFD", prompt)


def test_sanitize_hindi_text_strips_nukta_and_replaces_tez_and_hinglish() -> None:
    """Sanitizer converts तेज़/तेज -> तीव्र, आउटपुट -> निर्गत, and strips all NFD nukta."""
    sanitized = sanitize_hindi_text("तेज़ बुख़ार और फ़ौरन आउटपुट")
    assert sanitized == "तीव्र ज्वर और तत्काल निर्गत"
    assert "\u093c" not in unicodedata.normalize("NFD", sanitized)

    # Stray precomposed/decomposed nuktas are removed without damaging matras or anusvara
    stray = sanitize_hindi_text("क़ख़ग़ज़फ़ और श्वास कष्ट तथा संदेह")
    assert "\u093c" not in unicodedata.normalize("NFD", stray)
    assert "श्वास कष्ट" in stray
    assert "संदेह" in stray


def test_expanded_rural_clinical_vocabulary_size_and_v2_alignment() -> None:
    """Expanded lexicon covers 60+ EN/HI danger-sign & symptom phrasings aligned with v2.0.0 rules."""
    assert len(DANGER_FLAG_SYNONYMS) >= 90
    assert len(SYMPTOM_SYNONYMS) >= 45
    assert len(CANONICAL_DANGER_FLAGS) >= 35

    # Young-infant PSBI & pediatric v2.0.0 canonical mappings
    assert map_to_canonical_danger_flag("नाभि से पूय") == "umbilicus_red_or_draining_pus"
    assert map_to_canonical_danger_flag("weak cry") == "poor_feeding_or_weak_cry"
    assert map_to_canonical_danger_flag("yellow palms soles") == "jaundice_palms_or_soles"
    assert map_to_canonical_danger_flag("mastoiditis") == "mastoiditis_tender_swelling_behind_ear"
    assert map_to_canonical_danger_flag("dengue hemorrhagic signs") == "dengue_warning_signs"
    assert map_to_canonical_danger_flag("failed appetite test") == "failed_appetite_test_sam"

    # Maternal v2.0.0 canonical mappings
    assert map_to_canonical_danger_flag("puerperal sepsis") == "puerperal_sepsis_signs"
    assert map_to_canonical_danger_flag("lscs scar tenderness") == "previous_lscs_scar_tenderness"
    assert map_to_canonical_danger_flag("प्रसवोत्तर रक्तस्राव") == "postpartum_hemorrhage_heavy"
    assert map_to_canonical_danger_flag("अस्पष्ट दृष्टि") == "severe_headache_or_blurred_vision"
    assert map_to_canonical_symptom("उच्च रक्तचाप") == "high_blood_pressure"
    assert map_to_canonical_symptom("गर्भकालीन मधुमेह") == "gestational_diabetes_gdm"


def test_fallback_negation_safety_and_maternal_sos_extraction() -> None:
    """Offline fallback detects EN/HI maternal SOS and NEVER hallucinates negated flags."""
    structurer = LlamaCppSlmStructurer(model_path=None)

    # Judge Trap A #1: maternal_sos in English + pure Shuddh Tatsama Hindi
    sos_en = structurer.structure_note(
        "Pregnant mother has severe headache, blurred vision, BP 162/108",
        language="en",
    )
    assert sos_en.backend == "stub-slm-fallback"
    assert "severe_headache_or_blurred_vision" in sos_en.candidate_danger_flags
    assert "general_checkup" not in sos_en.extracted_symptoms

    sos_hi = structurer.structure_note(
        "गर्भवती महिला को तीव्र शिरोवेदना, अस्पष्ट दृष्टि और उच्च रक्तचाप है।",
        language="hi",
    )
    assert "severe_headache_or_blurred_vision" in sos_hi.candidate_danger_flags
    assert "high_blood_pressure" in sos_hi.extracted_symptoms
    assert "\u093c" not in unicodedata.normalize("NFD", sos_hi.recommended_follow_up)

    # Judge Trap A #2: Negation safety in English and Hindi SOV
    neg_en = structurer.structure_note("Child denies fits; no convulsions, no bleeding", language="en")
    assert neg_en.candidate_danger_flags == []

    neg_hi_sym, neg_hi_flags = extract_clinical_signals_from_text(
        "शिशु को दौरा नहीं है, रक्तस्राव अनुपस्थित, आक्षेप रहित।"
    )
    assert neg_hi_flags == []
    assert "convulsions" not in neg_hi_sym
    assert "severe_bleeding" not in neg_hi_sym


def test_untranscribed_stub_and_unrelated_transcripts_never_fabricate_fever_cough() -> None:
    """Stub untranscribed audio markers and unrelated transcripts must not fabricate fever/cough."""
    structurer = LlamaCppSlmStructurer(model_path=None)

    stub_en = structurer.structure_note(
        "[stub-audio-2048-bytes] Audio recorded; local Whisper ASR model not loaded.",
        language="en",
    )
    assert stub_en.extracted_symptoms == []
    assert stub_en.candidate_danger_flags == []
    assert "fever" not in stub_en.recommended_follow_up.lower()
    assert "cough" not in stub_en.recommended_follow_up.lower()

    stub_hi = structurer.structure_note(
        "[stub-audio-2048-bytes] Audio recorded; local Whisper ASR model not loaded.",
        language="hi",
    )
    assert stub_hi.extracted_symptoms == []
    assert stub_hi.candidate_danger_flags == []
    assert "\u093c" not in unicodedata.normalize("NFD", stub_hi.recommended_follow_up)

    headache_only = structurer.structure_note("Patient reports mild headache.", language="en")
    assert headache_only.extracted_symptoms == ["headache"]
    assert "fever" not in headache_only.extracted_symptoms
    assert "cough" not in headache_only.extracted_symptoms

    routine = structurer.structure_note("Routine immunization and growth monitoring visit.", language="en")
    assert "fever" not in routine.extracted_symptoms
    assert "cough" not in routine.extracted_symptoms

    spoken_resp = structurer.structure_note("Patient has shortness of breath and chills.", language="en")
    assert "fast_breathing" in spoken_resp.extracted_symptoms
    assert "fever" in spoken_resp.extracted_symptoms

    spoken_hi = structurer.structure_note("रोगी को सांस फूलना और ठंड लगना है।", language="hi")
    assert "fast_breathing" in spoken_hi.extracted_symptoms
    assert "fever" in spoken_hi.extracted_symptoms
