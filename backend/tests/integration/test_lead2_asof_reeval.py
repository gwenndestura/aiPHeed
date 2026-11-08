"""
tests/integration/test_lead2_asof_reeval.py
-------------------------------------------
PROTOCOL_LEAD2_ASOF_REEVAL (frozen before scoring): every refresh province-month has one evidence class; September
2026 is not verified for any province; one cut-off per province-month (food and all items together) is applied to
training and evaluation rows; the day-10 construction is reproduced; the verified-timing results are labelled apart
from the provisional ones; the five owner-named groups are ablated chronologically; the sealed files, the served
model and the blocked re-score are unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
RES = LT / "out" / "asof_reeval.json"
SEALS = {"cr_prospective.csv": "dd293e2e36c87be26657b98c51184c5b8b1887bb0252ee4aa65a3dc3a1103da6",
         "cranc_prospective.csv": "07c99e569746cb255dbd748c8c0eed095fd31944be551272d0187c45b49e3986",
         "rizal_2027q1_companion.csv": "b1edb799f6f08158161164e8fab96c8ec3954cba91d8af36fe6392866753094a"}
pytestmark = pytest.mark.skipif(not RES.exists(), reason="as-of re-evaluation missing")


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text())


@pytest.fixture(scope="module")
def led():
    return pd.read_csv(LT / "data" / "psa_cpi_availability_ledger_20261029.csv", dtype=str)


def test_protocol_frozen_and_seals_unchanged(res):
    proto = hashlib.sha256((LT / "PROTOCOL_LEAD2_ASOF_REEVAL.md").read_bytes()).hexdigest()
    assert proto == (LT / "runner" / "ASOF_REEVAL_SHA256.txt").read_text().strip() == res["protocol_sha256"]
    for f, sha in SEALS.items():
        assert hashlib.sha256((LT / "sealed" / f).read_bytes()).hexdigest() == sha


def test_every_province_month_classified(led):
    assert len(led) == 180 and set(led["class"]) <= {"V1", "V2", "V3", "P", "N", "U"} and led["evidence"].notna().all()
    assert set(led["province"]) == {"Batangas", "Cavite", "Laguna", "Quezon", "Rizal"}
    v = led[led["class"].isin(["V1", "V2"])]
    assert (v["archive_release_date"] < v["issue_date"]).all() and v["archive_sha256"].notna().all()
    v1 = led[led["class"] == "V1"]
    assert (v1["archive_capture_pht"].str[:10] < v1["issue_date"]).all()
    assert not led["class"].eq("V3").any()                        # no exact food + all-items retrieval before an issue


def test_sept2026_not_verified_anywhere(led):
    s = led[led["reference_month"] == "2026-09"].set_index("province")["class"].to_dict()
    assert s == {"Batangas": "P", "Cavite": "P", "Laguna": "P", "Quezon": "N", "Rizal": "N"}


def test_one_cutoff_rule_and_day10_reproduced(res):
    C = pd.read_csv(LT / "out" / "asof_reeval_cutoffs.csv")
    assert (C["m_VER"] >= C["m0"]).all() and (C["m_VER"] <= C["m_PROV"]).all() and (C["m_PROV"] <= C["m0"] + 2).all()
    assert res["D10_reproduces_cr_stack_max_abs"] < 1e-9 and max(res["D10_reproduces_rows_max_abs"].values()) < 1e-6
    assert res["timing_label"]["CRANCVER"] == "verified" and res["timing_label"]["CRANCD10"].startswith("provisional")


def test_lead2_metrics_reported(res):
    for c, r in res["results"].items():
        m = r["2"]
        assert m["n"] == 65 and m["high"] == 17
        assert m["false_alarms"] + m["missed_high"] == round((1 - m["accuracy"]) * 65)
    assert set(res["baselines_lead2"]) == {"always_low", "persistence", "climatology"}


def test_five_groups_ablated(res):
    want = {"market_prices", "climate_stress", "employment_remittances", "poverty_vulnerability", "news_nlp"}
    for k in ("ablation_B0", "ablation_CRANCVER"):
        assert want <= set(res[k]) and "all_five_groups" in res[k]
        assert all("holm_p_hurts" in res[k][g]["2"] for g in want)


def test_lead2_not_reliable_under_verified_timing(res):
    r = res["results"]
    assert r["B0"]["2"]["failed"] == ["R6"]
    assert "R6" in r["CRVER"]["2"]["failed"] and "R6" in r["CRANCVER"]["2"]["failed"]
    assert r["CRANCD10"]["2"]["failed"] == [] and res["timing_label"]["CRANCD10"].startswith("provisional")
    assert res["adoption_vs_B0"]["CRANCD10"]["failed"] and res["adoption_vs_B0"]["CRANCPROV"]["failed"]
    assert abs(r["CRANCVER"]["2"]["vs_B0"]["diff"]) < abs(r["CRANCD10"]["2"]["vs_B0"]["diff"])
    p = res["parts_lead2"]["B0"]
    assert p["errors_price_part_wrong_only"] == p["errors"] and p["oracle_model_hunger_x_true_price"] > p["model_accuracy"]


def test_vintage_differences_recorded(res):
    v = res["leakage"]["cpi_vintage_archived_headline_vs_final_vintage"]
    assert v["pages_with_headline"] == 29 and v["equal_to_published_final_vintage"] == 26 and len(v["differ"]) == 3
    assert res["leakage"]["cpi_base_2012_vs_2018"]["evaluation_rows_affected"] == 0


def test_rescore_still_blocked():
    m = json.loads((LT / "out" / "release_dates_map.json").read_text())
    assert m["rescore_can_run"] is False


def test_served_model_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    assert CH1.evaluation()["seal_sha256"] == "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
