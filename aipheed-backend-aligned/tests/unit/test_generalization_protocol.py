"""
Leakage-safety checks for scripts/supplementary/generalization_study.py.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline

import scripts.supplementary.generalization_study as G

EXP = Path("experiments/2026-10-09_generalization")


def test_preregistration_unchanged():
    assert hashlib.sha256((EXP / "PREREGISTRATION.json").read_bytes()).hexdigest() == G.PREREG_SHA


def test_pool_is_fixed_and_ordered_simplest_first():
    p = G.pool()
    assert len(p) == 54
    assert p[0]["id"] == "eq5_12|logistic|C=0.01|w=None"
    assert [c["fs"] for c in p[::18]] == ["eq5_12", "gov47_no_commodity", "gov47"]


def _toy():
    rows = []
    for t in range(14):
        q = f"{2020 + t // 4}-Q{t % 4 + 1}"
        for p in range(5):
            rows.append({"target_quarter": q, "province_code": f"P{p}", "y": (t + p) % 2, "x": float(t + p)})
    return pd.DataFrame(rows)


def test_training_rows_always_precede_the_test_quarter():
    d = _toy()
    for q, tr, te in G.splits(d, 8):
        assert (tr["target_quarter"].map(G.R.qi) < G.R.qi(q)).all()
        assert set(te["target_quarter"]) == {q} and len(te) == 5
        for q2, tr2, te2 in G.splits(tr, G.INNER_MIN):
            assert q not in set(tr2["target_quarter"]) | set(te2["target_quarter"])


def test_scaler_lives_inside_the_fitted_pipeline():
    m = G.make({"family": "logistic", "C": 1.0, "w": None}, np.array([0, 1]))
    assert isinstance(m, Pipeline) and m.steps[0][0] == "standardscaler"


def test_scale_pos_weight_comes_from_training_labels_only():
    m = G.make({"family": "lgbm", "w": "spw"}, np.array([1, 0, 0, 0]))
    assert abs(m.get_params()["scale_pos_weight"] - 3.0) < 1e-12


def test_frozen_prospective_config_cites_the_preregistration():
    p = EXP / "FROZEN_PROSPECTIVE_CONFIG.json"
    if p.exists():
        assert json.loads(p.read_text())["preregistration_sha256"] == G.PREREG_SHA
