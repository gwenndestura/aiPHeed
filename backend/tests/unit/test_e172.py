"""E172 (exploratory) unit tests: the R0 single-seed variant is E168's LightGBM exactly; variants differ only as the protocol says."""
import numpy as np
import pandas as pd

from app.e151 import prov as Pv
from app.e171 import candidates as C171
from app.e172 import lgbm_only as E


def _d(n=120, seed=0):
    r = np.random.default_rng(seed)
    return pd.DataFrame({"x1": r.normal(size=n), "x2": r.normal(size=n), "e": r.normal(size=n), "se_true": 0.3,
                         "region": r.integers(0, 6, n).astype(str), "gap_q": r.integers(1, 9, n), "lead": r.integers(1, 4, n)})


def test_r0_pooled_single_seed_reproduces_e168_lightgbm():
    d = _d()
    a, b = Pv.Res2(["x1", "x2"]).fit(d), E.VARIANTS["GR0P"](["x1", "x2"]).fit(d)
    assert a.n_ == b.n_ and np.abs(a.predict(d) - b.predict(d)).max() == 0.0


def test_bagged_variant_really_uses_five_seeds_and_differs():
    d = _d()
    m = E.VARIANTS["GR0PB"](["x1", "x2"]).fit(d)
    assert len(m.ms_) == 5 and np.abs(m.predict(d) - E.VARIANTS["GR0P"](["x1", "x2"]).fit(d).predict(d)).max() > 0


def test_lead_exact_trains_only_on_its_own_lead():
    d = _d(300)
    C171.LEAD_NOW["v"] = 2
    m = E.VARIANTS["GR0X"](["x1", "x2"]).fit(d)
    assert m.n_ in (100, 300, 600)
    full = E.VARIANTS["GR0P"](["x1", "x2"]).fit(d)
    assert np.abs(m.predict(d) - full.predict(d)).max() > 0


def test_menu_is_the_protocol_menu_and_lightgbm_only():
    m = E.stage2("OH")
    assert len(E.STAGE1) == 8 and len(m) == 32 and all(l.startswith("G") for _, l, _ in m)
    assert {f for _, _, f in m} == {"GOV", "FULL", "GOV_S"}
    assert all(issubclass(E.VARIANTS[l], E.LGB) for _, l, _ in m)


def test_workers_register_variants():
    from joblib import Parallel, delayed

    def probe():
        E._install()
        from app.e164 import auto as U
        return U.LEARNERS["GR0PB"].SEEDS, U.LEARNERS["LGBM"].__name__
    assert all(x == ((151, 152, 153, 154, 155), "Res2") for x in Parallel(n_jobs=2)(delayed(probe)() for _ in range(2)))
