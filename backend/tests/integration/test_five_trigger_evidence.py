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
        assert ev[g]["sentence"].startswith("Tested on past quarters")


def test_market_is_measurable_and_no_group_is_given_an_unsupported_effect():
    ev = CH1.trigger_evidence()
    assert "measurable" in ev["market"]["sentence"]
    for g in ("fish_kill", "ofw_remittance"):
        assert "could not be established" in ev[g]["sentence"]
    assert "not established" in ev["climate"]["sentence"]


def test_api_cards_carry_the_tested_contribution_at_both_scopes(thesis):
    assert CH1.evaluation()["seal_sha256"] == SERVED_SEAL
    for scope, id_ in (("province", "quezon"), ("region", "calabarzon")):
        r = client.get("/api/v1/explainability", params={"scope": scope, "id": id_, "quarter": "2027-Q1"})
        assert r.status_code == 200, r.text[:300]
        trig = {t["key"]: t for t in r.json()["triggers"]}
        assert set(FIVE) <= set(trig)
        for g in FIVE:
            assert CH1.trigger_evidence()[g]["sentence"] in (trig[g].get("plainEvidence") or ""), (scope, g)
