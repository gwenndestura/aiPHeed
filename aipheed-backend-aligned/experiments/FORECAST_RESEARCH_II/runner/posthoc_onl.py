"""POST-HOC sensitivity of the pre-registered online-selection forecaster ONL (not used for any selection): the
default arm before 4 known quarters, the minimum number of known quarters, and the selection score.

    python posthoc_onl.py       # out/posthoc_onl.json
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import ii_lib as L
from score_ii import ARMS

F, M = L.F, L.M


def onl(E, default="P0", min_q=4, score="price"):
    out = pd.Series(index=E.index, dtype=float)
    picks = {}
    for t in sorted(E["t"].unique()):
        hist = E[(E["t"] < t) & (E["q"] <= t - 1)]
        if hist["q"].nunique() < min_q:
            ch = default
        else:
            if score == "price":
                sc = {a: float(np.mean((hist[f"{a}_price"] - hist["price"]) ** 2)) for a in ARMS}
            else:
                sc = {a: float(np.mean((hist[f"{a}_p"] - hist["y"]) ** 2)) for a in ARMS}
            ch = min(ARMS, key=lambda a: (round(sc[a], 10), ARMS.index(a)))
        picks[F.qs(int(t))] = ch
        m = E["t"] == t
        out[m] = E.loc[m, f"{ch}_price"]
    return out, picks


def main():
    L.check_protocol()
    E = pd.read_csv(L.OUT / "predictions_ii.csv", dtype={"province_code": str})
    res = {"label": "POST-HOC sensitivity; not used for selection"}
    variants = {"pre-registered (P0, 4, price)": ("P0", 4, "price"), "default Z0": ("Z0", 4, "price"),
                "default J0": ("J0", 4, "price"), "min 3 quarters": ("P0", 3, "price"), "min 5 quarters": ("P0", 5, "price"),
                "min 6 quarters": ("P0", 6, "price"), "score T43c Brier": ("P0", 4, "t43c")}
    for name, (d, mq, sc) in variants.items():
        pp, picks = onl(E, d, mq, sc)
        col = E["pi_H_AB"] * pp
        G = E.assign(v=col)
        dec = {int(k): F.evaluate(g, "v", "PERS_AB") for k, g in G.groupby("lead")}
        res[name] = {"max_reliable_lead": F.max_reliable(dec), "picks": picks,
                     "leads": {k: {"acc": dec[k]["metrics"]["accuracy"], "brier": dec[k]["metrics"]["brier"],
                                   "recall": dec[k]["metrics"]["recall"], "precision": dec[k]["metrics"]["precision"],
                                   "failed": dec[k]["failed"]} for k in dec}}
        print(f"{name:32s} maxrel {res[name]['max_reliable_lead']} |", " | ".join(
            f"L{k} {v['acc']:.3f} Br{v['brier']:.3f} P{v['precision']:.2f} R{v['recall']:.2f} {''.join(v['failed'])}"
            for k, v in res[name]["leads"].items() if k <= 3))
    # by-origin contribution of the default period to the Lead-2 Brier gain of ONL over Z0
    g = E[E["lead"] == 2].copy()
    g["d"] = (g["ONL_p"] - g["y"]) ** 2 - (g["Z0_p"] - g["y"]) ** 2
    by = g.groupby("t")["d"].sum()
    res["lead2_brier_sum_diff_ONL_minus_Z0_by_origin"] = {F.qs(int(t)): float(v) for t, v in by.items()}
    print(res["lead2_brier_sum_diff_ONL_minus_Z0_by_origin"])
    L.dump("posthoc_onl.json", res)


if __name__ == "__main__":
    main()
