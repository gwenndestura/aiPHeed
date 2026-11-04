"""Objective 2 failure diagnosis for C-E2 (read only: stored walk-forward forecasts, no model fitted).

Why does C-E2 fail R3 (balanced accuracy) and R7 (stability over thirds)? For Leads 1-2 on the 62 verdict quarters:
confusion matrix, LOW recall, errors near the 11.3% line, accuracy on label changes vs repeats, the base rate and
accuracy per third, calibration bins, and the same figures for LOGIT and persistence on the same quarters.

    python obj2_diagnostics.py      # -> ../out/obj2_diagnostics.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
OUT = HERE / "out"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_model as CE  # noqa: E402

PC, N, V, H, R = CE.PC, CE.N, CE.V, CE.H, CE.R
NEAR = 2.0          # points from the 11.3% line treated as "near the line" (reported, not tuned)
MODELS = ("C-E2", "C-b", "LOGIT", "PERSIST")


def _stats(g: pd.DataFrame, n: str) -> dict:
    c = (g[n] >= .5).astype(int)
    y = g["y"].astype(int)
    tp, tn = int(((c == 1) & (y == 1)).sum()), int(((c == 0) & (y == 0)).sum())
    fp, fn = int(((c == 1) & (y == 0)).sum()), int(((c == 0) & (y == 1)).sum())
    return {"n": int(len(g)), "accuracy": round(float((c == y).mean()), 3) if len(g) else None,
            "high_recall": round(tp / (tp + fn), 3) if tp + fn else None,
            "low_recall": round(tn / (tn + fp), 3) if tn + fp else None, "TP": tp, "TN": tn, "FP": fp, "FN": fn}


def main():
    d = H.load()
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    CBF = pd.read_csv(N.OUT / "forecasts.csv")
    F = pd.read_csv(OUT / "ce2_fits.csv")
    comp = pd.concat([iv2[iv2["name"] == "LOGIT"][["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      CBF[CBF["name"] == "C-b"][["name", "t", "lead", "q", "p"]],
                      F[["name", "t", "lead", "q", "p"]]], ignore_index=True)
    Hq = lab_bl.set_index("q")["H"]
    yq = lab_bl.set_index("q")["y"]
    res = {"label": "read-only diagnosis of stored walk-forward forecasts", "near_line_points": NEAR, "leads": {}}
    for k in (1, 2):
        W = R.frame(comp, k, lab_bl).dropna(subset=list(MODELS)).copy()
        W["H"] = W["q"].map(Hq)
        W["prev_y"] = W["q"].map(lambda q: yq.get(q - 1))
        W["change"] = W["prev_y"].notna() & (W["prev_y"] != W["y"])
        W["near"] = (W["H"] - 11.3).abs() <= NEAR
        th = np.array_split(np.array(sorted(W["q"].unique())), 3)
        Lk = {"n": int(len(W)), "base_rate_high": round(float(W["y"].mean()), 3), "models": {}}
        for n in MODELS:
            m = {"all": _stats(W, n), "label_change": _stats(W[W["change"]], n), "label_repeat": _stats(W[~W["change"]], n),
                 "near_line": _stats(W[W["near"]], n), "far_from_line": _stats(W[~W["near"]], n),
                 "thirds": [{"period": f"{H.qs(int(x.min()))}..{H.qs(int(x.max()))}",
                             "base_rate_high": round(float(W[W["q"].isin(x)]["y"].mean()), 3),
                             **_stats(W[W["q"].isin(x)], n)} for x in th]}
            Lk["models"][n] = m
        e = W[(W["C-E2"] >= .5) != (W["y"] == 1)]
        Lk["C-E2_errors"] = [{"q": H.qs(int(r.q)), "observed_H": round(float(r.H), 1), "y": int(r.y),
                              "p": round(float(r["C-E2"]), 3), "label_change": bool(r.change), "near_line": bool(r.near),
                              "persistence_also_wrong": bool((r["PERSIST"] >= .5) != (r.y == 1))}
                             for _, r in e.iterrows()]
        bins = pd.cut(W["C-E2"], [0, .3, .5, .7, .85, 1.0], include_lowest=True)
        Lk["C-E2_calibration"] = [{"bin": str(b), "n": int(len(g)), "mean_p": round(float(g["C-E2"].mean()), 3),
                                   "observed_high": round(float(g["y"].mean()), 3)} for b, g in W.groupby(bins, observed=True)]
        Lk["C-E2_mean_p_by_class"] = {str(int(c)): round(float(g["C-E2"].mean()), 3) for c, g in W.groupby("y")}
        Lk["n_label_changes"] = int(W["change"].sum())
        Lk["n_near_line"] = int(W["near"].sum())
        res["leads"][str(k)] = Lk
    (OUT / "obj2_diagnostics.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    for k, Lk in res["leads"].items():
        print(f"Lead {k}: n {Lk['n']}, base rate HIGH {Lk['base_rate_high']}, label changes {Lk['n_label_changes']}, "
              f"near line {Lk['n_near_line']}; C-E2 mean p by class {Lk['C-E2_mean_p_by_class']}")
        for n, m in Lk["models"].items():
            print(f"  {n:8s} all {m['all']['accuracy']} LOWrec {m['all']['low_recall']} | change {m['label_change']['accuracy']}"
                  f" (n {m['label_change']['n']}) repeat {m['label_repeat']['accuracy']} | near {m['near_line']['accuracy']}"
                  f" far {m['far_from_line']['accuracy']} | thirds "
                  f"{[(t['period'], t['base_rate_high'], t['accuracy'], t['low_recall']) for t in m['thirds']]}")
        print("  calibration", Lk["C-E2_calibration"])
        print("  errors", [(x["q"], x["observed_H"], x["p"], "chg" if x["label_change"] else "", "near" if x["near_line"] else "",
                            "P-wrong" if x["persistence_also_wrong"] else "") for x in Lk["C-E2_errors"]])


if __name__ == "__main__":
    main()
