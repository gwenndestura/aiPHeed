"""
E196 reliability checks on existing results only (no model is refitted; E196 is not changed). Local only.
  1. Selection-adjusted (winner's-curse) estimate: empirical-Bayes shrinkage of E196's pooled Lead 1-3 accuracy gain
     over E184 toward the mean gain of every variant evaluated on the same 72 rows (E168 ... E196).
  2. Region jackknife of the gain.  3. Bootstrap CIs for E196's metrics.  4. Calibration by probability bin.

    python -m app.e196.reliability
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

from app.e178 import common as K
from app.e191 import run as R

D = K.D
OUT = D / "e196" / "out"
KEYS = ["key", "survey", "lead"]
KS = ["key", "survey"]
B = 4000


def mean_p(path, **flt):
    d = pd.read_csv(path)
    for k, v in flt.items():
        d = d[d[k] == v]
    d = d[d["lead"] <= 3]
    return d.groupby(KEYS)["p"].mean()


def variants():
    V = {}
    e = [pd.read_csv(D / "e184" / "out" / f) for f in ("all_rows.csv", "lead3_rows.csv")]
    e = pd.concat(e)
    e = e[(e["mode"] == "main") & (e["lead"] <= 3)]
    V["E184"] = e[e["arm"] == "E184"].groupby(KEYS)["p"].mean()
    V["E168"] = e[e["arm"] == "E168_rerun"].groupby(KEYS)["p"].mean()
    for exp, arm, f in (("E182", "E182", "e182/out/all_rows.csv"), ("E185", "E185", "e185/out/all_rows.csv"), ("E186", "E186", "e186/out/all_rows.csv")):
        d = pd.read_csv(D / f)
        d = d[(d["arm"] == arm) & (d["mode"] == "main") & (d["lead"] <= 3)]
        if exp == "E182":
            d3 = pd.read_csv(D / "e182/out/lead3_rows.csv")
            d = pd.concat([d, d3[(d3["arm"] == "E182") & (d3["mode"] == "main")]])
        V[exp] = d.groupby(KEYS)["p"].mean()
    for a in ("E188a", "E188b"):
        V[a] = mean_p(D / "e188/out/rows.csv", arm=a)
    for a in ("E189", "E189_ridge", "E189_rf"):
        V[a] = mean_p(D / "e189/out/rows.csv", arm=a)
    for a in ("E190a", "E190b"):
        V[a] = mean_p(D / "e190/out/rows.csv", arm=a)
    ar = pd.read_csv(D / "e191/out/arm_rows.csv")
    ar = ar[ar["lead"] <= 3]
    for a in sorted(set(ar["arm"])):
        if a in ("E184", "E168"):
            continue
        V["E191:" + a] = ar[ar["arm"] == a].groupby(KEYS)["p"].mean()
    for a in ("traj", "E192", "E192_20"):
        V["E192:" + a] = mean_p(D / "e192/out/rows.csv", arm=a)
    V["E193"] = pd.read_csv(D / "e193/out/per_seed_rows.csv").query("lead <= 3").groupby(KEYS)["p"].mean()
    p194 = pd.read_csv(D / "e196/out/e194_rerun_rows.csv")
    V["E194"] = p194[p194["lead"] <= 3].groupby(KEYS)["p"].mean()
    W = p194.pivot_table(index=KS, columns="lead", values="p")
    def lagged(rule):
        out = []
        for L in (1, 2, 3):
            s = W[rule(L)].mean(axis=1).rename("p").reset_index()
            s["lead"] = L
            out.append(s)
        return pd.concat(out).set_index(KEYS)["p"]
    V["E195"] = lagged(lambda L: [L, L + 1, L + 2])
    V["E196"] = lagged(lambda L: [1, 2] if L == 1 else [L])
    return V


def main():
    G = pd.read_csv(D / "e158/out/oof.csv")
    G = G[G["lead"] <= 3].set_index(KEYS)
    V = variants()
    X = G[["region", "y_high", "q_true"]].copy()
    for k, v in V.items():
        X[k] = v
    X = X.dropna(axis=1)
    names = [c for c in V if c in X]
    y = X["y_high"].astype(bool).values
    ok = {k: ((X[k].values >= .5) == y).astype(float) for k in names}
    regs = X["region"].values
    ureg = np.unique(regs)
    rng = np.random.default_rng(196)
    idx = [np.flatnonzero(regs == r) for r in ureg]
    draws = [np.concatenate([idx[i] for i in rng.integers(0, len(ureg), len(ureg))]) for _ in range(B)]
    # 1. paired gains over E184 (pooled Leads 1-3) and their bootstrap SEs
    g, se = {}, {}
    for k in names:
        if k == "E184":
            continue
        d = ok[k] - ok["E184"]
        g[k] = float(d.mean())
        se[k] = float(np.std([d[b].mean() for b in draws]))
    gv = np.array(list(g.values()))
    sev = np.array(list(se.values()))
    m = float(gv.mean())
    tau2 = max(0.0, float(gv.var(ddof=1)) - float(np.mean(sev ** 2)))
    Bk = tau2 / (tau2 + se["E196"] ** 2) if tau2 > 0 else 0.0
    adj = m + Bk * (g["E196"] - m)
    base = float(ok["E184"].mean())
    shrink = {"n_variants": len(g), "mean_gain_all_variants_pts": round(100 * m, 2), "between_variant_sd_pts": round(100 * np.sqrt(tau2), 2),
              "E196_observed_gain_pts": round(100 * g["E196"], 2), "E196_gain_se_pts": round(100 * se["E196"], 2), "shrinkage_weight": round(Bk, 3),
              "E196_selection_adjusted_gain_pts": round(100 * adj, 2), "E184_pooled_accuracy": round(100 * base, 2),
              "E196_observed_pooled_accuracy": round(100 * float(ok["E196"].mean()), 2),
              "E196_selection_adjusted_pooled_accuracy": round(100 * (base + adj), 2),
              "rank_of_E196_among_variants": int(1 + sum(v > g["E196"] for v in gv))}
    # 2. region jackknife
    d = ok["E196"] - ok["E184"]
    jack = {r: round(100 * float(d[regs != r].mean()), 2) for r in ureg}
    # 3. bootstrap CIs, E196 per lead
    lead = X.index.get_level_values("lead").values
    q = X["q_true"].values
    ci = {}
    for L in (1, 2, 3):
        s = lead == L
        p = X["E196"].values
        def stat(ix):
            ix = ix[s[ix]]
            pr, yy = p[ix] >= .5, y[ix]
            tp, fp, fn, tn = (pr & yy).sum(), (pr & ~yy).sum(), (~pr & yy).sum(), (~pr & ~yy).sum()
            return [(tp + tn) / len(ix), tp / max(1, tp + fn), tn / max(1, tn + fp), np.mean((p[ix] - q[ix]) ** 2)]
        st = np.array([stat(b) for b in draws])
        pt = stat(np.arange(len(y)))
        ci[L] = {nm: [round(float(pt[j]), 4), [round(float(np.percentile(st[:, j], 2.5)), 4), round(float(np.percentile(st[:, j], 97.5)), 4)]]
                 for j, nm in enumerate(("accuracy", "recall", "specificity", "brier"))}
        ci[L]["roc_auc"] = round(float(roc_auc_score(y[s], p[s])), 3)
    # 4. calibration by bin, pooled Leads 1-3
    cal = {}
    for a in ("E184", "E196"):
        b = pd.cut(X[a], [0, .2, .4, .5, .6, .8, 1.0], include_lowest=True)
        cal[a] = X.groupby(b, observed=True).agg(n=(a, "size"), mean_p=(a, "mean"), observed_high=("y_high", "mean")).round(3).reset_index().astype(str).to_dict("records")
    res = {"variants_used": names, "selection_adjustment": shrink, "region_jackknife_gain_pts": jack,
           "region_jackknife_min_max": [min(jack.values()), max(jack.values())], "bootstrap_ci_E196": ci, "calibration": cal}
    K.dump_json(res, OUT / "reliability.json")
    print(json.dumps(shrink, indent=1))
    print("region jackknife gain (pts) min/max:", res["region_jackknife_min_max"], "regions:", len(jack))
    for L, c in ci.items():
        print(f"L{L}", c)
    for a, rows in cal.items():
        print(a, [(r["mean_p"], r["observed_high"], r["n"]) for r in rows])


if __name__ == "__main__":
    main()
