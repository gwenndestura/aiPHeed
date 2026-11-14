"""E142: lock; the state model's identification rules (phi = 0 without a measured transition, phi in [0, 1], variance
grows with quarters since the survey); exact explanation decomposition of the issued forecast; FSSI v2 volume
correction is as-of and removes volume dependence; registry, register and the admin route."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import registry as R
from app.e142 import OUT
from app.e142 import evaluate as E
from app.e142 import model as M
from app.registry import prospective_provincial as PP


@pytest.fixture(autouse=True)
def _restore_e137_paths():
    from app.e137 import features as F
    saved = F.HRAW
    yield
    F.HRAW = saved
    for fn in (F._cpi, F._psa_rounds, F._quarterly):
        fn.cache_clear()


def test_lock():
    E.verify_lock()


def test_phi_not_identified_without_transitions_and_bounded():
    r = json.loads((OUT / "results.json").read_text())
    for p in r["rolling"]["params"]:
        assert 0.0 <= p["phi"] <= 1.0
        if p["n_transitions"] == 0:
            assert p["phi"] == 0.0 and p["weight_on_previous_round"] == 0.0


def test_variance_grows_with_quarters_since_survey():
    sm = M.StateModel("ridge")
    sm.phi_, sm.tau2_ = 0.93, 0.2
    sm.mu_model_ = type("Mu", (), {"predict_y": lambda self, X: np.zeros(len(X))})()
    X = pd.DataFrame({"prev_y": [0.5, 0.5], "prev_se_y": [0.1, 0.1]})
    _, V = sm.predict(X, h=np.array([4.0, 40.0]))
    assert V[0] < V[1] <= sm.tau2_ + 1e-12


def test_issued_forecast_decomposes_exactly_and_classes_follow_rule():
    f = json.loads((OUT / "issue" / "forecast_next_quarter.json").read_text())
    assert f["display_lead"] == 1 and "NOT validated" in f["claim"] and len(f["provinces"]) == 5
    for q in f["provinces"]:
        total = q["base_logit"] + sum(e["contribution_logit"] for e in q["explanations"])
        assert abs(total - q["relative_logit_forecast"]) < 0.01
        p, (lo, hi) = q["p_elevated"], q["p_interval90"]
        assert q["risk_class"] == ("HIGH" if p >= 0.8 and lo >= 0.5 else "LOW" if p <= 0.2 and hi < 0.5 else "UNCERTAIN")
        assert 0 < q["weight_on_last_survey"] < 1 and q["quarters_since_last_survey"] >= 30
    lg = pd.read_csv(OUT / "issue" / "lgus_next_quarter.csv")
    assert len(lg) == 142 and lg["label"].str.contains("not a municipal food-insecurity measurement").all()


def test_fssi_v2_is_as_of_and_removes_volume_dependence():
    d = pd.read_csv(OUT / "fssi_v2_province_quarter.csv")
    first = d.sort_values("quarter").groupby("province").head(1)
    assert first["fssi_v2"].isna().all()                     # no past quarters -> no baseline -> no value
    v = json.loads((OUT / "fssi_v2_validity.json").read_text())
    assert abs(v["T1_volume_dependence"]["fssi_v2"]["spearman"]) < abs(v["T1_volume_dependence"]["raw_share"]["spearman"]) / 2
    assert v["T3_convergent_validity"]["fssi_v2_vs_cyclones"]["p_one_sided"] < 0.05


def test_registry_register_and_route():
    from app.main import app
    from app.services.security import require_admin
    assert R.load()["models"]["e142-state-lgbm-1.0"]["status"] == "rejected" and (R.load().get("production") or {}).get("model_id") != "e142-state-lgbm-1.0"
    assert "e142-state-lgbm-1.0" in {r["model_id"] for r in PP.read()} and PP.verify()
    c = TestClient(app)
    assert c.get("/api/v1/admin/candidates/e142-state-lgbm-1.0/outlook").status_code in (401, 403)
    app.dependency_overrides[require_admin] = lambda: object()
    try:
        o = c.get("/api/v1/admin/candidates/e142-state-lgbm-1.0/outlook").json()
        assert o["CANDIDATE_NOT_APPROVED"] is True and o["target_quarter"] == "2027-Q1"
    finally:
        app.dependency_overrides.pop(require_admin, None)


@pytest.mark.legacy_served
def test_ch1_explanation_is_labelled_as_price_pressure():
    from app.main import app
    d = TestClient(app).get("/api/v1/explainability?scope=province&id=quezon").json()
    notes = {t["statusNote"] for t in d["triggers"]}
    assert all("price-pressure risk index" in n or "No official" in n for n in notes)
