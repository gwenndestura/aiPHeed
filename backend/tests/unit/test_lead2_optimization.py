"""Tests for LEAD2_OPTIMIZATION: frozen protocol and addenda, leakage audits (future perturbation, positive control,
historical replay), target verification, identical evaluation rows across candidates, frozen selection rules, the
12-family requirement, and that the served model and seal are unchanged unless the serve rule passed."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
L2 = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_OPTIMIZATION"
OUT = L2 / "out"
RUN = L2 / "runner"
UNI = ROOT / "aipheed-backend-aligned" / "experiments" / "FINAL_UNIFIED_LGBM"
SERVED = ROOT / "backend" / "data" / "ch1_engine"
FAMILIES = {"A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1"}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _j(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def _brier(p, y) -> float:
    return float(np.mean((np.clip(np.asarray(p, float), 0, 1) - np.asarray(y, float)) ** 2))


@pytest.mark.parametrize("doc, sha", [("PROTOCOL_LEAD2.md", "PROTOCOL_SHA256.txt"),
                                      ("ADDENDUM_1_STRUCTURAL_PRIOR.md", "ADDENDUM_1_SHA256.txt"),
                                      ("ADDENDUM_2_CONTROLLED_COMPARISON.md", "ADDENDUM_2_SHA256.txt"),
                                      ("ADDENDUM_3_HUNGER_ONSET.md", "ADDENDUM_3_SHA256.txt")])
def test_protocol_and_addenda_unchanged_since_freezing(doc, sha):
    assert _sha(L2 / doc) == (RUN / sha).read_text().strip()


@pytest.mark.parametrize("name", ["leakage_audit.json", "leakage_audit_addendum1.json",
                                  "leakage_audit_addendum2.json", "leakage_audit_addendum3.json"])
def test_future_data_perturbation_leaves_every_forecast_identical(name):
    a = _j(name)
    assert a["passed"] and len(a["origins"]) == 6 and all(o["identical"] for o in a["origins"])


def test_positive_control_perturbing_published_data_changes_the_forecast():
    c = _j("leakage_positive_control.json")
    assert c["changed"] and all(o["max_abs_change_P1"] > 0 for o in c["origins"])


def test_historical_replay_reproduces_the_scored_forecasts():
    r = _j("historical_replay.json")
    assert r["identical"] and all(o["rows_compared"] > 0 for o in r["origins"])


def test_baseline_reproduction_matches_the_unified_report():
    b = _j("baseline_reproduction.json")
    assert b["2"]["matches_report"] and b["2"]["n"] == 65 and b["2"]["quarters"] == 13
    assert b["2"]["dup_rows"] == 0 and b["2"]["tp"] + b["2"]["fn"] == 17


def test_target_definition_recomputes_exactly():
    t = (OUT / "target_verification.txt").read_text(encoding="utf-8")
    assert "labels recomputed == stored: True" in t and "P60 linear 11.3" in t


def test_every_candidate_is_scored_on_identical_rows():
    D = pd.read_csv(OUT / "predictions_addendum3.csv", dtype={"province_code": str})
    base = pd.read_csv(UNI / "out" / "predictions.csv", dtype={"province_code": str})
    assert len(D) == len(base) and not D.duplicated(["t", "lead", "province_code"]).any()
    cols = [c for c in D.columns if c.endswith("H0_p") or c.endswith("_p3")]
    assert cols and D[cols].notna().all().all()
    assert (D[D["lead"] == 2].shape[0], D[D["lead"] == 2]["q"].nunique()) == (65, 13)


def test_frozen_selections_follow_the_development_brier_rule():
    D = pd.read_csv(OUT / "predictions_addendum2.csv", dtype={"province_code": str})
    dev = D[(D["q"] <= 8099) & (D["lead"] == 2)]
    r2 = _j("results_addendum2.json")["selection"]
    for a, v in r2["dev_lead2_brier"].items():
        assert v == pytest.approx(_brier(dev[f"{a}_p"], dev["y"]), abs=1e-6)  # CSV keeps 6 significant figures
    order = ["P0H0", "P4H0", "P6H0", "P7H0", "P8H0"]
    best = order[0]
    for a in order[1:]:
        if r2["dev_lead2_brier"][a] < r2["dev_lead2_brier"][best] - 0.0005:
            best = a
    assert r2["adopted_before_calibration"] == best


def test_reported_lead2_metrics_recompute_from_predictions():
    D = pd.read_csv(OUT / "predictions_addendum3.csv", dtype={"province_code": str})
    r3 = _j("results_addendum3.json")
    for name, c in r3["candidates"].items():
        g = D[D["lead"] == 2]
        y = g["y"].astype(int).to_numpy()
        yh = (g[f"{name}_p3"] >= 0.5).astype(int).to_numpy()
        assert c["leads"]["2"]["metrics"]["accuracy"] == pytest.approx(float((yh == y).mean()))
        assert c["leads"]["2"]["confusion"]["fn"] == int(((yh == 0) & (y == 1)).sum())


def test_all_twelve_families_are_in_the_price_model_columns():
    import sys
    sys.path.insert(0, str(RUN))
    pytest.importorskip("lightgbm")
    import l2_lib as X
    fams = {X.FAMILY_OF[c] for c in X.base_cols(True)} - {"lead"}
    assert fams == FAMILIES
    assert {X.FAMILY_OF[c] for c in X.fe_cols(True)} - {"lead"} == FAMILIES


def test_no_reliable_verdict_is_issued_without_untouched_outcomes():
    for name in ("results_addendum2.json", "results_addendum3.json"):
        for c in _j(name)["candidates"].values():
            assert all(v["verdict"] in ("promising_not_yet_verified", "not_reliable") for v in c["leads"].values())


def test_served_model_is_the_adopted_candidate_with_its_own_seal():
    rule = _j("serve_rule_addendum3.json")["rule"]
    assert rule["serve"] and rule["adopted"] == "P0H4"
    ev = json.loads((SERVED / "evaluation.json").read_text(encoding="utf-8"))
    seal = OUT / "sealed_prospective_P0H4.csv"
    assert _sha(seal) == (OUT / "sealed_prospective_P0H4.csv.sha256").read_text().strip() == ev["seal_sha256"]
    assert ev["previous_seal_sha256"] == _sha(UNI / "out" / "sealed_prospective.csv")
    assert ev["protocol_sha256"] == _sha(L2 / "PROTOCOL_LEAD2.md") and ev["max_reliable_lead"] == 1
    assert not any(ev["leads"][k]["reliable"] for k in ("2", "3", "4", "5"))
    s = pd.read_csv(seal, dtype={"province_code": str})
    assert sorted(s["lead"].unique()) == list(range(1, 16)) and (s["issue_date"] == "2026-10-01").all()
    rows = pd.read_csv(SERVED / "rows.csv", dtype={"province_code": str})
    fwd = rows[rows["issue_date"] >= "2026-10-01"].merge(s, on=["province_code", "quarter", "lead"], suffixes=("", "_s"))
    assert len(fwd) == 20 and (fwd["probability"] - fwd["probability_s"]).abs().max() < 1e-9
    assert {f"avail_{g}" for g in ("market", "climate", "fish_kill", "employment", "ofw_remittance")} <= set(rows.columns)


def test_one_model_candidate_was_scored_and_not_served():
    r4 = _j("results_addendum4.json")
    chosen = r4["selection"]["chosen"]
    assert not r4["serve_rule"]["serve"] and r4["models"][chosen]["max_r1_r7_lead"] == 0
