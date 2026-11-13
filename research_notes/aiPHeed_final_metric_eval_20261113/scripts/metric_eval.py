r"""Metric-by-metric evaluation of FINAL against the owner's 8 targets (recall, F1, precision, BA >= 0.70; Brier <= 0.20; accuracy >= 0.75;
ROC-AUC >= 0.70; PR-AUC > HIGH prevalence), from the EXISTING 5-seed walk-forward fits (parts_mix p_final; 110 fits; no refit, cut-off 0.50).
By lead (1-8), by survey round, by class, vs persistence and always-LOW, seed and round-removal stability, bootstrap CIs. Run: python -I metric_eval.py"""
import glob, json
from pathlib import Path
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score, average_precision_score
HERE = Path(__file__).resolve().parents[1]; RN = HERE.parent; EV = HERE / "evidence"
K = ["key", "survey", "lead"]; rng = np.random.default_rng(20261113)
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")[K + ["province", "y_high", "PERS"]]
X = pd.concat([pd.read_csv(f) for f in glob.glob(str(RN / "aiPHeed_final_7of7_20261113" / "parts_mix" / "FINALMIX__*.csv"))])
S = X.merge(LAB, on=K)
M = X.groupby(K, as_index=False)["p_final"].mean().rename(columns={"p_final": "FINAL"}).merge(LAB, on=K)
M["ALWAYS_LOW"] = 0.0
T = {"recall_high": (.70, ">="), "f1_high": (.70, ">="), "precision_high": (.70, ">="), "balanced_accuracy": (.70, ">="), "brier": (.20, "<="),
     "accuracy": (.75, ">="), "roc_auc": (.70, ">="), "pr_auc": (None, "> prevalence")}
def met(y, p):
    y = np.asarray(y, int); p = np.asarray(p, float); h = p >= .5
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    rh, rl = tp / max(1, tp + fn), tn / max(1, tn + fp); ph = tp / (tp + fp) if tp + fp else np.nan; pl = tn / (tn + fn) if tn + fn else np.nan
    f1h = 2 * ph * rh / (ph + rh) if tp else 0.0; f1l = 2 * pl * rl / (pl + rl) if tn else 0.0
    both = 0 < y.sum() < len(y)
    return {"n": len(y), "high": int(y.sum()), "prevalence": y.mean(), "accuracy": (tp + tn) / len(y), "recall_high": rh, "precision_high": ph, "f1_high": f1h,
            "recall_low": rl, "precision_low": pl, "f1_low": f1l, "balanced_accuracy": (rh + rl) / 2, "brier": float(np.mean((p - y) ** 2)),
            "roc_auc": roc_auc_score(y, p) if both and np.ptp(p) > 0 else np.nan, "pr_auc": average_precision_score(y, p) if both and np.ptp(p) > 0 else (y.mean() if both else np.nan),
            "TP": tp, "FP": fp, "FN": fn, "TN": tn}
def ci(g, col, key, B=3000):
    v = []
    for _ in range(B):
        i = rng.integers(0, len(g), len(g)); y = g.y_high.values[i]
        if 0 < y.sum() < len(y): v.append(met(y, g[col].values[i])[key])
    return [round(float(np.nanpercentile(v, 2.5)), 3), round(float(np.nanpercentile(v, 97.5)), 3)]
def status(r, k):
    t, op = T[k]
    v = r[k]
    if v != v: return "n/a"
    if op == ">=": return "PASS" if v >= t else "FAIL"
    if op == "<=": return "PASS" if v <= t else "FAIL"
    return "PASS" if v > r["prevalence"] else "FAIL"
lead_rows, round_rows, base_rows, seed_rows = [], [], [], []
for L, g in M.groupby("lead"):
    r = met(g.y_high, g.FINAL)
    lead_rows.append({"lead": int(L), **{k: round(v, 4) if isinstance(v, float) else v for k, v in r.items()},
                      **{f"{k}_status": status(r, k) for k in T}, "all_pass": all(status(r, k) == "PASS" for k in T),
                      **({f"{k}_ci95": ci(g, "FINAL", k) for k in ("recall_high", "f1_high", "precision_high", "balanced_accuracy", "brier", "accuracy")} if L <= 2 else {})})
    for b in ("PERS", "ALWAYS_LOW"):
        rb = met(g.y_high, g[b]); d = ((g.FINAL - g.y_high) ** 2 - (g[b] - g.y_high) ** 2).values
        bs = [d[rng.integers(0, len(d), len(d))].mean() for _ in range(3000)]
        base_rows.append({"lead": int(L), "baseline": b, **{k: round(rb[k], 4) if rb[k] == rb[k] else None for k in T}, "prevalence": round(rb["prevalence"], 4),
                          "TP/FP/FN/TN": f'{rb["TP"]}/{rb["FP"]}/{rb["FN"]}/{rb["TN"]}', "FINAL_minus_base_brier": round(float(d.mean()), 4),
                          "brier_diff_ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)]})
    for s, x in g.groupby("survey"):
        rr = met(x.y_high, x.FINAL)
        round_rows.append({"lead": int(L), "round": s, **{k: round(v, 4) if isinstance(v, float) else v for k, v in rr.items()}, **{f"{k}_status": status(rr, k) for k in T}})
    for sd, x in S[S.lead == L].groupby("seed"):
        rr = met(x.y_high, x.p_final); seed_rows.append({"lead": int(L), "seed": int(sd), **{k: round(rr[k], 4) for k in T}})
pd.DataFrame(lead_rows).to_csv(EV / "ME_by_lead.csv", index=False, lineterminator="\n")
pd.DataFrame(round_rows).to_csv(EV / "ME_by_round.csv", index=False, lineterminator="\n")
pd.DataFrame(base_rows).to_csv(EV / "ME_baselines.csv", index=False, lineterminator="\n")
pd.DataFrame(seed_rows).to_csv(EV / "ME_by_seed.csv", index=False, lineterminator="\n")
pd.set_option("display.width", 320); pd.set_option("display.max_columns", 60)
L1 = pd.DataFrame(lead_rows)
print(L1[["lead", "n", "high", "prevalence", "recall_high", "f1_high", "precision_high", "balanced_accuracy", "brier", "accuracy", "roc_auc", "pr_auc", "recall_low", "precision_low", "f1_low", "TP", "FP", "FN", "TN", "all_pass"]].to_string(index=False))
print(L1[[c for c in L1.columns if c.endswith("_status")]].assign(lead=L1.lead).to_string(index=False))
print({k: v for k, v in lead_rows[0].items() if k.endswith("ci95")})
R = pd.DataFrame(round_rows); print(R[R.lead <= 2][["lead", "round", "n", "high", "recall_high", "f1_high", "precision_high", "balanced_accuracy", "brier", "accuracy", "roc_auc", "pr_auc", "prevalence"]].to_string(index=False))
B = pd.DataFrame(base_rows); print(B[B.lead <= 2].to_string(index=False))
Sd = pd.DataFrame(seed_rows); print(Sd[Sd.lead == 1].to_string(index=False)); print(Sd.groupby("lead")[list(T)].agg(["min", "max"]).round(3).to_string())
