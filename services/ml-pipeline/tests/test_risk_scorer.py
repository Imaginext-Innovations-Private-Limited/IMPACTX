"""Tests for LightGBM + TreeSHAP Tabular Risk Scorer."""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import patch

from aarogya_ml_pipeline.interfaces import (
    RiskScorer,
    RiskScoreResult,
    StubRiskScorer,
)
from aarogya_ml_pipeline.risk_scorer import (
    DEFAULT_FEATURE_VALUES,
    RISK_FEATURE_NAMES,
    LightGbmRiskScorer,
    extract_risk_features,
)


def test_risk_scorer_protocol_conformance() -> None:
    """Verify LightGbmRiskScorer conforms to runtime-checkable RiskScorer protocol."""
    scorer = LightGbmRiskScorer()
    assert isinstance(scorer, RiskScorer)
    assert hasattr(scorer, "score_risk")
    assert callable(scorer.score_risk)

    stub = StubRiskScorer()
    assert isinstance(stub, RiskScorer)


def test_risk_feature_names_canonical() -> None:
    """Verify canonical ordered features match expected clinical schema."""
    expected = [
        "age_months",
        "fever_days",
        "temperature_c",
        "respiratory_rate_bpm",
        "spo2_pct",
        "systolic_bp",
        "diastolic_bp",
        "hemoglobin_g_dl",
        "muac_cm",
        "is_pregnant",
        "gestational_weeks",
        "has_danger_sign",
        "symptom_count",
    ]
    assert RISK_FEATURE_NAMES == expected
    for name in expected:
        assert name in DEFAULT_FEATURE_VALUES


def test_deterministic_scoring() -> None:
    """Verify identical inputs produce identical risk scores and TreeSHAP attributions."""
    scorer = LightGbmRiskScorer()
    features: dict[str, float | int | bool] = {
        "age_months": 24,
        "fever_days": 3,
        "temperature_c": 38.6,
        "respiratory_rate_bpm": 48,
        "spo2_pct": 94,
        "systolic_bp": 98,
        "diastolic_bp": 62,
        "hemoglobin_g_dl": 10.2,
        "muac_cm": 12.8,
        "is_pregnant": False,
        "gestational_weeks": None,  # type: ignore[dict-item]
        "has_danger_sign": False,
        "symptom_count": 2,
    }

    res1 = scorer.score_risk(features)
    res2 = scorer.score_risk(features)

    assert isinstance(res1, RiskScoreResult)
    assert isinstance(res2, RiskScoreResult)
    assert res1.risk_score == res2.risk_score
    assert res1.risk_band == res2.risk_band
    assert res1.shap_attributions == res2.shap_attributions
    assert 0.0 <= res1.risk_score <= 1.0


def test_monotonicity_with_danger_signs() -> None:
    """Verify danger sign presence monotonically increases risk score."""
    scorer = LightGbmRiskScorer()
    base_patient: dict[str, float | int | bool] = {
        "age_months": 18,
        "fever_days": 1,
        "temperature_c": 37.4,
        "respiratory_rate_bpm": 28,
        "spo2_pct": 98,
        "systolic_bp": 92,
        "diastolic_bp": 58,
        "hemoglobin_g_dl": 12.5,
        "muac_cm": 14.5,
        "is_pregnant": False,
        "has_danger_sign": False,
        "symptom_count": 1,
    }

    danger_patient = dict(base_patient)
    danger_patient["has_danger_sign"] = True

    base_res = scorer.score_risk(base_patient)
    danger_res = scorer.score_risk(danger_patient)

    assert danger_res.risk_score > base_res.risk_score


def test_monotonicity_with_fever_and_hypoxia() -> None:
    """Verify worsening fever and hypoxia monotonically increase risk."""
    scorer = LightGbmRiskScorer()
    mild_patient: dict[str, float | int | bool] = {
        "age_months": 36,
        "fever_days": 0,
        "temperature_c": 36.8,
        "respiratory_rate_bpm": 24,
        "spo2_pct": 99,
        "hemoglobin_g_dl": 12.5,
        "has_danger_sign": False,
        "symptom_count": 0,
    }

    severe_patient: dict[str, float | int | bool] = dict(mild_patient)
    severe_patient.update({
        "fever_days": 6,
        "temperature_c": 39.8,
        "respiratory_rate_bpm": 62,
        "spo2_pct": 86,
        "symptom_count": 4,
    })

    mild_res = scorer.score_risk(mild_patient)
    severe_res = scorer.score_risk(severe_patient)

    assert severe_res.risk_score > mild_res.risk_score
    assert severe_res.risk_band in ("MODERATE", "HIGH")


def test_shap_attributions_keys_and_values() -> None:
    """Verify shap_attributions contains finite floats for canonical features."""
    scorer = LightGbmRiskScorer()
    features: dict[str, float | int | bool] = {
        "age_months": 240,
        "is_pregnant": True,
        "gestational_weeks": 28,
        "systolic_bp": 155,
        "diastolic_bp": 102,
        "fever_days": 2,
        "temperature_c": 38.2,
        "has_danger_sign": True,
        "symptom_count": 3,
    }

    res = scorer.score_risk(features)
    assert isinstance(res.shap_attributions, dict)
    assert len(res.shap_attributions) > 0

    for k, v in res.shap_attributions.items():
        assert isinstance(k, str)
        assert isinstance(v, float)
        assert not math.isnan(v)
        assert not math.isinf(v)

    if not scorer.is_fallback:
        for feat in RISK_FEATURE_NAMES:
            assert feat in res.shap_attributions


def test_missing_model_fallback() -> None:
    """Verify fallback to StubRiskScorer when model file does not exist."""
    missing_path = Path("/tmp/nonexistent_model_dir_12345/missing_model.txt")
    scorer = LightGbmRiskScorer(model_path=missing_path)

    assert scorer.is_fallback is True
    res = scorer.score_risk({"has_danger_sign": True, "fever_days": 4})

    assert isinstance(res, RiskScoreResult)
    assert res.backend == "stub-lightgbm-fallback"
    assert 0.0 <= res.risk_score <= 1.0
    assert res.risk_band in ("LOW", "MODERATE", "HIGH")


def test_missing_lightgbm_dependency_fallback() -> None:
    """Verify fallback when LightGBM module is not available."""
    with patch("aarogya_ml_pipeline.risk_scorer.lgb", None):
        scorer = LightGbmRiskScorer()
        assert scorer.is_fallback is True
        res = scorer.score_risk({"has_danger_sign": False, "fever_days": 1})
        assert res.backend == "stub-lightgbm-fallback"
        assert 0.0 <= res.risk_score <= 1.0


def test_empty_and_partial_features() -> None:
    """Verify scorer handles empty and partial feature dictionaries without errors."""
    scorer = LightGbmRiskScorer()
    res_empty = scorer.score_risk({})
    assert isinstance(res_empty, RiskScoreResult)
    assert 0.0 <= res_empty.risk_score <= 1.0

    res_partial = scorer.score_risk({"fever_days": 2, "temperature_c": 38.0})
    assert isinstance(res_partial, RiskScoreResult)
    assert 0.0 <= res_partial.risk_score <= 1.0


def test_risk_bands_calibration() -> None:
    """Verify calibrated bands match clinical cutoff boundaries."""
    scorer = LightGbmRiskScorer()

    # Low risk
    low = scorer.score_risk({
        "age_months": 24,
        "fever_days": 0,
        "temperature_c": 36.6,
        "has_danger_sign": False,
        "symptom_count": 0,
    })
    if low.risk_score < 0.35:
        assert low.risk_band == "LOW"

    # High risk with multiple critical flags
    high = scorer.score_risk({
        "has_danger_sign": True,
        "fever_days": 7,
        "temperature_c": 40.2,
        "spo2_pct": 82,
        "symptom_count": 5,
        "respiratory_rate_bpm": 75,
    })
    if high.risk_score >= 0.70:
        assert high.risk_band == "HIGH"


def test_extract_risk_features_helper() -> None:
    """Verify feature extractor parses dicts and TriageInput representations."""
    data = {
        "age_months": 12,
        "fever_days": 2,
        "temperature_c": 38.0,
        "danger_signs": ["convulsions"],
        "symptoms": ["cough", "fever"],
        "is_pregnant": False,
    }
    extracted = extract_risk_features(data)
    assert extracted["age_months"] == 12
    assert extracted["fever_days"] == 2
    assert extracted["has_danger_sign"] is True
    assert extracted["symptom_count"] == 2
    assert extracted["is_pregnant"] is False


def test_clinical_safety_floor_non_override() -> None:
    """Verify that RiskScoreResult is strictly advisory and has no triage severity override."""
    scorer = LightGbmRiskScorer()
    res = scorer.score_risk({"has_danger_sign": True})

    # RiskScoreResult must strictly follow the contract schema (no triage_severity field)
    dump = res.model_dump()
    assert "risk_score" in dump
    assert "risk_band" in dump
    assert "shap_attributions" in dump
    assert "backend" in dump
    assert "triage_severity" not in dump
    assert "referral_required" not in dump


def test_embedded_portable_gbdt_artifact_and_exact_treeshap_efficiency() -> None:
    """Embedded GBDT JSON (<30 KiB) runs exact Lundberg TreeSHAP with +/- attributions."""
    from aarogya_ml_pipeline.gbdt_treeshap import DEFAULT_ARTIFACT_PATH, PortableGbdtModel

    assert DEFAULT_ARTIFACT_PATH.is_file()
    assert DEFAULT_ARTIFACT_PATH.stat().st_size < 30 * 1024

    model = PortableGbdtModel.from_json_file(DEFAULT_ARTIFACT_PATH)
    assert model.num_trees >= 20
    assert model.feature_names == RISK_FEATURE_NAMES
    assert model.metrics["auroc"] >= 0.80

    scorer = LightGbmRiskScorer(model_path=Path("/tmp/nonexistent_lgbm_model.txt"))
    assert scorer.is_fallback is True
    assert scorer.portable_model is not None

    healthy = {
        "age_months": 36,
        "fever_days": 0,
        "temperature_c": 36.8,
        "respiratory_rate_bpm": 24,
        "spo2_pct": 99,
        "systolic_bp": 95,
        "diastolic_bp": 60,
        "hemoglobin_g_dl": 12.8,
        "muac_cm": 15.0,
        "is_pregnant": False,
        "has_danger_sign": False,
        "symptom_count": 0,
    }
    critical_maternal = {
        "age_months": 288,
        "fever_days": 3,
        "temperature_c": 39.0,
        "respiratory_rate_bpm": 26,
        "spo2_pct": 89,
        "systolic_bp": 168,
        "diastolic_bp": 112,
        "hemoglobin_g_dl": 6.4,
        "is_pregnant": True,
        "gestational_weeks": 32,
        "has_danger_sign": True,
        "symptom_count": 4,
    }
    young_infant_psbi = {
        "age_months": 1,
        "fever_days": 1,
        "temperature_c": 38.2,
        "respiratory_rate_bpm": 66,
        "spo2_pct": 90,
        "is_pregnant": False,
        "has_danger_sign": False,
        "symptom_count": 2,
    }

    for sample in (healthy, critical_maternal, young_infant_psbi):
        row = scorer._build_feature_row(sample, use_neutral_defaults=True)
        prob, margin, base_val, shap = model.explain(row)
        # Lundberg TreeSHAP Local Accuracy: base_value + sum(phi) == raw_margin
        assert abs((base_val + sum(shap.values())) - margin) < 1e-3
        assert set(shap.keys()) == set(RISK_FEATURE_NAMES)
        assert 0.0 <= prob <= 1.0

    healthy_res = scorer.score_risk(healthy)
    critical_res = scorer.score_risk(critical_maternal)
    psbi_res = scorer.score_risk(young_infant_psbi)

    assert healthy_res.backend == "stub-lightgbm-fallback"
    assert healthy_res.risk_band == "LOW"
    assert any(v < 0.0 for v in healthy_res.shap_attributions.values())

    assert critical_res.risk_band == "HIGH"
    assert any(v > 0.0 for v in critical_res.shap_attributions.values())
    assert critical_res.risk_score > healthy_res.risk_score

    assert psbi_res.risk_score > healthy_res.risk_score
    assert psbi_res.risk_band in ("MODERATE", "HIGH")

    # Partial healthy child with omitted Hb/MUAC/BP must score LOW (never fake anemia/SAM)
    partial_healthy = scorer.score_risk({
        "age_months": 30,
        "temperature_c": 36.8,
        "spo2_pct": 99,
        "respiratory_rate_bpm": 26,
    })
    assert partial_healthy.risk_band == "LOW"
    assert partial_healthy.risk_score < 0.35
    assert partial_healthy.shap_attributions["hemoglobin_g_dl"] <= 0.05
    assert partial_healthy.shap_attributions["spo2_pct"] <= 0.05
