from pathlib import Path

import joblib
import numpy as np
import pandas as pd

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "ssh_anomaly_detector.joblib"
)

_model_bundle = None


def predict_ssh(features):
    """
    Return an advisory anomaly prediction for an SSH session.
    This prediction does not control the response policy.
    """
    global _model_bundle

    if _model_bundle is None:
        _model_bundle = joblib.load(MODEL_PATH)

    model = _model_bundle["model"]
    feature_names = _model_bundle["features"]

    row = pd.DataFrame(
        [{name: features.get(name, 0) for name in feature_names}],
        columns=feature_names,
    )

    row = row.replace([np.inf, -np.inf], np.nan).fillna(0)
    row = row.clip(lower=0).astype("float32")
    row = np.log1p(row)

    prediction = int(model.predict(row)[0])
    score = float(model.decision_function(row)[0])

    return {
        "model": "IsolationForest",
        "prediction": "review" if prediction == -1 else "normal",
        "anomaly_score": round(score, 5),
        "mode": "shadow",
        "is_confirmed_attack": False,
    }
