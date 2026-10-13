"""
tests/integration/test_api_ranking.py
--------------------------------------
Province ranking (Section 1.2) and CPI_dev (Equation 5).

* The served order is the model's own probability, never anything else.
* Ties are reported as ties, not ordered arbitrarily.
* A withheld province is not ranked, and no other row points at it.
* The SHAP differences behind "why above the next province" add up to the gap
  in probability, because Equation 7 is additive.
* CPI_dev is the deviation from the province's own rolling mean over EARLIER
  quarters only (Equation 5 legend, Rule 3).
"""

from __future__ import annotations

import pandas as pd
import pytest

from app.ml.features.feature_matrix import CPI_DEV_WINDOW
from app.ml.inference.explainer import Explainer
from tests.integration.test_api_admin import api, auth_headers, make_user  # noqa: F401

QUARTER = "2025-Q4"


def test_cpi_dev_uses_only_earlier_quarters():
    f = pd.read_parquet("data/processed/features_fused.parquet").sort_values(
        ["province_code", "quarter"])
    for code, g in f.groupby("province_code"):
        g = g.reset_index(drop=True)
        for i in range(2, len(g)):
            prior = g.loc[max(0, i - CPI_DEV_WINDOW):i - 1, "food_cpi_yoy"]
            assert g.loc[i, "cpi_dev"] == pytest.approx(
                g.loc[i, "food_cpi_yoy"] - prior.mean(), abs=1e-9), (code, g.loc[i, "quarter"])


def test_ranking_follows_probability(api):
    body = api.get(f"/api/v1/ranking?quarter={QUARTER}").json()
    probs = [r["riskScore"] for r in body["data"]]
    assert probs == sorted(probs, reverse=True)
    assert [r["rank"] for r in body["data"]] == list(range(1, len(probs) + 1))
    for a, b in zip(body["data"], body["data"][1:]):
        assert a["gapToNextLower"] == pytest.approx(a["riskScore"] - b["riskScore"], abs=1e-4)
        assert a["tiedWithNextLower"] == (a["gapToNextLower"] == 0.0)
    assert body["method"]


def test_why_above_next_sums_to_the_gap():
    from app.ml.inference.predictor import Predictor

    fc = Predictor().forecast_quarter(QUARTER)
    a, b = fc[0], fc[1]
    ex = Explainer()
    sa = {r["feature_name"]: r["shap_value"] for r in ex.explain_province_quarter(a["province_code"], QUARTER)}
    sb = {r["feature_name"]: r["shap_value"] for r in ex.explain_province_quarter(b["province_code"], QUARTER)}
    total = sum(sa[k] - sb[k] for k in sa)
    assert total == pytest.approx(a["risk_probability"] - b["risk_probability"], abs=0.02)


def test_withheld_province_is_not_ranked(api):
    make_user(api)
    headers = auth_headers(api)
    api.get(f"/api/v1/admin/review?quarter={QUARTER}", headers=headers)
    api.post("/api/v1/admin/review/rv_2025Q4_laguna/reject", headers=headers,
             json={"reason": "Sensitive context - withhold publication"})

    rows = {p["id"]: p for p in api.get(f"/api/v1/provinces?quarter={QUARTER}").json()["data"]}
    assert rows["laguna"]["rank"] is None
    published = [p for p in rows.values() if not p["withheld"]]
    assert sorted(p["rank"] for p in published) == [1, 2, 3, 4]
    assert all(p["rankOf"] == 4 for p in published)

    body = api.get(f"/api/v1/ranking?quarter={QUARTER}").json()
    assert "laguna" not in {r["id"] for r in body["data"]}
    assert all(r["nextLowerId"] != "laguna" for r in body["data"])
