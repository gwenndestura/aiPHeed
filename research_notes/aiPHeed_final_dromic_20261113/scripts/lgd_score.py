r"""Score LG-D (PROTOCOL_DRM addendum 1) against FINAL and FINAL-LG; identity check in 2018/2019; seeds; drops. Run: python -I lgd_score.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"; K = ["key", "survey", "lead"]; RNDS = ["ENNS2018", "ENNS2019", "ENNS2021"]
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["province", "y_high"]]; LAB = LAB[LAB.lead == 1]
D = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "parts" / "LGD__*.csv"))]); D["drop"] = D["drop"].fillna("")
LG = pd.concat([pd.read_csv(f, usecols=K + ["seed", "p"]) for f in glob.glob(str(RN / "aiPHeed_final_model_optimization_20261113" / "parts" / "LG__*.csv"))])
FI = pd.concat([pd.read_csv(f, usecols=K + ["seed", "p"]) for f in glob.glob(str(RN / "aiPHeed_hcw_final_optimization_20261112" / "parts_fwd" / "FINAL__ENNS20*__1__*.csv"))])
ident = {s: float(D[(D.survey == s) & (D["drop"] == "")].merge(LG[LG.survey == s], on=K + ["seed"], suffixes=("", "_lg")).eval("abs(p - p_lg)").max()) for s in RNDS[:2]}
def met(y, p):
    y = np.asarray(y, int); p = np.asarray(p, float); h = p >= .5
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    r = tp / max(1, tp + fn); pr = tp / (tp + fp) if tp + fp else 0.0; sp = tn / max(1, tn + fp)
    return {"recall": r, "precision": pr, "f1": 2 * pr * r / (pr + r) if tp else 0.0, "ba": (r + sp) / 2, "brier": float(np.mean((p - y) ** 2)), "accuracy": (tp + tn) / len(y),
            "roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p), "prev": float(y.mean()), "cm": f"{tp}/{fp}/{fn}/{tn}"}
ok = lambda m: all([m["recall"] >= .7, m["f1"] >= .7, m["precision"] >= .7, m["ba"] >= .7, m["brier"] <= .2, m["accuracy"] >= .75, m["roc_auc"] >= .7, m["pr_auc"] > m["prev"]])
# LG-D seed-mean: 2018/2019 = FINAL-LG (identical by construction, verified above), 2021 = LG-D fits
lgd = pd.concat([LG[LG.survey != "ENNS2021"], D[(D.survey == "ENNS2021") & (D["drop"] == "")][K + ["seed", "p"]]])
rows = []
for nm, d in (("FINAL", FI), ("FINAL_LG", LG), ("LG_D", lgd)):
    x = LAB.merge(d.groupby(K, as_index=False).p.mean(), on=K)
    for s, z in list(x.groupby("survey")) + [("POOLED", x)]:
        m = met(z.y_high, z.p); rows.append({"model": nm, "seed": "mean", "round": s, **{k: round(v, 4) for k, v in m.items() if k != "cm"}, "TP/FP/FN/TN": m["cm"], "all_8_pass": ok(m)})
    for sd, g in d.groupby("seed"):
        x = LAB.merge(g[K + ["p"]], on=K); m = met(x[x.survey == "ENNS2021"].y_high, x[x.survey == "ENNS2021"].p)
        rows.append({"model": nm, "seed": str(sd), "round": "ENNS2021", **{k: round(v, 4) for k, v in m.items() if k != "cm"}, "TP/FP/FN/TN": m["cm"], "all_8_pass": ok(m)})
for dr, g in D[D["drop"] != ""].groupby("drop"):
    x = LAB.merge(g[K + ["p"]], on=K); m = met(x.y_high, x.p)
    rows.append({"model": "LG_D", "seed": f"drop_{dr}", "round": "ENNS2021", **{k: round(v, 4) for k, v in m.items() if k != "cm"}, "TP/FP/FN/TN": m["cm"], "all_8_pass": ok(m)})
R = pd.DataFrame(rows); R.to_csv(EV / "LGD_per_round_L1.csv", index=False, lineterminator="\n")
w = D[(D.survey == "ENNS2021") & (D["drop"] == "")]
x21 = LAB[LAB.survey == "ENNS2021"].merge(w.groupby(K, as_index=False).agg(p_LGD=("p", "mean"), drm_disp=("drm_disp", "first")), on=K).merge(
    LG[LG.survey == "ENNS2021"].groupby(K, as_index=False).p.mean().rename(columns={"p": "p_LG"}), on=K).sort_values("p_LGD", ascending=False)
x21.to_csv(EV / "LGD_2021_rows.csv", index=False, lineterminator="\n")
json.dump({"identity_vs_FINAL_LG_2018_2019_max_abs_p": ident, "drm_selected_share_2021_fits": float(w.drm_selected.mean()),
           "train_d3_nonmissing": int(w.train_d3_nonmissing.iloc[0])}, open(EV / "LGD_verdict.json", "w"), indent=1)
pd.set_option("display.width", 250)
print(json.dumps({"identity": ident, "drm_selected_share": float(w.drm_selected.mean())}))
print(R[["model", "seed", "round", "recall", "precision", "f1", "ba", "accuracy", "brier", "roc_auc", "pr_auc", "TP/FP/FN/TN", "all_8_pass"]].to_string(index=False))
print(x21[["province", "y_high", "p_LG", "p_LGD", "drm_disp"]].round(3).head(12).to_string(index=False))
