"""
tests/integration/test_lead2_cr_resolve.py
------------------------------------------
LEAD2_CR_RESOLVE: the protocol was frozen before scoring; P0H4-U and CR reproduce from committed inputs; CR's reported
figures hold; the one correction (CR-CAL) is scored with the unchanged rules and not adopted; timing checks hold; the
dashboard serves the evaluated P0H4 (province score = served probability, region = mean of provinces); served
artifacts unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
RES = LT / "out" / "cr_resolve.json"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
pytestmark = pytest.mark.skipif(not RES.exists(), reason="LEAD2_CR_RESOLVE results missing")


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text())


def test_protocol_frozen_and_used(res):
    want = (LT / "runner" / "CR_RESOLVE_SHA256.txt").read_text().strip()
    assert hashlib.sha256((LT / "PROTOCOL_LEAD2_CR_RESOLVE.md").read_bytes()).hexdigest() == want == res["protocol_sha256"]


def test_baselines_and_cr_reproduce(res):
    r = res["reproduction"]
    assert r["B0_max_abs"] < 1e-5 and r["CR_max_abs"] < 1e-5 and r["rows"] == 250
    cr, b0, p0 = (res["results"][c]["2"] for c in ("CR", "B0", "P0H4"))
    assert cr["tp_fp_fn_tn"] == [11, 7, 6, 41] and round(cr["accuracy"], 3) == 0.8
    assert round(cr["balanced_accuracy"], 3) == 0.751 and round(cr["recall"], 2) == 0.65 and round(cr["brier"], 3) == 0.147
    assert (cr["new_hits_vs_B0"], cr["new_false_alarms_vs_B0"]) == (2, 3)
    assert round(b0["brier"] - cr["brier"], 3) == 0.020
    rev = json.loads((LT / "out" / "cr_review.json").read_text())["brier_vs_B0"]
    assert round(rev["exact_sign_flip_p_one_sided"], 2) == 0.13
    assert b0["failed"] == ["R6"] and p0["failed"] == ["R3", "R5", "R6"] and cr["failed"] == []


def test_correction_scored_with_unchanged_rules_and_not_adopted(res):
    d = res["adoption_decision"]
    assert d["CR"] == {"adopted": False, "failed_rule": ["2_new_FA_le_new_hits"]}
    assert d["CRCAL"]["adopted"] is False and "2_new_FA_le_new_hits" in d["CRCAL"]["failed_rule"]
    assert res["results"]["CRCAL"]["2"]["failed"] == ["R6"] and res["results"]["CRCAL"]["max_reliable_lead"] == 1


def test_timing_and_alignment(res):
    t = res["timing"]
    assert t["target_quarter_equals_origin_plus_lead"] and t["cpi_newest_month_matches_day10_rule"]
    assert t["cpi_month_released_before_issue_under_rule"]
    assert all(t["input_audit"][k] for k in ("psa_month_before_issue_quarter", "sws_published_before_issue",
                                             "news_published_before_issue", "target_after_origin"))


@pytest.mark.parametrize("quarter", ["2026-Q4", "2027-Q1"])          # Lead 1 and Lead 2 of the 2026-10-01 issue
def test_dashboard_serves_the_evaluated_model(monkeypatch, quarter):
    monkeypatch.setenv("AIPHEED_LEAD2_MODEL", "thesis")
    monkeypatch.setenv("AIPHEED_NOW", "2026-10-20T09:00:00")
    for v in ("AIPHEED_CH1_ENGINE", "AIPHEED_SWS_REISSUE", "AIPHEED_SWS_REISSUE_DIR"):
        monkeypatch.delenv(v, raising=False)
    from app.ml.inference import ch1_system as CH1
    from app.services import dashboard as D
    assert CH1.evaluation()["seal_sha256"] == SERVED_SEAL
    ps = D.province_summary(quarter)
    rows = CH1.rows()
    assert len(ps) == 5
    for p in ps:
        r = rows[(p["provinceCode"], quarter)]
        assert abs(p["riskScoreExact"] - float(r["probability"])) < 1e-6 and r["seal_sha256"] == SERVED_SEAL
        assert "CR" not in r["model"]
    region = D.region_forecast(quarter)
    assert abs(region["riskScoreExact"] - round(sum(p["riskScoreExact"] for p in ps) / 5, 4)) < 1e-9
