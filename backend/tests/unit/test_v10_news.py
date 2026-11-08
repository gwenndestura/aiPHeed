"""
tests/unit/test_v10_news.py
---------------------------
The v10 news gate: publication before the issue only, share normalised by volume, no coverage is not zero, and a topic
model fitted on all years must fail.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.forecasting.as_of import LeakageError
from app.forecasting.v10 import news as N

CAV, LAG = "PH040100000", "PH040200000"


def frame() -> pd.DataFrame:
    return pd.DataFrame([
        {"published_ph": "2026-07-10T08:00:00+08:00", "geo_province_code": CAV, "relevant": 1, "source_domain": "a"},
        {"published_ph": "2026-08-10T08:00:00+08:00", "geo_province_code": CAV, "relevant": 0, "source_domain": "b"},
        {"published_ph": "2026-08-11T08:00:00+08:00", "geo_province_code": None, "relevant": 1, "source_domain": "a"},
    ])


def test_injected_future_article_is_rejected():
    honest = N.food_stress_share(frame(), "2026-10-01", "2026-07-01", CAV)
    future = pd.DataFrame([{"published_ph": "2026-10-01T00:00:00+08:00", "geo_province_code": CAV, "relevant": 1,
                            "source_domain": "z"}])
    assert N.food_stress_share(pd.concat([frame(), future], ignore_index=True), "2026-10-01", "2026-07-01", CAV) == honest


def test_article_just_before_issue_is_kept():
    late = pd.DataFrame([{"published_ph": "2026-09-30T23:59:00+08:00", "geo_province_code": CAV, "relevant": 1,
                          "source_domain": "z"}])
    assert N.food_stress_share(pd.concat([frame(), late], ignore_index=True), "2026-10-01", "2026-07-01", CAV)["count"] == 3


def test_share_is_normalised_by_volume():
    assert N.food_stress_share(frame(), "2026-10-01", "2026-07-01", CAV) == {"share": 0.5, "count": 2, "sources": 2}


def test_no_coverage_is_missing_not_zero():
    r = N.food_stress_share(frame(), "2026-10-01", "2026-07-01", LAG)
    assert np.isnan(r["share"]) and r["count"] == 0


def test_broader_area_news_is_kept_separate():
    assert N.food_stress_share(frame(), "2026-10-01", "2026-07-01", None) == {"share": 1.0, "count": 1, "sources": 1}


def test_missing_publication_time_raises():
    bad = frame()
    bad.loc[0, "published_ph"] = None
    with pytest.raises(LeakageError):
        N.food_stress_share(bad, "2026-10-01", "2026-07-01", CAV)


def test_topic_model_fitted_on_all_years_fails():
    with pytest.raises(LeakageError):
        N.assert_topic_fit_is_past_only(pd.Series(["2023-01-01T00:00:00+08:00", "2026-10-01T00:00:00+08:00"]), "2026-10-01")


def test_topic_model_fitted_on_past_passes():
    N.assert_topic_fit_is_past_only(pd.Series(["2023-01-01T00:00:00+08:00", "2026-09-30T23:59:00+08:00"]), "2026-10-01")
