"""Operational completion pieces: provincial prospective register (hash chain, write-once seals), the E140 next-quarter
candidate issue (dynamic target quarter, 142 LGUs labelled as a ranking, intervals), per-candidate check counts in the
release-gated outlook, admin-only candidate route, and the NLP convergent-validity output."""
from __future__ import annotations

import json

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


def test_scoring_uses_e137_target_rules(tmp_path):
    rows = pd.DataFrame({"province": ["Quezon", "Cavite", "Abra", "Sulu"], "survey": "X", "year": 2027,
                         "p": [50.0, 30.0, 70.0, 80.0], "se_p": [2.0, 2.0, 2.0, 2.0], "ref": 42.8, "instrument": "HFIAS"})
    f = tmp_path / "round.csv"
    rows.to_csv(f, index=False)
    res = PP.score(str(f))
    for mid in ("e138-where-lrp-1.0", "e139-lgbm-1.0", "e140-lgbm-native-1.0"):
        assert res["models"][mid]["n"] == 4 and 0 <= res["models"][mid]["expected_brier"] <= 1


def test_next_quarter_issue_and_lgus():
    f = json.loads((E140 / "forecast_next_quarter.json").read_text())
    assert f["lead"] == 1 and f["target_quarter"] == "2027-Q1" and f["issue_date"] == "2026-10-01"
    assert f["final_model"]["n_trees"] > 0 and "CANDIDATE" in f["validation_status"]
    assert "not the share of food-insecure households" in f["meaning"]
    for p in f["provinces"]:
        lo, hi = p["p_interval90"]
        assert 0 <= lo <= hi <= 1
    lg = pd.read_csv(E140 / "lgus_next_quarter.csv")
    assert len(lg) == 142 and lg["lgu_psgc"].is_unique
    assert lg["label"].str.contains("not a municipal food-insecurity measurement").all()
    assert ((lg["risk_score_low"] <= lg["risk_score"]) & (lg["risk_score"] <= lg["risk_score_high"])).all()


def test_outlook_reports_each_candidates_own_check_count():
    from app.main import app
    c = TestClient(app)
    out = c.get("/api/v1/final/food-insecurity/outlook").json()
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
