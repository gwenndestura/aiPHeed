"""
tests/integration/test_e67_lead2_best_model.py
----------------------------------------------
E67 (aipheed-backend-aligned/experiments/E67_Lead2_Best_Model_Objectives_1_4): Lead-2 goal test, five-trigger
ablation, missing-data audit, and the opt-in e67 serving mode (E66 layered system plus the E67 disclosure).

Evidence
  * the protocol is frozen; the A0 re-run reproduces the sealed E57 Lead-2 forecasts; the served E58 record equals A0;
  * the goal test outcome (no reading legitimately above 75%) and the trigger-group effects are what the tables say;
  * the disclosure the API serves is built only from the E67 tables and passes its integrity check.
Serving (e67)
  * Lead-2 target from the clock; e67 serves only its frozen 2027-Q1 record;
  * numbers (probability, decision, components) equal e58/e66; the production default (E38) is unchanged;
  * model identity (configuration per issue), trigger coverage, missing inputs read as unknown, LOW-under-watch text;
  * 142 LGUs with finite values, correct province mapping and a risk level consistent with the index.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import e41_lead2 as LEAD2
from app.ml.inference import e67_disclosure as D67
from app.ml.inference import enso_context as ENSO
from app.quarterly.target import forecast_target

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
E67 = ROOT / "aipheed-backend-aligned" / "experiments" / "E67_Lead2_Best_Model_Objectives_1_4"
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}
COUNTS = {"batangas": 34, "cavite": 23, "laguna": 30, "quezon": 41, "rizal": 14}
needs_e67 = pytest.mark.skipif(not (E67 / "out" / "r3_goal.json").exists(), reason="E67 outputs not present")


def _out(name):
    return json.loads((E67 / "out" / name).read_text(encoding="utf-8"))


def _table(name):
    return pd.read_csv(E67 / "tables" / name, dtype={"province_code": str})


@pytest.fixture
def mode(monkeypatch):
    def set_mode(m):
        if m is None:
            monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
        else:
            monkeypatch.setenv("AIPHEED_LEAD2_MODEL", m)
        monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    return set_mode


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _summary(q, slug, scope="province"):
    return _get("/api/v1/explainability", scope=scope, id=slug, quarter=q)["summary"]


# ------------------------------------------------------------------------------------------------ evidence
@needs_e67
def test_protocol_frozen_before_scoring():
    sys.path.insert(0, str(E67 / "runner"))
    import e67_lib as K
    sha = K.verify_protocol()
    for f in ("r1_ablation.json", "r2_coverage.json", "r3_goal.json", "r4_el_nino.json"):
        assert _out(f)["protocol_sha256"] == sha
    frozen = (E67 / "runner" / "PROTOCOL_FROZEN_AT.txt").read_text().strip()
    assert frozen < "2026-10-20T03"                          # frozen before the runs (console logs follow)


@needs_e67
def test_a0_reproduces_sealed_lead2_forecasts_and_served_record():
    assert _out("r1_ablation.json")["A0_vs_E57_max_abs_diff"] < 1e-9
    assert _out("r4_el_nino.json")["served_record_vs_A0_max_abs_diff"] < 1e-6
    A = _table("r1_ablation_predictions.csv")
    a0 = A[A["arm"] == "A0"]
    assert (a0["target"].map(lambda q: int(q[:4]) * 4 + int(q[-1])) -
            a0["origin_quarter"].map(lambda q: int(q[:4]) * 4 + int(q[-1])) == 2).all()   # Lead-2 everywhere
    assert set(A["arm"]) == {"A0", "X_climate", "X_fish", "X_employment", "X_ofw", "X_news", "M_only"}


@needs_e67
def test_goal_test_outcome_is_reported_honestly():
    G = _table("r3_goal_test.csv").set_index("reading")
    assert G.loc["E56", "correct"] == 36 and G.loc["EW", "correct"] == 39
    assert G.loc["MAJORITY", "T43_accuracy"] == pytest.approx(0.64)
    models = G[~G["verdict"].eq("baseline")]
    assert (models["verdict"] == "goal not met").all()     # no reading legitimately above 75% (G3 fails)
    assert (models["acc_minus_majority_lo"] <= 0).all()
    assert _out("r3_goal.json")["T43_eq_PS_rows"] == 50


@needs_e67
def test_trigger_group_effects_not_distinguishable():
    P = _table("r3_trigger_group_effects.csv")
    assert len(P) == 6 and (P["effect"] == "not distinguishable from zero").all()
    assert (P["ci95_lo"] < 0).all() and (P["ci95_hi"] > 0).all()


@needs_e67
def test_missing_inputs_are_not_zero_filled():
    S = _table("r2_coverage_summary.csv").set_index("feature")
    # remittances are NaN at the 2027-Q1 origin (BSP file ends 2025-Q4), never 0
    assert S.loc["remit_usd_yoy", "test_nan_at_2027Q1_origin"] == 1.0
    assert S.loc["remit_usd_yoy", "test_zero_at_2027Q1_origin"] == 0.0
    # D-E66-5 sensitivity: reading the incomplete 2026-Q3 typhoon count as unknown changes no price part
    T = _table("r1_typhoon_nan_sensitivity_2027Q1.csv")
    assert (T["tcNaN_p_price"] - T["A0_p_price"]).abs().max() < 1e-9
    assert (T["tcNaN_p"] - T["A0_p"]).abs().max() < 0.005


@needs_e67
def test_disclosure_is_built_from_e67_tables():
    d = D67.disclosure()
    body = {k: v for k, v in d.items() if k != "content_sha256"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() == d["content_sha256"]
    sys.path.insert(0, str(E67 / "runner"))
    import e67_lib as K
    assert d["protocolSha256"] == K.verify_protocol()
    eff = _table("r3_trigger_group_effects.csv").set_index("arm")
    arm = {"climate": "X_climate", "fish_kill": "X_fish", "employment": "X_employment", "ofw_remittance": "X_ofw",
           "news": "X_news"}
    for g in d["triggerCoverage"]:
        if g["key"] in arm:
            assert g["measuredEffect"] == eff.loc[f"{arm[g['key']]}_p", "effect"]
    tr = _table("r4_el_nino_trace.csv")
    for q, rows in d["lowUnderWatch"].items():
        for name, r in rows.items():
            t = tr[(tr["target"] == q) & (tr["province"] == name)].iloc[0]
            assert r["pricePart"] == pytest.approx(t["P_price"], abs=1e-4) and r["config"] == t["A0_config"]


# ------------------------------------------------------------------------------------------------ serving
def test_lead2_target_from_clock_and_no_stale_forecast(monkeypatch):
    assert forecast_target("2026-10-20T09:00:00")["target_quarter"] == "2027-Q1"
    assert forecast_target("2027-01-02T09:00:00")["target_quarter"] == "2027-Q2"
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e67")
    assert LEAD2.layered() and LEAD2.serves("2027-Q1") and not LEAD2.serves("2027-Q2")
    assert LEAD2.record()["lead"] == 2


def test_e67_numbers_equal_e58_and_default_unchanged(mode):
    mode("e58")
    base = {(q, c): _summary(q, s) for q in ("2027-Q1", "2026-Q4") for c, s in SLUG.items()}
    mode("e67")
    for (q, c), b in base.items():
        s = _summary(q, SLUG[c])
        assert s["probability"] == b["probability"] and s["result"] == b["result"]
        assert s["components"] == b["components"]
        assert s["modelIdentity"]["servingMode"] == "e67" and s["modelIdentity"]["targetQuarter"] == q
        assert s["climateWatch"]["level"].startswith("CLIMATE WATCH")
    mode(None)
    assert LEAD2.mode() == "e38"
    assert _get("/api/v1/explainability", scope="province", id="quezon", quarter="2027-Q1").get("summary") is None


def test_model_identity_follows_each_issue(mode):
    mode("e67")
    q1, q4 = _summary("2027-Q1", "cavite")["modelIdentity"], _summary("2026-Q4", "cavite")["modelIdentity"]
    assert q1["issued"] == "2026-10-01" and "configuration 23" in q1["servedModel"]
    assert q4["issued"] == "2026-07-01" and "configuration 68" in q4["servedModel"]
    assert "not validated" in q1["evidenceStatus"] and "not legitimately met" in q1["lead2Accuracy"]


def test_low_under_climate_watch_is_explained_with_matching_numbers(mode):
    mode("e67")
    d = D67.disclosure()["lowUnderWatch"]["2027-Q1"]
    rec = LEAD2.record()
    for c, s in SLUG.items():
        sm = _summary("2027-Q1", s)
        name = rec["provinces"][c]["name"]
        assert sm["result"] == "LOW"
        assert "Why the score is LOW although a climate watch is in force" in sm["sentence"]
        assert f"about {d[name]['foodProjection']:.1f}%" in sm["sentence"]
        assert sm["components"]["probabilityPricePressure"] == pytest.approx(d[name]["pricePart"], abs=1e-4)
        assert "not a model input" in sm["sentence"]          # the watch stays separate from the model number
    back = _summary("2026-Q3", "quezon")
    assert back.get("modelIdentity") is None and back.get("triggerCoverage") is None   # back-tests: no E67 claim


def test_trigger_coverage_in_api_and_missing_read_as_unknown(mode):
    mode("e67")
    s = _summary("2027-Q1", "laguna")
    cov = {g["key"]: g for g in s["triggerCoverage"]}
    assert set(cov) == {"market", "climate", "fish_kill", "employment", "ofw_remittance", "news"}
    assert cov["ofw_remittance"]["missingAtIssue"] is True and "unknown, not as zero" in cov["ofw_remittance"]["note"]
    assert "no official fish-kill event series" in cov["fish_kill"]["dataUsed"]
    assert "treated as unknown, not as no risk" in s["sentence"]


def test_disclosure_absent_degrades_to_e66(mode, monkeypatch, tmp_path):
    mode("e67")
    monkeypatch.setattr(D67, "DISCLOSURE", tmp_path / "missing.json")
    s = _summary("2027-Q1", "rizal")
    assert s.get("modelIdentity") is None and s["climateWatch"]["level"].startswith("CLIMATE WATCH")


def test_climate_statements_use_only_items_before_issue():
    for issue in ("2026-07-01", "2026-10-01"):
        assert all(dt < issue for dt, _ in ENSO.available_at(issue))
    assert ENSO.published_after("2026-10-01")[-1][0] == "2026-10-07"     # Advisory No. 5 (E67 source check 10-20)


def test_all_142_lgus_finite_mapped_and_consistent(mode):
    mode("e67")
    rows = []
    for s in SLUG.values():
        data = _get(f"/api/v1/provinces/{s}/municipalities", quarter="2027-Q1")["data"]
        assert len(data) == COUNTS[s] and all(r["provinceId"] == s for r in data)
        rows += data
    assert len(rows) == 142 and len({r["lguCode"] for r in rows}) == 142
    assert all(r["riskIndex"] is not None and math.isfinite(r["riskIndex"]) and 0 <= r["riskIndex"] <= 1 for r in rows)
    assert all(r["riskLevel"] in ("low", "moderate", "high") for r in rows)
    assert sum(r["tied"] for r in rows) == 0 and len({r["rankRegion"] for r in rows}) == 142
    rec = LEAD2.record()
    prov = {SLUG[c]: v["forecast"]["probability"] for c, v in rec["provinces"].items()}
    for r in rows:                                              # index = province score x vulnerability
        assert r["riskIndex"] == pytest.approx(prov[r["provinceId"]] * r["vulnerabilityIndex"], abs=6e-5)
        assert r["provinceEstimateSource"]["mode"] == "E67_LEAD2"
