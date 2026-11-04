"""Objective 4 table (read only): every model and baseline on identical quarters, Leads 1-2, with the same metrics.

Rows: C-b, C-E2, C-E5 candidates, and the 7 baselines + CLIM. Same verdict quarters (`R.frame`); the news-only
comparators also on the news era, as in the Holm family.

    python obj4_table.py      # -> ../out/obj4_table.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
OUT = HERE / "out"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_model as CE  # noqa: E402

PC, N, V, H, R, A = CE.PC, CE.N, CE.V, CE.H, CE.R, CE.A


def metrics(g: pd.DataFrame, n: str) -> dict:
    g = g[g[n].notna()]
    p, y = g[n].to_numpy(float), g["y"].to_numpy(int)
    c = (p >= .5).astype(int)
    tp, tn, fp, fn = int(((c == 1) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum()), int(((c == 1) & (y == 0)).sum()), \
        int(((c == 0) & (y == 1)).sum())
    pr = tp / (tp + fp) if tp + fp else 0.0
    rc = tp / (tp + fn) if tp + fn else 0.0
    return {"n": int(len(g)), "accuracy": round(float((c == y).mean()), 3),
            "balanced": round(float((rc + (tn / (tn + fp) if tn + fp else 0.0)) / 2), 3),
            "precision": round(pr, 3), "recall": round(rc, 3), "f1": round(2 * pr * rc / (pr + rc), 3) if pr + rc else 0.0,
            "auc": round(float(roc_auc_score(y, p)), 3) if len(set(y)) == 2 and len(set(p)) > 1 else None,
            "brier": round(float(np.mean((p - y) ** 2)), 4), "TP": tp, "FP": fp, "FN": fn, "TN": tn}


def main():
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    h3 = pd.read_csv(EXP / "OBJECTIVES_COMPLETION" / "out" / "h3_forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    CBF = pd.read_csv(N.OUT / "forecasts.csv")
    parts = [iv2[iv2["name"].isin(["LOGIT", "PSA-only", "NLP-only"])], h3, L[L["name"].isin(["PERSIST", "CLIM"])],
             CBF[CBF["name"] == "C-b"], pd.read_csv(OUT / "ce2_fits.csv")]
    if (OUT / "ce5_fits.csv").exists():
        parts.append(pd.read_csv(OUT / "ce5_fits.csv"))
    comp = pd.concat([x[["name", "t", "lead", "q", "p"]] for x in parts], ignore_index=True)
    names = [n for n in ["C-b", "C-E2", "C-E5R", "C-E5C", "C-E2-NONEWS", "PERSIST", "CLIM", "LOGIT", "PSA-only",
                         "NLP-only", "LGBM-GOV", "LGBM-NLP", "ALWAYS-HIGH"] if n in set(comp["name"]) | {"ALWAYS-HIGH"}]
    res = {"label": "same quarters for every row; news-era rows (t >= NEWS_ERA) reported separately", "leads": {}}
    for k in (1, 2):
        W = R.frame(comp, k, lab_bl)
        era = W[W["t"] >= V.NEWS_ERA]
        res["leads"][str(k)] = {"all_62": {n: metrics(W, n) for n in names},
                                "news_era": {n: metrics(era, n) for n in names},
                                "news_era_quarters": int(len(era))}
    (OUT / "obj4_table.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, x in res["leads"].items():
        print(f"Lead {k} (62 quarters; news era {x['news_era_quarters']})")
        for n, m in x["all_62"].items():
            print(f"  {n:12s} n {m['n']:3d} acc {m['accuracy']:.3f} bal {m['balanced']:.3f} P {m['precision']:.3f} "
                  f"R {m['recall']:.3f} F1 {m['f1']:.3f} AUC {m['auc']} Brier {m['brier']:.4f}")


if __name__ == "__main__":
    main()
