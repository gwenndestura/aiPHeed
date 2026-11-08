"""Horizon selection (FINAL_THESIS_OBJECTIVES Addendum 3, FINAL_VERIFICATION): the pure decision rule and its failure
cases, the publication timing behind each lead, the served horizon block and the independent verification outputs."""
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments"
VER = EXP / "FINAL_VERIFICATION"
OUT = VER / "out"
sys.path.insert(0, str(VER / "runner"))
from horizon_rule import select_horizon  # noqa: E402

SERVED = Path(__file__).resolve().parents[2] / "data" / "ch1_engine" / "evaluation.json"


def _v(passing: dict[int, bool], r1: dict[int, bool] | None = None) -> dict:
    return {k: {"reliable": ok, "criteria": {"R1": (r1 or {}).get(k, True)}} for k, ok in passing.items()}


def _j(p):
    return json.loads(p.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- the rule
def test_consecutive_passes_give_the_horizon():
    assert select_horizon(_v({1: True, 2: True, 3: False, 4: True}))["max_reliable_lead"] == 2


def test_lead_1_failing_means_no_reliable_horizon():
    s = select_horizon(_v({1: False, 2: True, 3: True}))
    assert s["max_reliable_lead"] is None and s["individually_passing_leads"] == [2, 3]


def test_a_later_pass_does_not_extend_the_horizon():
    assert select_horizon(_v({1: True, 2: False, 5: True}))["max_reliable_lead"] == 1


def test_gap_in_evaluated_leads_stops_the_horizon():
    assert select_horizon(_v({1: True, 3: True}))["max_reliable_lead"] == 1


def test_lead_0_nowcast_is_ignored():
    s = select_horizon(_v({0: True, 1: False}))
    assert s["max_reliable_lead"] is None and 0 not in s["leads_evaluated"]


def test_testable_horizon_is_the_longest_lead_meeting_R1():
    s = select_horizon(_v({1: True, 2: False, 3: False, 4: False}, {1: True, 2: True, 3: True, 4: False}))
    assert s["testable_horizon_R1"] == 3


def test_no_lead_is_capped_at_four():
    s = select_horizon(_v({k: k <= 6 for k in range(1, 9)}))
    assert s["max_reliable_lead"] == 6 and s["leads_evaluated"][-1] == 8


# ---------------------------------------------------------------- the evidence
def test_addendum_3_frozen_and_unchanged():
    ch1 = EXP / "FINAL_THESIS_OBJECTIVES"
    h = hashlib.sha256((ch1 / "ADDENDUM_3_HORIZON_EXTENSION.md").read_bytes()).hexdigest()
    assert h == (ch1 / "runner" / "ADDENDUM_3_SHA256.txt").read_text().strip()
    assert _j(OUT / "horizon_results.json")["addendum3_sha256"] == h


def test_every_evaluable_lead_was_scored():
    t, r = _j(OUT / "testability.json"), _j(OUT / "horizon_results.json")
    evaluable = [int(k) for k, v in t["leads"].items() if v["rows"]]
    assert evaluable == r["leads_evaluated"] == list(range(1, 9))
    assert t["leads"]["9"]["rows"] == 0


def test_horizon_result():
    r = _j(OUT / "horizon_results.json")
    assert select_horizon(r["leads"]) == {k: r[k] for k in ("leads_evaluated", "testable_horizon_R1",
                                                            "max_reliable_lead", "individually_passing_leads")}
    assert r["max_reliable_lead"] == 1 and r["testable_horizon_R1"] == 3 and r["individually_passing_leads"] == [1]
    for k in range(4, 9):
        assert not r["leads"][str(k)]["criteria"]["R1"]


@pytest.mark.parametrize("k", range(1, 9))
def test_publication_timing_per_lead(k):
    P = pd.read_csv(OUT / f"horizon_predictions_lead{k}.csv")
    assert (P["q"] == P["t"] + k).all()
    assert (pd.to_datetime(P["sws_newest_published"]) < pd.to_datetime(P["issue_date"])).all()
    newest = P["sws_newest_q"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1)
    assert ((P["q"] - newest) == P["true_horizon"]).all()
    assert (P["true_horizon"] >= k).all()            # the newest survey is never the target quarter itself


def test_served_evaluation_carries_the_horizon_block():
    ev = _j(SERVED)
    h = ev["horizon"]
    assert h["max_reliable_lead"] == ev["max_reliable_lead"] == 1
    assert h["leads"]["1"]["quarters_after_newest_sws"] == [1, 2]
    assert "R1" in h["why_not_longer"] or "10 target quarters" in h["why_not_longer"]


def test_independent_verification_outputs():
    m = _j(OUT / "verify_metrics.json")
    assert m["1"]["CH1"]["correct"] == 64 and m["1"]["CH1"]["n"] == 70 and m["1"]["matches_reported"]
    assert all(_j(OUT / "verify_repro.json")[k]["max_abs_diff_CH1_p"] == 0 for k in ("0", "1", "2", "3", "4"))
    lab = _j(OUT / "verify_labels.json")
    assert lab["independent_labelled_province_quarters"] == 100
    assert all(len(v["label_disagreements"]) <= 1 for v in lab["leads"].values())
    assert _j(OUT / "verify_leakage.json")["passed"]
