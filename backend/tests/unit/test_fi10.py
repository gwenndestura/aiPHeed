"""FI10 tests: as-of availability, target construction, lock/amendment, recomputation, serving, API, register."""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.fi9 import prospective as PR
from app.fi9 import quarters as Q
from app.fi9z.classmetrics import class_metrics
from app.fi10 import OUT, PROVINCES

D = pd.read_csv(OUT / "dataset.csv", parse_dates=["issue_date", "target_published"])
E = json.loads((OUT / "evaluation.json").read_text())


def test_lock_and_amendment():
    from app.fi10.study import _digest
    lock = json.loads((OUT / "PROTOCOL_LOCK.json").read_text())
    am = json.loads((OUT / "AMENDMENT_1.json").read_text())
    assert lock["sha256"] == _digest() == E["protocol_sha256"]
    assert am["locked_code_sha256"] == lock["code_sha256"]
    assert hashlib.sha256((OUT / "dataset.csv").read_bytes()).hexdigest() == am["dataset_sha256"]


def test_inputs_were_available_at_issue_and_targets_are_future():
    cpi_avail = D["cpi_month"].map(lambda m: pd.Timestamp(year=(m + 1) // 12, month=(m + 1) % 12 + 1, day=10))
    assert (cpi_avail <= D["issue_date"]).all()
    L = D[D["y"].notna()]
    assert (L["target_published"] > L["issue_date"]).all()
    assert (D["target_quarter"].map(Q.index) == D["issue_quarter"].map(Q.index) + D["lead"]).all()
    assert set(D["province"]) == set(PROVINCES)


def test_target_uses_only_earlier_quarters():
    from app.fi10.data import cpi_monthly, quarterly_target
    T = quarterly_target(cpi_monthly())
    r = T[(T["province"] == "Quezon") & (T["quarter"] == "2022-Q4")].iloc[0]
    prev = T[(T["province"] == "Quezon") & (T["qi"] >= r["qi"] - 20) & (T["qi"] < r["qi"])]["level"]
    assert r["threshold"] == pytest.approx(prev.mean() + prev.std(ddof=1))
    assert r["y"] == float(r["level"] > r["threshold"])


def test_reported_test_metrics_recompute():
    W = pd.read_csv(OUT / "predictions.csv")
    W = W[W["target_quarter"].str[:4].astype(int) >= 2016]
    for (lead, c), g in W.groupby(["lead", "config"]):
        rep = E["by_lead"][str(lead)][c]["test"]
        mine = class_metrics(g["y"], g["cls"], g["p"])
        for k in ("tp", "fp", "fn", "tn", "balanced_accuracy", "brier"):
            assert (mine[k] is None and rep[k] is None) or abs(mine[k] - rep[k]) < 1e-9, (lead, c, k)


def test_no_lead_adopted_and_outputs_say_provisional():
    assert E["max_reliable_lead"] is None and not any(s["adopt"] for s in E["selection"].values())
    f = json.loads((OUT / "forecast.json").read_text())
    assert all(v["status"].startswith("provisional") for v in f["leads"].values())
    assert "not issued" in f["lead_status"]["3"] and "not a measure of food insecurity" in f["what_is_forecast"]


def test_served_outlook_is_consistent():
    f = json.loads((OUT / "forecast.json").read_text())
    assert [p["province"] for p in f["provinces"]] == PROVINCES
    for h in ("1", "2"):
        thr = f["leads"][h]["decision_threshold"]
        for p in f["leads"][h]["provinces"]:
            assert Q.index(p["target_quarter"]) == Q.index(f["issue_quarter"]) + int(h)
            assert p["class"] == ("HIGH" if p["p_high"] + 0.005 >= thr and (p["p_high"] - 0.005 >= thr or p["class"] == "HIGH") else "LOW")
            assert 0 <= p["p_high"] <= 1 and p["p_low"] == pytest.approx(1 - p["p_high"], abs=0.011)
    assert PR.verify(OUT / "register.jsonl")


def test_api_fi10(monkeypatch):
    from app.main import app
    c = TestClient(app)
    f = json.loads((OUT / "forecast.json").read_text())
    monkeypatch.setenv("AIPHEED_NOW", f["issue_date"])
    r = c.get("/api/v1/fi10/provinces")
    assert r.status_code == 200 and len(r.json()["provinces"]) == 5
    nxt = Q.start(Q.index(f["issue_quarter"]) + 1) + pd.Timedelta(days=10)
    monkeypatch.setenv("AIPHEED_NOW", nxt.date().isoformat())
    assert c.get("/api/v1/fi10/provinces").status_code == 503
    e = c.get("/api/v1/fi10/evaluation").json()
    assert e["max_reliable_lead"] is None and "1" in e["by_lead"]
