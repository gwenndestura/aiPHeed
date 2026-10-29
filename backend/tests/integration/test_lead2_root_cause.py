"""
tests/integration/test_lead2_root_cause.py
------------------------------------------
LEAD2_ROOT_CAUSE: the protocol and the release-date addendum were frozen; the row-level error analysis confirms the
hunger cap from the data; the three corrections are scored with the unchanged rules and none is eligible; CR-ANC's
release-day sensitivity is reported, not adopted; the CR and CR-ANC prospective seals are intact; served model unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
RES, ERR = LT / "out" / "root_cause.json", LT / "out" / "rootcause_errors.csv"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
pytestmark = pytest.mark.skipif(not RES.exists(), reason="LEAD2_ROOT_CAUSE results missing")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text())


def test_protocol_and_addendum_frozen(res):
    assert sha(LT / "PROTOCOL_LEAD2_ROOT_CAUSE.md") == (LT / "runner" / "ROOT_CAUSE_SHA256.txt").read_text().strip() == res["protocol_sha256"]
    assert sha(LT / "ADDENDUM_ROOT_CAUSE_RELEASE_DATES.md") == (LT / "runner" / "ROOT_CAUSE_ADDENDUM_SHA256.txt").read_text().strip()


def test_error_analysis_confirms_hunger_cap_from_data():
    e = pd.read_csv(ERR)
    cr = e[e["candidate"] == "CR"]
    assert len(cr) == 13
    cap = cr[cr["pattern"] == "hunger_cap"]
    assert len(cap) == 3 and set(cap["target_quarter"]) == {"2023-Q4"}
    assert (cap["h_last_at_reissue"] == 11.3).all() and (cap["pi_hunger"] == 0.5).all() and (cap["H_realised"] > 11.3).all()
    # 7 false alarms = 5 price reversals + 2 model behaviour (the frozen protocol's "6 of 7" is an erratum)
    assert (cr["pattern"] == "price_fell_after_issue").sum() == 5 and (cr["pattern"] == "model_behaviour").sum() == 2
    assert set(cr["evidence"]) <= {"supported", "hypothesis"}


def test_corrections_scored_with_unchanged_rules_none_eligible(res):
    assert res["anc_reproduces_features_v2_lead1_max_abs"] < 1e-6
    a = res["adoption"]
    assert a["CRANC"]["failed_rule"] == ["2_L2_precision_within_0.02", "2_new_FA_le_new_hits"]
    assert a["CRANC"]["lead1_R"] == [] and a["CRANC"]["lead2_R"] == []
    assert not any(x["eligible"] for x in a.values())
    assert res["decision"]["eligible"] == [] and res["decision"]["research_candidate"] == "CR (unchanged)"
    m = res["results"]["CRANC"]["2"]
    assert m["tp_fp_fn_tn"] == [12, 8, 5, 40] and round(m["brier"], 4) == 0.1315
    assert res["results"]["CRT"]["2"]["tp_fp_fn_tn"][1] == 18                    # threshold correction adds false alarms
    assert "R3" in res["results"]["CRWCAL"]["1"]["failed"]


def test_release_day_sensitivity_is_reported_not_adopted(res):
    s = res["CRANC_release_day_sensitivity"]
    assert s["15"]["2"]["failed"] == ["R6"]
    assert s["20"]["2"]["failed"] == [] and s["20"]["failed_rule"] == []           # passes, but chosen after scoring
    assert res["decision"]["research_candidate"] == "CR (unchanged)"


def test_prospective_seals_intact():
    for name in ("cr_prospective", "cranc_prospective"):
        s = json.loads((LT / "sealed" / f"{name}.sha256").read_text())
        assert sha(LT / "sealed" / s["file"]) == s["sha256"]
        assert s["targets"] == ["2026-Q4", "2027-Q1", "2027-Q2", "2027-Q3"]
    assert json.loads((LT / "sealed" / "cr_prospective.sha256").read_text())["sha256"].startswith("dd293e2e")


def test_served_model_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    for v in ("AIPHEED_CH1_ENGINE", "AIPHEED_SWS_REISSUE"):
        monkeypatch.delenv(v, raising=False)
    assert CH1.evaluation()["seal_sha256"] == SERVED_SEAL and CH1.reliable_lead() == 1
