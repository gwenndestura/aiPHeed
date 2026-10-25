"""Tests for E108 (factored LightGBM, PROTOCOL.md section 11).

Future perturbation is checked per indicator family and lead, at the feature level and at the prediction level: a value
published on or after an issue date must change neither the 13 feature columns nor the forecast of that issue date.
"""
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "E108_Best_Defensible_Forecasting"
sys.path.insert(0, str(EXP / "runner"))
import e108_lib as F  # noqa: E402

E, M, L, np, pd = F.E, F.M, F.L, F.np, F.pd
OUT = EXP / "out"
T_TEST = E.qi("2025-Q1")                     # an origin with eligible training rows at every lead
FAMILY_SOURCE = {"A1": "cpi", "A2": "cpi", "A3": "rice", "C2": "climate", "C3": "prod", "C4": "prod", "E1": "lfs",
                 "E2": "ofw"}


def _perturb(source: str, t: int):
    """The study data with every value of one source published on or after O(t) changed."""
    d, x = E.data()
    m0, O = L.m0_of(t), L.origin(t)
    idx, yoy, prod, lfs = d.idx.copy(), d.yoy.copy(), d.prod.copy(), d.lfs.copy()
    x2 = {k: v.copy() for k, v in x.items()}
    if source == "cpi":
        idx.loc[idx["ym"] > m0, "index"] *= 1.5
        yoy.loc[yoy["ym"] > m0, "yoy"] += 40.0
    elif source == "prod":
        prod.loc[prod["q"] > t - 1, "value"] *= 4.0
    elif source == "lfs":
        lfs.loc[lfs["ym"] > (t - 1) // 4 * 12 + ((t - 1) % 4) * 3 + 2, "value"] += 9.0
    elif source == "climate":
        x2["climate"].loc[x2["climate"]["q"] > t, "tc_count"] += 7
        x2["climate"].loc[x2["climate"]["q"] >= t, "enso_phase"] = "LA_NINA"
    elif source in ("ofw", "rice"):
        num = x2[source].select_dtypes("number").columns.drop(["year", "q"], errors="ignore")
        x2[source].loc[x2[source]["q"] > t - 1, num] *= 3.0
    return L.Data(idx, yoy, d.sws, prod, lfs, d.news, meta=d.meta), x2


def _clear_feature_cache():
    for k in [k for k in E._CACHE if isinstance(k, tuple) and k and k[0] == "X"]:
        del E._CACHE[k]


def _forecast(t, k, d=None, x=None):
    r = F.forecast_at(t, k, F.PRIMARY, d, x)
    assert r is not None, "origin not eligible"
    return r[0]


# ------------------------------------------------------------------------------------------------ completeness
def test_all_twelve_families_enter_the_fitted_price_booster():
    df, mdl = F.forecast_at(T_TEST, 1)
    assert mdl.m.booster_.feature_name() == E.COLUMNS
    assert sorted({E.FAMILY_OF[c] for c in E.COLUMNS}) == E.EXPECTED_FAMILIES and len(E.FAMILIES) == 12
    assert np.allclose(df["p"], df["H1"] * df["price"])


# ------------------------------------------------------------------------------------------------ perturbation
@pytest.mark.parametrize("k", E.LEADS)
@pytest.mark.parametrize("family", sorted(FAMILY_SOURCE))
def test_future_values_of_each_data_family_change_neither_features_nor_forecast(family, k):
    base_X = E.feature_table(k, [T_TEST]).set_index("province_code")[E.COLUMNS]
    base_p = _forecast(T_TEST, k)
    dm, xm = _perturb(FAMILY_SOURCE[family], T_TEST)
    pert_X = E.feature_table(k, [T_TEST], dm, xm).set_index("province_code")[E.COLUMNS]
    pd.testing.assert_frame_equal(base_X, pert_X)
    pert_p = _forecast(T_TEST, k, dm, xm)
    assert np.allclose(base_p["p"], pert_p["p"], atol=1e-12)


@pytest.mark.parametrize("k", E.LEADS)
def test_future_backend_items_change_neither_features_nor_forecast(k, monkeypatch):
    """C1 (PAGASA items), N1 (headlines) and H1 (SWS rounds) published after O(t) are invisible at O(t)."""
    base_X = E.feature_table(k, range(E.FIRST_ORIGIN, T_TEST + 1)).copy()
    base_p = _forecast(T_TEST, k)
    after = (L.origin(T_TEST) + timedelta(days=1))
    monkeypatch.setattr(E.CW, "PAGASA_ENSO", list(E.CW.PAGASA_ENSO) + [(after.date().isoformat(),
                                                                         "El Nino Advisory: El Nino present")])
    rounds = E.TS._rounds(str(E.TS.SWS), E.TS.SWS.stat().st_mtime_ns)
    fake_round = (T_TEST, 60.0, after.date().isoformat())
    monkeypatch.setattr(E.TS, "_rounds", lambda path, mtime: rounds + (fake_round,))
    arts = E.P3.admitted()
    fake = [dict(arts[0], province_code=p, quarter=E.qs(T_TEST), published_ph=after.isoformat(),
                 article_key=f"fake-{p}") for p in E.PROVS for _ in range(6)]
    monkeypatch.setattr(E.P3, "admitted", lambda: tuple(arts) + tuple(fake))
    _clear_feature_cache()
    try:
        pert_X = E.feature_table(k, range(E.FIRST_ORIGIN, T_TEST + 1))
        pd.testing.assert_frame_equal(base_X[E.COLUMNS].reset_index(drop=True), pert_X[E.COLUMNS].reset_index(drop=True))
        assert np.allclose(base_p["p"], _forecast(T_TEST, k)["p"], atol=1e-12)
    finally:
        _clear_feature_cache()


def test_negative_control_items_published_before_the_issue_do_change_features(monkeypatch):
    """The perturbation test is not vacuous: the same fake items dated before O(t) change H1, N1 and C1."""
    t = E.qi("2022-Q3")                                   # no El Nino advisory in force; quarter with few headlines
    base = E.feature_table(1, [t]).set_index("province_code")
    before = (L.origin(t) - timedelta(days=2))
    monkeypatch.setattr(E.CW, "PAGASA_ENSO", list(E.CW.PAGASA_ENSO) + [(before.date().isoformat(),
                                                                         "El Nino Advisory: El Nino present")])
    rounds = E.TS._rounds(str(E.TS.SWS), E.TS.SWS.stat().st_mtime_ns)
    monkeypatch.setattr(E.TS, "_rounds", lambda path, mtime: rounds + ((t, 60.0, before.date().isoformat()),))
    arts = E.P3.admitted()
    fake = [dict(arts[0], province_code=p, quarter=E.qs(t), published_ph=before.isoformat(), article_key=f"fake-{p}-{i}")
            for p in E.PROVS for i in range(6)]
    sc = dict(E.P3.intensities(), **{a["article_key"]: 0.9 for a in fake})
    monkeypatch.setattr(E.P3, "admitted", lambda: tuple(arts) + tuple(fake))
    monkeypatch.setattr(E.P3, "intensities", lambda: sc)
    _clear_feature_cache()
    try:
        pert = E.feature_table(1, [t]).set_index("province_code")
        assert (pert["C1"] != base["C1"]).all() and (pert["H1"] != base["H1"]).all()
        assert (pert["N1"].fillna(-1) != base["N1"].fillna(-1)).all()
    finally:
        _clear_feature_cache()


def test_v1_is_a_static_profile():
    X = E.feature_table(1)
    assert (X.groupby("province_code")["V1"].nunique() == 1).all()


# ------------------------------------------------------------------------------------------------ labels
@pytest.mark.parametrize("k", E.LEADS)
def test_price_training_labels_are_known_at_the_issue(k):
    X = E.feature_table(k)
    d = E.data()[0]
    for t in range(E.qi("2022-Q4"), E.LAST_ORIGIN + 1):
        tr = F.price_rows(X, t, k)
        if not len(tr):
            continue
        assert (tr["q"] <= t - 1).all() and (tr["t"] + k == tr["q"]).all()
        months = {m for q in tr["q"].unique() for m in range(q // 4 * 12 + q % 4 * 3, q // 4 * 12 + q % 4 * 3 + 3)}
        assert max(months) <= L.m0_of(t)                  # every CPI month behind a training label is published at O(t)
        assert t + k not in set(tr["q"])
    ps = F.ps_frame(d)
    th = L.e40_spec()
    for r in ps.itertuples():
        assert r.y == int(r.F > th["food"][r.province_code] or r.F - r.HL > th["gap"][r.province_code])


def test_t43_equals_hunger_and_price():
    d = E.data()[0]
    j = E.t43_frame(d).merge(F.ps_frame(d)[["province_code", "q", "y"]].rename(columns={"y": "ps"}), on=["province_code", "q"])
    assert ((j["H"] > 11.3).astype(int) * j["ps"] == j["y"]).all()


# ------------------------------------------------------------------------------------------------ reproducibility
needs_run = pytest.mark.skipif(not (OUT / "results.json").exists(), reason="run runner/run_e108.py score first")


@needs_run
@pytest.mark.parametrize("k", [1, 2, 4])
def test_stored_predictions_reproduce(k):
    st = pd.read_csv(OUT / f"predictions_T43_lead{k}.csv", dtype={"province_code": str})
    q = int(st["q"].iloc[len(st) // 2])
    new = _forecast(q - k, k)
    j = st[st["q"] == q].merge(new, on="province_code")
    assert len(j) == 5 and np.allclose(j["F1_p"], j["p"], atol=1e-9)


@needs_run
def test_results_used_the_frozen_protocol_and_a_clean_runner():
    r = json.loads((OUT / "results.json").read_text())
    assert r["run"]["protocol_sha256"] == (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text().strip()
    assert r["run"]["protocol_sha256"] == F.sha256(EXP / "PROTOCOL.md")
    assert not r["run"]["runner_dirty"]


@pytest.mark.skipif(not (OUT / "sealed_prospective.csv").exists(), reason="run runner/run_e108.py prospective first")
def test_e108_seal_hash_matches_and_e107_seal_untouched():
    assert F.sha256(OUT / "sealed_prospective.csv") == (OUT / "sealed_prospective.csv.sha256").read_text().strip()
    assert F.sha256(F.E107_OUT / "sealed_prospective.csv") == \
        "246700a8d3c4fe76daf43adbfd5ea3c9d622dd124fb4d7137bde9f84a90c75fb"


SERVE = E.BACKEND / "data" / "e108"


@pytest.mark.skipif(not (SERVE / "evaluation_summary.json").exists(), reason="run runner/run_e108.py export first")
def test_api_serves_the_exported_files_unchanged():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    for route, name in (("evaluation", "evaluation_summary.json"), ("forecast", "forecast.json"),
                        ("indicators", "indicators.json")):
        r = c.get(f"/api/v1/e108/{route}")
        assert r.status_code == 200 and r.json() == json.loads((SERVE / name).read_text(encoding="utf-8"))
