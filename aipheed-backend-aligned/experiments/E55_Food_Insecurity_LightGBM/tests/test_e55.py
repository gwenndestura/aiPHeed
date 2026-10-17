"""E55 experiment tests (PROTOCOL.md section 10): as-of invariance (no leakage), study window, TreeSHAP exactness,
T43 label definition, protocol and frozen-file hashes.

    backend/venv/Scripts/python.exe -B -m pytest -q aipheed-backend-aligned/experiments/E55_Food_Insecurity_LightGBM/tests
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

E55 = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(E55 / "runner"))
import e55_lib as F  # noqa: E402

E, L, K, M, np, pd = F.E, F.L, F.K, F.M, F.np, F.pd


@pytest.fixture(scope="module")
def data():
    return E.load()


def test_protocol_hash_frozen():
    want = (E55 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    got = hashlib.sha256((E55 / "PROTOCOL.md").read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert got == want


def test_frozen_prospective_hash():
    f = E55 / "frozen" / "E55_LGBM_PROSPECTIVE_2027Q1.json"
    if not f.exists():
        pytest.skip("not frozen yet")
    want = (f.parent / (f.name + ".sha256")).read_text().split()[0]
    assert hashlib.sha256(f.read_bytes()).hexdigest() == want
    assert json.loads(f.read_text())["targetQuarter"] == "2027-Q1"


def test_study_window_and_t43_definition(data):
    d, X, B = data
    Y = F.t43_labels(d)
    assert Y["q"].min() >= L.FIRST_Q and X["t"].min() >= L.FIRST_Q
    th = L.e40_spec()
    s = Y.dropna(subset=["T43"])
    hi = s["H_all"] > th["H"]
    assert (s.loc[hi, "T43"] == s.loc[hi, "PS"]).all()
    assert (s.loc[~hi, "T43"] == 0).all()
    ev = s[(s["q"] >= L.qi("2024-Q2")) & (s["q"] <= L.qi("2026-Q3"))]
    assert len(ev) == 50 and (ev["H_all"] > th["H"]).all()          # hunger condition met on every evaluation row


def _truncated(d_full, t):
    """Every input source truncated to what was published before O(t)."""
    x = K.load_extra()
    O = L.origin(t)
    xc = {"climate": x["climate"][x["climate"]["q"] <= t], "ofw": x["ofw"][x["ofw"]["q"] <= t - 1],
          "rice": x["rice"][x["rice"]["q"] <= t - 1], "fssi": x["fssi"][x["fssi"]["q"] <= t]}
    ev = M.load_events()
    ev = ev[ev["announcement_date"] < O]
    dc = d_full.cut(t)
    allo = list(range(L.qi("2021-Q3"), t + 1))
    return dc, M.features(dc, xc, allo, ev), P2bases(dc, allo)


def P2bases(d, allo):
    return F.P2.bases(d, allo)


@pytest.mark.parametrize("tq", ["2024-Q3", "2026-Q3"])
def test_as_of_invariance(data, tq):
    d, X, B = data
    t = L.qi(tq)
    full = F.lgbm_forecast(d, X, B, t, n_jobs=4)
    dc, Xc, Bc = _truncated(d, t)
    cut = F.lgbm_forecast(dc, Xc, Bc, t, n_jobs=4)
    assert full["cfg"] == cut["cfg"]
    assert np.max(np.abs(full["p"] - cut["p"])) < 1e-12


def test_treeshap_exact(data):
    import shap
    d, X, B = data
    fx = F.lgbm_forecast(d, X, B, L.qi("2026-Q3"), n_jobs=4)
    mdl = fx["model"]
    c = mdl.contributions(fx["te"])
    sv = shap.TreeExplainer(mdl.model.booster_).shap_values(mdl._X(fx["te"]))
    assert np.max(np.abs(np.asarray(sv) - c.drop(columns="tree_bias").to_numpy())) < 1e-9
    for i in range(5):
        a = F.attribution(fx, i)
        assert a["error"] < 1e-9
        assert abs(F._sig(a["raw"]) - fx["p_price"][i]) < 1e-12


def test_intercept_free_trees(data):
    d, X, B = data
    fx = F.lgbm_forecast(d, X, B, L.qi("2026-Q3"), n_jobs=4)
    mdl, tr = fx["model"], fx["tr"]
    trees = mdl.raw(tr) - F.struct_logit(tr, mdl.m, mdl.scale)
    w = F.recency_weights(tr["q"], mdl.hl)
    assert abs(float(np.average(trees, weights=w))) < 1e-9
