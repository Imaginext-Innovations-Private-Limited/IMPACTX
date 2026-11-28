"""Specialized offline email phishing classifier trained on MeAJOR (trec5+trec6).

Complements the existing multilingual engine; never presented as a calibrated
fraud probability or proof of fraud.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import joblib
from scipy.sparse import hstack

DATA_DIR = Path(__file__).resolve().parent / "data"
EMAIL_MODEL_PATH = DATA_DIR / "email_phish_model.joblib"


@lru_cache(maxsize=1)
def _load_email_bundle(model_path: str = str(EMAIL_MODEL_PATH)) -> dict[str, Any] | None:
    p = Path(model_path)
    if not p.is_file():
        return None
    try:
        return joblib.load(p)
    except Exception:
        return None


def classify_email_text(text: str, model_path: Path = EMAIL_MODEL_PATH) -> dict[str, Any]:
    """Score email-like text using the bundled Word+Char TF-IDF LogisticRegression model."""
    clean = (text or "").strip()
    if len(clean.split()) < 8:
        return {"available": True, "score": None, "flag": "none"}

    bundle = _load_email_bundle(str(model_path))
    if bundle is None:
        return {"available": False, "score": None, "flag": "none"}

    x_w = bundle["word_vec"].transform([clean[:4000]])
    x_c = bundle["char_vec"].transform([clean[:4000]])
    prob = float(bundle["classifier"].predict_proba(hstack([x_w, x_c]))[0][1])

    flag = "none"
    if prob >= 0.85:
        flag = "caution"
    elif prob >= 0.65:
        flag = "review"
    return {"available": True, "score": prob, "flag": flag}
