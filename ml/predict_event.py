
from pathlib import Path
import joblib

from ml.train_model import make_text

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "honeypot_classifier.joblib"
)

_model = None


def predict_event(event):
    """Predict without changing the rule-based assessment."""
    global _model

    if _model is None:
        _model = joblib.load(MODEL_PATH)

    details = event.get("details") or {}
    domain = event.get("domain", "web")
    method = details.get("method", "UNKNOWN")
    path = details.get("path", "/")

    text = make_text(path, method, domain)
    prediction = _model.predict([text])[0]
    probabilities = _model.predict_proba([text])[0]
    classes = list(_model.named_steps["classifier"].classes_)

    confidence = float(probabilities[classes.index(prediction)])

    return {
        "prediction": str(prediction),
        "confidence": round(confidence, 3),
        "mode": "shadow",
    }
