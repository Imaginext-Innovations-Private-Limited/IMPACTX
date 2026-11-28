"""Unit tests for EWMA Spatiotemporal Outbreak Detector (T4-04)."""

from __future__ import annotations

import pytest

from aarogya_contracts import TriageSeverity
from aarogya_ml_pipeline.interfaces import OutbreakDetector, OutbreakSignal
from aarogya_ml_pipeline.outbreak_detector import (
    EwmaOutbreakDetector,
    MultiSyndromeSurveillanceReport,
    evaluate_village_syndromes,
    summarize_multi_syndrome_surveillance,
)


def test_protocol_conformance() -> None:
    detector = EwmaOutbreakDetector()
    assert isinstance(detector, OutbreakDetector)


def test_invalid_hyperparameters() -> None:
    with pytest.raises(ValueError, match="alpha"):
        EwmaOutbreakDetector(alpha=0.0)
    with pytest.raises(ValueError, match="alpha"):
        EwmaOutbreakDetector(alpha=1.5)
    with pytest.raises(ValueError, match="sigma_multiplier"):
        EwmaOutbreakDetector(sigma_multiplier=0.0)
    with pytest.raises(ValueError, match="min_baseline_days"):
        EwmaOutbreakDetector(min_baseline_days=0)
    with pytest.raises(ValueError, match="min_case_floor"):
        EwmaOutbreakDetector(min_case_floor=0)


def test_negative_counts_raise_value_error() -> None:
    detector = EwmaOutbreakDetector()
    with pytest.raises(ValueError, match="negative"):
        detector.detect_outbreak("village-01", "acute_diarrhea", [2, 3, -1, 4, 5])


def test_empty_series_handling() -> None:
    detector = EwmaOutbreakDetector()
    signal = detector.detect_outbreak("village-01", "acute_diarrhea", [])
    assert isinstance(signal, OutbreakSignal)
    assert signal.alert_triggered is False
    assert signal.ewma_value == 0.0
    assert signal.baseline_mean == 0.0
    assert signal.severity == TriageSeverity.YELLOW_PHC
    assert "empty" in signal.rationale


def test_short_series_handling() -> None:
    detector = EwmaOutbreakDetector(min_baseline_days=4)
    for length in range(1, 5):
        counts = [2] * length
        signal = detector.detect_outbreak("village-01", "acute_diarrhea", counts)
        assert isinstance(signal, OutbreakSignal)
        assert signal.alert_triggered is False
        assert "Insufficient baseline history" in signal.rationale


def test_flat_baseline_no_alert() -> None:
    detector = EwmaOutbreakDetector(alpha=0.3, sigma_multiplier=2.5, min_baseline_days=4)
    # 7 days of steady counts = 5
    counts = [5, 5, 5, 5, 5, 5, 5]
    signal = detector.detect_outbreak("village-01", "acute_diarrhea", counts)

    assert signal.alert_triggered is False
    assert signal.baseline_mean == 5.0
    assert pytest.approx(signal.ewma_value, rel=1e-3) == 5.0
    assert signal.ewma_value < signal.threshold
    assert signal.severity == TriageSeverity.YELLOW_PHC
    assert "remains within baseline threshold" in signal.rationale


def test_zero_variance_baseline_poisson_floor() -> None:
    detector = EwmaOutbreakDetector(alpha=0.3, sigma_multiplier=2.5, min_baseline_days=4, min_case_floor=3)
    # Zero counts historically, remaining zero today
    zero_signal = detector.detect_outbreak("village-01", "acute_diarrhea", [0, 0, 0, 0, 0])
    assert zero_signal.alert_triggered is False
    assert zero_signal.baseline_mean == 0.0
    assert zero_signal.ewma_value == 0.0
    assert zero_signal.threshold >= 3.0  # min_case_floor

    # Constant non-zero counts historically, remaining constant today
    const_signal = detector.detect_outbreak("village-01", "acute_diarrhea", [3, 3, 3, 3, 3])
    assert const_signal.alert_triggered is False
    assert const_signal.baseline_mean == 3.0
    assert pytest.approx(const_signal.ewma_value, rel=1e-3) == 3.0


def test_low_count_noise_suppression() -> None:
    detector = EwmaOutbreakDetector(alpha=0.3, sigma_multiplier=2.5, min_baseline_days=4, min_case_floor=3)
    # 0 -> 1 case in a small hamlet should NOT raise an outbreak alert
    signal_1 = detector.detect_outbreak("hamlet-tiny", "dengue_like_fever", [0, 0, 0, 0, 1])
    assert signal_1.alert_triggered is False

    # 1 -> 2 cases should also NOT raise an alert due to min_case_floor=3
    signal_2 = detector.detect_outbreak("hamlet-tiny", "dengue_like_fever", [1, 1, 1, 1, 2])
    assert signal_2.alert_triggered is False


def test_sudden_surge_detection_red_emergency() -> None:
    detector = EwmaOutbreakDetector(alpha=0.3, sigma_multiplier=2.5, min_baseline_days=4, min_case_floor=3)
    # Baseline ~ 1 case/day, then sudden massive spike to 25 cases today
    counts = [1, 1, 1, 1, 25]
    signal = detector.detect_outbreak("village-rampur", "acute_diarrhea", counts)

    assert signal.alert_triggered is True
    assert signal.ewma_value >= signal.threshold
    assert signal.severity == TriageSeverity.RED_EMERGENCY
    assert "EWMA surge detected" in signal.rationale
    assert signal.village_id == "village-rampur"
    assert signal.syndrome == "acute_diarrhea"


def test_moderate_surge_detection_yellow_phc() -> None:
    detector = EwmaOutbreakDetector(alpha=0.3, sigma_multiplier=2.5, min_baseline_days=4, min_case_floor=3)
    # Baseline: [2, 2, 2, 2]. mu_0 = 2.0, sigma_eff = sqrt(2) = 1.4142.
    # UCL = 2.0 + 2.5 * 1.4142 * sqrt(0.3 / 1.7) = 3.485. 2 * UCL = 6.97.
    # Today count = 7 -> z_t = 0.3 * 7 + 0.7 * 2.0 = 3.5.
    # z_t (3.5) >= threshold (3.485) and 3.5 < 2 * UCL (6.97) -> YELLOW_PHC.
    counts = [2, 2, 2, 2, 7]
    signal = detector.detect_outbreak("village-shampur", "dengue_like_fever", counts)

    assert signal.alert_triggered is True
    assert signal.severity == TriageSeverity.YELLOW_PHC
    assert "EWMA surge detected" in signal.rationale


def test_multi_day_accumulated_surge() -> None:
    detector = EwmaOutbreakDetector(alpha=0.3, sigma_multiplier=2.5, min_baseline_days=4, min_case_floor=3)
    # Baseline is ~2 cases, followed by escalating surge over 3 days
    counts = [2, 2, 2, 2, 5, 8, 12]
    signal = detector.detect_outbreak("village-kalyan", "respiratory_infection", counts)

    assert signal.alert_triggered is True
    assert signal.severity in (TriageSeverity.YELLOW_PHC, TriageSeverity.RED_EMERGENCY)


def test_evaluate_village_syndromes_batch_scanning() -> None:
    counts_by_key = {
        ("village-b", "acute_diarrhea"): [1, 1, 1, 1, 20],  # Surge
        ("village-a", "dengue_like_fever"): [0, 0, 0, 0, 1],  # Suppressed noise
        ("village-a", "acute_diarrhea"): [5, 5, 5, 5, 5],  # Flat
    }

    results = evaluate_village_syndromes(counts_by_key)
    assert len(results) == 3

    # Sorted order verification: ("village-a", "acute_diarrhea"), ("village-a", "dengue_like_fever"), ("village-b", "acute_diarrhea")
    assert results[0].village_id == "village-a" and results[0].syndrome == "acute_diarrhea"
    assert results[0].alert_triggered is False

    assert results[1].village_id == "village-a" and results[1].syndrome == "dengue_like_fever"
    assert results[1].alert_triggered is False

    assert results[2].village_id == "village-b" and results[2].syndrome == "acute_diarrhea"
    assert results[2].alert_triggered is True
    assert results[2].severity == TriageSeverity.RED_EMERGENCY


def test_zero_baseline_moderate_surge_reaches_yellow_phc() -> None:
    """Zero-baseline villages can trigger YELLOW_PHC before escalating to RED_EMERGENCY."""
    detector = EwmaOutbreakDetector(alpha=0.3, sigma_multiplier=2.5, min_baseline_days=4, min_case_floor=3)
    moderate = detector.detect_outbreak("village-zero", "acute_diarrhea", [0, 0, 0, 0, 10])
    assert moderate.alert_triggered is True
    assert moderate.severity == TriageSeverity.YELLOW_PHC

    extreme = detector.detect_outbreak("village-zero", "acute_diarrhea", [0, 0, 0, 0, 22])
    assert extreme.alert_triggered is True
    assert extreme.severity == TriageSeverity.RED_EMERGENCY


def test_summarize_multi_syndrome_surveillance_identifies_clusters_and_ranks() -> None:
    """Multi-syndrome summary flags co-occurring village outbreaks and ranks by severity."""
    counts_by_key = {
        ("village-rampur", "acute_diarrhea"): [1, 1, 1, 1, 22],  # RED
        ("village-rampur", "dengue_like_fever"): [2, 2, 2, 2, 7],  # YELLOW
        ("village-shampur", "respiratory_infection"): [2, 2, 2, 2, 7],  # YELLOW
        ("village-calm", "acute_diarrhea"): [2, 2, 2, 2, 2],  # GREEN (no alert)
    }
    report = summarize_multi_syndrome_surveillance(counts_by_key)
    assert isinstance(report, MultiSyndromeSurveillanceReport)
    assert report.total_series_evaluated == 4
    assert report.total_villages_monitored == 3
    assert report.total_alerts == 3
    assert report.red_alert_count == 1
    assert report.yellow_alert_count == 2
    assert report.multi_syndrome_villages == ["village-rampur"]
    assert report.syndrome_alert_counts == {
        "acute_diarrhea": 1,
        "dengue_like_fever": 1,
        "respiratory_infection": 1,
    }
    # Ranked RED -> YELLOW -> GREEN
    assert [v.village_id for v in report.villages] == [
        "village-rampur",
        "village-shampur",
        "village-calm",
    ]
    assert report.villages[0].multi_syndrome_cluster is True
    assert report.villages[0].highest_severity == TriageSeverity.RED_EMERGENCY
    assert report.villages[0].total_latest_cases == 29
    assert report.villages[2].highest_severity == TriageSeverity.GREEN_HOME
