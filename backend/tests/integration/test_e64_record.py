"""
tests/integration/test_e64_record.py
------------------------------------
E64: the served e64 record (AIPHEED_LEAD2_MODEL=e64) and its data-to-dashboard consistency.
  * Lead-2 alignment: issued day 1 of quarter t+1, target t+2 (2026-10-01 -> 2027-Q1);
  * every probability equals the sealed E64 run of the selected candidate; the attribution adds up;
  * training/serving parity: the news features stored with each forecast equal app.news.pipeline_v3 recomputed now;
  * news IDs behind a forecast were all published before its issue date;
  * the prospective 2027-Q1 seal matches its hash and the served values;
  * the dashboard serves the record (provinces, series, explanations) and the LGU ranking is built from the e64
    province forecasts of the same target quarter; the caveat quotes e64's own back-test count;
  * the E38 default is unaffected.
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
from app.news import pipeline_v3 as P

client = TestClient(app)
EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "E64_Objectives_1_3_Completion"
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}


@pytest.fixture
def e64(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e64")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-19T09:00:00")
    try:
        return LEAD2.record()
    except LEAD2.RecordError:
        pytest.skip("no e64 record (scripts/build_record_e64.py)")


def test_lead2_alignment(e64):
    assert (e64["origin"], e64["originQuarter"], e64["targetQuarter"], e64["lead"]) == ("2026-10-01", "2026-Q3", "2027-Q1", 2)
    for v in e64["provinces"].values():
        for q, e in v["pastDrivers"].items():
            t = P.qi(e["originQuarter"])
            assert q == P.qs(t + 2) and e["origin"] == P.origin(t).strftime("%Y-%m-%d")


def test_record_equals_the_sealed_run(e64):
    sealed = EXP / "sealed" / "candidates.csv"
    want = (sealed.parent / "candidates.csv.sha256").read_text().split()[0]
    assert hashlib.sha256(sealed.read_bytes()).hexdigest() == want
    s = pd.read_csv(sealed, dtype={"province_code": str})
    k = e64["candidate"]
    for _, r in s.iterrows():
        v = e64["provinces"][r["province_code"]]
        e = v["forecast"] if r["target"] == e64["targetQuarter"] else v["pastDrivers"][r["target"]]
        assert e["probability"] == pytest.approx(r[f"{k}_p"], abs=1e-4)


def test_attribution_adds_up(e64):
    for v in e64["provinces"].values():
        blocks = list(v["pastDrivers"].values()) + [{**v, "probabilityPricePressure": v["forecast"]["components"]["probabilityPricePressure"]}]
        for b in blocks:
            z = (b["baselineLogOdds"] + sum(x["logOddsEffect"] for x in b["fiveTriggerContributions"].values())
                 + b["otherContribution"]["logOddsEffect"] + b["povertyContribution"]["logOddsEffect"])
            assert 1 / (1 + math.exp(-z)) == pytest.approx(b["probabilityPricePressure"], abs=2e-3)


def test_news_features_training_serving_parity(e64):
    for code, v in e64["provinces"].items():
        for e in list(v["pastDrivers"].values()) + [v]:
            t = P.qi(e.get("originQuarter") or e64["originQuarter"])
            now = {r["province_code"]: r for r in P.n3_features(t)}[code]
            stored = e["newsEvidence"]["features"]
            for c in P.N3_COLS:
                a, b = stored[c], now[c]
                if b is None or (isinstance(b, float) and math.isnan(b)):
                    assert a is None
                else:
                    assert a == pytest.approx(b, abs=1e-9), (code, t, c)
            assert [x["key"] for x in e["newsEvidence"]["articles"]] == now["article_keys"]


def test_news_behind_a_forecast_predates_its_issue_date(e64):
    for v in e64["provinces"].values():
        for e in list(v["pastDrivers"].values()) + [v]:
            cut = e["newsEvidence"]["issueCutoffPH"]
            for a in e["newsEvidence"]["articles"] + e["newsEvidence"]["national"]:
                assert a["publishedPH"] < cut


def test_prospective_seal(e64):
    seal = EXP / "sealed" / "prospective_2027Q1.json"
    want = (seal.parent / (seal.name + ".sha256")).read_text().split()[0]
    assert hashlib.sha256(seal.read_bytes()).hexdigest() == want
    s = json.loads(seal.read_text(encoding="utf-8"))
    assert s["target"] == "2027-Q1" and s["issued"] == "2026-10-01" and s["candidate"] == e64["candidate"]
    for r in s["forecasts"]:
        assert r["probability"] == pytest.approx(e64["provinces"][r["province_code"]]["forecast"]["probability"], abs=1e-12)


def test_dashboard_serves_the_record_and_lgus_use_it(e64):
    tq = e64["targetQuarter"]
    rows = {p["provinceCode"]: p["riskScore"] for p in client.get(f"/api/v1/provinces?quarter={tq}").json()["data"]}
    for code, v in e64["provinces"].items():
        assert rows[code] == pytest.approx(v["forecast"]["probability"], abs=5e-4)
        ex = client.get(f"/api/v1/explainability?scope=province&id={SLUG[code]}&quarter={tq}").json()
        rd = {d["driver_group"]: d["group_shap"] for d in v["drivers"]["drivers"]}
        for t in ex["triggers"]:
            assert t["signedContribution"] == pytest.approx(rd.get(t["key"], 0.0), abs=1e-6)
        assert "not a tested probability" in ex["summary"]["sentence"]
        muni = client.get(f"/api/v1/provinces/{SLUG[code]}/municipalities?quarter={tq}").json()["data"]
        p = v["forecast"]["probability"]
        assert max(m["riskIndex"] for m in muni) <= round(p, 4) + 1e-9      # index = P x vulnerability, vulnerability <= 1
    lgus = sum(len(client.get(f"/api/v1/provinces/{s}/municipalities?quarter={tq}").json()["data"]) for s in SLUG.values())
    assert lgus == 142


def test_caveat_uses_e64_backtest_count(e64):
    b = e64["assessment"]["lowPriceBacktest"]
    r = pd.read_csv(EXP / "tables" / "c2_rows50.csv")
    s = r[r[f"{e64['candidate']}_p_price"] < b["cutoff"]]
    assert (b["n"], b["high"]) == (len(s), int(s["y"].sum()))
    low = [c for c, v in e64["provinces"].items() if v["forecast"]["components"]["probabilityPricePressure"] < b["cutoff"]]
    for code in low:
        cav = client.get(f"/api/v1/explainability?scope=province&id={SLUG[code]}&quarter=2027-Q1").json()["summary"]["caveat"]
        assert f"{b['high']} of {b['n']} price-pressure probabilities below" in cav


def test_e38_default_unaffected(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    assert not LEAD2.active()


def test_lgu_rows_trace_to_the_served_forecast(e64):
    tq = e64["targetQuarter"]
    shas = set()
    for code, slug in SLUG.items():
        rows = client.get(f"/api/v1/provinces/{slug}/municipalities?quarter={tq}").json()["data"]
        again = client.get(f"/api/v1/provinces/{slug}/municipalities?quarter={tq}").json()["data"]
        assert rows == again                                                 # reproducible
        p = e64["provinces"][code]["forecast"]["probability"]
        for m in rows:
            assert m["provinceEstimate"] == pytest.approx(p, abs=1e-6)
            src = m["provinceEstimateSource"]
            assert src["mode"] == "E64_LEAD2" and src["quarter"] == tq and src["origin"] == e64["origin"]
            assert m["riskIndex"] == pytest.approx(round(min(max(p * m["vulnerabilityIndex"], 0), 1), 4), abs=1e-9)
            assert "0.6 x poverty_norm + 0.4 x density_norm" in m["rankingMethod"]
            shas.add(m["rankingRowsSha256"])
    assert len(shas) == 1                                                    # one ranking run for the 142 LGUs
