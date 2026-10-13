"""
The governing 45-candidate configuration (config/governing_model.json) must
match the feature matrix on disk and reproduce the frozen MODEL-B2 result.
"""

import json
from pathlib import Path

import pandas as pd
import pytest

CFG = json.loads(Path("config/governing_model.json").read_text())
FS = CFG["feature_set"]


def test_candidates_are_the_fused_matrix_columns():
    fused = pd.read_parquet("data/processed/features_fused.parquet")
    cand = [c for c in fused.columns if c not in ("province_code", "quarter", "cpi_dev")]
    assert cand == FS["candidates_section_3_3_2_6"]
    assert len(cand) == FS["n_candidates"] == 45


def test_model_inputs_are_candidates_plus_two():
    assert FS["model_inputs"] == FS["candidates_section_3_3_2_6"] + ["cpi_dev", "sws_hunger"]
    assert FS["n_model_inputs"] == 47
    assert not {"label_stress", "stress_score", "y"} & set(FS["model_inputs"])


def test_protocol_is_unchanged():
    assert CFG["decision_threshold"] == 0.5
    assert CFG["seed"] == 42
    assert CFG["walk_forward"]["outer_min_target_quarters"] == 8
    assert len(CFG["walk_forward"]["test_quarters"]) == 11
    assert CFG["algorithm4_holdout"] == ["2024-Q3", "2024-Q4", "2025-Q1", "2025-Q4"]


@pytest.mark.slow
def test_reproduces_frozen_model_b2():
    import scripts.supplementary.algorithm4_timing_valid as A
    import scripts.supplementary.reliability_diagnostics as R
    from scripts.evaluate_governing_model import metrics, walk

    f, labels, cols = A.frame_t2()
    assert cols == FS["model_inputs"]
    r = walk(R.pairs(f, labels, 1), cols, CFG)
    m = metrics(r)
    exp = CFG["expected_results"]
    assert (m["correct"], m["accuracy_mean_fold"], m["f1_weighted"], m["roc_auc"]) == (
        exp["correct"], exp["accuracy_mean_fold"], exp["f1_weighted"], exp["roc_auc"])
    saved = pd.read_csv(exp["reference_predictions"])
    mg = r.merge(saved, on=["target_quarter", "province_code"], suffixes=("", "_saved"))
    assert len(mg) == 55 and (mg["pred"] == mg["pred_saved"]).all()
    assert (mg["p"] - mg["p_saved"]).abs().max() < 1e-12
