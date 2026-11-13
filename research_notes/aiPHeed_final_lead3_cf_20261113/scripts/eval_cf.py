r"""Scores CF vs FINAL under PROTOCOL_CF (sha 054239a1): thesis Algorithm 3 (mean fold accuracy >= 0.75, stop at first failure) and
Algorithm 4 (F1 HIGH >= 0.75, AUC >= 0.80), Leads 1-8, 5-seed mean probabilities, cut-off 0.50, then the 4-part decision rule.
Run: python -I eval_cf.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, f1_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
K = ["key", "survey", "lead"]
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["province", "y_high"]]
F = pd.concat([pd.read_csv(f) for f in glob.glob(str(RN / "aiPHeed_final_7of7_20261113" / "parts_mix" / "FINALMIX__*.csv"))]).groupby(K, as_index=False)["p_final"].mean().rename(columns={"p_final": "FINAL"})
C = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "parts" / "CF__*.csv"))])
seeds = C.groupby(K)["seed"].nunique().min()
C = C.groupby(K, as_index=False)["p"].mean().rename(columns={"p": "CF"})
D = F.merge(C, on=K).merge(LAB, on=K)
rows = []
for m in ("FINAL", "CF"):
    for L, g in D.groupby("lead"):
        fa = {s: float(((x[m] >= .5) == (x.y_high == 1)).mean()) for s, x in g.groupby("survey")}
        yh = (g[m] >= .5).astype(int)
        rows.append({"model": m, "lead": int(L), **{f"acc_{s[-4:]}": round(v, 4) for s, v in fa.items()}, "mean_fold_accuracy": round(float(np.mean(list(fa.values()))), 4),
                     "f1_high": round(f1_score(g.y_high, yh), 4), "auc": round(roc_auc_score(g.y_high, g[m]), 4), "brier": round(float(((g[m] - g.y_high) ** 2).mean()), 4),
                     "TP/FP/FN": f"{int(((yh == 1) & (g.y_high == 1)).sum())}/{int(((yh == 1) & (g.y_high == 0)).sum())}/{int(((yh == 0) & (g.y_high == 1)).sum())}"})
T = pd.DataFrame(rows)
def mrlt(t):
    k = 0
    for _, r in t.sort_values("lead").iterrows():
        if r.mean_fold_accuracy >= .75: k = r.lead
        else: break
    return int(k)
f, c = T[T.model == "FINAL"].set_index("lead"), T[T.model == "CF"].set_index("lead")
b5 = lambda m: float(((D[D.lead <= 5][m] - D[D.lead <= 5].y_high) ** 2).mean())
rule = {"1_MRLT_CF>=5": mrlt(T[T.model == "CF"]) >= 5,
        "2_mean_fold_acc_not_lower_than_FINAL_minus_0.0133_L1to5": bool(all(c.loc[L, "mean_fold_accuracy"] >= f.loc[L, "mean_fold_accuracy"] - .0133 for L in range(1, 6))),
        "3_pooled_Brier_L1to5_CF<=FINAL": b5("CF") <= b5("FINAL"),
        "4_F1_kept_at_leads_where_FINAL_passes(1,2,4)": bool(all(c.loc[L, "f1_high"] >= .75 for L in (1, 2, 4) if f.loc[L, "f1_high"] >= .75))}
out = {"seeds_per_row_min": int(seeds), "MRLT_FINAL": mrlt(T[T.model == "FINAL"]), "MRLT_CF": mrlt(T[T.model == "CF"]), "brier_L1to5": {"FINAL": round(b5("FINAL"), 4), "CF": round(b5("CF"), 4)},
       "decision_rule": rule, "ADOPT_CF": all(rule.values()), "lead3_F1": {"FINAL": float(f.loc[3, "f1_high"]), "CF": float(c.loc[3, "f1_high"])}}
fl = D[(D.FINAL >= .5) != (D.CF >= .5)][["survey", "lead", "province", "y_high", "FINAL", "CF"]].round(3)
T.to_csv(EV / "CF_vs_FINAL_by_lead.csv", index=False, lineterminator="\n"); fl.to_csv(EV / "CF_class_changes.csv", index=False, lineterminator="\n")
json.dump(out, open(EV / "CF_decision.json", "w"), indent=1, default=bool)
pd.set_option("display.width", 250); print(T.to_string(index=False)); print(json.dumps(out, indent=1, default=bool)); print(fl.to_string(index=False))
