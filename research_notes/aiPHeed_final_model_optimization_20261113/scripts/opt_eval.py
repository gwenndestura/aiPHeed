r"""PROTOCOL_OPT (sha bb05c253, written before any new arm was fitted or scored): per-round Lead-1 evaluation of every arm.
Stored predictions only (no refit here). Cut-off 0.50. SELECT = rolling-origin choice for the 2021 fold by log loss on the 2018+2019 Lead-1
out-of-sample forecasts, from the arms PROTOCOL_OPT names; 2018/2019 folds use FINAL. Supplementary stored arms are tabulated, never selected.
Synthetic-data arms are excluded (owner prohibition). Run: python -I opt_eval.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
K = ["key", "survey", "lead"]; RNDS = ["ENNS2018", "ENNS2019", "ENNS2021"]
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["province", "y_high", "PERS"]]
LAB = LAB[LAB.lead == 1]


def load_parts(folder, arms, tag=""):
    out = {}
    for a in arms:
        fs = glob.glob(str(folder / f"{a}__ENNS20*__1__*.csv"))
        if not fs:
            continue
        d = pd.concat([pd.read_csv(f, usecols=["key", "survey", "lead", "seed", "p"]) for f in fs])
        out[tag + a] = d
    return out


SEEDROWS = {}
SEEDROWS.update(load_parts(RN / "aiPHeed_hcw_final_optimization_20261112" / "parts_fwd",
                           ["FINAL", "BASE", "RATE", "RATE_SQRT", "IMPUTE", "MIND", "RIMP", "DROPGAP", "COMP"]))
SEEDROWS.update(load_parts(HERE / "parts", ["DELTA", "TRAJ", "DELTA_TRAJ"]))
SUPP = {}
SUPP.update(load_parts(RN / "aiPHeed_final_strengthening_20261112" / "parts_fwd", ["CAP", "CAPVAR", "VAR"]))
SUPP.update(load_parts(RN / "aiPHeed_final_conv_20261112" / "parts_fwd", ["CONV"]))
SUPP.update(load_parts(RN / "aiPHeed_hcw_round2_20261112" / "parts_fwd", ["A025_IMP", "A025_MIND", "A050_IMP", "A050_MIND", "A075_IMP", "A075_MIND", "A100_IMP"]))

D = LAB.copy()
A = pd.read_csv(RN / "aiPHeed_final_etmix_20261113" / "evidence" / "ETMIX_rows_all_leads.csv")[K + ["FINAL", "ETMIX"]]
D = D.merge(A.rename(columns={"FINAL": "FINAL_ref"}), on=K, how="left")
for name, f in (("FINAL_ET", RN / "aiPHeed_final_stability_lead_20261113" / "evidence" / "E_FINALET_province_rows.csv"),
                ("FINAL_SA", RN / "aiPHeed_final_standalone_20261113" / "evidence" / "E_FINALSA_province_rows.csv")):
    d = pd.read_csv(f)[["province", "survey", "1"]].rename(columns={"1": name}).assign(lead=1)
    D = D.merge(d, on=["province", "survey", "lead"], how="left")
C = pd.concat([pd.read_csv(f) for f in glob.glob(str(RN / "aiPHeed_final_lead3_cf_20261113" / "parts" / "CF__*__1__*.csv"))])
D = D.merge(C.groupby(K, as_index=False)["p"].mean().rename(columns={"p": "FINAL_CF"}), on=K, how="left")
D = D.rename(columns={"ETMIX": "FINAL_ETMIX"})
for a, d in {**SEEDROWS, **SUPP}.items():
    D = D.merge(d.groupby(K, as_index=False)["p"].mean().rename(columns={"p": a}), on=K, how="left")
repro = float((D.FINAL - D.FINAL_ref).abs().max())

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
POOL = ["FINAL", "BASE", "RATE", "RATE_SQRT", "IMPUTE", "MIND", "RIMP", "DROPGAP", "COMP", "FINAL_ET", "FINAL_SA", "FINAL_ETMIX", "FINAL_CF",
        "DELTA", "TRAJ", "DELTA_TRAJ"]
POOL = [a for a in POOL if a in D.columns and D[a].notna().all()]
past = D[D.survey.isin(["ENNS2018", "ENNS2019"])]
sel_ll = {a: ll(past.y_high.values, past[a].values) for a in POOL}
chosen = min(sel_ll, key=sel_ll.get)
D["SELECT"] = np.where(D.survey == "ENNS2021", D[chosen], D["FINAL"])
MODELS = ["SELECT"] + POOL + [a for a in SUPP if a in D.columns] + ["PERS"]

rows, verdict = [], {}
f0 = {s: met(D[D.survey == s].y_high, D[D.survey == s].FINAL) for s in RNDS}
pb = met(D.y_high, D.PERS)["brier"]
for mname in MODELS:
    g = D.dropna(subset=[mname]); per = {}
    for s, x in list(g.groupby("survey")) + [("POOLED", g)]:
        m = met(x.y_high, x[mname]); per[s] = m
        rows.append({"model": mname, "group": "supplementary" if mname in SUPP else ("baseline" if mname == "PERS" else "protocol"),
                     "round": s, "n": len(x), **{k: round(v, 4) for k, v in m.items() if k != "cm"}, "TP/FP/FN/TN": m["cm"], "all_8_pass": ok(m)})
    if mname == "PERS" or len(per) < 4:
        continue
    seeds_acc = None
    src = SEEDROWS.get(mname, SUPP.get(mname))
    if src is not None:
        s_ = src.merge(LAB[K + ["y_high"]], on=K)
        seeds_acc = {int(sd): round(float(((x.p >= .5).astype(int) == x.y_high).mean()), 4) for sd, x in s_.groupby("seed")}
        seeds_all8 = {int(sd): {r: ok(met(xx.y_high, xx.p)) for r, xx in x.groupby("survey")} for sd, x in s_.groupby("seed")}
    else:
        seeds_all8 = None
    verdict[mname] = {"every_round_all_8": all(ok(per[s]) for s in RNDS), "rounds_passing": [s for s in RNDS if ok(per[s])],
                      "2018_2019_not_worse_F1_BA": all(per[s]["f1"] >= f0[s]["f1"] - 1e-9 and per[s]["ba"] >= f0[s]["ba"] - 1e-9 for s in RNDS[:2]),
                      "pooled_brier_beats_persistence": per["POOLED"]["brier"] < pb,
                      "every_seed_pooled_acc_ge_75": None if seeds_acc is None else all(v >= .75 for v in seeds_acc.values()),
                      "seed_pooled_accuracy": seeds_acc, "seed_rounds_all8": seeds_all8,
                      "2021_cm": per["ENNS2021"]["cm"], "pooled_brier": round(per["POOLED"]["brier"], 4)}
    v = verdict[mname]
    v["ACCEPT"] = bool(v["every_round_all_8"] and v["2018_2019_not_worse_F1_BA"] and v["pooled_brier_beats_persistence"]
                       and v["every_seed_pooled_acc_ge_75"] is not False)
R = pd.DataFrame(rows); R.to_csv(EV / "OPT_per_round_L1.csv", index=False, lineterminator="\n")
D.to_csv(EV / "OPT_province_rows_L1.csv", index=False, lineterminator="\n")
json.dump({"final_repro_max_abs_diff": repro, "select_pool": POOL, "select_logloss_2018_2019": sel_ll, "select_chosen_for_2021": chosen,
           "verdict": verdict}, open(EV / "OPT_verdict.json", "w"), indent=1, default=bool)
pd.set_option("display.width", 260); pd.set_option("display.max_rows", 400)
print("FINAL repro max |diff|:", repro); print("SELECT chosen:", chosen, json.dumps({k: round(v, 4) for k, v in sel_ll.items()}))
print(R[["model", "round", "recall", "f1", "precision", "ba", "brier", "accuracy", "roc_auc", "pr_auc", "TP/FP/FN/TN", "all_8_pass"]].to_string(index=False))
print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("seed_rounds_all8",)} for k, v in verdict.items()}, indent=0, default=bool))
