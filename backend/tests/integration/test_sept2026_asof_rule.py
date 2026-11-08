"""
tests/integration/test_sept2026_asof_rule.py
--------------------------------------------
September 2026 as-of audit (ASOF_RULE_SEPT2026.md, addendum rule 2 restated): the rule file keeps its hash; the CPI the
model reads is decoded from the committed OpenSTAT responses with no mismatch; the 2026-10-14 snapshot holds food only;
the gap trace reproduces the sealed features; one cut-off per province-month is applied to every province and lead;
Rizal 2027-Q1 Lead 2 is LOW under every consistent cut-off and HIGH only under the food/all-items split; the companion
is a diagnostic record, not the counted forecast; seals, served model and the blocked re-score are unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
RES = LT / "out" / "sept2026_asof_rule.json"
SEALS = {"cr_prospective.csv": "dd293e2e36c87be26657b98c51184c5b8b1887bb0252ee4aa65a3dc3a1103da6",
         "cranc_prospective.csv": "07c99e569746cb255dbd748c8c0eed095fd31944be551272d0187c45b49e3986",
         "rizal_2027q1_companion.csv": "b1edb799f6f08158161164e8fab96c8ec3954cba91d8af36fe6392866753094a"}
pytestmark = pytest.mark.skipif(not RES.exists(), reason="September 2026 as-of audit missing")


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text())


@pytest.fixture(scope="module")
def var():
    return pd.read_csv(LT / "out" / "sept2026_asof_variants.csv")


def test_rule_and_seals_unchanged(res):
    rule = hashlib.sha256((LT / "ASOF_RULE_SEPT2026.md").read_bytes()).hexdigest()
    assert rule == (LT / "runner" / "ASOF_RULE_SHA256.txt").read_text().strip() == res["rule_file_sha256"]
    for f, sha in SEALS.items():
        assert hashlib.sha256((LT / "sealed" / f).read_bytes()).hexdigest() == sha


def test_source_chain_and_series_checked_separately(res):
    s = res["sources"]
    assert s["index_table"]["mismatches"] == 0 and s["index_table"]["cells_matched_to_model_csv"] == 690
    assert s["index_table"]["retrieved_at_utc"] == "2026-10-15T09:54:05Z"
    assert s["yoy_food_only"]["commodities_requested"] == ["2"]              # the 10-14 snapshot holds no all-items cell
    assert s["yoy_food_only"]["retrieved_at_utc"].startswith("2026-10-14T15:34:40")
    assert s["yoy_all_items_and_food"]["retrieved_at_utc"] == "2026-10-15T09:18:32Z"
    C = pd.DataFrame(res["checks"])
    assert (C["implied_yoy"] - C["yoy_E40_20261015"]).abs().max() <= 0.051
    food = C[C["series"] == "food"]
    assert (food["implied_yoy"] - food["yoy_E31_20261014"]).abs().max() <= 0.051
    assert C.loc[C["series"] == "all_items", "yoy_E31_20261014"].isna().all()


def test_gap_trace_reproduces_sealed_inputs():
    tr = pd.read_csv(LT / "out" / "sept2026_gap_trace.csv")
    inp = pd.read_csv(LT / "out" / "sept2026_vintage_inputs.csv")
    sealed = tr[tr["cutoff"] == "sealed Sep/Sep"].merge(inp[inp["seal"] == "CR-ANC"], on=["province", "lead", "feature"])
    assert len(sealed) == 30 and (sealed["value"] - sealed["value_used"]).abs().max() < 1e-5
    assert set(tr["cutoff"]) == {"sealed Sep/Sep", "companion Sep food / Aug all", "rule Aug/Aug"}
    assert tr["inputs"].str.contains("food\\[2026-").all() and tr["formula"].notna().all()


def test_one_cutoff_applied_everywhere(var):
    assert len(var) == 2 * 5 * 15 and set(var["lead"]) == {2, 3, 4}
    for v in ("V0_sealed_Sep", "V2_rule_owner_dates", "V3_rule_unverified_Aug"):
        assert not var.loc[var["variant"] == v, "mixed_vintage_gap"].any()
    assert (var.loc[var["variant"] == "V3_rule_unverified_Aug", ["cpi_food_features", "cpi_gap_food", "cpi_gap_all_items"]] == "2026-08").all().all()
    v0 = var[var["variant"] == "V0_sealed_Sep"]
    assert (v0["class"] == v0["sealed_class"]).all()


def test_rizal_lead2_low_under_every_consistent_cutoff(res, var):
    rz = var[(var["province"] == "Rizal") & (var["lead"] == 2)]
    for v, cls in {"V0_sealed_Sep": "LOW", "V2_rule_owner_dates": "LOW", "V3_rule_unverified_Aug": "LOW",
                   "V4_split_food_Sep_gap_Aug": "LOW", "V1_companion_split": "HIGH"}.items():
        assert (rz.loc[rz["variant"] == v, "class"] == cls).all(), v
    assert res["companion_reproduced_max_abs"] < 1e-5


def test_timing_dependent_rows(var):
    k = ["seal", "province", "lead"]
    c = var.pivot_table(index=k, columns="variant", values="class", aggfunc="first")
    dep = c[c["V0_sealed_Sep"] != c["V3_rule_unverified_Aug"]]
    assert len(dep) == 9 and (dep["V0_sealed_Sep"] == "HIGH").all()
    owner = c[c["V0_sealed_Sep"] != c["V2_rule_owner_dates"]].index.tolist()
    assert sorted(owner) == [("CR", "Rizal", 3), ("CR", "Rizal", 4), ("CR-ANC", "Rizal", 4)]


def test_companion_not_counted_and_rescore_blocked():
    rep = (LT / "LEAD2_SEPT2026_VINTAGE_AND_CAUSES_REPORT.md").read_text(encoding="utf-8")
    assert "Scoring rule (withdrawn 2026-10-29)" in rep and "It is **not** the counted forecast" in rep
    err = (LT / "ERRATUM_ROOT_CAUSE_RELEASE_DATES.md").read_text(encoding="utf-8")
    assert "## E5." in err and "## E6." in err
    m = json.loads((LT / "out" / "release_dates_map.json").read_text())
    assert m["rescore_can_run"] is False
    v2 = pd.read_csv(LT / "data" / "psa_cpi_release_dates_TO_FILL_v2.csv", dtype=str)
    assert (v2.loc[v2["reference_month"] == "2026-09", "status"] == "unresolved").all()


def test_served_model_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.evaluation()["seal_sha256"] == "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
