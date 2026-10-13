"""
Regression tests for the revised scoring and probability pipeline:
  app/ml/features/risk_score_v2.py  (score, decomposition, price evidence, final classification)
  app/ml/training/revised_trainer.py (time-valid LightGBM forecaster)
The fitting below uses either synthetic data or the forecaster's own training-only path;
no outer-test label is read by any test that exercises the forecaster.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from app.ml.features import risk_score_v2 as R
from app.ml.training import revised_trainer as RT

P = list(R.PROVINCES)


# ---- fixed 0.50 classification rule and INSUFFICIENT_DATA
def test_probability_equal_to_threshold_is_high():
    assert R.final_classification(0.50) == R.HIGH


def test_probability_above_threshold_is_high():
    assert R.final_classification(0.5000001) == R.HIGH and R.final_classification(1.0) == R.HIGH


def test_probability_below_threshold_is_low():
    assert R.final_classification(0.4999999) == R.LOW and R.final_classification(0.0) == R.LOW


def test_missing_or_stale_inputs_give_insufficient_data_never_high_or_low():
    assert R.final_classification(0.9, ["missing input: sws_hunger"]) == R.INSUFFICIENT_DATA
    assert R.final_classification(0.1, ["stale regional hunger input"]) == R.INSUFFICIENT_DATA
    assert R.final_classification(None) == R.INSUFFICIENT_DATA
    assert R.final_classification(float("nan")) == R.INSUFFICIENT_DATA
    with pytest.raises(ValueError):
        R.final_classification(1.5)


def test_insufficiency_rules():
    ok = pd.Series({"last_published_stress": 12.0, "sws_hunger": 15.0, "cpi_rel": -0.4,
                    "food_cpi_yoy": 3.1, "sws_age": 2})
    assert RT.insufficiency(ok) == []
    assert RT.insufficiency(ok.drop("cpi_rel")) == ["missing input: cpi_rel"]
    assert RT.insufficiency(ok.replace({12.0: np.nan})) == ["missing input: last_published_stress"]
    stale = ok.copy(); stale["sws_age"] = R.SWS_MAX_AGE_QUARTERS + 1
    assert RT.insufficiency(stale)[0].startswith("stale regional hunger input")
    edge = ok.copy(); edge["sws_age"] = R.SWS_MAX_AGE_QUARTERS
    assert RT.insufficiency(edge) == []


# ---- formula: negative and positive values, no zero-fill, decomposition
def test_formula_handles_negative_and_positive_deviations():
    sws = pd.DataFrame({"quarter": ["2024-Q2"], "sws_hunger_pct": [19.6]})
    cpi = pd.DataFrame({"province_code": P, "quarter": "2024-Q2", "food_cpi_yoy": [-1.0, 0.0, 2.0, 5.0, -6.0]})
    out = R.decompose_stress(R.compute_stress(sws, cpi))        # mean = 0
    assert np.allclose(out["stress"], [17.6, 19.6, 23.6, 29.6, 7.6])
    assert out["provincial_component"].sum() == pytest.approx(0.0)
    assert (out["regional_component"] == 19.6).all()               # one shared regional value


def test_missing_values_are_not_converted_to_zero():
    sws = pd.DataFrame({"quarter": ["2024-Q2"], "sws_hunger_pct": [19.6]})
    cpi = pd.DataFrame({"province_code": P, "quarter": "2024-Q2", "food_cpi_yoy": [1.0, np.nan, 2.0, 3.0, 4.0]})
    out = R.compute_stress(sws, cpi)
    assert out["stress"].isna().all()                              # zero-fill would have produced numbers
    ind = pd.DataFrame({"province_code": P * 2, "quarter": ["2024-Q1"] * 5 + ["2024-Q2"] * 5,
                        "food_cpi": [120.0] * 10, "food_cpi_yoy": [1, 2, 3, 4, 5, 2, np.nan, 3, 4, 5]})
    pi = R.price_pressure_indicators(ind)
    q2 = pi[pi["quarter"] == "2024-Q2"]
    assert q2["relative_pressure"].isna().all() and q2.loc[q2["province_code"] == P[1], "inflation_rate"].isna().all()


def test_price_indicators_distinguish_level_rate_change_and_relative():
    ind = pd.DataFrame({"province_code": P * 2, "quarter": ["2024-Q1"] * 5 + ["2024-Q2"] * 5,
                        "food_cpi": [130.0] * 5 + [131.0] * 5,
                        "food_cpi_yoy": [6, 6, 6, 6, 6, 2, 3, 4, 5, 6]})
    pi = R.price_pressure_indicators(ind).set_index(["quarter", "province_code"])
    row = pi.loc[("2024-Q2", P[0])]
    assert row["price_index_level"] == 131.0                       # high level ...
    assert row["inflation_rate"] == 2 and row["inflation_change"] == -4   # ... but slowing inflation
    assert row["relative_pressure"] == pytest.approx(-2.0)


# ---- forecaster: LightGBM, consistency, timing, calibration
@pytest.fixture(scope="module")
def frame():
    import scripts.supplementary.devprotocol_rule_l as D
    return D.development_frame()[0]


@pytest.fixture(scope="module")
def labels():
    return RT.TrainingLabels(RT.load_stress())


def test_primary_model_is_lightgbm_with_fixed_unweighted_configuration():
    from lightgbm import LGBMClassifier
    rng = np.random.default_rng(0)
    X = pd.DataFrame(rng.normal(size=(60, 7)), columns=RT.INPUTS)
    m = RT.fit(X, (X["sws_hunger"] > 0).astype(int).values)
    assert isinstance(m, LGBMClassifier)
    params = m.get_params()
    assert params.get("class_weight") is None and params.get("scale_pos_weight", 1.0) == 1.0
    assert params["num_leaves"] == 4 and params["min_child_samples"] == 5 and params["monotone_constraints"] == RT.MONOTONE


def test_reference_threshold_is_point_in_time(labels):
    t0, q0 = labels.reference(RT.RETROSPECTIVE_AS_OF)
    tp, qp = labels.reference(RT.PROSPECTIVE_AS_OF)
    assert t0 == pytest.approx(10.8434, abs=1e-3) and len(q0) == 8
    assert tp == pytest.approx(14.345, abs=1e-3) and len(qp) == 16


def test_label_access_is_restricted_to_published_earlier_quarters(labels):
    with pytest.raises(PermissionError):
        labels.for_target(["2024-Q1"], "2024-Q1")
    with pytest.raises(PermissionError):
        labels.for_target(["2023-Q4"], "2024-Q1")                 # 2023-Q4 label published after 2024-01-01


def test_no_future_information_changes_a_historical_forecast(frame, labels):
    tau = labels.reference(RT.RETROSPECTIVE_AS_OF)[0]
    a = RT.forecast_quarter(frame, labels, "2024-Q3", tau).rows
    s = RT.load_stress()
    s.loc[s["quarter"] >= "2024-Q2", "stress"] += 500.0          # target quarter and every later label
    b = RT.forecast_quarter(frame, RT.TrainingLabels(s), "2024-Q3", tau).rows
    pd.testing.assert_series_equal(a["probability"], b["probability"])


def test_calibration_uses_training_quarters_only(frame, labels):
    tau = labels.reference(RT.RETROSPECTIVE_AS_OF)[0]
    f = RT.forecast_quarter(frame, labels, "2025-Q4", tau)
    import scripts.supplementary.devprotocol_rule_l as D
    train_q = D.eligible_training_quarters("2025-Q4", "development")
    assert f.calibration["oof_quarters"] <= len(train_q) - RT.MIN_TRAIN_QUARTERS
    assert "2025-Q4" not in train_q


def test_training_and_inference_use_the_same_inputs(frame, labels):
    tau = labels.reference(RT.RETROSPECTIVE_AS_OF)[0]
    rows = RT.forecast_quarter(frame, labels, "2024-Q4", tau).rows
    te = RT.with_last_published_stress(frame[frame["target_quarter"] == "2024-Q4"].sort_values("province_code"),
                                       labels, "2024-Q4")
    for c in RT.INPUTS:                                              # served inputs are exactly the training-frame inputs
        assert np.allclose(rows[c].values, te[c].values, equal_nan=True), c


def test_short_history_is_insufficient_not_low(frame, labels):
    tau = labels.reference(RT.RETROSPECTIVE_AS_OF)[0]
    rows = RT.forecast_quarter(frame, labels, "2023-Q2", tau).rows
    assert (rows["classification"] == R.INSUFFICIENT_DATA).all() and rows["probability"].isna().all()


def test_shared_regional_input_is_identical_across_provinces(frame, labels):
    tau = labels.reference(RT.RETROSPECTIVE_AS_OF)[0]
    rows = RT.forecast_quarter(frame, labels, "2025-Q1", tau).rows
    assert rows["sws_hunger"].nunique() == 1 and rows["sws_round"].nunique() == 1


def test_served_artifact_matches_its_metadata():
    import hashlib, json
    art = Path("data/revised/revised_forecasts_retrospective.parquet")
    meta = json.loads(art.with_name(art.stem + "_meta.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(art.read_bytes()).hexdigest() == meta["sha256"]["artifact"]
    a = pd.read_parquet(art)
    assert a["target_quarter"].max() <= "2025-Q4"                   # no 2026 forecast
    ok = a["classification"] != R.INSUFFICIENT_DATA
    assert all(R.final_classification(p) == c for p, c in zip(a.loc[ok, "probability"], a.loc[ok, "classification"]))
    assert a.loc[~ok, "probability"].isna().all()
