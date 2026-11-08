"""
tests/integration/test_e120_firi_design.py
------------------------------------------
E120: the proposed consolidated FIRI (six indicators) keeps SWS out of the index, uses provincial data only in
provincial scores, uses 2021+ observations available before each issue, never fills missing values, reproduces from
its inputs, and leaves firi.py / production / E118-E119R2 unchanged. Runs runner/validate.py's checks.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
E = ROOT / "aipheed-backend-aligned" / "experiments" / "E120_FIRI_Consolidated_Design"
pytestmark = pytest.mark.skipif(not (E / "out" / "summary.json").exists(), reason="E120 outputs missing")


def test_e120_checks_pass():
    sys.path.insert(0, str(E / "runner"))
    spec = importlib.util.spec_from_file_location("e120_validate", E / "runner" / "validate.py")
    validate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate)
    r = validate.checks()
    failed = {x["check"]: x["detail"] for x in r if x["result"] != "PASS"}
    assert not failed, failed
    assert len(r) == 20


def test_served_firi_v2_untouched():
    from app.ml.inference import firi as FI
    assert len(FI.LABELS) == 12 and FI.THRESHOLD == 0.5 and FI.MIN_DOMAINS == 4
