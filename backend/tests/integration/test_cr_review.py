"""
tests/integration/test_cr_review.py
-----------------------------------
CR_REVIEW (adoption review of LEAD2_CPI_REFRESH candidate CR): the review reproduces from the committed scored rows; the
frozen adoption rule, recomputed, fails only on new false alarms; CR's R6 pass rests on a single row; the release-day
sensitivity reproduces CR at day 10; the served P0H4, its seal and the off-by-default re-issue are unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
REV, SENS = LT / "out" / "cr_review.json", LT / "out" / "cr_release_sensitivity.json"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
SERVED_FILES = {"rows.csv": "86d05bb62b3449d25b4261097a6ad1db1303ed628e3ad8aeea1eb01da1410cb3",
                "evaluation.json": "fbbb51f39721d34c051fec539b71e3d95e6607db38db961e9d2e2868e2e95187"}
pytestmark = pytest.mark.skipif(not REV.exists(), reason="CR_REVIEW results missing")


@pytest.fixture(scope="module")
def rev():
    return json.loads(REV.read_text())


@pytest.fixture(scope="module")
def lead2():
    E = pd.read_csv(LT / "out" / "cpi_refresh_rows.csv", dtype={"province_code": str})
    return E[E["lead"] == 2]


def test_changed_calls_reproduce_from_committed_rows(rev, lead2):
    b, k = lead2["B0_p"] >= .5, lead2["CR_p"] >= .5
    y = lead2["y"] == 1
    got = {"new hit": int((k & ~b & y).sum()), "lost hit": int((~k & b & y).sum()),
           "new false alarm": int((k & ~b & ~y).sum()), "removed false alarm": int((~k & b & ~y).sum())}
    assert got == rev["change_counts"] == {"new hit": 2, "lost hit": 1, "new false alarm": 3, "removed false alarm": 2}
    assert rev["changed_quarters"] == 4 and len(lead2) == 65 and lead2["q"].nunique() == 13
    # accuracy is identical: CR swaps calls, net +1 TP and +1 FP
    assert ((k.astype(int) == lead2["y"]).sum()) == ((b.astype(int) == lead2["y"]).sum()) == 52


def test_adoption_rule_recomputed_fails_only_on_false_alarms(rev):
    rule = rev["adoption_rule_recomputed"]
    assert [c for c, v in rule.items() if not v] == ["2_new_FA_le_new_hits"]
    committed = json.loads((LT / "out" / "cpi_refresh.json").read_text())["adoption"]["rule"]
    assert rule == committed


def test_brier_gain_vs_p0h4u_is_not_robust(rev):
    b = rev["brier_vs_B0"]
    assert b["quarters_better_worse_tied"] == [7, 6, 0]
    assert b["exact_sign_flip_p_one_sided"] > .10 and b["block_bootstrap_committed"]["p_less"] > .10
    assert b["top_quarter"] == "2024-Q4" and b["share_of_gain_from_top_quarter"] > .5
    assert b["multiplicity"]["n_candidate_comparisons"] == 11


def test_r6_pass_is_fragile(rev):
    assert rev["r6_fragility_CR"] == {"lost_hits_to_fail": 1, "extra_false_alarms_to_fail": 1}
    assert rev["cr_lead2_all_R_pass_in_loqo"] == 9                        # of 13 leave-one-quarter-out subsets
    sweep = rev["threshold_sweep_diagnostic"]
    assert [c for c, v in sweep.items() if v["CR"]["R6"]] == ["0.475", "0.5"]


def test_cpi_margins_and_release_sensitivity(rev):
    a = rev["cpi_availability"]
    assert a["min_margin_days"] == 2 and a["release_day_sensitivity"]["10"]["rows_with_fewer_months_than_day10"] == 0
    if not SENS.exists():
        pytest.skip("release-day sensitivity not run")
    s = json.loads(SENS.read_text())
    assert s["10"]["lead2_calls_differ_from_CR"] == 0                      # day 10 reproduces CR
    assert s["10"]["2"]["tp_fp_fn_tn"] == [11, 7, 6, 41]


def test_served_model_seal_and_flags_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    from app.ml.inference import sws_reissue as RI
    monkeypatch.delenv("AIPHEED_SWS_REISSUE", raising=False)
    monkeypatch.delenv("AIPHEED_SWS_REISSUE_DIR", raising=False)
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.evaluation()["seal_sha256"] == SERVED_SEAL and CH1.reliable_lead() == 1
    for name, sha in SERVED_FILES.items():
        assert hashlib.sha256((CH1.data_dir() / name).read_bytes()).hexdigest() == sha
    assert not RI.enabled() and CH1.state_token() == "" and not RI.history_path().exists()
