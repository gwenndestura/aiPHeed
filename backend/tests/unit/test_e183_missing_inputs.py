"""E183 (docs/e183/DESIGN.md): inputs never missing in training are filled with the training median in forecast rows
only; inputs sometimes missing in training keep LightGBM's handling; the same step runs in validation and serving; the
dashboard warns when a used input was filled, and rows from before E183 show no warning."""
import inspect

import numpy as np
import pandas as pd

from app.e168 import lgbm_only, robust as RB, serve


def test_only_unseen_missing_inputs_are_filled():
    tr = pd.DataFrame({"a": [1.0, 2.0, 3.0, 10.0], "b": [1.0, np.nan, 3.0, 4.0], "c": [0.0, 0.0, 1.0, 1.0]})
    te = pd.DataFrame({"a": [np.nan, 5.0], "b": [np.nan, np.nan], "c": [np.nan, 1.0]})
    out, filled = RB.fill_unseen_missing(tr, te, ["a", "b", "c"])
    assert out.loc[0, "a"] == 2.5 and out.loc[0, "c"] == 0.5          # training medians
    assert np.isnan(out.loc[0, "b"]) and np.isnan(out.loc[1, "b"])     # b was missing in training: learned handling kept
    assert out.loc[1, "a"] == 5.0 and filled == [["a", "c"], []]
    assert te.isna().sum().sum() == 4                                  # the caller's frame is not modified


def test_complete_rows_are_returned_unchanged():
    tr = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
    te = pd.DataFrame({"a": [5.0], "b": [6.0]})
    out, filled = RB.fill_unseen_missing(tr, te, ["a", "b"])
    assert out is te and filled == [[]]


def test_only_inputs_of_the_selected_feature_set_count():
    tag = "RSS|FULL|prune=False|leaves=3,minchild=10,lambda=20.0,trees=400|cal=raw"
    assert RB.used_by(tag, [["income_growth", "income_rel"], ["cpi_food_yoy", "income_rel"]]) == [[], ["cpi_food_yoy"]]


def test_validation_and_serving_fill_the_same_way():
    for src in (inspect.getsource(lgbm_only.task), inspect.getsource(serve._forecast)):
        assert "RB.fill_unseen_missing(tr, te)" in src
        assert src.index("RB.fill_unseen_missing(tr, te)") < src.index("run_proc(tr, te, AN")


def test_dashboard_warns_only_for_flagged_rows(monkeypatch):
    from app.ml.inference import e168_system as E
    base = {"probability": "0.6", "lead": "1", "issue_date": "2026-11-01", "score_pct": "51.0", "range90_low": "37.0",
            "range90_high": "65.0"}
    rows = {("PH040300000", "2027-Q1"): {**base, "inputs_filled": "2", "inputs_filled_names": "cpi_food_yoy;remit_yoy"},
            ("PH040400000", "2027-Q1"): dict(base),                                     # a pre-E183 row: no flag
            ("PH040500000", "2027-Q1"): {**base, "inputs_filled": "0", "inputs_filled_names": ""}}
    monkeypatch.setattr(E, "rows", lambda: rows)
    s = E.province_row("PH040300000", "Quezon", "2027-Q1", None)["confidence_statement"]
    assert "Data incomplete: 2 model input(s)" in s and "cpi_food_yoy, remit_yoy" in s
    for code in ("PH040400000", "PH040500000"):
        assert "Data incomplete" not in E.province_row(code, "X", "2027-Q1", None)["confidence_statement"]
