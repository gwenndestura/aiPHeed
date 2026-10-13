"""
Safety tests for experiments/2026-10-11_devprotocol/runner/run_exploratory.py.

None of these tests fits or scores a real model: the one orchestration test uses a
constant stub fitter and synthetic labels.
"""
import importlib.util
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

RUNNER_PATH = Path("experiments/2026-10-11_devprotocol/runner/run_exploratory.py")


def _load():
    spec = importlib.util.spec_from_file_location("run_exploratory", RUNNER_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod            # dataclasses need the module registered
    spec.loader.exec_module(mod)
    return mod


X = _load()


@pytest.fixture(scope="module")
def frame():
    f, usable = X.D.development_frame()
    return f, usable


@pytest.fixture(scope="module")
def vault():
    return X.LabelVault.from_project()


# ---- isolation from production
def test_runner_never_loads_production_modules():
    code = ("import sys, importlib.util;"
            f"s=importlib.util.spec_from_file_location('r', r'{RUNNER_PATH}');"
            "m=importlib.util.module_from_spec(s); sys.modules['r']=m; s.loader.exec_module(m);"
            "m.assert_no_forbidden_modules();"
            "print(sorted(x for x in sys.modules if x.startswith(m.FORBIDDEN_MODULE_PREFIXES)))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env={**__import__("os").environ, "PYTHONPATH": "."})
    assert out.returncode == 0, out.stderr[-500:]
    assert out.stdout.strip().splitlines()[-1] == "[]"


def test_runner_source_has_no_production_entry_points():
    src = RUNNER_PATH.read_text(encoding="utf-8")
    start = src.index("FORBIDDEN_MODULE_PREFIXES = (")
    code = src[:start] + src[src.index(")", start):]          # drop the deny-list itself
    code = code.split('"""', 2)[2]                             # drop the module docstring
    for s in ("app.tasks", "run_quarterly_pipeline", "pipeline/run", "uvicorn", "promote(",
              "joblib.dump", "pickle.dump", "to_parquet", "lgbm_best", "SCHEDULER"):
        assert s not in code, s


# ---- outputs
def test_run_folder_must_be_new_and_writes_stay_inside(tmp_path):
    r = X.RunDir(tmp_path / "run1")
    r.write_text("a.txt", "x")
    with pytest.raises(FileExistsError):
        r.write_text("a.txt", "y")
    with pytest.raises(PermissionError):
        r.write_text("../escape.txt", "x")
    with pytest.raises(FileExistsError):
        X.RunDir(tmp_path / "run1")


def test_hash_guard_detects_a_change(tmp_path):
    p = tmp_path / "data" / "f.csv"
    p.parent.mkdir()
    p.write_text("1")
    before = X.snapshot_hashes(("data/*",), root=tmp_path)
    p.write_text("2")
    with pytest.raises(RuntimeError):
        X.assert_unchanged(before, X.snapshot_hashes(("data/*",), root=tmp_path))


def test_protected_set_covers_labels_models_frozen_forecasts_and_reports():
    keys = X.snapshot_hashes()
    assert "data/processed/labels.parquet" in keys
    assert "models/lgbm_best.pkl" in keys
    assert "experiments/2026-10-09_window2021/FROZEN_2026_FORECASTS.csv" in keys
    assert "experiments/2026-10-11_devprotocol/PREREGISTRATION_DRAFT_v3.md" in keys
    assert not any(k.startswith("experiments/2026-10-11_devprotocol/runs") for k in keys)


# ---- labels and thresholds
def test_no_2026_label_can_enter(vault):
    assert max(vault.quarters()) == "2025-Q4"
    bad = pd.DataFrame({"quarter": ["2026-Q3"], "province_code": ["P"], "stress_score": [1.0]})
    with pytest.raises(RuntimeError):
        X.LabelVault(bad)


def test_training_access_is_limited_to_earlier_quarters(vault):
    with pytest.raises(PermissionError):
        vault.training(["2024-Q1", "2024-Q2"], "2024-Q2")


def test_test_labels_cannot_be_revealed_before_predictions_are_written(vault):
    with pytest.raises(PermissionError):
        vault.reveal("never-written", "2024-Q1")


def test_origin_threshold_ignores_test_and_later_quarters(frame, vault):
    f, _ = frame
    fold = X.fold_plan(["2024-Q1"])[0]
    tr = X.training_matrix(f, vault, fold)
    tau = X.fold_threshold("A-origin", tr, vault)
    assert set(tr["target_quarter"]) == set(fold.train_quarters)
    assert all(q < "2024-Q1" for q in tr["target_quarter"])
    # perturbing every row at or after the target must not move tau_T
    lab = vault._lab.copy()
    lab.loc[lab["quarter"] >= "2024-Q1", "stress_score"] += 1000.0
    v2 = X.LabelVault(lab)
    assert X.fold_threshold("A-origin", X.training_matrix(f, v2, fold), v2) == tau


def test_global_threshold_is_the_approved_value(vault):
    assert abs(vault.global_threshold() - X.THR_GLOBAL_EXPECTED) < 1e-3


# ---- folds and the minimum window
def test_primary_folds_meet_the_minimum_window():
    folds = X.fold_plan(X.TEST_PRIMARY)
    assert [f.target for f in folds] == X.TEST_PRIMARY
    assert [len(f.train_quarters) for f in folds] == [8, 9, 10, 11, 12, 13, 15]
    for f in folds:
        assert all(q < f.target for q in f.train_quarters)


def test_short_fold_is_refused_unless_sensitivity_s5():
    with pytest.raises(ValueError):
        X.fold_plan(["2023-Q3"])
    assert len(X.fold_plan(["2023-Q3"], allow_short=True)[0].train_quarters) == 7


def test_unlabelled_or_protected_quarters_cannot_be_targets():
    for q in ("2026-Q1", "2026-Q3"):
        with pytest.raises(ValueError):
            X.fold_plan([q])


def test_s6_subset_is_the_literal_consecutive_reading():
    assert set(X.S6_SUBSET) < set(X.TEST_PRIMARY) and min(X.S6_SUBSET) == "2024-Q3"


# ---- features
def test_fixed_feature_sets(frame):
    _, usable = frame
    fs = X.feature_sets(usable)
    assert len(fs["base"]["MODEL-B2"]) == 44 and len(fs["base"]["MODEL-A"]) == 12
    assert len(fs["S2"]["MODEL-B2"]) == 18 and len(fs["S2"]["MODEL-A"]) == 9
    for c in ("enso_numeric", "drought_alert", "tc_count", "rainfall_anomaly_pct"):
        assert c in fs["base"]["MODEL-B2"] and c not in fs["S1"]["MODEL-B2"]
    for s in fs.values():
        for cols in s.values():
            assert "rice_retail_regular" not in cols and "rice_retail_well" not in cols
            assert not X.LABEL_COLUMNS & set(cols)


def test_test_matrix_has_no_label_columns(frame):
    f, _ = frame
    te = X.test_matrix(f, "2025-Q4")
    assert not X.LABEL_COLUMNS & set(te.columns) and len(te) == 5


def test_s4_removes_supplementary_sws_inputs(frame):
    f, _ = frame
    s4 = X.s4_frame(f)
    assert (s4["sws_source"].dropna() == "production").all()
    base_q4 = f.loc[f["target_quarter"] == "2025-Q4", "sws_source"].iloc[0]
    assert base_q4 == "supplementary"
    assert (s4["sws_published"].dropna() < s4.loc[s4["sws_published"].notna(), "origin"]).all()


# ---- orchestration (stub fitter, synthetic labels; no real training)
class _Const:
    def __init__(self, v):
        self.v = v

    def predict_proba(self, X):
        return np.c_[np.full(len(X), 1 - self.v), np.full(len(X), self.v)]


def test_predict_fold_is_label_free_and_uses_fold_threshold(frame, tmp_path):
    f, usable = frame
    fold = X.fold_plan(["2024-Q1"])[0]
    rows = f[f["target_quarter"].isin(fold.train_quarters + ["2024-Q1"])][["target_quarter", "province_code"]]
    rng = np.random.default_rng(0)
    synth = rows.rename(columns={"target_quarter": "quarter"}).assign(stress_score=rng.normal(12, 3, len(rows)))
    v = X.LabelVault(synth)
    preds, tau = X.predict_fold(f, v, fold, "A-origin", X.feature_sets(usable)["base"],
                                fitter=lambda Xm, y, class_weighted: _Const(0.7), check_determinism=False)
    assert not X.LABEL_COLUMNS & set(preds.columns)
    expected = synth[synth["quarter"].isin(fold.train_quarters)]["stress_score"].median()
    assert tau == pytest.approx(expected)
    assert set(preds["model"]) == {"MODEL-B2", "MODEL-A", "Eq3-rule", "carry-forward",
                                   "always-HIGH (reference)", "always-LOW (reference)"}
    assert v.revealed == []
    run = X.RunDir(tmp_path / "r")
    p = run.write_csv("pred.csv", preds)
    v.register_predictions("k", p)
    assert len(v.reveal("k", "2024-Q1")) == 5


# ---- authorization gate
def test_execute_requires_authorization():
    with pytest.raises(SystemExit):
        X.main(["--execute"])


def test_runner_refuses_a_process_that_loaded_the_production_app():
    # tests/conftest.py imports app.main, so this pytest process is "contaminated":
    # the runner must refuse even a dry run here.
    assert "app.main" in sys.modules
    with pytest.raises(RuntimeError):
        X.main([])
