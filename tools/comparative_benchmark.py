"""Reproducible comparative benchmark: v2.1.1 baseline vs current offline vs online mode.

Separates actual live provider checks (when keys are configured) from mocked
fallback tests. Never fabricates live API responses.
"""
from __future__ import annotations

import json
import os
import random
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import GroupShuffleSplit

from scamshield import live_reputation
from scamshield.engine import analyze
from tools.train_url_model import load_phiusiil_urls

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "benchmark" / "comparative_benchmark.json"


def _metrics(yt: list[int], yp: list[int], lat_ms: list[float]) -> dict[str, object]:
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
        "avg_latency_ms": round(sum(lat_ms) / max(len(lat_ms), 1), 2),
    }


def _eval_phiusiil_sample(sample_urls: list[str], sample_labels: list[int]) -> dict[str, object]:
    yp, lat = [], []
    for u in sample_urls:
        t0 = time.perf_counter()
        lvl = analyze(u, channel="sms", language="en")["level"]
        lat.append((time.perf_counter() - t0) * 1000)
        yp.append(1 if lvl in {"review", "caution", "high"} else 0)
    return _metrics(sample_labels, yp, lat)


def _eval_v211_baseline(sample_urls: list[str], sample_labels: list[int]) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="scamshield-v211-") as tmp:
        wt = Path(tmp) / "v211"
        subprocess.run(["git", "worktree", "add", "--detach", str(wt), "v2.1.1"], cwd=ROOT, check=True, capture_output=True)
        try:
            script = (
                "import json, time\n"
                "from scamshield.engine import analyze\n"
                "urls = json.loads(input())\n"
                "out = []\n"
                "for u in urls:\n"
                "    t0 = time.perf_counter()\n"
                "    lvl = analyze(u[:6000], channel='sms', language='en')['level']\n"
                "    out.append((1 if lvl in {'review','caution','high'} else 0, (time.perf_counter()-t0)*1000))\n"
                "print(json.dumps(out))\n"
            )
            proc = subprocess.run(
                [sys.executable, "-c", script],
                cwd=wt,
                env={**os.environ, "PYTHONPATH": str(wt)},
                input=json.dumps(sample_urls),
                text=True,
                capture_output=True,
            )
            if proc.returncode != 0:
                raise RuntimeError(f"v2.1.1 eval failed: {proc.stderr}")
            res = json.loads(proc.stdout)
            yp = [r[0] for r in res]
            lat = [r[1] for r in res]
            return _metrics(sample_labels, yp, lat)
        finally:
            subprocess.run(["git", "worktree", "remove", "--force", str(wt)], cwd=ROOT, capture_output=True)


def main() -> None:
    urls, labels, groups, _ = load_phiusiil_urls()
    _, test_idx = next(GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=42).split(urls, labels, groups))
    rng = random.Random(42)
    chosen = rng.sample(list(test_idx), 500)
    sample_urls = [urls[i] for i in chosen]
    sample_labels = [int(labels[i]) for i in chosen]

    baseline_phi = _eval_v211_baseline(sample_urls, sample_labels)
    current_offline_phi = _eval_phiusiil_sample(sample_urls, sample_labels)

    groq_configured = bool(os.environ.get("GROQ_API_KEY", "").strip())
    gsb_configured = live_reputation.configured()

    from fastapi.testclient import TestClient
    from scamshield import main as app_main

    client = TestClient(app_main.app)
    online_probe_urls = sample_urls[:10]
    online_lat, fallbacks, api_failures = [], 0, 0
    for u in online_probe_urls:
        t0 = time.perf_counter()
        resp = client.post("/api/analyze", json={"text": u, "channel": "sms", "language": "en", "cloud_consent": True})
        online_lat.append((time.perf_counter() - t0) * 1000)
        body = resp.json()
        if body.get("analysis_mode") == "offline_fallback":
            fallbacks += 1
        if (body.get("live_reputation") or {}).get("status") in {"unavailable", "provider_error"}:
            api_failures += 1

    report = {
        "phiusiil_heldout_500_urls": {
            "baseline_v2_1_1": baseline_phi,
            "current_offline_v2_2": current_offline_phi,
        },
        "live_online_mode_status": {
            "groq_api_key_configured": groq_configured,
            "google_safe_browsing_key_configured": gsb_configured,
            "probe_samples": len(online_probe_urls),
            "offline_fallback_count": fallbacks,
            "offline_fallback_success_rate": round(fallbacks / len(online_probe_urls), 4) if not groq_configured else None,
            "live_provider_unavailable_or_error_count": api_failures,
            "avg_latency_ms": round(sum(online_lat) / len(online_lat), 2),
            "note": "Live Groq/Safe Browsing APIs not called because API keys are not configured in this environment.",
        },
    }
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
