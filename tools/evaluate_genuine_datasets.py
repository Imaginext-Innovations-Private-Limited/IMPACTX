"""Evaluate offline engine on genuine UCI SMS Spam Collection and held-out UCI PhiUSIIL URLs."""
from __future__ import annotations

import hashlib
import io
import json
import random
import time
import zipfile
from collections import Counter
from pathlib import Path

from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit

from scamshield.engine import analyze
from scamshield.url_classifier import classify_url, lookup_threat, normalize_url
from tools.train_url_model import load_phiusiil_urls

EXTERNAL_DIR = Path(__file__).resolve().parent.parent / "data" / "external"
SMS_ZIP = EXTERNAL_DIR / "sms_spam.zip"
OUT_PATH = Path(__file__).resolve().parent.parent / "benchmark" / "genuine_eval_report.json"


def eval_uci_sms() -> dict[str, object]:
    ham_levels: Counter[str] = Counter()
    spam_levels: Counter[str] = Counter()
    t0 = time.perf_counter()
    count = 0
    with zipfile.ZipFile(SMS_ZIP) as zf:
        lines = io.TextIOWrapper(zf.open("SMSSpamCollection"), "utf-8", errors="replace").readlines()
    for line in lines:
        if "\t" not in line:
            continue
        lbl, txt = line.split("\t", 1)
        txt = txt.strip()[:6000]
        if not txt:
            continue
        count += 1
        lvl = analyze(txt, channel="sms", language="en")["level"]
        if lbl == "ham":
            ham_levels[lvl] += 1
        else:
            spam_levels[lvl] += 1
    elapsed = time.perf_counter() - t0
    ham_total = sum(ham_levels.values())
    spam_total = sum(spam_levels.values())
    ham_caution_high = ham_levels["caution"] + ham_levels["high"]
    return {
        "total_messages": count,
        "ham_total": ham_total,
        "spam_total": spam_total,
        "ham_levels": dict(ham_levels),
        "spam_levels": dict(spam_levels),
        "ham_caution_high_fp_rate": round(ham_caution_high / max(ham_total, 1), 4),
        "avg_latency_ms": round((elapsed / max(count, 1)) * 1000, 2),
        "note": "UCI SMS spam includes promotional/marketing messages, not exclusively financial fraud.",
    }


def eval_heldout_phiusiil(sample_size: int = 2000) -> dict[str, object]:
    urls, labels, groups, _ = load_phiusiil_urls()
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42)
    train_idx, test_idx = next(splitter.split(urls, labels, groups))

    train_domains = {groups[i] for i in train_idx}
    test_domains = {groups[i] for i in test_idx}
    domain_overlap = len(train_domains & test_domains)

    rng = random.Random(42)
    chosen = rng.sample(list(test_idx), min(sample_size, len(test_idx)))

    y_true: list[int] = []
    y_url_ml: list[int] = []
    y_engine: list[int] = []
    threat_db_hits = 0
    unseen_y_true: list[int] = []
    unseen_y_engine: list[int] = []

    t0 = time.perf_counter()
    for idx in chosen:
        u = urls[idx]
        lbl = int(labels[idx])
        y_true.append(lbl)

        uinfo = classify_url(u)
        db_hit = bool(uinfo["threat_db_match"])
        if db_hit:
            threat_db_hits += 1
        y_url_ml.append(1 if (uinfo["ml_flag"] in {"review", "high"} or db_hit) else 0)

        eng = analyze(u, channel="sms", language="en")
        eng_pred = 1 if eng["level"] in {"review", "caution", "high"} else 0
        y_engine.append(eng_pred)
        if not db_hit:
            unseen_y_true.append(lbl)
            unseen_y_engine.append(eng_pred)
    elapsed = time.perf_counter() - t0

    def metrics(yt: list[int], yp: list[int]) -> dict[str, object]:
        fp = sum(1 for t, p in zip(yt, yp) if t == 0 and p == 1)
        fn = sum(1 for t, p in zip(yt, yp) if t == 1 and p == 0)
        return {
            "samples": len(yt),
            "accuracy": round(float(accuracy_score(yt, yp)), 4),
            "precision": round(float(precision_score(yt, yp, zero_division=0)), 4),
            "recall": round(float(recall_score(yt, yp, zero_division=0)), 4),
            "f1": round(float(f1_score(yt, yp, zero_division=0)), 4),
            "false_positives": fp,
            "false_negatives": fn,
        }

    return {
        "train_test_domain_overlap": domain_overlap,
        "threat_db_exact_matches_in_sample": threat_db_hits,
        "avg_latency_ms": round((elapsed / max(len(chosen), 1)) * 1000, 2),
        "url_classifier_only": metrics(y_true, y_url_ml),
        "full_engine_all_samples": metrics(y_true, y_engine),
        "full_engine_excluding_threat_db_hits": metrics(unseen_y_true, unseen_y_engine),
    }


def main() -> None:
    report = {
        "uci_sms_5574": eval_uci_sms(),
        "phiusiil_heldout_2000": eval_heldout_phiusiil(2000),
    }
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
