"""PROTOCOL sections 8 and 9 (limits): the schedule-B Lead-1 decomposition (H5), products ordered by warning time,
and the limits L1-L4 (label-noise ceiling, MDE / quarters needed, predictable share of the price error).

    python schedule_limits.py   # out/schedule_limits.json
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import ii_lib as L
from contrib_ii import boot

F, M, KEY = L.F, L.M, L.KEY


def main():
    L.check_protocol()
    E = pd.read_csv(L.OUT / "predictions_ii.csv", dtype={"province_code": str})
    res = json.loads((L.OUT / "results_ii.json").read_text())
    ta = json.loads((L.OUT / "target_audit.json").read_text())
    final = res["selection"]["chosen_FINAL"]
    bl = L.bl_quarters().set_index("q")
    out = {"FINAL": final}
    # ------------------------------------------------------------ H5
    g = E[E["lead"] == 1].copy()
    dec = {}
    for pc in ("P0", final):
        g["d"] = (g["pi_H_B"] * g[f"{pc}_price"] - g["y"]) ** 2 - (g["pi_H_A"] * g[f"{pc}_price"] - g["y"]) ** 2
        rows = []
        for t, h in g.groupby("t"):
            iss = F.issue(int(t), "B")
            kn = F.known(iss, "BL")
            q_last, h_last = kn[-1][0], kn[-1][1]
            se = float(bl.loc[q_last, "se_q"])
            rows.append({"origin": F.qs(int(t)), "target": F.qs(int(t) + 1), "B_reading_q": F.qs(q_last), "B_reading": h_last,
                         "se": se, "within_1se": bool(abs(h_last - F.H_LINE) < se), "target_H": float(h["H"].iloc[0]),
                         "brier_sum_B_minus_A": float(h["d"].sum())})
        D = pd.DataFrame(rows)
        pos = D[D["brier_sum_B_minus_A"] > 0]
        share = float(pos.loc[pos["within_1se"], "brier_sum_B_minus_A"].sum() / pos["brier_sum_B_minus_A"].sum()) if len(pos) else float("nan")
        dec[pc] = {"by_origin": D.to_dict("records"), "total_brier_diff_mean": float(g["d"].mean()),
                   "share_of_loss_from_within_1se": share, "H5_supported": bool(share >= .70)}
        print(pc, "B-A Lead-1 Brier", round(g["d"].mean(), 4), "share within 1SE", round(share, 2))
        print(D[D["brier_sum_B_minus_A"].abs() > 1e-3].to_string())
    out["H5"] = dec
    # ------------------------------------------------------------ products by warning time
    prods = []
    for k in F.LEADS:
        h = E[E["lead"] == k]
        for sch in ("A", "B"):
            if k == 1 and sch == "B":
                label = "L1-B (nowcast, issued inside the target quarter)"
            else:
                label = f"L{k}-{sch}"
            for pc in ("P0", final):
                p = h[f"pi_H_{sch}"] * h[f"{pc}_price"]
                m = M.cls(h["y"], p)
                prods.append({"product": label, "price_part": pc, "warning_days_median": float(h[f"warn_days_{sch}"].median()),
                              "accuracy": m["accuracy"], "brier": m["brier"], "recall": m["recall"], "precision": m["precision"], "n": m["n"]})
    out["products_by_warning"] = sorted(prods, key=lambda r: (r["warning_days_median"], r["price_part"]))
    for r in out["products_by_warning"]:
        print(f"{r['product']:52s} {r['price_part']:3s} warn {r['warning_days_median']:6.0f}d acc {r['accuracy']:.3f} Br {r['brier']:.3f} "
              f"R {r['recall']:.2f} P {r['precision']:.2f}")
    # ------------------------------------------------------------ L1 ceiling, L3 MDE, L4 predictable share
    out["L1_label_noise_ceiling"] = {k: v["accuracy_ceiling"] for k, v in ta["T2_noise"]["by_lead"].items()}
    l3 = {}
    for k in (1, 2, 3):
        h = E[E["lead"] == k]
        b = boot(h["q"], (h[f"{final}_p"] - h["y"]) ** 2, (h["P0H4U_p"] - h["y"]) ** 2)
        Q = h["q"].nunique()
        mde = 2.49 * b["sd"]
        l3[k] = {"diff": b["diff"], "ci90": b["ci90"], "sd": b["sd"], "mde": mde, "quarters_now": int(Q),
                 "quarters_needed_for_0.01": float(Q * (mde / .01) ** 2), "quarters_needed_for_0.02": float(Q * (mde / .02) ** 2)}
    out["L3_power_FINAL_vs_P0H4U"] = l3
    S = F.stack()
    A = pd.read_csv(L.OUT / "price_arms_ii.csv", dtype={"province_code": str})
    j0 = A[A["arm"] == "J0"][KEY + ["F_sd"]]
    R = S[S["t"].isin(sorted(E["t"].unique())) & S["ef"].notna()].merge(j0, on=KEY, how="inner")
    l4 = {}
    for k, h in R.groupby("lead"):
        mse = float(np.mean(h["ef"] ** 2))
        var_th = float(np.mean(h["F_sd"] ** 2))
        l4[int(k)] = {"z0_mse": mse, "innovation_variance": var_th, "bias_sq": float(np.mean(h["ef"]) ** 2),
                      "predictable_share_upper": float(1 - var_th / mse), "n": int(len(h))}
    out["L4_predictable_share"] = l4
    print("L1", out["L1_label_noise_ceiling"])
    print("L3", {k: (round(v["diff"], 4), round(v["mde"], 4), round(v["quarters_needed_for_0.02"], 1)) for k, v in l3.items()})
    print("L4", {k: (round(v["predictable_share_upper"], 2), round(v["bias_sq"] / v["z0_mse"], 2)) for k, v in l4.items()})
    L.dump("schedule_limits.json", out)


if __name__ == "__main__":
    main()
