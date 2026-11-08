"""E13 Amendment-1 synthetic tests: lag-3 availability, drift baselines and future-perturbation invariance.
No project data is read."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

RUNNER = Path(__file__).resolve().parents[1] / "runner"
sys.path.insert(0, str(RUNNER))
import e13_lib as L  # noqa: E402
import run_amendment1 as A  # noqa: E402

from test_e13_guard_and_lib import synth_comp, synth_rounds  # noqa: E402


def test_lag3_features_use_T_minus_3_only():
    c = synth_comp()
    f = A.b_features_lag(c, "2024-Q2", 3).set_index("province_code")
    ref = c[c["quarter"] == "2023-Q3"].set_index("province_code")
    assert np.allclose(f["F_lag"], ref["F"].reindex(f.index))


def test_lag3_training_targets_are_at_most_T_minus_3():
    c = synth_comp()
    tr = A.b_training_lag(c, "2024-Q4", 3)
    assert tr["quarter"].map(L.qi).max() == L.qi("2024-Q1")
    assert tr["quarter"].map(L.qi).min() == L.qi("2021-Q4")


def test_st3_invariant_to_values_after_T_minus_3():
    c = synth_comp()
    p0, _ = A.st3_forecasts(c, ["2024-Q4"])
    c2 = c.copy()
    c2.loc[c2["quarter"].map(L.qi) >= L.qi("2024-Q4") - 2, ["F", "D", "mean5"]] = 999.0
    p1, _ = A.st3_forecasts(c2, ["2024-Q4"])
    assert np.array_equal(p0["forecast"].to_numpy(), p1["forecast"].to_numpy())


def test_drift_baselines_use_published_history_only():
    r, c = synth_rounds(), synth_comp()
    T = "2024-Q3"
    fe = L.a_features(r, c, T)
    v0 = A.a_drift(r, c, T, fe["H_last"], fe["H_age_quarters"])
    r2 = r.copy()
    r2.loc[r2["published"] >= L.origin(T), "H"] = 999.0
    assert A.a_drift(r2, c, T, fe["H_last"], fe["H_age_quarters"]) == v0
    p0 = A.new_arms_primary(r, c, None, None, Ts_A=[], Ts_B=[T])
    c2 = c.copy()
    c2.loc[c2["quarter"].map(L.qi) >= L.qi(T) - 1, ["F", "D", "mean5"]] = 999.0
    p1 = A.new_arms_primary(r, c2, None, None, Ts_A=[], Ts_B=[T])
    assert np.array_equal(p0["forecast"].to_numpy(), p1["forecast"].to_numpy())


def test_b1_drift_formula():
    c = synth_comp()
    T = "2024-Q1"
    p = A.new_arms_primary(synth_rounds(), c, None, None, Ts_A=[], Ts_B=[T])
    pc = "PH040300000"
    f_lag = c[(c["quarter"] == "2023-Q3") & (c["province_code"] == pc)]["F"].iloc[0]
    f0 = c[(c["quarter"] == "2021-Q1") & (c["province_code"] == pc)]["F"].iloc[0]
    want = f_lag + 2 * (f_lag - f0) / (L.qi("2023-Q3") - L.qi("2021-Q1"))
    got = p[(p["arm"] == "B1_drift") & (p["province_code"] == pc)]["forecast"].iloc[0]
    assert abs(got - want) < 1e-12
