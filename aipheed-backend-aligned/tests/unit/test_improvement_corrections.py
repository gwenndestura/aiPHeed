"""
Data corrections K1-K4 and the strict-timing alignment of the improvement
study's corrected frame (scripts/supplementary/improvement_study.py).
"""

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import scripts.supplementary.improvement_study as I

KEY = ["province_code", "quarter"]


@pytest.fixture(scope="module")
def corrected():
    return I.corrected_features()


@pytest.fixture(scope="module")
def frame():
    return I.corrected_frame()


def test_preregistration_unchanged():
    assert hashlib.sha256(I.PREREG.read_bytes()).hexdigest() == I.PREREG_SHA


def test_k1_source_gaps_are_missing_not_zero(corrected):
    f, _ = corrected
    oil = pd.read_parquet("data/processed/oil_prices.parquet")[KEY]
    absent = f[KEY].merge(oil.assign(present=1), on=KEY, how="left")["present"].isna().values
    assert absent.sum() == 20
    assert f.loc[absent, "diesel_php_per_l"].isna().all()
    assert f.loc[~absent, "diesel_php_per_l"].notna().all()


def test_k2_rainfall_matches_measured_source(corrected):
    f, _ = corrected
    rain = pd.read_parquet("data/processed/province_rainfall.parquet")[KEY + ["rainfall_anomaly_pct"]]
    m = f[KEY + ["rainfall_anomaly_pct"]].merge(rain, on=KEY, suffixes=("", "_src"))
    assert len(m) == 120 and np.allclose(m["rainfall_anomaly_pct"], m["rainfall_anomaly_pct_src"])


def test_k3_fssi_only_where_articles_exist(corrected):
    f, _ = corrected
    assert f["FSSI"].notna().sum() == 33
    assert (f.loc[f["FSSI"].isna(), "fssi_article_count"] == 0).all()


def test_k4_commodity_dropped(corrected):
    f, _ = corrected
    assert not [c for c in f.columns if c.startswith("commodity_")]


def test_strict_timing_shift_has_no_zero_fill(frame):
    f, _, _, _, gov = frame
    first = f.sort_values("t").groupby("province_code").head(1)
    assert first[gov].isna().all().all()


def test_cpi_rel_is_previous_quarter_cross_section(frame):
    f, _, _, _, _ = frame
    psa = pd.read_parquet("data/processed/psa_indicators.parquet")
    psa["rel"] = psa["food_cpi_yoy"] - psa.groupby("quarter")["food_cpi_yoy"].transform("mean")
    psa["t"] = psa["quarter"].map(I.R.qi) + 1          # value of t-1 appears at t
    m = f[["province_code", "t", "cpi_rel"]].merge(psa[["province_code", "t", "rel"]], on=["province_code", "t"])
    assert np.allclose(m["cpi_rel"], m["rel"])


def test_sws_feature_never_uses_the_target_round(frame):
    f, labels, _, _, _ = frame
    rel = I.T.sws_release_dates()
    for q, v in f.groupby("quarter")["sws_hunger"].first().items():
        nxt = I.T.nxt(q)
        if nxt in rel:
            assert rel[nxt] >= I.T.qstart(nxt) or np.isnan(v)


def test_struct_rule_applies_eq3_threshold():
    X = pd.DataFrame({"sws_hunger": [14.0, 15.0, np.nan], "cpi_rel": [0.0, 0.0, 1.0]})
    p = I.StructRule().fit(X, np.array([0, 1, 1])).predict_proba(X)[:, 1]
    assert p[0] < 0.5 < p[1] and abs(p[2] - 2 / 3) < 1e-12
