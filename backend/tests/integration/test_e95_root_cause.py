"""
tests/integration/test_e95_root_cause.py
----------------------------------------
E95: tied to the frozen protocol, reproduces the E94 unified model exactly, the frozen selection kept it, the
regime-memory correction lowered confirmation-block Brier but lost selection-block detection, and K = 0.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

E95 = Path("..") / "aipheed-backend-aligned" / "experiments" / "E95_Root_Cause"
RUN = E95 / "runs" / "20261022T062732Z"


@pytest.fixture(scope="module")
def m():
    return json.loads((RUN / "metrics.json").read_text(encoding="utf-8"))


def test_protocol_and_reproduction(m):
    assert m["protocol_sha256"] == (E95 / "PROTOCOL.sha256").read_text().split()[0]
    assert hashlib.sha256((E95 / "PROTOCOL.md").read_bytes()).hexdigest() == m["protocol_sha256"]
    assert m["e94_reproduced_max_abs_diff"] < 1e-9


def test_selection_tradeoff_and_k(m):
    assert m["selected"] == min(m["selection_mean_brier"], key=m["selection_mean_brier"].get) == "M-U95-BASE"
    k1 = m["per_k"]["1"]
    assert k1["M-U95-PRUNE"]["confirmation_block"]["brier"] < k1["M-U95-BASE"]["confirmation_block"]["brier"]
    assert k1["M-U95-PRUNE"]["metrics"]["TP"] < k1["M-U95-BASE"]["metrics"]["TP"] == 12
    assert all(v["K"] == 0 for v in m["K"].values())


def test_research_hunger_target(m):
    h = m["research_hunger_target"]["1"]
    assert h["n"] == 13 and h["high"] == 10
    assert h["p"]["accuracy"] == pytest.approx(12 / 13)
    assert h["tests"]["clim"]["p_holm"] < 0.10 and h["tests"]["persist"]["p_holm"] >= 0.10
