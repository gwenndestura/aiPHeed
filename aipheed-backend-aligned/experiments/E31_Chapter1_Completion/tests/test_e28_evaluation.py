"""E28 Objectives 2 and 4: checks on the frozen evaluation and its outputs (runs/e28_eval)."""
import hashlib
import json

import pandas as pd
import pytest

from _paths import EXP

OUT = EXP / "runs" / "e28_eval"
pytestmark = pytest.mark.skipif(not (OUT / "results.json").exists(), reason="E28 evaluation not run yet")


def _res():
    return json.loads((OUT / "results.json").read_text(encoding="utf-8"))


def test_protocol_is_unchanged_since_freezing():
    want = (EXP / "runner" / "E28_PROTOCOL_SHA256.txt").read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256((EXP / "E28_EVALUATION_PROTOCOL.md").read_bytes()).hexdigest() == want
    assert _res()["inputs"]["protocol"] == want


def test_alignment_with_e25_and_leakage_counters():
    r = _res()
    for tg in ("T1_A", "T2"):
        a = r["alignment"][tg]
        assert a["mismatches"] == [] and a["train_rows_match"] == a["folds"] == a["test_rows_match"]
    assert r["leakage"]["no_pre2021_lag_values"] is True
    assert r["leakage"]["articles_outside_their_quarter_or_after_limit"] == 0
    assert r["shap_additivity_max_error"] is not None and r["shap_additivity_max_error"] < 1e-6


def test_every_arm_is_scored_on_identical_rows():
    P = pd.read_csv(OUT / "predictions.csv", dtype={"province_code": str})
    for tg, g in P.groupby("target"):
        keys = {a: set(zip(h["lead"], h["t"], h["province_code"])) for a, h in g.groupby("arm")}
        ref = keys["B1"]
        for a, k in keys.items():
            if a == "PROPOSED_E25":
                # documented exception (BUG_FIXES M-E28-3): E25's own LightGBM has no prediction at origin 2026-Q1
                # lead 1 (its features end at 2025-Q4); runs/e28_eval_common_rows.json re-scores every arm on the
                # shared rows
                assert ref - k == {(1, "2026-Q1", p) for p in g["province_code"].unique()} and not (k - ref), (tg, a)
                continue
            assert k == ref, (tg, a)
        y = g.groupby(["lead", "t", "province_code"])["y"].nunique()
        assert (y == 1).all()                       # one outcome per row, whatever the arm
    common = json.loads((EXP / "runs" / "e28_eval_common_rows.json").read_text(encoding="utf-8"))
    assert common["T1_A"]["rows"] == 140 and common["T2"]["rows"] == 205


def test_not_estimable_metrics_are_marked_and_no_lead_is_called_reliable_without_5_LOW():
    r = _res()
    det = json.loads((OUT / "E28_DETERMINATION.json").read_text(encoding="utf-8"))
    for tg, arms in r["summary"].items():
        for arm, d in arms.items():
            for lead, m in d["by_lead"].items():
                if m["HIGH"] == 0 or m["LOW"] == 0:
                    assert m["roc_auc"] is None and m["flags"]["roc_auc"] == "NOT_ESTIMABLE"
                if min(m["HIGH"], m["LOW"]) < 5 and m["roc_auc"] is not None:
                    assert m["flags"]["roc_auc"] == "UNSTABLE"
        for arm, leads in det[tg]["reliable_leads"].items():
            for L in leads:
                s = r["summary"][tg][arm]["by_lead"][str(L)]
                assert s["LOW"] >= 5 and s["HIGH"] >= 5 and s["dates"] >= 8


def test_baseline_definitions_cover_chapter_one_objective_4():
    arms = set(pd.read_csv(OUT / "predictions.csv", usecols=["arm"])["arm"])
    assert {"B1", "PSA_LR", "PSA_LGBM", "NLP_LR", "NLP_LGBM", "LR_COMB", "PROPOSED"} <= arms
    assert {"ALWAYS_HIGH", "CLIM", "MAJ"} <= arms
