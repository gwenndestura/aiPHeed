"""
E179 scoring (EXPLORATORY; test-informed comparison disclosed). Reads all_rows.csv written by run.py; recomputes nothing.
Labels and baselines come from the frozen E168 oof file. C1-C6 via the unchanged app.e156.leads.evaluate.

    cd backend && PYTHONPATH=. python ../experiments/E179_AGGRESSIVE_SIMPLE_OPTIMIZATION/score.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from app.e156 import leads as LD
from app.e171 import candidates as C171
from app.paths import BACKEND_DIR

H = Path(__file__).resolve().parent
KEY = ["key", "survey", "lead"]


def load():
    A = pd.read_csv(H / "all_rows.csv")
    main, cor = A[A["mode"] == "main"].copy(), A[A["mode"] == "corrupt"].copy()
    E = pd.read_csv(BACKEND_DIR / "data" / "e168" / "out" / "oof.csv")
    E = E[E["lead"].isin([1, 2, 3])][KEY + ["province", "region", "y_true", "y_high", "q_true", "PERS", "L", "mu_L", "half_L"]]
    E = E.rename(columns={"L": "E168", "mu_L": "mu_E168", "half_L": "half_E168"})
    S = pd.read_csv(BACKEND_DIR / "data" / "e172" / "out" / "oof.csv")[KEY + ["SIMPLE", "mu_SIMPLE", "half_SIMPLE"]]
    F = E.merge(S, on=KEY, how="left").merge(main, on=KEY, how="inner")
    return F, main, cor


def arms(F):
    names = [c[3:] for c in F.columns if c.startswith("p::")]
    for n in names:
        F[n] = F[f"p::{n}"]
        F[f"mu_{n}"] = F[f"mu::{n}"] if f"mu::{n}" in F else np.log(F[n] / (1 - F[n]))
        F[f"half_{n}"] = F[f"half::{n}"] if f"half::{n}" in F else np.nan
    return names


def main():
    F, main_, cor = load()
    names = arms(F)
    F["mu_TS_THR"] = F["mu_TS"]
    rows = []
    rel = {}
    for a in ["E168", "SIMPLE"] + names:
        if a not in F or F[a].isna().any():
            continue
        r = LD.evaluate(F, a, a)
        rel[a] = r
        for l in r["leads"]:
            c = l["confusion"]
            x = C171.extra(F[F["lead"] == l["lead"]].reset_index(drop=True), a)
            rows.append({"candidate_id": a, "lead": l["lead"], "correct": c["tp"] + c["tn"], "accuracy": l["accuracy"], "c1_low_bound": l["accuracy_95_low_effective_n"],
                         "majority": l["majority_rule"], "false_HIGH": c["fp"], "false_LOW": c["fn"], "precision": l["precision"], "recall": l["high_recall"],
                         "f1": l["f1"], "balanced_accuracy": l["balanced_accuracy"], "roc_auc": l["auc"], "pr_auc": x["pr_auc"], "brier": l["brier_soft"],
                         "cal_slope": x["slope"], "cal_intercept": x["intercept"], **{k: bool(v) for k, v in l["criteria"].items()},
                         "C1_C6_all": bool(l["reliable"])})
    R = pd.DataFrame(rows)
    R.to_csv(H / "experiment_results.csv", index=False, lineterminator="\n")
    grid = R[R["candidate_id"].str.contains(r"\|") & (R["lead"] == 2)].sort_values(["correct", "brier"], ascending=[False, True])
    best = grid.iloc[0]["candidate_id"]
    leak = float(np.max(np.abs(main_.sort_values(KEY)["p::TS"].values[:0] if False else 0.0)))
    m1 = main_[main_["lead"].isin([1, 2])].sort_values(KEY)[KEY + ["p::TS"]]
    c1 = cor.sort_values(KEY)[KEY + ["p::TS"]]
    lk = m1.merge(c1, on=KEY, suffixes=("", "_c"))
    leak = float(np.max(np.abs(lk["p::TS"] - lk["p::TS_c"])))
    # error analysis (Lead 2): E168 vs SIMPLE vs TS vs BEST72
    g = F[F["lead"] == 2].copy()
    for a in ("E168", "SIMPLE", "TS", best):
        g[f"{a}_correct"] = (g[a] >= .5) == (g["y_high"] == 1)
    g[["province", "survey", "y_high", "E168", "SIMPLE", "TS", best] + [f"{a}_correct" for a in ("E168", "SIMPLE", "TS", best)]].round(4).to_csv(
        H / "error_analysis.csv", index=False, lineterminator="\n")
    # calibration comparison
    R[R["candidate_id"].isin(["E168", "SIMPLE", "TS", "TS_THR", best])][["candidate_id", "lead", "brier", "cal_slope", "cal_intercept", "roc_auc"]].to_csv(
        H / "calibration_comparison.csv", index=False, lineterminator="\n")
    # stability: single seed vs 5-seed ensemble, same settings and inputs (class agreement on all 216 forecasts)
    st = []
    for r_, f_ in (("R0", "GOV"), ("R2", "GOV"), ("R0", "GOV_A"), ("R2", "GOV_A")):
        s1, s5 = F[f"{r_}|{f_}|seeds1"], F[f"{r_}|{f_}|seeds5"]
        st.append({"settings": r_, "inputs": f_, "class_differences_single_vs_5seed": int(((s1 >= .5) != (s5 >= .5)).sum()), "rows": len(F),
                   "mean_abs_p_diff": round(float((s1 - s5).abs().mean()), 4)})
    pd.DataFrame(st).to_csv(H / "stability_analysis.csv", index=False, lineterminator="\n")
    # feature importance of the training-selected configuration
    fi = [{"survey": s, "lead": int(l), "TS_config": c, **{"top_inputs": "; ".join(f"{k} {v}" for k, v in json.loads(j).items())}}
          for (s, l), (c, j) in main_.groupby(["survey", "lead"])[["TS_cfg", "TS_importance"]].first().iterrows()]
    pd.DataFrame(fi).to_csv(H / "feature_importance.csv", index=False, lineterminator="\n")
    # comparison table
    pick = {"E168": "E168 (locked, served)", "SIMPLE": "SIMPLE (E172 post-hoc)", "TS": "E179 TS (training-only selection)",
            "TS_THR": "E179 TS + training-only threshold", best: f"E179 BEST72 = {best} (TEST-INFORMED)"}
    C = R[R["candidate_id"].isin(pick)].assign(model=lambda d: d["candidate_id"].map(pick))
    C.to_csv(H / "evaluation_comparison.csv", index=False, lineterminator="\n")
    dist = grid["correct"]
    out = {"configurations": len([n for n in names if "|" in n]), "lead2_correct_distribution": {"min": int(dist.min()), "median": float(dist.median()),
           "max": int(dist.max())}, "best72": best, "leakage_TS_max_abs_change": leak, "E168_lead2": int(R[(R.candidate_id == "E168") & (R.lead == 2)]["correct"].iloc[0]),
           "TS_lead2": int(R[(R.candidate_id == "TS") & (R.lead == 2)]["correct"].iloc[0])}
    (H / "summary.json").write_text(json.dumps(out, indent=1), newline="\n")
    print(json.dumps(out, indent=1))
    print(C[["model", "lead", "correct", "accuracy", "c1_low_bound", "f1", "roc_auc", "brier", "C1_C6_all"]].to_string(index=False))
    print(pd.DataFrame(st).to_string(index=False))
    print({p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:10] for p in H.glob("*.csv")})


if __name__ == "__main__":
    main()
