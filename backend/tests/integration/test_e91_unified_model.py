"""
tests/integration/test_e91_unified_model.py
-------------------------------------------
E91 unified horizon-conditioned model: the run and seal are reproducible artifacts. One model per origin issues every
horizon, the pooled training pairs never use a label unposted at the origin, the frozen selection rule picked the
reported architecture, the validated K follows the unchanged PASS rule, and earlier seals are untouched.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

E91 = Path("..") / "aipheed-backend-aligned" / "experiments" / "E91_Unified_Horizon_Model"
RUN = E91 / "runs" / "20261022T045201Z"
KS = (1, 2, 3, 4)
CORE_ARMS = ["U-STRUCT", "U-CAL", "U-LR", "U-LR-RICE", "U-GB"]


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def metrics():
    return json.loads((RUN / "metrics.json").read_text(encoding="utf-8"))


def _acc(P, arm):
    issued = P[arm].notna()
    yhat = np.where(issued, (P[arm] >= 0.5).astype(int), 1 - P["y"])
    return float((yhat == P["y"]).mean())


def test_run_is_tied_to_the_frozen_protocol(metrics):
    assert metrics["protocol_sha256"] == (E91 / "PROTOCOL.sha256").read_text().split()[0]
    assert _sha(E91 / "PROTOCOL.md") == metrics["protocol_sha256"]


def test_same_rows_at_every_horizon_and_baseline_figures_reproduce():
    P = {k: pd.read_csv(RUN / f"predictions_k{k}.csv", dtype={"province_code": str}) for k in KS}
    targets = sorted(P[1]["target_q"].unique())
    for k in KS:
        assert len(P[k]) == 65 and sorted(P[k]["target_q"].unique()) == targets and int(P[k]["y"].sum()) == 16
        assert (P[k]["t"] == P[k]["target_q"].map(lambda q: int(q[:4]) * 4 + int(q[-1]) - 1) - k).all()
        assert np.allclose(P[k]["U-STRUCT"], P[k]["S-COV"], equal_nan=True)
    assert _acc(P[1], "S-SIM") == pytest.approx(55 / 65)          # E89 Lead-1 S-SIM 0.846
    assert _acc(P[2], "S-COV") == pytest.approx(52 / 65)          # E89 Lead-2 S-COV 0.800
    for a in CORE_ARMS:                                            # K = 4: the structural core cannot issue
        assert P[4][a].isna().all()


def test_selection_rule_and_validated_k(metrics):
    sel = metrics["selection_mean_brier"]
    assert metrics["selected"] == min(sel, key=sel.get) == "U-GB"
    assert "U-LR-RICE" not in sel and metrics["selection_horizons"] == [1, 2, 3]
    for arm, v in metrics["K"].items():
        ok = [metrics["per_k"][str(k)][arm]["pass"]["PASS"] and metrics["per_k"][str(k)][arm]["generalization"]["criteria"]["b"]
              and metrics["per_k"][str(k)][arm]["generalization"]["majority_quarters"] >= 0.6 for k in KS]
        K = 0
        for k, o in zip(KS, ok):
            if not o:
                break
            K = k
        assert v["K"] == K == 0                                    # no horizon passes for any arm


def test_pooled_training_pairs_use_only_labels_posted_before_the_origin():
    sys.path.insert(0, str((E91 / "runner").resolve()))
    import run_e91 as U
    d, _ = U.E.data()
    T, _ = U.load_tables()
    for q in ("2023-Q2", "2024-Q3", "2026-Q3"):
        t = U.L.qi(q)
        tr = U.pooled_pairs(T, d, t)
        av = U.E.available(d, t)
        posted = set(zip(av["province_code"], av["q"]))
        assert (tr["q"] <= t - 1).all() and (tr["t"] + tr["k"] == tr["q"]).all()
        assert all((p, qq) in posted for p, qq in zip(tr["province_code"], tr["q"]))
        assert set(tr["k"]) <= set(KS)


def test_seals():
    f = E91 / "sealed" / "e91_prospective.csv"
    assert _sha(f) == (E91 / "sealed" / "e91_prospective.csv.sha256").read_text().split()[0]
    S = pd.read_csv(f)
    assert sorted(S["K"].unique()) == [1, 2, 3] and set(S["origin"]) == {"2026-10-01"}
    exp = Path("..") / "aipheed-backend-aligned" / "experiments"
    for rel, sha in (("E83_Deep_Reconstruction/sealed/e83_prospective.csv", "1331d4987a320b15"),
                     ("E84_Objective_Continuation/sealed/e84_prospective.csv", "ad40266017f26dc5"),
                     ("E90_Advanced_Optimization/sealed/e90_prospective.csv", "cef43f6a80967bbc")):
        assert _sha(exp / rel).startswith(sha)
