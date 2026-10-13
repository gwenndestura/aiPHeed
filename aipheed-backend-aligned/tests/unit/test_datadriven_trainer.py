"""
Tests for app/ml/training/datadriven_trainer.py (E7): training-only group selection, feature filtering,
monotone constraints, contributions, timing. Fits use synthetic data or the training-only path.
"""
import numpy as np
import pandas as pd
import pytest

from app.ml.features import risk_score_v2 as R
from app.ml.training import datadriven_trainer as DD
from app.ml.training import revised_trainer as RT


@pytest.fixture(scope="module")
def frame():
    import scripts.supplementary.devprotocol_rule_l as D
    return D.development_frame()[0]


@pytest.fixture(scope="module")
def labels():
    return RT.TrainingLabels(RT.load_stress())


@pytest.fixture(scope="module")
def tau(labels):
    return labels.reference(RT.RETROSPECTIVE_AS_OF)[0]


def test_candidates_always_include_regional_core():
    assert len(DD.CANDIDATES) == 8 and all(c[0] == "R" for c in DD.CANDIDATES)
    assert ("R",) in DD.CANDIDATES and ("R", "GP", "GN", "N") in DD.CANDIDATES


def test_groups_do_not_overlap():
    cols = [c for v in DD.GROUPS.values() for c in v]
    assert len(cols) == len(set(cols))


def test_training_only_filter_drops_sparse_and_constant_columns():
    tr = pd.DataFrame({"a": [1.0, 2.0, np.nan, 4.0], "b": [np.nan, np.nan, np.nan, 1.0], "c": [5.0] * 4})
    assert DD.usable_columns(tr, ["a", "b", "c"]) == ["a"]


def test_monotone_only_on_regional_level_and_last_stress():
    rng = np.random.default_rng(1)
    X = pd.DataFrame(rng.normal(size=(80, 3)), columns=["last_published_stress", "cpi_rel", "FSSI"])
    m = DD.fit(X, (X["cpi_rel"] > 0).astype(int).values)
    assert m.get_params()["monotone_constraints"] == [1, 0, 0]
    assert m.get_params().get("class_weight") is None
    from lightgbm import LGBMClassifier
    assert isinstance(m, LGBMClassifier)


def test_contributions_reconstruct_the_raw_score():
    rng = np.random.default_rng(2)
    X = pd.DataFrame(rng.normal(size=(80, 2)), columns=["sws_hunger", "cpi_rel"])
    m = DD.fit(X, (X.sum(axis=1) > 0).astype(int).values)
    gc = DD.group_contributions(m, X)
    full = m.booster_.predict(X, pred_contrib=True)
    assert np.allclose(gc.sum(axis=1).values + full[:, -1], m.booster_.predict(X, raw_score=True))
    assert set(gc.columns) == set(DD.GROUPS) and (gc["N"] == 0).all()


def test_early_fold_falls_back_to_regional_core(frame, labels, tau):
    f = DD.forecast_quarter(frame, labels, "2023-Q4", tau)
    assert f.calibration["selected"] == ["R"] and "fallback" in f.calibration["reason"]


def test_selection_and_forecast_ignore_target_and_later_labels(frame, labels, tau):
    a = DD.forecast_quarter(frame, labels, "2025-Q1", tau)
    s = RT.load_stress()
    s.loc[s["quarter"] >= "2024-Q4", "stress"] += 500.0       # not published before the 2025-Q1 origin
    b = DD.forecast_quarter(frame, RT.TrainingLabels(s), "2025-Q1", tau)
    assert a.calibration["selected"] == b.calibration["selected"]
    pd.testing.assert_series_equal(a.rows["probability"], b.rows["probability"])


def test_selection_uses_only_training_quarters(frame, labels, tau):
    import scripts.supplementary.devprotocol_rule_l as D
    f = DD.forecast_quarter(frame, labels, "2025-Q4", tau)
    train_q = D.eligible_training_quarters("2025-Q4", "development")
    assert set(f.calibration["inner_quarters"]) <= set(train_q) and "2025-Q4" not in train_q


def test_classification_and_insufficient_rules_are_shared(frame, labels, tau):
    rows = DD.forecast_quarter(frame, labels, "2024-Q2", tau).rows
    assert all(R.final_classification(p) == c for p, c in zip(rows["probability"], rows["classification"]))
    early = DD.forecast_quarter(frame, labels, "2022-Q4", tau).rows
    assert (early["classification"] == R.INSUFFICIENT_DATA).all() and early["probability"].isna().all()


def test_regression_path_is_label_free(frame, labels):
    a = DD.regress_quarter(frame, labels, "2024-Q3", ("R", "GP"))
    s = RT.load_stress()
    s.loc[s["quarter"] >= "2024-Q2", "stress"] -= 300.0
    b = DD.regress_quarter(frame, RT.TrainingLabels(s), "2024-Q3", ("R", "GP"))
    assert np.allclose(a["pred_stress"], b["pred_stress"])
