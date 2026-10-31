"""
tests/integration/test_e121_firi3.py
------------------------------------
E121: the FIRI3 run on the real inputs verified its frozen protocol, is deterministic, reproduces the frozen E120
design exactly, passed every leakage check, kept provincial and regional scores apart, never scored a missing value,
and wrote immutable snapshots whose files match their manifests. FIRI v2 is unchanged.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from app.ml.inference import firi3 as F3

ROOT = Path(__file__).resolve().parents[3]
E = ROOT / "aipheed-backend-aligned" / "experiments" / "E121_FIRI3_Implementation"
pytestmark = pytest.mark.skipif(not (E / "out" / "summary.json").exists(), reason="E121 outputs missing")


@pytest.fixture(scope="module")
def summary():
    return json.loads((E / "out" / "summary.json").read_text())


def test_protocol_hash():
    h = hashlib.sha256((E / "E121_FIRI3_PROTOCOL.md").read_bytes()).hexdigest()
    assert h == (E / "runner" / "PROTOCOL_SHA256.txt").read_text().strip() == F3.PROTOCOL_SHA256


def test_deterministic_and_reproduces_e120(summary):
    assert summary["deterministic"] and summary["reproduces_e120"] and summary["bands_match_e120"]


def test_all_leakage_checks_pass(summary):
    bad = {k: v for k, v in summary["leakage"].items() if isinstance(v, bool) and not v}
    assert not bad, bad


def test_results_geography_and_missing():
    fs = pd.read_csv(E / "E121_FIRI3_FEATURE_RESULTS.csv")
    assert set(fs.loc[fs["scope"] == "provincial", "unit"]) == set(F3.PROVINCES)
    assert set(fs.loc[fs["scope"] == "regional", "unit"]) == {F3.REGION_LABEL}
    assert not fs.loc[fs["scope"] == "provincial", "feature"].str.endswith("_R").any()
    assert fs.loc[fs["status"].isin(["missing", "stale", "insufficient_history", "unavailable_at_issue", "incomplete_year"]), "score"].isna().all()
    ov = pd.read_csv(E / "E121_FIRI3_OVERALL_RESULTS.csv")
    ok = ov[ov["firi3"].notna()]
    assert ((ok["scope"] == "provincial") & (ok["indicators_available"] >= 4) | (ok["scope"] == "regional") & (ok["indicators_available"] >= 4)).all()
    assert ok["firi3"].between(0, 1).all()
    assert (ok.apply(lambda r: F3.band(r["firi3"], int(r["indicators_available"])) == r["band"], axis=1)).all()
    assert ov.loc[ov["firi3"].isna(), "band"].eq("not_computable").all()
    assert ov.loc[ov["scope"] == "regional", "firi_v2"].isna().all()


def test_snapshots_immutable_and_intact():
    snaps = sorted((E / "snapshots").iterdir())
    assert len(snaps) == 23
    for d in snaps:
        man = json.loads((d / "manifest.json").read_text())
        assert man["protocol_sha256"] == F3.PROTOCOL_SHA256
        assert man["kind"] in ("retrospective", "prospective")
        for name, h in man["files"].items():
            assert hashlib.sha256((d / name).read_bytes()).hexdigest() == h, (d.name, name)
    log = pd.read_csv(E / "out" / "snapshot_log.csv")
    assert set(log["action"]) <= {"written", "verified unchanged"}
