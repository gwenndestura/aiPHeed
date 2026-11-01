"""X1 (EXPERIMENT_PLAN section 2): how reliable is each observed BL hunger label, and what accuracy could a forecaster
that knew the true prevalence achieve against the observed labels? Nothing fitted. Writes out/x1_label_noise.json.

    python x1_label_noise.py
"""
from __future__ import annotations

import json
import math

import numpy as np
from scipy.stats import norm

import rlib as R


def main():
    R.frozen_ok()
    r = R.rounds()
    bl = r[(r["area"] == "BL") & (r["q"] >= R.qi("2021-Q1"))]
    rows = {}
    for q, g in bl.groupby("q"):
        h, n = float(g["H"].mean()), len(g)
        se = (float(g["moe"].mean()) / 1.959964) / math.sqrt(n)
        rows[R.qs(q)] = {"H": round(h, 2), "rounds": n, "se": round(se, 2), "label": int(h > R.H_LINE),
                         "reliability": round(float(norm.cdf(abs(h - R.H_LINE) / se)), 3)}
    firi_targets = [R.qs(q) for q in range(R.qi("2022-Q3"), R.qi("2026-Q3") + 1)]
    p0h4_targets = [R.qs(q) for q in range(R.qi("2023-Q2"), R.qi("2026-Q3") + 1)]

    def ceiling(ts):
        v = [rows[t]["reliability"] for t in ts if t in rows]
        return {"quarters": len(v), "expectedAccuracyOfTruthKnowingForecaster": round(float(np.mean(v)), 3),
                "quartersBelow0.80": [t for t in ts if t in rows and rows[t]["reliability"] < .8]}
    res = {"perQuarter": rows, "firiLead2Targets": ceiling(firi_targets), "p0h4Lead2Targets": ceiling(p0h4_targets)}
    R.OUT.mkdir(exist_ok=True)
    (R.OUT / "x1_label_noise.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for q, v in rows.items():
        print(q, v)
    print("FIRI targets:", res["firiLead2Targets"])
    print("P0H4 Lead-2 targets:", res["p0h4Lead2Targets"])


if __name__ == "__main__":
    main()
