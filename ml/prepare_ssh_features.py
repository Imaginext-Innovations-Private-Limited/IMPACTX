from pathlib import Path
import pandas as pd

SOURCE = Path("data/ssh_sessions.csv")
OUTPUT = Path("data/ssh_behavior_features.csv")

df = pd.read_csv(SOURCE)

numeric_cols = [
    "failed_logins",
    "successful_logins",
    "commands",
    "failed_commands",
    "downloads",
    "unique_command_count",
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

first = pd.to_datetime(df["first_seen"], utc=True, errors="coerce")
last = pd.to_datetime(df["last_seen"], utc=True, errors="coerce")

df["duration_seconds"] = (
    (last - first).dt.total_seconds().clip(lower=0).fillna(0)
)

# Behavioral indicators. These are not ground-truth attack labels.
df["has_commands"] = (df["commands"] > 0).astype(int)
df["has_downloads"] = (df["downloads"] > 0).astype(int)
df["has_failed_commands"] = (df["failed_commands"] > 0).astype(int)
df["has_failed_logins"] = (df["failed_logins"] > 0).astype(int)
df["has_successful_login"] = (df["successful_logins"] > 0).astype(int)

# Transparent heuristic score for investigation prioritization only.
score = (
    (df["failed_logins"] >= 3).astype(int) * 20
    + df["has_commands"] * 10
    + df["has_failed_commands"] * 15
    + df["has_downloads"] * 25
    + (df["unique_command_count"] >= 5).astype(int) * 15
)

df["heuristic_score"] = score.clip(upper=100)

# A session can have multiple behavior categories.
def behavior_profile(row):
    categories = []

    if row["failed_logins"] > 0:
        categories.append("authentication_failures")

    if row["successful_logins"] > 0:
        categories.append("successful_login")

    if row["commands"] > 0:
        categories.append("interactive_commands")

    if row["failed_commands"] > 0:
        categories.append("command_failures")

    if row["downloads"] > 0:
        categories.append("file_transfer")

    if not categories:
        categories.append("connection_or_other")

    return "|".join(categories)

df["behavior_profile"] = df.apply(behavior_profile, axis=1)

df.to_csv(OUTPUT, index=False)

print("Feature dataset created:", OUTPUT)
print("Rows:", len(df))
print("Columns:", len(df.columns))
print("\nBehavior profiles:")
print(df["behavior_profile"].value_counts().head(15).to_string())
print("\nHeuristic score distribution:")
print(df["heuristic_score"].describe().to_string())
print("\nSaved successfully.")
