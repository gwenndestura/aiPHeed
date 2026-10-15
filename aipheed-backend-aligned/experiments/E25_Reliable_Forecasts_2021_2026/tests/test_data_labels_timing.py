"""Data, labels, window, masking, publication timing and leakage (real authorized inputs, through the guard)."""
import numpy as np
import pandas as pd
import pytest

import _paths  # noqa: F401
import e25lib as E

qk = E.qk


@pytest.fixture(scope="module")
def data():
    rounds = E.load_rounds()
    comp, c26, D = E.load_components()
    mon, Dnow, cmp = E.load_monthly(c26, comp)
    X, gov, masked, const = E.load_features(rounds[rounds["definition_A"]])
    return {"rounds": rounds, "comp": comp, "D": D, "mon": mon, "Dnow": Dnow, "X": X, "masked": masked, "cmp": cmp}


def test_window_no_pre2021_and_no_post_2026Q2(data):
    for q in list(data["rounds"]["quarter"]) + list(data["D"]["quarter"]) + list(data["X"]["quarter"]):
        assert qk("2021-Q1") <= qk(q) <= qk("2026-Q2")
    assert data["mon"]["ym"].min() >= 2021 * 12 and data["mon"]["ym"].max() <= 2026 * 12 + 5
    assert all(w["outside_window"] == 0 for w in E.WINDOW_LOG)


def test_D_is_mean_zero_per_quarter_and_S1_is_H_plus_2D(data):
    g = data["D"].groupby("quarter")["D"].sum().abs()
    assert (g < 1e-9).all()
    T = E.Target("T1", "A", data["rounds"], data["D"])
    v = T.V.merge(data["D"], on=["province_code", "quarter"])
    H = v["quarter"].map(T.H)
    assert np.allclose(v["v"], H + 2 * v["D"])
    c = data["comp"].dropna(subset=["S1"]).merge(T.V, on=["province_code", "quarter"])
    assert np.allclose(c["S1"], c["v"])                       # E12 approved S1 reproduced exactly


def test_readings_label_counts(data):
    A = E.Target("T1", "A", data["rounds"], data["D"])
    B = E.Target("T1", "B", data["rounds"], data["D"])
    C = E.Target("T1", "C", data["rounds"], data["D"])
    assert set(B.V["quarter"]) - set(A.V["quarter"]) == {"2025-Q2", "2025-Q3"}
    assert set(C.V["quarter"]) == set(B.V["quarter"])
    assert C.H["2025-Q1"] != A.H["2025-Q1"]                   # reading C moves one round into 2025-Q1


def test_masking_removes_2020_information(data):
    X = data["X"]
    first = X[X["quarter"] == "2021-Q1"]
    for c in [c for c in X.columns if c.endswith("_lag1") or c.endswith("_accel")]:
        assert first[c].isna().all(), c
    assert X[X["quarter"].isin(["2021-Q1", "2021-Q2"])]["FSSI_lag2"].isna().all()
    assert X[X["quarter"] == "2021-Q1"]["cpi_dev"].isna().all()   # needs >= 2 in-window prior quarters


def test_2026_rounds_unusable_at_every_backtest_origin(data):
    r = data["rounds"]
    r26 = r[r["quarter"] >= "2026-Q1"]
    assert r26["published"].isna().all() and (r26["published_eff"] > E.origin(qk("2026-Q2"))).all()
    for t in range(qk("2023-Q1"), qk("2026-Q2") + 1):
        times, ys, _ = E.h_inputs(r, E.origin(t), False)
        assert times.max() <= qk("2025-Q4")


def test_label_publication_rule_and_training_pairs(data):
    T = E.Target("T1", "A", data["rounds"], data["D"])
    for t in range(qk("2023-Q3"), qk("2026-Q1") + 1):
        tau = T.tau(t)
        for k in (1, 2, 3):
            tr = E.training_pairs(T, t, k, tau, {})
            if tr.empty:
                continue
            assert tr["target_q"].max() <= t - 1
            for q in tr["target_quarter"].unique():
                maxpub = T.ru[T.ru["quarter"] == q]["published_eff"].max()
                assert maxpub < E.origin(t)


def test_dnow_available_before_origin_and_matches_quarter(data):
    # Dnow(t) uses months 1-2 of quarter t, released before O(t) (first day of t+1)
    D, N = data["D"], data["Dnow"]
    m = D.merge(N, on=["province_code", "quarter"])
    assert np.corrcoef(m["D"], m["Dnow"])[0, 1] > 0.8          # same scale and sign as the quarterly D
    assert data["cmp"]["max_abs_dD"] < 0.05                   # index-derived D vs approved E12 D


def test_features_use_quarter_t_news_and_t_minus_1_government(data):
    X = data["X"]
    # government columns on row t carry quarter t-1 values: row 2021-Q1 has none (2020-Q4 not loaded)
    assert X[X["quarter"] == "2021-Q1"]["unemployment_rate"].isna().all()
    assert X[X["quarter"] == "2021-Q2"]["unemployment_rate"].notna().all()
