"""
E176: why SIMPLE's Lead-2 Brier and ROC-AUC are worse than E168's. Reads E172's saved forecasts only; refits and re-scores nothing.

    cd backend && PYTHONPATH=. python ../experiments/E176_SIMPLE_IMPROVEMENT/analysis.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from app.paths import BACKEND_DIR

HERE = Path(__file__).resolve().parent
F = pd.read_csv(BACKEND_DIR / "data" / "e172" / "out" / "oof.csv")
A = ("E168", "SIMPLE")


def brier(p, q):
    return float(np.mean((np.asarray(p) - np.asarray(q)) ** 2))


def main():
    g = F[F["lead"] == 2].copy()
    y = g["y_high"] == 1
    for a in A:
        g[f"{a}_HIGH"] = g[a] >= 0.5
        g[f"{a}_correct"] = g[f"{a}_HIGH"] == y
        g[f"{a}_brier_term"] = (g[a] - g["q_true"]) ** 2
    g["change"] = np.select([g["E168_correct"] & ~g["SIMPLE_correct"], ~g["E168_correct"] & g["SIMPLE_correct"]],
                            ["SIMPLE newly wrong", "SIMPLE newly correct"], "same class")
    g["brier_term_diff"] = g["SIMPLE_brier_term"] - g["E168_brier_term"]
    cols = ["province", "region", "survey", "y_high", "q_true", "E168", "SIMPLE", "E168_correct", "SIMPLE_correct", "change",
            "E168_brier_term", "SIMPLE_brier_term", "brier_term_diff", "tag_SIMPLE", "lam_SIMPLE"]
    g[cols].round(4).sort_values(["change", "brier_term_diff"]).to_csv(HERE / "baseline_prediction_comparison.csv", index=False, lineterminator="\n")

    # calibration: by survey and by true class
    cal = []
    for (lab, sub) in [("all", g)] + [(s, x) for s, x in g.groupby("survey")] + [("true HIGH", g[y]), ("true LOW", g[~y])]:
        for a in A:
            cal.append({"subset": lab, "model": a, "rows": len(sub), "mean_p_high": round(sub[a].mean(), 4), "mean_q_true": round(sub["q_true"].mean(), 4),
                        "calibration_in_the_large": round(sub[a].mean() - sub["q_true"].mean(), 4), "brier": round(brier(sub[a], sub["q_true"]), 4),
                        "mean_abs_distance_from_0.5": round((sub[a] - 0.5).abs().mean(), 4)})
    C = pd.DataFrame(cal)
    C.to_csv(HERE / "calibration_analysis.csv", index=False, lineterminator="\n")

    # ranking: pooled vs within-survey AUC; where discordant pairs come from
    rk = []
    for a in A:
        rk.append({"model": a, "scope": "pooled 72", "auc": round(roc_auc_score(y, g[a]), 4)})
        for s, x in g.groupby("survey"):
            yy = x["y_high"] == 1
            if yy.nunique() == 2:
                rk.append({"model": a, "scope": f"within {s}", "auc": round(roc_auc_score(yy, x[a]), 4)})
        hi, lo = g[y], g[~y]
        P = hi[a].values[:, None] - lo[a].values[None, :]
        same = hi["survey"].values[:, None] == lo["survey"].values[None, :]
        rk.append({"model": a, "scope": "discordant pairs within survey", "auc": int(((P < 0) & same).sum())})
        rk.append({"model": a, "scope": "discordant pairs across surveys", "auc": int(((P < 0) & ~same).sum())})
    R = pd.DataFrame(rk)
    R.to_csv(HERE / "ranking_analysis.csv", index=False, lineterminator="\n")
    print(g["change"].value_counts().to_dict())
    print(g[g["change"] != "same class"][["province", "survey", "y_high", "E168", "SIMPLE"]].round(3).to_string(index=False))
    print(C.to_string(index=False))
    print(R.to_string(index=False))
    print("lambda by survey:", g.groupby("survey")[["lam_SIMPLE"]].first().round(3).to_dict()["lam_SIMPLE"],
          "| E168 tag/lam:", F[F["lead"] == 2].groupby("survey")["tag_SIMPLE"].first().to_dict())


if __name__ == "__main__":
    main()
