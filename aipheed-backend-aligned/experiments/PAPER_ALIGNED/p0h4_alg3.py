"""PAPER_ALIGNED: Algorithm 3 (Chapter III pp. 41-43) applied to the served P0H4 walk-forward rows, read only.

    python p0h4_alg3.py      # -> p0h4_alg3.json

Rule as written: one quarter per fold; a lead is reliable when the mean fold accuracy is >= 0.75; leads k = 1..8 are
tried in order and the search halts at the first failing lead. No model is fitted: the forecasts are the stored P0H4
walk-forward predictions (LEAD2_OPTIMIZATION/out/predictions_addendum3.csv, column P0H4_p3, HIGH at 0.50), and the
R1-R7 verdicts are the stored ones (backend/data/ch1_engine/evaluation.json).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
ROOT = EXP.parents[1]
PRED = EXP / "LEAD2_OPTIMIZATION" / "out" / "predictions_addendum3.csv"
EVAL = ROOT / "backend" / "data" / "ch1_engine" / "evaluation.json"
ACC_MIN, K_MAX = 0.75, 8


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    P = pd.read_csv(PRED, dtype={"province_code": str})
    ev = json.loads(EVAL.read_text(encoding="utf-8"))
    out, mrlt, stopped = {}, 0, False
    for k in range(1, K_MAX + 1):
        g = P[P["lead"] == k].copy()
        g["yhat"] = (g["P0H4_p3"] >= 0.5).astype(int)
        g["ok"] = (g["yhat"] == g["y"]).astype(int)
        fold = g.groupby("q")["ok"].mean()
        tp = int(((g.yhat == 1) & (g.y == 1)).sum())
        fn = int(((g.yhat == 0) & (g.y == 1)).sum())
        fp = int(((g.yhat == 1) & (g.y == 0)).sum())
        tn = int(((g.yhat == 0) & (g.y == 0)).sum())
        st = ev["leads"][str(k)]
        m = st["metrics"]
        crit = ev["horizon"]["leads"][str(k)].get("criteria", {})
        passed = bool(fold.mean() >= ACC_MIN)
        out[str(k)] = {"rows": int(len(g)), "folds": int(fold.size), "mean_fold_accuracy": round(float(fold.mean()), 4),
                       "pooled_accuracy": round(float(g["ok"].mean()), 4), "TP": tp, "FP": fp, "FN": fn, "TN": tn,
                       "recall": round(tp / (tp + fn), 4) if tp + fn else None,
                       "always_low_accuracy": round(float((g["y"] == 0).mean()), 4),
                       "stored_accuracy": round(m["accuracy"], 4), "balanced": round(m["balanced_accuracy"], 4),
                       "precision": round(m["precision"], 4), "auc": m.get("auc"), "brier": m.get("brier"),
                       "R1_R7": crit, "stored_reliable": st["reliable"],
                       "alg3": "pass" if passed and not stopped else ("FAIL (stop)" if not stopped else "after stop")}
        if not stopped:
            if passed:
                mrlt = k
            else:
                stopped = True
    res = {"rule": f"mean fold accuracy >= {ACC_MIN}, one quarter per fold, k = 1..{K_MAX}, halt at the first failure",
           "max_reliable_lead_alg3": mrlt, "max_reliable_lead_R1_R7": ev["max_reliable_lead"], "leads": out,
           "inputs": {"predictions": sha(PRED), "evaluation": sha(EVAL)}}
    (HERE / "p0h4_alg3.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"Maximum Reliable Lead Time (Algorithm 3): {mrlt}; under R1-R7: {ev['max_reliable_lead']}")
    for k, v in out.items():
        print(k, v["rows"], v["folds"], v["mean_fold_accuracy"], v["pooled_accuracy"], v["stored_accuracy"],
              v["always_low_accuracy"], v["recall"], v["alg3"])


if __name__ == "__main__":
    main()
