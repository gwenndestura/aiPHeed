"""FI6 unit tests: uncertainty-aware target, a-priori features and monotone signs, probability machinery, training
labels published before issue, validation kit, API."""
from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from scipy.stats import norm

from app.fi5.target import qindex
from app.fi6 import models as M
from app.fi6.features import ALL, DOMAIN, MONOTONE, NEWS, NEWS_PARTS, OUTCOME, SETS, design
from app.fi6.paths import OUT
from app.fi6.target import BASELINE_Q, MIN_OBS, candidates, labels, quarterly


def test_target_is_significant_rise_above_normal():
    lab = labels().dropna(subset=["y"])
    q = quarterly()
    for _, r in lab.sample(20, random_state=1).iterrows():
        w = q[(q["qi"] >= r["qi"] - BASELINE_Q) & (q["qi"] < r["qi"])]
        assert len(w) >= MIN_OBS
        assert r["y"] == int(r["hunger"] - w["hunger"].mean() > r["moe"])


def test_target_more_reliable_than_fi5():
    c = candidates().set_index("target")
    fi6 = c.loc["FI6: above five-year average by more than the margin of error"]
    fi5 = c.loc["FI5: above five-year average"]
    assert fi6["mean_p_flip"] < fi5["mean_p_flip"] / 2


def test_five_domains_news_inside_each_and_signs():
    assert set(DOMAIN.values()) - {"outcome"} == {"market", "climate", "employment", "remittance", "poverty"}
    for d in ["market", "climate", "employment", "remittance", "poverty"]:
        fs = [f for f in ALL if DOMAIN[f] == d]
        assert any(f in NEWS for f in fs) and any(f not in NEWS for f in fs), d
    assert MONOTONE["cpi_food_yoy"] == 1 and MONOTONE["remit_yoy"] == -1 and MONOTONE["poverty_inc"] == 1
    assert set(MONOTONE) == set(ALL) and len(ALL) == 18
    assert not set(SETS["psa_only"]) & (set(NEWS) | set(OUTCOME))
    assert set(SETS["nlp_only"]) == set(NEWS)
    assert all(not any(p.startswith("topic_") for p in parts) for parts in NEWS_PARTS.values())


def test_training_rows_published_before_issue():
    X = design(1)
    L = X[X["y"].notna()]
    r = L[L["tqi"] >= qindex("2018-Q1")].iloc[0]
    tr = L[L["target_published"] <= r["issue_ts"]]
    assert tr["tqi"].max() < r["tqi"] and len(tr) > 30


def test_probability_machinery():
    df = pd.DataFrame({"hunger_last": [10.0, 20.0], "threshold_known": [15.0, 15.0]})
    p = M.Persistence().fit(df, np.array([-3.0, 3.0, -1.0, 1.0])).predict_proba(df)
    s = np.std([-3.0, 3.0, -1.0, 1.0], ddof=1)
    assert p == pytest.approx([1 - norm.cdf(5 / s), 1 - norm.cdf(-5 / s)])


def test_monotone_constraint_is_respected():
    rng = np.random.default_rng(0)
    n = 80
    X = pd.DataFrame({c: rng.normal(size=n) for c in ALL})
    y = -2.0 * X["cpi_food_yoy"] + rng.normal(size=n)          # data push the "wrong" way
    m = M.DeltaModel(ALL).fit(X, y.to_numpy())
    grid = X.iloc[[0] * 5].copy()
    grid["cpi_food_yoy"] = np.linspace(-2, 2, 5)
    d = m.predict_delta(grid)
    assert np.all(np.diff(d) >= -1e-9)                          # constrained: never decreasing in food inflation


def test_validation_kit_hides_model_labels():
    from app.fi6.nlp_validation import KEY, SHEET, sample
    if not SHEET.exists():
        sample()
    s = pd.read_csv(SHEET, encoding="utf-8-sig")
    assert len(s) == 200 and not any(c.startswith(("p_", "is_")) or c in ("stress", "evidence_type") for c in s.columns)
    assert len(pd.read_csv(KEY)) == 200


@pytest.mark.skipif(not (OUT / "forecast.json").exists(), reason="run python -m app.fi6.pipeline all first")
def test_api_fi6():
    from app.main import app
    c = TestClient(app)
    for path in ["status", "forecast", "evaluation", "baselines", "target", "provinces", "lgus", "nlp/validation"]:
        r = c.get(f"/api/v1/fi6/{path}")
        assert r.status_code == 200, path
    f = c.get("/api/v1/fi6/forecast").json()
    assert len(f["forecasts"]) == 4
    for x in f["forecasts"]:
        assert len([s for s in re.split(r"(?<=[.!?])\s+", x["explanation"].strip()) if s]) <= 2
    assert c.get("/api/v1/fi6/lgus").json()["n"] == 142
