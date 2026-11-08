"""Serve the audited-input Chapter I forecast: re-run FINAL_THESIS_OBJECTIVES score + seal with the corrected inputs
(Addendum 1) into out/ch1_audited/, then export backend/data/ch1_engine/ from it. The first-run outputs and seal in
FINAL_THESIS_OBJECTIVES/out/ are left untouched.

    python export_audited.py
"""
from __future__ import annotations

import shutil
import sys

import rerun_ch1 as R

C = R.C
DEST = R.OUT / "ch1_audited"


def main():
    R._check()
    R.use_corrected()
    DEST.mkdir(exist_ok=True)
    C.OUT = DEST
    sys.path.insert(0, str(R.CH1 / "runner"))
    import run_ch1
    import export_ch1
    run_ch1.OUT = DEST
    shutil.copy(R.CH1 / "out" / "leakage_audit.json", DEST / "leakage_audit.json")   # same code; audit passed
    run_ch1.phase_score()
    run_ch1.phase_seal()
    export_ch1.main()


if __name__ == "__main__":
    main()
