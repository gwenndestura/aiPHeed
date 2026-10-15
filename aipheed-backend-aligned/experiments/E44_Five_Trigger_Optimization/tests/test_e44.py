"""E44 validity tests (gate A0): five-trigger presence in training and inference, as-of masking, alignment, freeze."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "runner"))
sys.path.insert(0, str(HERE.parents[1] / "E41_Lead2_Audit" / "tests"))
sys.path.insert(0, str(HERE.parents[1] / "E43_Five_Trigger_Risk" / "tests"))
import e44_components as P2  # noqa: E402
from test_e41 import perturb  # noqa: E402
from test_e43 import perturb_extra  # noqa: E402

C, K, L = P2.C, P2.K, P2.L
D, XR = L.load(), K.load_extra()
FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}
O = list(range(L.qi("2021-Q3"), L.qi("2026-Q3") + 1))
X = P2.features(D, XR, O)
B = P2.bases(D, O)


def test_protocol_frozen():
    want = (HERE.parent / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((HERE.parent / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_every_candidate_feature_set_covers_the_five_triggers():
    for cols in C.FEATURE_SETS.values():
        assert C.covers_five(cols)
    price = {g for g in P2.ALL_GROUPS if P2.PRICE_GROUPS[g]}
    hunger = {g for g in P2.ALL_GROUPS if g in P2.HUNGER_GROUPS}
    assert FIVE <= price and FIVE <= hunger
    assert "ur_last" not in C.F5 and "ofw_cash_remit_usd_bn" not in C.F5            # levels excluded (time proxies)


@pytest.mark.parametrize("t", [L.qi("2024-Q2"), L.qi("2026-Q1")])
def test_new_features_ignore_post_origin_data(t):
    o = list(range(L.qi("2021-Q3"), t + 1))
    a = P2.features(D, XR, o)
    b = P2.features(perturb(D, t), perturb_extra(XR, t), o)
    pd.testing.assert_frame_equal(a[a["t"] == t].reset_index(drop=True), b[b["t"] == t].reset_index(drop=True))


@pytest.mark.parametrize("supp", [False, True])
def test_component_forecast_ignores_post_origin_data(supp):
    t = L.qi("2025-Q1")
    o = list(range(L.qi("2021-Q3"), t + 1))
    outs = []
    for d, x in ((D, XR), (perturb(D, t), perturb_extra(XR, t))):
        Xd = P2.features(d, x, o)
        f = P2.forecast(d, Xd, P2.bases(d, o), t, supplementary=supp, n_jobs=1)
        outs.append((list(np.round(f["p"], 12)), f["threshold"], f["price_cfg"], f["hunger_alpha"]))
    assert outs[0] == outs[1]


def test_nested_classifier_selection_ignores_post_origin_data():
    t = L.qi("2025-Q1")
    o = list(range(L.qi("2021-Q3"), t + 1))
    cfgs = [c for c in C.grid(C.FEATURE_SETS) if c["window"] == "expanding" and c["features"] != "F5"][:12]
    outs = []
    for d, x in ((D, XR), (perturb(D, t), perturb_extra(XR, t))):
        Xd = P2.features(d, x, o)
        tr = K.training_pairs(Xd, d, t)
        te = Xd[Xd["t"] == t]
        r = C.select_and_predict(tr, te, cfgs, C.FEATURE_SETS, n_jobs=1)
        outs.append((str(r["config"]), r["threshold"], list(np.round(r["p"], 12))))
    assert outs[0] == outs[1]


def test_five_triggers_reach_training_and_inference():
    t = L.qi("2026-Q1")
    f = P2.forecast(D, X, B, t, n_jobs=1)
    model_cols = f["price_model"].cols
    assert FIVE <= {g for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g] if c in model_cols}
    contrib = f["price_model"].contributions(f["te"])
    assert FIVE <= {g for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g] if c in contrib.columns}
    assert FIVE <= {g for g in P2.HUNGER_GROUPS for c in P2.HUNGER_GROUPS[g] if c in f["hcols"]}
    assert f["te"][model_cols].shape[1] == len(model_cols)                         # inference receives every column


def test_supplementary_rounds_never_become_labels():
    t = L.qi("2026-Q1")
    hs = P2.h_series(D, t, supplementary=True)
    assert L.qi("2025-Q2") in hs.index and L.qi("2025-Q3") in hs.index
    labs = set(K.available_labels(D, t)["q"])
    assert L.qi("2025-Q2") not in labs and L.qi("2025-Q3") not in labs


def test_lead2_alignment():
    t = L.qi("2026-Q3")
    assert str(L.origin(t).date()) == "2026-10-01" and L.qs(t + 2) == "2027-Q1"
    tr = K.training_pairs(X, D, t)
    assert tr["q"].max() <= t - 1


def test_prospective_freeze_intact():
    fz = HERE.parent / "frozen" / "E44_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        pytest.skip("not frozen yet")
    want = (fz.parent / "E44_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    assert hashlib.sha256(fz.read_bytes()).hexdigest() == want
    r = json.loads(fz.read_text())
    assert r["origin"] == "2026-10-01" and r["target_quarter"] == "2027-Q1" and r["lead_from_origin"] == 2
    sel = r["selections_at_origin"].get("I2", {})
    assert FIVE <= {g for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g] if c in sel.get("price_features", [])}


def test_i4_addendum_frozen():
    want = (HERE.parent / "runner" / "ADDENDUM_I4_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((HERE.parent / "ADDENDUM_I4.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_i4_ignores_post_origin_data_and_uses_five_triggers():
    t = L.qi("2025-Q1")
    o = list(range(L.qi("2021-Q3"), t + 1))
    outs = []
    for d, x in ((D, XR), (perturb(D, t), perturb_extra(XR, t))):
        Xd = P2.features(d, x, o)
        f = P2.forecast_i4(d, Xd, P2.bases(d, o), t, n_jobs=1)
        outs.append((list(np.round(f["p"], 12)), f["threshold"], f["food_cfg"], f["gap_cfg"], round(f["rho"], 12)))
        for m in (f["food_model"], f["gap_model"]):
            assert FIVE <= {g for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g] if c in m.cols}
    assert outs[0] == outs[1]


def test_bivariate_price_probability_bounds():
    p = P2.p_price_biv([0.0, 50.0], [-50.0, 0.0], 2.0, 1.0, 0.5, ["PH040100000", "PH040100000"])
    assert p[0] < 0.01 and p[1] > 0.99


def test_i5_addendum_frozen():
    want = (HERE.parent / "runner" / "ADDENDUM_I5_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((HERE.parent / "ADDENDUM_I5.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_i5_forward_inner_validation_and_leakage():
    assert P2.forward_quarters(list(range(10))) == [4, 5, 6, 7, 8, 9]
    t = L.qi("2025-Q1")
    o = list(range(L.qi("2021-Q3"), t + 1))
    outs = []
    for d, x in ((D, XR), (perturb(D, t), perturb_extra(XR, t))):
        Xd = P2.features(d, x, o)
        f = P2.forecast_i5(d, Xd, P2.bases(d, o), t, n_jobs=1)
        outs.append((list(np.round(f["p"], 12)), f["threshold"], f["food_cfg"], f["gap_cfg"], f["hunger_alpha"]))
        for m in (f["food_model"], f["gap_model"]):
            assert FIVE <= {g for g in P2.ALL_GROUPS for c in P2.PRICE_GROUPS[g] if c in m.cols}
    assert outs[0] == outs[1]
