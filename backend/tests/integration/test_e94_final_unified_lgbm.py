"""
tests/integration/test_e94_final_unified_lgbm.py
------------------------------------------------
E94: tied to the frozen protocol, the unified model reproduces E93 LINDIR exactly, the frozen selection rule kept it,
its reported K = 1 figures reproduce from the predictions, and no horizon passes the unchanged PASS rule.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

E94 = Path("..") / "aipheed-backend-aligned" / "experiments" / "E94_Final_Unified_LightGBM"
RUN = E94 / "runs" / "20261022T061502Z"


@pytest.fixture(scope="module")
def metrics():
    return json.loads((RUN / "metrics.json").read_text(encoding="utf-8"))


def test_tied_to_frozen_protocol(metrics):
    assert metrics["protocol_sha256"] == (E94 / "PROTOCOL.sha256").read_text().split()[0]
    assert hashlib.sha256((E94 / "PROTOCOL.md").read_bytes()).hexdigest() == metrics["protocol_sha256"]


def test_reproduces_e93_and_selection(metrics):
    assert metrics["e93_reproduced_max_abs_diff"] < 1e-9
    sel = metrics["selection_mean_brier"]
    assert metrics["selected"] == min(sel, key=sel.get) == "M-U94"


def test_k1_figures_and_k(metrics):
    P = pd.read_csv(RUN / "predictions_k1.csv")
    yh = (P["M-U94"] >= 0.5).astype(int)
    assert float((yh == P["y"]).mean()) == pytest.approx(55 / 65)
    assert int(((yh == 1) & (P["y"] == 1)).sum()) == 12
    assert float(np.mean((P["M-U94"] - P["y"]) ** 2)) == pytest.approx(metrics["per_k"]["1"]["M-U94"]["metrics"]["brier"])
    p = metrics["per_k"]["1"]["M-U94"]["pass"]
    assert p["acc_gt_75"] and p["bal_beats_baselines"] and p["recall_ge_50"] and not p["brier_beats_sig"]
    assert all(v["K"] == 0 for v in metrics["K"].values())


def test_all_horizons_issued():
    for k in (1, 2, 3, 4):
        P = pd.read_csv(RUN / f"predictions_k{k}.csv")
        assert len(P) == 65 and P["M-U94"].notna().all()
