"""E178 Part B (docs/e178/PROTOCOL.md): synthetic training rows are labelled, made only from the rows they are given,
balanced as stated, reproducible, kept out of every scored set, and the augmented procedure without synthetic rows is
E168's run_proc exactly."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.e168 import lgbm_only as E
from app.e178 import augment as A
from app.e178 import retrain as RT


def _frame(n=80, seed=0, high_share=0.3):
    r = np.random.default_rng(seed)
    cols = sorted({c for v in E.FS.values() for c in v})
    d = pd.DataFrame(r.normal(0, 1, (n, len(cols))), columns=cols)
    d["lead"] = r.integers(1, 3, n)
    d["gap_q"] = r.integers(8, 30, n)
    for c in E.NEWS[:5]:                                 # zero-inflated news-like columns
        d[c] = np.where(r.random(n) < .7, 0.0, d[c])
    y = r.normal(-0.3, 0.8, n)
    y[: int(high_share * n)] = np.abs(y[: int(high_share * n)]) + 0.05
    y[int(high_share * n):] = -np.abs(y[int(high_share * n):]) - 0.05
    d["y_true"], d["se_true"] = y, r.uniform(.05, .2, n)
    d["q_true"] = 1 / (1 + np.exp(-y / d["se_true"]))
    d["region"] = r.choice([f"R{i}" for i in range(8)], n)
    d["key"] = [f"P{i % 30}" for i in range(n)]
    an = {a: y + r.normal(0, .3, n) for a in A.ANCH}
    return d, an


def test_allocation_balances_then_follows_shares():
    for n1, n0, n in [(10, 30, 10), (10, 30, 30), (10, 30, 100), (30, 10, 25), (20, 20, 10), (0, 15, 5)]:
        h = np.r_[np.ones(n1, bool), np.zeros(n0, bool)]
        a = A.allocate(h, n)
        assert a[0] + a[1] == n
        if n1 and n0 and n <= abs(n1 - n0):
            assert a[1 if n1 < n0 else 0] == n                   # all to the minority until parity
        if n1 and n0:                                             # the minority's share never falls
            mi, nmi = (1, n1) if n1 < n0 else (0, n0)
            assert (nmi + a[mi]) / (n1 + n0 + n) >= nmi / (n1 + n0) - 1e-12
        if n1 and n0 and n > abs(n1 - n0):                        # parity first, then the real shares
            gap = abs(n1 - n0)
            rest = n - gap
            assert a[1] == (gap if n1 < n0 else 0) + round(rest * n1 / (n1 + n0))


@pytest.mark.parametrize("gen", A.GENERATORS)
def test_synthetic_rows_are_labelled_bounded_and_from_the_given_rows(gen):
    d, an = _frame()
    cols = A.feature_columns(d)
    syn, sa, info = A.augment(d, an, gen, 0.5, A.rng_for(17801, "job", 0, gen, .5), cols, 17801)
    assert len(syn) == 40 and syn["is_synthetic"].all() and (syn["scenario_id"] == f"B:{gen}:r0.5").all()
    assert (syn["generator_seed"] == 17801).all()
    assert syn["parent"].between(0, len(d) - 1).all()
    assert set(syn["region"]) <= set(d["region"]) and set(sa) == set(A.ANCH)
    for c in cols:
        v = syn[c].dropna()
        assert ((v >= d[c].min() - 1e-12) & (v <= d[c].max() + 1e-12)).all(), c
    assert info["syn_high"] > info["syn_low"]                     # the minority class (HIGH) is filled first
    if gen == "smote":                                            # interpolation within class keeps the class
        assert ((syn["y_true"].values >= 0) == (d["y_true"].values[syn["parent"]] >= 0)).all()
    zero_inflated = [c for c in E.NEWS[:5] if c in cols]
    # jitter copies zero-inflated columns from the parent; smote and copula draw within the bounds checked above
    assert all(set(syn[c].dropna().unique()) <= set(d[c].unique()) or gen != "jitter" for c in zero_inflated)


@pytest.mark.parametrize("gen", A.GENERATORS)
def test_same_seed_same_rows(gen):
    d, an = _frame()
    cols = A.feature_columns(d)
    a = A.augment(d, an, gen, 1.0, A.rng_for(17801, "j", 1, gen, 1.0), cols, 17801)[0]
    b = A.augment(d, an, gen, 1.0, A.rng_for(17801, "j", 1, gen, 1.0), cols, 17801)[0]
    c = A.augment(d, an, gen, 1.0, A.rng_for(17802, "j", 1, gen, 1.0), cols, 17802)[0]
    assert a.equals(b) and not a[cols].equals(c[cols])


def test_augmented_learner_matches_lgbres():
    d, _ = _frame()
    d = d.assign(e=d["y_true"] * .3)
    m0 = E.LGBRes(E.FS["GOV"], 3, 10, 20.0, 150, True).fit(d)
    m1 = RT.LGBResAug(E.FS["GOV"], 3, 10, 20.0, 150, True).fit(d, d.iloc[:0])
    assert np.array_equal(m0.predict(d), m1.predict(d))
    syn = d.sample(20, random_state=1).assign(is_synthetic=True)
    m2 = RT.LGBResAug(E.FS["GOV"], 3, 10, 20.0, 150, True).fit(d, syn)
    assert m2.use_ == m0.use_                                     # filter and pruning from the real rows only
    assert m2.m_.get_params() == m0.m_.get_params()               # E168's LightGBM settings, unchanged


@pytest.fixture
def small_grid(monkeypatch):
    monkeypatch.setattr(E, "HPO", [(3, 10, 20.0, 150)])
    monkeypatch.setattr(E, "FS", {"GOV": E.FS["GOV"], "FULL": E.FS["FULL"]})


def _job(n_tr=90, n_te=12):
    tr, an = _frame(n_tr, seed=3)
    te, an_te = _frame(n_te, seed=4)
    AN = {a: (an[a], an_te[a]) for a in A.ANCH}
    return tr, te.drop(columns=["y_true", "se_true", "q_true"]), AN


def test_without_synthetic_rows_it_is_e168(small_grid):
    tr, te, AN = _job()
    P, chosen, tag, _, inner, nf = E.run_proc(tr, te, AN)
    arms, bal = RT.run_proc_aug(tr, te, AN, [], 17801, "job")
    a = arms[None]
    assert a["chosen"] == chosen and a["tag"] == tag and a["inner"] == inner and a["n_features"] == nf and bal == []
    for k in P:
        for u, v in zip(P[k], a["P"][k]):
            assert np.array_equal(np.asarray(u), np.asarray(v))


def test_synthetic_rows_are_never_scored(small_grid, monkeypatch):
    tr, te, AN = _job()
    seen = []
    orig = RT.LGBResAug.predict

    def spy(self, X):
        seen.append(("is_synthetic" in X.columns and X["is_synthetic"].any(), len(X)))
        return orig(self, X)

    monkeypatch.setattr(RT.LGBResAug, "predict", spy)
    arms, bal = RT.run_proc_aug(tr, te, AN, [("jitter", .5), ("smote", 1.0)], 17801, "job")
    assert seen and not any(s for s, _ in seen)                   # predictions only on real held-out rows and real outer rows
    assert all(n in (len(te),) or n < len(tr) for _, n in seen)
    for key, a in arms.items():
        mu, p, half = a["P"][a["chosen"]]
        assert len(mu) == len(te) and np.all((p >= 0) & (p <= 1))
        assert "aug=" in a["tag"]
    b = pd.DataFrame(bal)
    assert set(b["fold"]) == {"0", "1", "2", "3", "4", "final"}
    assert (b["n_syn"] == (b["ratio"] * b["n_real"]).round().astype(int)).all()


def test_outer_rows_must_be_real(small_grid):
    tr, te, AN = _job()
    with pytest.raises(AssertionError):
        RT.run_proc_aug(tr, te.assign(is_synthetic=False), AN, [], 17801, "job")


def test_fidelity_reports_every_check():
    d, an = _frame(120, seed=5)
    m = A.fidelity(d, an, "jitter", 17801, "job")
    assert set(m["checks"]) == {"ks", "wasserstein", "correlation", "tstr", "not_copies"}
    assert m["exact_copies"] == 0 and 0 <= m["copy_share"] <= 1 and m["tstr_ratio"] > 0
