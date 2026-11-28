#!/usr/bin/env python3
"""Train a deterministic synthetic LightGBM risk scoring model for Aarogya Mesh.

Generates synthetic pediatric and maternal patient records aligned with
``aarogya_clinical_engine.TriageInput`` features and trains a compact,
CPU-optimized LightGBM binary classifier serialized to text format.

Clinical Safety Invariant:
    Risk scores produced by this model are strictly advisory and NEVER
    override or downgrade deterministic triage rules in ``aarogya_clinical_engine``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from aarogya_ml_pipeline.gbdt_treeshap import (
    DEFAULT_ARTIFACT_PATH,
    train_portable_gbdt_artifact,
)

try:
    import numpy as np
except ImportError:
    np = None  # type: ignore[assignment]

try:
    import lightgbm as lgb
except ImportError:
    lgb = None


RISK_FEATURE_NAMES: list[str] = [
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

# Monotonicity constraints: +1 = increasing risk, -1 = decreasing risk, 0 = unconstrained
# Guaranteed to preserve clinical risk ordering
MONOTONE_CONSTRAINTS: list[int] = [
    0,   # age_months: non-linear across pediatric/maternal
    1,   # fever_days: longer fever -> higher risk
    1,   # temperature_c: higher fever -> higher risk
    1,   # respiratory_rate_bpm: fast breathing -> higher risk
    -1,  # spo2_pct: lower oxygen -> higher risk
    1,   # systolic_bp: hypertension -> higher risk
    1,   # diastolic_bp: hypertension -> higher risk
    -1,  # hemoglobin_g_dl: lower Hb (severe anemia) -> higher risk
    -1,  # muac_cm: lower MUAC (SAM malnutrition) -> higher risk
    0,   # is_pregnant
    0,   # gestational_weeks
    1,   # has_danger_sign: any WHO danger sign -> strongly higher risk
    1,   # symptom_count: more co-occurring symptoms -> higher risk
]


def generate_synthetic_data(
    n_samples: int = 3000,
    seed: int = 42,
) -> tuple[Any, Any]:
    """Generate synthetic young-infant, pediatric, and maternal clinical records.

    Encodes clinically authentic WHO IMNCI and NHM ASHA interaction effects:
    - Age-band tachypnea thresholds (<2m: >=60, 2-11m: >=50, 12-59m: >=40, adult: >=24 bpm)
    - Young-infant (<2m PSBI) thermal instability (fever >=37.5C or hypothermia <35.5C)
    - Cardiorespiratory synergy (SpO2 < 92% combined with age-band tachypnea)
    - Gestational pre-eclampsia interaction (pregnant >=20w with BP >=140/90 or >=160/110)
    - Severe maternal/pediatric anemia (Hb < 7.0 g/dL) and pediatric SAM (MUAC < 11.5 cm) + fever
    """
    if np is None:
        raise RuntimeError("numpy is required for generate_synthetic_data()")
    if n_samples < 1:
        raise ValueError(f"n_samples must be >= 1, got {n_samples}")
    rng = np.random.RandomState(seed)

    n_young = int(n_samples * 0.15)
    n_ped = int(n_samples * 0.40)
    n_mat = n_samples - n_young - n_ped

    # Cohort 1: Young infants (<2 months, PSBI vulnerable)
    yi_age = rng.uniform(0.1, 1.9, size=n_young)
    yi_is_pregnant = np.zeros(n_young, dtype=np.float64)
    yi_gest_weeks = np.full(n_young, np.nan, dtype=np.float64)
    yi_muac = np.full(n_young, np.nan, dtype=np.float64)
    yi_rr = rng.normal(46.0, 12.0, size=n_young).clip(28.0, 90.0)
    yi_sbp = np.full(n_young, np.nan, dtype=np.float64)
    yi_dbp = np.full(n_young, np.nan, dtype=np.float64)

    # Cohort 2: Pediatric patients (2 - 59 months)
    ped_age = rng.uniform(2.0, 59.0, size=n_ped)
    ped_is_pregnant = np.zeros(n_ped, dtype=np.float64)
    ped_gest_weeks = np.full(n_ped, np.nan, dtype=np.float64)
    ped_muac = rng.normal(13.8, 2.0, size=n_ped).clip(8.5, 22.0)
    ped_rr = rng.normal(33.0, 11.0, size=n_ped).clip(18.0, 85.0)
    ped_sbp = rng.normal(95.0, 10.0, size=n_ped).clip(70.0, 130.0)
    ped_dbp = rng.normal(60.0, 8.0, size=n_ped).clip(40.0, 85.0)

    # Cohort 3: Maternal patients (180 - 480 months)
    mat_age = rng.uniform(180.0, 480.0, size=n_mat)
    mat_is_pregnant = np.ones(n_mat, dtype=np.float64)
    mat_gest_weeks = rng.uniform(6.0, 41.0, size=n_mat)
    mat_muac = rng.normal(25.0, 3.5, size=n_mat).clip(18.0, 38.0)
    mat_rr = rng.normal(19.0, 4.5, size=n_mat).clip(12.0, 45.0)
    mat_sbp = rng.normal(120.0, 16.0, size=n_mat).clip(85.0, 195.0)
    mat_dbp = rng.normal(78.0, 11.0, size=n_mat).clip(55.0, 125.0)

    # Concatenate demographic features
    age_months = np.concatenate([yi_age, ped_age, mat_age])
    is_pregnant = np.concatenate([yi_is_pregnant, ped_is_pregnant, mat_is_pregnant])
    gestational_weeks = np.concatenate([yi_gest_weeks, ped_gest_weeks, mat_gest_weeks])
    muac_cm = np.concatenate([yi_muac, ped_muac, mat_muac])
    respiratory_rate_bpm = np.concatenate([yi_rr, ped_rr, mat_rr])
    systolic_bp = np.concatenate([yi_sbp, ped_sbp, mat_sbp])
    diastolic_bp = np.concatenate([yi_dbp, ped_dbp, mat_dbp])

    # Shared clinical signs across all cohorts
    fever_days = rng.choice([0, 0, 0, 1, 2, 3, 4, 5, 7, 10], size=n_samples).astype(np.float64)
    temperature_c = rng.normal(37.1, 0.85, size=n_samples).clip(34.6, 41.2)
    spo2_pct = rng.normal(96.8, 3.3, size=n_samples).clip(76.0, 100.0)
    hemoglobin_g_dl = rng.normal(11.4, 2.2, size=n_samples).clip(4.8, 16.5)
    has_danger_sign = rng.binomial(1, 0.14, size=n_samples).astype(np.float64)
    symptom_count = rng.poisson(1.3, size=n_samples).clip(0, 7).astype(np.float64)

    # Age-band fast-breathing thresholds (WHO IMNCI + adult baseline)
    rr_thresh = np.where(
        age_months < 2.0,
        60.0,
        np.where(age_months < 12.0, 50.0, np.where(age_months < 60.0, 40.0, 24.0)),
    )
    rr_excess = np.maximum(respiratory_rate_bpm - rr_thresh, 0.0)

    is_young_infant = age_months < 2.0
    is_child = (age_months >= 2.0) & (age_months < 60.0)
    sbp_safe = np.nan_to_num(systolic_bp, nan=110.0)
    dbp_safe = np.nan_to_num(diastolic_bp, nan=70.0)
    muac_safe = np.nan_to_num(muac_cm, nan=14.0)
    gest_safe = np.nan_to_num(gestational_weeks, nan=0.0)

    # Clinically grounded risk logit with WHO IMNCI & NHM ASHA interaction terms
    logits = np.full(n_samples, -2.1, dtype=np.float64)
    # 1. Severe general danger signs dominate advisory risk
    logits = logits + 3.8 * has_danger_sign
    # 2. Fever duration, hyperpyrexia, and hypothermia
    logits = logits + 0.30 * np.maximum(fever_days - 2.0, 0.0)
    logits = logits + 0.70 * np.maximum(temperature_c - 38.0, 0.0)
    logits = logits + 1.40 * np.maximum(35.5 - temperature_c, 0.0)
    # 3. Young-infant PSBI thermal/respiratory interaction (<2m)
    yi_sepsis_flag = is_young_infant & (
        (temperature_c >= 37.5) | (temperature_c < 35.5) | (respiratory_rate_bpm >= 60.0)
    )
    logits = logits + 2.3 * yi_sepsis_flag.astype(np.float64)
    # 4. Age-band tachypnea + hypoxia cardiorespiratory interaction
    logits = logits + 0.07 * rr_excess
    logits = logits + 0.32 * np.maximum(94.0 - spo2_pct, 0.0)
    cardio_synergy = (spo2_pct < 92.0) & (rr_excess > 0.0)
    logits = logits + 1.4 * cardio_synergy.astype(np.float64)
    # 5. Maternal gestational pre-eclampsia & severe hypertension crisis
    logits = logits + 0.04 * np.maximum(sbp_safe - 135.0, 0.0)
    logits = logits + 0.05 * np.maximum(dbp_safe - 88.0, 0.0)
    preeclampsia_flag = (is_pregnant > 0.5) & (gest_safe >= 20.0) & (
        (sbp_safe >= 140.0) | (dbp_safe >= 90.0)
    )
    severe_htn_flag = (sbp_safe >= 160.0) | (dbp_safe >= 110.0)
    logits = logits + 1.9 * preeclampsia_flag.astype(np.float64)
    logits = logits + 1.5 * severe_htn_flag.astype(np.float64)
    # 6. Severe anemia (<7 g/dL) and moderate anemia (<10.5 g/dL)
    logits = logits + 0.38 * np.maximum(10.5 - hemoglobin_g_dl, 0.0)
    logits = logits + 2.0 * (hemoglobin_g_dl < 7.0).astype(np.float64)
    # 7. Pediatric SAM malnutrition (<11.5 cm) + infection synergy
    sam_deficit = np.where(is_child, np.maximum(11.5 - muac_safe, 0.0), 0.0)
    sam_with_fever = is_child & (muac_safe < 11.5) & ((fever_days >= 2.0) | (temperature_c >= 38.0))
    logits = logits + 0.90 * sam_deficit + 1.2 * sam_with_fever.astype(np.float64)
    # 8. Multi-symptom burden
    logits = logits + 0.22 * symptom_count

    probs = 1.0 / (1.0 + np.exp(-logits))
    labels = (rng.uniform(0.0, 1.0, size=n_samples) < probs).astype(int)

    feature_matrix = np.column_stack([
        age_months,
        fever_days,
        temperature_c,
        respiratory_rate_bpm,
        spo2_pct,
        systolic_bp,
        diastolic_bp,
        hemoglobin_g_dl,
        muac_cm,
        is_pregnant,
        gestational_weeks,
        has_danger_sign,
        symptom_count,
    ])

    return feature_matrix, labels


def compute_binary_calibration_metrics(
    y_true: Any,
    y_prob: Any,
) -> dict[str, float]:
    """Compute pure-NumPy AUROC, Brier score, and accuracy without heavy sklearn bloat."""
    if np is None:
        raise RuntimeError("numpy is required for compute_binary_calibration_metrics()")
    y_true_arr = np.asarray(y_true, dtype=np.float64)
    y_prob_arr = np.clip(np.asarray(y_prob, dtype=np.float64), 0.0, 1.0)
    brier = float(np.mean((y_prob_arr - y_true_arr) ** 2))
    accuracy = float(np.mean((y_prob_arr >= 0.5) == (y_true_arr >= 0.5)))

    pos = y_prob_arr[y_true_arr >= 0.5]
    neg = y_prob_arr[y_true_arr < 0.5]
    if len(pos) == 0 or len(neg) == 0:
        auroc = 0.5
    else:
        # Mann-Whitney U rank statistic for exact AUROC
        combined = np.concatenate([pos, neg])
        order = np.argsort(combined)
        ranks = np.empty_like(order, dtype=np.float64)
        ranks[order] = np.arange(1, len(combined) + 1, dtype=np.float64)
        rank_sum_pos = float(np.sum(ranks[: len(pos)]))
        auroc = (rank_sum_pos - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg))

    return {
        "auroc": round(auroc, 4),
        "brier_score": round(brier, 4),
        "accuracy": round(accuracy, 4),
    }


def train_risk_model(
    output_path: Path,
    n_samples: int = 3000,
    seed: int = 42,
) -> Path:
    """Train LightGBM binary classifier and save compact model text file."""
    if lgb is None or np is None:
        raise RuntimeError("lightgbm and numpy are required for train_risk_model()")
    X, y = generate_synthetic_data(n_samples=n_samples, seed=seed)
    split = max(1, int(len(y) * 0.8))
    X_train, y_train = X[:split], y[:split]
    X_val, y_val = (X[split:], y[split:]) if split < len(y) else (X, y)

    dataset = lgb.Dataset(
        data=X_train,
        label=y_train,
        feature_name=RISK_FEATURE_NAMES,
        free_raw_data=False,
    )

    params: dict[str, object] = {
        "objective": "binary",
        "metric": "binary_logloss",
        "boosting_type": "gbdt",
        "num_leaves": 15,
        "max_depth": 4,
        "learning_rate": 0.08,
        "min_data_in_leaf": 15,
        "monotone_constraints": MONOTONE_CONSTRAINTS,
        "verbosity": -1,
        "seed": seed,
        "deterministic": True,
        "force_col_wise": True,
    }

    booster = lgb.train(params, dataset, num_boost_round=40)
    val_preds = booster.predict(X_val)
    metrics = compute_binary_calibration_metrics(y_val, val_preds)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(output_path))

    file_size_kib = output_path.stat().st_size / 1024.0
    print(
        f"Saved compact LightGBM risk model to {output_path} "
        f"({file_size_kib:.2f} KiB, {booster.num_trees()} trees, "
        f"val AUROC={metrics['auroc']:.4f}, Brier={metrics['brier_score']:.4f})"
    )
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train synthetic LightGBM risk scorer.")
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "models" / "risk_lgbm.txt",
        help="Path for saved LightGBM model text file.",
    )
    parser.add_argument(
        "--samples",
        "-n",
        type=int,
        default=3000,
        help="Number of synthetic clinical records to generate (default: 3000).",
    )
    parser.add_argument(
        "--seed",
        "-s",
        type=int,
        default=42,
        help="Deterministic random seed (default: 42).",
    )
    parser.add_argument(
        "--portable-json",
        action="store_true",
        help="Train zero-dependency portable GBDT+TreeSHAP JSON artifact instead of LightGBM .txt.",
    )
    parser.add_argument(
        "--portable-output",
        type=Path,
        default=DEFAULT_ARTIFACT_PATH,
        help="Destination for portable GBDT JSON artifact.",
    )
    args = parser.parse_args()

    if args.portable_json:
        artifact = train_portable_gbdt_artifact(
            output_path=args.portable_output,
            feature_names=RISK_FEATURE_NAMES,
            monotone_constraints=MONOTONE_CONSTRAINTS,
            n_samples=args.samples,
            seed=args.seed,
        )
        size_kib = args.portable_output.stat().st_size / 1024.0
        metrics = artifact["metrics"]
        print(
            f"Saved portable GBDT+TreeSHAP artifact to {args.portable_output} "
            f"({size_kib:.2f} KiB, {len(artifact['trees'])} trees, "
            f"val AUROC={metrics['auroc']:.4f}, Brier={metrics['brier_score']:.4f})"
        )
        return

    if lgb is None or np is None:
        sys.stderr.write(
            "ERROR: lightgbm and numpy are required unless --portable-json is passed.\n"
        )
        sys.exit(1)

    train_risk_model(output_path=args.output, n_samples=args.samples, seed=args.seed)


if __name__ == "__main__":
    main()
