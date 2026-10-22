"""
tests/integration/test_e93_lead2_breakthrough.py
------------------------------------------------
E93 unified news-informed LightGBM: tied to the frozen protocol, one framework issues K = 1..4 on identical targets,
news is an input of every selectable arm, the frozen selection rule picked the reported arm, the reported figures
reproduce from the predictions, and no horizon passes the unchanged PASS rule.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

E93 = Path("..") / "aipheed-backend-aligned" / "experiments" / "E93_Lead2_Breakthrough"
RUN = E93 / "runs" / "20261022T060351Z"
KS = (1, 2, 3, 4)


@pytest.fixture(scope="module")
def metrics():
    return json.loads((RUN / "metrics.json").read_text(encoding="utf-8"))


def test_tied_to_frozen_protocol(metrics):
    assert metrics["protocol_sha256"] == (E93 / "PROTOCOL.sha256").read_text().split()[0]
    assert hashlib.sha256((E93 / "PROTOCOL.md").read_bytes()).hexdigest() == metrics["protocol_sha256"]


def test_news_required_in_selectable_arms():
    src = (E93 / "runner" / "run_e93.py").read_text(encoding="utf-8")
    for arm in ('"M-U93-DIR": ("clf", True, False, True)', '"M-U93-LINDIR": ("lin", True, False, True)',
                '"M-U93-LINDIR-W": ("lin", True, True, True)'):
        assert arm in src


def test_one_framework_all_horizons_identical_targets():
    P = {k: pd.read_csv(RUN / f"predictions_k{k}.csv") for k in KS}
    for k in KS:
        assert len(P[k]) == 65 and int(P[k]["y"].sum()) == 16 and P[k]["M-U93-LINDIR"].notna().all()
        assert list(P[k]["target_q"]) == list(P[1]["target_q"])


def test_selection_figures_and_k(metrics):
    sel = metrics["selection_mean_brier"]
    assert metrics["selected"] == min(sel, key=sel.get) == "M-U93-LINDIR"
    P = pd.read_csv(RUN / "predictions_k1.csv")
    yh = (P["M-U93-LINDIR"] >= 0.5).astype(int)
    assert float((yh == P["y"]).mean()) == pytest.approx(55 / 65)
    assert int(((yh == 1) & (P["y"] == 1)).sum()) == 12
    assert float(np.mean((P["M-U93-LINDIR"] - P["y"]) ** 2)) == pytest.approx(
        metrics["per_k"]["1"]["M-U93-LINDIR"]["metrics"]["brier"])
    assert all(v["K"] == 0 for v in metrics["K"].values())
    assert metrics["per_k"]["1"]["M-U93-LINDIR"]["pass"]["PASS"] is False
