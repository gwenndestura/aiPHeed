"""
Safety tests for experiments/2026-10-11_devprotocol/runner/run_e3_compact_lgbm.py.

The only fitting here is on SYNTHETIC data, to verify LightGBM's monotone-constraint
syntax and column alignment. No experiment model is trained or scored.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PATH = Path("experiments/2026-10-11_devprotocol/runner/run_e3_compact_lgbm.py")


def _load():
    spec = importlib.util.spec_from_file_location("run_e3_compact_lgbm", PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


E3 = _load()


@pytest.fixture(scope="module")
def frame():
    return E3.D.development_frame()


@pytest.fixture(scope="module")
def vault():
    return E3.E1.LabelVault.from_project()


# ---- fixed configuration
def test_inputs_and_constraints_are_the_preregistered_ones():
    assert E3.INPUTS == ["last_published_stress", "sws_hunger", "sws_change", "cpi_rel", "food_cpi_yoy",
                         "rice_price_regular_accel", "unemployment_rate"]
    assert dict(zip(E3.INPUTS, E3.MONOTONE)) == {"last_published_stress": 1, "sws_hunger": 1, "sws_change": 0,
                                                 "cpi_rel": 0, "food_cpi_yoy": 0,
                                                 "rice_price_regular_accel": 0, "unemployment_rate": 0}
    assert E3.VARIANTS["+FSSI"] == (E3.INPUTS + ["FSSI"], E3.MONOTONE + [0])
    assert E3.LGBM_PARAMS == {"objective": "binary", "num_leaves": 4, "min_child_samples": 5,
                              "n_estimators": 100, "learning_rate": 0.05, "random_state": 42, "verbosity": -1}
    assert E3.TEST_QUARTERS == ["2023-Q4", "2024-Q1", "2024-Q2", "2024-Q3", "2024-Q4", "2025-Q1", "2025-Q4"]


def test_monotone_constraint_is_enforced_with_this_column_order():
    rng = np.random.default_rng(0)
    n = 200
    X = pd.DataFrame(rng.normal(size=(n, 7)), columns=E3.INPUTS)
    # synthetic labels that DECREASE with last_published_stress: the +1 constraint must override this
    y = (X["last_published_stress"] < 0).astype(int).values
    m = E3.fit_lgbm(X, y, E3.MONOTONE)
    grid = pd.DataFrame(np.zeros((50, 7)), columns=E3.INPUTS)
    grid["last_published_stress"] = np.linspace(-3, 3, 50)
    p = m.predict_proba(grid)[:, 1]
    assert np.all(np.diff(p) >= -1e-12)


def test_misaligned_feature_order_is_refused():
    X = pd.DataFrame(np.zeros((20, 7)), columns=list(reversed(E3.INPUTS)))
    with pytest.raises(RuntimeError):
        E3.fit_lgbm(X, np.r_[np.zeros(10), np.ones(10)], E3.MONOTONE)


# ---- origin validity of the constructed input
def test_last_published_stress_uses_only_labels_published_before_each_row_origin(frame, vault):
    frame, _ = frame
    fold = E3.E1.fold_plan(["2024-Q2"])[0]
    tr = E3.add_last_published_stress(E3.E1.training_matrix(frame, vault, fold), vault, fold.target)
    te = E3.add_last_published_stress(E3.E1.test_matrix(frame, fold.target), vault, fold.target)
    for q, a in zip(tr["target_quarter"], tr["anchor_quarter"]):
        if isinstance(a, str):
            assert a < q and E3.D.label_published(a)[0] < E3.E1.T.qstart(q)
    assert (te["anchor_quarter"] == max(fold.train_quarters)).all()
    assert te["last_published_stress"].notna().all()


def test_inputs_do_not_change_when_target_and_later_labels_change(frame, vault):
    frame, _ = frame
    fold = E3.E1.fold_plan(["2024-Q4"])[0]
    lab = vault._lab.copy()
    lab.loc[lab["quarter"] >= "2024-Q4", "stress_score"] += 500.0
    v2 = E3.E1.LabelVault(lab)
    a = E3.add_last_published_stress(E3.E1.test_matrix(frame, fold.target), vault, fold.target)
    b = E3.add_last_published_stress(E3.E1.test_matrix(frame, fold.target), v2, fold.target)
    pd.testing.assert_series_equal(a["last_published_stress"], b["last_published_stress"])


def test_all_seven_inputs_available_in_every_test_row(frame, vault):
    f, usable = frame
    assert all(c in usable for c in E3.INPUTS[1:] + ["FSSI"])
    avail = E3.input_availability(f, vault)
    for q, a in avail.items():
        assert all(a["test_nan"][c] == 0 for c in E3.INPUTS), q


# ---- label safety
def test_predict_fold_is_label_free_and_reveals_nothing(frame, vault):
    f, _ = frame

    class Const:
        def predict_proba(self, X):
            return np.c_[np.full(len(X), 0.4), np.full(len(X), 0.6)]

    fold = E3.E1.fold_plan(["2024-Q1"])[0]
    p = E3.predict_fold(f, vault, fold, "A-origin", E3.INPUTS, E3.MONOTONE,
                        fitter=lambda X, y, mono: Const(), check_determinism=False)
    assert not {"y", "stress_score", "label_stress"} & set(p.columns)
    assert set(p["model"]) == {"E3-LightGBM", "Eq3-rule", "carry-forward",
                               "always-HIGH (reference)", "always-LOW (reference)"}
    assert p.loc[p["model"].str.startswith("always"), "score"].isna().all()   # no manufactured scores
    assert vault.revealed == []


def test_balanced_accuracy_undefined_with_one_class():
    assert np.isnan(E3.balanced_accuracy([1, 1, 1], [1, 0, 1]))
    assert E3.balanced_accuracy([0, 1, 1, 0], [0, 1, 0, 0]) == pytest.approx(0.75)


def test_decision_rule():
    def block(e3, cf, eq, acc_e3=0.8, acc_cf=0.8):
        return {"E3-LightGBM": {"balanced_accuracy": e3, "mean_quarter_accuracy": acc_e3},
                "carry-forward": {"balanced_accuracy": cf, "mean_quarter_accuracy": acc_cf},
                "Eq3-rule": {"balanced_accuracy": eq}}
    ok = {"carry-forward": {"ci95": [0.02, 0.4]}, "Eq3-rule": {"ci95": [0.02, 0.4]}}
    wide = {"carry-forward": {"ci95": [-0.1, 0.4]}, "Eq3-rule": {"ci95": [-0.1, 0.4]}}
    assert E3.decision(block(0.9, 0.7, 0.75), ok)["verdict"] == "improvement"
    assert E3.decision(block(0.9, 0.7, 0.75), wide)["verdict"] == "non-inferiority"
    assert E3.decision(block(0.9, 0.7, 0.75, acc_e3=0.7), ok)["verdict"] == "non-inferiority"
    assert E3.decision(block(0.6, 0.7, 0.75), ok)["verdict"] == "no demonstrated improvement"
    assert E3.decision(block(0.72, 0.7, 0.75), ok)["verdict"] == "non-inferiority"


# ---- isolation and protection
def test_protected_set_covers_prior_runs():
    keys = E3.E1.snapshot_hashes(E3.PROTECTED_GLOBS)
    for d in ("runs/20261011T111651Z/", "runs/20261011T113409Z_E2/", "diagnosis_20261011T111651Z/"):
        assert any(k.startswith("experiments/2026-10-11_devprotocol/" + d) for k in keys), d
    assert "experiments/2026-10-11_devprotocol/E3_PROTOCOL.md" in keys


def test_runner_never_loads_production_modules():
    code = ("import sys, importlib.util;"
            f"s=importlib.util.spec_from_file_location('e3', r'{PATH}');"
            "m=importlib.util.module_from_spec(s); sys.modules['e3']=m; s.loader.exec_module(m);"
            "m.E1.assert_no_forbidden_modules(); print('ok')")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env={**os.environ, "PYTHONPATH": "."})
    assert out.returncode == 0 and out.stdout.strip().endswith("ok"), out.stderr[-400:]


def test_execute_requires_authorization():
    with pytest.raises(SystemExit):
        E3.main(["--execute"])
