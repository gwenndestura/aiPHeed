"""FI8 tests: the persistence correction collapses to damped persistence when predictors carry no signal, and
recovers a planted signal; selection uses training rows only."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.fi7 import models as M7
from app.fi8.study import DampedCorrection


def _frame(n=80, signal=0.0, seed=3):
    rng = np.random.default_rng(seed)
    base = np.full(n, 12.0)
    last = base + rng.normal(0, 4, n)
    x = rng.normal(size=n)
    tgt = base + 0.6 * (last - base) + signal * x + rng.normal(0, 1.0, n)
    return pd.DataFrame({"hunger_last": last, "baseline_known": base, "hunger_target": tgt, "hunger_age_q": 1.0,
                         "threshold_known": base + 5, "x": x, "noise": rng.normal(size=n)})


def test_no_signal_means_no_correction():
    df = _frame(signal=0.0)
    m = DampedCorrection(["noise"], "lasso").fit(df, df["hunger_target"] - df["hunger_last"])
    damped = M7.Damped().fit(df, df["hunger_target"] - df["hunger_last"])
    assert np.max(np.abs(m.predict_level(df) - damped.predict_level(df))) < 0.5


def test_planted_signal_is_recovered():
    df = _frame(signal=3.0)
    m = DampedCorrection(["x", "noise"], "lasso").fit(df, df["hunger_target"] - df["hunger_last"])
    assert "x" in m.selected and "noise" not in m.selected
    err_m = np.mean((m.predict_level(df) - df["hunger_target"]) ** 2)
    err_d = np.mean((M7.Damped().fit(df, df["hunger_target"]).predict_level(df) - df["hunger_target"]) ** 2)
    assert err_m < 0.5 * err_d
