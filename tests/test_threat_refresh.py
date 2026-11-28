"""Tests for atomic threat database refresh and metadata reporting."""
import gzip
import hashlib
import sqlite3

import pytest

from tools.refresh_threat_db import refresh_from_bytes


def test_atomic_refresh_valid_and_preserves_on_failure(tmp_path):
    db_path = tmp_path / "verified_threats.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE threats (url_hash TEXT PRIMARY KEY, source TEXT NOT NULL)")
    conn.execute("INSERT INTO threats VALUES (?, ?)", ("oldhash", "PhishTank"))
    conn.commit()
    conn.close()

    # Invalid gzip should raise and preserve existing DB
    with pytest.raises(ValueError):
        refresh_from_bytes(b"not-gzip", db_path=db_path, min_records=1)
    conn = sqlite3.connect(str(db_path))
    assert conn.execute("SELECT url_hash FROM threats").fetchall() == [("oldhash",)]
    conn.close()

    # Valid gzip should atomically replace DB and write meta.json
    csv_text = "phish_id,url,verified,online\n1,http://phish1.example/login,yes,yes\n2,http://phish2.example/pay,yes,yes\n"
    gz = gzip.compress(csv_text.encode("utf-8"))
    meta = refresh_from_bytes(gz, db_path=db_path, min_records=2)
    assert meta["unique_hashes"] == 2
    assert db_path.with_suffix(".meta.json").is_file()
    expected_h = hashlib.sha256(b"http://phish1.example/login").hexdigest()
    conn = sqlite3.connect(str(db_path))
    rows = {r[0] for r in conn.execute("SELECT url_hash FROM threats").fetchall()}
    conn.close()
    assert expected_h in rows
