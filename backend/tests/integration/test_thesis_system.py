"""
tests/integration/test_thesis_system.py
---------------------------------------
The final aiPHeed thesis system (AIPHEED_LEAD2_MODEL=thesis; FINAL_THESIS_SYSTEM_REPORT.md).

  * strict thesis-demo start: refuses another mode or a missing artifact (no silent fallback);
  * the runtime regional hunger outlook and provincial risk outlook equal the sealed E69 values;
  * the score, decision and components equal the served E58 record; the outlook is stated first; a LOW score under an
    ELEVATED outlook says so;
  * Objective 1 news evidence: the improved pipeline feeds the news panel; FSSI-v3 only when SUFFICIENT; real topics;
  * Objectives 2 and 4: the final evaluation reproduces the sealed predictions and the frozen reliability rule;
  * the target quarter advances with the clock and a stale record is never served;
  * 142 LGUs with finite values, correct provinces and risk levels; zero vs missing inputs are distinguished.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import main as MAIN
from app.main import app
from app.ml.inference import e41_lead2 as LEAD2
from app.ml.inference import thesis_system as T
from app.news import pipeline_v3 as P3

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
E69 = ROOT / "aipheed-backend-aligned" / "experiments" / "E69_Food_Insecurity_Risk_Framework"
SLUG = {"PH040100000": "cavite", "PH040200000": "laguna", "PH040300000": "quezon", "PH040400000": "rizal",
        "PH040500000": "batangas"}
COUNTS = {"batangas": 34, "cavite": 23, "laguna": 30, "quezon": 41, "rizal": 14}


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    return monkeypatch


def _get(path, **params):
    r = client.get(path, params=params)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def _summary(q, slug, scope="province"):
    return _get("/api/v1/explainability", scope=scope, id=slug, quarter=q)["summary"]


# ------------------------------------------------------------------------------------------------ configuration
def test_strict_start_requires_thesis_mode_and_artifacts(monkeypatch, tmp_path):
    monkeypatch.setenv("AIPHEED_STRICT_MODEL", "1")
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e69")
    with pytest.raises(RuntimeError, match="requires AIPHEED_LEAD2_MODEL=thesis"):
        MAIN.strict_model_check()
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    assert T.validate() == []
    MAIN.strict_model_check()                                     # ready: no exception
    monkeypatch.setattr(T, "REQUIRED", T.REQUIRED + (tmp_path / "missing.json",))
    with pytest.raises(RuntimeError, match="thesis system not ready"):
        MAIN.strict_model_check()
    monkeypatch.delenv("AIPHEED_STRICT_MODEL")
    MAIN.strict_model_check()                                     # not strict: never blocks the default service


def test_config_names_the_serving_model(thesis):
    sm = _get("/api/v1/config")["servingModel"]
    assert sm["mode"] == "thesis" and sm["model"] == T.MODEL_NAME and sm["lead"] == 2
    assert sm["targetQuarter"] == "2027-Q1" and sm["issued"] == "2026-10-01" and sm["servesTargetNow"] is True
    mp = _get("/api/v1/config")["modelPerformance"]
    assert mp["furthestReliableLead"] is None and [x["lead"] for x in mp["leads"]] == [1, 2, 3]


def test_default_is_unchanged(monkeypatch):
    monkeypatch.delenv("AIPHEED_LEAD2_MODEL", raising=False)
    assert LEAD2.mode() == "e38" and not T.active()
    assert _get("/api/v1/config").get("servingModel") is None


# ------------------------------------------------------------------------------------------------ runtime = sealed E69
def test_runtime_outlook_equals_sealed_e69(thesis):
    S = pd.read_csv(E69 / "sealed" / "outlook_forward.csv", dtype={"province_code": str})
    rec = LEAD2.record()
    for t_q, g in S.groupby("origin_quarter"):
        rh = T.regional_hunger(T.qi(t_q))
        assert rh["expectedHunger"] == pytest.approx(g["R0_RW_hat"].iloc[0], abs=0.05)
        assert rh["sigma"] == pytest.approx(g["R0_RW_sigma"].iloc[0], abs=1e-3)
        assert rh["probabilityAbove11_3"] == pytest.approx(g["R0_RW_p_elev"].iloc[0], abs=1e-3)
    q1 = S[S["target"] == rec["targetQuarter"]]
    for r in q1.itertuples():
        o = T.outlook(rec, r.province_code)
        assert o["tier"] == r.tier
        assert o["components"]["affordabilityHazard"] == bool(r.A_component)
        assert o["components"]["headlineAtIssue"] == pytest.approx(r.headline_at_issue, abs=0.01)


def test_hunger_outlook_uses_only_rounds_posted_before_issue():
    hs = T._posted("2026-07-01")
    assert T.qi("2026-Q2") not in hs and T.qi("2026-Q1") in hs     # 2026-Q2 round posted 2026-08-24
    assert T.qi("2022-Q1") not in T._posted("2026-10-14")         # no round: absent, never 0


# ------------------------------------------------------------------------------------------------ serving
def test_scores_equal_record_and_outlook_is_stated_first(thesis, monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e58")
    base = {(q, c): _summary(q, s) for q in ("2027-Q1", "2026-Q4") for c, s in SLUG.items()}
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    for (q, c), b in base.items():
        s = _summary(q, SLUG[c])
        assert s["probability"] == b["probability"] and s["result"] == b["result"] and s["components"] == b["components"]
        assert s["sentence"].startswith("FOOD-INSECURITY RISK OUTLOOK for")
        assert s["modelIdentity"]["servingMode"] == "thesis" and s["modelIdentity"]["targetQuarter"] == q
        tier = s["riskOutlook"]["tier"]
        assert tier in ("ELEVATED", "WATCH", "NO ELEVATED SIGNAL", "INSUFFICIENT DATA")
        if s["result"] == "LOW" and tier in ("ELEVATED", "WATCH"):
            assert "The LOW price score does not mean low food-insecurity risk" in s["sentence"]
        assert "not a probability" in s["sentence"] and "REGIONAL HUNGER" in s["sentence"]
    reg = _summary("2027-Q1", "calabarzon", "region")
    assert reg["sentence"].startswith("FOOD-INSECURITY RISK OUTLOOK, 2027-Q1:")
    for c, slug in SLUG.items():
        assert reg["riskOutlook"]["tiers"][LEAD2.record()["provinces"][c]["name"]] == _summary("2027-Q1", slug)["riskOutlook"]["tier"]
    assert _summary("2026-Q3", "quezon").get("riskOutlook") is None          # back-tests: no outlook claim


def test_missing_zero_and_placeholder_inputs_are_distinguished(thesis):
    s = _summary("2027-Q1", "laguna")
    st = {i["key"]: i["status"] for i in s["inputStatus"]}
    assert st["remit_usd_yoy"] == "missing" and st["typhoons"] == "substituted" and st["fish_kill_events"] == "not_collected"
    assert "observed_zero" in st.values() or all(v != 0 for v in [i["value"] for i in s["inputStatus"] if i["value"] is not None])
    assert "Missing values are treated as unknown, not as no risk" in s["sentence"]


def test_news_evidence_from_the_objective1_pipeline(thesis):
    rec = LEAD2.record()
    t = T.qi(rec["originQuarter"])
    for c, slug in SLUG.items():
        n = _summary("2027-Q1", slug)["newsEvidence"]
        f = P3.fssi_v3(c, t)
        assert n["articles"] == f["n"] and n["fssiStatus"] == f["status"]
        assert (n["fssi"] is None) == (f["status"] != "SUFFICIENT")       # FSSI only with >= 5 articles
        names = set(pd.read_csv(T.TOPIC_INFO)["Topic"].astype(str))
        assert all("outlier" not in x["topic"] and "_pct" not in x["topic"] for x in n["topics"])
        assert len(names) > 100
    feed = _get("/api/v1/news", scope="province", id="quezon", quarter="2027-Q1")
    assert feed["articleCount"] > 0 and all(d.get("source") for d in feed["data"])


def test_final_evaluation_reproduces_sealed_predictions():
    e = json.loads(T.EVALUATION.read_text())
    L = {x["lead"]: x for x in e["objective2"]["leads"]}
    m2 = L[2]["metrics"]["LightGBM E56-TUNED P(HIGH)"]
    assert m2["accuracy"] == pytest.approx(0.72) and m2["confusion"] == {"TP": 10, "FP": 6, "FN": 8, "TN": 26}
    assert L[1]["metrics"]["LightGBM E56-TUNED P(HIGH)"]["accuracy"] == pytest.approx(0.85)
    assert not any(x["reliable"] for x in L.values()) and e["objective2"]["furthestReliableLead"] is None
    b = e["objective4"]
    assert b["rows"] == 45 and set(b["models"]) >= {"I. Naive persistence", "Majority class (always LOW)"}
    est = {k: v["paired_vs_lightgbm"]["brier_advantage_established"] for k, v in b["models"].items() if "paired_vs_lightgbm" in v}
    assert est["I. Naive persistence"] is False
    assert sum(est.values()) == 2                                  # PSA-only LR and combined LR only


def test_target_advances_with_the_clock_and_no_stale_forecast(thesis, monkeypatch):
    monkeypatch.setenv("AIPHEED_NOW", "2027-01-15T09:00:00")
    sm = _get("/api/v1/config")["servingModel"]
    assert sm["servesTargetNow"] is False and sm["targetQuarter"] == "2027-Q1"
    assert not LEAD2.serves("2027-Q2")


def test_142_lgus_finite_mapped_and_coloured(thesis):
    rows = []
    for s in SLUG.values():
        data = _get(f"/api/v1/provinces/{s}/municipalities", quarter="2027-Q1")["data"]
        assert len(data) == COUNTS[s] and all(r["provinceId"] == s for r in data)
        rows += data
    assert len({r["lguCode"] for r in rows}) == 142 and sum(r["tied"] for r in rows) == 0
    assert all(math.isfinite(r["riskIndex"]) and r["riskLevel"] in ("low", "moderate", "high") for r in rows)
    assert all("not" in r["disaggregationLabel"].lower() for r in rows)          # prioritization, not a forecast


def test_runtime_input_status_matches_the_e68_classification(thesis):
    """The runtime classification (any future record) agrees with the E68 frozen classification where both exist."""
    from app.ml.inference import e68_disclosure as D68
    rec = LEAD2.record()
    d = D68.disclosure()["inputStatus"][rec["targetQuarter"]]
    alias = {"palayProductionYoY": "palay_yoy", "cornProductionYoY": "corn_yoy", "fisheriesProductionYoY": "fish_yoy",
             "aquacultureYoY": "aqua_yoy", "unemployment": "ur_yoy"}
    for c in SLUG:
        name = rec["provinces"][c]["name"]
        frozen = {i["key"]: i["status"] for i in d[name]["inputs"]}
        run = {alias.get(i["key"], i["key"]): i["status"] for i in T.input_status(rec, c)}
        shared = set(frozen) & set(run)
        assert len(shared) >= 18
        assert {k: run[k] for k in shared} == {k: frozen[k] for k in shared}, name


def test_pdf_reports_render_with_the_final_evaluation(thesis):
    for scope, sid in (("province", "quezon"), ("region", "calabarzon")):
        r = client.get("/api/v1/report", params={"scope": scope, "id": sid, "quarter": "2027-Q1"})
        assert r.status_code == 200 and r.headers["content-type"].startswith("application/pdf") and len(r.content) > 10_000
    tb = T.performance_tables()
    assert [row[0][:6] for row in tb["leadRows"]] == ["Lead 1", "Lead 2", "Lead 3", "Lead 4"]
    assert len(tb["baselineRows"]) == 6 and all(row[-1] == "no" for row in tb["leadRows"])
    assert T.relabel("Quezon: estimated probability of HIGH food-insecurity risk 15%") == "Quezon: exploratory food-price-pressure score 15%"
