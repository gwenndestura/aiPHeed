"""FI6 target: SWS involuntary hunger (Balance Luzon) significantly above its five-year normal.

    hunger_t      mean of the SWS rounds in quarter t (% of families)
    se_t          published 95 % margin of error / 1.96, divided by sqrt(rounds in the quarter)
    normal_t      mean of the readings in quarters t-20 .. t-1 (>= 8 readings)
    HIGH_t        hunger_t - normal_t > moe_t        (moe_t = the round's published margin)

So HIGH means the rise above normal is larger than what survey sampling alone could produce at 95 % confidence.
Quarters without a round are unlabeled. `candidates()` reproduces the label-reliability comparison that chose this
definition (expected probability that sampling error flips a label: P(flip) = Phi(-|distance to threshold| / se)).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from app.fi5.sources import sws_rounds
from app.fi5.target import qindex

AREA = "balance_luzon"
MOE_COL = {"balance_luzon": "area_moe_bl"}
BASELINE_Q, MIN_OBS = 20, 8


def quarterly(area: str = AREA) -> pd.DataFrame:
    r = sws_rounds()
    moe = r[MOE_COL[area]] if area in MOE_COL else r["area_moe_other"]
    r = r.assign(_moe=moe)
    g = r.groupby("quarter").agg(hunger=(area, "mean"), k=(area, "count"), moe=("_moe", "max"),
                                 published=("published", "max")).dropna(subset=["hunger"]).reset_index()
    g["qi"] = g["quarter"].map(qindex)
    g["se"] = g["moe"] / 1.96 / np.sqrt(g["k"])
    return g.sort_values("qi").reset_index(drop=True)


def labels(area: str = AREA) -> pd.DataFrame:
    q = quarterly(area)
    rows = []
    for _, r in q.iterrows():
        w = q[(q["qi"] >= r["qi"] - BASELINE_Q) & (q["qi"] < r["qi"])]
        if len(w) < MIN_OBS:
            rows.append({**r.to_dict(), "normal": np.nan, "anomaly": np.nan, "y": np.nan, "p_flip": np.nan})
            continue
        normal = float(w["hunger"].mean())
        se_d = float(np.sqrt(r["se"] ** 2 + (w["se"] ** 2).sum() / len(w) ** 2))
        a = r["hunger"] - normal
        rows.append({**r.to_dict(), "normal": normal, "anomaly": a, "threshold": normal + r["moe"],
                     "y": int(a > r["moe"]), "se_diff": se_d, "p_flip": float(norm.cdf(-abs(a - r["moe"]) / se_d))})
    return pd.DataFrame(rows)


def candidates(first_year: int = 2010) -> pd.DataFrame:
    """Label reliability of the target definitions that were considered (evaluated quarters only)."""
    d = labels()
    d = d[d["normal"].notna() & (d["qi"] >= first_year * 4)].reset_index(drop=True)
    a, sd, se, h, moe = d["anomaly"], d["se_diff"], d["se"], d["hunger"], d["moe"]
    ch = h.diff()
    se_ch = np.sqrt(se ** 2 + se.shift() ** 2)
    defs = {
        "FI5: above five-year average": (a > 0, norm.cdf(-a.abs() / sd)),
        "FI6: above five-year average by more than the margin of error": (a > moe, norm.cdf(-(a - moe).abs() / sd)),
        "above five-year average by more than one standard error": (a > sd, norm.cdf(-(a - sd).abs() / sd)),
        "absolute: at least 20 % of families": (h >= 20, norm.cdf(-(h - 20).abs() / se)),
        "absolute: at least 15 % of families": (h >= 15, norm.cdf(-(h - 15).abs() / se)),
        "rise versus the previous reading": (ch > 0, norm.cdf(-ch.abs() / se_ch)),
    }
    rows = []
    for name, (y, pf) in defs.items():
        m = ~np.isnan(np.asarray(pf, float))
        y, pf = np.asarray(y)[m], np.asarray(pf, float)[m]
        rows.append({"target": name, "n": int(m.sum()), "n_high": int(y.sum()), "high_share": float(y.mean()),
                     "mean_p_flip": float(pf.mean()), "share_p_flip_over_0.2": float((pf > 0.2).mean()),
                     "oracle_accuracy_ceiling": float(1 - pf.mean())})
    return pd.DataFrame(rows)
