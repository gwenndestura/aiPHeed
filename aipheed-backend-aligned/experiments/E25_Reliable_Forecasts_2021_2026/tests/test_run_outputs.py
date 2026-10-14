"""Chronological splits, identical rows, sealed bytes, reproducibility and reachability (frozen run outputs)."""
import hashlib
import json

import numpy as np
import pandas as pd
import pytest

import _paths
from _paths import EXP
import e25lib as E
import reachability as RCH


@pytest.fixture(scope="module")
def run():
    rid = _paths.primary_run()
    rd = EXP / "runs" / rid
    return rid, rd, json.loads((rd / "SEALS.json").read_text())


def test_sealed_predictions_match_their_hash(run):
    rid, rd, seals = run
    for nm, h in seals.items():
        assert hashlib.sha256((rd / f"predictions_{nm}.csv").read_bytes()).hexdigest() == h


def test_reproduction_byte_identical():
    r = json.loads((EXP / "runs" / "reproducibility.json").read_text())
    assert r["prediction_seals_identical"] and r["all_files_identical"] and r["run_code_identical"]
    assert r["monthly"]["identical"]


def test_chronological_folds(run):
    rid, rd, _ = run
    meta = json.loads((rd / "fold_meta_T1_A.json").read_text())
    for key, m in meta.items():
        t = E.qk(m["t"])
        assert E.qk(m["target_quarter"]) == t + m["lead"]
        assert m["n_train_quarters"] >= 8
    P = pd.read_csv(rd / "predictions_T1_A.csv", dtype={"province_code": str})
    assert (P["origin"] == P["t"].map(lambda q: E.origin(E.qk(q)).date().isoformat())).all()
    assert (P["target_quarter"].map(E.qk) - P["t"].map(E.qk) == P["lead"]).all()


def test_identical_rows_across_models_in_R_A(run):
    rid, rd, _ = run
    import score_e25 as S
    P = pd.read_csv(rd / "predictions_T1_A.csv", dtype={"province_code": str})
    models = S.REQ_B + [S.PROPOSED] + S.REFS + S.T1_CANDS
    d, dropped = S.rowset(P, models, "2025-Q4")
    keys = {m: set(map(tuple, d[d["model"] == m][["lead", "t", "province_code"]].to_numpy())) for m in models}
    first = next(iter(keys.values()))
    assert all(k == first for k in keys.values()) and not dropped


def test_reachability_exact_p_is_two_to_minus_m():
    for m in range(1, 7):
        d = np.r_[np.full(m, 0.2), np.zeros(8 - m)]
        assert abs(RCH.exact_p(d) - 2.0 ** -m) < 1e-12


def test_no_criterion_reported_met_when_it_is_not(run):
    rid, rd, _ = run
    r = json.loads((rd / "results.json").read_text())
    c = r["T1_A"]["criteria_C1_C9"]
    goal = all(c[k] is True for k in c if k.startswith("C") and k[1].isdigit() and k[:2] not in ("C8", "C9"))
    assert goal is False                      # the T1 forecasting goal is not met in the frozen run
    assert c["C9_generalizes_unseen"].startswith("NOT ASSESSABLE")
