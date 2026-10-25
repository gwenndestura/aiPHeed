"""Tests for E113 (final hunger forecast model; PROTOCOL_E113.md + ADDENDUM_1.md)."""
import json
import sys
from pathlib import Path

import pytest

EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "E113_Final_Model"
sys.path.insert(0, str(EXP / "runner"))
import e113_lib as L  # noqa: E402

E, F, np, pd = L.E, L.F, L.np, L.pd
OUT = EXP / "out"
needs_news = pytest.mark.skipif(not (OUT / "news_composites_C.csv").exists(), reason="run run_e113.py news first")


def test_cpi_day10_release_rule():
    assert L.cpi_available(2024 * 12 + 10, "2025-01-01")            # Nov 2024 released by 10 Dec
    assert not L.cpi_available(2024 * 12 + 11, "2025-01-01")        # Dec 2024 not released before 1 Jan
    assert L.cpi_features(E.issue(E.qi("2024-Q4")))["cpi_last_month"] == "2024-11"


def test_regime_anchor():
    s = ((E.qi("2024-Q3"), 10.0, 1), (E.qi("2024-Q4"), 20.0, 1), (E.qi("2025-Q2"), 30.0, 1))
    assert L.anchor(s, E.qi("2025-Q3")) == pytest.approx(15.0)                     # one post-break reading -> pre-break mean
    s2 = s + ((E.qi("2025-Q3"), 40.0, 1),)
    assert L.anchor(s2, E.qi("2025-Q4")) == pytest.approx(35.0)                    # >= 2 post-break -> post-break mean
    assert L.anchor(s, E.qi("2025-Q1")) == pytest.approx(20.0)


def test_ridge_without_intercept_returns_persistence_at_zero_features():
    X = np.array([[1.0, 2.0], [2.0, 1.0], [0.5, -1.0]])
    b = L._ridge_fit(X, np.array([1.0, 2.0, -1.0]), 10.0)
    assert np.zeros(2) @ b == 0.0


@needs_news
def test_news_quarter_used_only_after_its_last_headline():
    tab = L.composites("C")
    for t in range(E.FIRST_ORIGIN, E.LAST_ORIGIN + 1):
        r = L.news_row(t, E.issue(t))
        if t in tab.index and tab.loc[t, "last_published"] < pd.Timestamp(E.issue(t)):
            continue
        assert all(np.isnan(v) for v in r.values())


@needs_news
def test_training_targets_published_before_issue():
    for t in (E.qi("2024-Q2"), E.qi("2026-Q1")):
        tr = L.pairs(t, 1)
        for r in tr.itertuples():
            kn = {q for q, _, _ in L.known(E.issue(t), r.area)}
            assert r.q in kn and r.t < t


@needs_news
def test_future_data_changes_no_forecast():
    t = E.qi("2025-Q3")
    base = {(m, a): L.forecast(m, t, 1, a)["forecast"] for m in L.MODELS for a in L.AREAS}
    r0 = F.rounds()
    fake = r0.copy()
    fake["H"], fake["published"] = fake["H"] + 40, E.issue(t)
    cpi = L.cpi_monthly().copy()
    cpi[[not L.cpi_available(int(m), E.issue(t)) for m in cpi.index]] += 50
    tab = L.composites("C").copy()
    tab.loc[tab.index > t, "dis_yoy"] = 9.0
    L._OVERRIDE.update({"rounds": pd.concat([r0, fake], ignore_index=True), "cpi": cpi, ("news", "C"): tab})
    L.clear_caches()
    try:
        for (m, a), v in base.items():
            assert L.forecast(m, t, 1, a)["forecast"] == pytest.approx(v, abs=1e-9)
    finally:
        L._OVERRIDE.clear()
        L.clear_caches()


@needs_news
def test_negative_control_available_data_changes_forecasts():
    t = E.qi("2025-Q3")
    rw = L.forecast("RW", t, 1, "BL")["forecast"]
    r0 = F.rounds()
    r = r0.copy()
    r.loc[(r["area"] == "BL") & (r["q"] == t - 1), "H"] += 10
    L._OVERRIDE["rounds"] = r
    L.clear_caches()
    try:
        assert L.forecast("RW", t, 1, "BL")["forecast"] == pytest.approx(rw + 10)
    finally:
        L._OVERRIDE.clear()
        L.clear_caches()


needs_run = pytest.mark.skipif(not (OUT / "results.json").exists(), reason="run run_e113.py score first")


@needs_run
def test_scored_under_frozen_protocol_and_audit_passed():
    r = json.loads((OUT / "results.json").read_text())
    assert r["run"]["protocol_sha256"] == (EXP / "runner/PROTOCOL_SHA256.txt").read_text().strip() == L.sha256(EXP / "PROTOCOL_E113.md")
    assert r["run"]["addendum1_sha256"] == L.sha256(EXP / "ADDENDUM_1.md")
    assert json.loads((OUT / "leakage_audit.json").read_text())["passed"]


@needs_run
@pytest.mark.parametrize("k", [1, 2])
def test_stored_predictions_reproduce(k):
    st = pd.read_csv(OUT / f"panel_lead{k}.csv")
    r = st.iloc[len(st) // 2]
    for m in L.MODELS:
        assert L.forecast(m, int(r["t"]), k, r["area"])["forecast"] == pytest.approx(r[m], abs=1e-6)


@needs_run
def test_selection_follows_rule():
    r = json.loads((OUT / "results.json").read_text())
    rel = [m for m in L.CANDIDATES if r["decision"]["1"][m]["reliable"]]
    if not rel:
        mase = {m: r["lead"]["1"]["metrics"][m]["mase"] for m in L.CANDIDATES}
        best = min(mase, key=mase.get)
        tier2 = mase[best] < r["lead"]["1"]["metrics"]["RW"]["mase"] and r["decision"]["1"][best]["criteria"]["R4"]
        assert r["selection"]["adopted"] == (best if tier2 else "RW")


@pytest.mark.skipif(not (OUT / "sealed_prospective_A.csv").exists(), reason="run prospective first")
def test_seals_unchanged():
    for s in ("A", "B"):
        assert L.sha256(OUT / f"sealed_prospective_{s}.csv") == (OUT / f"sealed_prospective_{s}.csv.sha256").read_text().strip()
    for e in ("E107_Twelve_Indicator_LightGBM", "E108_Best_Defensible_Forecasting", "E109_Hunger_Forecasting",
              "E110_Hunger_Generalization", "E111_Hunger_Forecast_Audit", "E112_Food_Insecurity_Forecasting"):
        p = L.EXP / e / "out" / "sealed_prospective.csv"
        assert L.sha256(p) == (p.parent / "sealed_prospective.csv.sha256").read_text().strip()


SERVE = E.BACKEND / "data" / "e113"


@pytest.mark.skipif(not (SERVE / "forecast.json").exists(), reason="run export first")
def test_api_serves_exported_files():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    for route, name in (("evaluation", "evaluation_summary.json"), ("forecast", "forecast.json")):
        r = c.get(f"/api/v1/e113/{route}")
        assert r.status_code == 200 and r.json() == json.loads((SERVE / name).read_text(encoding="utf-8"))
