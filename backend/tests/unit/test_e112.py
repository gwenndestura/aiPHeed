"""Tests for E112 (food-insecurity forecasting with issue-date news indicators; PROTOCOL.md)."""
import json
import sys
from pathlib import Path

import pytest

EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "E112_Food_Insecurity_Forecasting"
sys.path.insert(0, str(EXP / "runner"))
import e112_lib as L  # noqa: E402
import news_indicators as NI  # noqa: E402

E, F, G, H9, np, pd = L.E, L.F, L.G, L.H9, L.np, L.pd
OUT = EXP / "out"


@pytest.mark.parametrize("src", ["C", "G"])
def test_news_indicators_use_only_headlines_published_before_issue(src):
    tab = L.news_table(src)
    for t in range(E.FIRST_ORIGIN, E.LAST_ORIGIN + 1):
        v = L.news_at(t, src)
        if t in tab.index and tab.loc[t, "last_published"] < pd.Timestamp(E.issue(t)):
            assert all(np.isnan(x) for x in v.values()) == tab.loc[t, [f"{c}_yoy" for c in L.CATS]].isna().all()
        else:
            assert all(np.isnan(x) for x in v.values())


def test_news_after_issue_date_is_refused(monkeypatch):
    t = E.qi("2025-Q3")
    tab = L.news_table("C").copy()
    tab.loc[t, "last_published"] = pd.Timestamp(E.issue(t))          # one headline on the issue date itself
    monkeypatch.setattr(L, "news_table", lambda src: tab)
    L._news_at.cache_clear()
    try:
        assert all(np.isnan(x) for x in L.news_at(t).values())
    finally:
        L._news_at.cache_clear()


def test_news_yoy_is_share_minus_share_four_quarters_earlier():
    tab = L.news_table("C")
    q = E.qi("2024-Q3")
    for c in L.CATS:
        assert tab.loc[q, f"{c}_yoy"] == pytest.approx(tab.loc[q, f"{c}_share"] - tab.loc[q - 4, f"{c}_share"], abs=1e-5)


def test_lexicon_tags_and_dedup():
    from app.news import pipeline_v3 as P
    assert NI._RX["price"].search("Rice prices up again") and NI._RX["disaster"].search("Bagyong Kristine")
    assert not NI._RX["shortage"].search("Senate approves budget")
    arts = [{"title": "Rice prices climb", "published_ph": "2024-05-01T08:00:00", "source": "A", "quarter": "2024-Q2", "article_key": "a"},
            {"title": "Rice prices climb", "published_ph": "2024-05-02T08:00:00", "source": "B", "quarter": "2024-Q2", "article_key": "b"}]
    kept, _ = P.dedupe(arts)
    assert len(kept) == 1


def test_lgbm12_reproduces_e109_and_news_variant_has_19_columns():
    for t in (E.qi("2024-Q2"), E.qi("2026-Q1")):
        assert L.lgbm_forecast(t, 1, E.COLUMNS)["forecast"] == pytest.approx(H9.forecast("LGBM", t, 1)["forecast"], abs=1e-9)
    assert len(L._cols(None)) == 19 and L._cols("news") == E.COLUMNS
    assert "A1_food" not in L._cols("fam:A1") and "A1_gap" not in L._cols("fam:A1") and len(L._cols("fam:A1")) == 17
    assert "NC_price" not in L._cols("cat:price") and len(L._cols("cat:price")) == 18


def test_twelve_families():
    assert len(E.FAMILIES) == 12 and sorted(E.FAMILIES) == E.EXPECTED_FAMILIES


def test_future_rounds_change_no_e112_forecast(monkeypatch):
    t = E.qi("2025-Q3")
    base = {(m, k): L.forecast(m, t, k)["forecast"] for m in ("RW", "NEWS-C", "LGBM12N") for k in (1, 2)}
    r0 = H9.rounds()
    fake = r0.copy()
    fake["H"], fake["published"] = fake["H"] + 40, "2027-06-01"
    monkeypatch.setattr(H9, "rounds", lambda: pd.concat([r0, fake], ignore_index=True))
    for f in (H9.known, H9.forecast, L.forecast):
        f.cache_clear()
    try:
        for (m, k), v in base.items():
            assert L.forecast(m, t, k)["forecast"] == pytest.approx(v, abs=1e-9)
    finally:
        for f in (H9.known, H9.forecast, L.forecast):
            f.cache_clear()


needs_run = pytest.mark.skipif(not (OUT / "results.json").exists(), reason="run runner/run_e112.py score first")


@needs_run
def test_scored_under_frozen_protocol():
    r = json.loads((OUT / "results.json").read_text())
    assert r["run"]["protocol_sha256"] == (EXP / "runner/PROTOCOL_SHA256.txt").read_text().strip() == L.sha256(EXP / "PROTOCOL.md")


@needs_run
@pytest.mark.parametrize("k", [1, 2])
def test_stored_predictions_reproduce(k):
    st = pd.read_csv(OUT / f"bl_lead{k}.csv")
    r = st.iloc[len(st) // 2]
    for m in L.BASELINES + L.CANDIDATES:
        assert L.forecast(m, int(r["t"]), k)["forecast"] == pytest.approx(r[m], abs=1e-6)


@needs_run
def test_final_method_follows_the_decision_rule():
    r = json.loads((OUT / "results.json").read_text())
    want = next((m for m in L.ORDER if r["status"][m].get("1") == "provisional"), "RW")
    assert r["final_method"] == want and r["max_reliable_lead"] is None


@pytest.mark.skipif(not (OUT / "sealed_prospective.csv").exists(), reason="run prospective first")
def test_seals_unchanged():
    assert L.sha256(OUT / "sealed_prospective.csv") == (OUT / "sealed_prospective.csv.sha256").read_text().strip()
    want = {"E107_Twelve_Indicator_LightGBM": "246700a8d3c4fe76daf43adbfd5ea3c9d622dd124fb4d7137bde9f84a90c75fb",
            "E108_Best_Defensible_Forecasting": "fbc8bf911b1342e7f839cd4c27d35b037bbcd92953281067cffe7747650c325f",
            "E109_Hunger_Forecasting": "61bcc3535d802b58c540a42b958533f8e171bbc8e3ae67e183a1c319df141840",
            "E110_Hunger_Generalization": "81f0b237ad0c98c3e65cc9371338817cbfa0e81ccd002b0539639ea2be751ee5",
            "E111_Hunger_Forecast_Audit": "adf27ba91985b99eb72530753d042ecdd633d00922c26f40f205867bac159589"}
    for e, h in want.items():
        assert L.sha256(EXP.parent / e / "out/sealed_prospective.csv") == h


SERVE = E.BACKEND / "data" / "e112"


@pytest.mark.skipif(not (SERVE / "forecast.json").exists(), reason="run export first")
def test_api_serves_exported_files():
    from fastapi.testclient import TestClient
    from app.main import app
    c = TestClient(app)
    for route, name in (("evaluation", "evaluation_summary.json"), ("forecast", "forecast.json"),
                        ("news-indicators", "news_indicators.json")):
        r = c.get(f"/api/v1/e112/{route}")
        assert r.status_code == 200 and r.json() == json.loads((SERVE / name).read_text(encoding="utf-8"))
