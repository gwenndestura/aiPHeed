"""E179 (docs/e179/PROTOCOL.md): with no augmentation E179 is E168's run_proc exactly; synthetic rows are never scored;
the one-standard-error rule picks "none" unless a setting is clearly better on the inner folds."""
from __future__ import annotations

import numpy as np
import pytest

from app.e168 import lgbm_only as E
from app.e178 import retrain as RT
from app.e179 import tuned as T
from tests.unit.test_e178_augment import _job as _job178


def _job():
    tr, te, AN = _job178()
    return tr, te.assign(survey="ENNS2021"), AN


@pytest.fixture
def small_grid(monkeypatch):
    monkeypatch.setattr(E, "HPO", [(3, 10, 20.0, 150)])
    monkeypatch.setattr(E, "FS", {"GOV": E.FS["GOV"], "FULL": E.FS["FULL"]})


def test_grid_is_the_protocols():
    assert T.SETTINGS[0] is None and len(T.SETTINGS) == 129
    assert sum(s[0] == "jitter" for s in T.SETTINGS[1:]) == 96 and sum(s[0] == "smote" for s in T.SETTINGS[1:]) == 32


def test_without_augmentation_it_is_e168(small_grid):
    tr, te, AN = _job()
    P, chosen, tag, _, inner, nf = E.run_proc(tr, te, AN)
    rows, sel, bal, _ = T.run_proc_tuned(tr, te, AN, (17901,), "job", settings=[None])
    for arm in ("E168_rerun", "E179"):
        o = next(r for r in rows if r["arm"].iloc[0] == arm)
        assert o["cfg"].iloc[0] == tag
        for k in P:
            assert np.array_equal(o[f"p_{k}"].values, np.asarray(P[k][1])) and np.array_equal(o[f"mu_{k}"].values, np.asarray(P[k][0]))
    assert sel[0]["chosen"] == "none" and bal == []


def test_synthetic_rows_never_scored_and_rule_is_consistent(small_grid, monkeypatch):
    tr, te, AN = _job()
    seen = []
    orig = RT.LGBResAug.predict

    def spy(self, X):
        seen.append("is_synthetic" in X.columns and bool(X["is_synthetic"].any()))
        return orig(self, X)

    monkeypatch.setattr(RT.LGBResAug, "predict", spy)
    settings = [None, ("jitter", .5, .4, .25, "uniform"), ("jitter", 1.0, 1.0, .5, "boundary"), ("smote", 2.0, .7, .25, "boundary")]
    rows, sel, bal, _ = T.run_proc_tuned(tr, te, AN, (17901, 17902), "job", settings=settings)
    assert seen and not any(seen)
    for s in sel:
        assert (s["chosen"] == "none") == (s["n_eligible"] == 0)
        if s["chosen"] != "none":
            assert s["gain_mean"] + s["gain_se"] < 0 and s["sse_chosen"] < s["sse_none"]
    for o in rows:
        assert np.all((o["p"] >= 0) & (o["p"] <= 1)) and len(o) == len(te)


def test_boundary_focus_draws_parents_near_the_line():
    from app.e178 import augment as A
    from tests.unit.test_e178_augment import _frame
    d, an = _frame(200, seed=9)
    cols = A.feature_columns(d)
    u = A.augment(d, an, "jitter", 1.0, A.rng_for(1, "j", 0, "jitter", 1.0), cols, 1, focus="uniform")[0]
    b = A.augment(d, an, "jitter", 1.0, A.rng_for(1, "j", 0, "jitter", 1.0), cols, 1, focus="boundary")[0]
    py = lambda s: np.abs(d["y_true"].values[s["parent"].values]).mean()
    assert py(b) < py(u)
    assert (b["scenario_id"].str.endswith(":boundary")).all()
