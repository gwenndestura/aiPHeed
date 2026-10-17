"""E46 I7 tests: addendum frozen, embargoed forward folds, no residual intercept, fixed decision rule, five triggers +
policy in the residual inputs, and no dependence on anything published after the origin."""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "runner"))
sys.path.insert(0, str(HERE.parents[1] / "E41_Lead2_Audit" / "tests"))
sys.path.insert(0, str(HERE.parents[1] / "E43_Five_Trigger_Risk" / "tests"))
import e46_i7 as I7  # noqa: E402
from test_e41 import perturb  # noqa: E402
from test_e43 import perturb_extra  # noqa: E402

M, L, K, P2, pd = I7.M, I7.L, I7.K, I7.P2, I7.pd
EV = M.load_events()
FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}


def test_addendum_frozen():
    want = (HERE.parent / "runner" / "ADDENDUM_I7_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((HERE.parent / "ADDENDUM_I7.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_forward_folds_are_embargoed():
    qs = list(range(100, 116))
    f = I7.folds(qs, "forward")
    assert 0 < len(f) <= I7.N_FORWARD
    for q, fit in f:
        assert fit and max(fit) <= q - 3 and len(fit) >= I7.MIN_EARLIER
    assert all(q not in fit for q, fit in I7.folds(qs, "loqo"))


def test_residual_has_no_intercept_and_grid_contains_base_only():
    X = pd.DataFrame({"a": np.arange(20.0), "b": np.r_[np.ones(10), np.zeros(10)]})
    m = I7.RidgeNI(["a", "b"], 1.0).fit(X, 5.0 + X["a"])
    assert m.m.intercept_ == 0.0
    assert any(c["alpha"] is None for c in I7.grid()) and all(c["alpha"] is None for c in I7.grid(True))


def test_i7_ignores_post_origin_data_keeps_five_triggers_and_fixed_rule():
    t = L.qi("2025-Q1")
    o = list(range(L.qi("2021-Q3"), t + 1))
    outs = []
    for d, x in ((L.load(), K.load_extra()), (perturb(L.load(), t), perturb_extra(K.load_extra(), t))):
        X = M.features(d, x, o, EV)
        f = I7.forecast(d, X, P2.bases(d, o), t, n_jobs=1)
        assert f["threshold"] == 0.5
        assert FIVE <= {g for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g] if c in f["pcols"]}
        assert set(M.POLICY) <= set(f["pcols"])
        outs.append((list(np.round(f["p"], 12)), f["food_cfg"], f["gap_cfg"], round(f["rho"], 12)))
    assert outs[0] == outs[1]
