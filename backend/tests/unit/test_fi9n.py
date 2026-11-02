"""FI9-N tests: FI6-N reproduction, horizon definitions, locked decisions, preservation of the news pipeline."""
from __future__ import annotations

import json

import pandas as pd

from app.fi9 import quarters as Q
from app.fi9n import OUT
from app.paths import BACKEND_DIR

S = json.loads((OUT / "news_study.json").read_text())


def test_protocol_lock_matches():
    from app.fi9n.study import _digest
    assert json.loads((OUT / "PROTOCOL_LOCK.json").read_text())["sha256"] == _digest() == S["protocol_sha256"]


def test_fi6n_reproduced_exactly():
    for h in ("QE1", "QE2"):
        assert max(S["rerun_vs_fi6n_saved_max_abs_p_diff"][h].values()) < 1e-9
    rep = S["fi6n_reproduction"]["lead1"]
    for c, b in rep["reported_brier"].items():
        assert abs(rep["recomputed"][c]["brier"] - b) < 1e-9
    a, b = rep["recomputed_gov_news_minus_gov"], rep["reported_gov_news_minus_gov"]
    assert all(abs(x - y) < 1e-9 for x, y in zip(a, b))


def test_horizon_issue_dates_and_targets():
    pr = pd.read_csv(OUT / "news_predictions.csv")
    for h, off in [("QE1", 1), ("OP1", 1), ("OP1w", 1), ("OP0", 0), ("QE2", 2)]:
        g = pr[pr["horizon"] == h]
        iq = g["issue_date"].map(Q.qi_of)
        assert (g["target_quarter"].map(Q.index) == iq + off).all(), h
        d = pd.to_datetime(g["issue_date"])
        if h.startswith("QE"):
            assert all(x == Q.end(Q.qi_of(x)) for x in d), h            # last day of the issue quarter
        else:
            assert all(x == Q.scheduled_issue(Q.qi_of(x)) for x in d), h  # end of the quarter's 2nd month
        assert (pd.to_datetime(g["train_max_target_published"]) <= d).all(), h
    n = pr.groupby("horizon")["target_quarter"].apply(frozenset)
    assert n.nunique() == 1                                               # same target quarters for every horizon


def test_locked_decisions_are_consistent_with_numbers():
    q, o = S["horizons"]["QE1"], S["horizons"]["OP1"]
    assert q["decisions"]["probability_quality_improved_95"] == (q["news_vs_no_news"]["ci95"][1] < 0)
    assert q["decisions"]["probability_quality_improved_bonferroni"] == (q["news_vs_no_news"]["ci99_bonferroni5"][1] < 0)
    assert o["decisions"]["probability_quality_improved_95"] == (o["news_vs_no_news"]["ci95"][1] < 0)
    for h, H in S["horizons"].items():
        assert H["decisions"]["beyond_latest_reading"] == (H["gov_news_vs_persistence"]["ci95"][1] < 0
                                                           or H["news_latest_vs_persistence"]["ci95"][1] < 0), h


def test_news_pipeline_preserved():
    for p in ["app/fi6/news_archive.py", "app/fi6/news_events.py", "app/fi6/news_model.py", "app/fi5/explain.py",
              "data/fi6/news_archive/articles.parquet", "data/fi6/news_archive/xlmr_scores_archive.parquet",
              "data/fi6/out_news/news_walkforward_predictions.csv", "data/fi6/out_news/news_evaluation.json"]:
        assert (BACKEND_DIR / p).exists(), p


def test_served_explanation_states_news_finding_precisely():
    f = json.loads((BACKEND_DIR / "data" / "fi9" / "out" / "forecast.json").read_text())
    assert "last day of the quarter" in f["explanation"] and "not better than the latest reading" in f["explanation"]
