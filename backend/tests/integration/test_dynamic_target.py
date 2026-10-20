"""
tests/integration/test_dynamic_target.py
----------------------------------------
The dashboard's forecast target comes from ONE backend function (app/quarterly/target.py). By default the system serves
lead 1 only (AIPHEED_MAX_LEAD=1): the target is the calendar quarter in which it is viewed (Asia/Manila), the E36
one-quarter-ahead forecast, and the E38 lead-2 row stays in the record but is not served. AIPHEED_MAX_LEAD=2 restores
the next-calendar-quarter target. Every surface uses that target; a target without a generated forecast is reported
as unavailable, never filled with an older forecast. The clock is controlled with AIPHEED_NOW / the `now` argument.
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
from app.quarterly.alerts_e31 import candidates
from app.quarterly.target import forecast_target

client = TestClient(app)
# The E38 next-quarter procedure and the E49-C2 numbers: every test here serves the E49 record (serve_e49; the default
# is E53-A1 since the final integration, see test_e53_served_model.py).
pytestmark = pytest.mark.usefixtures("serve_e49")
REC = json.loads(Path("data/e49/e49_record.json").read_text(encoding="utf-8"))
NQ = next(q for q in REC["quarters"] if q.get("role") == "next_quarter")
CUR = next(q for q in REC["quarters"] if q.get("role") == "current_quarter")



@pytest.mark.parametrize("now,target", [
    ("2026-10-15T10:00:00", "2027-Q1"),
    ("2027-01-15T10:00:00", "2027-Q2"),
    ("2027-04-01T00:00:00", "2027-Q3"),
    ("2027-07-20T12:00:00", "2027-Q4"),
    ("2027-10-05T08:00:00", "2028-Q1"),
    ("2026-12-31T23:59:59", "2027-Q1"),          # last second of December (PHT)
    ("2027-01-01T00:00:00", "2027-Q2"),          # first second of January (PHT)
    ("2026-12-31T16:30:00+00:00", "2027-Q2"),    # 00:30 on 1 January in Manila, still 31 December in UTC
    ("2027-03-31T15:59:59+00:00", "2027-Q2"),    # 23:59:59 PHT on 31 March
])
def test_target_is_the_next_calendar_quarter_in_manila_at_lead_2(lead2, now, target):
    t = forecast_target(now)
    assert t["target_quarter"] == target
    y, q = int(target[:4]), int(target[-1])
    cal = f"{y if q > 1 else y - 1}-Q{q - 1 if q > 1 else 4}"
    assert t["calendar_quarter"] == cal
    assert t["origin"] == f"{cal[:4]}-{3 * int(cal[-1]) - 2:02d}-01"


@pytest.mark.parametrize("now,target", [
    ("2026-10-15T10:00:00", "2026-Q4"),
    ("2026-12-31T23:59:59", "2026-Q4"),
    ("2027-01-01T00:00:00", "2027-Q1"),
    ("2026-12-31T16:30:00+00:00", "2027-Q1"),    # 00:30 on 1 January in Manila
])
def test_default_target_is_the_current_calendar_quarter_lead_1(now, target):
    t = forecast_target(now)
    assert t["target_quarter"] == target == t["calendar_quarter"]
    assert t["lead_from_latest_data_quarter"] == 1
    assert t["origin"] == f"{target[:4]}-{3 * int(target[-1]) - 2:02d}-01"


def test_target_advances_with_the_clock_and_is_not_hard_coded(monkeypatch):
    seen = set()
    for now in ("2026-11-01", "2027-02-01", "2027-05-01", "2027-08-01", "2027-11-01"):
        monkeypatch.setenv("AIPHEED_NOW", now + "T09:00:00")
        seen.add(forecast_target()["target_quarter"])
    assert seen == {"2026-Q4", "2027-Q1", "2027-Q2", "2027-Q3", "2027-Q4"}


def test_on_15_october_2026_every_surface_shows_the_lead_1_forecast_for_2026_q4(monkeypatch):
    # lead 1 only: the lead-2 preview (on by default since the final integration) is turned off here
    monkeypatch.setenv("AIPHEED_LEAD2_PREVIEW", "0")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    q = client.get("/api/v1/quarters?horizon=nowcast").json()
    assert q["current"] == "2026-Q4" and q["calendarQuarter"] == "2026-Q4"
    assert q["forecastTarget"]["target_quarter"] == "2026-Q4" and q["forecastTarget"]["available"] is True
    assert "2027-Q1" not in [x["id"] for x in q["quarters"]] and q["quarters"][-1]["id"] == "2026-Q4"
    cfg = client.get("/api/v1/config").json()
    assert "2027-Q1" not in cfg["quarterRange"]["forecastQuarters"]
    prov = {r["provinceCode"]: r for r in client.get("/api/v1/provinces").json()["data"]}       # default quarter
    for code, v in CUR["provinces"].items():
        assert prov[code]["currentQuarter"] == "2026-Q4"
        assert prov[code]["riskScore"] == pytest.approx(v["p_high"])
    region = client.get("/api/v1/forecast?scope=region&id=calabarzon").json()
    assert region["quarter"] == "2026-Q4"
    assert region["riskScore"] == pytest.approx(sum(v["p_high"] for v in CUR["provinces"].values()) / 5, abs=1e-4)
    assert client.get("/api/v1/provinces/laguna/municipalities").json()["quarter"] == "2026-Q4"
    assert client.get("/api/v1/explainability?scope=province&id=batangas").json()["quarter"] == "2026-Q4"
    for path in ("/api/v1/provinces?quarter=2027-Q1", "/api/v1/forecast?scope=region&id=calabarzon&quarter=2027-Q1",
                 "/api/v1/explainability?scope=province&id=laguna&quarter=2027-Q1"):
        assert client.get(path).status_code == 404                 # the lead-2 forecast is not served
    assert NQ["quarter"] == "2027-Q1" and NQ["lead"] == 2           # ... but stays in the record


def test_on_15_october_2026_every_surface_targets_2027_q1_at_lead_2(lead2, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    q = client.get("/api/v1/quarters?horizon=nowcast").json()
    # the quarter under way stays current; the lead-2 target is listed (and served) as a forecast
    assert q["current"] == "2026-Q4" and q["calendarQuarter"] == "2026-Q4"
    assert q["forecastTarget"]["target_quarter"] == "2027-Q1" and q["forecastTarget"]["available"] is True
    assert next(x for x in q["quarters"] if x["id"] == "2027-Q1")["state"] == "forecast"
    cfg = client.get("/api/v1/config").json()
    assert cfg["quarterRange"]["forecastTarget"]["target_quarter"] == "2027-Q1"
    assert "2027-Q1" in cfg["quarterRange"]["forecastQuarters"]
    prov = {r["provinceCode"]: r for r in client.get("/api/v1/provinces?quarter=2027-Q1").json()["data"]}
    for code, v in NQ["provinces"].items():
        assert prov[code]["currentQuarter"] == "2027-Q1"
        assert prov[code]["riskScore"] == pytest.approx(v["p_high"])
        assert "Next quarter" in prov[code]["horizonLabel"]
    # LGU ranking: the record (and PDF) and the municipal API are computed from the same 2027-Q1 probabilities
    rec_rows = {r["lgu_code"]: r for r in REC["lgu_ranking"]["rows"]}
    assert all(r["province_probability"] == pytest.approx(NQ["provinces"][r["province_code"]]["p_high"])
               for r in REC["lgu_ranking"]["rows"])
    muni = client.get("/api/v1/provinces/laguna/municipalities?quarter=2027-Q1").json()
    assert muni["quarter"] == "2027-Q1"
    for row in muni["data"]:
        assert row["riskIndex"] == pytest.approx(rec_rows[row["lguCode"]]["risk_index"], abs=1e-4)
    ex = client.get("/api/v1/explainability?scope=province&id=batangas&quarter=2027-Q1").json()
    assert ex["quarter"] == "2027-Q1"
    pdf = client.get("/api/v1/quarterly/e31/report.pdf")
    assert pdf.status_code == 200 and pdf.headers["X-Record-SHA256"] == REC["content_sha256"]


def test_a_target_without_a_forecast_is_unavailable_not_relabelled(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_PREVIEW", "0")                 # lead 1 only (the preview would serve 2027-Q1)
    monkeypatch.setenv("AIPHEED_NOW", "2027-01-15T09:00:00")
    q = client.get("/api/v1/quarters?horizon=nowcast").json()
    # lead 1: the 2027-Q1 target has no lead-1 forecast (the E38 lead-2 row is not served)
    assert q["forecastTarget"]["target_quarter"] == "2027-Q1" and q["forecastTarget"]["available"] is False
    last = q["quarters"][-1]
    assert last["id"] == "2027-Q1" and last["state"] == "unavailable" and "has not been generated" in last["reason"]
    assert q["current"] == "2026-Q4"                                  # newest existing forecast, under its own id
    r = client.get("/api/v1/provinces?quarter=2027-Q1")
    assert r.status_code == 404


def test_a_target_without_a_forecast_is_unavailable_not_relabelled_at_lead_2(lead2, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2027-01-15T09:00:00")
    q = client.get("/api/v1/quarters?horizon=nowcast").json()
    assert q["forecastTarget"]["target_quarter"] == "2027-Q2" and q["forecastTarget"]["available"] is False
    last = q["quarters"][-1]
    assert last["id"] == "2027-Q2" and last["state"] == "unavailable" and "has not been generated" in last["reason"]
    assert q["current"] == "2027-Q1"
    r = client.get("/api/v1/provinces?quarter=2027-Q2")
    assert r.status_code == 404


def test_historical_current_and_next_quarter_rows_are_distinguishable():
    roles = [q.get("role") for q in REC["quarters"]]
    assert roles.count("backtest") == 13 and roles[-2:] == ["current_quarter", "next_quarter"]
    cur = REC["quarters"][-2]
    assert cur["quarter"] == "2026-Q4" and cur["lead"] == 1 and NQ["quarter"] == "2027-Q1" and NQ["lead"] == 2
    assert all("observed_label" in v for q in REC["quarters"] if q["role"] == "backtest" for v in q["provinces"].values())
    assert not any("observed_label" in v for q in REC["quarters"][-2:] for v in q["provinces"].values())


def test_next_quarter_forecast_is_frozen_reproducible_and_cutoff_bound():
    fr = Path("data/e36/model/E38_PROSPECTIVE_2027Q1.json")
    want = Path("data/e36/model/E38_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    assert hashlib.sha256(fr.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == want
    f = json.loads(fr.read_text(encoding="utf-8"))
    assert f["origin"] == "2026-10-01" and f["latest_label_quarter"] == "2026-Q2"   # Sept round posted 2026-10-14
    assert NQ["provenance"]["news_evidence_window"]["evidence_quarter"] == "2026-Q3"
    import lightgbm as lgb

    cfg = json.loads(Path("data/e36/model/E38-LGBM-NQ_O2026-10-01_lead2.json").read_text(encoding="utf-8"))
    txt = Path("data/e36/model/E38-LGBM-NQ_O2026-10-01_lead2.txt").read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(txt).hexdigest() == cfg["artifact_sha256_lf"]
    booster = lgb.Booster(model_str=txt.decode("utf-8"))
    for code, v in f["provinces"].items():
        val = {d["key"]: d["value"] for d in v["drivers"]}
        x = pd.DataFrame([[math.nan if val[k] is None else val[k] for k in cfg["features"]]], columns=cfg["features"])
        raw = booster.predict(x, raw_score=True)[0] + cfg["prior_shift_logodds"]
        assert 1 / (1 + math.exp(-raw)) == pytest.approx(v["p_high"], abs=1e-6)
        assert NQ["provinces"][code]["p_high"] == pytest.approx(v["p_high"], abs=5e-5)


def test_five_triggers_keep_their_identity_and_follow_the_model(monkeypatch):
    """Market = |SHAP of the price inputs + trig_market| (+ its news share); each other driver = |SHAP of its trigger
    proportion| (+ its news share); the news inputs' |SHAP| is split by the topics of the validated titles behind them
    (province titles for news_n / news_direct_share, the region's for news_reg); the rest is not shown."""
    from app.ml.inference import e31_engine as E31

    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    groups = ["market", "climate", "fish_kill", "employment", "ofw_remittance"]
    for scope, ident in (("province", "batangas"), ("province", "laguna"), ("region", "calabarzon")):
        ex = client.get(f"/api/v1/explainability?scope={scope}&id={ident}").json()
        assert ex["quarter"] == "2026-Q4"
        keys = [t["key"] for t in ex["triggers"]]
        # all five groups are listed (a 0% group had no measurable effect) and the shares add up to 100
        assert sorted(keys) == sorted(groups) and sum(t["pct"] for t in ex["triggers"]) == 100
    ev = CUR["provenance"]["news_evidence_window"]["evidence_quarter"]
    for code, slug in (("PH040500000", "batangas"), ("PH040200000", "laguna")):
        shap = {d["key"]: d["contribution"] for d in CUR["provinces"][code]["drivers"]}
        sp, _ = E31.news_topic_shares(code, ev)
        sr, _ = E31.news_topic_shares(None, ev)
        a_p = abs(shap.get("news_n", 0)) + abs(shap.get("news_direct_share", 0))
        a_r = abs(shap.get("news_reg", 0))
        want = {g: a_p * sp[g] + a_r * sr[g] + abs(sum(shap.get(f, 0.0) for f in E31.TRIGGER_GROUP_FEATURES[g]))
                for g in groups}
        ex = client.get(f"/api/v1/explainability?scope=province&id={slug}").json()
        by = {t["key"]: t for t in ex["triggers"]}
        for g in groups:                                           # every group is listed, 0% ones included
            assert abs(by[g]["signedContribution"]) == pytest.approx(want[g], abs=2e-4)
        assert sum(want.values()) > 0
    laguna = {t["key"]: t["pct"] for t in client.get("/api/v1/explainability?scope=province&id=laguna").json()["triggers"]}
    assert laguna["fish_kill"] > 0 and laguna["market"] < 100          # fish-kill titles in Laguna, 2026-Q3
    assert "topic of the news titles" in ex["note"] and "only Market / Prices" not in ex["note"]
    region = client.get("/api/v1/forecast?scope=region&id=calabarzon").json()
    assert region["riskScore"] == pytest.approx(0.7784, abs=1e-4)      # E49-C2 forecast index


def test_alert_candidates_use_only_the_target_quarter(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    c = candidates(REC)
    assert {x["quarter"] for x in c} <= {"2026-Q4"}             # lead 1: only the 2026-Q4 forecast can stage alerts
    assert all("Not an official" in x["statement"] for x in c)
    assert not [x for x in candidates(REC, "all") if x["quarter"] == "2027-Q1"]   # the lead-2 row never stages
    monkeypatch.setenv("AIPHEED_NOW", "2027-01-15T09:00:00")
    assert candidates(REC) == []                               # 2027-Q1 has no lead-1 forecast: nothing to stage


def test_alert_candidates_use_only_the_target_quarter_at_lead_2(lead2, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    c = candidates(REC)
    assert c and {x["quarter"] for x in c} == {"2027-Q1"}
    monkeypatch.setenv("AIPHEED_NOW", "2027-01-15T09:00:00")
    assert candidates(REC) == []                               # 2027-Q2 has no forecast: nothing to stage


@pytest.mark.parametrize("viewed,latest,current,target", [
    ("2026-11-15T09:00:00", "2026-Q3", "2026-Q4", "2027-Q1"),
    ("2027-02-15T09:00:00", "2026-Q4", "2027-Q1", "2027-Q2"),
    ("2027-05-15T09:00:00", "2027-Q1", "2027-Q2", "2027-Q3"),
    ("2027-08-15T09:00:00", "2027-Q2", "2027-Q3", "2027-Q4"),
    ("2031-12-31T23:00:00", "2031-Q3", "2031-Q4", "2032-Q1"),
])
def test_dashboard_rule_table_e44(lead2, viewed, latest, current, target):
    """E44 brief: viewing quarter q -> latest completed q-1 -> target q+1 (= Lead 2 from q-1); never hard-coded.
    That is the lead-2 configuration (AIPHEED_MAX_LEAD=2, the lead2 fixture); the default serves lead 1 with the
    lead-2 row as a labelled preview (E53 port)."""
    from app.quarterly.target import forecast_target, shift

    ft = forecast_target(viewed)
    assert (ft["latest_complete_data_quarter"], ft["calendar_quarter"], ft["target_quarter"]) == (latest, current, target)
    assert shift(ft["latest_complete_data_quarter"], ft["lead_from_latest_data_quarter"]) == ft["target_quarter"]
