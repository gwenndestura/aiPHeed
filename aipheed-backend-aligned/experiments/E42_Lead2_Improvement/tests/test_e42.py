"""E42 validity tests (gate G0): E41 equivalence, as-of masking for PS / NLP / ML arms, study window, freeze."""
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
import e42_lib as K  # noqa: E402
from test_e41 import perturb  # noqa: E402

L = K.L
D = L.load()
O = list(range(L.qi("2021-Q3"), L.qi("2024-Q4") + 1))


def test_protocol_frozen():
    want = (HERE.parent / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert hashlib.sha256((K.E42 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want


def test_drift_variants_reproduce_e41_arms():
    a = K.m_forecasts(D, O, 2, 1.0)
    b = L.m1_forecasts(D, O, 2)
    np.testing.assert_allclose(a["F_hat"], b["F_hat"], equal_nan=True)
    np.testing.assert_allclose(a["p"], b["p"], equal_nan=True)
    z = L.m1_forecasts(D, O, 2, zero_drift=True)
    np.testing.assert_allclose(K.m_forecasts(D, O, 2, 0.0)["F_hat"], z["F_hat"], equal_nan=True)


@pytest.mark.parametrize("t", [L.qi("2023-Q2"), L.qi("2024-Q4")])
def test_prequential_ignores_post_origin_data(t):
    o = list(range(L.qi("2021-Q3"), t + 1))
    res = []
    for d in (D, perturb(D, t)):
        arms = {n: K.m_forecasts(d, o, 2, m) for n, m in K.ARMS.items()}
        ps = K.prequential(d, arms, o)
        res.append(ps[ps["t"] == t][["province_code", "p", "chosen", "platt"]].reset_index(drop=True))
    pd.testing.assert_frame_equal(res[0], res[1])


def test_nlp_features_use_only_quarter_t(monkeypatch):
    t = L.qi("2024-Q2")
    base = K.features(D, [t])
    panel = K.nlp_panel()
    later = panel["q"] > t
    panel.loc[later, "FSSI_v2"] = 99.0
    panel.loc[later, "n_admitted"] = 999
    monkeypatch.setattr(K, "nlp_panel", lambda: panel)
    pd.testing.assert_frame_equal(base, K.features(D, [t]))


@pytest.mark.parametrize("t", [L.qi("2025-Q1"), L.qi("2026-Q1")])
def test_ml_arms_ignore_post_origin_data(t):
    o = list(range(L.qi("2021-Q3"), t + 1))
    outs = []
    for d in (D, perturb(D, t)):
        X = K.features(d, o)
        tr = L.training_pairs(X, d.cut(t), t, 2)
        assert tr["q"].max() <= t - 1 and K.eligible(tr)
        te = X[X["t"] == t]
        outs.append([cls(K.COMB).fit(tr).predict(te) for cls in (K.LRModel, K.GBModel)])
    for a, b in zip(*outs):
        np.testing.assert_array_equal(a, b)


def test_missing_values_are_not_zero_filled_for_lightgbm():
    t = L.qi("2024-Q3")
    X = K.features(D, list(range(L.qi("2021-Q3"), t + 1)))
    assert X.loc[X["t"] == L.qi("2021-Q3"), "palay_yoy"].isna().all()      # year-ago quarter before 2021: missing
    tr = L.training_pairs(X, D.cut(t), t, 2)
    m = K.LRModel(K.COMB).fit(tr)
    assert "palay_yoy__missing" in m.miss or "palay_yoy" in m.miss


def test_ofw_group_is_empty_and_flagged():
    assert K.GROUPS["ofw_remittance"] == [] and not any("ofw" in c and "news" not in c for c in K.COMB)


def test_fssi_panel_in_window():
    assert K.nlp_panel()["q"].min() >= L.FIRST_Q


def test_prospective_freeze_intact():
    fz = K.E42 / "frozen" / "E42_PROSPECTIVE_2027Q1.json"
    if not fz.exists():
        pytest.skip("not frozen yet")
    want = (fz.parent / "E42_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    assert hashlib.sha256(fz.read_bytes()).hexdigest() == want
    r = json.loads(fz.read_text())
    assert r["origin"] == "2026-10-01" and r["lead2_target"] == "2027-Q1" and r["cpi_months_used_through"] == "2026-08"
