"""Issue-time covariates for Y3 (EXPERIMENT_PLAN_PHASE2.md section 3). feats(t) returns what was published before
O(t) = first day of quarter t+1. Read-only on FINAL_FOOD_INSECURITY_LIGHTGBM/data/long."""
from __future__ import annotations

import functools

import numpy as np
import pandas as pd

import p2lib as P

R = P.R
LONG = R.LONG
FEATS = ["rice_yoy", "rice_d3", "food_yoy", "oni_last", "oni_max6", "tc_prev", "palay_yoy", "unemp_chg"]
MONTHS = {m: i for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                      "September", "October", "November", "December"])}


@functools.lru_cache(maxsize=1)
def _cpi() -> pd.DataFrame:
    c = pd.read_csv(LONG / "cov_cpi.csv")
    c = c[c["geolocation"] == "PHILIPPINES"]
    k = {"01.1.1.12 - Rice": "rice", "01.1 - FOOD": "food"}
    c = c[c["commodity_description"].isin(k)]
    return c.assign(c=c["commodity_description"].map(k)).pivot_table(index="ym", columns="c", values="yoy")


@functools.lru_cache(maxsize=1)
def _oni() -> pd.Series:
    o = pd.read_csv(LONG / "cov_oni.csv")
    return pd.Series(o["oni"].to_numpy(float), index=(o["end_year"] * 12 + o["end_month"] - 1).to_numpy())


@functools.lru_cache(maxsize=1)
def _tc() -> tuple[pd.Series, int]:
    i = pd.read_csv(LONG / "cov_ibtracs_par.csv")
    return pd.Series(i["tc_par"].to_numpy(float), index=i["q"].to_numpy()), int(i["q"].min())


@functools.lru_cache(maxsize=1)
def _palay() -> pd.Series:
    p = pd.read_csv(LONG / "cov_palay.csv")
    return pd.Series(p["yoy"].to_numpy(float), index=p["q"].to_numpy())


@functools.lru_cache(maxsize=1)
def _lfs() -> pd.Series:
    l = pd.read_csv(LONG / "cov_lfs.csv")
    v = pd.to_numeric(l["Unemployment Rate Both sexes"], errors="coerce")
    ym = l["Year"] * 12 + l["Month"].map(MONTHS)
    return pd.Series(v.to_numpy(float), index=ym.to_numpy()).dropna()


def _get(s, k):
    return float(s.loc[k]) if k in s.index and pd.notna(s.loc[k]) else np.nan


@functools.lru_cache(maxsize=4096)
def feats(t: int) -> tuple:
    m0 = R.m0(t)                                      # month 2 of quarter t: newest CPI month at O(t)
    c = _cpi()
    rice = _get(c["rice"], m0)
    rice3 = _get(c["rice"], m0 - 3)
    o = _oni()
    om = m0 - 1                                       # season ending month 1 of quarter t
    tc, tc0 = _tc()
    l = _lfs()
    lk = l[l.index <= m0 - 2]
    un = np.nan
    if len(lk):
        last = lk.index.max()
        if last - 12 in l.index:
            un = float(l.loc[last] - l.loc[last - 12])
    out = {"rice_yoy": rice, "rice_d3": rice - rice3, "food_yoy": _get(c["food"], m0),
           "oni_last": _get(o, om), "oni_max6": float(o[(o.index > om - 6) & (o.index <= om)].max()) if om in o.index else np.nan,
           "tc_prev": float(tc.get(t - 1, 0.0)) if t - 1 >= tc0 else np.nan,
           "palay_yoy": _get(_palay(), t - 1), "unemp_chg": un}
    return tuple(out[f] for f in FEATS)
