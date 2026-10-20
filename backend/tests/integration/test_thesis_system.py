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
def test_firi_is_the_served_score_and_the_price_score_stays_a_component(thesis, monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "e58")
    base = {(q, c): _summary(q, s) for q in ("2027-Q1", "2026-Q4") for c, s in SLUG.items()}
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    rec = LEAD2.record()
    for (q, c), b in base.items():
        s = _summary(q, SLUG[c])
        f = T.firi_for(rec, q, c)
        assert s["probability"] == pytest.approx(round(f["firi"], 4)) and s["result"] == f["class"]
        assert s["components"] == b["components"]                    # LightGBM price part unchanged
        assert s["sentence"].startswith(f"ESTIMATED FOOD-INSECURITY RISK for {rec['provinces'][c]['name']}, {q}:")
        assert "not a probability" in s["sentence"] and s["riskOutlook"]["index"] == pytest.approx(round(f["firi"], 4))
        if b["result"] == "LOW" and f["class"] == "HIGH":
            assert "a LOW price score does not mean low food-insecurity risk" in s["sentence"]
    reg = _summary("2027-Q1", "calabarzon", "region")
    assert reg["sentence"].startswith("ESTIMATED FOOD-INSECURITY RISK, 2027-Q1:")
    back = _summary("2026-Q3", "quezon")
    assert back["riskOutlook"]["index"] == pytest.approx(round(T.firi_for(rec, "2026-Q3", "PH040300000")["firi"], 4))
    assert "Back-test estimate" in back["sentence"]


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
    rec = LEAD2.record()
    for r in rows:                                     # LGU index = province FIRI x LGU vulnerability (approved weights)
        code = next(c for c, s in SLUG.items() if s == r["provinceId"])
        f = T.firi_for(rec, "2027-Q1", code)["firi"]
        assert r["provinceEstimate"] == pytest.approx(f, abs=1e-6)
        assert r["riskIndex"] == pytest.approx(f * r["vulnerabilityIndex"], abs=6e-5)


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
    assert [row[0][:6] for row in tb["leadRows"][:4]] == ["Lead 1", "Lead 2", "Lead 3", "Lead 4"]
    assert [row[0][:10] for row in tb["leadRows"][4:]] == ["FIRI lead ", "FIRI lead ", "FIRI lead "]
    assert len(tb["baselineRows"]) == 6 and all(row[-1] == "no" for row in tb["leadRows"])
    assert T.relabel("Quezon: estimated probability of HIGH food-insecurity risk 15%") == "Quezon: exploratory food-price-pressure score 15%"



# ------------------------------------------------------------------------------------------------ FIRI v1
FIRI_DIR = ROOT / "aipheed-backend-aligned" / "experiments" / "FINAL_Thesis_System"


def _sha_lf(p):
    import hashlib
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_firi_protocol_amendment_and_anchors_frozen():
    import hashlib
    from app.ml.inference import firi as FI
    assert _sha_lf(FIRI_DIR / "FIRI_PROTOCOL.md") == (FIRI_DIR / "runner" / "FIRI_PROTOCOL_SHA256.txt").read_text().split()[0]
    assert _sha_lf(FIRI_DIR / "FIRI_PROTOCOL_AMENDMENT_1.md") == (FIRI_DIR / "runner" / "FIRI_AMENDMENT_1_SHA256.txt").read_text().split()[0]
    a = json.loads(FI.ANCHORS.read_text())
    body = {k: v for k, v in a.items() if k != "content_sha256"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() == a["content_sha256"]
    assert a["window"] == ["2021-Q3", "2023-Q4"] and a["indicators"]["N1"]["usable"] is False
    assert a["indicators"]["E1"]["usable"] and a["indicators"]["A2"]["usable"]
    assert (FIRI_DIR / "out" / "firi_anchors_v0_original_window.json").exists()     # the pre-amendment anchors kept


def test_firi_scoring_rules():
    from app.ml.inference import firi as FI
    anc = {"indicators": {k: {"usable": True, "p10": 0.0, "p90": 10.0} for k in FI.CONTINUOUS}}
    raw = {k: {"x": None, "status": "missing", "note": ""} for k in FI.LABELS}
    raw["A1"]["x"], raw["H1"]["x"], raw["C1"]["x"] = 0.2, 0.9, 1.0
    assert FI.score(raw, anc)["firi"] is None                  # 3 domains (A, H, C) < 4: INSUFFICIENT
    raw["A2"]["x"] = 20.0                                        # clipped to 1
    raw["V1"]["x"] = 0.5
    r = FI.score(raw, anc)
    assert r["domainsAvailable"] == 4 and r["indicators"]["A2"]["score"] == 1.0
    assert r["firi"] == pytest.approx(((0.2 + 1.0) / 2 + 0.9 + 1.0 + 0.5) / 4)    # missing dropped, never 0
    assert r["class"] == ("HIGH" if r["firi"] >= 0.5 else "LOW")


def test_runtime_firi_equals_the_evaluated_history(thesis):
    import csv
    rec = LEAD2.record()
    hist = {(r["target"], r["province_code"]): r for r in csv.DictReader(open(T.FIRI_HISTORY, encoding="utf-8"))}
    assert {q for q, _ in hist} == set(LEAD2.candidate_quarters())
    assert all(r["FIRI"] and 0 <= float(r["FIRI"]) <= 1 for r in hist.values())
    for c in SLUG:
        run = T.firi_for(rec, rec["targetQuarter"], c)
        h = hist[(rec["targetQuarter"], c)]
        hi = json.loads(h["indicators_json"])
        for k, v in hi.items():                       # training/serving parity: identical inputs except the record's
            if k == "A1":                             # 4-dp rounding of the price part (sealed file: 6 significant digits)
                assert run["indicators"][k]["x"] == pytest.approx(v["x"], abs=1e-4)
            else:
                assert run["indicators"][k]["x"] == v["x"] and run["indicators"][k]["status"] == v["status"]
        assert run["firi"] == pytest.approx(float(h["FIRI"]), abs=1e-5)
        st = {k: v["status"] for k, v in run["indicators"].items()}
        assert st["C2"] == "incomplete" and st["E2"] == "missing" and st["C1"] == "observed"
        assert run["indicators"]["C2"]["score"] is None and run["domains"]["N"] is None


def test_province_api_scores_are_firi_and_map_levels_follow(thesis):
    rec = LEAD2.record()
    for q in ("2027-Q1", "2026-Q4", "2025-Q2"):
        data = _get("/api/v1/provinces", quarter=q)["data"]
        assert len(data) == 5
        for p in data:
            code = next(c for c, s in SLUG.items() if s == p["id"])
            f = T.firi_for(rec, q, code)["firi"]
            assert p["riskScore"] == pytest.approx(f, abs=1e-6)
            assert p["riskLevel"] == ("high" if round(f, 2) >= 0.5 else "low")


def test_firi_evaluation_reported_honestly():
    e = json.loads(T.FIRI_EVALUATION.read_text())
    L2 = next(x for x in e["leads"] if x["lead"] == 2)
    assert L2["rows"] == 50 and not any(x["reliable"] for x in e["leads"])
    assert L2["FIRI"]["confusion"] == {"TP": 17, "FP": 27, "FN": 1, "TN": 5}
    assert e["domainsUsed"] == ["A", "C", "E", "H", "V"]
    assert e["objective4"]["comparisons"]["LightGBM E56-TUNED"]["brier_diff_firi_minus_baseline"] > 0   # FIRI worse on T43
    assert e["regionalOutcome"]["quarters"] == 18 and "shares its source" in e["regionalOutcome"]["note"]
    assert "no result validates" in e["evidenceStatus"].lower()


def test_driver_bars_explain_the_served_index(thesis):
    rec = LEAD2.record()
    for c, slug in SLUG.items():
        ex = _get("/api/v1/explainability", scope="province", id=slug, quarter="2027-Q1")
        assert "exact share of that index" in ex["note"] and "FIRI" in ex["note"]
        assert sum(t["pct"] for t in ex["triggers"]) == 100
        assert all(t["direction"] in ("increases_risk", "no_effect") for t in ex["triggers"])
        res = T.firi_for(rec, "2027-Q1", c)
        con = T.contributions(res)
        assert sum(con.values()) == pytest.approx(res["firi"], abs=1e-9)          # additive and exact
        d = T.firi_drivers(rec, "2027-Q1", c, {"drivers": []})
        five = sum(x["group_shap"] for x in d["drivers"])
        assert five + d["other_pct"] / 100 * res["firi"] == pytest.approx(res["firi"], abs=1e-3)   # other_pct: 1 dp


def test_factor_cards_follow_the_served_index(thesis):
    """Card statuses come from FIRI, not the price model: a group with a share contributes; an all-missing group is insufficient_data."""
    for sc, i, q in [("region", "calabarzon", "2027-Q1")] + [("province", s, q) for s in SLUG.values() for q in ("2027-Q1", "2024-Q3")]:
        ex = _get("/api/v1/explainability", scope=sc, id=i, quarter=q)
        for t in ex["triggers"]:
            if t["pct"] > 0:
                assert t["status"] == "contributes", (i, q, t)
            else:
                assert t["status"] in ("no_effect", "insufficient_data"), (i, q, t)
            assert t["evidenceNote"].startswith("In the risk index (FIRI v1"), (i, q, t)
            if t["status"] == "insufficient_data" and sc == "province":
                assert "missing is not zero" in t["evidenceNote"]


def test_class_follows_the_frozen_rule_near_the_threshold(thesis):
    """FIRI classifies the unrounded index (protocol section 4), as the evaluation did. Laguna 2026-Q1 (FIRI 0.49975,
    evaluated LOW) is served LOW with a shown score that cannot print as "0.50"; every served level agrees with the
    evaluated class in the history table."""
    for q in ("2024-Q3", "2025-Q2", "2026-Q1", "2026-Q2", "2026-Q4", "2027-Q1"):
        rows = _get("/api/v1/provinces", quarter=q)["data"]
        for p in rows:
            res = T.firi_for(LEAD2.record(), q, p["provinceCode"])
            assert p["riskLevel"] == res["class"].lower(), (q, p["id"])
            assert (round(p["riskScore"], 2) >= 0.5) == (res["class"] == "HIGH"), (q, p["id"], p["riskScore"])
    lag = next(p for p in _get("/api/v1/provinces", quarter="2026-Q1")["data"] if p["id"] == "laguna")
    assert lag["riskLevel"] == "low" and lag["riskScore"] == 0.49
    res = T.firi_for(LEAD2.record(), "2026-Q1", "PH040200000")
    assert T.fmt_index(res["firi"]) == "0.4998" and "LOW (risk index 0.4998" in T.firi_text(res, "Laguna", "2026-Q1")
