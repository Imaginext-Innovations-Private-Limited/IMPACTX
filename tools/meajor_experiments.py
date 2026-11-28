"""Cross-source MeAJOR email phishing experiments (Task 2 & Task 3).

Trains only on deduplicated trec5+trec6 (stripping anonymization tokens),
evaluates on unseen trec7, UCI SMS ham (4,827), and 10 contextual categories.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import pickle
import random
import re
import time
import zipfile
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.naive_bayes import ComplementNB
from sklearn.svm import LinearSVC

from scamshield.engine import _model as baseline_svm_model
from scamshield.engine import analyze as engine_analyze

csv.field_size_limit(10 * 1024 * 1024)

ROOT = Path(__file__).resolve().parent.parent
MEAJOR_CSV = ROOT / "data" / "external" / "meajor" / "meajor_cleaned_preprocessed.csv"
SMS_ZIP = ROOT / "data" / "external" / "sms_spam.zip"
OUT_REPORT = ROOT / "benchmark" / "meajor_model_comparison.json"
CANDIDATE_MODEL = ROOT / "scamshield" / "data" / "email_phish_model.joblib"

_ANON_RE = re.compile(r"<\|[A-Z_]+\|>|\[(?:ORGANIZATION|PERSON|LOCATION|EMAIL|URL|DATE|PHONE|NUMBER)\]", re.I)
_PHISH_TOPIC_RE = re.compile(
    r"\b(?:account|verify|verification|password|login|sign\s*in|bank|paypal|ebay|security|"
    r"suspend|suspended|confirm|update|billing|invoice|payment|transfer|wire|fund|million|"
    r"beneficiary|inheritance|lottery|urgent|confidential|click\s+here|dear\s+customer)\b",
    re.I,
)

CONTEXTUAL_CASES = [
    ("polished_phishing_email", 1, "Dear Valued Client, our quarterly compliance review requires confirming your online banking preferences. Please sign in at our verification portal."),
    ("fake_account_verification", 1, "Notice: Unusual sign-in activity was detected on your corporate mailbox. Re-authenticate your session within 24 hours to retain access."),
    ("credential_theft", 1, "IT Helpdesk: Your directory password expires today. Reply with your current password or enter your OTP code on the reset form."),
    ("bec_impersonation", 1, "Hi Finance Team, I am in a board meeting and cannot take calls. Please process an urgent vendor wire transfer of $18,500 today and keep this confidential."),
    ("recruitment_advance_fee", 1, "Congratulations! You are shortlisted for a remote data analyst role paying Rs 4,500 daily. Deposit a refundable training kit fee to receive your offer letter."),
    ("digital_arrest", 1, "CBI officer speaking. Your Aadhaar is linked to a seized narcotics parcel. Stay on video call; you are under digital arrest unless you pay the security deposit."),
    ("upi_refund_fraud", 1, "Your Rs 2,500 cashback refund is ready. Open your UPI app, approve the collect request, and enter your UPI PIN to receive the credit."),
    ("codemixed_indian", 1, "Aapka KYC expire ho gaya hai. Abhi paise transfer karo warna account block hoga aur police case darj hoga."),
    ("obfuscated_scam", 1, "U-R-G-E-N-T: Sh4re your O.T.P c0de n0w to av0id bank acc0unt suspensi0n."),
    ("legit_similar_wording", 0, "Security awareness reminder: Our bank will never ask for your password, OTP, or UPI PIN by email or phone. Always open the official app yourself."),
]


def _clean_text(subj: str, body: str) -> str:
    raw = f"{subj or ''}\n{body or ''}".strip()
    cleaned = _ANON_RE.sub(" ", raw)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned[:4000]


def _tmpl_hash(text: str) -> str:
    norm = re.sub(r"\d+", "0", text.lower())
    return hashlib.sha256(norm[:1500].encode("utf-8", errors="replace")).hexdigest()


def load_cross_source_meajor(max_train_per_class: int = 4000, max_test_per_class: int = 1500):
    seen_tmpls: set[str] = set()
    train_pos, train_neg = [], []
    test_pos, test_neg = [], []

    with open(MEAJOR_CSV, "r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = row.get("source", "")
            lbl = row.get("label", "")
            if src not in {"trec5", "trec6", "trec7"} or lbl not in {"0.0", "1.0"}:
                continue
            lang = (row.get("language") or "").lower()
            if lang and not lang.startswith("en"):
                continue
            txt = _clean_text(row.get("subject", ""), row.get("body", ""))
            if len(txt) < 40:
                continue
            # Skip heavily garbled encoding rows
            ascii_ratio = sum(1 for c in txt[:200] if ord(c) < 128) / max(min(len(txt), 200), 1)
            if ascii_ratio < 0.85:
                continue

            th = _tmpl_hash(txt)
            if th in seen_tmpls:
                continue
            seen_tmpls.add(th)

            y = 1 if lbl == "1.0" else 0
            # Focus positive class on phishing/financial/account/advance-fee emails (avoid Viagra/promo spam conflation)
            if y == 1 and not _PHISH_TOPIC_RE.search(txt):
                continue

            if src in {"trec5", "trec6"}:
                if y == 1 and len(train_pos) < max_train_per_class * 2:
                    train_pos.append(txt)
                elif y == 0 and len(train_neg) < max_train_per_class * 2:
                    train_neg.append(txt)
            else:  # trec7 unseen source
                if y == 1 and len(test_pos) < max_test_per_class * 2:
                    test_pos.append(txt)
                elif y == 0 and len(test_neg) < max_test_per_class * 2:
                    test_neg.append(txt)

    rng = random.Random(42)
    rng.shuffle(train_pos)
    rng.shuffle(train_neg)
    rng.shuffle(test_pos)
    rng.shuffle(test_neg)

    tr_p = train_pos[:max_train_per_class]
    tr_n = train_neg[:max_train_per_class]
    te_p = test_pos[:max_test_per_class]
    te_n = test_neg[:max_test_per_class]

    X_train = tr_p + tr_n
    y_train = [1] * len(tr_p) + [0] * len(tr_n)
    X_test = te_p + te_n
    y_test = [1] * len(te_p) + [0] * len(te_n)
    return X_train, y_train, X_test, y_test


def load_uci_sms_ham() -> list[str]:
    with zipfile.ZipFile(SMS_ZIP) as zf:
        lines = io.TextIOWrapper(zf.open("SMSSpamCollection"), "utf-8", errors="replace").readlines()
    return [l.split("\t", 1)[1].strip() for l in lines if l.startswith("ham\t")]


def main() -> None:
    print("Loading cross-source MeAJOR split (train: trec5+trec6, test: trec7)...")
    X_train, y_train, X_test, y_test = load_cross_source_meajor()
    sms_ham = load_uci_sms_ham()
    print(f"Train: {len(X_train)} ({sum(y_train)} pos), Test trec7: {len(X_test)} ({sum(y_test)} pos), UCI SMS ham: {len(sms_ham)}")

    word_vec = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=3, max_features=20000, sublinear_tf=True, dtype=np.float32)
    char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=5, max_features=15000, sublinear_tf=True, dtype=np.float32)

    X_tr_w = word_vec.fit_transform(X_train)
    X_tr_c = char_vec.fit_transform(X_train)
    X_tr = hstack([X_tr_w, X_tr_c])

    X_te = hstack([word_vec.transform(X_test), char_vec.transform(X_test)])
    X_sms = hstack([word_vec.transform(sms_ham), char_vec.transform(sms_ham)])
    X_ctx = hstack([word_vec.transform([c[2] for c in CONTEXTUAL_CASES]), char_vec.transform([c[2] for c in CONTEXTUAL_CASES])])

    results = {}

    # 1. Existing baseline 394-row char SVM
    base = baseline_svm_model()
    t0 = time.perf_counter()
    base_scores = base.decision_function(X_test)
    base_ms = (time.perf_counter() - t0) * 1000 / len(X_test)
    base_pred = [1 if s >= 0.20 else 0 for s in base_scores]
    base_sms_fp = sum(1 for s in base.decision_function(sms_ham) if s >= 0.20)
    base_ctx = [1 if s >= 0.20 else 0 for s in base.decision_function([c[2] for c in CONTEXTUAL_CASES])]
    results["1_baseline_char_svm_394"] = {
        "accuracy": round(float(accuracy_score(y_test, base_pred)), 4),
        "precision": round(float(precision_score(y_test, base_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, base_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, base_pred, zero_division=0)), 4),
        "false_positives": int(sum(1 for t, p in zip(y_test, base_pred) if t == 0 and p == 1)),
        "false_negatives": int(sum(1 for t, p in zip(y_test, base_pred) if t == 1 and p == 0)),
        "uci_sms_ham_fp_rate": round(base_sms_fp / len(sms_ham), 4),
        "contextual_10_hits": f"{sum(1 for (_, y, _), p in zip(CONTEXTUAL_CASES, base_ctx) if y == p)}/10",
        "latency_ms_per_doc": round(base_ms, 3),
        "model_kb": 0.0,
    }

    models = {
        "2_word_char_linear_svm": LinearSVC(C=1.0, class_weight="balanced", random_state=42),
        "3_word_char_logreg": LogisticRegression(C=2.0, max_iter=500, class_weight="balanced", random_state=42),
        "4_word_char_complement_nb": ComplementNB(alpha=0.5),
    }

    trained = {}
    for name, clf in models.items():
        clf.fit(X_tr, y_train)
        trained[name] = clf
        t0 = time.perf_counter()
        if hasattr(clf, "predict_proba"):
            probs = clf.predict_proba(X_te)[:, 1]
            pred = [1 if p >= 0.65 else 0 for p in probs]
            sms_fp = sum(1 for p in clf.predict_proba(X_sms)[:, 1] if p >= 0.65)
            ctx_pred = [1 if p >= 0.65 else 0 for p in clf.predict_proba(X_ctx)[:, 1]]
        else:
            scores = clf.decision_function(X_te)
            pred = [1 if s >= 0.20 else 0 for s in scores]
            sms_fp = sum(1 for s in clf.decision_function(X_sms) if s >= 0.20)
            ctx_pred = [1 if s >= 0.20 else 0 for s in clf.decision_function(X_ctx)]
        ms = (time.perf_counter() - t0) * 1000 / len(X_test)
        size_kb = len(pickle.dumps((word_vec, char_vec, clf))) / 1024
        results[name] = {
            "accuracy": round(float(accuracy_score(y_test, pred)), 4),
            "precision": round(float(precision_score(y_test, pred, zero_division=0)), 4),
            "recall": round(float(recall_score(y_test, pred, zero_division=0)), 4),
            "f1": round(float(f1_score(y_test, pred, zero_division=0)), 4),
            "false_positives": int(sum(1 for t, p in zip(y_test, pred) if t == 0 and p == 1)),
            "false_negatives": int(sum(1 for t, p in zip(y_test, pred) if t == 1 and p == 0)),
            "uci_sms_ham_fp_rate": round(sms_fp / len(sms_ham), 4),
            "contextual_10_hits": f"{sum(1 for (_, y, _), p in zip(CONTEXTUAL_CASES, ctx_pred) if y == p)}/10",
            "latency_ms_per_doc": round(ms, 3),
            "model_kb": round(size_kb, 1),
        }

    # 5. Lightweight soft-vote ensemble (LogReg + ComplementNB)
    lr = trained["3_word_char_logreg"]
    cnb = trained["4_word_char_complement_nb"]
    t0 = time.perf_counter()
    ens_p = 0.6 * lr.predict_proba(X_te)[:, 1] + 0.4 * cnb.predict_proba(X_te)[:, 1]
    ens_pred = [1 if p >= 0.65 else 0 for p in ens_p]
    ens_ms = (time.perf_counter() - t0) * 1000 / len(X_test)
    ens_sms_fp = sum(1 for p in (0.6 * lr.predict_proba(X_sms)[:, 1] + 0.4 * cnb.predict_proba(X_sms)[:, 1]) if p >= 0.65)
    ens_ctx = [1 if p >= 0.65 else 0 for p in (0.6 * lr.predict_proba(X_ctx)[:, 1] + 0.4 * cnb.predict_proba(X_ctx)[:, 1])]
    results["5_ensemble_logreg_cnb"] = {
        "accuracy": round(float(accuracy_score(y_test, ens_pred)), 4),
        "precision": round(float(precision_score(y_test, ens_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_test, ens_pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y_test, ens_pred, zero_division=0)), 4),
        "false_positives": int(sum(1 for t, p in zip(y_test, ens_pred) if t == 0 and p == 1)),
        "false_negatives": int(sum(1 for t, p in zip(y_test, ens_pred) if t == 1 and p == 0)),
        "uci_sms_ham_fp_rate": round(ens_sms_fp / len(sms_ham), 4),
        "contextual_10_hits": f"{sum(1 for (_, y, _), p in zip(CONTEXTUAL_CASES, ens_ctx) if y == p)}/10",
        "latency_ms_per_doc": round(ens_ms, 3),
        "model_kb": round(len(pickle.dumps((word_vec, char_vec, lr, cnb))) / 1024, 1),
    }

    # Save specialized LogReg email phishing model for potential integration
    joblib.dump({"word_vec": word_vec, "char_vec": char_vec, "classifier": lr}, CANDIDATE_MODEL, compress=3)
    print(f"Saved candidate LogReg email model: {CANDIDATE_MODEL} ({CANDIDATE_MODEL.stat().st_size / 1024:.1f} KB)")

    # Also check full current engine on the 10 contextual cases
    ctx_full = []
    for name, y, txt in CONTEXTUAL_CASES:
        lvl = engine_analyze(txt, channel="email" if "email" in name or "bec" in name or "verification" in name else "message", language="en")["level"]
        ctx_full.append({"case": name, "expected": y, "level": lvl})

    report = {
        "split": {"train_trec5_trec6": len(X_train), "test_trec7": len(X_test), "uci_sms_ham": len(sms_ham)},
        "models": results,
        "full_engine_contextual_10": ctx_full,
    }
    OUT_REPORT.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
