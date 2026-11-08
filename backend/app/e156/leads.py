"""
E156 maximum reliable lead, by the criteria in docs/e156/LEAD_RELIABILITY_CRITERIA.md. Reads E151 out-of-sample forecasts.

    python -m app.e156.leads [oof.csv] -> data/e156/out/lead_reliability.json
"""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from app.e147 import evaluate as E7
from app.e151 import OUT as O51
from app.e151 import prov as Pv
from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "e156" / "out"
SHARED = 0.726            # share of error variance shared within round and region, from the E156 audit
PER_CELL = 1.8


def evaluate(F, arm="GNT", tag="E151"):
    rng = np.random.default_rng(156)
    rows = []
    for h, g in F.groupby("lead"):
        g = g.reset_index(drop=True)
        y = g["y_high"].values == 1
        p = g[arm].values >= .5
        n = len(g)
        acc = float((p == y).mean())
        major = float(max(y.mean(), 1 - y.mean()))
        ne = n / (1 + (PER_CELL - 1) * SHARED)
        lo = acc - 1.96 * np.sqrt(acc * (1 - acc) / ne)
        tp, fp, fn, tn = int((p & y).sum()), int((p & ~y).sum()), int((~p & y).sum()), int((~p & ~y).sum())
        prec = tp / max(1, tp + fp)
        hr, lr = tp / max(1, tp + fn), tn / max(1, tn + fp)
        f1 = 2 * prec * hr / max(1e-9, prec + hr)
        d = E7.diff_ci(g, arm, "PERS", "q_true", rng, n=2000)
        sc = Pv.scale_test(g, arm, rng, n=2000)
        per = {s: (float(((x[arm] >= .5) == (x["y_high"] == 1)).mean()), float(((x["PERS"] >= .5) == (x["y_high"] == 1)).mean())) for s, x in g.groupby("survey")}
        c = {"C1": bool(acc > major and lo > major), "C2": bool(d["ci95"][1] < 0), "C3": bool(hr >= .5 and lr >= .5), "C4": bool(sc["slope_ci95"][0] <= 1 <= sc["slope_ci95"][1]), "C5": bool(sum(a >= b for a, b in per.values()) >= 2), "C6": bool(n >= 40)}
        rows.append({"lead": int(h), "rows": n, "accuracy": round(acc, 3), "accuracy_95_low_effective_n": round(lo, 3), "majority_rule": round(major, 3), "precision": round(prec, 3), "high_recall": round(hr, 3), "low_recall": round(lr, 3), "f1": round(f1, 3), "balanced_accuracy": round((hr + lr) / 2, 3), "auc": round(float(roc_auc_score(y, g[arm])), 3), "brier_soft": round(float(np.mean((g[arm] - g["q_true"]) ** 2)), 4),
                     "error_points": round(float(np.mean(np.abs(100 / (1 + np.exp(-g[f"mu_{arm}"])) - 100 / (1 + np.exp(-g["y_true"]))))), 2), "brier_minus_persistence": round(d["diff"], 4), "brier_minus_persistence_ci95": [round(v, 4) for v in d["ci95"]], "calibration_slope_ci95": [round(v, 2) for v in sc["slope_ci95"]], "by_round_model_vs_persistence": {k: [round(a, 3), round(b, 3)] for k, (a, b) in per.items()}, "criteria": c, "reliable": all(c.values()), "confusion": {"tp": tp, "fp": fp, "tn": tn, "fn": fn}})
    max_lead = 0
    for r in sorted(rows, key=lambda r: r["lead"]):
        if r["reliable"] and r["lead"] == max_lead + 1:
            max_lead = r["lead"]
        else:
            break
    first_fail = next((r["lead"] for r in sorted(rows, key=lambda r: r["lead"]) if not r["reliable"]), None)
    return {"model": tag, "leads": rows, "maximum_reliable_lead": max_lead, "first_failing_lead": first_fail, "lead1_passes": bool(rows[0]["reliable"]) if rows and rows[0]["lead"] == 1 else False}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else O51 / "prov_oof.csv"
    F = pd.read_csv(path)
    res = evaluate(F)
    (OUT / "lead_reliability.json").write_text(json.dumps(res, indent=1, default=float), newline="\n")
    for r in res["leads"]:
        print(r["lead"], r["rows"], r["accuracy"], r["accuracy_95_low_effective_n"], r["majority_rule"], r["f1"], r["auc"], r["brier_soft"], r["brier_minus_persistence_ci95"], r["calibration_slope_ci95"], {k: int(v) for k, v in r["criteria"].items()}, "RELIABLE" if r["reliable"] else "fail")
    print("max reliable lead", res["maximum_reliable_lead"], "first failing", res["first_failing_lead"], "lead1 passes", res["lead1_passes"])


if __name__ == "__main__":
    main()
