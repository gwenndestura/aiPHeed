"""
tests/integration/test_e46_corrected_candidate.py
-------------------------------------------------
AIPHEED_LEAD2_MODEL=e46 serves the defect-corrected model I7: exactly the frozen 2027-Q1 forecast (sha-checked),
labelled a forecast, with the acceptance status stated as not met, five trigger groups traced, and every dashboard
quarter carrying the same score (I7's own as-of backtest / earlier Lead-2 forecast). The default stays E38.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2

client = TestClient(app)
FROZEN = Path("..") / "aipheed-backend-aligned" / "experiments" / "E46_Rice_Policy" / "frozen"
FIVE = {"market", "climate", "fish_kill", "employment", "ofw_remittance"}


@pytest.fixture
def e46(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e46")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")


def test_serves_the_frozen_corrected_forecast(e46):
    f = FROZEN / "E46_I7_PROSPECTIVE_2027Q1.json"
    digest = hashlib.sha256(f.read_bytes()).hexdigest()
    assert digest == (FROZEN / "E46_I7_PROSPECTIVE_2027Q1.sha256").read_text().split()[0]
    frozen = json.loads(f.read_text())
    rec = LEAD2.record()
    assert rec["sources"]["frozen_sha256"] == digest and rec["origin"] == "2026-10-01"
    rows = {r["name"]: r for r in client.get("/api/v1/provinces?quarter=2027-Q1&horizon=nowcast").json()["data"]}
    for name, v in frozen["provinces"].items():
        assert rows[name]["riskScore"] == pytest.approx(v["I7_p"], abs=1e-9)
        assert rows[name]["estimateKind"] == "forecast" and rows[name]["observedOutcome"] is None
    for v in rec["provinces"].values():
        assert v["forecast"]["kind"].startswith("FORECAST") and v["forecast"]["decisionThreshold"] == 0.5


def test_acceptance_is_not_claimed_and_triggers_are_traced(e46):
    rec = LEAD2.record()
    assert rec["assessment"]["forecastingAcceptanceMet"] is False and rec["assessment"]["finalCandidate"] is None
    assert any("ACCEPTANCE NOT MET" in w for v in rec["provinces"].values() for w in v["warnings"])
    for v in rec["provinces"].values():
        assert set(v["fiveTriggerContributions"]) == FIVE and set(v["triggerStatus"]) == FIVE
    t = client.get("/api/v1/explainability?scope=province&id=cavite&quarter=2027-Q1").json()["triggers"]
    assert {x["key"] for x in t} == FIVE and all(x["status"] in ("contributes", "no_effect") for x in t)
    ind = client.get("/api/v1/config").json()["indicator"]
    assert ind["id"] == "food_stress_risk_probability" and "not met" in ind["caveat"]


def test_every_quarter_is_the_same_score(e46):
    rec = LEAD2.record()
    for q in ("2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4", "2027-Q1"):
        body = client.get(f"/api/v1/provinces?quarter={q}&horizon=nowcast").json()
        assert body["indicator"]["id"] == "food_stress_risk_probability" and len(body["data"]) == 5
    q4 = {r["provinceCode"]: r["riskScore"] for r in
          client.get("/api/v1/provinces?quarter=2026-Q4&horizon=nowcast").json()["data"]}
    assert q4 == {c: pytest.approx(v["earlierForecasts"][0]["probability"]) for c, v in rec["provinces"].items()}
    ts = client.get("/api/v1/forecast/timeseries?scope=region&id=calabarzon&horizon=nowcast").json()["series"]
    assert {p["scoreType"] for p in ts} == {"food_stress_risk_probability"} and ts[-1]["quarter"] == "2027-Q1"


def test_default_remains_e38(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-17T09:00:00")
    assert client.get("/api/v1/lead2/summary").status_code == 404


def test_past_quarters_carry_their_own_as_of_triggers(e46):
    """E47: every past quarter on the timeline shows the five trigger groups attributed by the model refitted at that
    quarter's own issue date (never 'not recorded', never another quarter's or another model's drivers)."""
    rec = LEAD2.record()
    shown = {r["provinceCode"]: r["riskScore"] for r in
             client.get("/api/v1/provinces?quarter=2026-Q3&horizon=nowcast").json()["data"]}
    for code, v in rec["provinces"].items():
        assert {"2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4"} <= set(v["pastDrivers"])
        assert v["pastDrivers"]["2026-Q3"]["origin"] == "2026-04-01"
        assert v["pastDrivers"]["2026-Q3"]["probability"] == pytest.approx(shown[code], abs=1e-3)
    # Lead 2: the target quarter q is issued after quarter q-2, so its evidence names q-2 (typhoons in that quarter)
    for q, origin_q in (("2026-Q2", "2025-Q4"), ("2026-Q3", "2026-Q1"), ("2026-Q4", "2026-Q2")):
        t = client.get(f"/api/v1/explainability?scope=province&id=quezon&quarter={q}").json()["triggers"]
        assert {x["key"] for x in t} == FIVE
        assert all(x["status"] in ("contributes", "no_effect") and x["evidenceNote"] for x in t)
        assert any(x["status"] == "contributes" for x in t)
        climate = next(x for x in t if x["key"] == "climate")
        assert origin_q in climate["evidenceNote"]             # the evidence is that issue date's own inputs
    region = client.get("/api/v1/explainability?scope=region&id=calabarzon&quarter=2026-Q2").json()["triggers"]
    assert {x["key"] for x in region} == FIVE and all(x["status"] != "not_recorded" for x in region)


def _builder():
    import importlib.util
    spec = importlib.util.spec_from_file_location("build_record_e46", Path("scripts") / "build_record_e46.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _qi(q):
    return int(q[:4]) * 4 + int(q[-1]) - 1


def _qs(i):
    return f"{i // 4}-Q{i % 4 + 1}"


def test_historical_quarter_mapping_and_information_cutoff(e46):
    """Lead 2 (E41 convention, as coded in e41_lib.origin/m0_of and as in the frozen 2027-Q1 artifact): target q is
    issued at 00:00 on the first day of quarter q-1 after quarter q-2; CPI through month 2 of q-2, typhoons and news
    through q-2, production / LFS / remittances through q-3, SWS rounds posted before the issue date. Checked for
    every past quarter, including the year boundaries (2024-Q2 -> 2024-01-01, 2025-Q1 -> 2024-10-01)."""
    rec = LEAD2.record()
    frozen = json.loads((FROZEN / "E46_I7_PROSPECTIVE_2027Q1.json").read_text())
    assert (frozen["origin"], frozen["origin_quarter"]) == ("2026-10-01", "2026-Q3") and rec["targetQuarter"] == "2027-Q1"
    seen = set()
    for v in rec["provinces"].values():
        for q, x in v["pastDrivers"].items():
            t = _qi(q) - 2
            first = t + 1
            assert x["origin"] == f"{first // 4}-{(first % 4) * 3 + 1:02d}-01" and x["originQuarter"] == _qs(t)
            cut = x["informationCutoff"]
            assert cut["cpiThrough"] == f"{t // 4}-{(t % 4) * 3 + 2:02d}"
            assert cut["typhoonsAndNewsThrough"] == _qs(t) and cut["productionLfsRemittancesThrough"] == _qs(t - 1)
            assert cut["swsLatestPosted"] < x["origin"]
            seen.add((q, x["origin"]))
    assert ("2024-Q2", "2024-01-01") in seen and ("2025-Q1", "2024-10-01") in seen


def test_contributions_are_consistent_with_each_quarters_own_prediction(e46):
    """Per province and past quarter: the ridge contributions add up to the model's own correction (exactly, with the
    hunger intercept stated as unattributed), the probability is that quarter's backtest, and the dashboard shares are
    the integer split of |log-odds effect| of the contributing groups."""
    rec = LEAD2.record()
    b = _builder()
    for code, v in rec["provinces"].items():
        past = {x["targetQuarter"]: x["probability"] for x in v["pastForecasts"] + v["earlierForecasts"]}
        for q, x in v["pastDrivers"].items():
            assert all(err < 1e-8 for k, err in x["checks"].items() if k.endswith("additivity_error"))
            assert x["probability"] == pytest.approx(past[q], abs=1e-3)
            for g, c in x["fiveTriggerContributions"].items():
                st = x["triggerStatus"][g]["status"]
                big = max(abs(c["foodInflationPoints"]), abs(c["gapPoints"]), abs(c["hungerPoints"])) >= b.NEGLIGIBLE_POINTS
                assert st == "insufficient_data" or st == ("contributes" if big else "no_effect")
    lo = rec["provinces"]["PH040300000"]["pastDrivers"]
    t = {x["key"]: x for x in client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2026-Q3").json()["triggers"]}
    eff = {g: abs(c["logOddsEffect"]) for g, c in lo["2026-Q3"]["fiveTriggerContributions"].items()
           if lo["2026-Q3"]["triggerStatus"][g]["status"] == "contributes"}
    top = max(eff, key=eff.get)
    assert t[top]["pct"] == max(x["pct"] for x in t.values()) and sum(x["pct"] for x in t.values()) == 100


def test_contributions_are_not_copied_across_quarters_or_provinces(e46):
    rec = LEAD2.record()
    q = rec["provinces"]["PH040300000"]["pastDrivers"]
    assert q["2026-Q2"]["fiveTriggerContributions"] != q["2026-Q3"]["fiveTriggerContributions"]
    clim = {c: v["pastDrivers"]["2026-Q3"]["fiveTriggerContributions"]["climate"]["foodInflationPoints"]
            for c, v in rec["provinces"].items()}
    assert len(set(clim.values())) > 1                          # climate inputs are provincial
    assert rec["provinces"]["PH040300000"]["pastDrivers"]["2026-Q3"]["fiveTriggerContributions"] != \
        rec["provinces"]["PH040300000"]["fiveTriggerContributions"]


def test_insufficient_data_rule_is_distinct_from_negligible():
    b = _builder()
    import math
    nan = float("nan")
    row = {"remit_usd_yoy": nan, "remit_php_yoy": nan, "fx_yoy": nan}
    assert b.group_status(row, "ofw_remittance", 0.5, 0.0, 0.0) == "insufficient_data"
    row["fx_yoy"] = 1.2
    assert b.group_status(row, "ofw_remittance", 0.05, 0.0, 0.0) == "no_effect"
    assert b.group_status(row, "ofw_remittance", 0.0, 0.0, 0.2) == "contributes"
    assert math.isclose(b.NEGLIGIBLE_POINTS, 0.1)


def test_e50_market_attribution_includes_the_cpi_projection(e46):
    """E50: the market group is credited with the base-effect food / gap projections (the model's price inputs), all
    groups use the training-mean reference, the SWS level is reported separately, and probabilities are unchanged."""
    rec = LEAD2.record()
    assert "training-set mean" in rec["attributionMethod"] and "not causal" in rec["attributionMethod"]
    first = {g: 0 for g in FIVE}
    for v in rec["provinces"].values():
        entries = list(v["pastDrivers"].values()) + [v]
        for x in entries:
            c, s = x["fiveTriggerContributions"], x["triggerStatus"]
            m = c["market"]
            assert {"baseProjectionFoodPoints", "baseProjectionGapPoints", "residualOnlyLogOddsEffect"} <= set(m)
            for g in FIVE - {"market"}:
                assert c[g]["logOddsEffect"] == c[g]["residualOnlyLogOddsEffect"]   # unchanged for the other groups
            assert 0.0 <= x["drivers"]["other_pct"] <= 100.0 and "otherContribution" in x
            eff = {g: abs(c[g]["logOddsEffect"]) if s[g]["status"] == "contributes" else 0.0 for g in FIVE}
            first[max(eff, key=eff.get)] += 1
    assert first["market"] > sum(first.values()) / 2                      # measured result, not a rule (E50 report)
    note = client.get("/api/v1/explainability?scope=province&id=quezon&quarter=2027-Q1").json()["note"]
    assert "historical average" in note and "not causes" in note
