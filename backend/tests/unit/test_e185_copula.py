"""E185 (docs/e185/PROTOCOL.md): the Gaussian-copula generator keeps each class's ranges and class, copies the parent's
missing pattern, is reproducible and labelled; tuning against a base setting keeps the base unless a setting is clearly
better; the earlier generators are unchanged."""
import numpy as np
import pytest

from app.e168 import lgbm_only as E
from app.e178 import augment as A
from app.e179 import tuned as T
from app.e185 import candidate as C
from tests.unit.test_e178_augment import _frame
from tests.unit.test_e179_tuned import _job


def test_copula_rows_are_bounded_balanced_and_reproducible():
    d, an = _frame(150, seed=11)
    d.loc[::7, E.NEWS[0]] = np.nan
    cols = A.feature_columns(d)
    s1, sa, info = A.augment(d, an, "copula", 1.0, A.rng_for(17901, "j", 0, "copula", 1.0), cols, 17901, tag="E185")
    s2 = A.augment(d, an, "copula", 1.0, A.rng_for(17901, "j", 0, "copula", 1.0), cols, 17901, tag="E185")[0]
    assert s1.equals(s2) and s1["is_synthetic"].all() and (s1["scenario_id"] == "E185:copula:r1").all()
    hi = d["y_true"].values >= 0
    for cl in (True, False):
        m = (d["y_true"].values[s1["parent"].values] >= 0) == cl
        assert ((s1.loc[m, "y_true"] >= 0) == cl).all()                         # class kept
        for c in cols[:15]:
            v, r = s1.loc[m, c].dropna(), d.loc[hi == cl, c].dropna()
            assert v.empty or (v.min() >= r.min() - 1e-12 and v.max() <= r.max() + 1e-12), c
    par = s1["parent"].values
    assert (s1[E.NEWS[0]].isna().values == d[E.NEWS[0]].isna().values[par]).all()   # parent's missing pattern
    assert info["syn_high"] + info["syn_low"] == 150 and set(sa) == set(A.ANCH)


def test_earlier_generators_unchanged():
    assert A.GENERATORS[:2] == ("jitter", "smote")


def test_grid_is_the_protocols():
    assert C.SETTINGS[0] is None and C.SETTINGS[1] == C.E184_SETTING and len(C.SETTINGS) == 18
    assert sum(s is not None and s[0] == "copula" for s in C.SETTINGS) == 12


@pytest.fixture
def small_grid(monkeypatch):
    monkeypatch.setattr(E, "HPO", [(3, 10, 20.0, 150)])
    monkeypatch.setattr(E, "FS", {"GOV": E.FS["GOV"], "FULL": E.FS["FULL"]})


def test_base_setting_is_kept_unless_clearly_beaten(small_grid):
    tr, te, AN = _job()
    rows, sel, _, _ = T.run_proc_tuned(tr, te, AN, (17901,), "job", settings=[None, C.E184_SETTING, ("copula", 1.0, 1.0, .25, "uniform")],
                                       base_setting=C.E184_SETTING)
    s = sel[0]
    assert s["base"] == T.setting_name(C.E184_SETTING)
    assert (s["chosen"] == s["base"]) == (s["n_eligible"] == 0)
    assert s["chosen"] != "none"
