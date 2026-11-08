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
    # these tests check the FIRI v2 pipeline as the served score; since aiPHeed/final-thesis-objectives the default
    # map score in thesis mode is the Chapter I risk forecast (ch1_system), so FIRI is selected explicitly here
    monkeypatch.setenv("AIPHEED_MAP_MODEL", "firi")
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
        assert r["riskIndex"] == pytest.approx(_shown(f * r["vulnerabilityIndex"]), abs=6e-5)


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
    assert [row[0][:14] for row in tb["leadRows"][4:]] == ["FIRI v2 lead 1", "FIRI v2 lead 2", "FIRI v2 lead 3"]
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


def _shown(v):
    """The display rule of the thesis mode (dashboard._shown): a LOW index that would print as 0.50 is truncated."""
    return math.floor(v * 100) / 100 if v < 0.5 and round(v, 2) >= 0.5 else v


def test_runtime_firi_equals_the_evaluated_history(thesis):
    import csv
    rec = LEAD2.record()
    hist = {(r["target"], r["province_code"]): r for r in csv.DictReader(open(T.FIRI_HISTORY, encoding="utf-8"))}
    assert {q for q, _ in hist} >= set(LEAD2.candidate_quarters())
    assert all(0 <= float(r["FIRI"]) <= 1 for r in hist.values() if r["FIRI"])
    assert {q for (q, _), r in hist.items() if not r["FIRI"]} == {"2022-Q2"}       # first origin: too little history
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
        assert run["version"] == "v2" and run["weights"] == pytest.approx(json.loads(h["weights_json"]), abs=1e-9)
        st = {k: v["status"] for k, v in run["indicators"].items()}
        assert st["C2"] == "incomplete" and st["E2"] == "missing" and st["C1"] == "observed"
        assert run["indicators"]["C2"]["score"] is None
    news = {c: T.firi_for(rec, rec["targetQuarter"], c)["domains"]["N"] for c in SLUG}
    assert news["PH040300000"] is None and all(v is not None for c, v in news.items() if c != "PH040300000")


def test_province_api_scores_are_firi_and_map_levels_follow(thesis):
    rec = LEAD2.record()
    for q in ("2027-Q1", "2026-Q4", "2025-Q2", "2024-Q3", "2024-Q2"):
        data = _get("/api/v1/provinces", quarter=q)["data"]
        assert len(data) == 5
        for p in data:
            code = next(c for c, s in SLUG.items() if s == p["id"])
            res = T.firi_for(rec, q, code)
            assert p["riskScore"] == pytest.approx(_shown(res["firi"]), abs=1e-6)
            assert p["riskLevel"] == res["class"].lower() == ("high" if res["firi"] >= 0.5 else "low")
            assert (round(p["riskScore"], 2) >= 0.5) == (res["class"] == "HIGH")      # the shown number never contradicts


def test_firi2_protocol_frozen_and_rule_applied():
    import hashlib
    proto = FIRI_DIR / "FIRI2_PROTOCOL.md"
    assert _sha_lf(proto) == (FIRI_DIR / "runner" / "FIRI2_PROTOCOL_SHA256.txt").read_text().split()[0]
    e = json.loads(T.FIRI_EVALUATION.read_text())
    assert e["protocolSha256"] == _sha_lf(proto) and e["selected"] == "C3"
    el = e["eligibility"]
    assert el["C0"]["eligible"] is False and el["C0"]["max_single_bound_indicator"] == "E1"   # v1: E1 saturated
    assert all(el[c]["eligible"] for c in ("C1", "C2", "C3"))
    l2 = e["regional"]["2"]["candidates"]
    best = max(l2[c]["accuracy"] for c in ("C1", "C2", "C3"))
    assert l2["C3"]["accuracy"] == best and l2["C3"]["accuracy"] >= l2["C0"]["accuracy"]
    assert e["lgbm_checks"]["L1"]["passes"] is False and e["lgbm_checks"]["L2"]["passes"] is False
    ref = json.loads(T.FIRI2_REFERENCE.read_text())
    body = {k: v for k, v in ref.items() if k != "content_sha256"}
    assert hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest() == ref["content_sha256"]
    seal = FIRI_DIR / "out" / "firi2_sealed_prospective.csv"
    assert _sha_lf(seal) == (FIRI_DIR / "out" / "firi2_sealed_prospective.sha256").read_text().split()[0]


def test_firi2_scoring_rules():
    from app.ml.inference import firi as FI
    assert FI.percentile(3, [1, 2, 3, 4]) == 0.625 and FI.percentile(0, [1, 2]) == 0 and FI.percentile(9, [1, 2]) == 1
    raw = {k: {"x": None, "status": "missing", "note": ""} for k in FI.LABELS}
    raw["A1"]["x"], raw["H1"]["x"], raw["C1"]["x"], raw["V1"]["x"] = 0.2, 0.9, 1.0, 0.5
    raw["A2"]["x"] = 3.0
    prior = {k: [] for k in FI.CONTINUOUS}
    r = FI.score_v2(raw, {**prior, "A2": [1.0] * 7})
    assert r["indicators"]["A2"]["status"] == "insufficient_history" and r["indicators"]["A2"]["score"] is None
    r = FI.score_v2(raw, {**prior, "A2": [1.0] * 4 + [5.0] * 4})
    assert r["indicators"]["A2"]["score"] == 0.5 and r["domainsAvailable"] == 4      # missing dropped, never 0
    assert r["firi"] == pytest.approx(((0.2 + 0.5) / 2 + 0.5 + 1.0 + 0.9) / 4)
    w = FI.score_v2(raw, {**prior, "A2": [1.0] * 4 + [5.0] * 4}, {"A": 2.0, "C": 1.0, "H": 1.0})   # V: prior weight 1
    assert w["weights"] == pytest.approx({"A": 0.4, "V": 0.2, "C": 0.2, "H": 0.2})
    assert w["firi"] == pytest.approx(0.4 * 0.35 + 0.2 * 0.5 + 0.2 * 1.0 + 0.2 * 0.9)
    assert sum(T.pushes(w).values()) + 0.5 == pytest.approx(w["firi"], abs=1e-12)
    assert sum(T.contributions(w).values()) == pytest.approx(w["firi"], abs=1e-12)


def test_firi2_no_leakage_in_reference_and_weights():
    ref = T.reference()
    for q in ("2023-Q4", "2025-Q2", "2026-Q3"):
        pv = T.prior_for(q)
        for k, vals in ref["values"].items():
            assert len(pv[k]) == sum(1 for qq, _ in vals if T.qi(qq) < T.qi(q))
    e = json.loads(T.FIRI_EVALUATION.read_text())
    for q, w in e["weights_lead2"].items():          # evidence weights use only outcome rounds posted before the issue
        assert w["C3_pairs"] <= len(T._posted(T.issue_of(T.qi(q))))
        if w["C3"] is not None:
            assert w["C3_pairs"] >= 6


def test_firi_evaluation_reported_honestly(thesis):
    perf = _get("/api/v1/config")["modelPerformance"]["firi"]
    l2 = next(x for x in perf["regional"] if x["lead"] == 2)
    assert perf["selected"] == "C3" and l2["quarters"] == 17
    assert l2["FIRI"]["confusion"] == {"TP": 11, "FP": 0, "FN": 1, "TN": 5}
    assert l2["before_FIRI_v1"]["accuracy"] == pytest.approx(16 / 17)
    assert "no paired Brier test establishes" in perf["goal75"] and "regional" in perf["goal75"]
    assert all(t["FIRI"]["accuracy"] < t["LightGBM"]["accuracy"] for t in perf["t43Agreement"])   # not a price model
    assert perf["lgbmChecks"] == {"plattRecalibration": False, "walkForwardThreshold": False}


def test_driver_bars_explain_the_served_index(thesis):
    rec = LEAD2.record()
    for c, slug in SLUG.items():
        ex = _get("/api/v1/explainability", scope="province", id=slug, quarter="2027-Q1")
        assert "moved from 0.5" in ex["note"] and "FIRI v2" in ex["note"]
        assert sum(t["pct"] for t in ex["triggers"]) == 100
        assert all(t["direction"] in ("increases_risk", "protective", "no_effect") for t in ex["triggers"])
        res = T.firi_for(rec, "2027-Q1", c)
        pu = T.pushes(res)
        assert sum(pu.values()) + 0.5 == pytest.approx(res["firi"], abs=1e-9)          # exact split around 0.5
        d = T.firi_drivers(rec, "2027-Q1", c, {"drivers": []})
        for x in d["drivers"]:
            assert x["group_shap"] == pytest.approx(sum(pu.get(k, 0) for k in T.FIVE_GROUPS[x["driver_group"]]), abs=1e-6)
            assert x["direction"] == ("increases_risk" if x["group_shap"] > 0 else "protective" if x["group_shap"] < 0 else "no_effect")
        tot = sum(abs(v) for v in pu.values())
        assert d["other_pct"] == pytest.approx(100 * sum(abs(pu.get(k, 0)) for k in T.OTHER_INDICATORS) / tot, abs=0.06)


def test_factor_cards_follow_the_served_index(thesis):
    """Card statuses come from FIRI, not the price model: a group with a share contributes; an all-missing group is insufficient_data."""
    for sc, i, q in [("region", "calabarzon", "2027-Q1")] + [("province", s, q) for s in SLUG.values() for q in ("2027-Q1", "2024-Q3")]:
        ex = _get("/api/v1/explainability", scope=sc, id=i, quarter=q)
        for t in ex["triggers"]:
            if t["pct"] > 0:
                assert t["status"] == "contributes", (i, q, t)
            else:
                assert t["status"] in ("no_effect", "insufficient_data"), (i, q, t)
            assert t["evidenceNote"].startswith("In the risk index (FIRI v2"), (i, q, t)
            if t["status"] == "insufficient_data" and sc == "province":
                assert "missing is not zero" in t["evidenceNote"]


def test_class_follows_the_frozen_rule_near_the_threshold(thesis):
    """FIRI classifies the unrounded index, as the evaluation did; a LOW index that would print as 0.50 is shown as
    0.49 and written with four decimals."""
    from app.services import dashboard as D
    for q in ("2024-Q2", "2024-Q3", "2025-Q2", "2026-Q1", "2026-Q2", "2026-Q4", "2027-Q1"):
        for p in _get("/api/v1/provinces", quarter=q)["data"]:
            res = T.firi_for(LEAD2.record(), q, p["provinceCode"])
            assert p["riskLevel"] == res["class"].lower(), (q, p["id"])
            assert (round(p["riskScore"], 2) >= 0.5) == (res["class"] == "HIGH"), (q, p["id"], p["riskScore"])
    assert D._shown(0.49975) == 0.49 and D._level(0.49975) == "low" and D._level(0.5) == "high"
    assert T.fmt_index(0.49975) == "0.4998" and T.fmt_index(0.736) == "0.74"
