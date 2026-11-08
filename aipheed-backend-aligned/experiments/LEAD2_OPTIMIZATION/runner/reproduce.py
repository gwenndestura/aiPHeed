"""Step 1: independent reproduction of the UNI-FINAL Lead-2 numbers from out/predictions.csv (no project metric code)."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, roc_auc_score, average_precision_score

HERE = Path(__file__).resolve().parent
UNI = HERE.parents[1] / "FINAL_UNIFIED_LGBM" / "out"
OUT = HERE.parent / "out"


def qs(q):
    return f"{q // 4}-Q{q % 4 + 1}"


def metrics(y, p, cut=0.5):
    y = np.asarray(y, int)
    p = np.asarray(p, float)
    yh = (p >= cut).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, yh, labels=[0, 1]).ravel()
    rec = tp / (tp + fn) if tp + fn else float("nan")
    spec = tn / (tn + fp) if tn + fp else float("nan")
    prec = tp / (tp + fp) if tp + fp else float("nan")
    f1 = 2 * prec * rec / (prec + rec) if tp else 0.0
    return {"n": int(len(y)), "acc": float((yh == y).mean()), "bal": float((rec + spec) / 2), "prec": prec,
            "rec": rec, "f1": f1, "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
            "brier": float(np.mean((p - y) ** 2)),
            "auc": float(roc_auc_score(y, p)) if len(set(y)) == 2 else None,
            "ap": float(average_precision_score(y, p)) if len(set(y)) == 2 else None}


def main():
    D = pd.read_csv(UNI / "predictions.csv", dtype={"province_code": str})
    res = json.loads((UNI / "results.json").read_text())
    out = {}
    for k in (1, 2, 3):
        g = D[D["lead"] == k]
        m = metrics(g["y"], g["UNI_p"])
        m["quarters"] = int(g["q"].nunique())
        m["high_share"] = float(g["y"].mean())
        m["origins"] = sorted({qs(int(t)) for t in g["t"]})[:1] + ["..."] + sorted({qs(int(t)) for t in g["t"]})[-1:]
        m["targets"] = [qs(int(q)) for q in sorted(g["q"].unique())]
        m["baselines"] = {b: metrics(g["y"], g[f"{b}_p"].clip(0, 1)) for b in ("ALWAYS-LOW", "PERSIST-SI", "CLIM")}
        m["dup_rows"] = int(g.duplicated(["t", "province_code"]).sum())
        rep = res["leads"][str(k)]["metrics"]
        m["reported"] = {"acc": rep["accuracy"], "bal": rep["balanced_accuracy"], "prec": rep["precision"],
                         "rec": rep["recall"], "brier": rep["brier"]}
        m["matches_report"] = all(abs(m[a] - m["reported"][a]) < 1e-6 for a in ("acc", "bal", "prec", "rec", "brier"))
        out[k] = m
        print(k, {a: round(m[a], 3) if isinstance(m[a], float) else m[a] for a in
                  ("n", "quarters", "acc", "bal", "prec", "rec", "f1", "tp", "fp", "fn", "tn", "brier", "auc", "ap",
                   "high_share", "matches_report", "dup_rows")})
        for b, bm in m["baselines"].items():
            print("   ", b, round(bm["acc"], 3), "bal", round(bm["bal"], 3), "brier", round(bm["brier"], 3))
    (OUT / "baseline_reproduction.json").write_text(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
