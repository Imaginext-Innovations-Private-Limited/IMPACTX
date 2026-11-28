
from pathlib import Path
import joblib

from train_model import make_text

MODEL_PATH = (
    Path(__file__).resolve().parent
    / "models"
    / "honeypot_classifier.joblib"
)

model = joblib.load(MODEL_PATH)

tests = [
    ("web", "GET", "/health"),
    ("web", "GET", "/products"),
    ("web", "GET", "/.env"),
    ("web", "GET", "/../../etc/passwd"),
    ("web", "GET", "/search?q=union+select"),
    ("web", "GET", "/images/logo.png"),
]

for domain, method, path in tests:
    text = make_text(path, method, domain)
    prediction = model.predict([text])[0]
    probabilities = model.predict_proba([text])[0]
    classes = model.named_steps["classifier"].classes_
    confidence = probabilities[list(classes).index(prediction)]

    print(f"Path: {path}")
    print(f"Prediction: {prediction}")
    print(f"Model probability for prediction: {confidence:.2f}")
    print("-" * 40)
