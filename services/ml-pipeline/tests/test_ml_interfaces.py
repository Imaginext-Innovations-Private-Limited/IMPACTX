"""Contract and protocol tests for Aarogya Mesh Tier-2 ML pipeline."""

from aarogya_contracts import (
    ActionCard,
    CrdtEvent,
    EnrichmentState,
    EventType,
    HlcTimestamp,
)
from aarogya_ml_pipeline import (
    ClinicalSlmStructurer,
    OutbreakDetector,
    RiskScorer,
    StubClinicalSlmStructurer,
    StubOutbreakDetector,
    StubRiskScorer,
    StubVoiceTranscriber,
    VoiceTranscriber,
    enrich_voice_note_event,
)


def test_protocols_and_stubs_are_runtime_compatible() -> None:
    asr = StubVoiceTranscriber()
    slm = StubClinicalSlmStructurer()
    scorer = StubRiskScorer()
    detector = StubOutbreakDetector()

    assert isinstance(asr, VoiceTranscriber)
    assert isinstance(slm, ClinicalSlmStructurer)
    assert isinstance(scorer, RiskScorer)
    assert isinstance(detector, OutbreakDetector)

    transcript = asr.transcribe(b"Child has fever and fast breathing", language_hint="en")
    structured = slm.structure_note(transcript.transcript, language="en")
    risk = scorer.score_risk({"fever_days": 3, "has_danger_sign": False})
    signal = detector.detect_outbreak("village-01", "acute_fever", [1, 1, 2, 1, 8])

    assert "fever" in structured.extracted_symptoms
    assert "fast_breathing" in structured.extracted_symptoms
    assert 0.0 <= risk.risk_score <= 1.0
    assert signal.alert_triggered is True


def test_enrich_voice_note_event_emits_valid_contracts() -> None:
    voice_event = CrdtEvent(
        event_id="evt-voice-001",
        hlc=HlcTimestamp(wall_ms=1_700_000_000_000, logical=0, node_id="phone-asha-01"),
        origin_node_id="phone-asha-01",
        patient_id="pat-001",
        event_type=EventType.VOICE_NOTE_RECORDED,
        enrichment_state=EnrichmentState.PENDING,
        payload={
            "language": "en",
            "transcript_hint": "Mother reports convulsion and fever.",
        },
    )

    emitted = enrich_voice_note_event(
        voice_event,
        hub_node_id="phc-hub-01",
        hlc=HlcTimestamp(wall_ms=1_700_000_005_000, logical=0, node_id="phc-hub-01"),
    )
    assert len(emitted) == 2
    enrichment_evt, card_evt = emitted

    assert enrichment_evt.event_type == EventType.ENRICHMENT_COMPLETED
    assert enrichment_evt.ref_event_id == "evt-voice-001"
    assert enrichment_evt.enrichment_state == EnrichmentState.COMPLETED

    assert card_evt.event_type == EventType.ACTION_CARD_ISSUED
    assert card_evt.ref_event_id == "evt-voice-001"
    card = ActionCard.model_validate(card_evt.payload)
    assert card.patient_id == "pat-001"
    assert card.source_event_id == enrichment_evt.event_id
