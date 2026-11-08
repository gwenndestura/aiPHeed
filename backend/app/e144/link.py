"""
E144 Stage C: link between SWS area hunger and measured provincial HFIAS (E141 panel), and the end-to-end check at the
survey rounds (PROTOCOL.md s.3-4).

    logit(p) = alpha + gamma * logit(H_area) + delta * r_hat + e,   weights 1 / (se^2 + s^2)

H_area is the area's SWS hunger in the survey's reference quarter (Q3; the survey-year mean if Q3 has no round); r_hat
is E143 C4's out-of-fold relative logit. M0 drops gamma.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.stats import norm

from app.e140 import model as M140
from app.e141 import evaluate as E141
from app.e141 import panel as P
from app.e143 import OUT as O143
from app.e143 import model as M143
from app.e144 import data as D
from app.e144 import model as MA
from app.fi5.target import qindex

TAU = 0.428                                   # national HFIAS moderate-or-severe, pooled ENNS 2018/2019
LT = float(np.log(TAU / (1 - TAU)))
ROUND_ORDER = ["NNS2013", "FNRI2015", "ENNS2018", "ENNS2019"]
C4 = "C4 HRE-LGBM-X"


def _area_hunger(area: str, ref_q: str) -> float:
    s = D.sws_quarterly()
    s = s[s["area"] == area]
    v = s.loc[s["qi"] == qindex(ref_q), "hunger"]
    if len(v):
        return float(v.iloc[0])
    v = s.loc[s["quarter"].str.startswith(ref_q[:4]), "hunger"]
    return float(v.mean()) if len(v) else np.nan


@lru_cache(maxsize=None)
def rows() -> pd.DataFrame:
    X = P.data(1)
    X = X[X["sws_area"].isin(D.AREAS)].copy()
    X["H"] = [_area_hunger(a, q) for a, q in zip(X["sws_area"], X["ref_quarter"])]
    p = X["p"] / 100.0
    X["y_abs"] = np.log(p / (1 - p))
    X["se_abs"] = (X["se_p"] / 100.0) / (p * (1 - p))
    X["q_star"] = norm.cdf((X["y_abs"] - LT) / X["se_abs"])
    R = pd.read_csv(O143 / "oof_rolling.csv")[["key", "survey", f"{C4}::yhat", f"{C4}::V"]]
    R.columns = ["key", "survey", "r_hat", "r_var"]
    # 2013: C4 structural estimate (no earlier round), trained on the E140 rows (2015/2018/2019), as in E143
    tr = M140.data(lead=1).copy()
    tr["prev_survey"] = np.where(tr["prev_y"].notna(), "FNRI2015", None)
    te = X[X["survey"] == "NNS2013"]
    an = M143.Anchored("hre", "lgbm").fit(tr)
    yh, V = an.predict(te)
    R13 = pd.DataFrame({"key": te["key"].values, "survey": "NNS2013", "r_hat": yh, "r_var": V})
    X = X.merge(pd.concat([R, R13]), on=["key", "survey"], how="left")
    return X.dropna(subset=["H", "r_hat", "y_abs"]).reset_index(drop=True)


def design(X, use_h=True):
    cols = [np.ones(len(X)), X["r_hat"].values] + ([MA._logit(X["H"].values)] if use_h else [])
    return np.column_stack(cols)


def fit(X, use_h=True, iters=30):
    A, y, se2 = design(X, use_h), X["y_abs"].values, X["se_abs"].values ** 2
    s2 = 0.05
    for _ in range(iters):
        w = 1.0 / (se2 + s2)
        XtW = A.T * w
        cov = np.linalg.inv(XtW @ A)
        b = cov @ (XtW @ y)
        r = y - A @ b
        s2 = max(1e-3, float(np.mean(r ** 2 - se2)))
    return {"beta": b, "cov": cov, "s2": s2, "use_h": use_h,
            "names": ["alpha", "delta_r_hat"] + (["gamma_logit_H"] if use_h else [])}


def predict(m, X, h_logit=None, h_sd=None):
    """Mean and variance of logit(p): parameter, residual, r_hat and (optionally forecast) H uncertainty."""
    Xd = X.copy()
    if h_logit is not None:
        Xd["H"] = 100 / (1 + np.exp(-np.asarray(h_logit)))
    A = design(Xd, m["use_h"])
    mu = A @ m["beta"]
    var = np.einsum("ij,jk,ik->i", A, m["cov"], A) + m["s2"] + m["beta"][1] ** 2 * Xd["r_var"].fillna(0).values
    if m["use_h"] and h_sd is not None:
        var = var + m["beta"][2] ** 2 * np.asarray(h_sd) ** 2
    return mu, var


def eb(p, q):
    return float(np.mean((p - q) ** 2 + q * (1 - q)))


def link_tests(rng, n_boot=1000) -> dict:
    X = rows()
    full = {u: fit(X, u) for u in (True, False)}
    g = []
    for _ in range(n_boot):
        b = pd.concat([grp.sample(len(grp), replace=True, random_state=int(rng.integers(1 << 31))) for _, grp in X.groupby("survey")])
        g.append(fit(b, True)["beta"][2])
    loro = {}
    for r in ROUND_ORDER:
        tr, te = X[X["survey"] != r], X[X["survey"] == r]
        res = {}
        for u, name in ((True, "M1 (with area hunger)"), (False, "M0 (no time signal)")):
            m = fit(tr, u)
            mu, var = predict(m, te)
            w = 1.0 / (te["se_abs"] ** 2 + m["s2"])
            res[name] = {"wrmse_logit": float(np.sqrt(np.sum(w * (te["y_abs"] - mu) ** 2) / np.sum(w))),
                         "eb_above_tau": eb(norm.cdf((mu - LT) / np.sqrt(var)), te["q_star"].values),
                         "bias_logit": float(np.mean(te["y_abs"] - mu))}
        loro[r] = res
    agg = {k: float(np.mean([loro[r][k]["wrmse_logit"] for r in ROUND_ORDER])) for k in loro[ROUND_ORDER[0]]}
    return {"n": int(len(X)), "rounds": X["survey"].value_counts().to_dict(),
            "area_hunger_by_round": X.groupby(["survey", "sws_area"])["H"].first().round(2).astype(str).to_dict(),
            "M1": {k: v for k, v in zip(full[True]["names"], map(float, full[True]["beta"]))} | {"s2": full[True]["s2"]},
            "M0": {k: v for k, v in zip(full[False]["names"], map(float, full[False]["beta"]))} | {"s2": full[False]["s2"]},
            "gamma_ci95": [float(np.percentile(g, 2.5)), float(np.percentile(g, 97.5))],
            "loro": loro, "loro_mean_wrmse": agg}


def e2e(Xa: pd.DataFrame, rng, n_boot=2000) -> dict:
    """Rolling end-to-end check: for 2015, 2018, 2019, Stage A (level) issued one quarter before the reference quarter's
    viewing quarter (h = 1), link and C4 from earlier rounds only."""
    X = rows()
    out = []
    for oid, train_rounds, target in E141.ORIGINS:
        tr, te = X[X["survey"].isin(train_rounds)], X[X["survey"] == target].copy()
        T = qindex(te["ref_quarter"].iloc[0])
        i = T - 2                                                # issue at the end of quarter i, h = 1
        d = D.q_end(i)
        A = Xa[Xa["y"].notna() & (Xa["label_published"] <= d)]
        lv = MA.LGBLevel(MA.SETS["A LightGBM (full)"]).fit(A)
        q = Xa[(Xa["issue_qi"] == i) & (Xa["h"] == 1)].set_index("area")
        mh, sh = lv.predict(q)
        hmap, smap = dict(zip(q.index, mh)), dict(zip(q.index, sh))
        m1, m0 = fit(tr, True), fit(tr, False)
        mu1, v1 = predict(m1, te, te["sws_area"].map(hmap).values, te["sws_area"].map(smap).values)
        mu0, v0 = predict(m0, te)
        te["E2E"] = norm.cdf((mu1 - LT) / np.sqrt(v1))
        te["C4-only"] = norm.cdf((mu0 - LT) / np.sqrt(v0))
        prev = X.set_index(["key", "survey"])[["y_abs", "se_abs"]]
        pv = [prev.loc[(k, s)] if (k, s) in prev.index else pd.Series({"y_abs": np.nan, "se_abs": np.nan})
              for k, s in zip(te["key"], te["prev_survey"].fillna("NONE"))]
        pv = pd.DataFrame(pv).reset_index(drop=True)
        te["Persistence"] = norm.cdf((pv["y_abs"].values - LT) / np.sqrt(pv["se_abs"].values ** 2 + m0["s2"]))
        te["origin"] = oid
        out.append(te)
    R = pd.concat(out, ignore_index=True).dropna(subset=["Persistence"])
    names = ["E2E", "C4-only", "Persistence"]
    dec = (np.abs(R["y_abs"] - LT) > 1.645 * R["se_abs"]).values
    yt = (R["y_abs"] > LT).astype(int).values
    from sklearn.metrics import roc_auc_score
    res = {"n": int(len(R)), "n_decisive": int(dec.sum()), "n_above_tau_decisive": int(yt[dec].sum()), "models": {}}
    for n in names:
        p = R[n].values
        res["models"][n] = {"eb": eb(p, R["q_star"].values),
                            "auc_decisive": float(roc_auc_score(yt[dec], p[dec])) if len(set(yt[dec])) == 2 else None,
                            "accuracy_decisive": float(np.mean((p[dec] >= 0.5) == yt[dec]))}
    regs = R["region"].unique()
    idx = {r: np.flatnonzero(R["region"].values == r) for r in regs}
    q = R["q_star"].values
    diffs = {b: [] for b in ("C4-only", "Persistence")}
    for _ in range(n_boot):
        ii = np.concatenate([idx[r] for r in rng.choice(regs, len(regs))])
        for b in diffs:
            diffs[b].append(eb(R["E2E"].values[ii], q[ii]) - eb(R[b].values[ii], q[ii]))
    res["E2E_minus"] = {b: {"diff": res["models"]["E2E"]["eb"] - res["models"][b]["eb"],
                            "ci95": [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]} for b, v in diffs.items()}
    res["by_origin"] = {o: {n: eb(g[n].values, g["q_star"].values) for n in names} for o, g in R.groupby("origin")}
    res["calabarzon"] = R[R["province"].isin(E141.CAL)][["origin", "province", "survey", "p", "q_star"] + names].round(3).to_dict(orient="records")
    return res, R
