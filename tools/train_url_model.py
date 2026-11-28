"""Train offline URL-only phishing classifier (UCI PhiUSIIL) and build threat DB (PhishTank).

Strictly uses URL-surface lexical features (no HTML/DOM/network features).
Uses domain-grouped train/test splitting and URL deduplication to prevent leakage.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import sqlite3
import zipfile
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import StandardScaler

from scamshield.url_classifier import (
    DATA_DIR,
    MODEL_PATH,
    THREAT_DB_PATH,
    extract_url_features,
    normalize_url,
    registered_domain,
)

EXTERNAL_DIR = Path(__file__).resolve().parent.parent / "data" / "external"
PHIUSIIL_ZIP = EXTERNAL_DIR / "phiusiil.zip"
PHISHTANK_GZ = EXTERNAL_DIR / "phishtank.csv.gz"
REPORT_PATH = DATA_DIR / "url_eval_report.json"


def build_threat_db(phishtank_gz: Path = PHISHTANK_GZ, db_path: Path = THREAT_DB_PATH) -> dict[str, int]:
    """Build local SQLite SHA-256 verified-threat lookup DB from PhishTank CSV."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE threats (url_hash TEXT PRIMARY KEY, source TEXT NOT NULL)")

    seen: set[str] = set()
    total_rows = 0
    batch: list[tuple[str, str]] = []
    with gzip.open(phishtank_gz, "rt", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            if row.get("verified") != "yes" or row.get("online") != "yes":
                continue
            norm = normalize_url(row.get("url", ""))
            if not norm:
                continue
            h = hashlib.sha256(norm.encode("utf-8")).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            batch.append((h, "PhishTank"))

    conn.executemany("INSERT INTO threats (url_hash, source) VALUES (?, ?)", batch)
    conn.commit()
    conn.execute("VACUUM")
    conn.close()
    return {"total_rows": total_rows, "unique_hashes": len(seen)}


def load_phiusiil_urls(phiusiil_zip: Path = PHIUSIIL_ZIP) -> tuple[list[str], list[int], list[str], dict[str, int]]:
    """Load deduplicated URLs from UCI PhiUSIIL.

    In PhiUSIIL, label='0' is Phishing (y=1) and label='1' is Legitimate (y=0).
    """
    seen: dict[str, int] = {}
    conflicts = 0
    total = 0
    with zipfile.ZipFile(phiusiil_zip) as zf:
        csv_name = [n for n in zf.namelist() if n.endswith(".csv")][0]
        with zf.open(csv_name) as f:
            reader = csv.DictReader(io.TextIOWrapper(f, "utf-8", errors="replace"))
            for row in reader:
                total += 1
                norm = normalize_url(row.get("URL", ""))
                if not norm:
                    continue
                # Invert PhiUSIIL label: 0 -> 1 (phishing), 1 -> 0 (legit)
                y = 1 if row.get("label") == "0" else 0
                if norm in seen:
                    if seen[norm] != y:
                        conflicts += 1
                        seen[norm] = -1
                    continue
                seen[norm] = y

    urls: list[str] = []
    labels: list[int] = []
    groups: list[str] = []
    for norm, y in seen.items():
        if y == -1:
            continue
        urls.append(norm)
        labels.append(y)
        host = norm.split("://", 1)[-1].split("/", 1)[0].split(":")[0]
        groups.append(registered_domain(host) or host)

    stats = {
        "raw_rows": total,
        "dedup_urls": len(urls),
        "conflicts_removed": conflicts,
        "phishing_count": sum(labels),
        "legit_count": len(labels) - sum(labels),
        "unique_domain_groups": len(set(groups)),
    }
    return urls, labels, groups, stats


def train_and_evaluate() -> None:
    print("Building PhishTank SQLite threat DB...")
    db_stats = build_threat_db()
    print("Threat DB stats:", db_stats, f"size={THREAT_DB_PATH.stat().st_size / 1024:.1f} KB")

    print("Loading & deduplicating UCI PhiUSIIL URLs...")
    urls, labels, groups, data_stats = load_phiusiil_urls()
    print("PhiUSIIL stats:", data_stats)

    surfaces: list[str] = []
    num_feats: list[list[float]] = []
    for u in urls:
        s, f, _ = extract_url_features(u)
        surfaces.append(s)
        num_feats.append(f)

    y = np.array(labels, dtype=np.int32)
    X_num = np.array(num_feats, dtype=np.float32)

    splitter = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
    train_idx, test_idx = next(splitter.split(surfaces, y, groups))

    train_surfaces = [surfaces[i] for i in train_idx]
    test_surfaces = [surfaces[i] for i in test_idx]
    y_train, y_test = y[train_idx], y[test_idx]

    vec = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        min_df=5,
        max_features=12000,
        lowercase=True,
        dtype=np.float32,
    )
    X_train_ng = vec.fit_transform(train_surfaces)
    X_test_ng = vec.transform(test_surfaces)

    scaler = StandardScaler()
    X_train_num = scaler.fit_transform(X_num[train_idx])
    X_test_num = scaler.transform(X_num[test_idx])

    X_train = hstack([X_train_ng, csr_matrix(X_train_num)])
    X_test = hstack([X_test_ng, csr_matrix(X_test_num)])

    clf = LogisticRegression(max_iter=500, C=2.0, class_weight="balanced", random_state=42)
    clf.fit(X_train, y_train)

    probs = clf.predict_proba(X_test)[:, 1]
    preds_05 = (probs >= 0.50).astype(int)
    preds_65 = (probs >= 0.65).astype(int)
    preds_85 = (probs >= 0.85).astype(int)

    metrics = {
        "roc_auc": round(float(roc_auc_score(y_test, probs)), 4),
        "threshold_0.50": {
            "accuracy": round(float(accuracy_score(y_test, preds_05)), 4),
            "precision": round(float(precision_score(y_test, preds_05)), 4),
            "recall": round(float(recall_score(y_test, preds_05)), 4),
            "f1": round(float(f1_score(y_test, preds_05)), 4),
        },
        "threshold_0.65": {
            "precision": round(float(precision_score(y_test, preds_65)), 4),
            "recall": round(float(recall_score(y_test, preds_65)), 4),
            "f1": round(float(f1_score(y_test, preds_65)), 4),
        },
        "threshold_0.85": {
            "precision": round(float(precision_score(y_test, preds_85)), 4),
            "recall": round(float(recall_score(y_test, preds_85)), 4),
            "f1": round(float(f1_score(y_test, preds_85)), 4),
        },
    }
    print("Domain-grouped held-out test metrics:")
    print(json.dumps(metrics, indent=2))
    print(classification_report(y_test, preds_05, target_names=["legitimate", "phishing"]))

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"vectorizer": vec, "scaler": scaler, "classifier": clf}, MODEL_PATH, compress=3)
    print(f"Saved model to {MODEL_PATH} ({MODEL_PATH.stat().st_size / 1024:.1f} KB)")

    report = {
        "dataset": "UCI PhiUSIIL (URL-only lexical features, domain-grouped 80/20 split)",
        "data_stats": data_stats,
        "train_rows": int(len(train_idx)),
        "test_rows": int(len(test_idx)),
        "threat_db": db_stats,
        "metrics": metrics,
    }
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Saved report to {REPORT_PATH}")


if __name__ == "__main__":
    train_and_evaluate()
