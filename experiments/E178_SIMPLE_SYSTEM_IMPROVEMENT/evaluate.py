"""
E178 step 2: evaluate the registered candidates (candidate_registry.csv, selection_rule.md) on the 156 untainted training rows only.

    cd backend && PYTHONPATH=. python ../experiments/E178_SIMPLE_SYSTEM_IMPROVEMENT/evaluate.py
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import GroupKFold

from app.e164 import auto as U

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("e177dev", HERE.parent / "E177_SIMPLE_V2" / "develop.py")
E177 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E177)
SINGLE = (151, 152, 153, 154, 155)
ENSEMBLES = ((151, 152, 153, 154, 155), (156, 157, 158, 159, 160), (161, 162, 163, 164, 165))


def degenerate(tr, cols):
    """Inputs constant in the training rows, or with <= 2 distinct values that move in lockstep with 'lead'."""
    out = []
    for c in cols:
        if c not in tr or c == "lead":
            continue
        x = tr[c]
        if x.nunique(dropna=True) <= 1:
            out.append(c)
        elif x.nunique(dropna=True) <= 2 and tr.groupby("lead")[c].nunique(dropna=True).max() <= 1:
            out.append(c)
    return out


def score_mu(tr, AN, cfg, folds, seeds):
    return np.mean([E177.oof_scores(tr, AN, cfg, folds, s) for s in seeds], axis=0)


def main():
    tr, AN = E177.training_rows()
    anchor, cfg, _, _ = E177.select(tr, AN)
    drop = degenerate(tr, U.FS[cfg[2]])
    U.FS["K2"] = [c for c in U.FS[cfg[2]] if c not in drop]
    k2 = (cfg[0], cfg[1], "K2")
    ref = (anchor, "GR0P", "FULL")
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    plan = {"K0_SIMPLE": (cfg, "single"), "K1_SEED_ENSEMBLE": (cfg, "ensemble"), "K2_DEGENERATE_INPUTS_REMOVED": (k2, "single"),
            "K3_K1_PLUS_K2": (k2, "ensemble"), "REF_E168CFG": (ref, "single"), "REF_E168CFG_ENSEMBLE": (ref, "ensemble")}
    val, stab = [], []
    for name, (c, kind) in plan.items():
        insts = [E177.oof_scores(tr, AN, c, folds, s) for s in SINGLE] if kind == "single" else [score_mu(tr, AN, c, folds, e) for e in ENSEMBLES]
        mets = [E177.metrics(*E177.probs(tr, mu, folds, "raw")[:3]) for mu in insts]
        primary = mets[0]
        X = np.column_stack(insts)
        cls = X >= 0
        val.append({"candidate": name, "config": "|".join(c), "inputs": len(U.FS[c[2]]), "instances": f"{len(insts)} {'single seeds' if kind == 'single' else '5-seed ensembles'}",
                    **{k: primary[k] for k in ("accuracy", "brier_vs_q", "roc_auc", "calibration_slope_logit", "calibration_intercept_logit")},
                    "brier_sd_across_instances": round(float(np.std([m["brier_vs_q"] for m in mets])), 5),
                    "accuracy_range_across_instances": f"{min(m['accuracy'] for m in mets):.4f}-{max(m['accuracy'] for m in mets):.4f}",
                    "population": "156 untainted FNRI2015 training rows, region folds"})
        stab.append({"candidate": name, "instances": len(insts), "kind": kind, "mean_score_sd": round(float(X.std(axis=1).mean()), 4),
                     "max_score_sd": round(float(X.std(axis=1).max()), 4), "rows_changing_class": int((cls.any(axis=1) & ~cls.all(axis=1)).sum()), "rows": len(tr)})
    V, S = pd.DataFrame(val), pd.DataFrame(stab)
    k0 = V.set_index("candidate").loc["K0_SIMPLE"]
    k0_flips = int(S.set_index("candidate").loc["K0_SIMPLE", "rows_changing_class"])
    noise = 2 * float(k0["brier_sd_across_instances"])
    dec = []
    for r in V.itertuples(index=False):
        if r.candidate.startswith("REF") or r.candidate == "K0_SIMPLE":
            dec.append("reference")
            continue
        acc_ok = r.accuracy >= k0["accuracy"]
        brier_ok = (k0["brier_vs_q"] - r.brier_vs_q) > noise
        stab_ok = int(S.set_index("candidate").loc[r.candidate, "rows_changing_class"]) < k0_flips
        dec.append("predictive + stability improvement" if acc_ok and brier_ok and stab_ok else
                   "stability improvement only (predictive unverified)" if stab_ok and acc_ok else
                   "stability improvement, but accuracy below K0" if stab_ok else "no improvement")
    V["decision_by_registered_rule"] = dec
    V.to_csv(HERE / "training_only_validation.csv", index=False, lineterminator="\n")
    S.to_csv(HERE / "stability_analysis.csv", index=False, lineterminator="\n")
    pd.DataFrame({"input_removed_in_K2": drop}).to_csv(HERE / "k2_removed_inputs.csv", index=False, lineterminator="\n")
    print("SIMPLE choice", cfg, "| K2 removes", drop, "| Brier noise threshold", round(noise, 5))
    print(V.drop(columns=["population"]).to_string(index=False))
    print(S.to_string(index=False))


if __name__ == "__main__":
    main()
