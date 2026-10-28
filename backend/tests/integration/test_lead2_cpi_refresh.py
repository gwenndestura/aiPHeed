"""
tests/integration/test_lead2_cpi_refresh.py
-------------------------------------------
LEAD2_CPI_REFRESH: the refreshed CPI columns reproduce the stack at the original cut-off and read no CPI month after
their own cut-off (future perturbation); the protocol was frozen before scoring; the frozen adoption rule is applied
exactly (CR passes R1-R7 at Leads 1-2 but is not adopted); the prospective seal is intact; served model unchanged.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[3]
LT = ROOT / "aipheed-backend-aligned" / "experiments" / "LEAD2_FIVE_TRIGGER"
RES = LT / "out" / "cpi_refresh.json"
SERVED_SEAL = "a498b5ef3fd9143348737a3a4464ba71c3c728fff48efa5f11d4c544644fbee1"
pytestmark = pytest.mark.skipif(not RES.exists(), reason="LEAD2_CPI_REFRESH results missing")


@pytest.fixture(scope="module")
def res():
    return json.loads(RES.read_text())


@pytest.fixture(scope="module")
def CF():
    sys.path.insert(0, str(LT / "runner"))
    import cpi_refresh_features
    return cpi_refresh_features


def test_protocol_frozen_and_used(res):
    want = (LT / "runner" / "CPI_REFRESH_SHA256.txt").read_text().strip()
    assert hashlib.sha256((LT / "PROTOCOL_LEAD2_CPI_REFRESH.md").read_bytes()).hexdigest() == want == res["protocol_sha256"]


def test_refreshed_features_reproduce_and_respect_the_release_rule(CF):
    a = json.loads((LT / "out" / "cpi_refresh_features_audit.json").read_text())
    assert a["reproduce_A1_food_max_abs"] < 1e-6 and a["reproduce_A1_gap_max_abs"] < 1e-6 and a["reproduce_A_mom_max_abs"] < 1e-6
    assert set(a["extra_months"]) <= {"1", "2"}
    # day-10 rule: month m is usable only when day 10 of month m+1 precedes the issue date
    m0 = 2026 * 12 + 7                                                     # 2026-08
    assert CF.newest_month("2026-10-15", m0) == m0 + 1 and CF.newest_month("2026-10-10", m0) == m0
    assert CF.newest_month("2026-10-11", m0) == m0 + 1 and CF.newest_month("2026-11-11", m0) == m0 + 2


def test_refreshed_features_read_no_later_cpi_month(CF):
    d, _ = CF.E.data()
    th = CF.L.e40_spec()
    R = pd.read_csv(LT / "data" / "cpi_refresh.csv", dtype={"province_code": str})
    sample = R.groupby("t").head(2)
    for x in sample.itertuples():
        idx = d.idx.copy()
        idx.loc[idx["ym"] > x.m0r, "index"] = 999.0                        # perturb every month after the cut-off
        dp = dataclasses.replace(d, idx=idx)
        got = CF.cols(dp, th, int(x.t), int(x.lead), x.province_code, int(x.m0r))
        want = (x.A1_food_r, x.A1_gap_r, x.A_mom_r)
        assert all(abs(g - w) < 1e-6 or (pd.isna(g) and pd.isna(w)) for g, w in zip(got, want)), x


def test_rule_applied_exactly_cr_not_adopted(res):
    a = res["adoption"]
    assert a["adopted"] is all(a["rule"].values()) is False
    assert [k for k, v in a["rule"].items() if not v] == ["2_new_FA_le_new_hits"]
    assert a["FINAL"] == "B0" and a["lead2_failed"] == ["R6"] and a["max_reliable_lead"] == 1
    assert a["CR_lead1_failed"] == [] and a["CR_lead2_failed"] == []
    m = res["cands"]["CR"]["leads"]["2"]["metrics"]
    assert (m["tp"], m["fp"], m["fn"], m["tn"]) == (11, 7, 6, 41)
    b = res["cands"]["B0"]["leads"]["2"]["metrics"]
    assert (b["tp"], b["fp"]) == (10, 6)                                   # baseline reproduced


def test_prospective_seal_intact():
    s = json.loads((LT / "sealed" / "cr_prospective.sha256").read_text())
    assert hashlib.sha256((LT / "sealed" / s["file"]).read_bytes()).hexdigest() == s["sha256"]
    P = pd.read_csv(LT / "sealed" / s["file"])
    assert len(P) == 20 and P["target_quarter"].min() == "2026-Q4"
    assert set(P.loc[P["lead"] >= 2, "issue_date"]) == {"2026-10-15"} and set(P.loc[P["lead"] == 1, "issue_date"]) == {"2026-10-01"}


def test_served_model_and_seal_unchanged(monkeypatch):
    from app.ml.inference import ch1_system as CH1
    monkeypatch.delenv("AIPHEED_CH1_ENGINE", raising=False)
    monkeypatch.delenv("AIPHEED_SWS_REISSUE", raising=False)
    assert CH1.data_dir().name == "ch1_engine" and CH1.evaluation()["seal_sha256"] == SERVED_SEAL
    assert not any("CR" in (r.get("model") or "") for r in CH1.rows().values())
