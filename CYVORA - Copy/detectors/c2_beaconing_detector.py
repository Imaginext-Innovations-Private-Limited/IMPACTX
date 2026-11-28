
from pathlib import Path
import joblib
import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR
    / "model"
    / "c2_beaconing"
    / "candidate_B"
    / "cyvora_rf_model.pkl"
)

FEATURES = [
    "duration",
    "orig_bytes",
    "resp_bytes",
    "orig_pkts",
    "resp_pkts",
    "orig_ip_bytes",
    "resp_ip_bytes",
    "missed_bytes"
]


class C2BeaconingDetector:

    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"C2 model not found: {MODEL_PATH}"
            )

        package = joblib.load(MODEL_PATH)

        self.model = package["model"]
        self.threshold = float(package["threshold"])
        self.log_transform = package["log_transform"]

        if self.model.n_features_in_ != len(FEATURES):
            raise ValueError(
                "C2 model feature count does not match."
            )

        if self.threshold != 0.57:
            raise ValueError(
                f"Unexpected C2 threshold: {self.threshold}"
            )

    def predict(self, traffic_data):

        if isinstance(traffic_data, dict):
            traffic_data = pd.DataFrame([traffic_data])

        missing = [
            feature for feature in FEATURES
            if feature not in traffic_data.columns
        ]

        if missing:
            raise ValueError(
                f"Missing C2 features: {missing}"
            )

        X = traffic_data[FEATURES].copy()

        X = X.clip(lower=0)

        if self.log_transform == "numpy.log1p":
            X = np.log1p(X)

        probabilities = self.model.predict_proba(X)[:, 1]

        results = []

        for probability in probabilities:
            results.append({
                "detector": "C2 Beaconing",
                "prediction": (
                    "C2 Beaconing Detected"
                    if probability >= self.threshold
                    else "Benign"
                ),
                "confidence": round(float(probability), 6),
                "threshold": self.threshold
            })

        return results
