"""E17 v3 synthetic tests (no project data): information cutoff, candidate formulas, pairs, selection rule, guard."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import guard  # noqa: E402
import v3_lib as V  # noqa: E402


def series():
    idx = [V.qk(q) for q in ["2021-Q2", "2021-Q3", "2021-Q4", "2022-Q2", "2022-Q3", "2022-Q4", "2023-Q1", "2023-Q2",
                             "2023-Q3", "2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q4"]]
    hs = pd.Series(np.linspace(10, 20, len(idx)) + np.sin(np.arange(len(idx))), index=idx)
    allq = range(V.qk("2021-Q1"), V.qk("2025-Q4") + 1)
    f5 = pd.Series(np.linspace(5, 1, len(allq)), index=list(allq))
    U = pd.Series(np.linspace(8, 4, len(allq)), index=list(allq))
    return hs, f5, U


def test_information_cutoff_invariance():
    hs, f5, U = series()
    T, h = V.qk("2025-Q4"), 5
    a, _ = V.h_candidates(hs, f5, U, T, h)
    hs2, f52, U2 = hs.copy(), f5.copy(), U.copy()
    for s in (hs2, f52, U2):
        s[s.index > T - h] = 999.0
    b, _ = V.h_candidates(hs2, f52, U2, T, h)
    assert a == b and "C1_carry_forward" in a


def test_carry_forward_mean_drift_formulas():
    hs, f5, U = series()
    T, h = V.qk("2025-Q4"), 5
    c, meta = V.h_candidates(hs, f5, U, T, h)
    obs = hs[hs.index <= T - h]
    assert c["C1_carry_forward"] == obs.iloc[-1]
    assert c["C2_mean"] == pytest.approx(obs.mean())
    g = (obs.iloc[-1] - obs.iloc[0]) / (obs.index[-1] - obs.index[0])
    assert c["C3_drift"] == pytest.approx(obs.iloc[-1] + g * (T - obs.index[-1]))
    assert meta["steps_to_target"] == T - obs.index[-1]


def test_damped_theil_sen():
    x = np.arange(6.0)
    assert V.theil_sen(x, 2 * x + 1) == pytest.approx(2.0)
    hs = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0], index=[10, 11, 12, 13, 14])
    c, _ = V.h_candidates(hs, pd.Series(dtype=float), pd.Series(dtype=float), 16, 2)
    assert c["C6_damped_theilsen"] == pytest.approx(5 + 1.0 * (0.8 + 0.64))


def test_training_pairs_respect_horizon():
    hs, f5, U = series()
    T, h = V.qk("2025-Q4"), 5
    _, meta = V.h_candidates(hs, f5, U, T, h)
    # training targets q must be <= T-h; with this series the ar1 model has 9 targets 2022-Q3..2024-Q3
    assert meta["C4_ridge_ar1_n_train"] == len([q for q in hs.index if V.qk("2022-Q3") <= q <= T - h])


def test_fd_candidates_cutoff_and_zero():
    rng = np.random.default_rng(1)
    qs = [V.qs(i) for i in range(V.qk("2021-Q1"), V.qk("2025-Q4") + 1)]
    rows = []
    for q in qs:
        F = rng.normal(5, 2, 5)
        for p, f in zip(["A", "B", "C", "D", "E"], F):
            rows.append({"province_code": p, "quarter": q, "F": f, "mean5": F.mean(), "D": f - F.mean()})
    comp = pd.DataFrame(rows)
    T, h = V.qk("2025-Q4"), 5
    a, _ = V.fd_candidates(comp, "D", T, h)
    c2 = comp.copy()
    c2.loc[c2["quarter"].map(V.qk) > T - h, ["F", "D", "mean5"]] = 999.0
    b, _ = V.fd_candidates(c2, "D", T, h)
    assert a.equals(b) and (a["D2_zero"] == 0).all() and "D4_ridge_shrink" in a


def test_selection_rule():
    base = pd.Series([2.0, 2.0, 2.0, 2.0], index=[1, 2, 3, 4])
    good = pd.Series([1.0, 1.0, 1.0, 1.0], index=[1, 2, 3, 4])
    lucky = pd.Series([3.0, 3.0, 3.0, -5.0 + 5.1], index=[1, 2, 3, 4])   # one great quarter, worse elsewhere
    assert V.rule_check(good, base)["passes"]
    r = V.rule_check(lucky, base)
    assert not r["passes"] and not r["cond2"]
    late_bad = pd.Series([0.1, 0.1, 2.5, 2.5], index=[1, 2, 3, 4])
    assert not V.rule_check(late_bad, base)["cond3"]


@pytest.mark.parametrize("path,write,want", [
    (guard.PROC / "cpi_full.parquet", False, "deny"),
    (guard.ROOT / "backend" / "data" / "processed" / "sws_hunger.parquet", False, "deny"),
    (guard.AL / "data" / "supplementary" / "collection_2026-10-09" / "provincial_food_cpi_yoy_2026H1_raw.csv", False, "deny"),
    (guard.PROC / "features_fused.parquet", False, "allow"),
    (guard.EXP / "runs" / "x.json", True, "allow"),
    (guard.AL / "experiments" / "2026-10-13_E17_Objectives_Evaluation" / "x.md", True, "deny"),
])
def test_guard(path, write, want):
    assert guard.decide(path, write) == want
