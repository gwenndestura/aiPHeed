import json, numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score
OUT = "data/e168/out"
A = pd.concat([pd.read_csv(f"{OUT}/all_rows.csv"), pd.read_csv(f"{OUT}/all_rows_l3_8.csv")], ignore_index=True)
A = A[A["mode"] == "main"]
G = pd.read_csv("data/e158/out/oof.csv")
res = {}
for L in range(1, 9):
    x = G[G["lead"] == L].merge(A[A["lead"] == L][["key", "survey", "lead", "p"]], on=["key", "survey", "lead"])
    y = (x["y_high"] == 1).astype(int); yh = (x["p"] >= .5).astype(int); yp = (x["PERS"] >= .5).astype(int)
    folds = {}
    for s, g in x.groupby("survey"):
        gy = (g["y_high"] == 1).astype(int); gp = (g["p"] >= .5).astype(int); gq = (g["PERS"] >= .5).astype(int)
        folds[s] = {"n": len(g), "acc": round(float((gy == gp).mean()), 3), "pers_acc": round(float((gy == gq).mean()), 3),
                    "auc": round(float(roc_auc_score(gy, g["p"])), 3) if gy.nunique() == 2 else None,
                    "f1_high": round(float(f1_score(gy, gp, zero_division=0)), 3), "n_high": int(gy.sum())}
    def m(pred, score):
        return {"accuracy": round(float((y == pred).mean()), 3),
                "precision_high": round(float(precision_score(y, pred, zero_division=0)), 3),
                "recall_high": round(float(recall_score(y, pred, zero_division=0)), 3),
                "f1_high": round(float(f1_score(y, pred, zero_division=0)), 3),
                "f1_weighted": round(float(f1_score(y, pred, average="weighted")), 3),
                "f1_macro": round(float(f1_score(y, pred, average="macro")), 3),
                "auc_roc": round(float(roc_auc_score(y, score)), 3)}
    res[L] = {"n": len(x), "n_high": int(y.sum()), "E168": m(yh, x["p"]), "persistence": m(yp, x["PERS"]),
              "mean_fold_accuracy": round(float(np.mean([f["acc"] for f in folds.values()])), 3),
              "mean_fold_accuracy_persistence": round(float(np.mean([f["pers_acc"] for f in folds.values()])), 3),
              "folds": folds}
json.dump(res, open(__import__("sys").argv[1], "w"), indent=1)
print(f"{'L':>2} {'n':>3} {'meanFoldAcc':>11} {'pooledAcc':>9} {'Prec':>5} {'Rec':>5} {'F1H':>5} {'F1w':>5} {'AUC':>5} | pers acc F1w AUC | folds")
for L, r in res.items():
    e, p = r["E168"], r["persistence"]
    print(f"{L:>2} {r['n']:>3} {r['mean_fold_accuracy']:>11} {e['accuracy']:>9} {e['precision_high']:>5} {e['recall_high']:>5} {e['f1_high']:>5} {e['f1_weighted']:>5} {e['auc_roc']:>5} | {r['mean_fold_accuracy_persistence']} {p['f1_weighted']} {p['auc_roc']} |",
          {s: (f['acc'], f['auc'], f['n_high'], f['n']) for s, f in r["folds"].items()})
