"""
E138 WHEN: does anything that varies over time explain the measured CHANGE in a province's relative food-insecurity
position between surveys? (PROTOCOL.md section 7.) The only within-province measured change available is
FNRI 2015 -> ENNS 2018/2019 (same instrument, same relative target).

    d_y      = y_ENNS - y_2015 (relative logit change), se = sqrt(se_ENNS^2 + se_2015^2)
    changes  = feature at the ENNS issue date minus the same feature at the 2015 issue date (Lead 0), plus cyclone
               count between the two dates and the 2015 relative position (regression to the mean)
Tests (frozen): (1) Spearman of d_y with each change, Holm-adjusted; (2) leave-one-region-out prediction of d_y by
weighted ridge on the time-varying changes, against zero change, mean change and mean reversion (d_y = -b * y_2015).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge

from app.e137 import features as F
from app.e138.where import data

TIME_VARYING = ["m_food_cpi_yoy", "m_rice_cpi_yoy", "m_food_threshold_rel", "c_rain_anom_6m", "c_agri_yoy", "c_fish_yoy",
                "p_poverty", "p_subsistence", "p_poverty_gap"]


def panel() -> pd.DataFrame:
    X = data()
    a = X[X["survey"] == "FNRI2015"].set_index("key")
    b = X[X["survey"] != "FNRI2015"].set_index("key")
    k = a.index.intersection(b.index)
    d = pd.DataFrame({"region": b.loc[k, "region"], "survey": b.loc[k, "survey"], "province": b.loc[k, "province"],
                      "y15": a.loc[k, "y"], "d_y": b.loc[k, "y"] - a.loc[k, "y"],
                      "se_d": np.sqrt(b.loc[k, "se_y"] ** 2 + a.loc[k, "se_y"] ** 2)})
    for f in TIME_VARYING:
        d[f"d_{f}"] = b.loc[k, f] - a.loc[k, f]
    tc = []
    for key in k:
        hits = F._storm_hits(key.replace(" ", ""))
        t0, t1 = pd.Timestamp(a.loc[key, "issue_date"]), pd.Timestamp(b.loc[key, "issue_date"])
        tc.append(float(((hits["t"] >= t0) & (hits["t"] < t1)).sum() / max((t1 - t0).days / 365.25, 1e-9)))
    d["tc_per_year_between"] = tc
    return d.reset_index()


def holm(p: list[float]) -> list[float]:
    order = np.argsort(p)
    m, adj, run = len(p), np.empty(len(p)), 0.0
    for i, j in enumerate(order):
        run = max(run, (m - i) * p[j])
        adj[j] = min(1.0, run)
    return adj.tolist()


def run() -> dict:
    d = panel()
    cols = [c for c in d.columns if c.startswith("d_") and c != "d_y"] + ["tc_per_year_between"]
    rows = []
    for c in cols + ["y15"]:
        s = d[["d_y", c]].dropna()
        r = spearmanr(s["d_y"], s[c])
        rows.append({"variable": c, "n": len(s), "spearman": float(r.statistic), "p": float(r.pvalue)})
    adj = holm([r["p"] for r in rows])
    for r, a in zip(rows, adj):
        r["p_holm"] = a
    w = 1.0 / (d["se_d"] ** 2 + max(0.01, d["d_y"].var() - (d["se_d"] ** 2).mean()))
    pred = {k: np.full(len(d), np.nan) for k in ("zero", "mean_change", "mean_reversion", "ridge_changes")}
    Xc = d[cols].fillna(d[cols].median())
    for reg in d["region"].unique():
        te, tr = d["region"] == reg, d["region"] != reg
        pred["zero"][te] = 0.0
        pred["mean_change"][te] = np.average(d.loc[tr, "d_y"], weights=w[tr])
        b = np.sum(w[tr] * d.loc[tr, "y15"] * d.loc[tr, "d_y"]) / np.sum(w[tr] * d.loc[tr, "y15"] ** 2)
        pred["mean_reversion"][te] = b * d.loc[te, "y15"]
        mu, sd = Xc[tr].mean(), Xc[tr].std(ddof=0).replace(0, 1)
        m = Ridge(alpha=3.0).fit((Xc[tr] - mu) / sd, d.loc[tr, "d_y"] - pred["mean_change"][te][0], sample_weight=w[tr])
        pred["ridge_changes"][te] = m.predict((Xc[te] - mu) / sd) + pred["mean_change"][te][0]
    mse = {k: float(np.average((d["d_y"] - v) ** 2, weights=w)) for k, v in pred.items()}
    sig = (np.abs(d["d_y"] / d["se_d"]) >= 1.96)
    return {"n": int(len(d)), "n_significant_changes": int(sig.sum()),
            "share_change_within_survey_error": float(1 - sig.mean()),
            "correlations": rows, "weighted_mse": mse,
            "skill_vs_zero": {k: 1 - v / mse["zero"] for k, v in mse.items()},
            "rows": d.assign(**{f"pred_{k}": v for k, v in pred.items()}).round(4).to_dict(orient="records")}
