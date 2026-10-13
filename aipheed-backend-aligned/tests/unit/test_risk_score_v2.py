"""
Tests for app/ml/features/risk_score_v2.py (candidate S1; not wired into serving).
Covers score calculation, threshold boundaries, missing values, point-in-time availability,
HIGH and LOW outputs, agreement with the approved formula, and isolation from serving code.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml.features import risk_score_v2 as R

P = list(R.PROVINCES)


def _cpi(quarter, values):
    return pd.DataFrame({"province_code": P, "quarter": quarter, "food_cpi_yoy": values})


# ---- score calculation
def test_stress_matches_equation3_by_hand():
    sws = pd.DataFrame({"quarter": ["2024-Q1"], "sws_hunger_pct": [20.0]})
    out = R.compute_stress(sws, _cpi("2024-Q1", [1.0, 2.0, 3.0, 4.0, 5.0]))   # regional mean 3
    assert out["regional_mean"].eq(3.0).all()
    assert np.allclose(out["stress"], [16.0, 18.0, 20.0, 22.0, 24.0])          # 20 + 2*(x-3)
    assert out["deviation"].sum() == pytest.approx(0.0)


def test_two_sws_rounds_in_a_quarter_are_averaged():
    sws = pd.DataFrame({"quarter": ["2022-Q2", "2022-Q2"], "sws_hunger_pct": [10.0, 14.0]})
    out = R.compute_stress(sws, _cpi("2022-Q2", [3.0] * 5))
    assert np.allclose(out["stress"], 12.0)


def test_matches_label_generator_on_all_80_approved_rows():
    lab = pd.read_parquet("data/processed/labels.parquet")
    lab = lab[(lab["quarter"] >= "2021-Q1") & (lab["quarter"] <= "2025-Q4")]
    sws = lab.groupby("quarter", as_index=False)["sws_hunger_pct"].first()
    ind = pd.read_parquet("data/processed/psa_indicators.parquet")
    ind = ind[ind["quarter"].isin(lab["quarter"].unique())]
    out = R.compute_stress(sws, ind).merge(lab[["province_code", "quarter", "stress_score"]],
                                           on=["province_code", "quarter"])
    assert len(out) == 80
    assert (out["stress"] - out["stress_score"]).abs().max() < 1e-3         # formula preserved


# ---- missing values
def test_missing_province_cpi_gives_nan_for_the_quarter_not_zero():
    sws = pd.DataFrame({"quarter": ["2024-Q1"], "sws_hunger_pct": [20.0]})
    out = R.compute_stress(sws, _cpi("2024-Q1", [1.0, 2.0, np.nan, 4.0, 5.0]))
    assert out["regional_mean"].isna().all() and out["stress"].isna().all()
    assert R.classify(out["stress"], 14.0) == [None] * 5


def test_missing_sws_gives_nan():
    out = R.compute_stress(pd.DataFrame({"quarter": ["2023-Q1"], "sws_hunger_pct": [9.0]}),
                           _cpi("2025-Q2", [1, 2, 3, 4, 5]))
    assert out["stress"].isna().all()


# ---- thresholds and labels
def test_threshold_boundaries():
    assert R.classify([14.345, 14.3451, 14.3449], 14.345) == [R.LOW, R.HIGH, R.LOW]
    with pytest.raises(ValueError):
        R.classify([1.0], float("nan"))


def test_both_high_and_low_are_produced():
    labels = R.classify([9.0, 12.0, 18.0, 25.0, np.nan], 14.345)
    assert labels == [R.LOW, R.LOW, R.HIGH, R.HIGH, None]


def test_probability_classification():
    assert R.classify_probability([0.5, 0.4999, 0.9, np.nan]) == [R.HIGH, R.LOW, R.HIGH, None]
    with pytest.raises(ValueError):
        R.classify_probability([1.2])


# ---- point-in-time reference
def _toy_stress(n_quarters=10):
    rows = []
    for i in range(n_quarters):
        q = f"{2021 + i // 4}-Q{i % 4 + 1}"
        for p in P:
            rows.append({"province_code": p, "quarter": q, "stress": float(i)})
    return pd.DataFrame(rows)


def test_reference_uses_only_quarters_published_before_as_of():
    s = _toy_stress(10)
    pub = {q: pd.Timestamp(year=int(q[:4]), month=int(q[-1]) * 3, day=15) + pd.Timedelta(days=60)
           for q in s["quarter"].unique()}
    thr, used = R.reference_threshold(s, pub.get, pd.Timestamp("2023-06-01"))
    assert all(pub[q] < pd.Timestamp("2023-06-01") for q in used)
    s2 = s.copy()
    s2.loc[~s2["quarter"].isin(used), "stress"] += 1000                     # later data cannot move it
    assert R.reference_threshold(s2, pub.get, pd.Timestamp("2023-06-01"))[0] == thr


def test_unknown_publication_dates_are_excluded_and_minimum_enforced():
    s = _toy_stress(10)
    with pytest.raises(R.InsufficientReference):
        R.reference_threshold(s, lambda q: None, pd.Timestamp("2030-01-01"))
    with pytest.raises(R.InsufficientReference):
        R.reference_threshold(s, lambda q: pd.Timestamp("2020-01-01"), pd.Timestamp("2030-01-01"), min_quarters=11)


def test_reference_reproduces_tau0_and_the_approved_threshold():
    import scripts.supplementary.devprotocol_rule_l as D
    lab = pd.read_parquet("data/processed/labels.parquet")
    lab = lab[(lab["quarter"] >= "2021-Q1") & (lab["quarter"] <= "2025-Q4")]
    s = lab.rename(columns={"stress_score": "stress"})[["province_code", "quarter", "stress"]]
    pub = lambda q: D.label_published(q, "development")[0]
    t0, used0 = R.reference_threshold(s, pub, pd.Timestamp("2023-10-01"))
    assert t0 == pytest.approx(10.8434, abs=1e-3) and len(used0) == 8
    tp, used = R.reference_threshold(s, pub, pd.Timestamp("2026-07-01"))
    assert tp == pytest.approx(14.345, abs=1e-3) and len(used) == 16


# ---- isolation: the candidate is not wired into labels, training or serving
def test_not_imported_by_the_legacy_label_training_or_served_model_path():
    # 2026-10-11: S1 was unwired everywhere. 2026-10-12: wiring into the revised pipeline was authorized
    # (revised_trainer, the assessment service/API and the shared classification rule). The legacy label
    # builder, legacy trainer and legacy served predictor must still not depend on it, so the original
    # model artifact and its labels cannot change through this module.
    legacy = [Path("app/ml/features/label_generator.py"), Path("app/ml/training/trainer.py"),
              Path("app/ml/inference/predictor.py"), Path("app/ml/features/feature_matrix.py")]
    for path in legacy:
        assert "risk_score_v2" not in path.read_text(encoding="utf-8"), path
