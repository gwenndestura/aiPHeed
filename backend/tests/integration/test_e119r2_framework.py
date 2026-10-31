"""
tests/integration/test_e119r2_framework.py
------------------------------------------
E119-R2: every FIRI v2 indicator, E118 dataset and E119 feature is mapped into the proposed framework; geography and the
2021+ window are preserved; regional forecasting and provincial profiling stay separate; nothing trained or changed.
Runs the same checks as runner/validate.py.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
E = ROOT / "aipheed-backend-aligned" / "experiments" / "E119R2_Indicator_Framework_Redesign"
pytestmark = pytest.mark.skipif(not (E / "out" / "manifest.json").exists(), reason="E119-R2 outputs missing")


@pytest.fixture(scope="module")
def results():
    sys.path.insert(0, str(E / "runner"))
    spec = importlib.util.spec_from_file_location("e119r2_validate", E / "runner" / "validate.py")
    validate = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(validate)
    return {r["check"]: r for r in validate.checks()}


def test_all_validation_checks_pass(results):
    failed = {k: v["detail"] for k, v in results.items() if v["result"] != "PASS"}
    assert not failed, failed
    assert len(results) == 21


def test_seven_indicators_cover_four_fao_dimensions():
    import pandas as pd
    fw = pd.read_csv(E / "E119R2_PROPOSED_INDICATOR_FRAMEWORK.csv")
    assert list(fw["code"]) == ["FP", "PS", "CH", "HI", "SV", "NS", "EH"]
    firi = {c.strip() for s in fw["firi"] for c in s.split(",")}
    assert firi == {"A1", "A2", "A3", "V1", "C1", "C2", "C3", "C4", "E1", "E2", "N1", "H1"}
    fao = pd.read_csv(E / "E119R2_FAO_DIMENSION_MAPPING.csv")
    for d in ("Availability", "Access", "Utilization", "Stability"):
        assert fao[d].notna().any(), d
