"""
tests/integration/test_lead2_pit_leakage.py
-------------------------------------------
Point-in-time and leakage guards for the Lead-2 research stack (PROTOCOL_LEAD2_ROOTCAUSE_II):
- every issue-time input is published before its issue date (CPI month, SWS round, news);
- training rows never contain a target quarter at or after the origin, and their price labels were known at it;
- the frozen T43c label re-derives from its components and evaluation rows are aligned to t + lead;
- the verified-timing CPI cut-off uses only months released strictly before the row's issue, one month for food and
  all items together, never beyond m0 + 2;
- the label thresholds' window closes before the first Lead-2 evaluation issue;
- the root-cause results are present (errors attributed, quarter clustering measured).
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
EXP = ROOT / "aipheed-backend-aligned" / "experiments"
LT = EXP / "LEAD2_FIVE_TRIGGER"
FR = EXP / "FORECAST_RESEARCH" / "data"
pytestmark = pytest.mark.skipif(not (LT / "out" / "lead2_rootcause.json").exists(), reason="root-cause outputs missing")
TH_F = {"PH040100000": 4.713333333333334, "PH040200000": 6.053333333333334}


@pytest.fixture(scope="module")
def stack():
    return pd.read_csv(LT / "data" / "stack_l2.csv", dtype={"province_code": str})


def test_issue_time_inputs_published_before_issue(stack):
    iss = pd.to_datetime(stack["issue_date"])
    psa_end = pd.to_datetime(stack["psa_newest_month"] + "-01") + pd.offsets.MonthEnd(0)
    assert (psa_end < iss).all()
    for c in ("sws_newest_published", "news_latest_published"):
        m = stack[c].notna()
        assert (pd.to_datetime(stack.loc[m, c]) < iss[m]).all(), c
    assert (stack["target_q"] == stack["t"] + stack["lead"]).all()


def test_training_rows_and_labels_known_at_origin():
    kp = pd.read_csv(LT / "data" / "known_price_l2.csv", dtype={"province_code": str})
    assert (kp["q"] <= kp["t"] - 1).all()                     # a price label enters training only after its quarter ends
    E = pd.read_csv(LT / "out" / "asof_reeval_rows.csv", dtype={"province_code": str})
    assert (E["q"] == E["t"] + E["lead"]).all()
    assert not kp.merge(E[["t", "province_code", "q"]], on=["t", "province_code", "q"]).shape[0]   # no evaluation target in its own origin's training labels


def test_target_rederives_from_components():
    L = pd.read_csv(FR / "labels_t43c.csv", dtype={"province_code": str})
    assert ((L["H"] > 11.3).astype(int) == L["hunger"]).all()
    assert ((L["price"] & L["hunger"]) == L["y"]).all()
    for p, th in TH_F.items():                                # food leg of the price label at the frozen threshold
        g = L[L["province_code"] == p]
        assert ((g["F"] > th) <= (g["price"] == 1)).all()


def test_verified_cpi_cutoff_uses_only_months_released_before_issue():
    C = pd.read_csv(LT / "out" / "asof_reeval_cutoffs.csv", dtype={"province_code": str})
    led = pd.read_csv(LT / "data" / "psa_cpi_availability_ledger_20261029.csv", dtype=str)
    names = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal", "PH040500000": "Batangas"}
    assert (C["m0"] <= C["m_VER"]).all() and (C["m_VER"] <= C["m0"] + 2).all()
    for r in C[C["m_VER"] > C["m0"]].itertuples():
        for m in range(r.m0 + 1, r.m_VER + 1):
            row = led.loc[(led["reference_month"] == f"{m // 12}-{m % 12 + 1:02d}") & (led["province"] == names[r.province_code])].iloc[0]
            assert row["class"] in ("V1", "V2") and row["archive_release_date"] < r.issue_B
    assert C.groupby(["t", "lead", "province_code"]).size().max() == 1          # one cut-off per row: food and all items together


def test_threshold_window_closes_before_first_evaluation_issue():
    led = pd.read_csv(LT / "data" / "psa_cpi_availability_ledger_20261029.csv", dtype=str)
    dec22 = led.loc[led["reference_month"] == "2022-12", "archive_release_date"].dropna()
    res = json.loads((LT / "out" / "asof_reeval.json").read_text())
    first = res["leakage"]["price_thresholds"]["first_lead2_evaluation_issue"]
    assert (dec22 < first).all() and first == "2023-01-20"


def test_root_cause_measured():
    d = json.loads((LT / "out" / "lead2_rootcause.json").read_text())
    b0 = d["error_attribution"]["B0"]
    assert b0["errors"] == 13 and b0["by_part"] == {"price": 13}
    assert all(c["R6_pass_rate_cluster_bootstrap"] < .5 for c in d["cluster"].values())
    assert all(c["high_quarters"] == 7 for c in d["cluster"].values())
    assert d["ceiling_oracle_eval_period_noise_UPPER_BOUND"]["2"]["tp_fp_fn"][0] / 17 < .6


def test_bias_track_selected_on_development_only():
    p = LT / "out" / "bias_track.json"
    if not p.exists():
        pytest.skip("bias-track outputs missing")
    d = json.loads(p.read_text())
    import hashlib
    assert d["protocol_sha256"] == hashlib.sha256((LT / "PROTOCOL_LEAD2_BIAS_TRACK.md").read_bytes()).hexdigest()
    assert d["development_candidate"] == []                   # neither X1 nor X1-VER passes the development rule
    assert not d["development_selection"]["X1_vs_B0"]["1a_L2_dev_brier_gain_ge_0.005"]
    assert d["adoption_vs_B0"]["X1VER"]                       # a full-sample R1-R7 pass is not adoption
