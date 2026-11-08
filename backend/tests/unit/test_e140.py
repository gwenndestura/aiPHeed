"""E140: lock, zero trees excluded from both grids, island group is a 3-level covariate (no unit identifiers),
diagnostics recorded, decision follows the frozen rule, registry keeps production empty."""
from __future__ import annotations

import json

from app import registry as R
from app.e140 import evaluate as E
from app.e140 import model as M


def test_protocol_lock_matches_code():
    E.verify_lock()


def test_zero_trees_cannot_be_selected():
    assert 0 not in M.LT_GRID and 0 not in M.GBC_GRID


def test_island_is_coarse_geography_not_identifier():
    X = M.data()
    assert X["island_code"].nunique() == 3 and X["island_code"].notna().all()
    banned = {"key", "province", "region", "survey", "year", "y", "q", "status"}
    assert not banned & (set(M.LT_FEATURES) | set(M.GBC_FEATURES))


def test_decision_follows_frozen_rule():
    r = json.loads((E.OUT / "results.json").read_text())
    c = r["gate"]["checks"]
    structural = all(c[k] for k in ["T1_trees_selected", "T2_trees_beat_linear_prior", "G1_beats_national",
                                    "G5_discrimination_classes", "G6_calibration", "G4_not_worse_than_best_benchmark",
                                    "G7_overfitting", "G8_island_transfer"])
    full = structural and all(c[k] for k in ["G2_beyond_region_history", "G3_noninferior_persistence", "G9_forward_in_time"])
    assert r["gate"]["decision"] == ("A" if full else "B" if structural else "C")
    assert r["final_model"]["n_trees"] > 0


def test_diagnostics_present():
    d = json.loads((E.OUT / "diagnostics.json").read_text())
    assert set(d["D4_tree_curves"]) >= {"with_prior", "without_prior"}


def test_e140_not_in_production():
    reg = R.load()
    assert reg["models"]["e140-lgbm-native-1.0"]["status"] == "rejected" and (reg.get("production") or {}).get("model_id") != "e140-lgbm-native-1.0"
