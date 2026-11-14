"""E182 (docs/e182/PROTOCOL.md): the fixed setting is the protocol's; without synthetic rows the procedure is E168's
run_proc exactly; synthetic rows are never scored; the candidate is the plain mean over the five seeds."""
from __future__ import annotations

import numpy as np
import pytest

from app.e168 import lgbm_only as E
from app.e178 import retrain as RT
from app.e179 import tuned as T
from app.e182 import candidate as C
from tests.unit.test_e179_tuned import _job


@pytest.fixture
def small_grid(monkeypatch):
    monkeypatch.setattr(E, "HPO", [(3, 10, 20.0, 150)])
    monkeypatch.setattr(E, "FS", {"GOV": E.FS["GOV"], "FULL": E.FS["FULL"]})


def test_setting_is_the_protocols():
    assert C.SETTING == ("jitter", 2.0, 1.0, 0.5, "boundary") and C.SETTING in T.SETTINGS


def test_e168_part_is_run_proc_and_candidate_is_the_seed_mean(small_grid, monkeypatch):
    tr, te, AN = _job()
    P, chosen, *_ = E.run_proc(tr, te, AN)
    seen = []
    orig = RT.LGBResAug.predict

    def spy(self, X):
        seen.append("is_synthetic" in X.columns and bool(X["is_synthetic"].any()))
        return orig(self, X)

    monkeypatch.setattr(RT.LGBResAug, "predict", spy)
    r = C.fixed(tr, te, AN, (17901, 17902), "job")
    for u, v in zip(P[chosen], r["E168"]):
        assert np.array_equal(np.asarray(u), np.asarray(v))
    singles = [C.fixed(tr, te, AN, (sd,), "job")[C.NAME] for sd in (17901, 17902)]
    for k in range(3):
        assert np.allclose(r[C.NAME][k], (np.asarray(singles[0][k]) + np.asarray(singles[1][k])) / 2)
    assert seen and not any(seen)
    assert np.all((r[C.NAME][1] >= 0) & (r[C.NAME][1] <= 1))
