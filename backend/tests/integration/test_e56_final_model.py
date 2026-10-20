"""
tests/integration/test_e56_final_model.py
-----------------------------------------
AIPHEED_LEAD2_MODEL=e56 serves the final model of the E56 LightGBM optimization cycle (two-quarter food-insecurity risk,
target T43). These tests check that:
  * the served 2027-Q1 probabilities are reproduced from the saved artifacts ALONE (LightGBM booster text, offset and
    hunger parameters, feature rows), without the training code, and equal the frozen prospective file;
  * the artifacts match their manifest;
  * the horizon and data freshness are stated (predictor quarter 2026-Q3 -> target 2027-Q1; latest target data known
    at issue 2026-Q2), and the API exposes them;
  * the TreeSHAP explanations reconstruct the price log-odds;
  * the record serves only its own target quarter (no stale forecast when the clock moves to 2027-Q1);
  * the production default stays E38 (rollback).
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from scipy.stats import multivariate_normal, norm

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2
from app.quarterly.target import forecast_target

client = TestClient(app)
ART = Path("data/e56/model")
EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "E56_LightGBM_Optimization"
FROZEN = EXP / "frozen" / "E56_TUNED_PROSPECTIVE_2027Q1.json"


@pytest.fixture
def e56(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e56")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")


def _reproduce() -> dict[str, float]:
    import lightgbm as lgb
    off = json.loads((ART / "offset.json").read_text())
    hun = json.loads((ART / "hunger.json").read_text())
    schema = [f["name"] for f in json.loads((ART / "feature_schema.json").read_text())["features"]]
    rows = pd.read_csv(ART / "features_2027Q1.csv", dtype={"province_code": str})
    booster = lgb.Booster(model_str=(ART / "booster.txt").read_text(encoding="utf-8").replace("\r\n", "\n"))
    assert booster.feature_name() == schema
    m = off["drift_multiplier"]
    rho = off["error_correlation"]
    bvn = multivariate_normal(mean=[0, 0], cov=[[1, rho], [rho, 1]])
    h_hat = hun["H_base"] + hun["intercept"] + sum(hun["z_row"][k] * hun["coef"][k] for k in hun["coef"])
    p_hunger = 1 - norm.cdf((hun["threshold_H"] - h_hat) / hun["rmse"])
    raw = booster.predict(rows[schema].astype(float), raw_score=True)
    out = {}
    for i, r in rows.iterrows():
        zf = (off["threshold_food"][r["province_code"]] - r[f"base_{m}"]) / off["food_rmse"]
        zg = (off["threshold_gap"][r["province_code"]] - r[f"gbase_{m}"]) / off["gap_rmse"]
        ps = min(max(1 - float(bvn.cdf([zf, zg])), 1e-12), 1 - 1e-12)
        init = float(np.clip(math.log(ps / (1 - ps)), -off["logit_clip"], off["logit_clip"]))
        p_price = 1 / (1 + math.exp(-(init + raw[i] - off["tree_mean_constant"])))
        out[r["province_code"]] = p_hunger * p_price
    return out


def test_manifest_matches_artifacts():
    man = json.loads((ART / "manifest.json").read_text())
    assert set(man) == {"booster.txt", "config.json", "feature_schema.json", "features_2027Q1.csv", "hunger.json", "offset.json"}
    for name, sha in man.items():
        assert hashlib.sha256((ART / name).read_bytes()).hexdigest() == sha


def test_served_forecast_reproduced_from_saved_model(e56):
    rec = LEAD2.record()
    rep = _reproduce()
    frozen = json.loads(FROZEN.read_text())
    assert rec["modelFamily"] == "LightGBM" and rec["targetQuarter"] == frozen["targetQuarter"] == "2027-Q1"
    assert rec["finalModelArtifacts"] == json.loads((ART / "manifest.json").read_text())
    for code, v in rec["provinces"].items():
        assert v["forecast"]["probability"] == pytest.approx(rep[code], abs=1e-9)
        assert frozen["forecasts"][code]["p"] == pytest.approx(rep[code], abs=1e-6)


def test_horizon_and_freshness_are_disclosed(e56):
    f = LEAD2.record()["dataFreshness"]
    assert (f["predictorQuarter"], f["intermediateQuarter"], f["targetQuarter"], f["horizonQuarters"]) == \
           ("2026-Q3", "2026-Q4", "2027-Q1", 2)
    assert f["latestTargetQuarterKnownAtIssue"] == "2026-Q2" and f["latestTargetQuarterInData"] == "2026-Q3"
    s = client.get("/api/v1/lead2/summary").json()
    assert s["dataFreshness"]["targetQuarter"] == "2027-Q1" and s["timing"]["targetQuarter"] == "2027-Q1"
    rows = client.get("/api/v1/provinces?quarter=2027-Q1&horizon=nowcast").json()
    assert rows["indicator"]["horizon"].startswith("two-quarter-ahead forecast issued 2026-10-01 from predictors through 2026-Q3")
    assert "2026-Q2" in rows["indicator"]["horizon"]


def test_treeshap_reconstructs_and_note_is_e56(e56):
    rec = LEAD2.record()
    for v in rec["provinces"].values():
        for e in [v] + list(v["pastDrivers"].values()):
            assert e["checks"]["treeshap_reconstruction_error"] < 1e-9
            assert e["checks"]["probability_reproduction_error"] < 1e-9
    note = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2027-Q1").json()["note"]
    assert "TreeSHAP" in note and "PSA 2021 poverty" in note and "not causes" in note


def test_target_advances_and_no_stale_forecast(monkeypatch):
    assert forecast_target("2026-10-17T09:00:00")["target_quarter"] == "2027-Q1"
    assert forecast_target("2027-01-15T09:00:00")["target_quarter"] == "2027-Q2"
    assert forecast_target("2027-04-15T09:00:00")["target_quarter"] == "2027-Q3"
    assert forecast_target("2027-07-15T09:00:00")["target_quarter"] == "2027-Q4"
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e56")
    monkeypatch.setenv("AIPHEED_NOW", "2027-01-15T09:00:00")
    assert not LEAD2.governs() and not LEAD2.serves("2027-Q2")     # the 2027-Q1 record never stands in for 2027-Q2


def test_rollback_default_is_e38(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    assert LEAD2.mode() == "e38" and not LEAD2.active()
