"""Step 1: reproduce the served P0H4 from code and recompute its metrics independently (sklearn only).

- H4 is recomputed at every (origin, lead) of the evaluation rows and compared with LEAD2_OPTIMIZATION's scored value.
- The price part P0 was replayed from code in LEAD2_OPTIMIZATION (out/historical_replay.json, 3 origins, <= 5e-7).
- Metrics at Leads 1-3 are recomputed and compared with backend/data/ch1_engine/evaluation.json.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parents[1]
sys.path.insert(0, str(EXP / "LEAD2_OPTIMIZATION" / "runner"))
import a3 as A3  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.metrics import average_precision_score, confusion_matrix, roc_auc_score  # noqa: E402

OUT = HERE.parent / "out"
L2OUT = EXP / "LEAD2_OPTIMIZATION" / "out"
SERVED = EXP.parents[1] / "backend" / "data" / "ch1_engine" / "evaluation.json"


def metrics(y, p):
    y, p = np.asarray(y, int), np.asarray(p, float)
    yh = (p >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, yh, labels=[0, 1]).ravel()
    rec, spec = tp / (tp + fn), tn / (tn + fp)
    prec = tp / (tp + fp) if tp + fp else float("nan")
    return {"n": int(len(y)), "high": int(y.sum()), "acc": float((yh == y).mean()), "bal": float((rec + spec) / 2),
            "precision": float(prec), "recall": float(rec), "f1": float(2 * prec * rec / (prec + rec)) if tp else 0.0,
            "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn), "false_alarm_rate": float(fp / (fp + tn)),
            "auc": float(roc_auc_score(y, p)), "pr_auc": float(average_precision_score(y, p)),
            "brier": float(np.mean((p - y) ** 2))}


def main():
    A3.U.setup()
    D = pd.read_csv(L2OUT / "predictions_addendum3.csv", dtype={"province_code": str})
    pairs = D[["t", "lead"]].drop_duplicates()
    h = {(int(t), int(k)): A3.h4(int(t), int(k)) for t, k in pairs.itertuples(index=False)}
    raw = np.array([h[(int(t), int(k))] for t, k in zip(D["t"], D["lead"])])
    recomputed = np.where(np.isnan(raw), D["H1"], raw)
    h4_max_diff = float(np.max(np.abs(recomputed - D["pi_H4"])))
    p = recomputed * D["P0_price"]
    ev = json.loads(SERVED.read_text(encoding="utf-8"))
    out = {"h4_recomputed_max_abs_diff": h4_max_diff,
           "product_max_abs_diff_vs_scored": float(np.max(np.abs(p - D["P0H4_p3"]))), "leads": {}}
    for k in (1, 2, 3):
        m = D["lead"] == k
        g = D[m]
        r = metrics(g["y"], p[m.to_numpy()])
        r["quarters"] = int(g["q"].nunique())
        r["targets"] = f"{g['q'].min() // 4}-Q{g['q'].min() % 4 + 1}..{g['q'].max() // 4}-Q{g['q'].max() % 4 + 1}"
        sv = ev["leads"][str(k)]["metrics"]
        r["matches_served_evaluation"] = all(abs(r[a] - sv[b]) < 1e-6 for a, b in
                                             (("acc", "accuracy"), ("bal", "balanced_accuracy"), ("recall", "recall"),
                                              ("brier", "brier")))
        out["leads"][k] = r
        print(k, {a: (round(v, 4) if isinstance(v, float) else v) for a, v in r.items()})
    print("H4 recomputed max diff", h4_max_diff, "| product max diff", out["product_max_abs_diff_vs_scored"])
    (OUT / "p0h4_reproduction.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
