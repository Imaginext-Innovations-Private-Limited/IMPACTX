"""Unit tests check the logic with small hand-built inputs.

These inputs exercise code paths (for example, a stent line billed above its ceiling);
they are not evaluation data and are never reported as accuracy. Accuracy is measured
only on real cases with `python -m kk eval eval/cases`.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from kk.kb import KnowledgeBase  # noqa: E402
from kk.service import Auditor  # noqa: E402


@pytest.fixture(scope="session")
def kb():
    return KnowledgeBase()


@pytest.fixture()
def auditor(kb):
    return Auditor(kb)


def bill(lines, admission="2026-11-18", discharge="2026-11-20", **header):
    return {"header": {"hospital_name": "Test Hospital", "admission_date": admission,
                       "discharge_date": discharge, **header},
            "lines": lines}
