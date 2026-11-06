"""E166 temperature shrink, synthetic data only (no outcomes)."""
import numpy as np
import pandas as pd

from app.e166 import temperature as T


def test_classes_identical_for_any_lambda():
    rng = np.random.default_rng(1)
    mu, sd = rng.normal(0, 1.5, 2000), np.full(2000, 0.6)
    base = mu >= 0
    for lam in (1e-6, 0.3, 0.51, 0.73, 0.88, 1.0):
        s, p, cls = T.apply_lambda(mu, sd, lam)
        assert (cls == base).all()
        assert ((s >= 0) == base).all()
        assert ((p >= .5) == base).all()


def test_estimator_recovers_known_slope():
    rng = np.random.default_rng(2)
    s = rng.normal(0, 1, 400)
    w = rng.uniform(0.5, 5, 400)
    y = 0.1 + 0.62 * s + rng.normal(0, 0.05, 400) / np.sqrt(w)
    lam, var = T.wls_slope(s, y, w)
    assert abs(lam - 0.62) < 0.02 and 0 < var < 1e-3


def test_too_few_pairs_gives_no_estimate():
    lam, var = T.wls_slope(np.arange(10.0), np.arange(10.0), np.ones(10))
    assert np.isnan(lam) and np.isnan(var)


def test_combine_inverse_variance_clip_and_fallback():
    lam, src = T.combine(0.6, 0.01, 0.9, 0.04)
    assert abs(lam - (0.6 / 0.01 + 0.9 / 0.04) / (1 / 0.01 + 1 / 0.04)) < 1e-12 and src == "a+b"
    assert T.combine(float("nan"), float("nan"), 0.1, 0.01) == (0.3, "b")
    assert T.combine(1.4, 0.01, float("nan"), float("nan")) == (1.0, "a")
    assert T.combine(float("nan"), float("nan"), float("nan"), float("nan")) == (1.0, "none")


def _pairs(n_before=40, n_after=40, slope_before=0.7, seed=3):
    rng = np.random.default_rng(seed)
    cut = pd.Timestamp("2018-04-01")
    rows = []
    for k in range(n_before + n_after):
        before = k < n_before
        iss = cut - pd.Timedelta(days=400 - k) if before else cut + pd.Timedelta(days=k)
        pub = cut - pd.Timedelta(days=30 + (n_before - k)) if before else cut + pd.Timedelta(days=k)
        f = rng.normal(-1.5, 0.4)
        rows.append({"issue_start": iss, "published": pub, "lead": 1, "f": f, "y": 0.0 + slope_before * f + rng.normal(0, 0.02)})
    return pd.DataFrame(rows), cut


def test_lambda_never_uses_data_released_on_or_after_issue_date():
    P, cut = _pairs()
    lam0 = T.lam_sws(P, cut, 1)
    P2 = P.copy()
    late = P2["published"] >= cut
    P2.loc[late, "y"] = 1e6                                           # poison everything released on/after the issue date
    P2.loc[late, "f"] = -1e6
    assert T.lam_sws(P2, cut, 1) == lam0
    assert abs(lam0[0] - 0.7) < 0.05 and lam0[2] == 40


def test_pair_published_exactly_on_issue_date_is_excluded():
    P, cut = _pairs()
    P.loc[0, "published"] = cut
    assert len(T.sws_pairs_for(P, cut, 1)) == 39


def test_forward_splits_only_fit_on_earlier_rounds():
    sp = T.forward_splits(["ENNS2019", "FNRI2015", "ENNS2018", "FNRI2015"])
    assert sp == [(["FNRI2015"], "ENNS2018"), (["FNRI2015", "ENNS2018"], "ENNS2019")]
    for fit, held in sp:
        assert all(int(r[-4:]) < int(held[-4:]) for r in fit)
    assert T.forward_splits(["FNRI2015"]) == []


def test_sws_pools_leads_only_when_same_lead_pairs_are_too_few():
    P, cut = _pairs()
    P.loc[P.index[:25], "lead"] = 2                                    # only 15 lead-1 pairs before the cut
    l1, _, n1, k1 = T.lam_sws(P, cut, 1)
    assert k1 == "pooled" and n1 == 15 and np.isnan(l1)               # leads <= 1 pooled is still 15: no estimate
    l2, _, n2, k2 = T.lam_sws(P, cut, 2)
    assert k2 == "same" and n2 == 25                                   # 25 same-lead pairs at lead 2
    P.loc[P.index[:10], "lead"] = 3
    l3, _, n3, k3 = T.lam_sws(P, cut, 3)
    assert k3 == "pooled" and n3 == 40 and abs(l3 - 0.7) < 0.05       # 10 same-lead pairs -> pooled leads <= 3


def test_corrupt_sws_only_touches_readings_published_on_or_after_cut():
    s = pd.DataFrame({"hunger": [10.0, 11.0, 12.0, 13.0], "published": pd.to_datetime(["2017-12-01", "2018-03-31", "2018-04-01", "2018-06-01"])})
    c = T.corrupt_sws(s, pd.Timestamp("2018-04-01"))
    assert (c["hunger"].iloc[:2] == s["hunger"].iloc[:2]).all()
    assert (c["hunger"].iloc[2:] != s["hunger"].iloc[2:]).all()
