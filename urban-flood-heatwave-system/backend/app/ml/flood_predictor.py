"""
Flood Risk ML Predictor
Combines: rainfall forecast + drainage sensor data + lake level + elevation + citizen reports
Uses a gradient-boosted ensemble (scikit-learn) with a fallback rule-based scorer.
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class FloodFeatures:
    rainfall_mm_1h: float          # Rainfall last 1 hour
    rainfall_mm_3h: float          # Rainfall last 3 hours
    rainfall_forecast_6h: float    # Forecast next 6 hours
    drainage_capacity_mm: float    # Drainage capacity mm/hr
    drainage_blockage_pct: float   # 0-100 blockage
    lake_level_pct: float          # 0-100 lake fill level
    elevation_m: float             # Street elevation (lower = more risk)
    soil_saturation: float         # 0-1 (derived from prior rainfall)
    citizen_reports_1h: int        # Flood reports in area last hour
    water_level_cm: float          # Sensor water level in drain


def rule_based_flood_score(f: FloodFeatures) -> float:
    """
    Transparent rule-based flood risk scorer.
    Returns a risk score 0.0 (safe) to 1.0 (critical).
    """
    score = 0.0

    # Rainfall contribution (max 0.35)
    rain_ratio = min((f.rainfall_mm_1h + f.rainfall_mm_3h * 0.5) / 100.0, 1.0)
    score += rain_ratio * 0.35

    # Drainage saturation (max 0.25)
    effective_capacity = max(f.drainage_capacity_mm * (1 - f.drainage_blockage_pct / 100), 1.0)
    drain_stress = min(f.rainfall_mm_1h / effective_capacity, 1.0)
    score += drain_stress * 0.25

    # Lake level pressure (max 0.15)
    score += (f.lake_level_pct / 100.0) * 0.15

    # Elevation risk (lower = higher risk, max 0.10)
    elev_risk = max(0.0, 1.0 - f.elevation_m / 20.0)  # < 20m adds risk
    score += elev_risk * 0.10

    # Soil saturation (max 0.10)
    score += f.soil_saturation * 0.10

    # Citizen reports (max 0.05)
    report_factor = min(f.citizen_reports_1h / 10.0, 1.0)
    score += report_factor * 0.05

    return min(score, 1.0)


def classify_risk(score: float) -> str:
    if score >= 0.75:
        return "CRITICAL"
    elif score >= 0.5:
        return "HIGH"
    elif score >= 0.25:
        return "MEDIUM"
    return "LOW"


class FloodPredictor:
    """
    Wraps rule-based scorer with optional sklearn model (loaded at startup).
    Falls back to rule-based if model not available.
    """

    def __init__(self):
        self.model = None
        self._try_load_model()

    def _try_load_model(self):
        try:
            import joblib, os
            model_path = os.path.join(os.path.dirname(__file__), "flood_model.pkl")
            if os.path.exists(model_path):
                self.model = joblib.load(model_path)
        except Exception:
            self.model = None

    def predict(self, features: FloodFeatures) -> dict:
        if self.model is not None:
            X = np.array([[
                features.rainfall_mm_1h,
                features.rainfall_mm_3h,
                features.rainfall_forecast_6h,
                features.drainage_capacity_mm,
                features.drainage_blockage_pct,
                features.lake_level_pct,
                features.elevation_m,
                features.soil_saturation,
                features.citizen_reports_1h,
                features.water_level_cm,
            ]])
            score = float(self.model.predict_proba(X)[0][1])
        else:
            score = rule_based_flood_score(features)

        risk_level = classify_risk(score)
        return {
            "risk_score": round(score, 4),
            "risk_level": risk_level,
            "model_used": "ml_model" if self.model else "rule_based",
        }


# Singleton
flood_predictor = FloodPredictor()
