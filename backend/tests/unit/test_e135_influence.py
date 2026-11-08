"""
tests/unit/test_e135_influence.py
---------------------------------
E135 (feature-influence optimization): frozen protocol, deliverables, reference reproduction (FULL7 = E134-AREA-T,
HFM-X at prior 1), nested choices use only past published targets, group-specific prior scales, the frozen selection
rule and the reported outcome, and the harmful/demonstrated classification.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[2].parent
E = REPO / "aipheed-backend-aligned" / "experiments" / "E135_Feature_Influence"
pytestmark = pytest.mark.skipif(not (E / "out" / "e135_metrics.csv").exists(), reason="E135 outputs not built")
DELIV = ["E135_FEATURE_AUDIT.csv", "E135_FEATURE_INFLUENCE_EXPERIMENTS.csv", "E135_TRIGGER_GROUP_ABLATION.csv",
         "E135_LEAD_COMPARISON.csv", "E135_OVERFITTING_GENERALIZATION_REPORT.md", "E135_HIGH_HUNGER_BIAS_REPORT.md",
         "E135_FINAL_RESEARCH_PACKAGE.md"]


def _load(name: str):
    sys.path.insert(0, str(E / "runner"))
    spec = importlib.util.spec_from_file_location(name, E / "runner" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_protocol_and_deliverables():
    sha = hashlib.sha256((E / "E135_FROZEN_PROTOCOL.md").read_bytes()).hexdigest()
    assert (E / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0] == sha
    for d in DELIV:
        assert (E / d).exists(), d


def test_references_reproduce_and_nested_choices_are_past_only():
    P = pd.read_csv(E / "out" / "e135_predictions.csv")
    assert np.nanmax(np.abs(P["f_FULL7"] - P["f_E134-AREA-T"])) < 1e-6
    assert np.nanmax(np.abs(P["f_HFMX-s1"] - P["f_HFM-X"])) < 1e-6
    C = pd.read_csv(E / "out" / "e135_nested_choices.csv")
    P["issue"], P["pub"] = pd.to_datetime(P["issue"]), pd.to_datetime(P["published_target"])
    for r in C.sample(20, random_state=135).itertuples():
        issue = pd.Timestamp(r.issue)
        n = int(((P.policy == r.policy) & (P.lead == r.lead) & (P.issue < issue) & (P.pub < issue)).sum())
        assert n == r.past_rows
    first = C[C.past_rows < 8]
    assert (first.loc[first.procedure == "X-SEL", "choice"] == "A+C+E+N+V+aR+aP").all()
    assert set(first.loc[first.procedure.isin(["X-NSD", "X-STACK", "X-COMB"]), "choice"].astype(float)) == {1.0}


def test_group_prior_scale_shrinks():
    S = _load("e135_run")
    from datetime import date
    rr = S.X.rounds()
    qa = S.X.asof(rr, date(2025, 10, 1))
    drv, adrv = {"rice": S.R.Drivers("rice")}, S.E.AreaDrivers()
    _, _, f1 = S.predict_cfg(qa, date(2025, 10, 1), S.L.qi("2026-Q1"), drv, adrv, ("A",), {"A": 1.0})
    _, _, f2 = S.predict_cfg(qa, date(2025, 10, 1), S.L.qi("2026-Q1"), drv, adrv, ("A",), {"A": 0.1})
    assert f2.beta["A"] <= f1.beta["A"] + 1e-9


def test_selection_and_outcome():
    s = json.loads((E / "out" / "e135_summary.json").read_text())
    assert s["selection"]["candidate"] == "HFM-X" and s["maximum_reliable_lead"] is None
    assert s["any_rule_set_passed"] == [] and not s["any_model_any_lead_75"]
    assert all(r["model"] != "X-EXCL" for r in s["selection"]["table"])
    assert all(v < 2 / 3 for k, v in s["nested_choice_modal_share"].items() if k.endswith("|2"))
    a = pd.read_csv(E / "out" / "e135_loo_audit.csv")
    rem = a.test == "removed from FULL7"
    exp = rem & (a.delta_mae_variant_minus_full7 > 0) & (a.delta_within_variant_minus_full7 < 0) & (a.p_full7_better_sq_error < 0.10)
    assert (a.demonstrated_contribution == exp).all()
    assert set(a.loc[a.harmful & (a.lead == 2), "group"]) == {"aP"}
