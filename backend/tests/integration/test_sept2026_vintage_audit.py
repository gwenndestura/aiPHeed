"""
tests/integration/test_sept2026_vintage_audit.py
------------------------------------------------
September 2026 CPI vintage audit of the sealed CR and CR-ANC forecasts: the seals are untouched and reproduced; every
input is classified; food inputs are value-matched to the pre-issue OpenSTAT snapshot; Rizal and Quezon all-items
inputs are same-day unresolved and no input is classified as available without evidence; under the food/all-items
split construction only the Rizal Lead-2 call changes (superseded as a timing verdict by test_sept2026_asof_rule.py);
served model unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
RES = LT / "out" / "sept2026_vintage_audit.json"
SEALS = {"cr_prospective.csv": "dd293e2e36c87be26657b98c51184c5b8b1887bb0252ee4aa65a3dc3a1103da6",
         "cranc_prospective.csv": "07c99e569746cb255dbd748c8c0eed095fd31944be551272d0187c45b49e3986"}
pytestmark = pytest.mark.skipif(not RES.exists(), reason="September 2026 vintage audit missing")


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text())


def test_seals_untouched_and_reproduced(res):
    for f, sha in SEALS.items():
        assert hashlib.sha256((LT / "sealed" / f).read_bytes()).hexdigest() == sha
    assert all(s["reproduced_max_abs"] < 1e-5 for s in res["seals"].values())


def test_every_input_classified_with_evidence():
    I = pd.read_csv(LT / "out" / "sept2026_vintage_inputs.csv")
    assert len(I) == 45 + 75 and I["evidence"].notna().all()
    food = I[I["feature"].isin(["A1_food", "A_mom", "A1_food_anc"])]
    assert (food["classification"] == "demonstrably available before issue").all()
    gap = I[I["feature"].isin(["A1_gap", "A1_gap_anc"])]
    assert (gap.loc[gap["province"].isin(["Rizal", "Quezon"]), "classification"] == "same-day timing unresolved").all()
    owner = gap.loc[gap["province"].isin(["Cavite", "Laguna", "Batangas"]), "classification"]
    assert owner.str.contains("owner-reported").all()                       # never upgraded to "demonstrably" without sources
    assert not I["classification"].str.contains("released after issue").any()


def test_provenance_records_and_pre_issue_food_snapshot(res):
    assert res["food_pre_issue_source"].startswith("2026-10-14T15:34:40Z")
    assert "2026-10-15T09:18:32Z" in res["all_items_first_seen"]


def test_split_construction_changes_only_rizal_lead2(res):
    for s in res["seals"].values():
        changed = [(r["province"], r["lead"]) for r in s["sensitivity"] if r["changed_class"]]
        assert changed == [("Rizal", 2)]


def test_served_model_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.evaluation()["seal_sha256"] == "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"


def test_rizal_companion_sealed_alongside_untouched_originals(res):
    comp = LT / "sealed" / "rizal_2027q1_companion.csv"
    man = json.loads((LT / "sealed" / "rizal_2027q1_companion.sha256").read_text())
    assert hashlib.sha256(comp.read_bytes()).hexdigest() == man["sha256"]
    assert man["originals_unchanged"] == SEALS and man["latest_outcome_quarter_at_seal"] < "2027-Q1"
    C = pd.read_csv(comp, dtype={"province_code": str})
    assert len(C) == 2 and set(C["companion_of"]) == {"CR", "CR-ANC"}
    assert (C["province"] == "Rizal").all() and (C["target_quarter"] == "2027-Q1").all() and (C["lead"] == 2).all()
    assert (C["cpi_through"] == "food 2026-09, all items 2026-08").all()
    assert (C["class"] == "HIGH").all() and (C["original_class"] == "LOW").all()
    for r in C.itertuples():                                            # matches the audit's diagnostic re-prediction
        sens = [s for s in res["seals"][r.companion_of]["sensitivity"] if s["province"] == "Rizal" and s["lead"] == 2][0]
        assert abs(r.probability - sens["probability_all_items_aug"]) < 1e-5 and r.original_class == sens["sealed_class"]
