"""
Contract tests for GET /api/v1/assessments* (revised pipeline) and its consistency with the
dashboard's risk_level rule. Reads only the served artifact; no model is trained here.
"""
import json
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.features import risk_score_v2 as R
from app.services import reference as ref

from app.services import assessment as svc

ART = svc.ARTIFACT


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture(scope="module")
def artifact():
    return pd.read_parquet(ART)


def test_api_and_dashboard_use_the_same_rule():
    for p in (0.0, 0.4999, 0.5, 0.73, 1.0):
        assert ref.risk_level(p) == R.final_classification(p).lower()
    assert ref.risk_level(0.5) == "high" and ref.risk_level(0.4999) == "low"


def test_assessment_probabilities_and_classes_match_the_artifact(client, artifact):
    for q in ("2023-Q4", "2024-Q1", "2025-Q4"):
        body = client.get("/api/v1/assessments", params={"quarter": q}).json()
        a = artifact[artifact["target_quarter"] == q].set_index("province_code")
        assert len(body["provinces"]) == 5
        for p in body["provinces"]:
            row = a.loc[p["provinceCode"]]
            assert p["forecast"]["probability"] == pytest.approx(round(float(row["probability"]), 4))
            assert p["forecast"]["classification"] == R.final_classification(p["forecast"]["probability"])
            assert p["forecast"]["threshold"] == 0.5


def test_insufficient_data_is_reported_not_classified(client):
    body = client.get("/api/v1/assessments", params={"quarter": "2022-Q2"}).json()
    for p in body["provinces"]:
        assert p["forecast"]["classification"] == R.INSUFFICIENT_DATA
        assert p["forecast"]["probability"] is None and p["missingDataWarnings"]
    assert body["region"]["classificationCounts"][R.INSUFFICIENT_DATA] == 5


def test_regional_signal_is_shared_and_labelled_regional(client):
    body = client.get("/api/v1/assessments", params={"quarter": "2025-Q1"}).json()
    sig = [p["regionalHungerSignal"] for p in body["provinces"]]
    assert len({s["value"] for s in sig}) == 1 and all(s["sharedAcrossProvinces"] for s in sig)
    assert "NOT a province-specific" in sig[0]["scope"]


def test_payload_separates_forecast_score_and_evidence(client):
    p = client.get("/api/v1/assessments", params={"quarter": "2025-Q4"}).json()["provinces"][0]
    for key in ("forecast", "regionalHungerSignal", "provincialFoodPriceEvidence", "supportingStressScore",
                "mainFactors", "missingDataWarnings", "rationale", "limitations"):
        assert key in p
    assert "not a probability" in p["supportingStressScore"]["meaning"]
    assert p["forecast"]["model"].startswith("LightGBM")
    ev = p["evidenceContributions"]
    assert set(ev["groups"]) == {"R", "GP", "GN", "N"} and ev["selectedGroups"]
    assert all(g["logOddsContribution"] is None for k, g in ev["groups"].items() if k not in ev["selectedGroups"])
    assert p["forecast"]["horizon"].startswith("1 quarter ahead")
    assert p["provincialFoodPriceEvidence"]["published"] and p["regionalHungerSignal"]["published"]


def test_unknown_or_protected_quarter_returns_404(client):
    assert client.get("/api/v1/assessments", params={"quarter": "2026-Q3"}).status_code == 404
    assert client.get("/api/v1/assessments", params={"quarter": "bad"}).status_code == 422


def test_methodology_states_fixed_rule_and_limits(client):
    m = client.get("/api/v1/assessments/methodology").json()
    assert m["classificationRule"]["threshold"] == 0.5
    assert m["model"]["family"] == "LightGBM" and m["model"]["class_weight"] is None
    assert "not an official" in m["target"]["status"]


def test_quarter_index_counts_match_artifact(client, artifact):
    qs = {d["quarter"]: d for d in client.get("/api/v1/assessments/quarters").json()}
    for q, g in artifact.groupby("target_quarter"):
        assert qs[q]["HIGH"] + qs[q]["LOW"] + qs[q]["INSUFFICIENT_DATA"] == 5
        assert qs[q]["HIGH"] == int((g["classification"] == R.HIGH).sum())
