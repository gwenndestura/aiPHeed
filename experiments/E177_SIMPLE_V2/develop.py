"""
E177: SIMPLE v2 training-only development on the only untainted labelled rows (FNRI 2015 targets, NNS 2013 anchors; 156 rows used
to train the ENNS 2018/2019 forecasts). The 72 evaluation outcomes are never read: the script asserts that no training row shares
a (province, survey) outcome with them and never touches the forecast targets' labels.

    cd backend && PYTHONPATH=. python ../experiments/E177_SIMPLE_V2/develop.py
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold

from app.e144 import data as SWSD
from app.e147 import features as Fe
from app.e148 import model as M8
from app.e150 import evaluate as Ev
from app.e150 import model as M
from app.e151 import prov as Pv
from app.e154 import model as E154
from app.e164 import auto as U
from app.e171 import candidates as C171
from app.e172 import lgbm_only as E
from app.paths import BACKEND_DIR

HERE = Path(__file__).resolve().parent
LEAD = 2
SEEDS = (151, 152, 153, 154, 155)


def training_rows():
    E._install()
    Fe.LT = 0.0
    M.Hier, M.Store = Pv.Hier2, Pv.Store2
    C171.LEAD_NOW["v"] = LEAD
    S = Pv.Store2(None)
    i = M8.RQ["ENNS2018"] - LEAD
    P = M.Pipeline(S, i, Pv.ROUNDS, Pv.ORIGIN["ENNS2018"])
    sw = SWSD.sws_quarterly()
    H = E154.income()
    tr = C171.add_sws(E154.add_income(Pv.add_inputs(S, P.tr), H), sw).reset_index(drop=True)
    tg = M8.targets(S.s8, ["ENNS2018"]).drop(columns=["y", "se_y", "q_high", "p"], errors="ignore")   # target labels dropped
    te = C171.add_sws(E154.add_income(Pv.add_inputs(S, M.rows_for(S, tg, [LEAD], Pv.ORIGIN["ENNS2018"])), H), sw).reset_index(drop=True)
    ev = set(zip(*pd.read_csv(BACKEND_DIR / "data" / "e168" / "out" / "oof.csv")[["key", "survey"]].values.T))
    assert set(tr["survey"]) == {"FNRI2015"} and not any((k, s) in ev for k, s in zip(tr["key"], tr["survey"])), "tainted training rows"
    AN = U.anchors(S, P, tr, te)                       # test rows only feed the anchor API; their outputs and labels are not used
    return tr, AN


def select(tr, AN):
    """SIMPLE's own rule (E173), training-only: anchor from E168's stage 1, learner from the SIMPLE menu."""
    _, _, r1 = E.score(tr, AN, E.STAGE1)
    anchor = min(E.STAGE1, key=lambda c: r1[c]["sse"])[0]
    menu = [c for c in E.stage2(anchor) if E.SUBSETS["SIMPLE"](c)]
    _, _, r2 = E.score(tr, AN, menu)
    return anchor, min(menu, key=lambda c: r2[c]["sse"]), r1, r2


def oof_scores(tr, AN, cfg, folds, seed=151):
    a, l, f = cfg
    atr = AN[a][0]
    y = tr["y_true"].values
    cls = U.LEARNERS[l]
    old = cls.SEEDS
    cls.SEEDS = (seed,)
    try:
        mu = np.full(len(tr), np.nan)
        for i_tr, i_te in folds:
            mu[i_te] = atr[i_te] + cls(U.FS[f]).fit(tr.iloc[i_tr].assign(e=y[i_tr] - atr[i_tr])).predict(tr.iloc[i_te])
    finally:
        cls.SEEDS = old
    return mu


def probs(tr, mu, folds, mode):
    """P(HIGH) for each held-out fold using only the other folds' out-of-fold scores (cross-fitted sd / Platt / temperature)."""
    y, yh = tr["y_true"].values, (tr["y_true"].values >= 0).astype(int)
    q = tr["q_true"].values if "q_true" in tr else norm.cdf(tr["y_true"] / tr["se_true"])
    p = np.zeros(len(tr))
    lam_used = []
    for _, i_te in folds:
        o = np.setdiff1d(np.arange(len(tr)), i_te)
        sd = float(np.sqrt(np.mean((y[o] - mu[o]) ** 2)))
        if mode == "raw":
            p[i_te] = norm.cdf(mu[i_te] / sd)
        elif mode == "platt":
            m = LogisticRegression(C=1e6).fit(mu[o].reshape(-1, 1), yh[o])
            p[i_te] = m.predict_proba(mu[i_te].reshape(-1, 1))[:, 1]
        elif mode == "temp":
            grid = np.round(np.arange(0.3, 1.51, 0.05), 2)
            lam = grid[int(np.argmin([np.mean((norm.cdf(g * mu[o] / sd) - q[o]) ** 2) for g in grid]))]
            lam_used.append(float(lam))
            p[i_te] = norm.cdf(lam * mu[i_te] / sd)
    return p, q, yh, lam_used


def metrics(p, q, yh, mu=None):
    lp = np.log(np.clip(p, 1e-6, 1 - 1e-6) / np.clip(1 - p, 1e-6, 1))
    lr = LogisticRegression(C=1e6).fit(lp.reshape(-1, 1), yh)
    return {"rows": int(len(p)), "accuracy": round(float(((p >= .5) == (yh == 1)).mean()), 4), "brier_vs_q": round(float(np.mean((p - q) ** 2)), 4),
            "roc_auc": round(float(roc_auc_score(yh, p)), 4), "mean_p": round(float(p.mean()), 4), "mean_q": round(float(q.mean()), 4),
            "calibration_slope_logit": round(float(lr.coef_[0][0]), 3), "calibration_intercept_logit": round(float(lr.intercept_[0]), 3),
            "mean_abs_dist_0.5": round(float(np.abs(p - .5).mean()), 4)}


def main():
    tr, AN = training_rows()
    anchor, cfg, r1, r2 = select(tr, AN)
    folds = list(GroupKFold(min(5, tr["region"].nunique())).split(tr, groups=tr["region"]))
    ref = (anchor, "GR0P", "FULL")
    stumps = (anchor, "GR1P", cfg[2])
    mu0, mur, mus = oof_scores(tr, AN, cfg, folds), oof_scores(tr, AN, ref, folds), oof_scores(tr, AN, stumps, folds)
    rows, cal = [], []
    for name, mu, mode in (("C0_SIMPLE", mu0, "raw"), ("C1_PLATT", mu0, "platt"), ("C2_TEMPERATURE", mu0, "temp"), ("C3_STUMPS", mus, "raw"),
                           ("REF_E168CFG", mur, "raw")):
        p, q, yh, lam = probs(tr, mu, folds, mode)
        m = metrics(p, q, yh)
        rows.append({"candidate": name, "config": "|".join(stumps if name == "C3_STUMPS" else ref if name.startswith("REF") else cfg),
                     "population": "156 FNRI2015 training rows (untainted), region-fold cross-fitted", **m,
                     "temperature_by_fold": json.dumps(lam) if lam else ""})
        for f_i, (_, i_te) in enumerate(folds):
            cal.append({"candidate": name, "fold": f_i, "rows": len(i_te), "mean_p": round(float(p[i_te].mean()), 4), "mean_q": round(float(q[i_te].mean()), 4),
                        "brier": round(float(np.mean((p[i_te] - q[i_te]) ** 2)), 4)})
    V = pd.DataFrame(rows)
    base = V.set_index("candidate").loc["C0_SIMPLE"]
    elig = V[V["candidate"].isin(["C0_SIMPLE", "C1_PLATT", "C2_TEMPERATURE", "C3_STUMPS"]) & (V["accuracy"] >= base["accuracy"])]
    order = {"C0_SIMPLE": 0, "C2_TEMPERATURE": 1, "C1_PLATT": 2, "C3_STUMPS": 3}
    win = elig.assign(o=elig["candidate"].map(order)).sort_values(["brier_vs_q", "o"]).iloc[0]["candidate"]
    V["selected_by_registered_rule"] = V["candidate"] == win
    V.to_csv(HERE / "training_only_validation.csv", index=False, lineterminator="\n")
    pd.DataFrame(cal).to_csv(HERE / "calibration_analysis.csv", index=False, lineterminator="\n")
    # stability: seed variation of the C0 out-of-fold scores, and class flips across seeds
    S = np.column_stack([oof_scores(tr, AN, cfg, folds, s) for s in SEEDS])
    R = np.column_stack([oof_scores(tr, AN, ref, folds, s) for s in SEEDS])
    st = []
    for name, X in (("C0_SIMPLE", S), ("REF_E168CFG", R)):
        cls = X >= 0
        st.append({"candidate": name, "seeds": len(SEEDS), "mean_sd_of_score_across_seeds": round(float(X.std(axis=1).mean()), 4),
                   "max_sd_of_score_across_seeds": round(float(X.std(axis=1).max()), 4),
                   "rows_whose_class_changes_across_seeds": int((cls.any(axis=1) & ~cls.all(axis=1)).sum()), "rows": len(tr)})
    for k, v in sorted(r2.items(), key=lambda kv: kv[1]["sse"])[:5]:
        st.append({"candidate": "SIMPLE menu (top-5 training score)", "seeds": "", "mean_sd_of_score_across_seeds": "", "max_sd_of_score_across_seeds": "",
                   "rows_whose_class_changes_across_seeds": "", "rows": "", "config": "|".join(k), "training_sse": round(v["sse"], 3)})
    pd.DataFrame(st).to_csv(HERE / "model_stability.csv", index=False, lineterminator="\n")
    print("anchor", anchor, "SIMPLE choice", cfg)
    print(V.drop(columns=["population"]).to_string(index=False))
    print(pd.DataFrame(st).head(2).to_string(index=False))


if __name__ == "__main__":
    main()
