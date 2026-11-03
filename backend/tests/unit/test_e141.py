"""E141: the recovered 2013 HFIAS round (parsed values against the FNRI table, comparability, approximate SE flagged),
the three-round panel (history only from the previous round; no 2013 row in the untouched test's training), the lock,
the frozen decision rule, the registry and the candidate route."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import registry as R
from app.e141 import DATA, OUT
from app.e141 import evaluate as E
from app.e141 import panel as P

T13 = pd.read_csv(DATA / "clean" / "nns2013_hfias.csv")

@pytest.fixture(autouse=True)
def _restore_e137_paths():
    """panel.data points E137's builders at the longer PSA files (process-wide, as in the locked run); restore them so
    later tests see E137's own inputs."""
    from app.e137 import features as F
    saved = F.HRAW
    yield
    F.HRAW = saved
    for fn in (F._cpi, F._psa_rounds, F._quarterly):
        fn.cache_clear()

def test_2013_table_matches_fnri_appendix_33():
    assert len(T13) == 78 and T13["sum_check"].between(99.9, 100.1).all()
    r = T13.set_index("province")
    assert tuple(r.loc["Batangas", ["n", "food_secure_pct", "mild_pct", "moderate_pct", "severe_pct"]]) == (713, 41.86, 17.36, 29.59, 11.19)
    assert tuple(r.loc["Quezon", ["moderate_pct", "severe_pct"]]) == (35.40, 13.47)
    assert r.loc["Sulu", "severe_pct"] == 52.07
    assert set(T13["instrument"]) == {"HFIAS"} and T13["se_method"].str.startswith("approximate").all()
    assert P.NAT2013["mod_sev"] == 50.8

def test_panel_history_comes_only_from_the_previous_round():
    X = P.data(1)
    assert X.groupby("survey").size().to_dict() == {"NNS2013": 78, "FNRI2015": 78, "ENNS2018": 22, "ENNS2019": 25}
    assert X.loc[X["survey"] == "NNS2013", ["a_prev_y", "a_region_prev"]].isna().all().all()
    f15 = X[X["survey"] == "FNRI2015"].set_index("key")
    t13 = X[X["survey"] == "NNS2013"].set_index("key")
    assert np.allclose(f15["a_prev_y"], t13.loc[f15.index, "y"])
    enns = X[X["survey"].str.startswith("ENNS")].set_index("key")
    assert np.allclose(enns["a_prev_y"], f15.loc[enns.index, "y"])
    assert (pd.to_datetime(X["issue_date"]) < pd.to_datetime(X["year"].astype(str) + "-07-01")).all()

def test_rolling_origins_train_only_on_earlier_rounds():
    order = P.ROUND_ORDER
    for _, train, target in E.ORIGINS:
        assert max(order.index(t) for t in train) < order.index(target)

def test_lock_and_frozen_decision():
    E.verify_lock()
    r = json.loads((OUT / "results.json").read_text())
    c = r["gate"]["checks"]
    assert r["gate"]["survey_to_survey_forecast_validated"] == all(v for k, v in c.items() if k != "R3_trees_beat_linear_prior")
    assert r["untouched_2013"]["n"] == 78

def test_registry_and_candidate_route():
    from app.main import app
    from app.services.security import require_admin
    assert R.load()["models"]["e141-lgbm-3round-1.0"]["status"] == "rejected" and R.load().get("production") is None
    c = TestClient(app)
    assert c.get("/api/v1/admin/candidates/e141-lgbm-3round-1.0/outlook").status_code in (401, 403)
    app.dependency_overrides[require_admin] = lambda: object()
    try:
        o = c.get("/api/v1/admin/candidates/e141-lgbm-3round-1.0/outlook").json()
        assert o["CANDIDATE_NOT_APPROVED"] is True and len(o["provinces"]) == 5 and "NOT validated" in o["claim"]
        assert all(p["risk_class"] in ("HIGH", "LOW", "UNCERTAIN") for p in o["provinces"])
        assert c.get("/api/v1/admin/candidates/e141-lgbm-3round-1.0/lgus").json()["n"] == 142
    finally:
        app.dependency_overrides.pop(require_admin, None)
