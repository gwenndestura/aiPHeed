"""E144: lock; as-of guarantees (labels, history and training rows never come from after the issue date); link algebra;
issued forecast covers the five provinces for viewing quarter + 1..4 with the stated class rule; admin-only route."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app import registry as R
from app.e144 import OUT
from app.e144 import data as D
from app.e144 import evaluate as E
from app.e144 import link as L
from app.e144 import model as MA
from app.fi5.target import qindex
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


def test_history_and_news_are_as_of_the_issue_date():
    X = MA.panel()
    s = D.sws_quarterly().set_index(["area", "qi"])["published"]
    sample = X.dropna(subset=["hunger_last"]).sample(200, random_state=0)
    for _, r in sample.iterrows():
        assert r["hunger_age_q"] >= r["h"] + 1                     # last reading is at or before the issue quarter
        last_q = int(r["target_qi"] - r["hunger_age_q"])
        assert s[(r["area"], last_q)] <= r["issue_date"]
    n = D.news_quarterly()
    assert all(pe == D.q_end(int(q)) for pe, q in zip(n["period_end"], n["qi"]))   # a quarter's news is usable only after it ends
    assert D.news("balance_luzon", qindex("2020-Q1"), D.q_end(qindex("2019-Q4"))) == {}   # quarter not complete yet


def test_training_rows_never_use_labels_published_after_issue():
    X = MA.panel()
    i = qindex("2021-Q1")
    d = D.q_end(i)
    W1 = MA.walk_forward(X, i, i, pd.Timestamp("2026-10-01"))
    Xc = X.copy()
    late = Xc["label_published"] > d
    Xc.loc[late & (Xc["issue_qi"] != i), "y"] = 1 - Xc.loc[late & (Xc["issue_qi"] != i), "y"]   # corrupt future labels
    W2 = MA.walk_forward(Xc, i, i, pd.Timestamp("2026-10-01"))
    assert np.allclose(W1["A LightGBM (full)"].values, W2["A LightGBM (full)"].values)


def test_link_recovers_coefficients_on_synthetic_data():
    rng = np.random.default_rng(0)
    n = 400
    X = pd.DataFrame({"H": rng.uniform(5, 30, n), "r_hat": rng.normal(0, 0.4, n), "se_abs": np.full(n, 0.1)})
    X["y_abs"] = -1.0 + 0.8 * MA._logit(X["H"]) + 1.0 * X["r_hat"] + rng.normal(0, 0.15, n)
    m = L.fit(X, True)
    assert abs(m["beta"][2] - 0.8) < 0.1 and abs(m["beta"][1] - 1.0) < 0.1


def test_issue_covers_five_provinces_four_quarters_and_class_rule():
    f = json.loads((OUT / "issue" / "forecast.json").read_text())
    F = pd.DataFrame(f["forecasts"])
    assert set(F["province"]) == {"Cavite", "Laguna", "Batangas", "Rizal", "Quezon"}
    assert sorted(F["h"].unique()) == [1, 2, 3, 4]
    v = qindex(f["viewing_quarter"])
    assert f["dashboard_target_quarter"] == F.loc[F["h"] == 1, "target_quarter"].iloc[0]
    for _, r in F.iterrows():
        assert qindex(r["target_quarter"]) == v + int(r["h"])
        want = "HIGH" if r["p_high"] >= 0.8 else "LOW" if r["p_high"] <= 0.2 else "UNCERTAIN"
        assert r["risk_class"] == want
    lg = pd.read_csv(OUT / "issue" / "lgus_next_quarter.csv")
    assert len(lg) == 142 and lg["label"].str.contains("not a municipal food-insecurity measurement").all()


def test_registry_and_admin_route_only():
    from app.main import app
    from app.services.security import require_admin
    assert R.load().get("production") is None
    assert "e144-lbf-1.0" in {x["model_id"] for x in PP.read()} and PP.verify()
    c = TestClient(app)
    assert c.get("/api/v1/admin/candidates/e144-lbf-1.0/outlook").status_code in (401, 403)
    app.dependency_overrides[require_admin] = lambda: object()
    try:
        o = c.get("/api/v1/admin/candidates/e144-lbf-1.0/outlook").json()
        assert o["CANDIDATE_NOT_APPROVED"] is True
    finally:
        app.dependency_overrides.pop(require_admin, None)
