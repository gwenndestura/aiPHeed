"""
tests/integration/test_lead2_tuning.py
--------------------------------------
LEAD2_TUNING: the 72 x 5 LightGBM search is scored under a protocol frozen before scoring; the search space contains
the P0H4-U grid and reproduces P0H4-U on it; the development-global choice reads DEV rows only; the new feature arms
read only cut-off months; the frozen rule is applied as written (nothing adopted); the baseline and the served model
are unchanged.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
RES = LT / "out" / "tune.json"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
pytestmark = pytest.mark.skipif(not RES.exists(), reason="LEAD2_TUNING results missing")


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text())


@pytest.fixture(scope="module")
def runner():
    sys.path.insert(0, str(LT / "runner"))
    import features_v5
    import final
    import lt_lib
    import tune_lib
    return lt_lib, tune_lib, final, features_v5


def test_protocol_frozen_and_used(res):
    want = (LT / "runner" / "TUNING_SHA256.txt").read_text().strip()
    assert hashlib.sha256((LT / "PROTOCOL_LEAD2_TUNING.md").read_bytes()).hexdigest() == want == res["protocol_sha256"]


def test_search_space_contains_and_reproduces_p0h4u(runner):
    T, U, FN, _ = runner
    assert len(U.STRUCT) == 72 and len(U.B0_SIDS) == 4 and {50, 150} <= set(U.CKPT)
    S = pd.read_csv(T.DATA / "stack_v4.csv", dtype={"province_code": str})
    E = pd.read_csv(T.OUT / "final_rows.csv", dtype={"province_code": str})
    P = U.nested(S, T.U2, FN.DIRS, sorted(E["t"].unique()), sids=U.B0_SIDS, ckpts=(50, 150))
    m = E[T.KEY + ["B0_price"]].merge(P, on=T.KEY)
    assert len(m) == 250 and (m["B0_price"] - m["pi_P"]).abs().max() < 1e-5


def test_g0_chosen_on_dev_rows_by_the_frozen_rule(res):
    D = pd.read_csv(LT / "out" / "tune_dev_configs.csv")
    assert len(D) == 360
    ok = D[D["dev_L1_brier"] <= res["cands"]["B0"]["leads"]["1"]["dev"]["brier"] + 0.005]
    assert ok.sort_values(["dev_L2_brier", "cfg"]).iloc[0]["cfg"] == res["G0_cfg"]
    assert not any(c.startswith("conf") for c in D.columns)


def test_feature_arms_read_only_cut_off_months(runner):
    _, _, _, F5 = runner
    yf, yg = F5.yoy_frames()
    for p in yf.columns:
        for m0 in range(int(yf.index.min()) + 24, int(yf.index.max()) + 1, 3):
            for Y in (yf, yg):
                a, b = F5.own_dev(Y, p, m0), F5.own_dev(Y[Y.index <= m0], p, m0)
                assert (a == b) or (pd.isna(a) and pd.isna(b)), (p, m0)


def test_frozen_rule_applied_nothing_adopted(res):
    s = res["selection"]
    assert s["adopted"] is all(s["rule"].values()) is False
    assert s["FINAL"] == "B0" and s["lead2_failed"] == ["R6"] and s["max_reliable_lead"] == 1
    assert "R6" in s["strongest_lead2_failed"]


def test_baselines_unchanged(res, monkeypatch):
    for c, acc, tp, fp in (("P0H4", 0.769, 6, 4), ("B0", 0.800, 10, 6)):
        m = res["cands"][c]["leads"]["2"]["metrics"]
        assert round(m["accuracy"], 3) == acc and (m["tp"], m["fp"]) == (tp, fp)
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.evaluation()["seal_sha256"] == SERVED_SEAL
