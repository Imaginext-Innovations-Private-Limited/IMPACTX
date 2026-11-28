"""Daily watcher for official pages (run from cron or a scheduler).

For each page in data/watch.yaml: download, hash, compare with the last run, keep a dated
copy when it changed, and print what changed. A person then downloads the new notification
PDF, runs the importer, checks every staged row and approves it.

Also warns about rules that expire within 30 days.
"""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from kk.kb import KnowledgeBase  # noqa: E402

DATA = ROOT / "data"
STATE = DATA / "raw" / "watch_state.json"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "KharchaKavach-refresh/2.0 (+public-interest)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.read()


def main() -> int:
    pages = yaml.safe_load((DATA / "watch.yaml").read_text())["pages"]
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    changed = []
    for p in pages:
        try:
            body = fetch(p["url"])
        except Exception as e:   # network errors are reported, never fatal
            print(f"[error] {p['name']}: {e}")
            continue
        h = hashlib.sha256(body).hexdigest()
        if state.get(p["name"]) != h:
            out = DATA / "raw" / f"{date.today().isoformat()}_{p['name']}.html"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(body)
            changed.append(p["name"])
            state[p["name"]] = h
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=2))
    print("changed:", ", ".join(changed) if changed else "nothing")

    kb = KnowledgeBase()
    soon = date.today() + timedelta(days=30)
    for table, rows in kb.tables.items():
        for r in rows:
            if r.valid_to and date.today() <= r.valid_to <= soon:
                print(f"[expiring] {table} {r.id} valid to {r.valid_to} - check for an extension notification")
    return 0


if __name__ == "__main__":
    sys.exit(main())
