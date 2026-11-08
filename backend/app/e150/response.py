"""
Quarterly response function learned on SWS area-quarters, the only outcome measured every quarter, then applied to each province's own inputs.

SWS is regional and a different construct, so it is never a provincial label. It supplies a *direction and rough size of response* to quarterly inputs; whether that signal
relates to HFIAS is decided on measured survey rows, by a separately estimated loading.

    python -m app.e150.response build -> data/e150/out/{h_signal.parquet, response_check.json}
"""
from __future__ import annotations

import json
import sys
import warnings

import lightgbm as lgb
import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy.stats import spearmanr

from app.e144 import data as D
from app.e147 import features as Fe
from app.e148 import OUT as O148
from app.e148 import panel as Pn
from app.e150 import OUT
from app.fi5.target import qindex

warnings.filterwarnings("ignore")
INPUTS = ["cpi_food_yoy", "cpi_rice_yoy", "cpi_food_accel", "c_soil_anom_3m", "c_rain_anom_6m", "c_tc_4q", "c_agri_yoy", "c_fish_yoy", "oni", "unemp_rate", "unemp_yoy", "remit_yoy"]
STATE = ["sws_last", "sws_anom", "lead"]
PARAMS = dict(objective="regression", n_estimators=200, learning_rate=0.03, num_leaves=7, max_depth=3, min_child_samples=20, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, random_state=150, n_jobs=1, verbose=-1)
LEADS = list(range(1, 9))
AREAS = ["balance_luzon", "visayas", "mindanao"]
FIRST_ISSUE = qindex("2015-Q1")


def province_inputs() -> pd.DataFrame:
    g = pd.read_parquet(O148 / "gov_panel.parquet")
    c = pd.read_parquet(OUT / "cpi_panel.parquet")
    P = g.merge(c, on=["key", "qi"], how="left")
    b = Fe.base_rows().drop_duplicates("key").set_index("key")
    P["sws_area"] = P["key"].map(b["sws_area"])
    return P


def sws_state(area: str, i: int) -> dict:
    s = D.sws_quarterly()
    s = s[(s["area"] == area) & (s["published"] < Pn.q_start(i))].sort_values("qi")
    if s.empty:
        return {"sws_last": np.nan, "sws_anom": np.nan}
    h = Fe._logit(s["hunger"].values)
    return {"sws_last": float(h[-1]), "sws_anom": float(h[-1] - np.mean(h[-9:-1])) if len(h) >= 3 else np.nan}


def area_rows(P: pd.DataFrame) -> pd.DataFrame:
    a = P[P["sws_area"].isin(AREAS)].groupby(["sws_area", "qi"])[INPUTS].mean().reset_index()
    s = D.sws_quarterly()
    rows = []
    for _, r in a.iterrows():
        st = sws_state(r["sws_area"], int(r["qi"]))
        for h in LEADS:
            t = s[(s["area"] == r["sws_area"]) & (s["qi"] == int(r["qi"]) + h)]
            row = {**r.to_dict(), **st, "lead": h, "T": int(r["qi"]) + h}
            if len(t):
                row["dy"] = float(Fe._logit(t["hunger"].iloc[0])) - st["sws_last"] if st["sws_last"] == st["sws_last"] else np.nan
                row["published"] = t["published"].iloc[0]
            rows.append(row)
    return pd.DataFrame(rows)


def _fit(A, cols, i, exclude=None):
    t = A[A["dy"].notna() & (A["published"] < Pn.q_start(i))]
    if exclude:
        t = t[t["sws_area"] != exclude]
    if len(t) < 60:
        return None
    return lgb.LGBMRegressor(**PARAMS).fit(t[cols], t["dy"])


def _issue(i, A, P):
    """As of issue i: province signal for every lead; and held-out-area predictions for the independent check."""
    m = _fit(A, INPUTS + STATE, i)
    ar = _fit(A, STATE, i)
    out, chk = [], []
    if m is None:
        return out, chk
    x = P[(P["qi"] == i) & P["sws_area"].isin(AREAS)].copy()
    states = {a: sws_state(a, i) for a in AREAS}
    for c in ("sws_last", "sws_anom"):
        x[c] = x["sws_area"].map(lambda a: states[a][c])
    for h in LEADS:
        x["lead"] = h
        out.append(pd.DataFrame({"key": x["key"].values, "i": i, "lead": h, "h_full": m.predict(x[INPUTS + STATE]), "h_ar": ar.predict(x[STATE])}))
    for area in AREAS:
        m0, a0 = _fit(A, INPUTS + STATE, i, area), _fit(A, STATE, i, area)
        if m0 is None:
            continue
        q = A[(A["sws_area"] == area) & (A["qi"] == i) & A["dy"].notna()]
        if len(q):
            chk.append(pd.DataFrame({"area": area, "i": i, "lead": q["lead"].values, "actual": q["dy"].values, "pred_full": m0.predict(q[INPUTS + STATE]), "pred_ar": a0.predict(q[STATE])}))
    return out, chk


def build():
    P = province_inputs()
    A = area_rows(P)
    res = Parallel(n_jobs=16)(delayed(_issue)(i, A, P) for i in range(FIRST_ISSUE, Pn.LAST + 1))
    H = pd.concat([d for o, _ in res for d in o], ignore_index=True)
    H["h_signal"] = H["h_full"] - H["h_ar"]                 # response to quarterly inputs, beyond SWS mean reversion
    H.to_parquet(OUT / "h_signal.parquet", index=False)
    C = pd.concat([d for _, c in res for d in c], ignore_index=True)
    C.to_csv(OUT / "response_heldout_area.csv", index=False, lineterminator="\n")
    rng = np.random.default_rng(150)
    out = {"training_area_quarters": int(A[A["lead"] == 1]["dy"].notna().sum()), "by_lead": {}}
    for h, g in C.groupby("lead"):
        qs = g["i"].unique()
        by = {q: g[g["i"] == q] for q in qs}
        d_full, d_ar = [], []
        for _ in range(2000):
            x = pd.concat([by[q] for q in rng.choice(qs, len(qs))])
            d_full.append(spearmanr(x["pred_full"], x["actual"]).statistic)
            d_ar.append(np.mean((x["pred_full"] - x["actual"]) ** 2) - np.mean((x["pred_ar"] - x["actual"]) ** 2))
        out["by_lead"][f"L{h}"] = {"n": int(len(g)), "rho_full": float(spearmanr(g["pred_full"], g["actual"]).statistic), "rho_full_ci95": [float(np.nanpercentile(d_full, 2.5)), float(np.nanpercentile(d_full, 97.5))],
                                   "rho_ar": float(spearmanr(g["pred_ar"], g["actual"]).statistic), "mae_full": float(np.abs(g["pred_full"] - g["actual"]).mean()), "mae_ar": float(np.abs(g["pred_ar"] - g["actual"]).mean()), "mae_no_change": float(g["actual"].abs().mean()),
                                   "mse_full_minus_ar": float(np.mean((g["pred_full"] - g["actual"]) ** 2) - np.mean((g["pred_ar"] - g["actual"]) ** 2)), "mse_diff_ci95": [float(np.percentile(d_ar, 2.5)), float(np.percentile(d_ar, 97.5))],
                                   "corr_signal_vs_actual_beyond_ar": float(spearmanr(g["pred_full"] - g["pred_ar"], g["actual"] - g["pred_ar"]).statistic)}
    l1 = H[H["lead"] == 1].sort_values(["key", "i"])
    l1["d"] = l1.groupby("key")["h_signal"].diff()
    out["province_signal"] = {"sd_logit": float(l1["h_signal"].std()), "mean_abs_quarter_change_logit": float(l1["d"].abs().mean()), "between_province_sd_within_issue": float(l1.groupby("i")["h_signal"].std().mean())}
    (OUT / "response_check.json").write_text(json.dumps(out, indent=1, default=float), newline="\n")
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    {"build": build}[sys.argv[1]]()
