"""
Safety tests for experiments/2026-10-11_devprotocol/runner/run_e2_relative_cpi.py.
No real model is fitted: the orchestration test uses a constant stub and synthetic targets.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PATH = Path("experiments/2026-10-11_devprotocol/runner/run_e2_relative_cpi.py")


def _load():
    spec = importlib.util.spec_from_file_location("run_e2_relative_cpi", PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


E2 = _load()


@pytest.fixture(scope="module")
def table():
    return E2.target_table()


@pytest.fixture(scope="module")
def frame():
    return E2.D.development_frame()


def test_target_is_complete_and_sums_to_zero(table):
    assert len(table) == 100 and table["quarter"].min() == "2021-Q1" and table["quarter"].max() == "2025-Q4"
    assert (table.groupby("quarter").size() == 5).all()
    assert table.groupby("quarter")["d"].sum().abs().max() < 1e-9
    assert not table["d"].isna().any()


def test_target_matches_the_equation3_provincial_component(table):
    lab = pd.read_parquet("data/processed/labels.parquet")
    m = lab.merge(table, on=["province_code", "quarter"])
    assert len(m) == 80
    assert ((m["stress_score"] - m["sws_hunger_pct"]) / 2 - m["d"]).abs().max() < 1e-4


def test_target_does_not_use_sws():
    src = PATH.read_text(encoding="utf-8")
    body = src.split("def target_table", 1)[1].split("def published", 1)[0]
    assert "sws" not in body.lower()


def test_no_2026_target_can_be_loaded():
    with pytest.raises(RuntimeError):
        E2.TargetVault(pd.DataFrame({"quarter": ["2026-Q3"], "province_code": ["P"], "d": [0.0]}))


def test_training_access_and_reveal_order(table):
    v = E2.TargetVault(table)
    with pytest.raises(PermissionError):
        v.training(["2024-Q1"], "2024-Q1")
    with pytest.raises(PermissionError):
        v.reveal("never", "2024-Q1")


def test_eligibility_respects_publication_dates(table):
    v = E2.TargetVault(table)
    for f in E2.fold_plan(v):
        o = E2.T.qstart(f.target)
        assert all(q < f.target and E2.published(q)[0] < o for q in f.train_quarters)
        assert f.eligible == (len(f.train_quarters) >= E2.MIN_TRAIN_QUARTERS)


def test_test_quarters_and_exposure_split():
    assert len(E2.TEST_QUARTERS) == 9 and set(E2.LESS_EXPOSED) == {"2025-Q2", "2025-Q3"}
    assert set(E2.REUSED) | set(E2.LESS_EXPOSED) == set(E2.TEST_QUARTERS)
    assert not any(q.startswith("2026") for q in E2.TEST_QUARTERS)


def test_feature_set_is_the_44_input_model_b2_set(frame):
    _, usable = frame
    cols = E2.feature_cols(usable)
    assert len(cols) == 44 and not E2.TARGET_COLUMNS & set(cols)


def test_predict_fold_is_target_free_and_baselines_use_training_only(frame, table):
    f, usable = frame
    v = E2.TargetVault(table)
    fold = next(x for x in E2.fold_plan(v) if x.target == "2024-Q2")
    # perturb the target quarter and later: predictions must not change
    t2 = table.copy()
    t2.loc[t2["quarter"] >= "2024-Q2", "d"] += 99.0
    v2 = E2.TargetVault(t2)

    class Const:
        def predict(self, X):
            return np.full(len(X), 0.1)

    stub = lambda X, y: Const()
    p1 = E2.predict_fold(f, v, fold, E2.feature_cols(usable), fitter=stub, check_determinism=False)
    p2 = E2.predict_fold(f, v2, fold, E2.feature_cols(usable), fitter=stub, check_determinism=False)
    assert not E2.TARGET_COLUMNS & set(p1.columns)
    pd.testing.assert_frame_equal(p1, p2)
    assert set(p1["model"]) == set(E2.MODELS) and v.revealed == []
    cf = p1[p1["model"] == "Carry-forward"]
    assert (cf["carry_forward_source_quarter"] == max(fold.train_quarters)).all()


def test_protected_set_includes_e1_artifacts():
    keys = E2.E1.snapshot_hashes(E2.PROTECTED_GLOBS)
    assert any(k.startswith("experiments/2026-10-11_devprotocol/runs/20261011T111651Z/") for k in keys)
    assert any(k.startswith("experiments/2026-10-11_devprotocol/diagnosis_20261011T111651Z/") for k in keys)
    assert "data/processed/psa_indicators.parquet" in keys


def test_runner_never_loads_production_modules():
    code = ("import sys, importlib.util;"
            f"s=importlib.util.spec_from_file_location('e2', r'{PATH}');"
            "m=importlib.util.module_from_spec(s); sys.modules['e2']=m; s.loader.exec_module(m);"
            "m.E1.assert_no_forbidden_modules(); print('ok')")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env={**os.environ, "PYTHONPATH": "."})
    assert out.returncode == 0 and out.stdout.strip().endswith("ok"), out.stderr[-400:]


def test_decision_rule_requires_all_three_conditions():
    base = {"MODEL-B2-reg": {"mean_spearman": 0.6, "mae": 1.0}, "Carry-forward": {"mean_spearman": 0.3, "mae": 1.0}}
    assert E2.decision(base, {"ci95": [0.05, 0.5]})["verdict"] == "demonstrates value"
    assert E2.decision(base, {"ci95": [-0.05, 0.5]})["verdict"].startswith("no demonstrated")
    worse = {**base, "MODEL-B2-reg": {"mean_spearman": 0.6, "mae": 1.1}}
    assert E2.decision(worse, {"ci95": [0.05, 0.5]})["verdict"].startswith("no demonstrated")
    small = {**base, "MODEL-B2-reg": {"mean_spearman": 0.45, "mae": 0.9}}
    assert E2.decision(small, {"ci95": [0.05, 0.5]})["verdict"].startswith("no demonstrated")


def test_execute_requires_authorization():
    with pytest.raises(SystemExit):
        E2.main(["--execute"])
