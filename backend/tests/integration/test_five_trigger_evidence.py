"""
tests/integration/test_five_trigger_evidence.py
-----------------------------------------------
LEAD2_FIVE_TRIGGER: the dashboard's five trigger groups (Market/Prices, Climate, Employment, Fish production, OFW
remittances) each carry their measured held-out contribution, generated from the ablation export, at province and
region scope; the served probabilities are unchanged.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml.inference import ch1_system as CH1

client = TestClient(app)
ROOT = Path(__file__).resolve().parents[3]
ABL = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER" / "out" / "ablation.json"
FIVE = ["market", "climate", "employment", "fish_kill", "ofw_remittance"]
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
pytestmark = pytest.mark.skipif(not CH1.TRIGGER_EVIDENCE.exists(), reason="trigger evidence export missing")


@pytest.fixture
def thesis(monkeypatch):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    return monkeypatch


def test_the_five_groups_are_the_dashboard_groups_and_match_the_ablation():
    ev = CH1.trigger_evidence()
    assert set(ev) == set(FIVE) == set(CH1.SHOWN_GROUPS)
    a = json.loads(ABL.read_text())
    for g in FIVE:
        assert ev[g]["class"] == a["classification"][g]["class"]
        for k in ("1", "2"):
            assert ev[g]["brier_change_without"][k] == a["leads"][k][g]["loo_t43c"]
        assert ev[g]["sentence"].startswith(("Tested on past quarters", "Tests on past quarters"))


def test_market_is_measurable_and_no_group_is_given_an_unsupported_effect():
    ev = CH1.trigger_evidence()
    # Market: confirmed at Lead 1 (Holm p < .001), not at Lead 2 (Holm p .06)
    assert ev["market"]["sentence"].endswith("Its contribution is measurable for the current quarter (Lead 1).")
    assert "the next quarter (Lead 2), a difference not confirmed after correcting for multiple tests" in ev["market"]["sentence"]
    for g in ("fish_kill", "ofw_remittance"):
        assert "could not be established" in ev[g]["sentence"]
    assert "not established" in ev["climate"]["sentence"]
    for g in FIVE:
        if "measurable" in ev[g]["sentence"]:                                       # only with a Holm-confirmed lead
            assert any(ev[g]["brier_change_without"][k].get("holm_p_hurts", 1) < .05 for k in ("1", "2")), g


EMPLOYMENT_WORDING = ("Tests on past quarters did not establish an independent contribution from employment-related "
                      "indicators at Lead 1 or Lead 2 after correcting for multiple comparisons. Employment-related "
                      "indicators are included in the LightGBM model. However, their independent contribution to "
                      "forecasting has not been established by the current evaluation.")


def test_employment_card_does_not_claim_a_measurable_contribution():
    # CR_REVIEW 20.8: employment's leave-group-out gain is not established after Holm correction (Lead 1 p .11)
    s = CH1.trigger_evidence()["employment"]["sentence"]
    assert s == EMPLOYMENT_WORDING
    assert "measurable" not in s and "made the forecasts" not in s                # no unconfirmed change stated as a result
    assert "no predictive value" not in s
    assert "E1" in CH1.trigger_evidence()["employment"]["columns"]                 # still a model input
    assert CH1.plain_evidence("PH040300000", "2026-Q4", "employment").endswith(EMPLOYMENT_WORDING)


NOT_CONFIRMED = "a difference not confirmed after correcting for multiple tests"
CARDS = {
    "market": "Tested on past quarters: leaving this group out made the forecasts worse for the current quarter (Lead 1) "
              f"and made the forecasts worse for the next quarter (Lead 2), {NOT_CONFIRMED}. Its contribution is "
              "measurable for the current quarter (Lead 1).",
    "climate": "Tested on past quarters: leaving this group out made a difference too small to confirm for the current "
               f"quarter (Lead 1) and made the forecasts slightly better for the next quarter (Lead 2), {NOT_CONFIRMED}. "
               "Its contribution is not established after correcting for multiple tests.",
    "employment": EMPLOYMENT_WORDING,
    "fish_kill": "Tested on past quarters: leaving this group out made a difference too small to confirm for the current "
                 "quarter (Lead 1) and made a difference too small to confirm for the next quarter (Lead 2). Its "
                 "contribution could not be established with the data available.",
    "ofw_remittance": "Tested on past quarters: leaving this group out made no meaningful difference for the current "
                      "quarter (Lead 1) and made no meaningful difference for the next quarter (Lead 2). Its contribution "
                      "could not be established with the data available.",
}


def test_every_card_states_only_what_the_corrected_tests_support():
    ev = CH1.trigger_evidence()
    assert {g: ev[g]["sentence"] for g in FIVE} == CARDS
    # climate: removal helped at Lead 2 only on an uncorrected interval (the registered test is one-sided, "hurts")
    assert ev["climate"]["brier_change_without"]["2"]["ci90"][1] < 0 and "noise" not in ev["climate"]["sentence"]
    for g in FIVE:
        for k in ("1", "2"):
            x = ev[g]["brier_change_without"][k]
            if max(abs(x["diff"]), *map(abs, x["ci90"])) >= .001:              # interval not inside the floor
                assert f"no meaningful difference for {X_PERIOD[k]}" not in ev[g]["sentence"], (g, k)


X_PERIOD = {"1": "the current quarter (Lead 1)", "2": "the next quarter (Lead 2)"}


def test_regenerating_the_evidence_keeps_the_approved_wording():
    import sys
    sys.path.insert(0, str(ABL.parents[1] / "runner"))
    import export_evidence as X
    assert X.APPROVED["employment"] == EMPLOYMENT_WORDING
    new, cur = X.build(), json.loads(CH1.TRIGGER_EVIDENCE.read_text(encoding="utf-8"))
    assert json.loads(json.dumps(new, default=float)) == cur                       # the served file is the generator's output
    for g in FIVE:
        assert "Its contribution is measurable." not in new["groups"][g]["sentence"], g
    # employment never regains the old claim, even if its Lead-1 interval were confirmed only before correction
    r = json.loads(ABL.read_text())["leads"]
    r = json.loads(json.dumps(r))
    r["1"]["employment"]["loo_t43c"]["holm_p_hurts"] = 0.06
    assert X.sentence("employment", r) == EMPLOYMENT_WORDING


def test_api_cards_carry_the_tested_contribution_at_both_scopes(thesis):
    assert CH1.evaluation()["seal_sha256"] == SERVED_SEAL
    for scope, id_ in (("province", "quezon"), ("region", "calabarzon")):
        r = client.get("/api/v1/explainability", params={"scope": scope, "id": id_, "quarter": "2027-Q1"})
        assert r.status_code == 200, r.text[:300]
        trig = {t["key"]: t for t in r.json()["triggers"]}
        assert set(FIVE) <= set(trig)
        for g in FIVE:
            assert CH1.trigger_evidence()[g]["sentence"] in (trig[g].get("plainEvidence") or ""), (scope, g)
