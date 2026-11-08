"""
tests/unit/test_v2_legacy_leakage.py
------------------------------------
Leak tests for the legacy feature paths that do not go through app.forecasting.as_of (AUDIT D5; v2 step 5). Each
test injects information dated at or after the issue and requires it to be excluded, with a positive control that
the same injection dated just before the issue IS used (so the test cannot pass vacuously).

  FIRI v2 normalisation history   app.ml.inference.thesis_system.prior_for (values at strictly earlier origins)
  News / NLP (FSSI-v3, N3)        app.news.pipeline_v3.asof (articles published before O(t), by timestamp)
  Dashboard quarterly clock       app.quarterly.target.forecast_target (information cutoff = quarter start, exclusive)
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.ml.inference import thesis_system as TS
from app.news import pipeline_v3 as P3
from app.quarterly.target import forecast_target


def _qi(q: str) -> int:
    return int(q[:4]) * 4 + int(q[-1]) - 1


# ---------------------------------------------------------------- FIRI v2 normalisation history
def test_firi_prior_excludes_same_and_later_origins(monkeypatch):
    vals = {"A2": [("2025-Q4", 1.0), ("2026-Q1", 2.0), ("2026-Q2", 999.0), ("2026-Q3", 888.0)]}
    monkeypatch.setattr(TS, "reference", lambda: {"values": vals})
    p = TS.prior_for("2026-Q2")
    assert p["A2"] == [1.0, 2.0]                       # the origin itself and later origins never enter
    assert 999.0 not in p["A2"] and 888.0 not in p["A2"]


def test_firi_prior_positive_control(monkeypatch):
    vals = {"A2": [("2026-Q1", 5.0)]}
    monkeypatch.setattr(TS, "reference", lambda: {"values": vals})
    assert TS.prior_for("2026-Q2")["A2"] == [5.0]      # one quarter earlier IS used


# ---------------------------------------------------------------- news / NLP by publication timestamp
def _art(t: int, published: datetime, key: str) -> dict:
    return {"quarter": P3.qs(t), "published_ph": published.isoformat(), "province_code": "PH040100000",
            "article_key": key, "relevant": 1}


@pytest.mark.parametrize("t", [_qi("2025-Q3"), _qi("2026-Q2")])
def test_news_asof_excludes_articles_at_or_after_issue(monkeypatch, t):
    O = P3.origin(t)
    arts = (_art(t, O - timedelta(seconds=1), "before"), _art(t, O, "at_issue"), _art(t, O + timedelta(days=3), "after"))
    monkeypatch.setattr(P3, "admitted", lambda: arts)
    keys = {a["article_key"] for a in P3.asof(t)}
    assert keys == {"before"}                           # positive control kept; on/after the issue dropped


def test_news_origin_is_first_day_of_next_quarter():
    t = _qi("2026-Q3")
    assert P3.origin(t) == datetime(2026, 10, 1)


# ---------------------------------------------------------------- dashboard clock
@pytest.mark.parametrize("now,cut", [("2026-11-01T10:00", "2026-10-01T00:00:00+08:00 (exclusive)"),
                                     ("2027-01-01T00:00", "2027-01-01T00:00:00+08:00 (exclusive)")])
def test_dashboard_cutoff_is_quarter_start_exclusive(now, cut):
    assert forecast_target(now)["information_cutoff"] == cut
