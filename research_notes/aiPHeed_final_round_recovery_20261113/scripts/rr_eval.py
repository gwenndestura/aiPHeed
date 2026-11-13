r"""PROTOCOL_RR (written before this script ran): per-round evaluation of FINAL and candidates C1-C6 at Leads 1-3 against the 8 targets.
Stored predictions only (no refit). STACK weights are learned from earlier released rounds' out-of-sample forecasts only. Run: python -I rr_eval.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
K = ["key", "survey", "lead"]
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["province", "y_high", "PERS"]]
A = pd.read_csv(RN / "aiPHeed_final_etmix_20261113" / "evidence" / "ETMIX_rows_all_leads.csv")[K + ["FINAL", "ETMIX"]]
D = LAB.merge(A, on=K)
for name, f in (("ET", RN / "aiPHeed_final_stability_lead_20261113" / "evidence" / "E_FINALET_province_rows.csv"),
                ("SA", RN / "aiPHeed_final_standalone_20261113" / "evidence" / "E_FINALSA_province_rows.csv")):
    d = pd.read_csv(f); lc = [c for c in d.columns if c.isdigit()]
    d = d.melt(id_vars=["province", "survey"], value_vars=lc, var_name="lead", value_name=name).assign(lead=lambda x: x.lead.astype(int))
    D = D.merge(d, on=["province", "survey", "lead"], how="left")
C = pd.concat([pd.read_csv(f) for f in glob.glob(str(RN / "aiPHeed_final_lead3_cf_20261113" / "parts" / "CF__*.csv"))]).groupby(K, as_index=False)["p"].mean().rename(columns={"p": "CF"})
D = D.merge(C, on=K, how="left")
D = D[D.lead <= 3].copy()
ll = lambda y, p: float(-np.mean(y * np.log(np.clip(p, 1e-6, 1)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1))))
wlog = {}
for base in ("FINAL", "ET"):
    col = "STACK" if base == "FINAL" else "STACK_ET"
    D[col] = D[base]
    for L in (1, 2, 3):
        past = D[(D.lead == L) & D.survey.isin(["ENNS2018", "ENNS2019"])].dropna(subset=[base])
        grid = np.round(np.arange(0, 1.001, .01), 2)
        w = float(grid[int(np.argmin([ll(past.y_high.values, w_ * past[base].values + (1 - w_) * past.PERS.values) for w_ in grid]))])
        m = (D.lead == L) & (D.survey == "ENNS2021")
        D.loc[m, col] = w * D.loc[m, base] + (1 - w) * D.loc[m, "PERS"]
        wlog[f"{col}_L{L}"] = w
TGT = ["recall", "f1", "precision", "ba", "brier", "accuracy", "roc_auc", "pr_auc"]
def met(y, p):
    y = np.asarray(y, int); p = np.asarray(p, float); h = p >= .5
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    r = tp / max(1, tp + fn); pr = tp / (tp + fp) if tp + fp else 0.0; sp = tn / max(1, tn + fp)
    return {"recall": r, "f1": 2 * pr * r / (pr + r) if tp else 0.0, "precision": pr, "ba": (r + sp) / 2, "brier": float(np.mean((p - y) ** 2)),
            "accuracy": (tp + tn) / len(y), "roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p), "prev": y.mean(), "cm": f"{tp}/{fp}/{fn}/{tn}"}
ok = lambda m: all([m["recall"] >= .7, m["f1"] >= .7, m["precision"] >= .7, m["ba"] >= .7, m["brier"] <= .2, m["accuracy"] >= .75, m["roc_auc"] >= .7, m["pr_auc"] > m["prev"]])
rows, verdict = [], {}
MODELS = ["FINAL", "ET", "SA", "ETMIX", "CF", "STACK", "STACK_ET", "PERS"]
for L in (1, 2, 3):
    for mname in MODELS:
        g = D[D.lead == L].dropna(subset=[mname])
        per = {}
        for s, x in list(g.groupby("survey")) + [("POOLED", g)]:
            m = met(x.y_high, x[mname]); per[s] = m
            rows.append({"lead": L, "model": mname, "round": s, "n": len(x), **{k: round(v, 3) for k, v in m.items() if k not in ("cm",)}, "TP/FP/FN/TN": m["cm"], "all_8_pass": ok(m)})
        if L == 1 and mname != "PERS":
            f0 = {s: met(D[(D.lead == 1) & (D.survey == s)].y_high, D[(D.lead == 1) & (D.survey == s)].FINAL) for s in ("ENNS2018", "ENNS2019")}
            pb = met(g.y_high, g.PERS)["brier"]
            verdict[mname] = {"every_round_all_8": all(ok(per[s]) for s in ("ENNS2018", "ENNS2019", "ENNS2021")),
                              "2018_2019_not_worse_F1_BA": all(per[s]["f1"] >= f0[s]["f1"] - 1e-9 and per[s]["ba"] >= f0[s]["ba"] - 1e-9 for s in f0),
                              "pooled_brier_beats_persistence": per["POOLED"]["brier"] < pb,
                              "2021_recall": f'{round(per["ENNS2021"]["recall"] * 4)}/4', "2021_cm": per["ENNS2021"]["cm"]}
            verdict[mname]["ACCEPT"] = all(v for k, v in verdict[mname].items() if isinstance(v, bool))
R = pd.DataFrame(rows); R.to_csv(EV / "RR_per_round.csv", index=False, lineterminator="\n")
json.dump({"stack_weights": wlog, "verdict_L1": verdict}, open(EV / "RR_verdict.json", "w"), indent=1, default=bool)
pd.set_option("display.width", 250); pd.set_option("display.max_rows", 200)
print(json.dumps(wlog)); print(R[R.lead == 1].to_string(index=False)); print(json.dumps(verdict, indent=1, default=bool))
print(D[(D.lead == 1) & (D.survey == "ENNS2021") & ((D.y_high == 1) | (D.PERS >= .5))][["province", "y_high", "FINAL", "ET", "SA", "ETMIX", "CF", "STACK", "PERS"]].round(3).to_string(index=False))
