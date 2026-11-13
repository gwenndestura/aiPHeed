r"""Deliverables 2-5: FINAL rolling-origin results by round, metrics vs baselines, HIGH detection, Leads 1-5, seeds, bootstrap,
threshold sensitivity, province breakdown, gates G1-G9 and G10c of PROTOCOL_REL (sha 1efdf5a4). Uses the EXISTING 5-seed FINAL fits
(../aiPHeed_final_7of7_20261113/parts_mix, column p_final; 110 fits) -- no refit, no tuning. Retrospective.
Run: python -I rel_eval.py"""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import chi2
from sklearn.metrics import roc_auc_score, average_precision_score

HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent
sys.path.insert(0, str(RN / "aiPHeed_final_standalone_20261113" / "scripts"))
from calib import _irls, ece, intercept, logit, slope   # noqa: E402
EV = HERE / "evidence"
K = ["key", "survey", "lead"]
LEADS = (1, 2, 3, 4, 5)
rng = np.random.default_rng(20261113)
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
X = pd.concat([pd.read_csv(f) for f in glob.glob(str(RN / "aiPHeed_final_7of7_20261113" / "parts_mix" / "FINALMIX__*.csv"))])
meta = {(d["survey"], d["lead"], d["seed"]): d["train_high_share"]
        for d in (json.load(open(f)) for f in glob.glob(str(RN / "aiPHeed_final_stability_lead_20261113" / "features_lead" / "FINALL__*.json")))}
X["p_clim"] = [meta[(s, l, sd)] for s, l, sd in zip(X.survey, X.lead, X.seed)]
S = X.merge(LAB[K + ["y_high"]], on=K)                                       # per-seed rows
M = X.groupby(K, as_index=False).agg(FINAL=("p_final", "mean"), CLIM=("p_clim", "mean"), gap_q=("gap_q", "first"))
M = M.merge(LAB[K + ["province", "region", "y_high", "y_true", "PERS", "PSA", "LR", "LR_NEWS"]], on=K)
M["ALWAYS_LOW"] = 0.0
M = M[M.lead.isin(LEADS)].reset_index(drop=True)
M.to_csv(EV / "REL_rows_L1to5.csv", index=False, lineterminator="\n")
BASES = {"ALWAYS_LOW": "always-LOW (p = 0)", "CLIM": "climatology (training HIGH share)", "PERS": "persistence (latest provincial survey)",
         "PSA": "PSA-indicator logistic", "LR": "logistic regression (all inputs + anchor)", "LR_NEWS": "NLP-only logistic"}


def core(y, p):
    y = np.asarray(y, int); p = np.asarray(p, float); h = p >= .5
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    rec, spec = tp / max(1, tp + fn), tn / max(1, tn + fp)
    prec = tp / (tp + fp) if tp + fp else np.nan
    npv = tn / (tn + fn) if tn + fn else np.nan
    f1h = 2 * prec * rec / (prec + rec) if tp else 0.0
    f1l = 2 * npv * spec / (npv + spec) if tn else 0.0
    both = 0 < y.sum() < len(y)
    return dict(n=len(y), high=int(y.sum()), accuracy=(tp + tn) / len(y), precision_high=prec, recall_high=rec, f1_high=f1h,
                recall_low=spec, macro_f1=(f1h + f1l) / 2, balanced_accuracy=(rec + spec) / 2,
                roc_auc=roc_auc_score(y, p) if both and np.ptp(p) > 0 else np.nan,
                pr_auc=average_precision_score(y, p) if both and np.ptp(p) > 0 else (y.mean() if both else np.nan),
                brier=float(np.mean((p - y) ** 2)), TP=tp, FP=fp, FN=fn, TN=tn)


def calib(y, p):
    y = np.asarray(y, int); p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6); lp = logit(p)
    b = _irls(np.column_stack([np.ones(len(y)), lp]), y.astype(float))
    m1 = np.clip(1 / (1 + np.exp(-np.clip(b[0] + b[1] * lp, -30, 30))), 1e-9, 1 - 1e-9)
    lr = 2 * (np.sum(y * np.log(m1) + (1 - y) * np.log(1 - m1)) - np.sum(y * np.log(p) + (1 - y) * np.log(1 - p)))
    return dict(ece10=ece(p, y), mean_p_minus_rate=float(p.mean() - y.mean()), cal_slope=slope(p, y), cal_intercept=intercept(p, y),
                cox_p=float(chi2.sf(max(lr, 0.0), 2)))


KEYS = ("accuracy", "precision_high", "recall_high", "f1_high", "macro_f1", "balanced_accuracy", "roc_auc", "pr_auc", "brier")


def boot(g, col, B=3000, cluster=False):
    out = []
    prov = g.key.unique()
    idx = {k: np.where(g.key.values == k)[0] for k in prov}
    for _ in range(B):
        i = np.concatenate([idx[k] for k in rng.choice(prov, len(prov))]) if cluster else rng.integers(0, len(g), len(g))
        yy = g.y_high.values[i]
        if 0 < yy.sum() < len(yy):
            r = core(yy, g[col].values[i]); out.append([r[k] for k in KEYS])
    A = np.array(out, float)
    return {k: [round(float(np.nanpercentile(A[:, j], 2.5)), 3), round(float(np.nanpercentile(A[:, j], 97.5)), 3)] for j, k in enumerate(KEYS)}


def paired(g, a, b, B=4000):
    """Bootstrap 95 % CIs of Brier(a)-Brier(b), acc(a)-acc(b), PR-AUC(a)-PR-AUC(b) on identical rows."""
    y = g.y_high.values; pa, pb = g[a].values, g[b].values
    db, dacc, dpr = [], [], []
    for _ in range(B):
        i = rng.integers(0, len(g), len(g)); yy = y[i]
        db.append(np.mean((pa[i] - yy) ** 2) - np.mean((pb[i] - yy) ** 2))
        dacc.append(np.mean((pa[i] >= .5) == yy) - np.mean((pb[i] >= .5) == yy))
        if 0 < yy.sum() < len(yy):
            dpr.append(average_precision_score(yy, pa[i]) - (average_precision_score(yy, pb[i]) if np.ptp(pb[i]) > 0 else yy.mean()))
    q = lambda v: [round(float(np.percentile(v, 2.5)), 4), round(float(np.percentile(v, 97.5)), 4)]
    return dict(d_brier=round(float(np.mean((pa - y) ** 2) - np.mean((pb - y) ** 2)), 4), d_brier_ci=q(db),
                d_acc=round(float(np.mean((pa >= .5) == y) - np.mean((pb >= .5) == y)), 4), d_acc_ci=q(dacc), d_prauc_ci=q(dpr))


R4 = lambda d: {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in d.items()}
summary, base_rows, round_rows, seed_rows, thr_rows, gates = [], [], [], [], [], []
for L in LEADS:
    g = M[M.lead == L].reset_index(drop=True)
    r = {**core(g.y_high, g.FINAL), **calib(g.y_high, g.FINAL)}
    ci, cci = boot(g, "FINAL"), boot(g, "FINAL", cluster=True)
    summary.append({"lead": L, **R4(r), "acc_ci_row": ci["accuracy"], "acc_ci_province_cluster": cci["accuracy"], "recall_ci": ci["recall_high"],
                    "f1_high_ci": ci["f1_high"], "macro_f1_ci": ci["macro_f1"], "pr_auc_ci": ci["pr_auc"], "brier_ci": ci["brier"]})
    for b, nm in BASES.items():
        rb = core(g.y_high, g[b]); pr = paired(g, "FINAL", b)
        base_rows.append({"lead": L, "baseline": b, "description": nm, **{f"base_{k}": round(float(rb[k]), 4) if rb[k] == rb[k] else None for k in KEYS},
                          "base_TP/FP/FN/TN": f'{rb["TP"]}/{rb["FP"]}/{rb["FN"]}/{rb["TN"]}', **{f"FINAL_{k}": round(float(r[k]), 4) for k in KEYS}, **pr})
    for s, x in g.groupby("survey"):
        rr = core(x.y_high, x.FINAL)
        round_rows.append({"lead": L, "round": s, **R4(rr), "pers_accuracy": round(core(x.y_high, x.PERS)["accuracy"], 4),
                           "pers_recall_high": round(core(x.y_high, x.PERS)["recall_high"], 4)})
    for sd, x in S[S.lead == L].groupby("seed"):
        rr = core(x.y_high, x.p_final); seed_rows.append({"lead": L, "seed": int(sd), **R4({k: rr[k] for k in KEYS + ("TP", "FP", "FN", "TN")})})
    for t in np.round(np.arange(.30, .71, .05), 2):
        rr = core(g.y_high, np.where(g.FINAL.values >= t, 1.0, 0.0))
        thr_rows.append({"lead": L, "threshold": float(t), **R4({k: rr[k] for k in ("accuracy", "precision_high", "recall_high", "f1_high", "macro_f1", "balanced_accuracy")}),
                         "TP/FP/FN/TN": f'{rr["TP"]}/{rr["FP"]}/{rr["FN"]}/{rr["TN"]}'})
    RR = [x for x in round_rows if x["lead"] == L]; SR = [x for x in seed_rows if x["lead"] == L]
    B = {x["baseline"]: x for x in base_rows if x["lead"] == L}
    G = {"G1_acc>=.75": r["accuracy"] >= .75,
         "G2_acc_beats_alwaysLOW": B["ALWAYS_LOW"]["d_acc_ci"][0] > 0,
         "G3_recall>=.75_and_each_round>=.50": r["recall_high"] >= .75 and min(x["recall_high"] for x in RR) >= .5,
         "G4_prec>=.60_F1>=.70": (r["precision_high"] >= .6) and r["f1_high"] >= .7,
         "G5_BA>=.75_macroF1>=.75": r["balanced_accuracy"] >= .75 and r["macro_f1"] >= .75,
         "G6_calibration_consistent": abs(r["mean_p_minus_rate"]) <= .10 and r["cox_p"] >= .05,
         "G7_brier_beats_PERS_and_CLIM": B["PERS"]["d_brier_ci"][1] < 0 and B["CLIM"]["d_brier_ci"][1] < 0,
         "G8_prauc>=PERS": r["pr_auc"] >= B["PERS"]["base_pr_auc"],
         "G9_each_seed>=.75_each_round>=.70": min(x["accuracy"] for x in SR) >= .75 and min(x["accuracy"] for x in RR) >= .70,
         "G10c_cluster_acc_lo>=.65": cci["accuracy"][0] >= .65}
    gates.append({"lead": L, **G, "all_G1_G9": all(v for k, v in G.items() if not k.startswith("G10"))})
mx = 0
for x in gates:
    if x["all_G1_G9"] and mx == x["lead"] - 1:
        mx = x["lead"]
pd.DataFrame(summary).to_csv(EV / "REL_summary_by_lead.csv", index=False, lineterminator="\n")
pd.DataFrame(base_rows).to_csv(EV / "REL_vs_baselines.csv", index=False, lineterminator="\n")
pd.DataFrame(round_rows).to_csv(EV / "REL_by_round.csv", index=False, lineterminator="\n")
pd.DataFrame(seed_rows).to_csv(EV / "REL_by_seed.csv", index=False, lineterminator="\n")
pd.DataFrame(thr_rows).to_csv(EV / "REL_threshold_sensitivity.csv", index=False, lineterminator="\n")
pd.DataFrame(gates).to_csv(EV / "REL_gates_by_lead.csv", index=False, lineterminator="\n")
# HIGH-risk detection detail (Lead 1) and province breakdown (Leads 1-5)
g1 = M[M.lead == 1]
g1[g1.y_high == 1].assign(pct=lambda d: (100 / (1 + np.exp(-d.y_true))).round(1), FINAL=lambda d: d.FINAL.round(3), PERS=lambda d: d.PERS.round(3),
                          detected=lambda d: d.FINAL >= .5)[["survey", "province", "region", "pct", "FINAL", "PERS", "detected"]].sort_values(["survey", "province"]).to_csv(EV / "REL_HIGH_cases_L1.csv", index=False, lineterminator="\n")
g1[(g1.y_high == 0) & (g1.FINAL >= .5)].assign(pct=lambda d: (100 / (1 + np.exp(-d.y_true))).round(1))[["survey", "province", "region", "pct", "FINAL", "PERS"]].to_csv(EV / "REL_false_alarms_L1.csv", index=False, lineterminator="\n")
pv = M.assign(ok=(M.FINAL >= .5) == (M.y_high == 1)).groupby(["province", "region"]).agg(rows=("ok", "size"), correct=("ok", "sum"), rounds=("survey", "nunique")).reset_index()
pv["accuracy"] = (pv.correct / pv.rows).round(3); pv.sort_values("accuracy").to_csv(EV / "REL_by_province_L1to5.csv", index=False, lineterminator="\n")
rg = M[M.lead == 1].assign(ok=lambda d: (d.FINAL >= .5) == (d.y_high == 1)).groupby("region").agg(rows=("ok", "size"), accuracy=("ok", "mean"), high=("y_high", "sum")).round(3).reset_index()
rg.to_csv(EV / "REL_by_region_L1.csv", index=False, lineterminator="\n")
g1b = g1.assign(bin=pd.cut(g1.FINAL, [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0], include_lowest=True))
g1b.groupby("bin", observed=True).agg(n=("y_high", "size"), mean_p=("FINAL", "mean"), observed=("y_high", "mean")).round(3).reset_index().to_csv(EV / "REL_reliability_L1.csv", index=False, lineterminator="\n")
json.dump({"max_reliable_lead_G1_G9": mx, "independent_evaluation_periods": 3, "evaluation_rows_per_lead": 72,
           "note": "3 test rounds (2018, 2019, 2021) are the only genuinely distinct evaluation periods; leads re-forecast the same 72 province-rounds."},
          open(EV / "REL_max_lead.json", "w"), indent=1)
pd.set_option("display.width", 320); pd.set_option("display.max_columns", 40)
print(pd.DataFrame(summary).drop(columns=["acc_ci_row", "f1_high_ci", "macro_f1_ci", "pr_auc_ci", "brier_ci"]).to_string(index=False))
print(pd.DataFrame(gates).to_string(index=False)); print("MAX LEAD", mx)
print(pd.DataFrame(base_rows)[["lead", "baseline", "base_accuracy", "base_recall_high", "base_macro_f1", "base_pr_auc", "base_brier", "d_brier", "d_brier_ci", "d_acc_ci"]].to_string(index=False))
print(pd.DataFrame(round_rows)[["lead", "round", "n", "high", "accuracy", "recall_high", "precision_high", "pers_accuracy", "pers_recall_high", "FP", "FN"]].to_string(index=False))
