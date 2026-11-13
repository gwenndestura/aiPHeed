r"""FINAL-ETMIX (protocol a365da1f; p = (p_g + p_s)/2) walk-forward evaluation at Leads 1-8 from the EXISTING fits (no refit, no new
variant): ../aiPHeed_final_7of7_20261113/parts_mix (5 seeds). Objective 2 metrics with province-round bootstrap intervals, confusion
matrices, per-round and per-province results, seed spread, calibration diagnostics, threshold sensitivity (supplementary only; the
0.50 cut-off is fixed), and Objective 4 paired comparisons with the four required baselines on identical rows.
Retrospective: the 72 province-rounds were reused during development. Run: python -I etmix_eval.py"""
import glob, json, sys
from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import binomtest, chi2
from sklearn.metrics import roc_auc_score

HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent
ST, MX = RN / "aiPHeed_final_stability_lead_20261113", RN / "aiPHeed_final_7of7_20261113"
sys.path.insert(0, str(RN / "aiPHeed_final_standalone_20261113" / "scripts"))
from calib import _irls, ece, intercept, logit, slope   # noqa: E402
EV = HERE / "evidence"
K = ["key", "survey", "lead"]
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
BASE = {"PERS": "Naive persistence (latest provincial survey)", "PSA": "PSA-only indicator baseline (logistic)",
        "LR_NEWS": "NLP-only sentiment baseline (logistic, news features)", "LR": "Logistic regression (all inputs + anchor)"}
REF = {"FINAL": "FINAL (g only; historical comparison)", "GNT": "E151 LightGBM residual (reference)", "NEWS": "Anchor + NLP LightGBM (reference)"}
rng = np.random.default_rng(20261113)

X = pd.concat([pd.read_csv(f) for f in glob.glob(str(MX / "parts_mix" / "FINALMIX__*.csv"))])
meta = {(d["survey"], d["lead"], d["seed"]): d["train_high_share"] for d in (json.load(open(f)) for f in glob.glob(str(ST / "features_lead" / "FINALL__*.json")))}
X["p_clim"] = [meta[(s, l, sd)] for s, l, sd in zip(X.survey, X.lead, X.seed)]
SEEDROWS = X.merge(LAB[K + ["y_high"]], on=K)
M = X.groupby(K, as_index=False).agg(ETMIX=("p", "mean"), FINAL=("p_final", "mean"), p_clim=("p_clim", "mean"), gap_q=("gap_q", "first"),
                                    differs=("p_et", lambda s: s.notna().any()))
M = M.merge(LAB[K + ["province", "region", "y_high", "y_true", "y_anchor"] + list(BASE) + ["GNT", "NEWS"]], on=K)
M.to_csv(EV / "ETMIX_rows_all_leads.csv", index=False)


def core(y, p, pc=None):
    y = np.asarray(y, int); p = np.asarray(p, float); h = p >= .5
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    rec, spec, prec = tp / max(1, tp + fn), tn / max(1, tn + fp), tp / max(1, tp + fp)
    o = dict(n=len(y), high=int(y.sum()), low=int((1 - y).sum()), accuracy=(tp + tn) / len(y), precision=prec, recall_high=rec,
             f1=2 * prec * rec / max(1e-9, prec + rec), auroc=roc_auc_score(y, p) if 0 < y.sum() < len(y) else np.nan,
             balanced_accuracy=.5 * (rec + spec), recall_low=spec, brier=float(np.mean((p - y) ** 2)), TP=tp, FP=fp, FN=fn, TN=tn)
    if pc is not None:
        o["bss_vs_training_rate"] = 1 - o["brier"] / float(np.mean((np.asarray(pc) - y) ** 2))
        o["ece10"], o["mean_p_minus_rate"], o["cal_slope"], o["cal_intercept_logit"] = ece(p, y), float(p.mean() - y.mean()), slope(p, y), intercept(p, y)
        lp = logit(p); b = _irls(np.column_stack([np.ones(len(y)), lp]), y.astype(float))
        m1 = np.clip(1 / (1 + np.exp(-np.clip(b[0] + b[1] * lp, -30, 30))), 1e-9, 1 - 1e-9); pcl = np.clip(p, 1e-6, 1 - 1e-6)
        lr = 2 * (np.sum(y * np.log(m1) + (1 - y) * np.log(1 - m1)) - np.sum(y * np.log(pcl) + (1 - y) * np.log(1 - pcl)))
        o["cox_p"] = float(chi2.sf(max(lr, 0.0), 2))
    return o


KEYS = ("accuracy", "precision", "recall_high", "f1", "auroc", "balanced_accuracy", "brier")


def boot(y, p, B=3000):
    y, p = np.asarray(y), np.asarray(p); out = []
    for _ in range(B):
        i = rng.integers(0, len(y), len(y))
        if 0 < y[i].sum() < len(y):
            r = core(y[i], p[i]); out.append([r[k] for k in KEYS])
    A = np.array(out, float)
    return {k: [round(float(np.nanpercentile(A[:, j], 2.5)), 3), round(float(np.nanpercentile(A[:, j], 97.5)), 3)] for j, k in enumerate(KEYS)}


R = lambda d: {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}
by_lead, base_rows, thr_rows = {}, [], []
for L, g in M.groupby("lead"):
    y = g.y_high.values
    r = core(y, g.ETMIX, g.p_clim)
    rounds = {s[-4:]: R({k: v for k, v in core(x.y_high, x.ETMIX).items() if k in ("n", "high", "accuracy", "balanced_accuracy", "recall_high", "precision", "auroc", "FP", "FN")})
              for s, x in g.groupby("survey")}
    seeds = {int(sd): core(x.y_high, x.p)["accuracy"] for sd, x in SEEDROWS[SEEDROWS.lead == L].groupby("seed")}
    mfa = float(np.mean([v["accuracy"] for v in rounds.values()]))
    by_lead[int(L)] = {**R(r), "ci95": boot(y, g.ETMIX.values), "by_round": rounds, "mean_fold_accuracy": round(mfa, 4),
                       "seed_accuracy": {k: round(float(v), 4) for k, v in seeds.items()}, "rows_where_mixture_differs_from_FINAL": int(g.differs.sum())}
    for b, name in {**BASE, **REF}.items():
        x = g[g[b].notna()]
        rb, re_ = core(x.y_high, x[b]), core(x.y_high, x.ETMIX)
        d = (x.ETMIX - x.y_high) ** 2 - (x[b] - x.y_high) ** 2
        bs = np.array([d.values[rng.integers(0, len(d), len(d))].mean() for _ in range(4000)])
        ce, cb = (x.ETMIX >= .5) == (x.y_high == 1), (x[b] >= .5) == (x.y_high == 1)
        n01, n10 = int((ce & ~cb).sum()), int((~ce & cb).sum())
        mc = binomtest(n01, n01 + n10, .5).pvalue if n01 + n10 else 1.0
        da = []
        for _ in range(2000):
            i = rng.integers(0, len(x), len(x)); yy = x.y_high.values[i]
            if 0 < yy.sum() < len(yy):
                da.append(roc_auc_score(yy, x.ETMIX.values[i]) - roc_auc_score(yy, x[b].values[i]))
        base_rows.append({"lead": int(L), "comparator": b, "description": name, "required_baseline": b in BASE, "n": len(x),
                          **{f"ETMIX_{k}": round(re_[k], 3) for k in KEYS}, **{f"BASE_{k}": round(rb[k], 3) for k in KEYS},
                          "BASE_TP/FP/FN/TN": f'{rb["TP"]}/{rb["FP"]}/{rb["FN"]}/{rb["TN"]}',
                          "brier_ETMIX_minus_base": round(float(d.mean()), 4), "brier_ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
                          "brier_sig_better": bool(np.percentile(bs, 97.5) < 0), "auc_diff": round(float(np.mean(da)), 3),
                          "auc_diff_ci95": [round(float(np.percentile(da, 2.5)), 3), round(float(np.percentile(da, 97.5)), 3)],
                          "mcnemar_ETMIX_right_base_wrong": n01, "mcnemar_base_right_ETMIX_wrong": n10, "mcnemar_p": round(float(mc), 4)})
    if L in (1, 2):
        for t in np.round(np.arange(.30, .71, .05), 2):
            rr = core(y, np.where(g.ETMIX.values >= t, .99, .01))
            thr_rows.append({"lead": int(L), "threshold": float(t), **{k: round(rr[k], 3) for k in ("accuracy", "precision", "recall_high", "f1", "balanced_accuracy")},
                             "TP/FP/FN/TN": f'{rr["TP"]}/{rr["FP"]}/{rr["FN"]}/{rr["TN"]}'})
g1 = M[M.lead == 1].copy(); g1["bin"] = pd.cut(g1.ETMIX, [0, .1, .2, .3, .4, .5, .6, .7, .8, .9, 1.0], include_lowest=True)
g1.groupby("bin", observed=True).agg(n=("y_high", "size"), mean_p=("ETMIX", "mean"), observed_high_rate=("y_high", "mean")).round(3).reset_index().to_csv(EV / "ETMIX_reliability_L1.csv", index=False)
P = M.pivot_table(index=["province", "region", "survey", "y_high"], columns="lead", values="ETMIX").round(3).reset_index()
ok = M.assign(ok=(M.ETMIX >= .5) == (M.y_high == 1)).groupby(["province", "survey"])["ok"].agg(["sum", "size"])
P["leads_correct"] = [f"{int(ok.loc[(a, b), 'sum'])}/{int(ok.loc[(a, b), 'size'])}" for a, b in zip(P.province, P.survey)]
P.to_csv(EV / "ETMIX_province_by_lead.csv", index=False)
B = pd.DataFrame(base_rows)
thesis, robust, rob_rows = 0, 0, []
for L in sorted(by_lead):
    r = by_lead[L]
    pers = B[(B.lead == L) & (B.comparator == "PERS")].iloc[0]
    crit = {"mean_fold_acc>=.75": r["mean_fold_accuracy"] >= .75, "brier_sig_better_than_persistence": bool(pers.brier_sig_better),
            "every_seed>=.75": min(r["seed_accuracy"].values()) >= .75, "every_round>=.70": min(v["accuracy"] for v in r["by_round"].values()) >= .70,
            "HIGH_and_LOW_recall>=.75": r["recall_high"] >= .75 and r["recall_low"] >= .75}
    rob_rows.append({"lead": L, **crit, "robust_pass": all(crit.values())})
    if crit["mean_fold_acc>=.75"] and thesis == L - 1:
        thesis = L
    if all(crit.values()) and robust == L - 1:
        robust = L
json.dump({"by_lead": by_lead, "thesis_algorithm3_max_lead": thesis, "robust_rule_max_lead": robust, "robust_rule_by_lead": rob_rows,
           "note": "Retrospective on 72 reused province-rounds (50 at Leads 7-8). Not independent validation."}, open(EV / "ETMIX_lead_results.json", "w"), indent=1, default=float)
B.to_csv(EV / "ETMIX_vs_baselines_by_lead.csv", index=False)
pd.DataFrame(thr_rows).to_csv(EV / "ETMIX_threshold_sensitivity.csv", index=False)
T = pd.DataFrame([{"lead": L, "n": r["n"], "HIGH": r["high"], "LOW": r["low"], "accuracy": r["accuracy"], "acc_ci": r["ci95"]["accuracy"], "precision": r["precision"],
                   "recall": r["recall_high"], "rec_ci": r["ci95"]["recall_high"], "f1": r["f1"], "auc": r["auroc"], "auc_ci": r["ci95"]["auroc"], "BA": r["balanced_accuracy"],
                   "brier": r["brier"], "TP/FP/FN/TN": f'{r["TP"]}/{r["FP"]}/{r["FN"]}/{r["TN"]}', "mean_fold_acc": r["mean_fold_accuracy"],
                   "ece": r["ece10"], "p-rate": r["mean_p_minus_rate"], "slope": r["cal_slope"], "cox_p": r["cox_p"],
                   "worst_seed_acc": min(r["seed_accuracy"].values()), "round_recall": {s: f'{round(v["recall_high"] * v["high"])}/{v["high"]}' for s, v in r["by_round"].items()}}
                  for L, r in by_lead.items()])
T.to_csv(EV / "ETMIX_summary_by_lead.csv", index=False)
pd.set_option("display.width", 320); pd.set_option("display.max_columns", 40)
print(T.to_string(index=False)); print("thesis max lead", thesis, "robust max lead", robust)
print(pd.DataFrame(rob_rows).to_string(index=False))
print(B[B.required_baseline][["lead", "comparator", "ETMIX_accuracy", "BASE_accuracy", "ETMIX_precision", "BASE_precision", "ETMIX_recall_high", "BASE_recall_high",
                              "ETMIX_f1", "BASE_f1", "ETMIX_auroc", "BASE_auroc", "brier_ETMIX_minus_base", "brier_ci95", "mcnemar_p"]].to_string(index=False))
