"""LEAD2_SUBGROUP: diagnostic of the K1 subgroup signals on the scored LEAD2_FINAL rows (nothing is fitted on
evaluation outcomes; no new candidate is scored here).

1. Lead-2 probabilities of every HIGH case and every false alarm, B0 (P0H4-U) vs K1.
2. Ordering: T43c and price-term AUC, and each HIGH case's rank among the LOW rows (share of LOW rows scored below it).
3. Redundancy: R^2 of each K column on the existing aggregate price columns (training rows at the final origin), and
   the HIGH-minus-LOW standardised difference of the residual (the part not explained by the aggregates).
4. Early warning at the cut-off for each missed HIGH case: percentile of the K columns and A1 among that origin's
   training rows (in the direction training HIGH rows took), and the price-condition rate among the 10 training rows
   nearest in K space alone.
5. Headroom: the Lead-2 HIGH/LOW counts K1 would give at each cut between the highest missed HIGH and 0.50, reported
   only to show whether ANY cut could convert the ordering gain; a cut is never chosen here.

    python subgroup_diag.py     # ../out/subgroup_diag.json, ../out/subgroup_cases.csv
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

import lt_lib as T
from features_v4 import K_COLS
from limits import auc

F, KEY = T.F, T.KEY
AGG = ["A1_food", "A1_gap", "A_mom", "F_ex", "G_ex", "mom1", "mom6", "accel", "vol6", "A3", "R_rice_yoy", "R_rice_mom3"]
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}


def ols_r2_resid(X: pd.DataFrame, y: pd.Series):
    m = X.notna().all(axis=1) & y.notna()
    A = np.column_stack([np.ones(m.sum()), X[m].to_numpy(float)])
    b, *_ = np.linalg.lstsq(A, y[m].to_numpy(float), rcond=None)
    r = y[m].to_numpy(float) - A @ b
    return 1 - r.var() / y[m].var(ddof=0), pd.Series(r, index=y[m].index)


def smd(x, y) -> float:
    a, b = x[y == 1], x[y == 0]
    s = np.sqrt((a.var() + b.var()) / 2)
    return float((a.mean() - b.mean()) / s) if s > 0 else float("nan")


def main():
    S = pd.read_csv(T.DATA / "stack_v4.csv", dtype={"province_code": str})
    E = pd.read_csv(T.OUT / "final_rows.csv", dtype={"province_code": str})
    E = E.merge(S[KEY + K_COLS + ["A1_food", "A1_gap"]], on=KEY, how="left")
    res = {}
    # ------------------------------------------------------------ 1-2 cases and ordering
    res["auc"] = {}
    for k in (1, 2):
        g = E[E["lead"] == k]
        h = g[g["hunger"] == 1]
        res["auc"][k] = {"t43c_B0": auc(g["y"], g["B0_p"]), "t43c_K1": auc(g["y"], g["K1_p"]),
                         "price_on_hunger_rows_B0": auc(h["price"], h["B0_price"]),
                         "price_on_hunger_rows_K1": auc(h["price"], h["K1_price"])}
    g = E[E["lead"] == 2].copy()
    low = g[g["y"] == 0]
    for c in ("B0", "K1"):
        g[f"{c}_rank_among_low"] = [float((low[f"{c}_p"] < p).mean()) if y == 1 else np.nan for p, y in zip(g[f"{c}_p"], g["y"])]
    g["province"], g["target"] = g["province_code"].map(NAMES), g["q"].map(F.qs)
    g["case"] = np.select([(g["y"] == 1) & (g["B0_p"] >= .5), g["y"] == 1, g["B0_p"] >= .5, g["K1_p"] >= .5],
                          ["hit", "missed HIGH", "false alarm B0", "false alarm K1 only"], "")
    cases = g[g["case"] != ""].sort_values(["case", "q", "province"])
    cols = ["case", "target", "province", "pi_H_AB", "B0_price", "K1_price", "B0_p", "K1_p", "B0_rank_among_low",
            "K1_rank_among_low"] + K_COLS + ["A1_food", "A1_gap"]
    cases[cols].to_csv(T.OUT / "subgroup_cases.csv", index=False, lineterminator="\n", float_format="%.4g")
    miss = g[(g["y"] == 1) & (g["B0_p"] < .5)]
    hit = g[(g["y"] == 1) & (g["B0_p"] >= .5)]
    res["lead2_mean_rank_among_low"] = {"missed_B0": float(miss["B0_rank_among_low"].mean()),
                                        "missed_K1": float(miss["K1_rank_among_low"].mean()),
                                        "hits_B0": float(hit["B0_rank_among_low"].mean()),
                                        "hits_K1": float(hit["K1_rank_among_low"].mean())}
    res["lead2_missed_K1_minus_B0_p"] = {f"{r.province} {r.target}": float(r.K1_p - r.B0_p) for r in miss.itertuples()}
    res["lead2_low_rows_scored_above_best_missed_K1"] = int((low["K1_p"] >= miss["K1_p"].max()).sum())
    res["lead2_low_rows_scored_above_best_missed_B0"] = int((low["B0_p"] >= miss["B0_p"].max()).sum())
    # hunger-capped misses: P = 0.5 x pi_P can never reach 0.50
    res["lead2_misses_capped_by_hunger_term"] = int((miss["pi_H_AB"] <= .5 + 1e-9).sum())
    # ------------------------------------------------------------ 3 redundancy (training rows at the final origin)
    tr = T.train_rows(S, int(E["t"].max()))
    res["redundancy"] = {}
    for c in K_COLS:
        r2, resid = ols_r2_resid(tr[AGG], tr[c])
        yy = tr.loc[resid.index, "y"]
        res["redundancy"][c] = {"r2_on_aggregates": float(r2), "n": int(len(resid)), "smd_raw": smd(tr.loc[resid.index, c], yy),
                                "smd_residual": smd(resid, yy),
                                "max_abs_corr": max((abs(float(tr[[c, a]].corr().iloc[0, 1])), a) for a in AGG)}
    # ------------------------------------------------------------ 4 early warning at the cut-off for each miss
    ew = []
    for r in miss.itertuples():
        trr = T.train_rows(S, int(r.t))
        row = {"case": f"{r.province} {r.target}", "B0_p": r.B0_p, "K1_p": r.K1_p, "pi_H": r.pi_H_AB}
        for c in K_COLS + ["A1_food", "A1_gap"]:
            x = trr[c].dropna()
            up = trr.loc[trr["y"] == 1, c].mean() > trr.loc[trr["y"] == 0, c].mean()
            v = getattr(r, c)
            row[f"pct_{c}"] = float((x < v).mean() if up else (x > v).mean()) if pd.notna(v) and len(x) else np.nan
        Z = trr[K_COLS].dropna()
        mu, sd = Z.mean(), Z.std()
        d = (((Z - mu) / sd - (pd.Series({c: getattr(r, c) for c in K_COLS}) - mu) / sd) ** 2).sum(axis=1)
        nn = d.nsmallest(10).index
        row["K_space_10nn_price_rate"] = float(trr.loc[nn, "y"].mean())
        row["train_price_rate"] = float(trr["y"].mean())
        row["strong_K_signal"] = bool(max(row[f"pct_{c}"] for c in K_COLS) >= .90 or row["K_space_10nn_price_rate"] >= .7)
        ew.append(row)
    res["early_warning_misses"] = ew
    # ------------------------------------------------------------ 5 headroom (descriptive only)
    cuts = sorted({round(float(p), 3) for p in miss["K1_p"]} | {.5})
    res["headroom_K1"] = [{"cut": c, "tp": int(((g["K1_p"] >= c) & (g["y"] == 1)).sum()),
                           "fp": int(((g["K1_p"] >= c) & (g["y"] == 0)).sum()),
                           "recall": float(((g["K1_p"] >= c) & (g["y"] == 1)).sum() / g["y"].sum()),
                           "precision": float(((g["K1_p"] >= c) & (g["y"] == 1)).sum() / max(1, (g["K1_p"] >= c).sum()))}
                          for c in cuts]
    (T.OUT / "subgroup_diag.json").write_text(json.dumps(res, indent=1, default=float))
    pd.set_option("display.width", 250)
    print(cases[cols].round(3).to_string(index=False))
    print(json.dumps({k: v for k, v in res.items() if k != "early_warning_misses"}, indent=1, default=float))
    print(pd.DataFrame(ew).round(3).to_string(index=False))


if __name__ == "__main__":
    main()
