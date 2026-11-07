"""E178 output checks (from backend: PYTHONPATH=. python -m pytest ../experiments/E178_SIMPLE_SYSTEM_IMPROVEMENT/test_e178.py -q)."""
from pathlib import Path

import pandas as pd

H = Path(__file__).resolve().parent


def test_required_files():
    for f in ("E178_REPORT.md", "data_quality_audit.csv", "feature_audit.csv", "temporal_validation.csv", "stability_analysis.csv",
              "candidate_registry.csv", "evaluation_comparison.csv", "PROTECTED_ARTIFACTS_CHECK.md", "selection_rule.md"):
        assert (H / f).exists(), f


def test_training_only_population_and_lightgbm():
    v = pd.read_csv(H / "training_only_validation.csv")
    assert v["population"].str.contains("untainted").all()
    assert (pd.read_csv(H / "candidate_registry.csv")["lightgbm"] == "yes").all()


def test_no_candidate_claims_predictive_improvement_and_new_ones_unverified():
    v = pd.read_csv(H / "training_only_validation.csv")
    assert not (v["decision_by_registered_rule"] == "predictive + stability improvement").any()
    c = pd.read_csv(H / "evaluation_comparison.csv")
    assert c["population"].str.contains("UNVERIFIED").any()


def test_structural_audit_has_no_problem_rows():
    d = pd.read_csv(H / "data_quality_audit.csv")
    assert not d["verdict"].astype(str).str.contains("PROBLEM").any()
