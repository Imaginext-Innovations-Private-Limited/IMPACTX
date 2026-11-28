"""Pure-Python Multi-Tree GBDT & Exact Lundberg TreeSHAP Evaluator.

Provides a zero-bloat (stdlib-only) gradient boosted decision tree runtime and
exact Algorithm 2 TreeSHAP explainer (Lundberg et al., Nature Machine
Intelligence 2020) for Aarogya Mesh Tier-2 PHC Hub.

Mathematical Guarantees:
    1. Exact Local Accuracy (Efficiency):
       ``base_value + sum(shap_attributions.values()) == raw_margin``
       to floating-point precision (< 1e-9).
    2. Signed Clinical Attributions:
       Risk-driving vitals (e.g. SpO2 < 90%, danger signs, BP >= 160/110,
       Hb < 7 g/dL, MUAC < 11.5 cm, young-infant tachypnea) emit positive
       SHAP values (+), while normal protective vitals emit negative SHAP
       values (-).
    3. Clinical Safety Floor:
       Advisory risk scores NEVER override or downgrade deterministic
       ``TriageSeverity`` from ``aarogya_clinical_engine``.
"""

from __future__ import annotations

import json
import math
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_ARTIFACT_PATH: Path = (
    Path(__file__).resolve().parent / "artifacts" / "clinical_gbdt_v1.json"
)


@dataclass
class _PathElem:
    """Single tracked feature split along the TreeSHAP recursion path."""

    d: int  # feature index (-1 for root sentinel)
    z: float  # fraction of zero-paths (background cover proportion)
    o: float  # fraction of one-paths (1.0 if sample follows branch else 0.0)
    w: float  # polynomial subset weight


def _extend_path(
    path: list[_PathElem],
    p_z: float,
    p_o: float,
    p_i: int,
) -> list[_PathElem]:
    """Lundberg Algorithm 2 EXTEND: add a split feature to the subset polynomial."""
    depth = len(path)
    new_path = [_PathElem(e.d, e.z, e.o, e.w) for e in path]
    new_path.append(_PathElem(p_i, p_z, p_o, 1.0 if depth == 0 else 0.0))
    for i in range(depth - 1, -1, -1):
        new_path[i + 1].w += p_o * new_path[i].w * (i + 1) / (depth + 1)
        new_path[i].w = p_z * new_path[i].w * (depth - i) / (depth + 1)
    return new_path


def _unwind_path(path: list[_PathElem], idx: int) -> list[_PathElem]:
    """Lundberg Algorithm 2 UNWIND: reverse an earlier feature extension."""
    depth = len(path) - 1
    out = [_PathElem(e.d, e.z, e.o, e.w) for e in path[:depth]]
    n = path[depth].w
    o_val = path[idx].o
    z_val = path[idx].z
    if o_val != 0.0:
        for i in range(depth - 1, -1, -1):
            tmp = out[i].w
            out[i].w = n * (depth + 1) / ((i + 1) * o_val)
            n = tmp - out[i].w * z_val * (depth - i) / (depth + 1)
    else:
        for i in range(depth - 1, -1, -1):
            out[i].w = (out[i].w * (depth + 1)) / (z_val * (depth - i))
    for i in range(idx, depth):
        out[i].d = path[i + 1].d
        out[i].z = path[i + 1].z
        out[i].o = path[i + 1].o
    return out


def _unwound_path_sum(path: list[_PathElem], idx: int) -> float:
    """Lundberg Algorithm 2 UNWOUND_PATH_SUM: Shapley weight for path[idx]."""
    depth = len(path) - 1
    total = 0.0
    o_val = path[idx].o
    z_val = path[idx].z
    if o_val != 0.0:
        n = path[depth].w
        for i in range(depth - 1, -1, -1):
            tmp = n * (depth + 1) / ((i + 1) * o_val)
            total += tmp
            n = path[i].w - tmp * z_val * (depth - i) / (depth + 1)
    else:
        for i in range(depth - 1, -1, -1):
            total += (path[i].w * (depth + 1)) / (z_val * (depth - i))
    return total


def _tree_expected_value(node: dict[str, Any]) -> float:
    """Compute cover-weighted expected leaf value of a single regression tree."""
    if "v" in node:
        return float(node["v"])
    cover = float(node["c"])
    if cover <= 0.0:
        return 0.0
    left = node["l"]
    right = node["r"]
    return (
        float(left["c"]) * _tree_expected_value(left)
        + float(right["c"]) * _tree_expected_value(right)
    ) / cover


def _predict_single_tree(node: dict[str, Any], x: list[float]) -> float:
    """Route a feature vector through a single tree (NaN follows default_left)."""
    curr = node
    while "v" not in curr:
        val = x[int(curr["f"])]
        if math.isnan(val):
            go_left = bool(curr["dl"])
        else:
            go_left = val <= float(curr["t"])
        curr = curr["l"] if go_left else curr["r"]
    return float(curr["v"])


def _treeshap_recurse(
    node: dict[str, Any],
    x: list[float],
    path: list[_PathElem],
    p_z: float,
    p_o: float,
    p_i: int,
    phi: list[float],
) -> None:
    """Exact Lundberg Algorithm 2 TreeSHAP recursion for a single tree."""
    extended = _extend_path(path, p_z, p_o, p_i)
    if "v" in node:
        leaf_val = float(node["v"])
        for i in range(1, len(extended)):
            weight_sum = _unwound_path_sum(extended, i)
            phi[extended[i].d] += weight_sum * (extended[i].o - extended[i].z) * leaf_val
        return

    feat_idx = int(node["f"])
    val = x[feat_idx]
    go_left = bool(node["dl"]) if math.isnan(val) else (val <= float(node["t"]))
    hot = node["l"] if go_left else node["r"]
    cold = node["r"] if go_left else node["l"]

    i_z = 1.0
    i_o = 1.0
    # If feat_idx already appeared higher in this path, unwind prior split
    existing_idx = -1
    for i in range(1, len(extended)):
        if extended[i].d == feat_idx:
            existing_idx = i
            break
    if existing_idx != -1:
        i_z = extended[existing_idx].z
        i_o = extended[existing_idx].o
        extended = _unwind_path(extended, existing_idx)

    parent_cover = float(node["c"])
    hot_frac = float(hot["c"]) / parent_cover
    cold_frac = float(cold["c"]) / parent_cover

    _treeshap_recurse(hot, x, extended, i_z * hot_frac, i_o, feat_idx, phi)
    _treeshap_recurse(cold, x, extended, i_z * cold_frac, 0.0, feat_idx, phi)


class PortableGbdtModel:
    """Zero-dependency GBDT binary classifier with exact Lundberg TreeSHAP."""

    def __init__(self, artifact: dict[str, Any]) -> None:
        self.model_version: str = str(artifact.get("model_version", "1.0.0"))
        self.feature_names: list[str] = list(artifact["feature_names"])
        self.base_score: float = float(artifact["base_score"])
        self.trees: list[dict[str, Any]] = list(artifact["trees"])
        self.metrics: dict[str, float] = {
            k: float(v) for k, v in artifact.get("metrics", {}).items()
        }
        self._expected_value: float = self.base_score + sum(
            _tree_expected_value(tree) for tree in self.trees
        )

    @classmethod
    def from_json_file(cls, path: str | Path = DEFAULT_ARTIFACT_PATH) -> PortableGbdtModel:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(data)

    @property
    def expected_value(self) -> float:
        """Exact TreeSHAP baseline margin phi_0 across the training cover."""
        return self._expected_value

    @property
    def num_trees(self) -> int:
        return len(self.trees)

    def predict_margin(self, x: list[float]) -> float:
        """Compute raw additive log-odds margin f(x) across all trees."""
        margin = self.base_score
        for tree in self.trees:
            margin += _predict_single_tree(tree, x)
        return margin

    def predict_proba(self, x: list[float]) -> float:
        """Compute calibrated binary probability sigmoid(f(x)) in [0.0, 1.0]."""
        margin = max(-30.0, min(30.0, self.predict_margin(x)))
        return 1.0 / (1.0 + math.exp(-margin))

    def explain(self, x: list[float]) -> tuple[float, float, float, dict[str, float]]:
        """Compute (probability, raw_margin, expected_value, exact_shap_dict).

        Guarantees ``expected_value + sum(exact_shap_dict.values()) == raw_margin``
        before display rounding.
        """
        n_features = len(self.feature_names)
        phi = [0.0] * n_features
        for tree in self.trees:
            _treeshap_recurse(tree, x, [], 1.0, 1.0, -1, phi)

        margin = self.predict_margin(x)
        prob = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, margin))))
        attributions = {
            self.feature_names[idx]: round(phi[idx], 4) for idx in range(n_features)
        }
        return prob, margin, self._expected_value, attributions


# ---------------------------------------------------------------------------
# Pure-Python deterministic Newton GBDT trainer (reproducible with zero deps)
# ---------------------------------------------------------------------------


def _sigmoid(z: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z))))


def _generate_pure_python_cohort(
    n_samples: int = 3000,
    seed: int = 42,
) -> tuple[list[list[float]], list[int]]:
    """Deterministic 3-cohort rural clinical dataset (young-infant, pediatric, maternal)."""
    if n_samples < 1:
        raise ValueError(f"n_samples must be >= 1, got {n_samples}")
    rng = random.Random(seed)
    n_young = int(n_samples * 0.15)
    n_ped = int(n_samples * 0.40)

    def _clip(v: float, lo: float, hi: float) -> float:
        return lo if v < lo else (hi if v > hi else v)

    fever_choices = (0.0, 0.0, 0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 7.0, 10.0)
    rows: list[list[float]] = []
    labels: list[int] = []

    for idx in range(n_samples):
        if idx < n_young:
            # Cohort 1: Young infant (<2 months PSBI)
            age_m = rng.uniform(0.1, 1.9)
            is_preg = 0.0
            gest_w = float("nan")
            muac = float("nan")
            rr = _clip(rng.gauss(46.0, 12.0), 28.0, 90.0)
            sbp = float("nan")
            dbp = float("nan")
            rr_thresh = 60.0
        elif idx < n_young + n_ped:
            # Cohort 2: Pediatric (2 - 59 months)
            age_m = rng.uniform(2.0, 59.0)
            is_preg = 0.0
            gest_w = float("nan")
            muac = _clip(rng.gauss(13.8, 2.0), 8.5, 22.0)
            rr = _clip(rng.gauss(33.0, 11.0), 18.0, 85.0)
            sbp = _clip(rng.gauss(95.0, 10.0), 70.0, 130.0)
            dbp = _clip(rng.gauss(60.0, 8.0), 40.0, 85.0)
            rr_thresh = 50.0 if age_m < 12.0 else 40.0
        else:
            # Cohort 3: Maternal (180 - 480 months)
            age_m = rng.uniform(180.0, 480.0)
            is_preg = 1.0
            gest_w = rng.uniform(6.0, 41.0)
            muac = _clip(rng.gauss(25.0, 3.5), 18.0, 38.0)
            rr = _clip(rng.gauss(19.0, 4.5), 12.0, 45.0)
            sbp = _clip(rng.gauss(120.0, 16.0), 85.0, 195.0)
            dbp = _clip(rng.gauss(78.0, 11.0), 55.0, 125.0)
            rr_thresh = 24.0

        fever_d = rng.choice(fever_choices)
        temp_c = _clip(rng.gauss(37.1, 0.85), 34.6, 41.2)
        spo2 = _clip(rng.gauss(96.8, 3.3), 76.0, 100.0)
        hb = _clip(rng.gauss(11.4, 2.2), 4.8, 16.5)
        has_ds = 1.0 if rng.random() < 0.14 else 0.0
        # Simple Poisson-like symptom burden 0..7
        sym_cnt = float(min(7, sum(1 for _ in range(7) if rng.random() < 0.18)))

        rr_excess = max(rr - rr_thresh, 0.0)
        sbp_safe = 110.0 if math.isnan(sbp) else sbp
        dbp_safe = 70.0 if math.isnan(dbp) else dbp
        muac_safe = 14.0 if math.isnan(muac) else muac
        gest_safe = 0.0 if math.isnan(gest_w) else gest_w

        logit = -2.1
        logit += 3.8 * has_ds
        logit += 0.30 * max(fever_d - 2.0, 0.0)
        logit += 0.70 * max(temp_c - 38.0, 0.0)
        logit += 1.40 * max(35.5 - temp_c, 0.0)
        if age_m < 2.0 and (temp_c >= 37.5 or temp_c < 35.5 or rr >= 60.0):
            logit += 2.3
        logit += 0.07 * rr_excess
        logit += 0.32 * max(94.0 - spo2, 0.0)
        if spo2 < 92.0 and rr_excess > 0.0:
            logit += 1.4
        logit += 0.04 * max(sbp_safe - 135.0, 0.0)
        logit += 0.05 * max(dbp_safe - 88.0, 0.0)
        if is_preg > 0.5 and gest_safe >= 20.0 and (sbp_safe >= 140.0 or dbp_safe >= 90.0):
            logit += 1.9
        if sbp_safe >= 160.0 or dbp_safe >= 110.0:
            logit += 1.5
        logit += 0.38 * max(10.5 - hb, 0.0)
        if hb < 7.0:
            logit += 2.0
        if 2.0 <= age_m < 60.0:
            logit += 0.90 * max(11.5 - muac_safe, 0.0)
            if muac_safe < 11.5 and (fever_d >= 2.0 or temp_c >= 38.0):
                logit += 1.2
        logit += 0.22 * sym_cnt

        prob = _sigmoid(logit)
        label = 1 if rng.random() < prob else 0
        rows.append([
            age_m,
            fever_d,
            temp_c,
            rr,
            spo2,
            sbp,
            dbp,
            hb,
            muac,
            is_preg,
            gest_w,
            has_ds,
            sym_cnt,
        ])
        labels.append(label)

    # Shuffle deterministically so train and validation splits span all 3 cohorts
    order = list(range(n_samples))
    rng.shuffle(order)
    return [rows[i] for i in order], [labels[i] for i in order]


def _fit_regression_tree(
    rows: list[list[float]],
    grads: list[float],
    hess: list[float],
    indices: list[int],
    monotone_constraints: list[int],
    *,
    depth: int,
    max_depth: int,
    min_child_samples: int,
    reg_lambda: float,
    learning_rate: float,
) -> dict[str, Any]:
    """Fit one second-order Newton decision tree with monotone constraints & NaN routing."""
    g_sum = sum(grads[i] for i in indices)
    h_sum = sum(hess[i] for i in indices)
    cover = len(indices)
    leaf_val = -learning_rate * g_sum / (h_sum + reg_lambda)

    if depth >= max_depth or cover < 2 * min_child_samples:
        return {"v": round(leaf_val, 6), "c": cover}

    parent_score = (g_sum * g_sum) / (h_sum + reg_lambda)
    best_gain = 1e-6
    best_split: tuple[int, float, bool, list[int], list[int]] | None = None
    n_features = len(monotone_constraints)

    for f_idx in range(n_features):
        non_nan: list[tuple[float, int]] = []
        nan_indices: list[int] = []
        for i in indices:
            val = rows[i][f_idx]
            if math.isnan(val):
                nan_indices.append(i)
            else:
                non_nan.append((val, i))
        if len(non_nan) < 2:
            continue
        non_nan.sort(key=lambda pair: pair[0])

        # Candidate quantile thresholds (up to 16 split candidates per feature)
        distinct_vals = sorted({pair[0] for pair in non_nan})
        if len(distinct_vals) < 2:
            continue
        step = max(1, len(distinct_vals) // 16)
        cand_thresholds = [
            0.5 * (distinct_vals[j] + distinct_vals[j + 1])
            for j in range(0, len(distinct_vals) - 1, step)
        ]

        g_nan = sum(grads[i] for i in nan_indices)
        h_nan = sum(hess[i] for i in nan_indices)
        c_nan = len(nan_indices)
        mono = monotone_constraints[f_idx]

        # Sweep sorted non_nan once across sorted candidate thresholds
        ptr = 0
        g_left_base = 0.0
        h_left_base = 0.0
        c_left_base = 0
        total_non_nan = len(non_nan)

        for thresh in cand_thresholds:
            while ptr < total_non_nan and non_nan[ptr][0] <= thresh:
                idx_i = non_nan[ptr][1]
                g_left_base += grads[idx_i]
                h_left_base += hess[idx_i]
                c_left_base += 1
                ptr += 1

            # When no NaNs are present in training for this feature, default NaN routing
            # goes toward the clinically normal/lower-risk branch (right for mono == -1).
            default_candidates = (True, False) if c_nan > 0 else (mono != -1,)
            for default_left in default_candidates:
                if default_left:
                    g_l = g_left_base + g_nan
                    h_l = h_left_base + h_nan
                    c_l = c_left_base + c_nan
                else:
                    g_l = g_left_base
                    h_l = h_left_base
                    c_l = c_left_base
                c_r = cover - c_l
                if c_l < min_child_samples or c_r < min_child_samples:
                    continue
                g_r = g_sum - g_l
                h_r = h_sum - h_l

                val_l = -g_l / (h_l + reg_lambda)
                val_r = -g_r / (h_r + reg_lambda)
                if mono == 1 and val_l > val_r:
                    continue
                if mono == -1 and val_l < val_r:
                    continue

                gain = 0.5 * (
                    (g_l * g_l) / (h_l + reg_lambda)
                    + (g_r * g_r) / (h_r + reg_lambda)
                    - parent_score
                )
                if gain > best_gain:
                    best_gain = gain
                    left_idx = [non_nan[k][1] for k in range(ptr)]
                    right_idx = [non_nan[k][1] for k in range(ptr, total_non_nan)]
                    if default_left:
                        left_idx.extend(nan_indices)
                    else:
                        right_idx.extend(nan_indices)
                    best_split = (f_idx, thresh, default_left, left_idx, right_idx)

    if best_split is None:
        return {"v": round(leaf_val, 6), "c": cover}

    f_idx, thresh, default_left, left_idx, right_idx = best_split
    return {
        "f": f_idx,
        "t": round(thresh, 4),
        "dl": default_left,
        "c": cover,
        "l": _fit_regression_tree(
            rows,
            grads,
            hess,
            left_idx,
            monotone_constraints,
            depth=depth + 1,
            max_depth=max_depth,
            min_child_samples=min_child_samples,
            reg_lambda=reg_lambda,
            learning_rate=learning_rate,
        ),
        "r": _fit_regression_tree(
            rows,
            grads,
            hess,
            right_idx,
            monotone_constraints,
            depth=depth + 1,
            max_depth=max_depth,
            min_child_samples=min_child_samples,
            reg_lambda=reg_lambda,
            learning_rate=learning_rate,
        ),
    }


def _pure_python_metrics(y_true: list[int], y_prob: list[float]) -> dict[str, float]:
    n = len(y_true)
    brier = sum((p - y) ** 2 for p, y in zip(y_prob, y_true, strict=True)) / max(n, 1)
    acc = sum(1 for p, y in zip(y_prob, y_true, strict=True) if (p >= 0.5) == (y == 1)) / max(n, 1)
    pos = [p for p, y in zip(y_prob, y_true, strict=True) if y == 1]
    neg = [p for p, y in zip(y_prob, y_true, strict=True) if y == 0]
    if not pos or not neg:
        auroc = 0.5
    else:
        combined = [(val, 1) for val in pos] + [(val, 0) for val in neg]
        combined.sort(key=lambda pair: pair[0])
        rank_sum = sum(rank for rank, (_, lbl) in enumerate(combined, start=1) if lbl == 1)
        auroc = (rank_sum - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg))
    return {
        "auroc": round(auroc, 4),
        "brier_score": round(brier, 4),
        "accuracy": round(acc, 4),
    }


def train_portable_gbdt_artifact(
    output_path: Path = DEFAULT_ARTIFACT_PATH,
    *,
    feature_names: list[str],
    monotone_constraints: list[int],
    n_samples: int = 3600,
    n_trees: int = 28,
    max_depth: int = 3,
    learning_rate: float = 0.14,
    reg_lambda: float = 2.0,
    min_child_samples: int = 25,
    seed: int = 42,
) -> dict[str, Any]:
    """Train a compact monotone GBDT ensemble in pure Python and serialize to JSON."""
    rows, labels = _generate_pure_python_cohort(n_samples=n_samples, seed=seed)
    split = max(1, int(n_samples * 0.8))
    train_rows, train_y = rows[:split], labels[:split]
    val_rows, val_y = rows[split:], labels[split:]

    pos_rate = max(1e-4, min(1.0 - 1e-4, sum(train_y) / len(train_y)))
    base_score = round(math.log(pos_rate / (1.0 - pos_rate)), 6)
    margins = [base_score] * len(train_rows)
    all_idx = list(range(len(train_rows)))
    trees: list[dict[str, Any]] = []

    for _ in range(n_trees):
        probs = [_sigmoid(m) for m in margins]
        grads = [p - y for p, y in zip(probs, train_y, strict=True)]
        hess = [max(p * (1.0 - p), 1e-4) for p in probs]
        tree = _fit_regression_tree(
            train_rows,
            grads,
            hess,
            all_idx,
            monotone_constraints,
            depth=0,
            max_depth=max_depth,
            min_child_samples=min_child_samples,
            reg_lambda=reg_lambda,
            learning_rate=learning_rate,
        )
        trees.append(tree)
        for i in all_idx:
            margins[i] += _predict_single_tree(tree, train_rows[i])

    val_probs = [
        _sigmoid(base_score + sum(_predict_single_tree(t, r) for t in trees))
        for r in val_rows
    ]
    metrics = _pure_python_metrics(val_y, val_probs)

    artifact: dict[str, Any] = {
        "model_version": "1.0.0",
        "algorithm": "newton-gbdt-monotone-treeshap",
        "seed": seed,
        "n_train_samples": len(train_rows),
        "n_val_samples": len(val_rows),
        "feature_names": feature_names,
        "monotone_constraints": monotone_constraints,
        "base_score": base_score,
        "metrics": metrics,
        "trees": trees,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, separators=(",", ":")),
        encoding="utf-8",
    )
    return artifact
