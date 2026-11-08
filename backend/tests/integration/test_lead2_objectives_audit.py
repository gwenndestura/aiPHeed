"""
tests/integration/test_lead2_objectives_audit.py
------------------------------------------------
LEAD2_OBJECTIVES_AUDIT: the Lead-2 evaluation reproduces from committed inputs; the served P0H4 fails the mandatory
Lead-2 criteria at every cut; no scored candidate is adopted; the label's provincial variation comes from the price
condition only; the maximum reliable served lead is 1; served artifacts unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
AUD = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER" / "out" / "lead2_objectives_audit.json"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
pytestmark = pytest.mark.skipif(not AUD.exists(), reason="LEAD2_OBJECTIVES_AUDIT results missing")


@pytest.fixture(scope="module")
def aud():
    return json.loads(AUD.read_text())


def test_evaluation_reproduces_from_committed_inputs(aud):
    r = aud["reproduction"]
    assert r["B0_price_max_abs"] < 1e-6 and r["CR_price_max_abs"] < 1e-6 and r["rows"] == 250
    assert r["served_export_lead1_rows_matched"] == 70 and r["served_vs_P0H4_prob_max_abs"] < 1e-9
    assert r["served_observed_equals_label"] is True


def test_served_lead2_fails_mandatory_criteria(aud):
    m = aud["lead2"]["P0H4"]
    a = m["all"]
    assert round(a["accuracy"], 3) == 0.769 and a["tp_fp_fn_tn"] == [6, 4, 11, 44]
    assert m["uncertainty"]["failed_R1_R7"] == ["R3", "R5", "R6"]
    assert a["accuracy"] - aud["baselines_lead2"]["always_low_accuracy"] < 0.035     # two rows above always-LOW
    assert m["dev"]["tp_fp_fn_tn"][0] == 1 and m["dev"]["tp_fp_fn_tn"][2] == 10       # 1 of 11 DEV HIGH cases caught
    assert m["uncertainty"]["accuracy_ci90_quarter_block"][0] < 0.75
    assert not any(v["precision"] >= .6 and v["recall_high"] >= .6 for v in m["threshold_sweep_diagnostic"].values())


def test_no_scored_candidate_is_adopted(aud):
    c = aud["candidates_lead2"]
    assert len({(x["experiment"], x["candidate"]) for x in c}) == len(c) >= 12
    assert not any(x["adopted"] for x in c)
    assert [x["candidate"] for x in c if x["failed"] == []] == ["CR"]               # the only R1-R7 pass, not adopted


def test_target_province_variation_is_price_only(aud):
    t = aud["target_validity"]
    assert t["hunger_component_identical_across_provinces_every_quarter"] is True
    assert (t["quarters_with_hunger_condition"], t["quarters"]) == (11, 13)


def test_served_reliable_horizon_and_artifacts_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    from app.ml.inference import sws_reissue as RI
    for v in ("AIPHEED_SWS_REISSUE", "AIPHEED_SWS_REISSUE_DIR", "AIPHEED_CH1_ENGINE"):
        monkeypatch.delenv(v, raising=False)
    assert CH1.evaluation()["seal_sha256"] == SERVED_SEAL and CH1.reliable_lead() == 1 and not RI.enabled()
