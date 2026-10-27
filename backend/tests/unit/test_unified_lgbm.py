"""Tests for FINAL_UNIFIED_LGBM (one LightGBM across leads): frozen protocol and addendum, leakage audit, development-only
selection, the horizon verdicts, the seal, and agreement between the served evaluation and the scored results."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
UNI = ROOT / "aipheed-backend-aligned" / "experiments" / "FINAL_UNIFIED_LGBM"
OUT = UNI / "out"
SERVED = ROOT / "backend" / "data" / "ch1_engine"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _j(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def test_protocol_and_addendum_are_frozen():
    assert _sha(UNI / "PROTOCOL_UNIFIED_LGBM.md") == (UNI / "runner" / "PROTOCOL_SHA256.txt").read_text().strip()
    assert _sha(UNI / "ADDENDUM_1_IMPROVEMENT_ARMS.md") == (UNI / "runner" / "ADDENDUM_1_SHA256.txt").read_text().strip()
    assert _j(OUT / "results.json")["protocol_sha256"] == _sha(UNI / "PROTOCOL_UNIFIED_LGBM.md")


def test_leakage_audit_passed_at_six_origins():
    a = _j(OUT / "leakage_audit.json")
    assert a["passed"] and len(a["origins"]) == 6 and all(o["identical"] and o["n_price"] for o in a["origins"])


def test_variant_and_hunger_model_chosen_on_development_brier():
    s = _j(OUT / "results.json")["selection"]
    br = s["dev_brier_T43c_mean_leads_1_4"]
    assert s["chosen_price_variant"] == min(br, key=br.get)
    hb = s["dev_brier_hunger_condition"]
    assert s["hunger_model"] == ("HG" if hb["HG"] < hb["pi_H"] else "pi_H")


def test_one_model_scores_every_lead_and_the_horizons_follow_the_rule():
    r = _j(OUT / "results.json")
    leads = {int(k): v for k, v in r["leads"].items()}
    assert sorted(leads) == list(range(1, 16))
    mrl = None
    for k in sorted(leads):
        if leads[k]["reliable"]:
            mrl = k
        else:
            break
    assert r["max_reliable_lead"] == mrl == 1
    assert r["testable_horizon_R1"] == max(k for k, v in leads.items() if v["criteria"]["R1"]) == 5
    assert leads[1]["metrics"]["accuracy"] >= 0.75 and all(leads[1]["criteria"].values())


def test_post_hoc_arms_were_selected_on_development_quarters_only():
    imp = _j(OUT / "improved_results.json")
    assert imp["status"].startswith("post-hoc")
    sel = imp["dev_selection"]
    cap = "U4" if sel["U4"]["brier"] < sel["UNI-FINAL"]["brier"] else "UNI-FINAL"
    assert imp["capacity_choice"] == cap


def test_served_evaluation_matches_the_scored_results():
    r, ev = _j(OUT / "results.json"), _j(SERVED / "evaluation.json")
    assert ev["protocol_sha256"] == r["protocol_sha256"] and ev["max_reliable_lead"] == r["max_reliable_lead"]
    for k in ("1", "2", "3", "4", "5"):
        assert ev["leads"][k]["metrics"]["accuracy"] == pytest.approx(r["leads"][k]["metrics"]["accuracy"])
    h = ev["horizon"]
    assert h["generated_up_to"] == 15 and h["testable_horizon_R1"] == 5 and h["max_reliable_lead"] == 1


def test_seal_unchanged_and_served_forecasts_match_it():
    seal = OUT / "sealed_prospective.csv"
    assert _sha(seal) == (OUT / "sealed_prospective.csv.sha256").read_text().strip() == _j(SERVED / "evaluation.json")["seal_sha256"]
    s = pd.read_csv(seal, dtype={"province_code": str})
    assert sorted(s["lead"].unique()) == list(range(1, 16)) and (s["issue_date"] == "2026-10-01").all()
    rows = pd.read_csv(SERVED / "rows.csv", dtype={"province_code": str})
    fwd = rows[rows["issue_date"] >= "2026-10-01"].merge(s, on=["province_code", "quarter", "lead"], suffixes=("", "_s"))
    assert len(fwd) == 20 and (fwd["probability"] - fwd["probability_s"]).abs().max() < 1e-9


def test_lead2_seasonal_arm_was_frozen_and_not_adopted():
    assert _sha(UNI / "ADDENDUM_2_LEAD2_SEASONAL.md") == (UNI / "runner" / "ADDENDUM_2_SHA256.txt").read_text().strip()
    r = _j(OUT / "seasonal_results.json")
    assert r["adopted"] is (r["dev_brier"]["U6_p"] < r["dev_brier"]["UNI_p"]) and r["adopted"] is False
    assert _j(SERVED / "evaluation.json")["max_reliable_lead"] == 1
