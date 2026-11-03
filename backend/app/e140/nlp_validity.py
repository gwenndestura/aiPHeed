"""
Objective 1, NLP validation without human labels (owner rule): CONVERGENT VALIDITY of the province-quarter news
signals against independently measured events. This tests whether the XLM-R/BERTopic signals move with the real-world
conditions they claim to reflect; it does NOT establish sentiment accuracy.

    python -m app.e140.nlp_validity   -> data/e140/out/nlp_validity.json

Pre-specified tests (one-sided: the signal should be HIGHER when the event is present):
    V1 climate news (FI5 fssi_raw_climate, 2021+)   vs tropical cyclones within 150 km of the province that quarter (IBTrACS)
    V2 market news  (FI5 fssi_raw_market, 2021+)    vs the province's food CPI YoY at the latest annual value public that quarter
    V3 archive risk share (FI6-N, 2012+)            vs tropical cyclones that quarter
Spearman correlation over CALABARZON province-quarters; quarters with no articles are excluded, not set to zero.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from app.e137 import features as F
from app.paths import BACKEND_DIR

OUT = BACKEND_DIR / "data" / "e140" / "out"
CAL = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]


def _q_bounds(q: str):
    y, n = int(q[:4]), int(q[-1])
    s = pd.Timestamp(year=y, month=3 * n - 2, day=1)
    return s, s + pd.DateOffset(months=3)


def cyclones(prov: str, q: str) -> int:
    h = F._storm_hits(F.nospace(prov))
    s, e = _q_bounds(q)
    return int(((h["t"] >= s) & (h["t"] < e)).sum())


def _cpi2018() -> pd.DataFrame:
    """Annual-average provincial CPI 2018=100, mean of the food groups used in training: 2021-2022 and 2024-2025 held."""
    parts = []
    for f in (BACKEND_DIR / "data" / "e137" / "raw" / "y2023" / "psa" / "cpi2018_ave.csv",
              BACKEND_DIR / "data" / "e139" / "raw" / "psa" / "cpi2018_ave_2024_2025.csv"):
        d = pd.read_csv(f, encoding="latin-1")
        d["k"] = d["Geolocation"].map(F.nospace)
        ycols = [c for c in d.columns if c.endswith("Ave")]
        d[ycols] = d[ycols].apply(pd.to_numeric, errors="coerce")
        parts.append(d.groupby("k")[ycols].mean().rename(columns=lambda c: int(c[:4])))
    return pd.concat(parts, axis=1)


_C18 = None


def cpi_yoy(prov: str, q: str) -> float:
    """YoY of the latest annual value public at the quarter start (annual A public from 15 Feb A+1)."""
    global _C18
    s, _ = _q_bounds(q)
    a = s.year - 1 if s >= pd.Timestamp(year=s.year, month=2, day=15) else s.year - 2
    if a < 2019:
        return F.row_features(F.nospace(prov), s, None)["m_food_cpi_yoy"]
    _C18 = _cpi2018() if _C18 is None else _C18
    k = F.nospace(prov)
    if k in _C18.index and a in _C18.columns and a - 1 in _C18.columns:
        return float(np.log(_C18.at[k, a] / _C18.at[k, a - 1]))
    return np.nan


def test(x, y):
    d = pd.DataFrame({"x": x, "y": y}).dropna()
    if len(d) < 8 or d["x"].nunique() < 2 or d["y"].nunique() < 2:
        return {"n": int(len(d)), "spearman": None, "p_one_sided": None}
    r = spearmanr(d["x"], d["y"])
    p = r.pvalue / 2 if r.statistic > 0 else 1 - r.pvalue / 2
    return {"n": int(len(d)), "spearman": float(r.statistic), "p_one_sided": float(p)}


def run() -> dict:
    f5 = pd.read_csv(BACKEND_DIR / "data" / "fi5" / "nlp" / "fssi_province_quarter.csv")
    f5 = f5[f5["geo"].isin(CAL) & (f5["n_articles"] > 0)].copy()
    f5["tc"] = [cyclones(p, q) for p, q in zip(f5["geo"], f5["quarter"])]
    f5["cpi"] = [cpi_yoy(p, q) for p, q in zip(f5["geo"], f5["quarter"])]
    a = pd.read_csv(BACKEND_DIR / "data" / "fi6" / "news_archive" / "fssi_archive_province_quarter.csv")
    a = a[a["province"].isin(CAL) & (a["articles"] > 0)].copy()
    a["tc"] = [cyclones(p, q) for p, q in zip(a["province"], a["quarter"])]
    res = {"V1_climate_news_vs_cyclones": test(f5["tc"], f5["fssi_raw_climate"]),
           "V2_market_news_vs_food_cpi_yoy": test(f5["cpi"], f5["fssi_raw_market"]),
           "V3_archive_risk_share_vs_cyclones": test(a["tc"], a["risk_share_corrected"]),
           "coverage": {"fi5_province_quarters_with_articles": int(len(f5)), "fi5_quarters": [f5["quarter"].min(), f5["quarter"].max()],
                        "archive_province_quarters_with_articles": int(len(a)), "archive_quarters": [a["quarter"].min(), a["quarter"].max()]},
           "note": "Convergent validity only; sentiment accuracy needs a human-labelled set (excluded by owner rule)."}
    res["V2_market_news_vs_food_cpi_yoy"]["note"] = ("provincial CPI 2018=100 annual averages held for 2021-2022 and "
                                                     "2024-2025 only; quarters whose YoY needs 2023 are excluded")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "nlp_validity.json").write_text(json.dumps(res, indent=2, default=str))
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str))
