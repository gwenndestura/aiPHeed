"""Safety and correctness tests for experiments/2026-10-11_devprotocol/runner/run_e5_scoring.py (no real fitting)."""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PATH = Path("experiments/2026-10-11_devprotocol/runner/run_e5_scoring.py")


def _load():
    spec = importlib.util.spec_from_file_location("run_e5_scoring", PATH)
    m = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


E5 = _load()


@pytest.fixture(scope="module")
def vault():
    return E5.E1.LabelVault.from_project()


@pytest.fixture(scope="module")
def table():
    return E5.E2.target_table()


@pytest.fixture(scope="module")
def frame():
    return E5.D.development_frame()[0]


def test_s2_reference_uses_only_pre_origin_labels(vault):
    ref = E5.s2_reference(vault)
    lab = vault._lab.copy()
    lab.loc[lab["quarter"] >= "2023-Q3", "stress_score"] += 1000.0
    ref2 = E5.s2_reference(E5.E1.LabelVault(lab))
    for k in ("mu_R", "sigma_R", "sigma_d", "cutoff"):
        assert ref[k] == pytest.approx(ref2[k])
    assert ref["reference_quarters"][-1] == "2023-Q2" and len(ref["reference_quarters"]) == 8


def test_s2_score_matches_hand_calculation():
    rows = pd.DataFrame({"q": ["a"] * 5, "stress_score": [10.0, 12.0, 14.0, 16.0, 18.0]})
    p = {"mu_R": 10.0, "sigma_R": 2.0, "sigma_d": 1.0}
    # SWS = 14, d = (s - 14)/2 -> [-2,-1,0,1,2]; z = (14-10)/2 + d/1
    assert np.allclose(E5.s2_score(rows, p, "q"), [0.0, 1.0, 2.0, 3.0, 4.0])
    with pytest.raises(RuntimeError):
        E5.s2_score(rows.iloc[:4], p, "q")


def test_p1_uses_inflation_rate_not_index_level(table):
    r_ref = 5.0
    pv = E5.PriceVault(table, r_ref)
    t = pv._t
    expected = ((t["yoy"] > r_ref) & (t["yoy_prev"] > r_ref)).astype(int)
    assert (t["y"] == expected).all()
    assert "food_cpi" not in t.columns                       # the index level is never used
    assert t["quarter"].min() == "2021-Q2"                     # 2021-Q1 has no in-window predecessor


def test_p1_reference_is_point_in_time(table):
    ref = E5.p1_reference(table)
    assert all(E5.E2.published(q)[0] < E5.T.qstart("2023-Q4") for q in ref["reference_quarters"])
    t2 = table.copy()
    t2.loc[t2["quarter"] >= "2023-Q3", "food_cpi_yoy_target"] += 50
    assert E5.p1_reference(t2)["r_ref"] == pytest.approx(ref["r_ref"])


def test_price_vault_access_rules(table):
    pv = E5.PriceVault(table, 5.0)
    with pytest.raises(PermissionError):
        pv.training(["2024-Q1"], "2024-Q1")
    with pytest.raises(PermissionError):
        pv.reveal("never", "2024-Q1")
    with pytest.raises(RuntimeError):
        E5.PriceVault(pd.DataFrame({"quarter": ["2026-Q3"], "province_code": ["P"], "food_cpi_yoy_target": [1.0]}), 5.0)


def test_p1_folds_meet_minimum_and_respect_publication(table):
    pv = E5.PriceVault(table, 5.0)
    for t, f in zip(E5.TEST_QUARTERS, E5.p1_folds(pv)):
        assert f is not None and len(f.train_quarters) >= 8
        assert all(q < t and E5.E2.published(q)[0] < E5.T.qstart(t) for q in f.train_quarters)


class _Const:
    def predict_proba(self, X):
        return np.c_[np.full(len(X), 0.4), np.full(len(X), 0.6)]


def test_predictions_are_label_free(vault, table, frame):
    stub = lambda X, y, mono: _Const()
    fold = E5.E1.fold_plan(["2024-Q2"])[0]
    p = E5.predict_s2(frame, vault, fold, E5.s2_reference(vault), fitter=stub, check=False)
    pv = E5.PriceVault(table, E5.p1_reference(table)["r_ref"])
    f1 = E5.p1_folds(pv)[2]
    q = E5.predict_p1(frame, vault, pv, f1, fitter=stub, check=False)
    for df in (p, q):
        assert not {"y", "stress_score", "yoy"} & set(df.columns)
        assert set(df["model"]) == {"E3-LightGBM", "carry-forward", "origin-rule",
                                    "always-HIGH (reference)", "always-LOW (reference)"}
    assert vault.revealed == [] and pv.revealed == []


def test_monotone_settings():
    assert E5.MONO["S2"] == [1, 1, 0, 0, 0, 0, 0] and E5.MONO["P1"] == [0] * 7


def test_protected_set_covers_e4():
    keys = E5.E1.snapshot_hashes(E5.PROTECTED_GLOBS)
    assert any(k.startswith("experiments/2026-10-11_devprotocol/runs/20261011T120714Z_E4/") for k in keys)
    assert "experiments/2026-10-11_devprotocol/E5_SCORING_PROTOCOL.md" in keys


def test_runner_never_loads_production_modules():
    code = ("import sys, importlib.util;"
            f"s=importlib.util.spec_from_file_location('e5', r'{PATH}');"
            "m=importlib.util.module_from_spec(s); sys.modules['e5']=m; s.loader.exec_module(m);"
            "m.E1.assert_no_forbidden_modules(); print('ok')")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         env={**os.environ, "PYTHONPATH": "."})
    assert out.returncode == 0 and out.stdout.strip().endswith("ok"), out.stderr[-400:]


def test_execute_requires_authorization():
    with pytest.raises(SystemExit):
        E5.main(["--execute"])
