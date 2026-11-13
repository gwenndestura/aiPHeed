"""PROTOCOL_FINAL.md stage 1: score single arms on the held-out round (FNRI 2015) and compose FINAL by the locked rule.
Writes evidence/stage1_metrics.csv, stage1_paired.csv, final_config.json."""
import glob
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

STUDY = Path(__file__).resolve().parents[1]
EV = STUDY / "evidence"
K = ["key", "survey", "lead"]
rng = np.random.default_rng(7)
R = pd.concat([pd.read_csv(f) for f in glob.glob(str(STUDY / "parts_rev" / "*.csv"))], ignore_index=True)
assert R.groupby("arm").size().nunique() == 1, R.groupby("arm").size()
M = R.groupby(K + ["arm"], as_index=False).agg(p=("p", "mean"), mu=("mu", "mean"), y_true=("y_true", "first"), q_true=("q_true", "first"), y_anchor=("y_anchor", "first"))
M["y_high"] = (M.y_true >= 0).astype(int)
W = M.pivot_table(index=K + ["y_high", "q_true", "y_true", "y_anchor"], columns="arm", values="p").reset_index()
MU = M.pivot_table(index=K, columns="arm", values="mu").reset_index()


def met(p, y, q):
    h = p >= .5
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    pr, rh, rl = tp / max(1, tp + fp), tp / max(1, tp + fn), tn / max(1, tn + fp)
    return dict(n=len(y), accuracy=round(100 * (tp + tn) / len(y), 1), precision=round(pr, 3), recall_high=round(rh, 3), recall_low=round(rl, 3), f1=round(2 * pr * rh / max(1e-9, pr + rh), 3),
                balanced_accuracy=round(50 * (rh + rl), 1), roc_auc=round(roc_auc_score(y, p), 3), brier=round(float(np.mean((p - y) ** 2)), 4), brier_q=round(float(np.mean((p - q) ** 2)), 4),
                TP=tp, FP=fp, FN=fn, TN=tn)


ARMS = [a for a in ["BASE", "RATE", "RATE_SQRT", "IMPUTE", "RIMP", "MIND", "DROPGAP", "COMP", "FINAL"] if a in W]
T = pd.DataFrame([{"arm": a, "lead": L, **met(g[a].values, g.y_high.values, g.q_true.values)} for L, g in W.groupby("lead") for a in ARMS])
x = M.merge(MU[K], on=K)
bias = M.assign(err=M.mu - M.y_true, dm=M.mu - M.y_anchor, dy=M.y_true - M.y_anchor).groupby(["arm", "lead"]).agg(mean_error_logit=("err", "mean"), mean_pred_change=("dm", "mean"), mean_actual_change=("dy", "mean"),
                                                                                                           sd_pred_change=("dm", "std"), sd_actual_change=("dy", "std")).round(3).reset_index()
T = T.merge(bias, on=["arm", "lead"])
T.to_csv(EV / "stage1_metrics.csv", index=False, lineterminator="\n")


def paired(a, b="BASE", leads=(1, 2)):
    g = W[W.lead.isin(leads)]
    d = ((g[a] - g.q_true) ** 2 - (g[b] - g.q_true) ** 2).values
    cl = g.key.values
    u = np.unique(cl)
    idx = {c: np.flatnonzero(cl == c) for c in u}
    bs = np.array([d[np.concatenate([idx[c] for c in rng.choice(u, len(u))])].mean() for _ in range(6000)])
    g1 = W[W.lead == 1]
    oa, ob = (g1[a] >= .5) == (g1.y_high == 1), (g1[b] >= .5) == (g1.y_high == 1)
    return dict(arm=a, pooled_brier_q=round(float(np.mean((g[a] - g.q_true) ** 2)), 5), diff_vs_base=round(float(d.mean()), 4), ci_lo=round(float(np.percentile(bs, 2.5)), 4), ci_hi=round(float(np.percentile(bs, 97.5)), 4),
                share_boot_below_0=round(float((bs < 0).mean()), 4), L1_accuracy=round(100 * float(oa.mean()), 1), L1_rows_better=int((oa & ~ob).sum()), L1_rows_worse=int((~oa & ob).sum()))


P = pd.DataFrame([paired(a) for a in ARMS])
P.to_csv(EV / "stage1_paired.csv", index=False, lineterminator="\n")
p = P.set_index("arm")
base = p.loc["BASE"]


def pick(order):
    ok = [a for a in order if p.at[a, "pooled_brier_q"] < base.pooled_brier_q and p.at[a, "L1_accuracy"] >= base.L1_accuracy]
    return min(ok, key=lambda a: (p.at[a, "pooled_brier_q"], order.index(a))) if ok else None


choice = {"T": pick(["RATE", "RATE_SQRT"]), "M": pick(["IMPUTE", "RIMP", "DROPGAP", "MIND"]), "C": pick(["COMP"])}
cfg = {}
if choice["T"]:
    cfg["rate"] = {"RATE": "lin", "RATE_SQRT": "sqrt"}[choice["T"]]
if choice["M"]:
    cfg["miss"] = {"IMPUTE": "median", "RIMP": "rimp", "DROPGAP": "dropgap", "MIND": "mind"}[choice["M"]]
if choice["C"]:
    cfg["comp"] = True
if "FINAL" not in ARMS:
    (EV / "final_config.json").write_text(json.dumps({"stage1_choice": choice, "config": cfg, "note": "composed by the locked stage-1 rule on the held-out round; forward folds not read"}, indent=1))
pd.set_option("display.width", 250)
print(T.to_string(index=False))
print(P.to_string(index=False))
print("choice", choice, "config", cfg)
