r"""(7-of-7 study copy: adds FINAL-MIX from parts_mix; inputs read from ../aiPHeed_final_stability_lead_20261113) FINAL_IMPROVEMENT_PROTOCOL section 3 (sha c5e76bd5): per-lead reliability of FINAL and FINAL-ET under the locked PROTOCOL_SA rules.
FINAL = parts_lead/FINALL__*; FINAL-ET = FINAL with the ENNS2021 Lead 1-6 rows taken from parts_et (variant ET).
Run: python -I lead_eval.py"""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import chi2
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parents[1]
ST = HERE.parent / "aiPHeed_final_stability_lead_20261113"
sys.path.insert(0, str(HERE.parent / "aiPHeed_final_standalone_20261113" / "scripts"))
from calib import _irls, ece, intercept, logit, slope   # noqa: E402

EV = HERE / "evidence"
K = ["key", "survey", "lead"]
SEEDS = (168, 1, 2, 3, 4)
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
lab = LAB[K + ["province", "region", "y_high", "q_true", "PERS"]]
rng = np.random.default_rng(7)

F = pd.concat([pd.read_csv(f) for f in glob.glob(str(ST / "parts_lead" / "FINALL__*.csv"))])
meta = {(d["survey"], d["lead"], d["seed"]): d for d in (json.load(open(f)) for f in glob.glob(str(ST / "features_lead" / "FINALL__*.json")))}
F["p_clim"] = [meta[(s, l, sd)]["train_high_share"] for s, l, sd in zip(F.survey, F.lead, F.seed)]
ARMS = {"FINAL": F}
et_files = glob.glob(str(ST / "parts_et" / "ET__*.csv"))
if et_files:
    E = pd.concat([pd.read_csv(f) for f in et_files])
    E = E[E.variant == "ET"][["key", "survey", "lead", "seed", "p", "mu"]]
    G = F.merge(E, on=["key", "survey", "lead", "seed"], how="left", suffixes=("", "_et"))
    G["p"], G["mu"] = G.p_et.fillna(G.p), G.mu_et.fillna(G.mu)
    ARMS["FINAL-ET"] = G.drop(columns=["p_et", "mu_et"])
X = pd.concat([pd.read_csv(f) for f in glob.glob(str(HERE / "parts_mix" / "FINALMIX__*.csv"))])[["key", "survey", "lead", "seed", "p"]]
ARMS["FINAL-MIX"] = F.drop(columns=["p"]).merge(X, on=["key", "survey", "lead", "seed"])


def core(g):
    p, y = g.p.values, g.y_high.values.astype(int)
    h = p >= 0.5
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    rec, spec, prec = tp / max(1, tp + fn), tn / max(1, tn + fp), tp / max(1, tp + fp)
    o = dict(n=len(g), high=int(y.sum()), low=int((1 - y).sum()), accuracy=(tp + tn) / len(g), balanced_accuracy=0.5 * (rec + spec), recall_high=rec,
             recall_low=spec, precision=prec, f1=2 * prec * rec / max(1e-9, prec + rec), TP=tp, FP=fp, FN=fn, TN=tn,
             auroc=roc_auc_score(y, p) if 0 < y.sum() < len(y) else np.nan, brier=float(np.mean((p - y) ** 2)),
             brier_clim=float(np.mean((g.p_clim.values - y) ** 2)))
    o["bss"] = 1 - o["brier"] / o["brier_clim"]
    o["ece10"], o["mean_p_minus_rate"], o["cal_slope"], o["cal_intercept_logit"] = ece(p, y), float(p.mean() - y.mean()), slope(p, y), intercept(p, y)
    lp = logit(p)
    b = _irls(np.column_stack([np.ones(len(y)), lp]), y.astype(float))
    m1 = np.clip(1 / (1 + np.exp(-np.clip(b[0] + b[1] * lp, -30, 30))), 1e-9, 1 - 1e-9)
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    lr = 2 * (np.sum(y * np.log(m1) + (1 - y) * np.log(1 - m1)) - np.sum(y * np.log(pc) + (1 - y) * np.log(1 - pc)))
    o["cox_p"] = float(chi2.sf(max(lr, 0.0), 2))
    return o


def ci(g, keys=("balanced_accuracy", "auroc", "accuracy", "precision", "recall_high", "f1", "brier")):
    cl = (g.key + g.survey).values
    u = np.unique(cl)
    idx = {c: np.flatnonzero(cl == c) for c in u}
    B = []
    for _ in range(3000):
        x = g.iloc[np.concatenate([idx[c] for c in rng.choice(u, len(u))])]
        if 0 < x.y_high.sum() < len(x):
            r = core(x)
            B.append([r[k] for k in keys])
    B = np.array(B, float)
    return {k: [round(float(np.nanpercentile(B[:, j], 2.5)), 3), round(float(np.nanpercentile(B[:, j], 97.5)), 3)] for j, k in enumerate(keys)}


def ece_null(p, n=3000):
    return float(np.percentile([ece(p, rng.binomial(1, p)) for _ in range(n)], 95))


def baseline(g, col):
    x = g.assign(p=col)
    r = core(x)
    return {k: round(r[k], 3) for k in ("balanced_accuracy", "recall_high", "precision", "auroc", "brier")}


OUT, PROV = {}, []
for arm, S in ARMS.items():
    S = S[S.seed.isin(SEEDS)]
    M = S.groupby(K, as_index=False)[["p", "p_clim"]].mean().merge(lab, on=K)
    res = {}
    for L, g in M.groupby("lead"):
        r = core(g)
        rounds = {sv: {k: (round(v, 3) if isinstance(v, float) else v) for k, v in core(x).items() if k in ("n", "high", "balanced_accuracy", "recall_high", "precision", "auroc", "FP", "FN")}
                  for sv, x in g.groupby("survey")}
        seeds = [round(core(x.merge(lab, on=K))["balanced_accuracy"], 3) for _, x in S[S.lead == L].groupby("seed")]
        r_null = ece_null(g.p.values)
        evaluable = g.survey.nunique() >= 2 and r["high"] >= 10 and r["low"] >= 10
        crit = {"data": evaluable, "R3": r["balanced_accuracy"] >= .70 and r["auroc"] >= .70, "R4": r["recall_high"] >= .80, "R5": r["precision"] >= .60,
                "R6": r["ece10"] <= r_null and abs(r["mean_p_minus_rate"]) <= .10 and r["cox_p"] >= .05 and r["bss"] > 0,
                "R7b": min(seeds) >= .70,
                "R7c": all(v["balanced_accuracy"] >= .60 and v["recall_high"] >= .50 for v in rounds.values() if v["high"] >= 4 and v["n"] - v["high"] >= 4)}
        res[int(L)] = {**{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, "ece10_null_p95": round(r_null, 3), "ci95": ci(g),
                       "rounds_included": sorted(g.survey.unique()), "provinces": int(g.key.nunique()), "by_round": rounds, "seed_BA": seeds,
                       "baselines": {"persistence_latest_survey": baseline(g, g.PERS.values), "climatology_training_rate": baseline(g, g.p_clim.values),
                                     "always_low": baseline(g, np.zeros(len(g)))},
                       "criteria": crit, "reliable": all(crit.values()) if evaluable else None}
        PROV.append(g.assign(arm=arm)[["arm", "province", "survey", "lead", "y_high", "p"]])
    mrl = 0
    for L in sorted(res):
        if res[L]["reliable"]:
            mrl = L
        else:
            break
    OUT[arm] = {"by_lead": res, "max_reliable_lead": mrl if mrl else "none established",
                "first_failure": next(({"lead": L, "failed": [k for k, v in res[L]["criteria"].items() if not v]} for L in sorted(res) if not res[L]["reliable"]), None)}
json.dump(OUT, open(EV / "LEAD_results.json", "w"), indent=1, default=float)
P = pd.concat(PROV).pivot_table(index=["arm", "province", "survey", "y_high"], columns="lead", values="p").round(3).reset_index()
P.to_csv(EV / "LEAD_province_by_lead.csv", index=False)
rows = []
for arm, o in OUT.items():
    for L, r in o["by_lead"].items():
        rows.append({"arm": arm, "lead": L, "n": r["n"], "rounds": "+".join(s[-4:] for s in r["rounds_included"]), "HIGH": r["high"], "LOW": r["low"],
                     "BA": r["balanced_accuracy"], "AUROC": r["auroc"], "acc": r["accuracy"], "prec": r["precision"], "recall": r["recall_high"], "F1": r["f1"],
                     "brier": r["brier"], "TP/FP/FN/TN": f'{r["TP"]}/{r["FP"]}/{r["FN"]}/{r["TN"]}', "ece": r["ece10"], "ece_null95": r["ece10_null_p95"],
                     "mean_p-rate": r["mean_p_minus_rate"], "cox_p": r["cox_p"], "worst_seed_BA": min(r["seed_BA"]),
                     "round_recall": {s[-4:]: v["recall_high"] for s, v in r["by_round"].items()}, "failed": [k for k, v in r["criteria"].items() if not v],
                     "reliable": r["reliable"]})
T = pd.DataFrame(rows)
T.to_csv(EV / "LEAD_summary_table.csv", index=False)
pd.set_option("display.width", 250)
print(T.drop(columns=["acc", "F1"]).to_string(index=False))
print({a: (o["max_reliable_lead"], o["first_failure"]) for a, o in OUT.items()})
