"""Tests for FINAL_OBJECTIVE_ACHIEVEMENT (FINAL_FORECASTING_PROTOCOL.md): frozen protocol, leakage audit, the verified
accuracy ceiling and the seal, read from the experiment's outputs."""
import hashlib
import json
from pathlib import Path

import pytest

EXP = Path(__file__).resolve().parents[3] / "aipheed-backend-aligned" / "experiments" / "FINAL_OBJECTIVE_ACHIEVEMENT"
OUT = EXP / "out"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def test_protocol_hash_unchanged():
    assert _sha(EXP / "FINAL_FORECASTING_PROTOCOL.md") == (EXP / "runner" / "PROTOCOL_SHA256.txt").read_text().strip()


def test_leakage_audit_passed_with_negative_control():
    a = json.loads((OUT / "leakage_audit.json").read_text())
    assert a["passed"] and a["negative_control_changed"] and len(a["origins"]) == 10


def test_ceiling_simulation_was_validated_before_use():
    v = json.loads((OUT / "results_verify.json").read_text())
    assert v["V2_ceiling_validated"] is (v["V2_share_inside"] >= 0.8)
    assert all(c["inside"] for c in v["V2_check_cells"]) == (v["V2_share_inside"] == 1.0)
    assert 0.06 <= v["V3_null_bootstrap"]["rejection_rate_at_0.10"] <= 0.14
    assert max(h["bayes"]["mean"] for h in v["V2_simulated"].values()) < 0.75


def test_reported_verdict_matches_results():
    r = json.loads((OUT / "results_primary.json").read_text())
    assert r["max_reliable_lead"] is None
    assert not any(r["FIL_OA"][k]["pass"] for k in r["FIL_OA"])


def test_seal_hash():
    p = OUT / "sealed_prospective.csv"
    assert _sha(p) == (OUT / "sealed_prospective.csv.sha256").read_text().strip()


@pytest.mark.parametrize("lead", ["0", "1", "2", "3", "4"])
def test_no_lead_reaches_the_target(lead):
    r = json.loads((OUT / "results_primary.json").read_text())
    assert r["FIL_OA"][lead]["metrics"]["accuracy"] < 0.75
