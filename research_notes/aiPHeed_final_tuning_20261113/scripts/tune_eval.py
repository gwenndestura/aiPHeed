r"""PROTOCOL_TUNE scoring. Training-only choices applied first (A2/A5 class weighting by lowest inner OOF Brier; A3/A5 threshold = engine's inner
`thr`); then every arm is scored on the HISTORICAL TEST rounds 2018/2019/2021 + pooled; seeds; drops; SELECT; bootstrap; decision rule.
Run: python -I tune_eval.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; P_ = HERE / "parts"; EV = HERE / "evidence"
K = ["key", "survey", "lead"]; RNDS = ["ENNS2018", "ENNS2019", "ENNS2021"]
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["province", "y_high", "PERS"]]; LAB = LAB[LAB.lead == 1]
ALL = pd.concat([pd.read_csv(f) for f in glob.glob(str(P_ / "*.csv"))]); ALL["drop"] = ALL["drop"].fillna("")
main, drops = ALL[ALL["drop"] == ""], ALL[ALL["drop"] != ""]


def pick_cw(d):
    """per fold x seed: the class weighting with the lowest inner OOF Brier (training only)"""
    b = d.groupby(["survey", "seed", "cw"]).inner_brier.first().reset_index()
    best = b.loc[b.groupby(["survey", "seed"]).inner_brier.idxmin(), ["survey", "seed", "cw"]]
    return d.merge(best, on=["survey", "seed", "cw"]), best


A2sel, A2choice = pick_cw(main[main.arm == "A2"])
A5sel, A5choice = pick_cw(main[main.arm == "A5"])
LGr = main[(main.arm == "A2") & (main.cw == "balanced")]          # = FINAL-LG refit (checked against stored FINAL-LG below)
ARMS = {"FINAL_LG(refit)": (LGr, "0.5"), "A1_LG_WIDE": (main[main.arm == "A1"], "0.5"), "A2_LG_CW": (A2sel, "0.5"),
        "A3_LG_THR": (LGr, "thr"), "A4_LG_SANC": (main[main.arm == "A4"], "0.5"), "A5_LG_OPT": (A5sel, "thr"), "A5_LG_OPT@0.5": (A5sel, "0.5")}
FI = pd.concat([pd.read_csv(f, usecols=K + ["seed", "p"]) for f in glob.glob(str(RN / "aiPHeed_hcw_final_optimization_20261112" / "parts_fwd" / "FINAL__ENNS20*__1__*.csv"))])
LGs = pd.concat([pd.read_csv(f, usecols=K + ["seed", "p"]) for f in glob.glob(str(RN / "aiPHeed_final_model_optimization_20261113" / "parts" / "LG__*.csv"))])
repro = float(LGr[K + ["seed", "p"]].merge(LGs, on=K + ["seed"], suffixes=("", "_s")).eval("abs(p - p_s)").max())


def met(y, p, thr):
    y = np.asarray(y, int); p = np.asarray(p, float); h = p >= np.asarray(thr, float)
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    r = tp / max(1, tp + fn); pr = tp / (tp + fp) if tp + fp else 0.0; sp = tn / max(1, tn + fp); npv = tn / (tn + fn) if tn + fn else 0.0
    return {"recall": r, "precision": pr, "f1": 2 * pr * r / (pr + r) if tp else 0.0, "low_recall": sp, "low_precision": npv, "ba": (r + sp) / 2,
            "accuracy": (tp + tn) / len(y), "brier": float(np.mean((p - y) ** 2)), "roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
            "prev": float(y.mean()), "false_pos": fp, "missed_high": fn, "cm": f"{tp}/{fp}/{fn}/{tn}"}


ok = lambda m: all([m["recall"] >= .7, m["f1"] >= .7, m["precision"] >= .7, m["ba"] >= .7, m["brier"] <= .2, m["accuracy"] >= .75, m["roc_auc"] >= .7, m["pr_auc"] > m["prev"]])


def agg(d, mode):
    g = d.groupby(K, as_index=False).agg(p=("p", "mean"), thr=("thr", "mean"))
    if mode == "0.5":
        g["thr"] = 0.5
    return g


def score(name, d, mode, tag="mean"):
    x = LAB.merge(d, on=K); out = []
    for s, z in list(x.groupby("survey")) + ([("POOLED", x)] if x.survey.nunique() == 3 else []):
        m = met(z.y_high, z.p, z.thr)
        out.append({"model": name, "seed": tag, "round": s, "threshold": "training-chosen" if mode == "thr" else "0.50", "mean_thr": round(float(z.thr.mean()), 3),
                    **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items() if k != "cm"}, "TP/FP/FN/TN": m["cm"], "all_8_pass": ok(m)})
    return out


rows = []
rows += score("FINAL", FI.groupby(K, as_index=False).p.mean().assign(thr=.5), "0.5")
rows += score("FINAL_LG", LGs.groupby(K, as_index=False).p.mean().assign(thr=.5), "0.5")
rows += score("PERSISTENCE", LAB[K + ["PERS"]].rename(columns={"PERS": "p"}).assign(thr=.5), "0.5")
H = pd.read_csv(RN / "aiPHeed_final_detection_20261113" / "evidence" / "ATTR_per_round_L1.csv")
for nm, (d, mode) in ARMS.items():
    rows += score(nm, agg(d, mode), mode)
    for sd, g in d.groupby("seed"):
        rows += score(nm, agg(g, mode), mode, tag=str(sd))
for nm, d, mode in (("A5_LG_OPT", drops[drops.arm == "A5"], "thr"), ("FINAL_LG(refit)", drops[drops.arm == "A2"], "0.5")):
    if len(d):
        dd = pick_cw(d.assign(seed=d["drop"]))[0] if nm.startswith("A5") else d.assign(seed=d["drop"])
        for dr, g in dd.groupby("seed"):
            rows += score(nm, agg(g, mode), mode, tag=f"drop_{dr}")
R = pd.DataFrame(rows); R.to_csv(EV / "TUNE_per_round_L1.csv", index=False, lineterminator="\n")
# rolling-origin SELECT for the 2021 fold: lowest log loss on 2018+2019 out-of-sample forecasts (rounds released before the 2021 origin)
ll = lambda y, p: float(-np.mean(y * np.log(np.clip(p, 1e-6, 1 - 1e-6)) + (1 - y) * np.log(np.clip(1 - p, 1e-6, 1 - 1e-6))))
cand = {"FINAL_LG": LGs.groupby(K, as_index=False).p.mean(), **{nm: agg(d, "0.5")[K + ["p"]] for nm, (d, _) in ARMS.items() if not nm.endswith("@0.5") and nm != "A3_LG_THR"}}
sel_ll = {nm: ll(*(lambda x: (x.y_high.values, x.p.values))(LAB[LAB.survey.isin(RNDS[:2])].merge(d, on=K))) for nm, d in cand.items()}
chosen = min(sel_ll, key=sel_ll.get)
# bootstrap vs FINAL-LG (pooled Brier)
rng = np.random.default_rng(20261113); boot = {}
base = LAB.merge(LGs.groupby(K, as_index=False).p.mean().rename(columns={"p": "lg"}), on=K)
for nm, (d, mode) in ARMS.items():
    if nm.endswith("@0.5"):
        continue
    b = base.merge(agg(d, "0.5")[K + ["p"]], on=K); v = ((b.p - b.y_high) ** 2 - (b.lg - b.y_high) ** 2).values
    idx = [np.where(b.survey.values == s)[0] for s in RNDS]
    bs = [v[np.concatenate([rng.choice(i, len(i)) for i in idx])].mean() for _ in range(2000)]
    boot[nm] = {"dBrier_vs_FINAL_LG": round(float(v.mean()), 4), "ci95": [round(float(np.quantile(bs, .025)), 4), round(float(np.quantile(bs, .975)), 4)]}
g = lambda m, r, sd="mean": R[(R.model == m) & (R["round"] == r) & (R.seed == sd)].iloc[0]
lg0 = {r: g("FINAL_LG", r) for r in RNDS + ["POOLED"]}
dec = {}
for nm in ARMS:
    if nm == "FINAL_LG(refit)":
        continue
    seeds = sorted(R[(R.model == nm) & R.seed.str.fullmatch(r"\d+")].seed.unique())
    c1 = all(bool(g(nm, r).all_8_pass) for r in ("ENNS2018", "ENNS2019", "POOLED")) and all(bool(g(nm, r, s).all_8_pass) for s in seeds for r in ("ENNS2018", "ENNS2019", "POOLED"))
    c2 = float(g(nm, "POOLED").brier) <= float(lg0["POOLED"].brier) + .005
    r21 = g(nm, "ENNS2021"); tp, fp = map(int, r21["TP/FP/FN/TN"].split("/")[:2]); tp0 = int(lg0["ENNS2021"]["TP/FP/FN/TN"].split("/")[0])
    c3 = tp > tp0 and fp <= 2 and float(r21.f1) > float(lg0["ENNS2021"].f1)
    c4 = chosen == nm.replace("@0.5", "")
    dec[nm] = {"1_2018_2019_pooled_all8_mean_and_seeds": c1, "2_pooled_brier_le_LG+0.005": c2, "3_2021_more_HIGH_le2FP_F1_up": c3, "4_SELECT_picks_it": c4,
               "BETTER_THAN_FINAL_LG": bool(c1 and c2 and c3 and c4), "2021": r21["TP/FP/FN/TN"]}
cfgs = {nm: d.groupby(["survey"]).cfg.agg(lambda s: s.value_counts().index[0]).to_dict() for nm, (d, _) in ARMS.items()}
out = {"FINAL_LG_refit_repro_max_abs_p": repro, "cw_choice_A2": {f"{a}/{b}": int(v) for (a, b), v in A2choice.groupby("survey").cw.value_counts().items()},
       "cw_choice_A5": {f"{a}/{b}": int(v) for (a, b), v in A5choice.groupby("survey").cw.value_counts().items()}, "SELECT_logloss_2018_2019": sel_ll, "SELECT_chosen_for_2021": chosen,
       "bootstrap": boot, "decision": dec, "modal_configs": cfgs}
json.dump(out, open(EV / "TUNE_verdict.json", "w"), indent=1, default=str)
pd.set_option("display.width", 280); pd.set_option("display.max_rows", 400)
c = ["model", "seed", "round", "threshold", "mean_thr", "recall", "precision", "f1", "low_recall", "low_precision", "ba", "accuracy", "brier", "roc_auc", "pr_auc", "false_pos", "missed_high", "TP/FP/FN/TN", "all_8_pass"]
print(R[R.seed == "mean"][c].to_string(index=False)); print(R[R.seed != "mean"][c].to_string(index=False)); print(json.dumps({k: v for k, v in out.items() if k != "modal_configs"}, indent=1, default=str))
