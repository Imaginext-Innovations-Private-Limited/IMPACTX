
from pathlib import Path
import joblib
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR
    / "model"
    / "ddos"
    / "V3_ORION"
    / "cyvora_ddos_v3_conflict_filtered_candidate.pkl"
)

THRESHOLD = 0.4950522269566362

FEATURES = [
    "flw_duration",
    "fwd_pkt_total",
    "bwd_pkt_total",
    "fwd_pkt_len_total",
    "bwd_pkt_len_total",
    "flw_iat_mean",
    "flw_iat_std",
    "flw_iat_max",
    "flw_iat_min",
    "fwd_iat_total",
    "fwd_iat_mean",
    "fwd_iat_std",
    "fwd_iat_max",
    "fwd_iat_min",
    "bwd_iat_total",
    "bwd_iat_mean",
    "bwd_iat_std",
    "bwd_iat_max",
    "bwd_iat_min"
]


class DDoSDetector:

    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"DDoS model not found: {MODEL_PATH}"
            )

        self.model = joblib.load(MODEL_PATH)

        if self.model.n_features_in_ != len(FEATURES):
            raise ValueError(
                "Model feature count does not match configuration."
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
                f"Missing DDoS features: {missing}"
            )

        X = traffic_data[FEATURES]

        probabilities = self.model.predict_proba(X)[:, 1]

        results = []

        for probability in probabilities:
            results.append({
                "detector": "DDoS",
                "prediction": (
                    "DDoS Attack"
                    if probability >= THRESHOLD
                    else "Benign"
                ),
                "confidence": round(float(probability), 6),
                "threshold": THRESHOLD
            })

        return results
