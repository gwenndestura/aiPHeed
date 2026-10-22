"""
tests/integration/test_e98_acceptance_gate.py
---------------------------------------------
E98: tied to the frozen protocol; the direct-target arms train only on outcomes posted before each issue date; no direct
arm passes rule D, so FIRI v2 stays the best defensible regional index and no probability is offered; E97 reproduces
exactly and the served artifacts are unchanged since E97 (version identity); the release gate is recorded as FAILED.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

E98 = Path("..") / "aipheed-backend-aligned" / "experiments" / "E98_Acceptance_Gate"


def _latest(suffix: str, name: str) -> dict:
    d = sorted(p for p in (E98 / "runs").iterdir() if p.is_dir() and p.name.endswith(suffix))[-1]
    return json.loads((d / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def direct():
    return _latest("_direct", "direct_target.json")


@pytest.fixture(scope="module")
def repro():
    return _latest("_diag_repro", "diagnose_and_reproduce.json")


def test_protocol(direct, repro):
    sha = hashlib.sha256((E98 / "PROTOCOL.md").read_bytes()).hexdigest()
    assert (E98 / "PROTOCOL.sha256").read_text().split()[0] == sha == direct["protocol_sha256"] == repro["protocol_sha256"]


def test_direct_arms_leakage_free_and_decision(direct):
    for lead in ("1", "2"):
        r = direct["leads"][lead]
        assert r["leakage_audit_ok"]
        for arm, rows in r["training_audit"].items():
            for x in rows:
                assert x["latest_pair_target"] is None or x["latest_pair_target"] < x["target"]
    d = direct["decision"]
    assert d["passing_rule_D"] == [] and d["best_defensible_regional_model"] == "FIRI"
    assert d["regional_probability_offered"] is False
    m2 = direct["leads"]["2"]["metrics"]
    assert m2["FIRI"]["accuracy"] == pytest.approx(14 / 15) and m2["H1"]["accuracy"] == pytest.approx(10 / 15)
    assert direct["leads"]["1"]["metrics"]["FIRI"]["accuracy"] == pytest.approx(14 / 16)


def test_reproduction_and_version_identity(repro):
    r = repro["R"]
    assert r["firi"]["identical_excluding_stamp"] and r["obj4"]["identical_excluding_stamp"]
    assert r["version_identity"] and r["changed_since_e97"] == []
    # E99 changed these three serving files on purpose (display wording only; release_candidate_manifest.json)
    later = {"app/ml/inference/thesis_system.py", "app/services/dashboard.py", "app/quarterly/lgu_audit.py"}
    for p, h in r["served_artifacts"].items():
        if p not in later:
            assert hashlib.sha256(Path(p).read_bytes()).hexdigest() == h, p


def test_psa_diagnostic(repro):
    p = repro["P"]
    assert p["eligible_quarters"][0] == "2024-Q4" and len(p["eligible_quarters"]) == 6


def test_release_gate_recorded_failed():
    g = json.loads((E98 / "release_gate.json").read_text(encoding="utf-8"))
    assert g["deploy"] is False
    failed = {c["id"] for c in g["criteria"] if c["status"] != "PASS"}
    assert {"G4", "G9"} <= failed
