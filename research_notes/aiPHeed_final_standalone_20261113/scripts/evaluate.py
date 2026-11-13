r"""PROTOCOL_SA scorer (sha 15202d27). Scores one configuration's stored seed-level forward runs against the standalone rules
3-6 and the stability parts of Rule 7 (7b-7d). Reads labels; never refits. Run:
  python -I evaluate.py FINAL  <parts_dir>  [--thr]   (--thr: class HIGH when the seed-mean probability >= the seed-mean
  training-chosen threshold, PROTOCOL_SA Part B; otherwise the 0.50 cut-off)
Writes evidence/E_<ARM>_*.csv|json and a reliability diagram PNG."""
import glob
import json
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import chi2
from sklearn.metrics import roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parent))
from calib import _irls, ece, intercept, logit, slope   # noqa: E402

ARM, PARTS = sys.argv[1], Path(sys.argv[2])
THR = len(sys.argv) > 3 and sys.argv[3] == "--thr"
TAG = ARM + ("_thr" if THR else "")
HERE = Path(__file__).resolve().parents[1]
EV = HERE / "evidence"
CACHE = HERE.parent / "aiPHeed_objective_completion_20261111" / "cache"
LAB = pd.read_csv("C:/Users/admin/aipheed_e145/backend/data/e158/out/oof.csv")
K = ["key", "survey", "lead"]
SEEDS = (168, 1, 2, 3, 4)
rng = np.random.default_rng(7)

S = pd.concat([pd.read_csv(f) for f in glob.glob(str(PARTS / f"{ARM}__*.csv"))])
S = S[S.seed.isin(SEEDS) & S.lead.isin([1, 2, 3])]
if "variant" in S:
    S = S[S.variant == "none"]                      # perturbed copies (Rule 7e) are scored separately
if THR:
    assert "thr" in S, "no training-chosen threshold stored for this arm"
    S["cut"] = S["thr"]
else:
    S["cut"] = 0.5
assert S.groupby(["survey", "lead", "seed"]).ngroups == 45, "expected 3 rounds x 3 leads x 5 seeds"
lab = LAB[LAB.lead.isin([1, 2, 3])][K + ["province", "region", "island", "y_high", "q_true", "y_true", "y_anchor", "gap_q"]]
M = S.groupby(K, as_index=False)[["p", "cut"]].mean().merge(lab, on=K, how="inner")
assert len(M) == 216 and M.groupby("lead").size().eq(72).all()
# training HIGH rate per fold (the climatology forecast available at origin) for the Brier skill score
base = {}
for sv in ("ENNS2018", "ENNS2019", "ENNS2021"):
    for L in (1, 2, 3):
        tr = pickle.load(open(CACHE / f"{sv}_{L}.pkl", "rb"))["tr"]
        base[(sv, L)] = float((tr["y_true"] >= 0).mean())
M["p_clim"] = [base[(s, l)] for s, l in zip(M.survey, M.lead)]


def core(g):
    p, y, q = g.p.values, g.y_high.values.astype(int), g.q_true.values
    h = p >= g.cut.values
    tp, fp, fn, tn = int((h & (y == 1)).sum()), int((h & (y == 0)).sum()), int((~h & (y == 1)).sum()), int((~h & (y == 0)).sum())
    rec, spec = tp / max(1, tp + fn), tn / max(1, tn + fp)
    prec = tp / max(1, tp + fp)
    out = dict(n=len(g), accuracy=(tp + tn) / len(g), balanced_accuracy=0.5 * (rec + spec), recall_high=rec, recall_low=spec, precision=prec,
               f1=2 * prec * rec / max(1e-9, prec + rec), TP=tp, FP=fp, FN=fn, TN=tn,
               auroc=roc_auc_score(y, p) if 0 < y.sum() < len(y) else np.nan, brier=float(np.mean((p - y) ** 2)), brier_q=float(np.mean((p - q) ** 2)),
               brier_clim=float(np.mean((g.p_clim.values - y) ** 2)))
    out["bss_vs_training_rate"] = 1 - out["brier"] / out["brier_clim"]
    out["ece10"], out["mean_p_minus_rate"] = ece(p, y), float(p.mean() - y.mean())
    out["cal_slope"], out["cal_intercept_logit"] = slope(p, y), intercept(p, y)
    lp = logit(p)
    b = _irls(np.column_stack([np.ones(len(y)), lp]), y.astype(float))
    m1 = 1 / (1 + np.exp(-(b[0] + b[1] * lp)))
    pc = np.clip(p, 1e-6, 1 - 1e-6)
    ll1 = float(np.sum(y * np.log(m1) + (1 - y) * np.log(1 - m1)))
    ll0 = float(np.sum(y * np.log(pc) + (1 - y) * np.log(1 - pc)))
    out["cox_lr"], out["cox_p"] = 2 * (ll1 - ll0), float(chi2.sf(2 * (ll1 - ll0), 2))
    return out


def ci(g, keys=("balanced_accuracy", "auroc", "accuracy", "precision", "recall_high", "recall_low", "f1", "brier", "bss_vs_training_rate",
                "ece10", "mean_p_minus_rate", "cal_slope", "cal_intercept_logit")):
    cl = (g.key + g.survey).values
    u = np.unique(cl)
    idx = {c: np.flatnonzero(cl == c) for c in u}
    B = []
    for _ in range(6000 if g.lead.nunique() == 1 else 3000):
        x = g.iloc[np.concatenate([idx[c] for c in rng.choice(u, len(u))])]
        if 0 < x.y_high.sum() < len(x):
            r = core(x)
            B.append([r[k] for k in keys])
    B = np.array(B, float)
    return {k: [round(float(np.nanpercentile(B[:, j], 2.5)), 3), round(float(np.nanpercentile(B[:, j], 97.5)), 3)] for j, k in enumerate(keys)}


def ece_null(p, n=5000):
    sim = [ece(p, rng.binomial(1, p)) for _ in range(n)]
    return float(np.percentile(sim, 95))


R = {"arm": TAG, "class_rule": "p >= seed-mean training threshold" if THR else "p >= 0.50", "protocol_sha256": "15202d27800c3eb1e7efea5abe33a8dcf7ac67d6b9170eeb3c8080839ba957eb", "evidence_class": "retrospective, reused 72 rows"}
rows = []
for L, g in M.groupby("lead"):
    r = core(g)
    r["ece10_null_p95"] = ece_null(g.p.values)
    R[f"lead{L}"] = {**{k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()}, "ci95": ci(g)}
    rows.append({"lead": L, **r})
pd.DataFrame(rows).round(4).to_csv(EV / f"E_{TAG}_metrics_by_lead.csv", index=False)
R["pooled_leads_1_3"] = {k: (round(v, 4) if isinstance(v, float) else v) for k, v in core(M).items()}
R["pooled_leads_1_3"]["ci95"] = ci(M)

L1 = M[M.lead == 1].copy()
R["by_round_L1"] = {sv: {k: round(v, 3) if isinstance(v, float) else v for k, v in core(g).items() if k in ("n", "balanced_accuracy", "recall_high", "recall_low", "precision", "auroc", "TP", "FP", "FN", "TN", "brier")}
                    for sv, g in L1.groupby("survey")}
R["recall_by_lead"] = {int(L): f"{int(((g.p >= g.cut) & (g.y_high == 1)).sum())}/{int(g.y_high.sum())}" for L, g in M.groupby("lead")}
R["missed_high_L1"] = L1[(L1.y_high == 1) & (L1.p < L1.cut)][["province", "survey", "p", "cut", "q_true"]].round(3).to_dict("records")
R["false_alarms_L1"] = L1[(L1.y_high == 0) & (L1.p >= L1.cut)][["province", "survey", "p", "cut", "q_true"]].round(3).to_dict("records")
R["confident_wrong_L1"] = L1[((L1.p >= L1.cut) != (L1.y_high == 1)) & ((L1.p - .5).abs() >= .2)][["province", "survey", "y_high", "p"]].round(3).to_dict("records")
R["threshold_by_round_L1"] = L1.groupby("survey")["cut"].agg(["min", "mean", "max"]).round(3).to_dict("index")
R["expected_label_errors_L1"] = round(float(np.minimum(L1.q_true, 1 - L1.q_true).sum()), 2)     # survey noise: expected wrongly-classed labels
R["leave_one_round_out_L1"] = {f"without {sv}": {k: round(v, 3) for k, v in core(L1[L1.survey != sv]).items() if k in ("balanced_accuracy", "auroc", "recall_high", "precision")}
                               for sv in sorted(L1.survey.unique())}
# 7b worst seed (Lead 1)
ws = []
for sd, g in S[S.lead == 1].groupby("seed"):
    x = g.drop(columns=[c for c in ("province",) if c in g]).merge(lab, on=K).assign(p_clim=0.5)
    ws.append({"seed": int(sd), **{k: round(v, 3) for k, v in core(x).items() if k in ("balanced_accuracy", "recall_high", "precision", "auroc")}})
R["seeds_L1"] = ws
R["worst_seed_balanced_accuracy_L1"] = min(w["balanced_accuracy"] for w in ws)
# per-province table (all leads)
P = M.assign(ok=(M.p >= .5) == (M.y_high == 1)).pivot_table(index=["province", "survey", "region", "y_high"], columns="lead", values="p").reset_index()
P.columns = [str(c) if not isinstance(c, str) else c for c in P.columns]
P.round(3).to_csv(EV / f"E_{TAG}_province_rows.csv", index=False)
# reliability diagram data (Lead 1, 10 bins) + figure
bn = np.minimum((L1.p.values * 10).astype(int), 9)
rel = pd.DataFrame({"bin": bn, "p": L1.p.values, "y": L1.y_high.values, "q": L1.q_true.values}).groupby("bin").agg(n=("p", "size"), mean_p=("p", "mean"), observed=("y", "mean"), mean_q=("q", "mean")).reset_index()
rel.round(3).to_csv(EV / f"E_{TAG}_reliability_L1.csv", index=False)
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(4.2, 4.2), dpi=150)
    ax.plot([0, 1], [0, 1], color="#888", lw=1, ls="--", label="perfect")
    ax.scatter(rel.mean_p, rel.observed, s=rel.n * 12, color="#2b6cb0", alpha=.8, label="observed HIGH share (size = n)")
    ax.set_xlabel("forecast probability of HIGH (Lead 1)")
    ax.set_ylabel("observed share HIGH")
    ax.set_title(f"{TAG}: reliability, 72 province-rounds", fontsize=9)
    ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    fig.savefig(EV / f"E_{TAG}_reliability_L1.png")
except Exception as e:                       # the figure is a convenience; the table above is the evidence
    R["figure_error"] = str(e)
json.dump(R, open(EV / f"E_{TAG}_summary.json", "w"), indent=1, default=float)
l1 = R["lead1"]
print(json.dumps({k: l1[k] for k in ("balanced_accuracy", "auroc", "accuracy", "precision", "recall_high", "f1", "TP", "FP", "FN", "TN", "brier",
                                      "bss_vs_training_rate", "ece10", "ece10_null_p95", "mean_p_minus_rate", "cal_slope", "cal_intercept_logit", "cox_p")}, indent=0))
print("CI", json.dumps(l1["ci95"]))
print("rounds", json.dumps(R["by_round_L1"]))
print("recall by lead", R["recall_by_lead"], "worst seed BA", R["worst_seed_balanced_accuracy_L1"])
print("LORO", json.dumps(R["leave_one_round_out_L1"]))
print("expected label errors", R["expected_label_errors_L1"])
