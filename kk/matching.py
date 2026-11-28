"""Map a patient's own words to official HBP 2022 procedures.

BM25 over character 3-grams works across scripts and spelling variants. The phrase
list starts from the official procedure names and grows only from real phrasings
(native-speaker translations and consented user queries) in package_phrases.csv.
The top match is always confirmed by the user before any entitlement rule uses it.
"""

from __future__ import annotations

import csv
import math
import unicodedata
from collections import Counter
from pathlib import Path

from .kb import KnowledgeBase


def _grams(text: str, n: int = 3) -> list[str]:
    t = unicodedata.normalize("NFC", text.lower())
    t = " " + " ".join(t.split()) + " "
    return [t[i:i + n] for i in range(max(0, len(t) - n + 1))]


class PackageMatcher:
    def __init__(self, kb: KnowledgeBase, k1: float = 1.5, b: float = 0.75) -> None:
        self.docs: list[tuple[str, str, Counter]] = []   # (procedure_code, display_name, grams)
        names = {r.data["procedure_code"]: r.data["procedure_name"] for r in kb.tables["hbp_packages"]}
        for code, name in names.items():
            self.docs.append((code, name, Counter(_grams(name))))
        path = Path(kb.dir) / "reference" / "package_phrases.csv"
        if path.exists():
            with path.open(encoding="utf-8", newline="") as fh:
                for r in csv.DictReader(fh):
                    if r["procedure_code"] in names:
                        self.docs.append((r["procedure_code"], names[r["procedure_code"]], Counter(_grams(r["phrase"]))))
        self.k1, self.b = k1, b
        self.N = len(self.docs)
        self.avg = sum(sum(c.values()) for _, _, c in self.docs) / self.N if self.N else 0
        df = Counter()
        for _, _, c in self.docs:
            df.update(c.keys())
        self.idf = {g: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for g, n in df.items()}

    def search(self, query: str, k: int = 5) -> list[dict]:
        if not self.docs:
            return []
        q = Counter(_grams(query))
        best: dict[str, float] = {}
        names: dict[str, str] = {}
        for code, name, c in self.docs:
            dl = sum(c.values())
            score = 0.0
            for g in q:
                tf = c.get(g, 0)
                if tf:
                    score += self.idf[g] * tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * dl / self.avg))
            if score > best.get(code, 0):
                best[code], names[code] = score, name
        ranked = sorted(best.items(), key=lambda kv: -kv[1])[:k]
        return [{"procedure_code": c, "procedure_name": names[c], "score": round(s, 3)} for c, s in ranked if s > 0]
