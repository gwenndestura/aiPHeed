"""
Mechanical decision table (docs/aipheed/v2/PREREGISTRATION.md section 6). Reliability uses the frozen
e130_lib.numeric_reliability itself (protocol lock R2), loaded read-only from the research package; this module is
used by offline scripts and tests only. The API reads the stored verdict file (results/v2_verdict.json).
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

from app.forecasting.evidence import ReliabilityStatus

REPO = Path(__file__).resolve().parents[4]
E130_LIB = REPO / "aipheed-backend-aligned" / "experiments" / "E130_Provincial_Risk_Score_Forecasting" / "runner" / "e130_lib.py"
BASELINES = ["persistence", "climatology"]          # as applied in the completed backend run (MODEL_REPORT)
DEVELOPMENT_PASS = "DEVELOPMENT_PASS"


def frozen_lib():
    if "e130_lib_v2" not in sys.modules:
        spec = importlib.util.spec_from_file_location("e130_lib_v2", E130_LIB)
        m = importlib.util.module_from_spec(spec)
        sys.modules["e130_lib_v2"] = m
        spec.loader.exec_module(m)
    return sys.modules["e130_lib_v2"]


def reliability(rows: pd.DataFrame, model: str) -> dict:
    """rows: y, se, tqi, area, f_<model>, f_persistence, f_climatology, lo80_<model>, hi80_<model>."""
    d = rows.rename(columns={"area": "province"}).assign(target_q=rows["tqi"])
    base = [b for b in BASELINES if f"f_{b}" in d and not d[f"f_{b}"].equals(d[f"f_{model}"])]
    return frozen_lib().numeric_reliability(d, model, base)


def label(rules_passed: bool, n_quarters: int, n_rows: int, future: bool) -> str:
    if not future:
        return DEVELOPMENT_PASS if rules_passed else ReliabilityStatus.NOT_RELIABLE.value
    if n_quarters < 10 or n_rows < 40:
        return ReliabilityStatus.NOT_YET_TESTABLE.value
    return ReliabilityStatus.RELIABLE.value if rules_passed else ReliabilityStatus.NOT_RELIABLE.value


def maximum_reliable_lead(labels: dict[int, str]) -> int | None:
    best = None
    for k in sorted(labels):
        if labels[k] != ReliabilityStatus.RELIABLE.value:
            break
        best = k
    return best


def served_status(dev_label: str, future_label: str) -> str:
    """Development label until the future rows meet N1, then the future label (never typed by hand)."""
    return dev_label if future_label == ReliabilityStatus.NOT_YET_TESTABLE.value else future_label
