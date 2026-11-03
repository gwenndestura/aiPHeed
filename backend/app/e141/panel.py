"""
E141 three-round provincial panel: one row per province x survey round (NNS 2013, FNRI 2015, ENNS 2018/2019), each with
features as of its issue date (`lead` quarters before the round's reference quarter, Q3 of the survey year) and the
measured history known at that date (the province's position and its region's mean position in the PREVIOUS round).

No quarterly label is created; a row exists only where a survey measured the province.
"""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
from scipy.stats import norm

from app.e137 import features as F
from app.e137 import outcomes as O
from app.e140 import model as M140
from app.e141 import DATA, RAW
from app.hfias.panel import ISLAND, SWS_AREA
from app.hfias.panel import norm as key

NAT2013 = {"mod_sev": 34.1 + 16.7, "insecure": 100 - 34.1}
ROUND_ORDER = ["NNS2013", "FNRI2015", "ENNS2018", "ENNS2019"]


def _use_long_history() -> None:
    """Point E137's builders at the longer PSA files (2010+ CPI and production, 2006+ poverty rounds)."""
    if F.HRAW != RAW:
        F.HRAW = RAW
        for fn in (F._cpi, F._psa_rounds, F._quarterly):
            fn.cache_clear()


@lru_cache(maxsize=None)
def _cpi_long() -> pd.DataFrame:
    d = pd.read_csv(RAW / "psa" / "cpi_2012base_1994_2018.csv")
    d["k"] = d["Geolocation"].map(F.nospace)
    return d


def cpi_yoy(k: str, issue: pd.Timestamp, items: list[str]) -> float:
    """Same definition as E137 (log ratio of the latest public annual index to the year before, mean of the items), but
    allowing base years from 2010 so that 2013 issue dates have a value."""
    years = [y for y in range(2011, 2019) if pd.Timestamp(f"{y + 1}-02-15") <= issue]
    if not years:
        return np.nan
    a = max(years)
    g = _cpi_long()
    g = g[(g["k"] == k) & g["Commodity"].isin(items)]
    if g.empty:
        return np.nan
    x1, x0 = (pd.to_numeric(g[f"Annual {y}"], errors="coerce").mean() for y in (a, a - 1))
    return float(np.log(x1 / x0)) if x1 > 0 and x0 > 0 else np.nan


def outcomes(outcome: str = "mod_sev", reference: str = "pooled") -> pd.DataFrame:
    d = O.load(outcome, reference)
    t = pd.read_csv(DATA / "clean" / "nns2013_hfias.csv")
    t["key"] = t["province"].map(key)
    region = dict(zip(d["key"], d["region"]))
    island = dict(zip(d["key"], d["island"]))
    y, se_y = O._rel(t[f"{outcome}_pct"], t[f"{outcome}_se"], NAT2013[outcome])
    r13 = pd.DataFrame({"key": t["key"], "province": t["province"], "region": t["key"].map(region), "survey": "NNS2013",
                        "year": 2013, "ref_quarter": "2013-Q3", "p": t[f"{outcome}_pct"], "se_p": t[f"{outcome}_se"],
                        "ref": NAT2013[outcome], "has_value": True, "se_imputed": True, "source": t["source"],
                        "y": y, "se_y": se_y, "half_width": 1.959964 * t[f"{outcome}_se"]})
    r13["status"] = O.status(r13["y"], r13["se_y"], r13["half_width"], r13["has_value"])
    r13["q"] = norm.cdf(r13["y"] / r13["se_y"])
    r13["sws_area"] = r13["region"].map(SWS_AREA)
    r13["island"] = r13["key"].map(island)
    r13["outcome"], r13["reference"] = outcome, reference
    d = d[d["has_value"]].drop(columns=["prev_y", "prev_se_y"])
    allr = pd.concat([r13[r13["region"].notna()], d], ignore_index=True)
    allr["round"] = allr["survey"].map(ROUND_ORDER.index)
    # previous measured round of the same province (2013 -> 2015 -> ENNS)
    allr = allr.sort_values(["key", "round"]).reset_index(drop=True)
    allr["prev_y"] = allr.groupby("key")["y"].shift(1)
    allr["prev_se_y"] = allr.groupby("key")["se_y"].shift(1)
    allr["prev_survey"] = allr.groupby("key")["survey"].shift(1)
    return allr


def data(lead: int = 1, outcome: str = "mod_sev", reference: str = "pooled") -> pd.DataFrame:
    _use_long_history()
    d = outcomes(outcome, reference)
    X = F.build(d, lead)
    food = ["Rice", "Corn", "Fruit (ND)", "Vegetables (ND)", "Meat (ND)", "Milk, cheese and eggs (ND)", "Fish  and Seafood (ND)"]
    issues = [F.issue_date(int(y), lead) for y in X["year"]]
    X["m_food_cpi_yoy"] = [cpi_yoy(k.replace(" ", ""), i, food) for k, i in zip(X["key"], issues)]
    X["m_rice_cpi_yoy"] = [cpi_yoy(k.replace(" ", ""), i, ["Rice"]) for k, i in zip(X["key"], issues)]
    X["a_prev_y"] = X["prev_y"]                       # measured position in the previous round (public before issue)
    prev_reg = X.groupby(["survey", "region"])["y"].mean()
    X["a_region_prev"] = [prev_reg.get((ps, r), np.nan) if isinstance(ps, str) else np.nan
                          for ps, r in zip(X["prev_survey"], X["region"])]
    X["island_code"] = X["island"].map(M140.ISLAND).astype(float)
    return X
