"""E31: forecast vs nowcast news alignment (app/news/alignment.py)."""
from datetime import datetime

import pytest

import _paths  # noqa: F401
from app.news.alignment import AlignmentViolation, assert_aligned, evidence_window, provenance, select


def art(key, published, quarter):
    return {"article_key": key, "published_ph": published, "quarter": quarter}


ARTS = [art("q2_early", "2026-04-02T09:00:00+08:00", "2026-Q2"),
        art("q2_last_second", "2026-06-30T23:59:59+08:00", "2026-Q3"[:5] + "Q2"),
        art("q3_oct_after", "2026-09-30T10:00:00+08:00", "2026-Q3"),
        art("q3_aug", "2026-08-15T12:00:00+08:00", "2026-Q3"),
        art("q4_oct5", "2026-10-05T08:00:00+08:00", "2026-Q4"),
        art("q4_oct10_late", "2026-10-10T23:00:00+08:00", "2026-Q4"),
        art("q4_oct11", "2026-10-11T00:00:01+08:00", "2026-Q4")]


def keys(xs):
    return sorted(a["article_key"] for a in xs)


def test_forecast_uses_previous_quarter_news_only():
    w = evidence_window("2026-Q3", "forecast", "2026-06-30T23:59:59+08:00")
    assert w.evidence_quarter == "2026-Q2" and w.coverage == "FULL" and w.lead == 1
    used, why = select(ARTS, w)
    assert keys(used) == ["q2_early", "q2_last_second"]
    assert why["other_quarter"] == 5


def test_forecast_cutoff_inside_target_quarter_is_refused():
    with pytest.raises(AlignmentViolation):
        evidence_window("2026-Q3", "forecast", "2026-07-15T00:00:00+08:00")


def test_forecast_partial_window_when_cutoff_inside_evidence_quarter():
    w = evidence_window("2026-Q3", "forecast", "2026-05-31T23:59:59+08:00")
    assert w.coverage == "PARTIAL" and w.days_covered == 61
    assert keys(select(ARTS, w)[0]) == ["q2_early"]


def test_nowcast_uses_same_quarter_news_up_to_cutoff():
    w = evidence_window("2026-Q4", "nowcast", "2026-10-10")          # date = end of that PH day
    assert w.evidence_quarter == "2026-Q4" and w.coverage == "PARTIAL" and w.days_covered == 10
    used, _ = select(ARTS, w)
    assert keys(used) == ["q4_oct10_late", "q4_oct5"]               # Oct 11 excluded; no Q3 stand-in


def test_nowcast_before_target_start_is_refused():
    with pytest.raises(AlignmentViolation):
        evidence_window("2026-Q4", "nowcast", "2026-09-30T23:59:59+08:00")


def test_nowcast_of_ended_quarter_is_full():
    w = evidence_window("2026-Q3", "nowcast", "2026-10-14T12:00:00+08:00")
    assert w.coverage == "FULL" and keys(select(ARTS, w)[0]) == ["q3_aug", "q3_oct_after"]


def test_lead2_forecast_and_bad_leads():
    w = evidence_window("2026-Q3", "forecast", "2026-04-01T00:00:00+08:00", lead=2)
    assert w.evidence_quarter == "2026-Q1"
    with pytest.raises(AlignmentViolation):
        evidence_window("2026-Q3", "forecast", "2026-06-30", lead=0)
    with pytest.raises(AlignmentViolation):
        evidence_window("2026-Q3", "nowcast", "2026-08-01", lead=1)
    with pytest.raises(AlignmentViolation):
        evidence_window("2021-Q1", "forecast", "2020-12-31")        # evidence before the study window


def test_assert_aligned_catches_leaked_article_and_provenance_hash():
    w = evidence_window("2026-Q4", "nowcast", "2026-10-10")
    with pytest.raises(AlignmentViolation):
        assert_aligned([ARTS[-1]], w)
    used, _ = select(ARTS, w)
    assert_aligned(used, w)
    p1 = provenance(w, datetime(2026, 10, 10, 23, 30), {"store": "news_e31"}, [a["article_key"] for a in used])
    p2 = provenance(w, datetime(2026, 10, 10, 23, 30), {"store": "news_e31"}, reversed([a["article_key"] for a in used]))
    assert p1 == p2 and p1["mode"] == "nowcast" and p1["information_cutoff"].startswith("2026-10-10T23:59:59")


def test_authorized_limit_caps_window():
    from datetime import timezone, timedelta
    lim = datetime(2026, 10, 15, tzinfo=timezone(timedelta(hours=8)))
    w = evidence_window("2026-Q4", "nowcast", "2026-12-31", authorized_limit_excl=lim)
    assert w.window_end_excl_ph.startswith("2026-10-15T00:00:00") and w.coverage == "PARTIAL"
