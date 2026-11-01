"""Y4 (EXPERIMENT_PLAN_PHASE2.md; EXPLORATORY: fitted and scored on the 2021+ rows only). Replaces the product
pi_H x pi_P by a logistic combination of [logit pi_H, logit pi_P] refitted at each origin t on earlier evaluation rows
whose T43c label was published before O(t) (all BL rounds of the target quarter published before O(t), target <= t-1).
Fallback to the product when fewer than 20 training rows or fewer than 3 of either class.
Variants: same lead only / leads 1-3 pooled (with lead as a feature); price term P0 or P4.
Writes out/stack.json, out/stack_rows.csv.

    python -B stack.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import numpy as np  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

import p2lib as P  # noqa: E402

R = P.R
OUT = Path(__file__).resolve().parent / "out"
MIN_ROWS, MIN_CLASS = 20, 3


def lg(p):
    p = np.clip(np.asarray(p, float), 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def main():
    P.plan2_ok()
    import pandas as pd
    raw = pd.read_csv(P.EXP / "FINAL_ARCHITECTURE" / "out" / "predictions.csv", dtype={"province_code": str})
    raw = raw[raw["lead"].between(1, 3)].copy()
    r = R.rounds()
    bl = r[r["area"] == "BL"].groupby("q")["published"].max()
    d = P.load_p0h4()
    res, fb = {}, {}
    for price in ("P0", "P4"):
        for mode in ("sameLead", "leads1to3"):
            col = f"STK_{price}_{mode}"
            out = []
            for i, row in d.iterrows():
                t, k = int(row["t"]), int(row["lead"])
                iss = R.issue(t)
                known_q = {q for q, p in bl.items() if p < iss and q <= t - 1}
                tr = raw[raw["q"].isin(known_q)]
                if mode == "sameLead":
                    tr = tr[tr["lead"] == k]
                X = np.column_stack([lg(tr["pi_H4"]), lg(tr[f"{price}_price"])] + ([tr["lead"].to_numpy(float)] if mode != "sameLead" else []))
                y = tr["y"].to_numpy(int)
                x0 = np.array([lg([row["pi_H4"]])[0], lg([row[f"{price}_price"]])[0]] + ([float(k)] if mode != "sameLead" else []))
                if len(y) >= MIN_ROWS and y.sum() >= MIN_CLASS and (1 - y).sum() >= MIN_CLASS and not np.isnan(X).any():
                    out.append(float(LogisticRegression(C=1.0).fit(X, y).predict_proba(x0.reshape(1, -1))[0, 1]))
                    fb.setdefault(col, []).append(0)
                else:
                    out.append(float(row["pi_H4"] * row[f"{price}_price"]))
                    fb.setdefault(col, []).append(1)
            d[col] = out
    for col in [c for c in d.columns if c.startswith("STK_")]:
        for k in (1, 2):
            g = d[d["lead"] == k]
            o = P.official_rules(g, col)
            res[f"lead{k}_{col}"] = {"metrics": P.full_metrics(g, col), "failed": o["failed"], "passesAll": o["passesAll"],
                                     "fallbackRows": int(np.array(fb[col])[(d["lead"] == k).to_numpy()].sum())}
            m = res[f"lead{k}_{col}"]["metrics"]
            print(f"L{k} {col:20s} fallback {res[f'lead{k}_{col}']['fallbackRows']:2d}/{len(g)} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} "
                  f"P {m['precision'] or 0:.2f} R {m['recall']:.2f} Brier {m['brier']:.4f} CM {m['TP']}/{m['FP']}/{m['FN']}/{m['TN']} fails {o['failed']}")
    res["status"] = "exploratory: fitted and scored on the same 2021-2026 quarters; not a confirmatory test"
    OUT.mkdir(exist_ok=True)
    (OUT / "stack.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    d[["t", "lead", "province_code", "q", "y", "pi_H4", "P0_price", "P4_price"] + [c for c in d.columns if c.startswith("STK_")]] \
        .to_csv(OUT / "stack_rows.csv", index=False, lineterminator="\n", float_format="%.5f")


if __name__ == "__main__":
    main()
