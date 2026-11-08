"""FI9 tests: quarter arithmetic, pure inference, leakage (future poisoning), protocol lock, audit, API, LGU mapping."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.fi9 import MODEL, OUT
from app.fi9 import quarters as Q


@pytest.mark.parametrize("date,cur,target", [
    ("2026-11-03", "2026-Q4", "2027-Q1"), ("2026-12-31", "2026-Q4", "2027-Q1"), ("2027-01-01", "2027-Q1", "2027-Q2"),
    ("2027-06-30", "2027-Q2", "2027-Q3"), ("2027-09-30", "2027-Q3", "2027-Q4"), ("2027-10-01", "2027-Q4", "2028-Q1"),
])
def test_lead1_is_next_calendar_quarter(date, cur, target):
    r = Q.lead1(date)
    assert (r["current_quarter"], r["target_quarter"], r["horizon"]) == (cur, target, 1)
    assert Q.index(Q.label(Q.qi_of(date))) == Q.qi_of(date)


def test_scheduled_issue_is_end_of_second_month():
    assert Q.scheduled_issue(Q.index("2027-Q1")).date().isoformat() == "2027-02-28"
    assert Q.scheduled_issue(Q.index("2028-Q1")).date().isoformat() == "2028-02-29"
    assert Q.end(Q.index("2026-Q4")).date().isoformat() == "2026-12-31"


ART = {"kind": "damped_tau", "params": {"phi": 0.67, "sigma": 4.5, "tau": 0.125}}
ROW = {"hunger_last": 22.0, "baseline_known": 15.0, "hunger_age_q": 2, "threshold_known": 20.0, "moe_last": 2.5}


def test_inference_is_pure_bounded_and_rejects_missing_inputs():
    from app.fi9.serve import predict
    a, b = predict(ART, ROW), predict(ART, dict(ROW))
    assert a == b and 0 <= a["p_high"] <= 1
    assert a["level_pp"] == pytest.approx(15 + 0.67 ** 2 * 7)
    assert predict(ART, {**ROW, "hunger_last": 60})["class"] == "HIGH"
    assert predict(ART, {**ROW, "hunger_last": 5, "baseline_known": 5})["p_high"] < 0.01
    with pytest.raises(ValueError):
        predict(ART, {**ROW, "baseline_known": np.nan})
    with pytest.raises(ValueError):
        predict(ART, {k: v for k, v in ROW.items() if k != "threshold_known"})


def test_future_records_cannot_change_a_historical_row():
    """Poison every source with absurd values that become available after the issue date: the row must not move."""
    from app.fi5.features import FeatureBuilder
    fb = FeatureBuilder()
    issue_qi, d = Q.index("2019-Q2"), pd.Timestamp("2019-05-31")
    before = fb.row(issue_qi, issue_qi + 1, issue_date=d)
    for attr in ["cpi", "palay", "lfs", "remit", "poverty", "oni", "nasa"]:
        df = getattr(fb, attr).copy()
        fut = df.tail(3).copy()
        num = fut.select_dtypes("number").columns.difference(["year", "month"])
        fut[num] = 999.0
        fut["available_from"] = d + pd.Timedelta(days=1)
        fb.__dict__[attr] = pd.concat([df, fut], ignore_index=True)
    sws = fb.sws.copy()
    fut = sws.tail(2).copy().assign(hunger=99.0, published=d + pd.Timedelta(days=1))
    fb.__dict__["sws"] = pd.concat([sws, fut], ignore_index=True)
    after = fb.row(issue_qi, issue_qi + 1, issue_date=d)
    for k, v in before.items():
        assert (pd.isna(v) and pd.isna(after[k])) or v == after[k], k


def test_forecast_time_dataset_leakage_checks():
    chk = json.loads((OUT / "leakage_checks.json").read_text())
    assert all(v for k, v in chk.items() if not k.startswith("n_"))
    X = pd.read_csv(OUT / "forecast_time_dataset_h1.csv")
    assert (X["target_quarter"].map(Q.index) - X["issue_quarter"].map(Q.index) == 1).all()


def test_protocol_lock_detects_changes(monkeypatch):
    from app.fi9 import protocol as P
    assert P.check() == json.loads((OUT / "PROTOCOL_LOCK.json").read_text())["sha256"]
    monkeypatch.setitem(P.PROTOCOL, "split", {"development_target_years": [2010, 2020], "test_target_years": [2021, 2100]})
    with pytest.raises(RuntimeError):
        P.check()


def test_selection_and_audit():
    ev = json.loads((OUT / "lead1_evaluation.json").read_text())
    au = json.loads((OUT / "audit.json").read_text())
    assert au["all_passed"], [k for k, v in au["checks"].items() if not v]
    assert ev["reproduces_fi7_lead1"]["max_abs_p_diff"] < 1e-9
    assert ev["selection"]["lead1_status"] in ("provisional", "validated (regional)")
    sel = ev["selection"]
    assert sel["lead1_status"] == ("validated (regional)" if all(sel["validated_lead1_checks"].values()) else "provisional")


def test_ece_and_calibration_line():
    from app.fi9.evaluate import calib_line, ece
    rng = np.random.default_rng(3)
    p = rng.uniform(0, 1, 5000)
    y = (rng.uniform(0, 1, 5000) < p).astype(int)
    assert ece(y, p) < 0.03
    cl = calib_line(y, p)
    assert abs(cl["slope"] - 1) < 0.15 and abs(cl["intercept"]) < 0.15


def test_lgu_priority_mapping():
    t = pd.read_csv(OUT / "lgu_priority.csv", dtype={"lgu_psgc": str})
    assert len(t) == 142 and t["lgu_psgc"].is_unique
    assert t.groupby("province_name").size().to_dict() == {"Batangas": 34, "Cavite": 23, "Laguna": 30, "Quezon": 41, "Rizal": 14}
    assert t["forecast_status"].str.contains("not measured or forecast hunger").all()


def test_api_fi9(monkeypatch):
    from app.main import app
    c = TestClient(app)
    f = json.loads((OUT / "forecast.json").read_text())
    monkeypatch.setenv("AIPHEED_NOW", f["issue_date"])
    r = c.get("/api/v1/fi9/outlook")
    assert r.status_code == 200
    b = r.json()
    assert b["target_quarter"] == Q.lead1(f["issue_date"])["target_quarter"] and b["horizon"].startswith("Lead 1")
    assert b["artifact_sha256"] == json.loads((MODEL / "lead1_model.json").read_text())["sha256"]
    assert b["status"] in ("provisional", "validated") and "Balance Luzon" in b["geographic_scope"]
    nxt = Q.start(Q.index(f["issue_quarter"]) + 1) + pd.Timedelta(days=40)
    monkeypatch.setenv("AIPHEED_NOW", nxt.date().isoformat())
    r = c.get("/api/v1/fi9/outlook")
    assert r.status_code == 503 and r.json()["detail"]["status"] == "stale"
    assert c.get("/api/v1/fi9/quarters", params={"date": "2027-12-31"}).json()["target_quarter"] == "2028-Q1"
    assert c.get("/api/v1/fi9/quarters", params={"date": "not-a-date"}).status_code == 422
    assert c.get("/api/v1/fi9/priority").json()["n"] == 142
    assert c.get("/api/v1/fi9/priority", params={"province": "Atlantis"}).status_code == 404
    assert c.get("/api/v1/fi9/priority", params={"lgu_psgc": "000000000"}).status_code == 404
    assert c.get("/api/v1/fi9/evaluation", params={"period": "bogus"}).status_code == 422
    e = c.get("/api/v1/fi9/evaluation", params={"period": "test"}).json()
    assert e["selection"]["selected"] == b["model"]
    assert c.get("/api/v1/fi9/model").json()["artifact"]["model"] == b["model"]
    assert c.get("/api/v1/fi9/audit").json()["all_passed"]
