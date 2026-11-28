from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "ssh_behavior_features.csv"
MODEL_DIR = ROOT / "ml" / "models"
MODEL_PATH = MODEL_DIR / "ssh_anomaly_detector.joblib"
REPORT_PATH = ROOT / "data" / "ssh_anomaly_review.csv"

FEATURES = [
    "failed_logins",
    "successful_logins",
    "commands",
    "failed_commands",
    "downloads",
    "unique_command_count",
    "duration_seconds",
]

print("Loading SSH session features...")
df = pd.read_csv(DATA, usecols=FEATURES)
df = df.replace([np.inf, -np.inf], np.nan).fillna(0)
df = df.clip(lower=0)

# Log transform reduces the influence of extreme count values.
X = np.log1p(df[FEATURES].astype("float32"))

print("Sessions:", len(X))
print("Features:", FEATURES)

model = IsolationForest(
    n_estimators=100,
    contamination="auto",
    random_state=42,
    n_jobs=-1,
)
model.fit(X)

# Lower decision_function scores indicate more unusual sessions.
scores = model.decision_function(X)
predictions = model.predict(X)

MODEL_DIR.mkdir(parents=True, exist_ok=True)
joblib.dump(
    {"model": model, "features": FEATURES},
    MODEL_PATH,
)

review = df.copy()
review["anomaly_score"] = scores
review["anomaly_flag"] = np.where(predictions == -1, "review", "normal")
review.nlargest(200, "anomaly_score", keep="all").to_csv(
    ROOT / "data" / "ssh_high_score_review.csv", index=False
)

# Save the most anomalous sessions for manual investigation.
review.nsmallest(200, "anomaly_score").to_csv(REPORT_PATH, index=False)

print("\nModel saved:", MODEL_PATH)
print("Manual review file:", REPORT_PATH)
print("Flagged sessions:", int((predictions == -1).sum()))
print("Flag rate:", round(float((predictions == -1).mean()) * 100, 2), "%")
print("\nLowest anomaly scores (most unusual):")
print(
    review.nsmallest(10, "anomaly_score")[
        FEATURES + ["anomaly_score", "anomaly_flag"]
    ].to_string(index=False)
)
print("\nNote: anomaly flags are not verified attack labels.")
