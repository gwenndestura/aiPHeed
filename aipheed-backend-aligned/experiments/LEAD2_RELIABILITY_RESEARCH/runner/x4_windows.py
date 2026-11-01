"""X4 (post hoc, descriptive; not in the frozen plan, no candidate): in every 13-quarter window of 2005-2020 (the size of
the P0H4 Lead-2 test), how often does the persistence hunger forecast (RW, pooled fit) meet R2 (accuracy >= 0.75) and R3
(balanced accuracy >= 0.70) at Lead 2? Reads out/x2_rows.csv only. Writes out/x4_windows.json.

    python x4_windows.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import rlib as R

W = 13


def main():
    R.frozen_ok()
    d = pd.read_csv(R.OUT / "x2_rows.csv")
    d = d[(d["lead"] == 2) & (d["fit"] == "pooled")]
    res = {}
    for area, g in d.groupby("area"):
        g = g.sort_values("target").reset_index(drop=True)
        acc, bal, both, undefined = [], [], [], 0
        for i in range(len(g) - W + 1):
            w = g.iloc[i:i + W]
            m = R.metrics(w["y"], w["RW"])
            acc.append(m["accuracy"])
            if m["balanced"] is None:
                undefined += 1
                continue
            bal.append(m["balanced"])
            both.append(m["accuracy"] >= .75 and m["balanced"] >= .70)
        res[area] = {"windows": len(acc), "windowsWithBothClasses": len(bal), "oneClassOnly": undefined,
                     "shareAcc>=0.75": round(float(np.mean(np.array(acc) >= .75)), 3),
                     "shareBal>=0.70 (two-class windows)": round(float(np.mean(np.array(bal) >= .70)), 3) if bal else None,
                     "shareBoth (two-class windows)": round(float(np.mean(both)), 3) if both else None,
                     "medianBalanced": round(float(np.median(bal)), 3) if bal else None}
    (R.OUT / "x4_windows.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for a, v in res.items():
        print(a, v)


if __name__ == "__main__":
    main()
