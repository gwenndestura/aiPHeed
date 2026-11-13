r"""Thesis Chapter III Section 3.4 Algorithm 3 (MRLT) and Algorithm 4 targets for FINAL (RATE + MIND), Leads 1-8, from the EXISTING
5-seed walk-forward fits (../aiPHeed_final_7of7_20261113/parts_mix, p_final; 110 fits). No refit, no threshold change (0.50).
Folds = survey rounds (ENNS 2018, 2019, 2021): each fold trains only on rounds released before its origin (expanding window) with a
gap of k quarters between origin and target. Rule: mean fold accuracy >= 0.75; stop at the first failing k; MRLT = last passing k.
Run: python -I algorithm3.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, f1_score

HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
K = ["key", "survey", "lead"]
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
X = pd.concat([pd.read_csv(f) for f in glob.glob(str(RN / "aiPHeed_final_7of7_20261113" / "parts_mix" / "FINALMIX__*.csv"))])
meta = {(d["survey"], d["lead"], d["seed"]): d for d in (json.load(open(f)) for f in glob.glob(str(RN / "aiPHeed_final_stability_lead_20261113" / "features_lead" / "FINALL__*.json")))}
M = X.groupby(K, as_index=False).agg(p=("p_final", "mean"), origin=("origin", "first")).merge(LAB[K + ["province", "y_high", "PERS"]], on=K)
S = X.merge(LAB[K + ["y_high"]], on=K)
folds, leads = [], []
for (L, sv), g in M.groupby(["lead", "survey"]):
    m = meta[(sv, L, 168)]
    yhat = (g.p >= .5).astype(int)
    hist_q = int(m["origin"]) - 8054                       # quarters of HFIAS history (NNS 2013 Q3 onward) available at the origin
    folds.append({"lead": int(L), "fold_test_round": sv, "origin_qi": int(m["origin"]), "train_rounds": "+".join(sorted(m["train_rounds"])),
                  "train_rows": m["train_rows"], "quarters_of_history_at_origin": hist_q, "min_8_quarters": hist_q >= 8,
                  "gap_quarters": int(L), "n": len(g), "high": int(g.y_high.sum()), "accuracy": round(float((yhat == g.y_high).mean()), 4),
                  "persistence_accuracy": round(float(((g.PERS >= .5).astype(int) == g.y_high).mean()), 4),
                  "seed_accuracies": [round(float(((x.p_final >= .5).astype(int) == x.y_high).mean()), 4) for _, x in S[(S.lead == L) & (S.survey == sv)].groupby("seed")]})
F = pd.DataFrame(folds)
mrlt, stopped, first_fail = 0, False, None
for L, g in M.groupby("lead"):
    f = F[F.lead == L]; mfa = float(f.accuracy.mean()); yhat = (g.p >= .5).astype(int)
    tp = int(((yhat == 1) & (g.y_high == 1)).sum()); fp = int(((yhat == 1) & (g.y_high == 0)).sum()); fn = int(((yhat == 0) & (g.y_high == 1)).sum())
    passed = mfa >= .75
    if not stopped:
        if passed: mrlt = int(L)
        else: stopped, first_fail = True, int(L)
    leads.append({"lead": int(L), "folds": len(f), "fold_accuracies": dict(zip(f.fold_test_round, f.accuracy)), "mean_fold_accuracy": round(mfa, 4),
                  "threshold": 0.75, "result": "PASS" if passed else "FAIL", "considered_by_algorithm3": int(L) <= (first_fail or 99),
                  "passing_folds": int((f.accuracy >= .75).sum()), "failing_folds": int((f.accuracy < .75).sum()),
                  "pooled_accuracy": round(float((yhat == g.y_high).mean()), 4), "precision_high": round(tp / max(1, tp + fp), 4),
                  "recall_high": round(tp / max(1, tp + fn), 4), "f1_high": round(f1_score(g.y_high, yhat), 4),
                  "f1_weighted": round(f1_score(g.y_high, yhat, average="weighted"), 4), "f1_macro": round(f1_score(g.y_high, yhat, average="macro"), 4),
                  "auc_roc": round(roc_auc_score(g.y_high, g.p), 4), "F1_high>=0.75": f1_score(g.y_high, yhat) >= .75, "AUC>=0.80": roc_auc_score(g.y_high, g.p) >= .8,
                  "persistence_mean_fold_accuracy": round(float(f.persistence_accuracy.mean()), 4), "TP/FP/FN": f"{tp}/{fp}/{fn}", "n": len(g)})
T = pd.DataFrame(leads)
F.to_csv(EV / "A3_folds.csv", index=False, lineterminator="\n"); T.to_csv(EV / "A3_leads.csv", index=False, lineterminator="\n")
json.dump({"MRLT": mrlt, "first_failing_lead": first_fail, "rule": "mean fold accuracy >= 0.75, stop at first failure (thesis Algorithm 3)"}, open(EV / "A3_mrlt.json", "w"), indent=1)
pd.set_option("display.width", 300); pd.set_option("display.max_columns", 30)
print(T.drop(columns=["fold_accuracies"]).to_string(index=False)); print(F.drop(columns=["seed_accuracies"]).to_string(index=False)); print("MRLT", mrlt, "first fail", first_fail)
