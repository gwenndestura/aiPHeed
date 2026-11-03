"""
E137 Layer S features, built for each HFIAS row as of its issue date (lead k = k quarters before the survey's
reference quarter, Q3 of the survey year; 2015 fieldwork was July-November).

Release rules (a value is used only if public on the issue date):
    PSA annual provincial CPI (year A, 2012=100)            from 15 February of A+1
    PSA poverty, subsistence, poverty gap, food threshold   round R from 1 January of R+2 (conservative)
    PSA census population (2010, 2015)                      census C from 1 January of C+2
    PSA quarterly palay+corn and fisheries                  45 days after the quarter ends
    NASA POWER monthly rainfall                             30 days after the month ends
    IBTrACS track positions                                 real time
    Previous HFIAS measurement (anchor)                     the 2015 FSS (public 2016) for ENNS rows

Groups (the only three with a national provincial series 2012-2019; see PROTOCOL.md section 4):
    market    m_food_cpi_yoy, m_rice_cpi_yoy, m_food_threshold_rel
    climate   c_rain_anom_6m, c_tc_4q, c_tc_clim, c_agri_pc, c_agri_yoy, c_fish_yoy
    poverty   p_poverty, p_subsistence, p_poverty_gap, p_density
    anchor    a_prev_y (previously measured relative position; "outcome history", not a contributor group)
Employment (no provincial LFS before 2021 on PSA OpenSTAT) and news (archive collected for CALABARZON only) cannot be
learned nationally; they are assessed in Layer T only.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

import numpy as np
import pandas as pd

from app.e137 import RAW
from app.e137.acquire import centroids
from app.hfias import RAW as HRAW
from app.hfias.panel import norm as key

GROUPS = {
    "market": ["m_food_cpi_yoy", "m_rice_cpi_yoy", "m_food_threshold_rel"],
    "climate": ["c_rain_anom_6m", "c_tc_4q", "c_tc_clim", "c_agri_pc", "c_agri_yoy", "c_fish_yoy"],
    "poverty": ["p_poverty", "p_subsistence", "p_poverty_gap", "p_density"],
    "anchor": ["a_prev_y"],
}
FEATURES = [f for g in GROUPS.values() for f in g]
GROUP_OF = {f: g for g, fs in GROUPS.items() for f in fs}
# Expected direction on relative food insecurity (+1 raises, -1 lowers, 0 free). Set from theory before any fit.
MONOTONE = {"m_food_cpi_yoy": 1, "m_rice_cpi_yoy": 1, "m_food_threshold_rel": 0,
            "c_rain_anom_6m": 0, "c_tc_4q": 1, "c_tc_clim": 1, "c_agri_pc": 0, "c_agri_yoy": -1, "c_fish_yoy": -1,
            "p_poverty": 1, "p_subsistence": 1, "p_poverty_gap": 1, "p_density": 0, "a_prev_y": 1}
FOOD_ITEMS = ["Rice", "Corn", "Fruit (ND)", "Vegetables (ND)", "Meat (ND)", "Milk, cheese and eggs (ND)",
              "Fish  and Seafood (ND)"]
TC_RADIUS_KM = 150.0
LEADS = [0, 1, 2, 3, 4]
GEO_ALIAS = {"metropolitanmanila": None}
NAME_ALIAS = {"mtprovince": "mountain", "mountainprovince": "mountain", "saranggani": "sarangani"}


def nospace(s: str) -> str:
    k = key(s).replace(" ", "")
    return NAME_ALIAS.get(k, k)


def issue_date(year: int, lead: int) -> pd.Timestamp:
    """Start of the reference quarter (Q3 of the survey year) minus `lead` quarters."""
    return pd.Timestamp(year=year, month=7, day=1) - pd.DateOffset(months=3 * lead)


def _logit(p):
    p = np.clip(np.asarray(p, float) / 100, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


@lru_cache(maxsize=None)
def _cpi() -> pd.DataFrame:
    d = pd.read_csv(HRAW / "psa" / "cpi_2012base_1994_2018.csv")
    d["k"] = d["Geolocation"].map(nospace)
    return d


@lru_cache(maxsize=None)
def _psa_rounds(fname: str, pattern: str) -> pd.DataFrame:
    """Province x round table: columns are round years, values numeric."""
    path = RAW / "psa" / fname if (RAW / "psa" / fname).exists() else HRAW / "psa" / fname
    d = pd.read_csv(path, dtype=str, encoding="latin-1")
    d["k"] = d.iloc[:, 0].map(nospace)
    cols = {int(m.group(1)): c for c in d.columns if (m := re.search(pattern + r".*?(\d{4})\s*$", c))}
    out = pd.DataFrame({y: pd.to_numeric(d[c], errors="coerce").values for y, c in cols.items()}, index=d["k"])
    return out[~out.index.duplicated()]


@lru_cache(maxsize=None)
def _census() -> pd.DataFrame:
    pop = pd.read_csv(RAW / "psa" / "population_2010_2024.csv", dtype=str, encoding="latin-1")
    pop = pop[pop.iloc[:, 0].str.match(r"^\.\.\.\.[^.]")]
    pop["k"] = pop.iloc[:, 0].str.replace("*", "", regex=False).map(nospace)
    area = pd.read_csv(RAW / "psa" / "land_area_density_2024.csv", dtype=str, encoding="latin-1")
    area = area[area.iloc[:, 0].str.match(r"^\.\.\.\.[^.]")]
    area["k"] = area.iloc[:, 0].str.replace("*", "", regex=False).map(nospace)
    a = pd.to_numeric(area.set_index("k").filter(like="Land Area").iloc[:, 0], errors="coerce")
    p = pop.set_index("k")
    out = pd.DataFrame({2010: pd.to_numeric(p.filter(like="2010)").iloc[:, 0], errors="coerce"),
                        2015: pd.to_numeric(p.filter(like="2015)").iloc[:, 0], errors="coerce")})
    out = out[~out.index.duplicated()]
    out["area"] = a[~a.index.duplicated()].reindex(out.index)
    return out


def _latest(years, as_of: pd.Timestamp, lag_years: int = 2) -> int | None:
    ok = [y for y in years if pd.Timestamp(year=y + lag_years, month=1, day=1) <= as_of]
    return max(ok) if ok else None


@lru_cache(maxsize=None)
def _quarterly(fname: str, label_col: str, labels: tuple) -> pd.DataFrame:
    d = pd.read_csv(HRAW / "psa" / fname)
    d = d[d[label_col].isin(labels)].copy()
    d["k"] = d["Geolocation"].map(nospace)
    qcols = [c for c in d.columns if re.match(r"^\d{4} Quarter \d$", c)]
    d[qcols] = d[qcols].apply(pd.to_numeric, errors="coerce")
    return d.groupby("k")[qcols].sum(min_count=1)


def _published_quarters(cols, as_of):
    def end(c):
        y, q = int(c[:4]), int(c[-1])
        return pd.Timestamp(year=y, month=3 * q, day=1) + pd.offsets.MonthEnd(0)
    return [c for c in cols if end(c) + pd.Timedelta(days=45) <= as_of]


@lru_cache(maxsize=None)
def _geo() -> dict:
    out = {}
    for name, xy in centroids().items():
        k = nospace(name)
        k = GEO_ALIAS.get(k, k)
        if k:
            out[k.replace(" ", "")] = xy
    return out


@lru_cache(maxsize=None)
def _rain() -> dict:
    out = {}
    for f in (RAW / "nasa").glob("power_*.json"):
        k = nospace(f.stem.replace("power_", ""))
        k = (GEO_ALIAS.get(k, k) or "").replace(" ", "")
        if not k:
            continue
        v = json.loads(f.read_text())["properties"]["parameter"]["PRECTOTCORR"]
        s = pd.Series({pd.Period(f"{x[:4]}-{x[4:]}", "M"): val for x, val in v.items() if x[4:] != "13"}, dtype=float)
        out[k] = s.where(s > -900)
    return out


@lru_cache(maxsize=None)
def _tracks() -> pd.DataFrame:
    d = pd.read_csv(RAW / "ibtracs" / "ibtracs.WP.list.v04r01.csv", skiprows=[1], usecols=["SID", "ISO_TIME", "LAT", "LON"],
                    low_memory=False)
    d["t"] = pd.to_datetime(d["ISO_TIME"], errors="coerce")
    d = d[(d["t"] >= "1990-01-01") & (d["t"] < "2027-01-01")]
    d["LAT"], d["LON"] = pd.to_numeric(d["LAT"], errors="coerce"), pd.to_numeric(d["LON"], errors="coerce")
    return d[d["LAT"].between(2, 23) & d["LON"].between(113, 131)].reset_index(drop=True)


def _km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 6371.0 * 2 * np.arcsin(np.sqrt(a))


@lru_cache(maxsize=None)
def _storm_hits(k: str) -> pd.DataFrame:
    """First time each storm comes within TC_RADIUS_KM of the province centroid."""
    xy = _geo().get(k)
    if xy is None:
        return pd.DataFrame(columns=["SID", "t"])
    t = _tracks()
    near = t[_km(t["LAT"].values, t["LON"].values, xy[1], xy[0]) <= TC_RADIUS_KM]
    return near.groupby("SID", as_index=False)["t"].min()


def row_features(k: str, issue: pd.Timestamp, prev_y: float | None) -> dict:
    out = {f: np.nan for f in FEATURES}
    # market
    cpi = _cpi()
    a = max(y for y in range(2012, 2019) if pd.Timestamp(f"{y + 1}-02-15") <= issue) if issue >= pd.Timestamp("2013-02-15") else None
    if a and a - 1 >= 2012:
        g = cpi[cpi["k"] == k]
        for name, items in (("m_food_cpi_yoy", FOOD_ITEMS), ("m_rice_cpi_yoy", ["Rice"])):
            gi = g[g["Commodity"].isin(items)]
            if len(gi):
                x1, x0 = (pd.to_numeric(gi[f"Annual {y}"], errors="coerce").mean() for y in (a, a - 1))
                out[name] = float(np.log(x1 / x0)) if x1 > 0 and x0 > 0 else np.nan
    thr = _psa_rounds("food_threshold_subsistence_2006_2015.csv", r"Food Threshold")
    r = _latest([y for y in thr.columns if y >= 2006], issue)
    if r and k in thr.index:
        out["m_food_threshold_rel"] = float(np.log(thr.at[k, r] / thr.at["philippines", r]))
    # poverty
    pov = _psa_rounds("poverty_1991_2015.csv", r"Incidence")
    sub = _psa_rounds("subsistence_1991_2015.csv", r"Incidence")
    gap = _psa_rounds("poverty_gap_severity_2006_2015.csv", r"Poverty Gap")
    for name, tab, fn in (("p_poverty", pov, _logit), ("p_subsistence", sub, _logit), ("p_poverty_gap", gap, float)):
        r = _latest(list(tab.columns), issue)
        if r and k in tab.index and pd.notna(tab.at[k, r]):
            out[name] = float(fn(tab.at[k, r]))
    cen = _census()
    c = _latest([2010, 2015], issue)
    pop = cen.at[k, c] if (c and k in cen.index) else np.nan
    if k in cen.index and pd.notna(pop) and pd.notna(cen.at[k, "area"]) and cen.at[k, "area"] > 0:
        out["p_density"] = float(np.log(pop / cen.at[k, "area"]))
    # climate and agriculture
    for name, fname, col, labels in (("agri", "palay_corn_quarterly.csv", "Ecosystem/Croptype", ("Palay", "Corn")),
                                     ("fish", "fisheries_quarterly.csv", "Subsector", ("FISHERIES",))):
        q = _quarterly(fname, col, labels)
        if k not in q.index:
            continue
        pub = _published_quarters(list(q.columns), issue)
        if len(pub) >= 8:
            last4, prev4 = q.loc[k, pub[-4:]].sum(min_count=4), q.loc[k, pub[-8:-4]].sum(min_count=4)
            if last4 > 0 and prev4 > 0:
                out[f"c_{name}_yoy"] = float(np.log(last4 / prev4))
            if name == "agri" and pd.notna(pop) and last4 > 0:
                out["c_agri_pc"] = float(np.log(last4 / pop))
    rain = _rain().get(k)
    if rain is not None:
        last_month = (issue - pd.Timedelta(days=30)).to_period("M") - 1
        months = pd.period_range(last_month - 5, last_month, freq="M")
        if all(m in rain.index for m in months):
            v = rain[months].mean()
            clim = [rain[[pd.Period(year=y, month=m.month, freq="M") for m in months]].mean() for y in range(2000, 2010)]
            out["c_rain_anom_6m"] = float((v - np.mean(clim)) / np.std(clim, ddof=1))
    hits = _storm_hits(k)
    if _geo().get(k) is not None:
        out["c_tc_4q"] = float(((hits["t"] < issue) & (hits["t"] >= issue - pd.Timedelta(days=365))).sum())
        out["c_tc_clim"] = float(((hits["t"] >= "1990-01-01") & (hits["t"] < "2010-01-01")).sum() / 20.0)
    out["a_prev_y"] = prev_y if prev_y is not None and np.isfinite(prev_y) else np.nan
    return out


def build(d: pd.DataFrame, lead: int) -> pd.DataFrame:
    """Feature matrix for outcome rows `d` (from outcomes.load) at one lead."""
    rows = []
    for _, r in d.iterrows():
        issue = issue_date(int(r["year"]), lead)
        k = r["key"].replace(" ", "")
        rows.append({"issue_date": issue.date().isoformat(), "lead": lead,
                     **row_features(k, issue, r["prev_y"] if r["survey"] != "FNRI2015" else None)})
    return pd.concat([d.reset_index(drop=True), pd.DataFrame(rows)], axis=1)


def coverage(X: pd.DataFrame) -> pd.Series:
    return X[FEATURES].notna().mean().round(3)
