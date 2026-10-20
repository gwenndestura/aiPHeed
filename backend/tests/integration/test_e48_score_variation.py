"""
tests/integration/test_e48_score_variation.py
---------------------------------------------
E48: where province scores come from and whether they respond to quarter-specific inputs.

The production (E38) scores are read unchanged from the E36/E38 record, which the fitted LightGBM boosters reproduce;
their near-constancy since 2025-Q4 comes from the saturated v1 label, not from serving. The e46 candidate's scores
are the candidate's own as-of estimates and change with each issue date's inputs.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app

# E53 port (tina-e53-port): this E41-E48 candidate test runs under Angel's original configuration (E36 record,
# lead-2 target, no preview); the served default is now E53 (see tests/integration/test_e53_served_model.py).
pytestmark = pytest.mark.usefixtures("angel_original_config")
client = TestClient(app)
E36 = json.loads(Path("data/e36/e36_record.json").read_text(encoding="utf-8"))
NAMES = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]


def _drivers(v):
    return {d["key"]: d["value"] for d in v.get("drivers", [])}


@pytest.fixture
def e38(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")


@pytest.fixture
def e46(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e46")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")


def test_api_scores_equal_the_record_for_every_quarter_and_province(e38):
    for q in E36["quarters"]:
        r = client.get(f"/api/v1/provinces?quarter={q['quarter']}&horizon=nowcast")
        assert r.status_code == 200, q["quarter"]
        shown = {x["name"]: x["riskScore"] for x in r.json()["data"]}
        stored = {v["province"]: v["p_high"] for v in q["provinces"].values()}
        assert shown == pytest.approx(stored, abs=1e-9)


def test_record_probabilities_are_the_models_own_log_odds(e38):
    for q in E36["quarters"]:
        for v in q["provinces"].values():
            if v.get("shap_expected_value_logodds") is None:
                continue
            z = v["shap_expected_value_logodds"] + sum(d["contribution"] for d in v["drivers"])
            assert 1 / (1 + math.exp(-z)) == pytest.approx(v["p_high"], abs=1e-4)


def test_served_e38_booster_reproduces_the_frozen_next_quarter_scores_in_feature_order():
    lgb = pytest.importorskip("lightgbm")
    nq = E36["next_quarter_model"]
    booster = lgb.Booster(model_file=nq["file"])
    assert booster.feature_name() == nq["config"]["features"]
    q = next(x for x in E36["quarters"] if x["quarter"] == "2027-Q1")
    for v in q["provinces"].values():
        x = _drivers(v)
        raw = booster.predict([[x[f] for f in nq["config"]["features"]]], raw_score=True)[0]
        assert 1 / (1 + math.exp(-(raw + v["prior_shift_logodds"]))) == pytest.approx(v["p_high"], abs=1e-4)
        # diagnostic responsiveness (synthetic input, not a forecast): province food-price pressure moves the output
        lo = dict(x, Dnow=-3.3, D_last=-3.4)
        raw_lo = booster.predict([[lo[f] for f in nq["config"]["features"]]], raw_score=True)[0]
        assert raw_lo < raw or x["Dnow"] < -2


def test_static_and_time_varying_inputs_are_joined_by_quarter_and_province():
    for q in E36["quarters"]:
        vals = [_drivers(v) for v in q["provinces"].values()]
        assert len({round(x["H_margin"], 6) for x in vals}) == 1          # regional SWS input: one value per quarter
        if q["quarter"] >= "2023-Q2":
            assert len({round(x["D_last"], 6) for x in vals}) > 1          # provincial CPI input differs by province
    by_q = {q["quarter"]: _drivers(next(iter(q["provinces"].values()))) for q in E36["quarters"]}
    # the hunger input is unchanged only where no new approved SWS round was posted (2025-Q2/Q3 have none)
    assert by_q["2025-Q4"]["H_margin"] == by_q["2026-Q1"]["H_margin"]
    assert by_q["2026-Q1"]["H_margin"] != by_q["2026-Q2"]["H_margin"]


def test_no_province_repeats_its_score_exactly_between_consecutive_quarters(e38):
    for name in NAMES:
        ps = [next(v["p_high"] for v in q["provinces"].values() if v["province"] == name) for q in E36["quarters"]]
        assert all(a != b for a, b in zip(ps, ps[1:])), name


def test_candidate_scores_respond_to_each_issue_dates_inputs(e46):
    from app.ml.inference import e41_lead2 as LEAD2
    rec = LEAD2.record()
    for code, v in rec["provinces"].items():
        # refit probabilities (4 dp) in issue-date order; consecutive issue dates give different estimates
        qs = sorted(v["pastDrivers"], key=lambda s: (int(s[:4]), int(s[-1])))
        ps = [v["pastDrivers"][q]["probability"] for q in qs] + [v["forecast"]["probability"]]
        assert all(a != b for a, b in zip(ps, ps[1:])), code
        assert max(ps) - min(ps) > 0.1
    shown = {}
    for q in ("2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4", "2027-Q1"):
        shown[q] = {x["provinceCode"]: x["riskScore"] for x in
                    client.get(f"/api/v1/provinces?quarter={q}&horizon=nowcast").json()["data"]}
    for code in rec["provinces"]:
        assert len({round(shown[q][code], 4) for q in shown}) == len(shown)
