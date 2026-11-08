"""
tests/integration/test_dynamic_target.py
----------------------------------------
The dashboard forecasts the calendar quarter after the one in which it is viewed (Asia/Manila), from ONE backend
function (app/quarterly/target.py). Every surface uses that target; a target without a generated forecast is reported
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
REC = json.loads(Path("data/e36/e36_record.json").read_text(encoding="utf-8"))
NQ = next(q for q in REC["quarters"] if q.get("role") == "next_quarter")


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
def test_target_is_the_next_calendar_quarter_in_manila(now, target):
    t = forecast_target(now)
    assert t["target_quarter"] == target
    y, q = int(target[:4]), int(target[-1])
    cal = f"{y if q > 1 else y - 1}-Q{q - 1 if q > 1 else 4}"
    assert t["calendar_quarter"] == cal
    assert t["origin"] == f"{cal[:4]}-{3 * int(cal[-1]) - 2:02d}-01"


def test_target_advances_with_the_clock_and_is_not_hard_coded(monkeypatch):
    seen = set()
    for now in ("2026-11-01", "2027-02-01", "2027-05-01", "2027-08-01", "2027-11-01"):
        monkeypatch.setenv("AIPHEED_NOW", now + "T09:00:00")
        seen.add(forecast_target()["target_quarter"])
    assert seen == {"2027-Q1", "2027-Q2", "2027-Q3", "2027-Q4", "2028-Q1"}


def test_on_15_october_2026_every_surface_targets_2027_q1(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    q = client.get("/api/v1/quarters?horizon=nowcast").json()
    assert q["current"] == "2027-Q1" and q["calendarQuarter"] == "2026-Q4"
    assert q["forecastTarget"]["target_quarter"] == "2027-Q1" and q["forecastTarget"]["available"] is True
    cfg = client.get("/api/v1/config").json()
    assert cfg["quarterRange"]["forecastTarget"]["target_quarter"] == "2027-Q1"
    assert "2027-Q1" in cfg["quarterRange"]["forecastQuarters"]
    prov = {r["provinceCode"]: r for r in client.get("/api/v1/provinces").json()["data"]}       # default quarter
    for code, v in NQ["provinces"].items():
        assert prov[code]["currentQuarter"] == "2027-Q1"
        assert prov[code]["riskScore"] == pytest.approx(v["p_high"])
        assert "Next quarter" in prov[code]["horizonLabel"]
    # LGU ranking: the record (and PDF) and the municipal API are computed from the same 2027-Q1 probabilities
    rec_rows = {r["lgu_code"]: r for r in REC["lgu_ranking"]["rows"]}
    assert all(r["province_probability"] == pytest.approx(NQ["provinces"][r["province_code"]]["p_high"])
               for r in REC["lgu_ranking"]["rows"])
    muni = client.get("/api/v1/provinces/laguna/municipalities").json()
    assert muni["quarter"] == "2027-Q1"
    for row in muni["data"]:
        assert row["riskIndex"] == pytest.approx(rec_rows[row["lguCode"]]["risk_index"], abs=1e-4)
    ex = client.get("/api/v1/explainability?scope=province&id=batangas").json()
    assert ex["quarter"] == "2027-Q1"
    pdf = client.get("/api/v1/quarterly/e31/report.pdf")
    assert pdf.status_code == 200 and pdf.headers["X-Record-SHA256"] == REC["content_sha256"]


def test_a_target_without_a_forecast_is_unavailable_not_relabelled(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2027-01-15T09:00:00")
    q = client.get("/api/v1/quarters?horizon=nowcast").json()
    assert q["forecastTarget"]["target_quarter"] == "2027-Q2" and q["forecastTarget"]["available"] is False
    last = q["quarters"][-1]
    assert last["id"] == "2027-Q2" and last["state"] == "unavailable" and "has not been generated" in last["reason"]
    assert q["current"] == "2027-Q1"                                  # newest existing forecast, under its own id
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
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    for scope, ident in (("province", "batangas"), ("province", "laguna"), ("region", "calabarzon")):
        ex = client.get(f"/api/v1/explainability?scope={scope}&id={ident}").json()
        keys = [t["key"] for t in ex["triggers"]]
        assert sorted(keys) == sorted(["market", "climate", "fish_kill", "employment", "ofw_remittance"])
        assert len(keys) == 5 and sum(t["pct"] for t in ex["triggers"]) in (100, 0)
        by = {t["key"]: t for t in ex["triggers"]}
        for k in ("climate", "fish_kill", "employment", "ofw_remittance"):
            assert by[k]["signedContribution"] == 0.0          # no input of the served model
    v = NQ["provinces"]["PH040500000"]
    price = sum(d["contribution"] for d in v["drivers"] if d["key"] in ("D_last", "Dnow", "rice_rel"))
    ex = client.get("/api/v1/explainability?scope=province&id=batangas").json()
    m = next(t for t in ex["triggers"] if t["key"] == "market")
    assert m["signedContribution"] == pytest.approx(price, abs=2e-3)
    assert m["direction"] == ("increases_risk" if price >= 0 else "protective")
    assert "only Market / Prices" in ex["note"]


def test_alert_candidates_use_only_the_target_quarter(monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-15T09:00:00")
    c = candidates(REC)
    assert c and {x["quarter"] for x in c} == {"2027-Q1"}
    assert all("Not an official" in x["statement"] for x in c)
    monkeypatch.setenv("AIPHEED_NOW", "2027-01-15T09:00:00")
    assert candidates(REC) == []                               # 2027-Q2 has no forecast: nothing to stage


@pytest.mark.parametrize("viewed,latest,current,target", [
    ("2026-11-15T09:00:00", "2026-Q3", "2026-Q4", "2027-Q1"),
    ("2027-02-15T09:00:00", "2026-Q4", "2027-Q1", "2027-Q2"),
    ("2027-05-15T09:00:00", "2027-Q1", "2027-Q2", "2027-Q3"),
    ("2027-08-15T09:00:00", "2027-Q2", "2027-Q3", "2027-Q4"),
    ("2031-12-31T23:00:00", "2031-Q3", "2031-Q4", "2032-Q1"),
])
def test_dashboard_rule_table_e44(viewed, latest, current, target):
    """E44 brief: viewing quarter q -> latest completed q-1 -> target q+1 (= Lead 2 from q-1); never hard-coded."""
    from app.quarterly.target import forecast_target, shift

    ft = forecast_target(viewed)
    assert (ft["latest_complete_data_quarter"], ft["calendar_quarter"], ft["target_quarter"]) == (latest, current, target)
    assert shift(ft["latest_complete_data_quarter"], ft["lead_from_latest_data_quarter"]) == ft["target_quarter"]
