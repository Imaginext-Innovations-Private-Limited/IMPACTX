
from pathlib import Path

import joblib
import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR
    / "model"
    / "dns_tunnelling"
    / "cyvora_dns_lightgbm_candidate_v2.pkl"
)

FEATURES = [
    "hits",
    "domain_data_portion",
    "fqdn_count",
    "fqdn_hit_ratio",
    "unique_dns_types",
    "dns_type_A_count",
    "dns_type_A_ratio",
    "dns_type_AAAA_count",
    "dns_type_AAAA_ratio",
    "dns_type_TXT_count",
    "dns_type_TXT_ratio",
    "dns_type_SOA_count",
    "dns_type_SOA_ratio",
    "dns_type_NS_count",
    "dns_type_NS_ratio",
    "dns_type_MX_count",
    "dns_type_MX_ratio",
    "dns_type_DS_count",
    "dns_type_DS_ratio",
    "dns_type_CNAME_count",
    "dns_type_CNAME_ratio",
    "dns_type_HTTPS_count",
    "dns_type_HTTPS_ratio",
    "dns_type_OTHER_count",
    "dns_type_OTHER_ratio",
    "top1_records_count",
    "top1_records_ratio",
    "other_comp_last_24_fqdn_count",
    "other_comp_last_24_fqdn_hit_ratio",
    "other_comp_last_24_hits",
    "other_comp_last_24_unique_company",
    "other_comp_window_fqdn_count",
    "other_comp_window_fqdn_hit_ratio",
    "other_comp_window_hits",
    "other_comp_window_unique_company",
    "file_chunk_detection_positive",
    "file_chunk_detection_negative"
]


class DNSTunnellingDetector:

    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"DNS model not found: {MODEL_PATH}"
            )

        bundle = joblib.load(MODEL_PATH)

        self.model = bundle["model"]
        self.threshold = float(bundle["threshold"])

        if len(FEATURES) != 37:
            raise ValueError("DNS feature list must contain 37 features.")

        if self.model.num_feature() != len(FEATURES):
            raise ValueError("DNS model and feature count mismatch.")

        if bundle.get("feature_count", 37) != len(FEATURES):
            raise ValueError("Saved DNS feature count mismatch.")

    def predict(self, traffic_data):

        if isinstance(traffic_data, dict):
            traffic_data = pd.DataFrame([traffic_data])

        missing = [
            feature for feature in FEATURES
            if feature not in traffic_data.columns
        ]

        if missing:
            raise ValueError(f"Missing DNS features: {missing}")

        X = traffic_data[FEATURES].copy()

        for feature in FEATURES:
            X[feature] = pd.to_numeric(
                X[feature], errors="coerce"
            )

        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(0).astype("float32")

        probabilities = self.model.predict(X)

        results = []

        for probability in probabilities:
            results.append({
                "detector": "DNS Tunnelling",
                "prediction": (
                    "DNS Tunnelling Detected"
                    if probability >= self.threshold
                    else "Benign"
                ),
                "confidence": round(float(probability), 6),
                "threshold": self.threshold
            })

        return results
