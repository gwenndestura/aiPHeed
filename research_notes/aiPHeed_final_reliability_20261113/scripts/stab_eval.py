r"""Scores the G10a (training-round removal) and G10b (unseen provinces) refits of stab_jobs.py against the full FINAL fit on the same
Lead-1 rows. 5-seed mean probabilities; cut-off 0.50. Run: python -I stab_eval.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parents[1]; EV = HERE / "evidence"
K = ["key", "survey"]
REL = pd.read_csv(EV / "REL_rows_L1to5.csv"); REL = REL[REL.lead == 1]


def met(y, p):
    y, p = np.asarray(y, int), np.asarray(p, float); h = p >= .5
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    return {"n": len(y), "high": int(y.sum()), "accuracy": round((tp + tn) / len(y), 4), "recall_high": round(tp / max(1, tp + fn), 4),
            "precision_high": round(tp / (tp + fp), 4) if tp + fp else None, "brier": round(float(np.mean((p - y) ** 2)), 4), "TP/FP/FN/TN": f"{tp}/{fp}/{fn}/{tn}"}


X = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "parts" / "*.csv"))])
rows = []
for (kind, what, sv), x in X.groupby(["kind", "what", "survey"]):
    z = x.groupby(K, as_index=False).agg(p=("p", "mean"), seeds=("seed", "nunique"), train_rows=("train_rows", "first"),
                                         train_rows_full=("train_rows_full", "first"), train_rounds=("train_rounds", "first")).merge(REL[K + ["y_high", "FINAL"]], on=K)
    a, b = met(z.y_high, z.p), met(z.y_high, z.FINAL)
    rows.append({"test": "G10a drop training round" if kind == "dropround" else "G10b unseen provinces", "fold": sv, "removed": what, "seeds": int(z.seeds.min()),
                 "train_rows": int(z.train_rows.iloc[0]), "train_rows_full": int(z.train_rows_full.iloc[0]), "train_rounds_used": z.train_rounds.iloc[0],
                 **{f"refit_{k}": v for k, v in a.items()}, "full_accuracy": b["accuracy"], "full_recall_high": b["recall_high"], "full_brier": b["brier"],
                 "class_flips_vs_full": int(((z.p >= .5) != (z.FINAL >= .5)).sum())})
rows.append({"test": "G10a drop training round", "fold": "ENNS2019", "removed": "FNRI2015", "seeds": 0, "train_rounds_used": "ENNS2018",
             "note": "NOT EXECUTABLE: the 2019 fold trains on FNRI2015 only (ENNS2018 not yet released at the 2019 origin, 6-quarter lag), so removing 2015 leaves no training rows (GroupKFold n_splits=0); failure kept in evidence/run_stab.log"})
T = pd.DataFrame(rows)
T["note"] = np.where((T.fold == "ENNS2019") & (T.removed == "ENNS2018"), "NO-OP: ENNS2018 is not in the 2019 fold's training rows (not released at the origin); identical to the full fit", T["note"])
# pooled unseen-province result across the three folds
U = X[X.kind == "unseen"].groupby(K, as_index=False)["p"].mean().merge(REL[K + ["y_high", "FINAL"]], on=K)
pool = {"unseen_pooled": met(U.y_high, U.p), "full_pooled_same_rows": met(U.y_high, U.FINAL),
        "unseen_by_round": {s: met(x.y_high, x.p) for s, x in U.groupby("survey")}}
G10a = T[(T.test.str.startswith("G10a")) & T.refit_accuracy.notna() & (T.fold == "ENNS2021")]
gate = {"G10a_all_executable_refits_acc>=.70": bool((G10a.refit_accuracy >= .70).all()), "G10a_executable": int(len(G10a)), "G10a_not_executable_or_noop": 2, "G10a_max_flips_vs_full": int(G10a.class_flips_vs_full.max()), "G10a_recall_range": [float(G10a.refit_recall_high.min()), float(G10a.refit_recall_high.max())],
        "G10b_unseen_acc>=.70_and_recall>=.50": bool(pool["unseen_pooled"]["accuracy"] >= .70 and pool["unseen_pooled"]["recall_high"] >= .50)}
T.to_csv(EV / "STAB_round_and_province_refits.csv", index=False, lineterminator="\n")
json.dump({"pooled": pool, "gates": gate}, open(EV / "STAB_summary.json", "w"), indent=1)
pd.set_option("display.width", 300); pd.set_option("display.max_columns", 30)
print(T.drop(columns=["note"], errors="ignore").to_string(index=False)); print(json.dumps(pool, indent=1)); print(gate)
