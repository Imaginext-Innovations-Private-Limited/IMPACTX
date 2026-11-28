"""
Heatwave Risk Calculator
Uses temperature, humidity, UV index, urban heat island factor, and time-of-day.
Outputs a Heat Index + risk level + recommended actions.
"""

import math
from dataclasses import dataclass


@dataclass
class HeatFeatures:
    temp_celsius: float
    humidity_pct: float
    uv_index: float
    wind_speed_kmh: float
    urban_heat_island_offset: float   # extra degrees due to UHI effect (~2-5°C)
    is_night: bool
    consecutive_hot_days: int         # number of days above threshold


def heat_index(temp_c: float, rh: float) -> float:
    """
    Steadman's Heat Index formula (Celsius).
    Returns the feels-like temperature.
    """
    T = temp_c * 9 / 5 + 32  # convert to Fahrenheit for formula
    HI = (-42.379
          + 2.04901523 * T
          + 10.14333127 * rh
          - 0.22475541 * T * rh
          - 0.00683783 * T * T
          - 0.05481717 * rh * rh
          + 0.00122874 * T * T * rh
          + 0.00085282 * T * rh * rh
          - 0.00000199 * T * T * rh * rh)
    return (HI - 32) * 5 / 9  # back to Celsius


def calculate_heatwave_risk(f: HeatFeatures) -> dict:
    """
    Returns risk score (0-1), risk level, heat index, and health advice.
    """
    effective_temp = f.temp_celsius + f.urban_heat_island_offset
    hi = heat_index(effective_temp, f.humidity_pct)

    # Risk score components
    score = 0.0

    # Temperature component (max 0.40)
    temp_score = max(0.0, (effective_temp - 30) / 20.0)
    score += min(temp_score, 1.0) * 0.40

    # Heat index beyond raw temp (max 0.25)
    hi_excess = max(0.0, hi - effective_temp) / 15.0
    score += min(hi_excess, 1.0) * 0.25

    # UV index component (max 0.15)
    score += min(f.uv_index / 11.0, 1.0) * 0.15

    # Consecutive hot days amplifier (max 0.10)
    score += min(f.consecutive_hot_days / 7.0, 1.0) * 0.10

    # Wind chill relief (reduce score)
    wind_relief = min(f.wind_speed_kmh / 30.0, 1.0) * 0.10
    score = max(0.0, score - wind_relief)

    # Night reduces risk
    if f.is_night:
        score *= 0.60

    score = min(score, 1.0)

    # Classify
    if score >= 0.75:
        risk_level = "CRITICAL"
        advice = [
            "Extreme heat emergency – stay indoors with AC",
            "Go to nearest cooling centre immediately",
            "Do not exercise outdoors",
            "Check on elderly neighbours",
            "Call emergency services if someone collapses",
        ]
    elif score >= 0.5:
        risk_level = "HIGH"
        advice = [
            "Avoid outdoor activities between 11am–4pm",
            "Drink water every 20 minutes",
            "Visit a cooling centre if you have no AC",
            "Wear light, loose clothing and sunscreen",
        ]
    elif score >= 0.25:
        risk_level = "MEDIUM"
        advice = [
            "Stay hydrated and limit sun exposure",
            "Use fans and keep curtains closed",
            "Check the latest heatwave forecast",
        ]
    else:
        risk_level = "LOW"
        advice = ["Conditions are normal – stay hydrated."]

    return {
        "risk_score": round(score, 4),
        "risk_level": risk_level,
        "heat_index_celsius": round(hi, 1),
        "effective_temp_celsius": round(effective_temp, 1),
        "health_advice": advice,
    }
