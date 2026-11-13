r"""PROTOCOL_OPT2 (sha f3a6fdf7) scoring of LG: 5-seed mean and every seed, each round, pooled; 2018/2019 identity with FINAL; decision rule.
Same metric definitions as opt_eval.py. Run: python -I opt2_eval.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
K = ["key", "survey", "lead"]; RNDS = ["ENNS2018", "ENNS2019", "ENNS2021"]
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["province", "y_high", "PERS"]]
LAB = LAB[LAB.lead == 1]
ll = lambda y, p: float(-np.mean(y * np.log(np.clip(p, 1e-6, 1 - 1e-6)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1 - 1e-6))))


def met(y, p):
    y = np.asarray(y, int); p = np.asarray(p, float); h = p >= .5
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    r = tp / max(1, tp + fn); pr = tp / (tp + fp) if tp + fp else 0.0; sp = tn / max(1, tn + fp)
    return {"recall": r, "f1": 2 * pr * r / (pr + r) if tp else 0.0, "precision": pr, "ba": (r + sp) / 2, "brier": float(np.mean((p - y) ** 2)),
            "accuracy": (tp + tn) / len(y), "roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p), "prev": float(y.mean()),
            "logloss": ll(y, p), "cm": f"{tp}/{fp}/{fn}/{tn}"}


ok = lambda m: all([m["recall"] >= .7, m["f1"] >= .7, m["precision"] >= .7, m["ba"] >= .7, m["brier"] <= .2, m["accuracy"] >= .75,
                    m["roc_auc"] >= .7, m["pr_auc"] > m["prev"]])
LG = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "parts" / "LG__*.csv"))])
FI = pd.concat([pd.read_csv(f, usecols=K + ["seed", "p"]) for f in glob.glob(str(RN / "aiPHeed_hcw_final_optimization_20261112" / "parts_fwd" / "FINAL__ENNS20*__1__*.csv"))])
idm = LG.merge(FI, on=K + ["seed"], suffixes=("", "_final"))
ident = {s: float((g.p - g.p_final).abs().max()) for s, g in idm.groupby("survey")}
rows = []
for nm, src in [("LG_mean", LG.groupby(K, as_index=False)["p"].mean()), ("FINAL_mean", FI.groupby(K, as_index=False)["p"].mean())] + \
               [(f"LG_seed{s}", g[K + ["p"]]) for s, g in LG.groupby("seed")]:
    d = LAB.merge(src, on=K)
    for s, x in list(d.groupby("survey")) + [("POOLED", d)]:
        m = met(x.y_high, x.p)
        rows.append({"model": nm, "round": s, **{k: round(v, 4) for k, v in m.items() if k != "cm"}, "TP/FP/FN/TN": m["cm"], "all_8_pass": ok(m)})
R = pd.DataFrame(rows); R.to_csv(EV / "OPT2_LG_per_round_L1.csv", index=False, lineterminator="\n")
pb = met(LAB.y_high, LAB.PERS)["brier"]
mean_ok = R[(R.model == "LG_mean") & R["round"].isin(RNDS)].all_8_pass.all()
seed_ok = R[R.model.str.startswith("LG_seed") & R["round"].isin(RNDS)].all_8_pass.all()
pool_b = float(R[(R.model == "LG_mean") & (R["round"] == "POOLED")].brier.iloc[0])
D = LAB.merge(LG.groupby(K, as_index=False)["p"].mean().rename(columns={"p": "LG"}), on=K).merge(
    FI.groupby(K, as_index=False)["p"].mean().rename(columns={"p": "FINAL"}), on=K)
D[D.survey == "ENNS2021"].sort_values("LG", ascending=False).to_csv(EV / "OPT2_LG_2021_rows.csv", index=False, lineterminator="\n")
v = {"identity_with_FINAL_2018_2019_max_abs_p_diff": ident, "LG_mean_all8_every_round": bool(mean_ok), "LG_every_seed_all8_every_round": bool(seed_ok),
     "pooled_brier": pool_b, "persistence_pooled_brier": pb, "pooled_brier_beats_persistence": pool_b < pb,
     "n_pairs_2021": int(LG[LG.survey == "ENNS2021"].n_pairs.iloc[0]), "n_train_2021": int(LG[LG.survey == "ENNS2021"].n_train.iloc[0])}
v["DECISION"] = "LG passes the locked rule: seal as prospective challenger (not validated, not dashboard)" if (mean_ok and seed_ok and pool_b < pb) \
    else "LG fails the locked rule: FINAL kept"
json.dump(v, open(EV / "OPT2_verdict.json", "w"), indent=1, default=bool)
pd.set_option("display.width", 250)
print(R[["model", "round", "recall", "f1", "precision", "ba", "brier", "accuracy", "roc_auc", "pr_auc", "TP/FP/FN/TN", "all_8_pass"]].to_string(index=False))
print(json.dumps(v, indent=1, default=bool))
print(D[D.survey == "ENNS2021"].sort_values("LG", ascending=False)[["province", "y_high", "PERS", "FINAL", "LG"]].round(3).head(14).to_string(index=False))
