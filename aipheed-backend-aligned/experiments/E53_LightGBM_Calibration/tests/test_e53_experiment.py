"""E53 experiment checks: protocol and addendum frozen before their scores, run 1 reproduces E52 and repeats
byte-identically, decisions follow the frozen rules, no frozen file for an arm that failed, prospective status pending.

    backend/venv/Scripts/python.exe -B -m pytest -q -p no:cacheprovider tests
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

E53 = Path(__file__).resolve().parents[1]
RUN1, REPEAT, I2 = (E53 / "runs" / r for r in ("20261017T140057Z", "20261017T140524Z", "i2_20261017T140757Z"))
E52 = E53.parent / "E52_Objectives_Acceptance"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def test_protocol_and_addendum_unchanged():
    assert _sha(E53 / "PROTOCOL.md") == (E53 / "runner" / "PROTOCOL_SHA256.txt").read_text().split()[0]
    assert _sha(E53 / "ADDENDUM_I2.md") == (E53 / "runner" / "ADDENDUM_I2_SHA256.txt").read_text().split()[0]
    assert json.loads((RUN1 / "results.json").read_text())["protocol_sha256"] == _sha(E53 / "PROTOCOL.md")
    assert json.loads((I2 / "results.json").read_text())["addendum_sha256"] == _sha(E53 / "ADDENDUM_I2.md")


def test_run1_reproduces_e52_and_repeats():
    a = pd.read_csv(RUN1 / "rows.csv")
    b = pd.read_csv(E52 / "runs" / "20261017T132935Z" / "rows.csv")
    assert len(a) == 50 and (a["R0_p"] - b["E52PS_p"]).abs().max() < 1e-9
    assert (RUN1 / "rows.csv").read_bytes() == (REPEAT / "rows.csv").read_bytes()
    assert (RUN1 / "predictions.csv").read_bytes() == (REPEAT / "predictions.csv").read_bytes()
    r1, r2 = (json.loads((r / "results.json").read_text()) for r in (RUN1, REPEAT))
    r1.pop("run_utc"), r2.pop("run_utc")
    assert r1 == r2


def test_decisions_follow_the_rules():
    r1, r2 = (json.loads((r / "results.json").read_text()) for r in (RUN1, I2))
    assert r1["decision"]["calibrated_replaces_R0"] is None and r2["decision"]["calibrated_replaces_R0"] is None
    assert r1["decision"]["LGB-R_meets_LightGBM_requirement_for_development"] is False
    assert r1["decision"]["secondary_LightGBM_passing"] == [] and r2["decision"]["LightGBM_meets_requirement_for_development"] == []
    assert not any(r1["decision"]["trigger_adds_reliable_information"].values())
    for a in ("LGB-R", "LGB-RL", "LGB-C"):
        assert r1["metrics"][a]["accuracy"] < 0.75
    for a in ("LGB-R2", "LGB-C2"):
        assert r2["metrics"][a]["accuracy"] < 0.75


def test_no_frozen_file_for_failed_arms_and_e52_freeze_intact():
    assert not list((E53 / "frozen").glob("*.json")) if (E53 / "frozen").exists() else True
    f = E52 / "frozen" / "E52_PS_PROSPECTIVE_2027Q1.json"
    assert hashlib.sha256(f.read_bytes()).hexdigest() == (f.parent / (f.stem + ".sha256")).read_text().split()[0]
    st = json.loads((E53 / "prospective_status.json").read_text())
    assert st[f.name]["status"].startswith("pending")
