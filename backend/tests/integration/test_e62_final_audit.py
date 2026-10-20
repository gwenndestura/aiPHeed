"""
tests/integration/test_e62_final_audit.py
-----------------------------------------
E62 final audit (aipheed-backend-aligned/experiments/E62_Final_System_Audit): regression tests for the defects fixed in
E62 and for the data-to-dashboard consistency checks that the audit relies on.

Fixed defects
  * D-E62-1  the unemployment caveat ("statistical pattern, not evidence") appears for every province whose Employment
             bar is drawn as lowering the score while unemployment rose, not only when Employment is a named reason;
  * D-E62-2  news shown beside a Lead-2 estimate follows that estimate's own issue date: an earlier forecast is never
             shown with articles published after it was issued;
  * D-E62-3  the back-test news note states the two-quarter-ahead timing (not "the previous quarter's news").
Consistency
  * served province scores, time series (province and region mean) equal the record;
  * the record's attribution adds up to its price part at every origin; back-tests equal the sealed E57 file;
  * the outcome labels in the record equal labels recomputed from the raw PSA / SWS files;
  * serving never mutates the cached record; the E38 default keeps its news wording.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "aipheed-backend-aligned" / "experiments"
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}


@pytest.fixture
def e58(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e58")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-19T09:00:00")


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _entries(v: dict, target: str) -> dict:
    out = {x["targetQuarter"]: x for x in v["pastForecasts"] + v["earlierForecasts"]}
    out[target] = {"probability": v["forecast"]["probability"], "origin": None}
    return out


def test_employment_caveat_follows_every_drawn_bar(e58):
    rec = LEAD2.record()
    seen = 0
    for code, v in rec["provinces"].items():
        ex = _get("/api/v1/explainability", scope="province", id=SLUG[code], quarter="2027-Q1")
        lowered = any(t["key"] == "employment" and t["direction"] == "protective" and t["pct"] > 0
                      and t["status"] == "contributes" for t in ex["triggers"])
        rising = (v["observed"]["employment"].get("unemploymentChangeYoY") or 0) > 0
        has = "not evidence that job losses reduce food stress" in ex["summary"]["caveat"]
        assert has == (lowered and rising), v["name"]
        seen += has
    assert seen == 5                                   # 2027-Q1: employment lowers all five while unemployment rose


def test_news_beside_a_lead2_estimate_never_postdates_its_issue_date(e58):
    for q in LEAD2.candidate_quarters():
        rows = LEAD2.rows_for(q)
        origin, kind = rows[0]["origin"], rows[0]["estimate_kind"]
        a = _get("/api/v1/news", scope="province", id="laguna", quarter=q, page=1, pageSize=50)
        if kind in ("forecast", "earlier_forecast"):
            assert a["evidenceMode"] == "FORECAST"
            y, k = int(q[:4]), int(q[-1])
            i = y * 4 + k - 1 - 2
            assert a["evidenceQuarter"] == f"{i // 4}-Q{i % 4 + 1}"
            assert all(x["date"] < origin for x in a["data"]), (q, origin)
            assert f"published before {origin}" in a["evidenceNote"]
        else:
            assert a["evidenceMode"] == "OBSERVED"
            assert "previous quarter's news" not in a["evidenceNote"]
            assert f"made as of {origin}" in a["evidenceNote"]


def test_e38_default_news_wording_unchanged(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-19T09:00:00")
    a = _get("/api/v1/news", scope="province", id="laguna", quarter="2026-Q3")
    if a.get("evidenceMode") == "OBSERVED":
        assert "one-quarter-ahead" in a["evidenceNote"]


def test_served_scores_and_series_equal_the_record(e58):
    rec = LEAD2.record()
    tq = rec["targetQuarter"]
    rows = {p["provinceCode"]: p["riskScore"] for p in _get("/api/v1/provinces", quarter=tq)["data"]}
    for code, v in rec["provinces"].items():
        assert rows[code] == pytest.approx(v["forecast"]["probability"], abs=5e-4)
        want = {q: e["probability"] for q, e in _entries(v, tq).items()}
        got = {p["quarter"]: p["riskScore"] for p in _get("/api/v1/forecast/timeseries", scope="province", id=SLUG[code])["series"]}
        assert set(got) == set(want), v["name"]
        for q in want:
            assert got[q] == pytest.approx(want[q], abs=5e-3), (v["name"], q)
    reg = {p["quarter"]: p["riskScore"] for p in _get("/api/v1/forecast/timeseries", scope="region", id="calabarzon")["series"]}
    for q, s in reg.items():
        vals = [_entries(v, tq)[q]["probability"] for v in rec["provinces"].values()]
        assert s == pytest.approx(sum(vals) / 5, abs=5e-3), q
    region = _get("/api/v1/forecast", scope="region", id="calabarzon", quarter=tq)["riskScore"]
    assert region == pytest.approx(sum(v["forecast"]["probability"] for v in rec["provinces"].values()) / 5, abs=5e-4)


def test_lgu_outputs_cover_all_142(e58):
    tq = LEAD2.record()["targetQuarter"]
    lgus = [m for s in SLUG.values() for m in _get(f"/api/v1/provinces/{s}/municipalities", quarter=tq)["data"]]
    assert len(lgus) == 142 and len({m["lguCode"] for m in lgus}) == 142
    assert all(m["riskIndex"] is not None and math.isfinite(m["riskIndex"]) for m in lgus)
    assert all("not an independent municipal forecast" in m["disaggregationLabel"] for m in lgus)


def test_record_attribution_adds_up_at_every_origin(e58):
    rec = LEAD2.record()
    for v in rec["provinces"].values():
        blocks = list(v["pastDrivers"].values()) + [{**v, "probabilityPricePressure": v["forecast"]["components"]["probabilityPricePressure"]}]
        for b in blocks:
            c = b["fiveTriggerContributions"]
            z = (b["baselineLogOdds"] + sum(x["logOddsEffect"] for x in c.values())
                 + b["otherContribution"]["logOddsEffect"] + b["povertyContribution"]["logOddsEffect"])
            assert 1 / (1 + math.exp(-z)) == pytest.approx(b["probabilityPricePressure"], abs=2e-3)


def test_record_backtests_equal_the_sealed_e57_file(e58):
    sealed = EXP / "E57_E56_Rolling_Origin_Test" / "sealed" / "predictions.csv"
    if not sealed.exists():
        pytest.skip("E57 sealed file not present")
    want = (sealed.parent / "predictions.csv.sha256").read_text().split()[0]
    assert hashlib.sha256(sealed.read_bytes()).hexdigest() == want
    s = pd.read_csv(sealed, dtype={"province_code": str})
    rec = LEAD2.record()
    n = 0
    for _, r in s.iterrows():
        e = {x["targetQuarter"]: x for x in rec["provinces"][r["province_code"]]["pastForecasts"]}[r["target"]]
        assert e["probability"] == pytest.approx(r["E56_p"], abs=1e-3)
        n += 1
    assert n == 50


def test_record_outcomes_equal_labels_from_raw_files(e58):
    yoy = EXP / "E40_SWS_CPI_Tiers" / "data_acquired" / "psa_cpi_yoy_headline_food_2021_2026.csv"
    spec = EXP / "E40_SWS_CPI_Tiers" / "label_spec.json"
    sws = ROOT / "backend" / "data" / "inputs" / "sws_rounds.csv"
    if not (yoy.exists() and spec.exists()):
        pytest.skip("raw label inputs not present")
    th = json.loads(spec.read_text(encoding="utf-8"))["thresholds"]
    y = pd.read_csv(yoy, dtype={"province_code": str})
    y["quarter"] = y["reference_month"].map(lambda s: f"{s[:4]}-Q{(int(s[5:7]) - 1) // 3 + 1}")
    g = y.groupby(["province_code", "commodity", "quarter"])["yoy_pct"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] == 3].pivot_table(index=["province_code", "quarter"], columns="commodity", values="mean")
    h = pd.read_csv(sws).groupby("quarter")["H"].mean()
    rec = LEAD2.record()
    for code, v in rec["provinces"].items():
        for x in v["pastForecasts"]:
            f, hl = g.loc[(code, x["targetQuarter"])]["food"], g.loc[(code, x["targetQuarter"])]["all_items"]
            high = h[x["targetQuarter"]] > th["H"] and (f > th["food"][code] or f - hl > th["gap"][code])
            assert bool(x["observedHigh"]) == bool(high), (v["name"], x["targetQuarter"])


def test_serving_does_not_mutate_the_cached_record(e58):
    rec = LEAD2.record()
    before = hashlib.sha256(json.dumps(rec, sort_keys=True, default=str).encode()).hexdigest()
    tq = rec["targetQuarter"]
    for _ in range(2):
        _get("/api/v1/explainability", scope="region", id="calabarzon", quarter=tq)
        for s in SLUG.values():
            _get("/api/v1/explainability", scope="province", id=s, quarter=tq)
            _get("/api/v1/forecast/timeseries", scope="province", id=s)
            _get("/api/v1/news", scope="province", id=s, quarter=tq)
    after = hashlib.sha256(json.dumps(LEAD2.record(), sort_keys=True, default=str).encode()).hexdigest()
    assert before == after and LEAD2.record() is rec
