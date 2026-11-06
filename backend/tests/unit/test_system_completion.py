"""Operational completion pieces: provincial prospective register (hash chain, write-once seals), the E140 next-quarter
candidate issue (dynamic target quarter, 142 LGUs labelled as a ranking, intervals), per-candidate check counts in the
release-gated outlook, admin-only candidate route, and the NLP convergent-validity output."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app import registry as R
from app.paths import BACKEND_DIR
from app.registry import prospective_provincial as PP

E140 = BACKEND_DIR / "data" / "e140" / "out"


def test_register_chain_and_seals_unchanged():
    assert PP.verify()
    recs = PP.read()
    assert {r["model_id"] for r in recs} >= {"e138-where-lrp-1.0", "e139-lgbm-1.0", "e140-lgbm-native-1.0"}
    import hashlib
    for r in recs:
        assert hashlib.sha256((BACKEND_DIR / r["seal_path"]).read_text().encode()).hexdigest() == r["seal_sha256"]


def test_register_is_idempotent_and_detects_tampering(tmp_path):
    p = tmp_path / "reg.jsonl"
    seal = BACKEND_DIR / "data" / "e139" / "out" / "sealed_prediction.json"
    a = PP.register("m", seal, "a" * 64, "2026-10-01", path=p)
    b = PP.register("m", seal, "a" * 64, "2026-10-01", path=p)
    assert a == b and len(PP.read(p)) == 1 and PP.verify(p)
    rec = json.loads(p.read_text())
    rec["issue_date"] = "2025-01-01"
    p.write_text(json.dumps(rec) + "\n")
    assert not PP.verify(p)


def test_scoring_uses_e137_target_rules_and_baselines(tmp_path):
    rows = pd.DataFrame({"province": ["Quezon", "Cavite", "Abra", "Sulu", "Quezon"], "survey": "X", "year": 2027,
                         "p": [50.0, 30.0, 70.0, 80.0, 40.0], "se_p": [2.0, 2.0, 2.0, 2.0, 2.0], "ref": [42.8] * 4 + [31.4],
                         "instrument": ["HFIAS"] * 4 + ["FIES"]})
    f = tmp_path / "round.csv"
    rows.to_csv(f, index=False)
    res = PP.score(str(f))
    h = res["by_instrument"]["HFIAS"]
    assert h["role"].startswith("confirmation") and res["by_instrument"]["FIES"]["role"].startswith("agreement")
    for mid in ("e138-where-lrp-1.0", "e139-lgbm-1.0", "e140-lgbm-native-1.0"):
        m = h["models"][mid]
        assert m["n"] == 4 and 0 <= m["expected_brier"] <= 1 and set(m["minus_baseline_expected_brier"]) == {"NAT", "PERS", "REGPREV"}
    assert h["models"]["PERS"]["n"] == 4 and h["models"]["NAT"]["n"] == 4
    assert res["by_instrument"]["FIES"]["models"]["e140-lgbm-native-1.0"]["n"] == 1


def test_scoring_rejects_incomplete_round_file(tmp_path):
    f = tmp_path / "bad.csv"
    pd.DataFrame({"province": ["Quezon"], "p": [40.0]}).to_csv(f, index=False)
    try:
        PP.score(str(f))
        raise AssertionError("expected ValueError")
    except ValueError as e:
        assert "se_p" in str(e)


def test_next_quarter_issue_and_lgus():
    f = json.loads((E140 / "forecast_next_quarter.json").read_text())
    assert f["display_lead"] == 1 and f["target_quarter"] == "2027-Q1" and f["issue_date"] == "2026-10-01"
    assert f["final_model"]["n_trees"] > 0 and "CANDIDATE" in f["validation_status"]
    assert "not the share of food-insecure households" in f["meaning"] and "NOT validated" in f["claim"]
    assert f["explanation_method"].startswith("exact TreeSHAP")
    for p in f["provinces"]:
        lo, hi = p["p_interval90"]
        assert 0 <= lo <= hi <= 1
        assert p["risk_class"] == ("HIGH" if lo >= 0.5 else "LOW" if hi < 0.5 else "UNCERTAIN")
        assert {e["group"] for e in p["explanations"]} <= {"poverty", "market", "climate", "history", "geography"}
    lg = pd.read_csv(E140 / "lgus_next_quarter.csv")
    assert len(lg) == 142 and lg["lgu_psgc"].is_unique
    assert lg["label"].str.contains("not a municipal food-insecurity measurement").all()
    assert (lg["status"] == "candidate ranking pending provincial forecast validation").all()
    assert ((lg["priority_score_low"] <= lg["priority_score"]) & (lg["priority_score"] <= lg["priority_score_high"])).all()
    assert lg["vulnerability"].notna().all() and lg["poverty_incidence_2021"].notna().all()
    assert lg["province_name"].value_counts().to_dict() == {"Quezon": 41, "Batangas": 34, "Laguna": 30, "Cavite": 23, "Rizal": 14}


def test_explanations_add_up_to_the_prediction():
    from app.e139 import live as LV
    from app.e140 import issue as I
    from app.e140 import model as M
    X = M.data(lead=1)
    final = M.make("LGBM-AUTO").fit(X)
    Z = LV.build(LV.ISSUE, write=False)
    Z["island_code"] = 0.0
    c, method = I.contributions(final, Z)
    assert method.startswith("exact") and np.allclose(c.sum(axis=1), final.predict_y(Z))


def test_quarter_clock_advances_one_quarter_in_manila_time():
    from app.quarterly.target import forecast_target
    assert forecast_target("2026-11-04T09:00")["target_quarter"] == "2027-Q1"
    assert forecast_target("2027-02-10T09:00")["target_quarter"] == "2027-Q2"
    assert forecast_target("2027-05-01T09:00")["target_quarter"] == "2027-Q3"
    assert forecast_target("2026-12-31T16:30:00+00:00")["target_quarter"] == "2027-Q2"   # already 1 Jan 2027 in Manila


def test_candidate_outlook_flags_a_past_issue(monkeypatch):
    from app.e140 import serve
    monkeypatch.setenv("AIPHEED_NOW", "2027-02-10T09:00")
    o = serve.outlook()
    assert o["current"] is False and o["expected_target_quarter"] == "2027-Q2" and o["target_quarter"] == "2027-Q1"


def test_outlook_reports_each_candidates_own_check_count():
    from app.main import app
    c = TestClient(app)
    out = c.get("/api/v1/final/food-insecurity/outlook").json()
    if out["status"] == "approved":                     # an approved model is served instead of the candidate list
        assert R.load()["models"][out["production"]["model_id"]]["gate"]["passed"]
        return
    assert out["status"] == "validation_pending" and out["forecast"] is None
    reg = R.load()["models"]
    for cand in out["candidates"]:
        assert cand["checks_total"] == len(reg[cand["model_id"]]["gate"]["checks"])


def test_e140_candidate_route_is_admin_only():
    from app.main import app
    from app.services.security import require_admin
    c = TestClient(app)
    assert c.get("/api/v1/admin/candidates/e140-lgbm-native-1.0/outlook").status_code in (401, 403)
    app.dependency_overrides[require_admin] = lambda: object()
    try:
        r = c.get("/api/v1/admin/candidates/e140-lgbm-native-1.0/outlook").json()
        assert r["CANDIDATE_NOT_APPROVED"] is True and r["target_quarter"] == "2027-Q1"
        assert c.get("/api/v1/admin/candidates/e140-lgbm-native-1.0/lgus").json()["n"] == 142
        assert c.get("/api/v1/admin/candidates/e140-lgbm-native-1.0/register").json()["verified"] is True
    finally:
        app.dependency_overrides.pop(require_admin, None)


def test_nlp_validity_recorded():
    v = json.loads((E140 / "nlp_validity.json").read_text())
    assert v["V3_archive_risk_share_vs_cyclones"]["n"] > 100
    assert "Convergent validity only" in v["note"]
