"""
Safety and correctness tests for experiments/2026-10-11_devprotocol/runner/run_e4_risk_definitions.py.
No experiment model is trained: orchestration uses a constant stub.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PATH = Path("experiments/2026-10-11_devprotocol/runner/run_e4_risk_definitions.py")


def _load():
    spec = importlib.util.spec_from_file_location("run_e4_risk_definitions", PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


E4 = _load()


@pytest.fixture(scope="module")
def vault():
    return E4.E1.LabelVault.from_project()


@pytest.fixture(scope="module")
def frame():
    return E4.D.development_frame()[0]


def test_tau0_uses_only_labels_published_before_the_first_origin(vault):
    t0 = E4.tau0(vault)
    lab = vault._lab.copy()
    lab.loc[lab["quarter"] >= "2023-Q3", "stress_score"] += 1000.0     # everything not yet published at 2023-10-01
    assert E4.tau0(E4.E1.LabelVault(lab)) == t0
    assert abs(t0 - 10.8434) < 1e-3                                   # equals the first fold's training median


def test_d_d_equals_frozen_reference_and_positive_deviation(vault):
    lab = vault._lab
    t0 = E4.tau0(vault)
    y = E4.label("D-D", lab, t0, "quarter")
    e2 = importlib.util.spec_from_file_location("e2", "experiments/2026-10-11_devprotocol/runner/run_e2_relative_cpi.py")
    m = importlib.util.module_from_spec(e2); sys.modules["e2"] = m; e2.loader.exec_module(m)
    d = lab.merge(m.target_table(), on=["quarter", "province_code"], how="left")["d"].values
    expected = ((lab["stress_score"].values > t0) & (d > 1e-9)).astype(int)
    assert (y == expected).all()


def test_simple_definitions_are_plain_thresholds(vault):
    lab = vault._lab
    assert (E4.label("D-A", lab, 14.345, "quarter") == (lab["stress_score"] > 14.345).astype(int)).all()
    assert (E4.label("D-C", lab, 10.8, "quarter") == (lab["stress_score"] > 10.8).astype(int)).all()


def test_d_d_refuses_incomplete_quarters(vault):
    with pytest.raises(RuntimeError):
        E4.label("D-D", vault._lab.iloc[:3], 10.0, "quarter")


def test_thresholds_by_definition(vault, frame):
    fold = E4.E1.fold_plan(["2024-Q2"])[0]
    tr = E4.E1.training_matrix(frame, vault, fold)
    t0 = E4.tau0(vault)
    assert E4.threshold("D-A", tr, vault, t0) == pytest.approx(14.345, abs=1e-3)
    assert E4.threshold("D-B", tr, vault, t0) == pytest.approx(tr["stress_score"].median())
    assert E4.threshold("D-C", tr, vault, t0) == t0 == E4.threshold("D-D", tr, vault, t0)


def test_predict_fold_is_label_free_and_reveals_nothing(vault, frame):
    class Const:
        def predict_proba(self, X):
            return np.c_[np.full(len(X), 0.3), np.full(len(X), 0.7)]

    fold = E4.E1.fold_plan(["2024-Q1"])[0]
    for defn in E4.DEFINITIONS:
        p = E4.predict_fold(frame, vault, fold, defn, E4.tau0(vault),
                            fitter=lambda X, y, mono: Const(), check_determinism=False)
        assert not {"y", "stress_score"} & set(p.columns)
        if defn == "D-D":
            assert p.loc[p["model"].isin(["Eq3-rule", "carry-forward"]), "score"].isna().all()
    assert vault.revealed == []


def test_model_configuration_is_e3_unchanged():
    assert E4.E3.INPUTS[:2] == ["last_published_stress", "sws_hunger"] and E4.E3.MONOTONE == [1, 1, 0, 0, 0, 0, 0]
    assert E4.E3.LGBM_PARAMS["num_leaves"] == 4 and E4.E3.LGBM_PARAMS["min_child_samples"] == 5
    assert E4.TEST_QUARTERS == E4.E1.TEST_PRIMARY


def test_protected_set_covers_all_prior_runs():
    keys = E4.E1.snapshot_hashes(E4.PROTECTED_GLOBS)
    for d in ("20261011T111651Z/", "20261011T113409Z_E2/", "20261011T114801Z_E3/"):
        assert any(k.startswith("experiments/2026-10-11_devprotocol/runs/" + d) for k in keys), d
    assert "experiments/2026-10-11_devprotocol/E4_RISK_DEFINITION_PROTOCOL.md" in keys


def test_runner_never_loads_production_modules():
    code = ("import sys, importlib.util;"
            f"s=importlib.util.spec_from_file_location('e4', r'{PATH}');"
            "m=importlib.util.module_from_spec(s); sys.modules['e4']=m; s.loader.exec_module(m);"
            "m.E1.assert_no_forbidden_modules(); print('ok')")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env={**os.environ, "PYTHONPATH": "."})
    assert out.returncode == 0 and out.stdout.strip().endswith("ok"), out.stderr[-400:]


def test_execute_requires_authorization():
    with pytest.raises(SystemExit):
        E4.main(["--execute"])
