"""E177 output checks (run from backend: PYTHONPATH=. python -m pytest ../experiments/E177_SIMPLE_V2/test_e177.py -q)."""
from pathlib import Path

import pandas as pd

H = Path(__file__).resolve().parent


def test_required_files_exist():
    for f in ("E177_REPORT.md", "candidate_registry.csv", "training_only_validation.csv", "calibration_analysis.csv", "model_stability.csv",
              "evaluation_comparison.csv", "PROTECTED_ARTIFACTS_CHECK.md"):
        assert (H / f).exists(), f


def test_validation_is_training_only_and_lightgbm_only():
    v = pd.read_csv(H / "training_only_validation.csv")
    assert v["population"].str.contains("untainted").all() and (v["rows"] == 156).all()
    reg = pd.read_csv(H / "candidate_registry.csv")
    assert (reg["lightgbm"] == "yes").all() and set(v["candidate"]) == set(reg["candidate"])


def test_exactly_one_selected_and_v2_not_scored_on_the_72_rows():
    v = pd.read_csv(H / "training_only_validation.csv")
    assert v["selected_by_registered_rule"].sum() == 1
    c = pd.read_csv(H / "evaluation_comparison.csv")
    assert c.loc[c["model"].str.startswith("SIMPLE v2"), "population"].str.contains("UNVERIFIED").all()
