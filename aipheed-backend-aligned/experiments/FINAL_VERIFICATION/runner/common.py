"""Shared set-up for FINAL_VERIFICATION: the audited inputs (FINAL_THESIS_OBJECTIVES Addendum 1) loaded into the
unchanged ch1_lib code, exactly as FIRI_V2_DATA_AUDIT/runner/rerun_ch1.py does."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
VER = HERE.parent
EXP = VER.parent
OUT = VER / "out"
sys.path.insert(0, str(EXP / "FIRI_V2_DATA_AUDIT" / "runner"))
import rerun_ch1 as R  # noqa: E402

C, FM, B, E, L, np, pd = R.C, R.FM, R.B, R.E, R.L, R.np, R.pd
CH1 = R.CH1
AUDITED = EXP / "FIRI_V2_DATA_AUDIT" / "out" / "ch1_audited"


def setup():
    R._check()
    R.use_corrected()
