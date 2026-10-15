"""E41 tests: study window, as-of masking (leakage), lead alignment, labels, M1 arithmetic, E40 consistency, freeze."""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "runner"))
import e41_lib as L  # noqa: E402

D = L.load()
ORIGINS = [L.qi(q) for q in ("2022-Q2", "2023-Q4", "2024-Q3", "2025-Q1", "2026-Q1", "2026-Q3")]


def perturb(d: L.Data, t: int, seed: int = 7) -> L.Data:
    """Change every value published on or after O(t); keep everything before it."""
    rng = np.random.default_rng(seed)
    m0, O = L.m0_of(t), L.origin(t)
    idx, yoy, sws = d.idx.copy(), d.yoy.copy(), d.sws.copy()
    prod, lfs, news = d.prod.copy(), d.lfs.copy(), d.news.copy()
    f = idx["ym"] > m0
    idx.loc[f, "index"] *= rng.uniform(0.7, 1.3, f.sum())
    f = yoy["ym"] > m0
    yoy.loc[f, "yoy"] += rng.normal(0, 5, f.sum())
    f = sws["published"] >= O
    sws.loc[f, "H"] += rng.normal(0, 8, f.sum())
    f = prod["q"] >= t
    prod.loc[f, "value"] *= rng.uniform(0.2, 3, f.sum())
    f = lfs["ym"] > (t - 1) // 4 * 12 + ((t - 1) % 4) * 3 + 2
    lfs.loc[f, "value"] += rng.normal(0, 3, f.sum())
    f = news["q"] > t
    news.loc[f, [c for c in news if c.startswith("hits_") or c == "news_n"]] *= 3
    return L.Data(idx, yoy, sws, prod, lfs, news)


def test_study_window_asserted():
    assert D.idx["ym"].min() >= L.FIRST_YM and D.yoy["ym"].min() >= L.FIRST_YM
    assert D.sws["q"].min() >= L.FIRST_Q and D.prod["q"].min() >= L.FIRST_Q and D.news["q"].min() >= L.FIRST_Q
    with pytest.raises(L.WindowViolation):
        L._assert_window("x", ym=np.array([L.FIRST_YM - 1]))


def test_lead2_alignment():
    t = L.qi("2026-Q3")
    assert str(L.origin(t).date()) == "2026-10-01"
    assert L.ym_s(L.m0_of(t)) == "2026-08"                      # September CPI is released after the origin
    assert [L.ym_s(m) for m in L.target_months(t, 2)] == ["2027-01", "2027-02", "2027-03"]
    assert [L.ym_s(m) for m in L.target_months(t, 1)] == ["2026-10", "2026-11", "2026-12"]
    c = D.cut(t)
    assert c.idx["ym"].max() == L.m0_of(t) and (c.sws["published"] < L.origin(t)).all()
    assert c.prod["q"].max() <= t - 1 and c.news["q"].max() <= t


@pytest.mark.parametrize("t", ORIGINS)
def test_features_ignore_post_origin_data(t):
    a = L.features(D.cut(t), t)
    b = L.features(perturb(D, t).cut(t), t)
    pd.testing.assert_frame_equal(a, b)


@pytest.mark.parametrize("t", ORIGINS[:-1])
def test_m1_and_probability_ignore_post_origin_data(t):
    o = list(range(L.qi("2021-Q3"), t + 1))
    a = L.m1_forecasts(D, o, 2)
    b = L.m1_forecasts(perturb(D, t), o, 2)
    pd.testing.assert_frame_equal(a[a["t"] == t].reset_index(drop=True), b[b["t"] == t].reset_index(drop=True))


@pytest.mark.parametrize("t", [L.qi("2025-Q1"), L.qi("2026-Q1")])
def test_ml_forecasts_ignore_post_origin_data(t):
    o = list(range(L.qi("2021-Q3"), t + 1))
    out = []
    for d in (D, perturb(D, t)):
        X = L.feature_table(d, o)
        tr = L.training_pairs(X, d.cut(t), t, 2)
        te = X[X["t"] == t]
        assert tr["q"].max() <= t - 1
        m = L.fit_lgbm(tr, L.FEATURES)
        out.append((L.fit_predict_lr(tr, te), m.predict_proba(te[L.FEATURES].astype(float))[:, 1]))
    np.testing.assert_array_equal(out[0][0], out[1][0])
    np.testing.assert_array_equal(out[0][1], out[1][1])


@pytest.mark.parametrize("t", [L.qi("2023-Q2"), L.qi("2024-Q3")])
def test_e40_simulation_ignores_post_origin_data(t):
    assert L.e40_simulate(D.cut(t), t, n=2000) == L.e40_simulate(perturb(D, t).cut(t), t, n=2000)


def test_fpp_label_definition():
    lab = L.fpp_labels(D)
    assert ((lab["F"] > 4.0) == (lab["y"] == 1)).all()
    y = D.yoy[D.yoy["commodity"] == "food"].assign(q=lambda x: x["ym"].map(L.q_of_ym))
    full = y.groupby(["province_code", "q"]).size()
    assert set(lab.set_index(["province_code", "q"]).index) == set(full[full == 3].index)


def test_variance_factor_and_probability_rule():
    assert math.isclose(L.var_factor([5, 6, 7]), 50 / 9) and math.isclose(L.var_factor([2, 3, 4]), 23 / 9)
    m = L.m1_forecasts(D, list(range(L.qi("2021-Q3"), L.qi("2023-Q1"))), 2).dropna(subset=["F_hat"])
    assert ((m["p"] > 0.5) == (m["F_hat"] > 4.0)).all()


def test_m1_exact_on_constant_growth():
    """With a constant monthly growth the projection reproduces the true YoY exactly."""
    g = 0.004
    ym = np.arange(L.FIRST_YM, L.FIRST_YM + 30)
    idx = pd.DataFrame({"province_code": "PH040100000", "commodity": "food", "ym": ym, "index": 100 * np.exp(g * (ym - ym[0]))})
    d = L.Data(idx, D.yoy.iloc[:0], D.sws, D.prod, D.lfs, D.news)
    t = L.qi("2022-Q3")
    r = L.m1_point(d.cut(t), t, 2, "PH040100000")
    assert math.isclose(r["F_hat"], 100 * (math.exp(12 * g) - 1), rel_tol=1e-9)
    assert r["s_theory"] < 1e-9


def test_e40_rule_reproduces_frozen_dev_labels():
    dev_end = L.qi("2025-Q1")
    mine = L.e40_labels(D.cut(dev_end + 1))
    mine = mine[mine["q"] <= dev_end].set_index(["province_code", "q"])["y"]
    ref = pd.read_csv(L.E40 / "label_primary.csv", dtype={"province_code": str})
    ref = ref[ref["quarter"].map(L.qi) <= dev_end].dropna(subset=["y_high"])
    ref = ref.assign(q=ref["quarter"].map(L.qi)).set_index(["province_code", "q"])["y_high"].astype(int)
    common = mine.index.intersection(ref.index)
    assert len(common) >= 70
    assert (mine.loc[common] == ref.loc[common]).all()


def test_prospective_freeze_intact():
    fz = L.E41 / "frozen" / "E41_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        pytest.skip("not frozen yet")
    want = (fz.parent / "E41_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    assert hashlib.sha256(fz.read_bytes()).hexdigest() == want
    r = json.loads(fz.read_text())
    assert r["origin"] == "2026-10-01" and r["lead2_target"] == "2027-Q1" and r["cpi_months_used_through"] == "2026-08"
    for v in r["provinces"].values():
        p = v["lead2_fpp_probability"]
        assert 0 <= p <= 1 and v["lead2_band"] == ("High" if p >= 2 / 3 else "Watch" if p >= 1 / 3 else "Low")
