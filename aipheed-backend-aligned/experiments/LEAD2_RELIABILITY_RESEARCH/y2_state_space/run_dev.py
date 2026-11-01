"""Y2 development: latent-state Kalman AR(1) hunger model vs RW, Lead 2 (and Lead 1 for reference), 2005-2020.
Writes out/y2_dev_rows.csv.

    python -B run_dev.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import devrows  # noqa: E402
import hmodels as H  # noqa: E402
import p2lib as P  # noqa: E402

OUT = Path(__file__).resolve().parent / "out"


def main():
    P.plan2_ok()
    d = devrows.build({"KAL": H.kalman}, leads=(1, 2))
    OUT.mkdir(exist_ok=True)
    d.to_csv(OUT / "y2_dev_rows.csv", index=False, lineterminator="\n", float_format="%.5f")
    print(len(d), "rows; NaN KAL:", int(d["KAL"].isna().sum()))


if __name__ == "__main__":
    main()
