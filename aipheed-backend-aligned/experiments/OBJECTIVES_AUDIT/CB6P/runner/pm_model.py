"""C-B6D-E-X-PM (../PREREGISTRATION_PM.md, hash checked): C-B6D-E-X with the paper's median cut-off.

Runs fi_provincial.run() unchanged with THR = median of S and all outputs redirected to out/pm/ (originals untouched).

    python pm_model.py           # primary: median over the 250 evaluation rows
    python pm_model.py sens      # sensitivity: median over all 270 labelled rows -> out/pm_sens/
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import hashlib
import shutil
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fi_provincial as FP  # noqa: E402

PLAN = FP.HERE / "PREREGISTRATION_PM.md"
INPUTS = ("cb6p_labels.csv", "fi_regional_fits.csv", "cb6d_fits.csv", "cb6p2_fits.csv")


def check() -> str:
    b = PLAN.read_bytes().replace(b"\r\n", b"\n")
    body, last = b.rstrip(b"\n").rsplit(b"\n", 1)
    h = hashlib.sha256(body + b"\n").hexdigest()
    assert last.split()[1].decode() == h, "PM pre-registration changed"
    return h


def main(sens: bool):
    h = check()
    L = pd.read_csv(FP.OUT / "fi_labels_ext.csv")
    thr = float(L["S"].median()) if sens else float(L[L["q"] >= FP.Q_EXT]["S"].median())
    assert abs(thr - (14.42 if sens else 14.325)) < 1e-9, thr
    out = FP.OUT / ("pm_sens" if sens else "pm")
    out.mkdir(exist_ok=True)
    for f in INPUTS:
        shutil.copyfile(FP.OUT / f, out / f)
    FP.THR, FP.OUT = thr, out
    print(f"PM plan {h[:8]}  THR {thr}  -> {out}", flush=True)
    FP.run()


if __name__ == "__main__":
    main(len(sys.argv) > 1 and sys.argv[1] == "sens")
