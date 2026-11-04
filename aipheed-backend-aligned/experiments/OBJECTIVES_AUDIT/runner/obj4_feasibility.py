"""Objective 4 feasibility (analysis only): what Brier score would ANY model need on the 62 verdict quarters to be
statistically better than each baseline, and is that achievable given SWS label noise?

- Noise floor: a forecaster that knew true quarterly hunger exactly would issue p* = P(true H > 11.3 | sampling error)
  and still score E[(p* - y)^2] = mean p*(1 - p*) against the hard labels (out/obj2_error_level.csv, n = 600 per round).
- Required gain vs baseline b: mu = (z_{1-a} + z_0.8) * sigma_b / sqrt(n_eff), with sigma_b and lag-1 rho of C-E2's
  per-quarter gain (out/obj4_power.json) taken as the spread a better model would also have (assumption), at the
  loosest (0.05) and strictest (0.05/14) Holm levels. Required Brier = Brier_b - mu.

    python obj4_feasibility.py   # -> ../out/obj4_feasibility.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

OUT = Path(__file__).resolve().parents[1] / "out"


def main():
    E = pd.read_csv(OUT / "obj2_error_level.csv")
    P = json.loads((OUT / "obj4_power.json").read_text(encoding="utf-8"))["comparisons"]
    R = json.loads((OUT / "ce2_results.json").read_text(encoding="utf-8"))["holm_family_14"]
    base = {(f["lead"], f["comparator"]): (f["brier_comparator"], f["brier_candidate"]) for f in R}
    res = {"noise_floor": {}, "comparisons": []}
    for k in (1, 2):
        e = E[E["lead"] == k]
        pt = e["P_true_high_n600"]
        res["noise_floor"][str(k)] = {"perfect_true_state_brier": round(float((pt * (1 - pt)).mean()), 4),
                                      "perfect_true_state_accuracy": round(float(np.maximum(pt, 1 - pt).mean()), 3)}
    for c in P:
        k, b = c["lead"], c["baseline"]
        n_eff = c["n_quarters"] * (1 - c["lag1_rho"]) / (1 + c["lag1_rho"])
        bb, cand = base[(k, b)]
        row = {"lead": k, "baseline": b, "n": c["n_quarters"], "baseline_brier": round(bb, 4),
               "C-E2_brier_same_quarters": round(cand, 4)}
        for lvl, a in (("alpha_0.05", .05), ("alpha_0.0036", .05 / 14)):
            mu = (norm.ppf(1 - a) + norm.ppf(.8)) * c["sd"] / np.sqrt(n_eff)
            row[f"required_brier_{lvl}"] = round(bb - mu, 4)
        row["floor"] = res["noise_floor"][str(k)]["perfect_true_state_brier"]
        row["feasible_at_0.05"] = bool(row["required_brier_alpha_0.05"] > row["floor"])
        res["comparisons"].append(row)
    (OUT / "obj4_feasibility.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("noise floor", res["noise_floor"])
    for r in res["comparisons"]:
        print(f"L{r['lead']} {r['baseline']:12s} base {r['baseline_brier']:.3f} C-E2 {r['C-E2_brier_same_quarters']:.3f} "
              f"need <= {r['required_brier_alpha_0.05']:.3f} (alpha .05) / {r['required_brier_alpha_0.0036']:.3f} (alpha/14); "
              f"floor {r['floor']:.3f}")


if __name__ == "__main__":
    main()
