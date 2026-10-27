"""Tests for FINAL_ARCHITECTURE: frozen protocol, leakage audit (incl. ONI and injected PAGASA items), candidate C
reproducing S3, the frozen selection and recommendation rules, the climate placebo verdict, the full Market removal
diagnostic, and that the served P0H4 and its seal were not changed."""
import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
FA = ROOT / "aipheed-backend-aligned" / "experiments" / "FINAL_ARCHITECTURE"
OUT = FA / "out"
L2 = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_OPTIMIZATION" / "out"
SERVED = ROOT / "backend" / "data" / "ch1_engine"


def _j(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_protocol_unchanged_since_freezing():
    assert _sha(FA / "PROTOCOL_FINAL_ARCHITECTURE.md") == (FA / "runner" / "PROTOCOL_SHA256.txt").read_text().strip()
    assert _j(OUT / "results.json")["protocol_sha256"] == _sha(FA / "PROTOCOL_FINAL_ARCHITECTURE.md")


def test_future_perturbation_including_climate_inputs_leaves_forecasts_identical():
    a = _j(OUT / "leakage_audit.json")
    assert a["passed"] and len(a["origins"]) == 6 and set(a["candidates"]) == {"C", "D", "E", "F", "G"}


def test_candidate_c_reproduces_s3_and_replays():
    assert _j(OUT / "results.json")["C_reproduces_S3_max_abs_diff"] < 1e-5
    r = _j(OUT / "historical_replay_C.json")
    assert r["identical"] and all(o["rows_compared"] > 0 for o in r["origins"])


def test_selection_and_recommendation_follow_the_frozen_rules():
    r = _j(OUT / "results.json")
    dev = {n: r["candidates"][n]["dev_brier_mean_leads_1_3"] for n in "CDEFG"}
    order = {"C": 0, "D": 1, "E": 1, "F": 1, "G": 2}
    best = min((n for n in "CDEFG" if r["eligibility"][n]), key=lambda n: (dev[n], order[n]))
    chosen = min((n for n in "CDEFG" if r["eligibility"][n] and dev[n] - dev[best] <= 0.002), key=lambda n: order[n])
    assert r["chosen"] == chosen == "C"
    assert r["recommendation"]["single_model_recommended"] and r["recommendation"]["lead3_significantly_worse"]
    for n in "CDEFG":
        assert r["candidates"][n]["max_promising_lead"] == 1


def test_climate_gain_failed_its_placebo_and_is_not_claimed():
    r = _j(OUT / "results.json")
    assert r["block_usefulness"]["D"]["adds_predictive_value"]          # passed the pre-set screen ...
    p = _j(OUT / "climate_placebo_D.json")
    assert p["perm_p"]["2"] > 0.10                                     # ... but shuffled climate does as well
    report = (FA / "FINAL_ARCHITECTURE_REPORT.md").read_text(encoding="utf-8")
    assert "failed placebo" in report or "**Placebo**" in report


def test_market_information_is_essential_in_the_single_model():
    m = _j(OUT / "market_full_removal_C.json")["variants"]["without Market columns and without offset"]
    for k in ("1", "2"):
        assert m[k]["brier_full_minus_ablated"]["ci90"][1] < 0


def test_served_model_and_seal_unchanged():
    ev = _j(SERVED / "evaluation.json")
    assert ev["seal_sha256"] == _sha(L2 / "sealed_prospective_P0H4.csv") == \
        (L2 / "sealed_prospective_P0H4.csv.sha256").read_text().strip()
    rows = pd.read_csv(SERVED / "rows.csv", dtype={"province_code": str})
    P = pd.read_csv(L2 / "predictions_addendum3.csv", dtype={"province_code": str})
    P = P[P["lead"] == 1].assign(quarter=lambda d: d["q"].map(lambda q: f"{q // 4}-Q{q % 4 + 1}"))
    m = rows[rows["lead"] == 1].merge(P[["province_code", "quarter", "P0H4_p3"]], on=["province_code", "quarter"])
    assert len(m) == 70 and (m["probability"] - m["P0H4_p3"]).abs().max() < 1e-5
    assert {f"avail_{g}" for g in ("poverty", "news", "hunger_indicator")} <= set(rows.columns)
