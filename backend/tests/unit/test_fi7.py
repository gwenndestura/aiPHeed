"""FI7 tests: release-aware issue dates, no future information, new indicators' release rules, model mechanics,
training-only thresholds, and the API."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.fi5.target import qindex
from app.fi7 import extra_sources as X
from app.fi7 import models as M
from app.fi7.design import Designer, issue_date
from app.fi7.paths import OUT


def test_issue_dates():
    assert issue_date(qindex("2026-Q4"), "operational") == pd.Timestamp("2026-11-30")
    assert issue_date(qindex("2025-Q1"), "operational") == pd.Timestamp("2025-02-28")
    assert issue_date(qindex("2025-Q1"), "quarter_end") == pd.Timestamp("2025-03-31")


@pytest.fixture(scope="module")
def frame():
    return Designer("operational").frame(1)


def test_operational_rows_use_only_published_information(frame):
    r = frame[frame["target_quarter"] == "2026-Q1"].iloc[0]
    assert r["issue_date"] == "2025-11-30" and r["last_reading_quarter"] == "2025-Q3"   # released 2025-11-05
    L = frame[frame["y"].notna()]
    o = L[L["tqi"] >= qindex("2018-Q1")].iloc[0]
    tr = L[L["target_published"] <= o["issue_ts"]]
    assert tr["tqi"].max() < o["tqi"]


def test_release_rules_never_earlier_than_reference_period():
    c = X.load_cache()
    for k in ["world", "under", "fish"]:
        assert (c[k]["available_from"] > c[k]["period_end"]).all(), k
    r = X.asof_extra(pd.Timestamp("2024-11-30"), pd.Timestamp("2024-10-01"), c)
    w = c["world"]
    assert r["world_rice_yoy"] == pytest.approx(w[w["available_from"] <= "2024-11-30"]["world_rice_yoy"].iloc[-1])


def test_damped_persistence_recovers_decay():
    rng = np.random.default_rng(1)
    n = 80
    base = np.full(n, 12.0)
    last = base + rng.normal(0, 4, n)
    tgt = base + 0.6 * (last - base) + rng.normal(0, 0.5, n)
    df = pd.DataFrame({"hunger_last": last, "baseline_known": base, "hunger_target": tgt, "hunger_age_q": np.ones(n),
                       "threshold_known": base + 5})
    m = M.Damped().fit(df, tgt - last)
    assert m.phi == pytest.approx(0.6, abs=0.05)


def test_threshold_is_chosen_on_training_folds_only():
    rng = np.random.default_rng(2)
    n = 70
    df = pd.DataFrame({"hunger_last": rng.normal(15, 4, n), "baseline_known": 12.0, "hunger_age_q": 1.0})
    df["hunger_target"] = 12 + 0.5 * (df["hunger_last"] - 12) + rng.normal(0, 2, n)
    df["threshold_known"] = 17.0
    df["y"] = (df["hunger_target"] > 17).astype(int)
    m = M.Thresholded(lambda: M.Damped()).fit(df, df["hunger_target"] - df["hunger_last"])
    assert 0.1 <= m.tau <= 0.9
    np.testing.assert_allclose(m.predict_proba(df), m.inner.predict_proba(df))   # probabilities untouched


@pytest.mark.skipif(not (OUT / "forecast.json").exists(), reason="run python -m app.fi7.serve issue first")
def test_api_fi7():
    from app.main import app
    c = TestClient(app)
    for p in ["forecast", "evaluation", "experiments", "lgus", "provinces"]:
        assert c.get(f"/api/v1/fi7/{p}").status_code == 200, p
    f = c.get("/api/v1/fi7/forecast").json()
    nq = [x for x in f["forecasts"] if x["h"] == 1][0]
    assert nq["target_quarter"] > nq["current_quarter"]
    assert c.get("/api/v1/fi7/lgus").json()["n"] == 142
