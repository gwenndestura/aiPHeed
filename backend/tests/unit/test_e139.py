"""E139 final system: lock, no identifier features, linear-prior behaviour, history features use only earlier
surveys, live features respect release dates, 142-LGU coverage labelled as vulnerability, registry status and API
gating (candidate on admin routes only; public outlook stays validation_pending unless approved)."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from app import registry as R
from app.e139 import OUT
from app.e139 import evaluate as E
from app.e139 import live as LV
from app.e139 import model as M

X = M.data()


def test_protocol_lock_matches_code():
    E.verify_lock()


def test_no_identifier_or_label_features():
    banned = {"key", "province", "region", "island", "survey", "year", "y", "q", "status", "p", "se_y"}
    assert not banned & set(M.ALL)
    assert set(M.BASE) <= set(M.ALL)


def test_history_features_come_from_earlier_surveys_only():
    f15 = X[X["survey"] == "FNRI2015"]
    assert f15["a_prev_y"].isna().all() and f15["a_region_prev"].isna().all()
    enns = X[X["survey"] != "FNRI2015"]
    reg15 = f15.groupby("region")["y"].mean()
    assert np.allclose(enns["a_region_prev"], enns["region"].map(reg15))


def test_zero_trees_equals_the_linear_prior():
    t = X.sample(80, random_state=1)
    m = M.LGBM()
    m.alpha_ = 10.0
    base, booster = m._fit(t, 0)
    assert booster is None
    assert np.allclose(M.LGBM._pred(base, None, t, m.cols), base.predict_y(t))


def test_tfwd_is_strictly_forward():
    tr, te = next(E.folds(X, "TFWD"))
    assert set(X.loc[te, "survey"]) == {"ENNS2019"} and "ENNS2019" not in set(X.loc[tr, "survey"])


def test_live_features_respect_release_dates():
    Z = pd.read_csv(OUT / "live_features.csv")
    assert (Z["issue_date"] == "2026-10-01").all() and len(Z) == 78
    cols = [c for c in pd.read_csv(LV.RAW / "psa" / "palay_corn_q_2023_2026.csv", nrows=0).columns if "Quarter" in c]
    pub = LV.F._published_quarters(cols, LV.ISSUE)
    assert pub[-1] == "2026 Quarter 2"                     # Q3 2026 is public only from 14 Nov 2026


def test_outputs_cover_all_calabarzon_lgus_as_vulnerability():
    lg = pd.read_csv(OUT / "lgus_calabarzon.csv")
    assert len(lg) == 142 and lg["province_name"].value_counts().to_dict() == {"Quezon": 41, "Batangas": 34, "Laguna": 30,
                                                                               "Cavite": 23, "Rizal": 14}
    assert lg["label"].str.contains("not a municipal food-insecurity measurement").all()
    live = json.loads((OUT / "provinces_live.json").read_text())
    assert len(live["provinces"]) == 5 and all(0 <= p["p_elevated"] <= 1 for p in live["provinces"])
    assert all(not l["validated"] for l in live["leads"]) == (live["max_reliable_lead"] is None)


def test_registry_rejected_and_api_gated():
    from app.main import app
    from app.services.security import require_admin
    m = R.load()["models"]["e139-lgbm-1.0"]
    assert m["status"] == "rejected" and R.load().get("production") is None
    c = TestClient(app)
    assert c.get("/api/v1/final/food-insecurity/outlook").json()["status"] == "validation_pending"
    assert c.get("/api/v1/admin/candidates/e139-lgbm-1.0/outlook").status_code in (401, 403)
    app.dependency_overrides[require_admin] = lambda: object()
    try:
        r = c.get("/api/v1/admin/candidates/e139-lgbm-1.0/outlook").json()
        assert r["CANDIDATE_NOT_APPROVED"] is True and len(r["provinces"]) == 5
        assert c.get("/api/v1/admin/candidates/e139-lgbm-1.0/lgus").json()["n"] == 142
    finally:
        app.dependency_overrides.pop(require_admin, None)
