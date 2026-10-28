"""LEAD2_ARCH: verification of the P0H4-U prediction equation, the hunger cap, target learning, the P0H4 vs P0H4-U
difference and evaluation uncertainty (diagnostic; nothing is fitted on evaluation outcomes, nothing new is scored).

A. Equation: P = pi_H x pi_P with pi_H = Phi((h_last - 11.3) / max(sigma_h, 0.5)) at the S-AB issue date (served H1
   where the pooled sigma is not estimable) and pi_P = LightGBM sigmoid output; recomputed for all 250 rows.
B. Cap: for every Lead-2 HIGH case the price probability needed for P >= 0.50 is 0.50 / pi_H; a case is capped when
   that is >= 1. Controlled test: P with pi_P = 1 - 1e-12 and with the largest pi_P the model ever produced.
C. Target learning: per evaluation origin, training rows, distinct labels, the price base rate, and the distinct T43c
   HIGH labels a direct model would have (labels whose SWS round was published before the origin).
D. P0H4 (quarter-start issue) vs P0H4-U (Lead-2 re-issue after the SWS release): every Lead-2 row whose class differs.
E. Uncertainty: binomial chance that the observed recall reaches 11/17 for several true recalls.

    python arch_audit.py        # ../out/arch_audit.json, ../out/arch_cap_cases.csv, ../out/arch_p0h4_vs_u.csv
"""
from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
from scipy.stats import binom, norm

import lt_lib as T

F, KEY = T.F, T.KEY
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}


def pi_h_row(t: int, k: int, sched: str, h1: float) -> dict:
    iss = F.issue(t, sched)
    h = F.pi_h(iss, t + k)
    if np.isnan(h["pi_H"]):
        h["pi_H"] = h1
    return {"issue": iss, **h}


def main():
    C = pd.read_csv(T.OUT / "candidates.csv", dtype={"province_code": str})
    S = T.stack()
    E = C.merge(S[KEY + ["H1"]], on=KEY)
    res = {}
    # ------------------------------------------------------------ A equation
    rec = [pi_h_row(int(t), int(k), "A" if k == 1 else "B", h1) for t, k, h1 in zip(E["t"], E["lead"], E["H1"])]
    E["pi_H_re"] = [r["pi_H"] for r in rec]
    E["sigma_h"] = [r.get("sigma_h", np.nan) for r in rec]
    E["h_last"] = [r.get("h_last_iss", np.nan) for r in rec]
    E["sws_q"] = [r.get("sws_q") for r in rec]
    E["issue"] = [r["issue"] for r in rec]
    res["A_equation"] = {"pi_H_recomputed_max_abs": float((E["pi_H_re"] - E["pi_H_AB"]).abs().max()),
                         "P_equals_piH_x_piP_max_abs": float((E["pi_H_AB"] * E["C0_price"] - E["C0_p"]).abs().max()),
                         "rows": int(len(E)), "fallback_rows_H1": int(E["sigma_h"].isna().sum()),
                         "pi_P_min": float(E["C0_price"].min()), "pi_P_max": float(E["C0_price"].max()),
                         "clipping_in_path": False, "decision": "HIGH if P >= 0.50"}
    # ------------------------------------------------------------ B cap
    g = E[(E["lead"] == 2) & (E["y"] == 1)].copy()
    g["needed_pi_P"] = 0.5 / g["pi_H_AB"]
    g["capped"] = g["needed_pi_P"] >= 1 - 1e-12
    g["P_if_pi_P_1"] = g["pi_H_AB"] * (1 - 1e-12)
    g["P_if_max_pi_P_ever"] = g["pi_H_AB"] * E["C0_price"].max()
    g["hit"] = g["C0_p"] >= .5
    g["province"], g["target"] = g["province_code"].map(NAMES), g["q"].map(F.qs)
    cols = ["province", "target", "issue", "sws_q", "h_last", "sigma_h", "pi_H_AB", "C0_price", "C0_p", "needed_pi_P",
            "capped", "P_if_pi_P_1", "P_if_max_pi_P_ever", "hit"]
    g[cols].sort_values(["target", "province"]).to_csv(T.OUT / "arch_cap_cases.csv", index=False, lineterminator="\n", float_format="%.4g")
    ties = g[g["capped"]]
    res["B_cap"] = {"lead2_high": int(len(g)), "capped": int(g["capped"].sum()),
                    "capped_cases": [f"{r.province} {r.target}" for r in ties.itertuples()],
                    "capped_h_last": sorted(set(ties["h_last"].round(2))),
                    "controlled_max_P_if_pi_P_1": float(ties["P_if_pi_P_1"].max()) if len(ties) else None,
                    "recall_ceiling_at_0.50": f"{int((~g['capped']).sum())}/{len(g)}",
                    "uncapped_needing_pi_P_above_max_ever": int(((~g["capped"]) & (g["P_if_max_pi_P_ever"] < .5)).sum()),
                    "rank_note": "capped cases are bounded below 0.50 for classification, not for ranking"}
    # ------------------------------------------------------------ C target learning
    r = F.rounds()
    bl = r[r["area"] == "BL"].groupby("q").agg(H=("H", "mean"), pub=("published", "max"))
    tl = []
    for t in sorted(E["t"].unique()):
        tr = T.train_rows(S, int(t))
        o = F.origin(int(t)).date().isoformat()
        pub = bl[bl["pub"] < o]
        trp = tr[tr["q"].isin(pub.index)]
        Y = (trp["y"] == 1) & (trp["q"].map(pub["H"]) > F.H_LINE)
        d = trp.assign(Y=Y.astype(int)).drop_duplicates(["province_code", "q"])
        tl.append({"origin": F.qs(int(t)), "dev": bool(int(t) + 2 <= F.DEV_LAST), "train_rows": int(len(tr)),
                   "distinct_price_labels": int(tr.drop_duplicates(["province_code", "q"]).shape[0]),
                   "rows_per_label": round(len(tr) / max(1, tr.drop_duplicates(["province_code", "q"]).shape[0]), 1),
                   "price_base_rate": round(float(tr["y"].mean()), 3),
                   "direct_T43c_high_rows": int(Y.sum()), "direct_T43c_high_distinct": int(d["Y"].sum()),
                   "direct_model_eligible": bool(int(Y.sum()) >= T.MIN_HIGH)})
    consist = T.known_price().groupby(["province_code", "q"])["y_price"].nunique().max()
    res["C_target_learning"] = {"by_origin": tl, "price_label_identical_across_leads_and_origins": bool(consist == 1),
                                "dev_origins_direct_ineligible": sum(1 for x in tl if x["dev"] and not x["direct_model_eligible"]),
                                "dev_origins": sum(1 for x in tl if x["dev"])}
    # ------------------------------------------------------------ D P0H4 vs P0H4-U
    l2 = E[E["lead"] == 2].copy()
    a = [pi_h_row(int(t), 2, "A", h1) for t, h1 in zip(l2["t"], l2["H1"])]
    l2["issue_A"], l2["sws_A"], l2["pi_H_A_re"] = [x["issue"] for x in a], [x.get("sws_q") for x in a], [x["pi_H"] for x in a]
    diff = l2[(l2["P0H4_p3"] >= .5) != (l2["C0_p"] >= .5)].copy()
    diff["province"], diff["target"] = diff["province_code"].map(NAMES), diff["q"].map(F.qs)
    diff["label"] = np.where(diff["y"] == 1, "HIGH", "LOW")
    dcols = ["province", "target", "label", "issue_A", "sws_A", "pi_H_A", "P0H4_p3", "issue", "sws_q", "pi_H_AB", "C0_p"]
    diff[dcols].to_csv(T.OUT / "arch_p0h4_vs_u.csv", index=False, lineterminator="\n", float_format="%.4g")
    res["D_p0h4_vs_u"] = {"rows_differing": int(len(diff)), "gained_hits": int(((diff["y"] == 1) & (diff["C0_p"] >= .5)).sum()),
                          "new_false_alarms": int(((diff["y"] == 0) & (diff["C0_p"] >= .5)).sum()),
                          "same_price_part": bool((l2["P0_price"] - l2["C0_price"]).abs().max() < 1e-5),
                          "pi_H_A_recomputed_max_abs": float((l2["pi_H_A_re"] - l2["pi_H_A"]).abs().max()),
                          "median_days_later": float((pd.to_datetime(l2["issue"]) - pd.to_datetime(l2["issue_A"])).dt.days.median())}
    # ------------------------------------------------------------ E uncertainty
    res["E_uncertainty"] = {"lead2_high": 17, "high_quarters": int(g["q"].nunique()), "quarters": int(l2["q"].nunique()),
                            "P_observed_recall_ge_11_of_17": {str(p): float(1 - binom.cdf(10, 17, p)) for p in (.55, .59, .65, .70, .75)},
                            "one_case_moves_recall_by": round(1 / 17, 3),
                            "high_cases_needed_for_90pct_lower_bound_above_0.60_if_true_0.70":
                                int(math.ceil((norm.ppf(.95) ** 2) * .7 * .3 / (.10 ** 2)))}
    (T.OUT / "arch_audit.json").write_text(json.dumps(res, indent=1, default=float))
    pd.set_option("display.width", 250)
    print(g[cols].sort_values(["target", "province"]).round(3).to_string(index=False))
    print(diff[dcols].round(3).to_string(index=False))
    print(pd.DataFrame(tl).to_string(index=False))
    print(json.dumps({k: v for k, v in res.items() if k != "C_target_learning"}, indent=1, default=float))
    print({k: v for k, v in res["C_target_learning"].items() if k != "by_origin"})


if __name__ == "__main__":
    main()
