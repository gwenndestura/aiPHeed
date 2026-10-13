"""
Window rule W (approved period 2021-2026) and the label-blind 2026 rows of
scripts/supplementary/window2021_study.py.
"""

import hashlib

import numpy as np
import pandas as pd
import pytest

import scripts.supplementary.window2021_study as W


@pytest.fixture(scope="module")
def frame():
    return W.window_frame(extend=True)


def test_preregistration_unchanged():
    assert hashlib.sha256(W.PREREG.read_bytes()).hexdigest() == W.PREREG_SHA


def test_no_value_with_reference_period_before_2021(frame):
    f, inputs, gov, _ = frame
    first = f[f["quarter"] == "2021-Q1"]
    # government series at 2021-Q1 would be 2020-Q4 values under strict timing
    assert first[gov].isna().all().all()
    assert f[f["quarter"] < "2021-Q1"][inputs].isna().all().all()


def test_sws_feature_uses_only_2021_rounds_released_before_target(frame):
    f, _, _, _ = frame
    rel = W.T.sws_release_dates()
    for q in f["quarter"].unique():
        v, _, age, last = W.sws_known(q)
        if last is not None:
            assert W.qi(last) >= W.qi("2021-Q1")
            assert rel[last] < W.T.qstart(W.T.nxt(q))
            assert age == W.qi(W.T.nxt(q)) - W.qi(last)


def test_2018_poverty_vintage_removed(frame):
    f, _, _, _ = frame
    assert f[f["quarter"] <= "2022-Q3"]["poverty_incidence"].isna().all()
    assert f[f["quarter"] >= "2022-Q4"]["poverty_incidence"].notna().all()


def test_labels_restricted_and_thresholded():
    lab = W.window_labels(W.THR_PRIMARY)
    assert lab["quarter"].min() >= "2021-Q1" and len(lab) == 80
    assert abs(lab["stress_score"].median() - W.THR_PRIMARY) < 1e-9
    assert ((lab["stress_score"] > W.THR_PRIMARY).astype(int) == lab["label_stress"]).all()


def test_2026_rows_carry_no_invented_government_values(frame):
    f, _, gov, _ = frame
    q1 = f[f["quarter"] == "2026-Q1"].set_index("province_code")
    q4 = f[f["quarter"] == "2025-Q4"]
    # after the strict-timing shift, 2026-Q1 government inputs are the observed 2025-Q4 values
    raw, _ = W.window_features(extend=True)
    raw4 = raw[raw["quarter"] == "2025-Q4"].set_index("province_code")
    for c in ("food_cpi_yoy", "rice_price_regular", "cpi_rel"):
        assert np.allclose(q1[c].values, raw4.loc[q1.index, c].values, equal_nan=True)
    assert len(q4) == 5


def test_rule_uses_threshold():
    X = pd.DataFrame({"sws_hunger": [14.0, 14.5], "cpi_rel": [0.0, 0.0]})
    p = W.RuleT(14.345).fit(X, np.array([0, 1])).predict_proba(X)[:, 1]
    assert p[0] < 0.5 < p[1]
