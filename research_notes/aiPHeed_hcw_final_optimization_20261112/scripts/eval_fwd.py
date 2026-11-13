"""PROTOCOL_FINAL.md stage 3: forward chronological folds. Scores every arm (transparency) and applies rules 1-7 to each;
only FINAL is eligible. Writes evidence/fwd_*.csv|json."""
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binomtest
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score

STUDY = Path(__file__).resolve().parents[1]
RN, EV = STUDY.parent, STUDY / "evidence"
K, LEADS, ROUNDS = ["key", "survey", "lead"], [1, 2, 3], ("ENNS2018", "ENNS2019", "ENNS2021")
G = pd.read_csv(r"C:\Users\admin\aipheed_e145\backend\data\e158\out\oof.csv")
LAB = G[G.lead.isin(LEADS)][K + ["province", "region", "island", "y_anchor", "y_true", "y_high", "q_true", "PERS", "E158"]]
rd = lambda pat: pd.concat([pd.read_csv(f) for f in glob.glob(str(pat))], ignore_index=True)
NEW = rd(STUDY / "parts_fwd" / "*.csv")
P = {a: d for a, d in NEW.groupby("arm") if d.groupby(["survey", "lead", "seed"]).ngroups == 45}
P["FIX"] = rd(RN / "aiPHeed_objective_completion_20261111" / "parts" / "FIX__*.csv")
P = {a: d[d.seed.isin([168, 1, 2, 3, 4]) & d.lead.isin(LEADS)].copy() for a, d in P.items()}
b = P["BASE"].merge(P["FIX"][K + ["seed", "p"]], on=K + ["seed"], suffixes=("", "_fix"))
repro = {"rows": len(b), "max_abs_diff_BASE_vs_FIX": float((b.p - b.p_fix).abs().max())}
ORDER = [a for a in ["RATE", "RATE_SQRT", "IMPUTE", "RIMP", "MIND", "DROPGAP", "COMP", "FINAL"] if a in P]
M, SEEDP = [], {}
for a, d in P.items():
    SEEDP[a] = d[K + ["seed", "p"]]
    M.append(d.groupby(K, as_index=False)[["p", "mu"]].mean().merge(LAB, on=K).assign(arm=a))
for a in ("PERS", "E158"):
    M.append(LAB.assign(arm=a, p=LAB[a], mu=np.nan))
M = pd.concat(M, ignore_index=True)
rng = np.random.default_rng(7)


def base(p, y, q):
    h = p >= .5
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    pr, rh, rl = tp / max(1, tp + fp), tp / max(1, tp + fn), tn / max(1, tn + fp)
    two = 0 < y.sum() < len(y)
    return dict(accuracy=100 * (h == (y == 1)).mean(), precision=pr, recall_high=rh, recall_low=rl, f1=2 * pr * rh / max(1e-9, pr + rh), balanced_accuracy=50 * (rh + rl),
                roc_auc=roc_auc_score(y, p) if two else np.nan, pr_auc=average_precision_score(y, p) if two else np.nan,
                brier=float(np.mean((p - y) ** 2)), brier_q=float(np.mean((p - q) ** 2)), TP=tp, FP=fp, FN=fn, TN=tn)


def met(g, ci=True):
    p, y, q = np.clip(g.p.values.astype(float), 1e-6, 1 - 1e-6), g.y_high.values.astype(int), g.q_true.values
    m = base(p, y, q)
    m["mean_fold_accuracy"] = (g.assign(ok=((p >= .5) == (y == 1))).groupby("survey")["ok"].mean() * 100).mean()
    m["log_loss"] = float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))
    if 0 < y.sum() < len(y):
        c = LogisticRegression(C=1e6, max_iter=2000).fit(np.log(p / (1 - p)).reshape(-1, 1), y)
        m["cal_slope"], m["cal_intercept"] = float(c.coef_[0][0]), float(c.intercept_[0])
    bn = np.clip((p * 5).astype(int), 0, 4)
    m["ece_5bin"] = float(sum(abs(p[bn == k].mean() - y[bn == k].mean()) * (bn == k).mean() for k in range(5) if (bn == k).any()))
    if g.mu.notna().all():
        m["mean_error_logit"], m["mean_pred_change"], m["mean_actual_change"] = float((g.mu - g.y_true).mean()), float((g.mu - g.y_anchor).mean()), float((g.y_true - g.y_anchor).mean())
        m["sd_pred_change"], m["sd_actual_change"] = float((g.mu - g.y_anchor).std()), float((g.y_true - g.y_anchor).std())
    if ci:
        bs = pd.DataFrame([base(p[ix], y[ix], q[ix]) for ix in (rng.integers(0, len(p), len(p)) for _ in range(2000))])
        for k in ("accuracy", "balanced_accuracy", "brier"):
            m[f"{k}_ci95"] = f"[{np.nanpercentile(bs[k], 2.5):.3g}, {np.nanpercentile(bs[k], 97.5):.3g}]"
    return {"n": len(g), "n_high": int(y.sum()), **{k: (round(v, 4) if isinstance(v, float) else v) for k, v in m.items()}}


def seed_stats(a, L):
    if a not in SEEDP:
        return {}
    s = SEEDP[a][SEEDP[a].lead == L].merge(LAB, on=K)
    s["ok"] = (s.p >= .5) == (s.y_high == 1)
    acc = s.groupby("seed").apply(lambda x: (x.groupby("survey")["ok"].mean() * 100).mean(), include_groups=False)
    hi = s.assign(h=s.p >= .5).groupby(K)["h"].mean()
    return {"worst_seed_mean_fold": round(float(acc.min()), 1), "seed_sd_mean_fold": round(float(acc.std()), 2), "rows_class_flips_across_seeds": int(((hi > 0) & (hi < 1)).sum())}


T = pd.DataFrame([{"arm": a, "lead": L, **met(g), **seed_stats(a, L)} for (a, L), g in M.groupby(["arm", "lead"])])
T.to_csv(EV / "fwd_metrics_by_lead.csv", index=False, lineterminator="\n")
BYR = pd.DataFrame([{"arm": a, "lead": L, "test_round": s, **met(g, ci=False)} for (a, L, s), g in M.groupby(["arm", "lead", "survey"])])
BYR.to_csv(EV / "fwd_metrics_by_round.csv", index=False, lineterminator="\n")
pd.DataFrame([{"arm": a, "lead": L, "island": s, **{k: v for k, v in met(g, ci=False).items() if k in ("n", "n_high", "accuracy", "recall_high", "recall_low", "brier", "TP", "FP", "FN", "TN")}}
              for (a, L, s), g in M.groupby(["arm", "lead", "island"])]).to_csv(EV / "fwd_metrics_by_island.csv", index=False, lineterminator="\n")
CAL = ["Cavite", "Laguna", "Batangas", "Rizal", "Quezon"]
M[M.province.isin(CAL)].pivot_table(index=["province", "survey", "lead", "y_high"], columns="arm", values="p").round(3).to_csv(EV / "fwd_calabarzon_rows.csv", lineterminator="\n")
M[M.lead == 1].pivot_table(index=["province", "region", "island", "survey", "y_high", "q_true"], columns="arm", values="p").round(3).to_csv(EV / "fwd_rows_L1.csv", lineterminator="\n")


def paired(a, leads, ref="FIX"):
    x = M[(M.arm == a) & M.lead.isin(leads)].merge(M[(M.arm == ref) & M.lead.isin(leads)][K + ["p"]], on=K, suffixes=("", "_b"))
    d = ((x.p - x.q_true) ** 2 - (x.p_b - x.q_true) ** 2).values
    cl = (x.key + x.survey).values
    u = np.unique(cl)
    idx = {c: np.flatnonzero(cl == c) for c in u}
    bs = np.array([d[np.concatenate([idx[c] for c in rng.choice(u, len(u))])].mean() for _ in range(6000)])
    return {"diff": round(float(d.mean()), 4), "ci": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)], "share_boot_below_0": round(float((bs < 0).mean()), 4)}


def mcnemar(a, L, ref="FIX"):
    x = M[(M.arm == a) & (M.lead == L)].merge(M[(M.arm == ref) & (M.lead == L)][K + ["p"]], on=K, suffixes=("", "_b"))
    oa, ob = (x.p >= .5) == (x.y_high == 1), (x.p_b >= .5) == (x.y_high == 1)
    w, l = int((oa & ~ob).sum()), int((~oa & ob).sum())
    return {"better_rows": w, "worse_rows": l, "p": round(float(binomtest(w, w + l, .5).pvalue), 3) if w + l else 1.0}


t = T.set_index(["arm", "lead"])
br = BYR[BYR.lead == 1].set_index(["arm", "test_round"])
dec, rows = {}, []
for a in ORDER:
    g = lambda c, L, arm=a: t.at[(arm, L), c]
    r1 = all(g("mean_fold_accuracy", L) >= g("mean_fold_accuracy", L, "FIX") - 1.4 for L in LEADS)
    r2 = int(sum(g("brier_q", L) < g("brier_q", L, "FIX") for L in LEADS))
    r3 = paired(a, LEADS)
    r4 = all(g("recall_high", L) >= g("recall_high", L, "FIX") - 0.04 and g("recall_low", L) >= g("recall_low", L, "FIX") - 0.04 for L in LEADS)
    r5 = all(g("worst_seed_mean_fold", L) >= g("worst_seed_mean_fold", L, "FIX") - 1.4 for L in LEADS)
    r6 = bool(g("balanced_accuracy", 1) >= g("balanced_accuracy", 1, "FIX"))
    r7 = all((br.at[(a, s), "TP"] + br.at[(a, s), "TN"]) >= (br.at[("FIX", s), "TP"] + br.at[("FIX", s), "TN"]) - 1 for s in ROUNDS)
    ok = bool(r1 and r2 >= 2 and r3["ci"][1] < 0 and r4 and r5 and r6 and r7)
    mc = {L: mcnemar(a, L) for L in LEADS}
    dec[a] = {"rule1": bool(r1), "rule2_leads_better": r2, "rule3_pooled": r3, "rule3_L1": paired(a, [1]), "rule4": bool(r4), "rule5": bool(r5), "rule6": r6, "rule7": bool(r7), "PASS_1_7": ok, "mcnemar": mc,
              "eligible": a == "FINAL"}
    rows.append({"arm": a, "L1_acc": g("accuracy", 1), "L2_acc": g("accuracy", 2), "L3_acc": g("accuracy", 3), "L1_prec": g("precision", 1), "L1_rec_high": g("recall_high", 1), "L1_rec_low": g("recall_low", 1),
                 "L1_f1": g("f1", 1), "L1_bal_acc": g("balanced_accuracy", 1), "L1_auc": g("roc_auc", 1), "L1_brier": g("brier", 1), "L1_cal_slope": g("cal_slope", 1), "pooled_brier_q_diff": r3["diff"],
                 "ci_lo": r3["ci"][0], "ci_hi": r3["ci"][1], "L1_better": mc[1]["better_rows"], "L1_worse": mc[1]["worse_rows"], "worst_seed_L1": g("worst_seed_mean_fold", 1),
                 "r1": r1, "r2": r2, "r3": r3["ci"][1] < 0, "r4": r4, "r5": r5, "r6": r6, "r7": r7, "PASS_1_7": ok})
D = pd.DataFrame(rows)
D.to_csv(EV / "fwd_decision_table.csv", index=False, lineterminator="\n")
(EV / "fwd_decision.json").write_text(json.dumps({"reproduction": repro, "arms": dec}, indent=1, default=str))
pd.set_option("display.width", 280)
print(json.dumps(repro))
show = ["arm", "lead", "accuracy", "precision", "recall_high", "recall_low", "f1", "balanced_accuracy", "roc_auc", "pr_auc", "brier", "brier_q", "cal_slope", "ece_5bin", "TP", "FP", "FN", "TN", "worst_seed_mean_fold", "mean_error_logit", "accuracy_ci95"]
for L in LEADS:
    print(T[T.lead == L][show].sort_values("brier_q").to_string(index=False))
print(D.to_string(index=False))
print(BYR[(BYR.lead == 1)].pivot_table(index="arm", columns="test_round", values=["accuracy", "FP", "FN", "mean_error_logit"]).round(2).to_string())
