"""R3/R7 margin for C-E2 and C-E6 (read only, stored walk-forward fits; nothing fitted).

R3: balanced accuracy >= 0.70. R7: each third >= 0.60 and leave-one-quarter-out min >= 0.70 (hr_lib rules, unedited).
Reports how many additional correct calls each rule needs, which wrong calls are nearest 0.50, how far C-E6 moved
them relative to C-E2, and whether those quarters' labels are within SWS sampling noise.

    python obj2_r3r7_margin.py   # -> ../out/obj2_r3r7_margin.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "out"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_model as CE  # noqa: E402

H, V, R = CE.H, CE.V, CE.R


def main():
    lab = V.area_labels(H.load())
    lb = lab[lab["area"] == "BL"]
    E = pd.read_csv(OUT / "obj2_error_level.csv")
    F = pd.concat([pd.read_csv(OUT / "ce2_fits.csv"), pd.read_csv(OUT / "ce6_fits.csv")])[["name", "t", "lead", "q", "p"]]
    L = pd.read_csv(CE.N.LEADS_FILE)
    comp = pd.concat([F, L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]]])
    res = {}
    for k in (1, 2):
        W = R.frame(comp, k, lb).dropna(subset=["C-E2", "C-E6"])
        th = np.array_split(np.array(sorted(W["q"].unique())), 3)
        e = E[E["lead"] == k].set_index("target")
        Lk = {}
        for n in ("C-E2", "C-E6"):
            c, y = (W[n] >= .5).astype(int), W["y"].astype(int)
            tp, tn = int(((c == 1) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum())
            pos, neg = int(y.sum()), int((1 - y).sum())
            need_tn = max(0, math.ceil((2 * .70 - tp / pos) * neg - 1e-9) - tn)
            mid = W["q"].isin(th[1])
            acc_mid = float((c[mid] == y[mid]).mean())
            need_mid = max(0, math.ceil(.60 * int(mid.sum()) - 1e-9) - int((c[mid] == y[mid]).sum()))
            Lk[n] = {"TP": tp, "TN": tn, "positives": pos, "negatives": neg,
                     "balanced": round((tp / pos + tn / neg) / 2, 4), "R3_extra_correct_LOW_needed": need_tn,
                     "middle_third_accuracy": round(acc_mid, 3), "R7_extra_correct_calls_in_middle_third": need_mid}
        wrong_low = W[(W["y"] == 0) & (W["C-E6"] >= .5)].copy()
        wrong_low["moved_toward_LOW"] = wrong_low["C-E6"] - wrong_low["C-E2"]
        wrong_low = wrong_low.sort_values("C-E6")
        Lk["missed_LOW_quarters"] = [{"target": H.qs(int(r.q)), "p_C-E2": round(float(r["C-E2"]), 3),
                                      "p_C-E6": round(float(r["C-E6"]), 3), "change": round(float(r.moved_toward_LOW), 3),
                                      "observed_H": float(e.loc[H.qs(int(r.q)), "observed_H"]),
                                      "P_true_high_n600": float(e.loc[H.qs(int(r.q)), "P_true_high_n600"]),
                                      "middle_third": bool(r.q in set(th[1]))} for _, r in wrong_low.iterrows()]
        Lk["nearest_missed_LOW_distance_to_0.5"] = round(float(wrong_low["C-E6"].min() - .5), 3) if len(wrong_low) else None
        res[str(k)] = Lk
    (OUT / "obj2_r3r7_margin.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
