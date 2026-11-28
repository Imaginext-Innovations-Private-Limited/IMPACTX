"""Safe, atomic threat-database refresh from authorized PhishTank feed.

Validates downloaded gzip CSV schema and record count before atomically
replacing scamshield/data/verified_threats.db. Preserves existing snapshot on failure.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import sqlite3
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from scamshield.url_classifier import THREAT_DB_PATH, normalize_url

PHISHTANK_FEED_URL = "https://data.phishtank.com/data/online-valid.csv.gz"


def refresh_from_bytes(
    gz_bytes: bytes,
    db_path: Path = THREAT_DB_PATH,
    min_records: int = 1000,
    source_label: str = "PhishTank online-valid.csv.gz",
) -> dict[str, object]:
    """Validate gzipped PhishTank CSV bytes and atomically replace threat DB."""
    if not gz_bytes or not gz_bytes.startswith(b"\x1f\x8b"):
        raise ValueError("Invalid gzip payload; existing threat DB preserved.")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_db = db_path.with_suffix(".db.tmp")
    if tmp_db.exists():
        tmp_db.unlink()

    seen: set[str] = set()
    batch: list[tuple[str, str]] = []
    total_rows = 0

    try:
        text_stream = gzip.decompress(gz_bytes).decode("utf-8", errors="replace").splitlines()
        reader = csv.DictReader(text_stream)
        required_cols = {"phish_id", "url", "verified", "online"}
        if not reader.fieldnames or not required_cols.issubset(set(reader.fieldnames)):
            raise ValueError("Missing required PhishTank CSV columns; existing threat DB preserved.")

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

        if len(batch) < min_records:
            raise ValueError(f"Too few valid records ({len(batch)} < {min_records}); existing threat DB preserved.")

        conn = sqlite3.connect(str(tmp_db))
        conn.execute("CREATE TABLE threats (url_hash TEXT PRIMARY KEY, source TEXT NOT NULL)")
        conn.executemany("INSERT INTO threats (url_hash, source) VALUES (?, ?)", batch)
        conn.commit()
        conn.execute("VACUUM")
        conn.close()

        db_sha256 = hashlib.sha256(tmp_db.read_bytes()).hexdigest()
        os.replace(tmp_db, db_path)

        meta = {
            "source": source_label,
            "snapshot_timestamp": datetime.now(timezone.utc).isoformat(),
            "total_rows_read": total_rows,
            "unique_hashes": len(batch),
            "db_sha256": db_sha256,
            "redistribution_note": "Verify PhishTank non-commercial/research feed terms before public redistribution.",
        }
        db_path.with_suffix(".meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return meta
    except Exception:
        if tmp_db.exists():
            tmp_db.unlink()
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=None, help="Optional local .csv.gz snapshot path")
    parser.add_argument("--min-records", type=int, default=1000)
    args = parser.parse_args()

    if args.input is not None:
        gz_bytes = args.input.read_bytes()
    else:
        req = urllib.request.Request(PHISHTANK_FEED_URL, headers={"User-Agent": "ScamShield-ThreatRefresh/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            gz_bytes = resp.read()

    meta = refresh_from_bytes(gz_bytes, min_records=args.min_records)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
