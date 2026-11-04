"""Objective 2: error-level dataset and survey-label uncertainty (analysis only; no model is fitted or changed).

SWS Balance Luzon design: 600 respondents per round (SWS Q3 2026 media release, in the repository: "600 respondents in
Balance Luzon with +/-4% margin"). Earlier rounds may have used smaller samples, so n = 300 is reported as a
sensitivity scenario. The quarter label is the mean of its r non-commissioned rounds, so its sampling SE is
sqrt(H(1-H)/(n r)) in proportion units (simple random sampling; design effects ignored, which understates the SE).

P(true quarter hunger > 11.3% | observed H) ~ Phi((H - 11.3) / SE) (flat prior). A label is "uncertain" when that
probability is between 0.10 and 0.90. No label is changed: the uncertainty is reported beside the hard labels.

    python obj2_label_uncertainty.py   # -> ../out/obj2_error_level.csv, ../out/obj2_label_uncertainty.json
"""
from __future__ import annotations

import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")

import json
from math import erf, sqrt
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
EXP = HERE.parent
OUT = HERE / "out"
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ce_model as CE  # noqa: E402

PC, N, V, H, R = CE.PC, CE.N, CE.V, CE.H, CE.R
LINE, SCEN = 11.3, (600, 300)
MODELS = ("C-E2", "C-b", "LOGIT", "PERSIST")


def phi(z: float) -> float:
    return 0.5 * (1 + erf(z / sqrt(2)))


def main():
    d = H.load()
    s = d.sws[d.sws["area"] == "BL"]
    rounds = s.groupby("q")["H"].agg(["mean", "count"]).rename(columns={"mean": "H", "count": "rounds"})
    lab = V.area_labels(d)
    lab_bl = lab[lab["area"] == "BL"]
    iv2 = pd.read_csv(EXP / "IMPROVE_V2" / "out" / "forecasts.csv")
    L = pd.read_csv(N.LEADS_FILE)
    CBF = pd.read_csv(N.OUT / "forecasts.csv")
    F = pd.read_csv(OUT / "ce2_fits.csv")
    comp = pd.concat([iv2[iv2["name"] == "LOGIT"][["name", "t", "lead", "q", "p"]],
                      L[L["name"].isin(["PERSIST", "CLIM"])][["name", "t", "lead", "q", "p"]],
                      CBF[CBF["name"] == "C-b"][["name", "t", "lead", "q", "p"]], F[["name", "t", "lead", "q", "p"]]])
    CE._init()
    T = N._G["T"]
    T = T[T["area"] == "BL"].set_index(["t", "lead"])
    yq = lab_bl.set_index("q")["y"]
    rows, summ = [], {"design": {"n_per_round": list(SCEN), "source": "SWS Q3 2026 media release (600, +/-4%)",
                                 "uncertain_band": [0.10, 0.90]}, "leads": {}}
    for k in (1, 2):
        W = R.frame(comp, k, lab_bl).dropna(subset=list(MODELS)).copy()
        th = np.array_split(np.array(sorted(W["q"].unique())), 3)
        third = {q: i + 1 for i, x in enumerate(th) for q in x}
        for _, w in W.iterrows():
            q, t = int(w["q"]), int(w["t"])
            Hq, r = float(rounds.loc[q, "H"]), int(rounds.loc[q, "rounds"])
            pt = {n_: phi((Hq - LINE) / (100 * sqrt((Hq / 100) * (1 - Hq / 100) / (n_ * r)))) for n_ in SCEN}
            x = T.loc[(t, k)] if (t, k) in T.index else None
            avail = int(x[[c for c in CE.CE if c != "lead"]].notna().sum()) if x is not None else None
            p = float(w["C-E2"])
            wrong = (p >= .5) != (w["y"] == 1)
            change = (q - 1) in yq.index and yq[q - 1] != w["y"]
            unc = 0.10 < pt[600] < 0.90
            cat = ("correct" if not wrong else "label-uncertain" if unc else "label-change" if change
                   else "regime-2015-2020" if third[q] == 2 else "other")
            rows.append({"lead": k, "origin": H.qs(t), "target": H.qs(q), "p_C-E2": round(p, 4), "pred": int(p >= .5),
                         "actual": int(w["y"]), "correct": not wrong, "p_distance_from_0.5": round(abs(p - .5), 4),
                         "observed_H": round(Hq, 2), "rounds": r, "H_distance_from_11.3": round(Hq - LINE, 2),
                         "P_true_high_n600": round(pt[600], 3), "P_true_high_n300": round(pt[300], 3),
                         "label_uncertain_n600": unc, "label_change": bool(change), "third": third[q],
                         "inputs_available": avail, "inputs_total": len(CE.CE) - 1, "error_category": cat,
                         **{f"p_{m}": round(float(w[m]), 4) for m in MODELS if m != "C-E2"}})
        E = pd.DataFrame([x for x in rows if x["lead"] == k])
        Lk = {"n": int(len(E)), "uncertain_labels": {str(n_): int(((E[f"P_true_high_n{n_}"] > .1) & (E[f"P_true_high_n{n_}"] < .9)).sum()) for n_ in SCEN},
              "accuracy_ceiling": {str(n_): round(float(np.maximum(E[f"P_true_high_n{n_}"], 1 - E[f"P_true_high_n{n_}"]).mean()), 3)
                                   for n_ in SCEN},
              "errors_by_category": E[~E["correct"]]["error_category"].value_counts().to_dict(),
              "accuracy_certain_vs_uncertain": {
                  "certain": round(float(E[~E["label_uncertain_n600"]]["correct"].mean()), 3),
                  "uncertain": round(float(E[E["label_uncertain_n600"]]["correct"].mean()), 3) if E["label_uncertain_n600"].any() else None},
              "brier_hard_vs_soft": {}}
        for m in MODELS:
            col = "p_C-E2" if m == "C-E2" else f"p_{m}"
            Lk["brier_hard_vs_soft"][m] = {"hard": round(float(((E[col] - E["actual"]) ** 2).mean()), 4),
                                          "soft_n600": round(float(((E[col] - E["P_true_high_n600"]) ** 2).mean()), 4)}
        Lk["inputs_available_min_max"] = [int(E["inputs_available"].min()), int(E["inputs_available"].max())]
        summ["leads"][str(k)] = Lk
    pd.DataFrame(rows).to_csv(OUT / "obj2_error_level.csv", index=False)
    (OUT / "obj2_label_uncertainty.json").write_text(json.dumps(summ, indent=1), encoding="utf-8")
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
