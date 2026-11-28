
from pathlib import Path
import joblib
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR / "model" / "data_exfiltration"
    / "cyvora_exfiltration_model.pkl"
)

FEATURE_PATH = (
    BASE_DIR / "model" / "data_exfiltration"
    / "cyvora_exfiltration_features.pkl"
)


class DataExfiltrationDetector:

    def __init__(self):
        if not MODEL_PATH.exists():
            raise FileNotFoundError(f"Model not found: {MODEL_PATH}")

        if not FEATURE_PATH.exists():
            raise FileNotFoundError(f"Feature file not found: {FEATURE_PATH}")

        self.model = joblib.load(MODEL_PATH)
        self.features = list(joblib.load(FEATURE_PATH))

        if len(self.features) != 75:
            raise ValueError(
                f"Expected 75 features, found {len(self.features)}"
            )

        if self.model.n_features_in_ != len(self.features):
            raise ValueError("Model and feature count do not match.")

        if hasattr(self.model, "feature_names_in_"):
            if list(self.model.feature_names_in_) != self.features:
                raise ValueError("Model feature order does not match.")

    def predict(self, traffic_data):

        if isinstance(traffic_data, dict):
            traffic_data = pd.DataFrame([traffic_data])

        missing = [
            feature for feature in self.features
            if feature not in traffic_data.columns
        ]

        if missing:
            raise ValueError(f"Missing features: {missing}")

        X = traffic_data[self.features]

        predictions = self.model.predict(X)
        probabilities = self.model.predict_proba(X)

        results = []

        for prediction, probability in zip(predictions, probabilities):

            predicted_index = list(self.model.classes_).index(prediction)

            results.append({
                "detector": "Data Exfiltration",
                "prediction": (
                    "Data Exfiltration Detected"
                    if prediction == 1
                    else "Benign"
                ),
                "confidence": round(
                    float(probability[predicted_index]), 6
                )
            })

        return results
