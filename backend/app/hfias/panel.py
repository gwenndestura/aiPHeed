"""
Province panel for the HFIAS target: one row per province measured in both FNRI 2015 and an ENNS round (2018 or 2019),
with features built as of an issue date `lead` quarters before the survey year's first quarter.

Release rules (every feature uses only values public on the issue date):
    FNRI 2015 HFIAS, PSA 2015 poverty/subsistence    public before the earliest issue date used (2017-01-01)
    PSA annual provincial CPI by food group (year A) public from 15 February of A+1
    PSA quarterly palay/corn and fisheries (quarter q) public 45 days after the quarter ends
    SWS hunger (area)                                its release date
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from app.hfias import CLEAN, RAW

# 2015 FNRI region -> SWS area (H1). NCR, Balance Luzon, Visayas, Mindanao.
SWS_AREA = {"NCR": "metro_manila", "CAR": "balance_luzon", "Ilocos": "balance_luzon", "Cagayan Valley": "balance_luzon",
            "Central Luzon": "balance_luzon", "CALABARZON": "balance_luzon", "MIMAROPA": "balance_luzon",
            "Bicol": "balance_luzon", "Western Visayas": "visayas", "Central Visayas": "visayas",
            "Eastern Visayas": "visayas", "Zamboanga Peninsula": "mindanao", "Northern Mindanao": "mindanao",
            "Davao": "mindanao", "SOCCSKSARGEN": "mindanao", "ARMM": "mindanao", "Caraga": "mindanao"}
ISLAND = {"metro_manila": "Luzon", "balance_luzon": "Luzon", "visayas": "Visayas", "mindanao": "Mindanao"}
FAMILIES = {"y2015_logit": "lag (HFIAS 2015)", "poverty_2015": "V1", "subsistence_2015": "V1",
            "rice_cpi_change": "A3", "food_cpi_change": "A1/A2", "fish_cpi_change": "A1/A2",
            "palay_corn_change": "C3", "fisheries_change": "C4", "sws_change": "H1"}
GROUP = {"V1": "poverty", "A3": "market", "A1/A2": "market", "C3": "climate", "C4": "climate", "H1": "H1",
         "lag (HFIAS 2015)": "lag"}


ALIASES = {"samar": "western samar"}         # PSA/ENNS "Samar" = FNRI 2015 "Western Samar"


def norm(name: str) -> str:
    s = re.sub(r"\s*(\d+|[a-z])/\s*", " ", str(name))
    s = re.sub(r"^\.+", "", s).strip().lower()
    s = s.replace("ñ", "n").replace("�", "n")
    s = re.sub(r"\bprovince\b", "", s)
    s = re.sub(r"[^a-z ]", " ", s)
    s = " ".join(s.split())
    return ALIASES.get(s, s)


def logit(p):
    p = np.clip(np.asarray(p, float) / 100, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def expit(x):
    return 100 / (1 + np.exp(-np.asarray(x, float)))


TARGET = "insecure"          # HFIAS households food insecure at any level (FNRI's headline indicator); "mod_sev" secondary


def outcomes(target: str = TARGET) -> pd.DataFrame:
    """Provinces measured in FNRI 2015 and an ENNS round. y = target share (%); y_se = its sampling SE (median of the
    same round where the deck printed no interval); nat = the national value of the same round (class reference)."""
    f = pd.read_csv(CLEAN / "fnri2015_hfias.csv")
    f = f[f["level"] == "province"].copy()
    f["key"] = f["name"].map(norm)
    f["insecure_se"] = f["food_secure_se"]
    e = pd.read_csv(CLEAN / "enns_hfias.csv")
    e["key"] = e["area"].map(norm)
    e = e[~e["key"].str.contains(r"\bcity\b") & ~e["key"].isin(["pateros"])]     # HUCs / NCR towns: no 2015 province
    e["ph_insecure_pct"] = 100 - e["ph_food_secure_pct"]
    e["nat"] = e.groupby("year")[f"ph_{target}_pct"].transform("median")
    e["y_se"] = e[f"{target}_se"].fillna(e.groupby("year")[f"{target}_se"].transform("median"))
    e["y_se_imputed"] = e[f"{target}_se"].isna()
    e = e.dropna(subset=[f"{target}_pct"])
    m = e[["key", "area", "year", f"{target}_pct", "y_se", "y_se_imputed", "nat", "file"]].merge(
        f[["key", "name", "region", f"{target}_pct", f"{target}_se"]], on="key", suffixes=("", "_2015"))
    m = m.rename(columns={f"{target}_pct_2015": "y2015", f"{target}_se_2015": "y2015_se", f"{target}_pct": "y", "name": "province"})
    m["target"] = target
    m["sws_area"] = m["region"].map(SWS_AREA)
    m["island"] = m["sws_area"].map(ISLAND)
    m.attrs["unmatched_enns"] = sorted(set(e["key"]) - set(m["key"]))
    return m.reset_index(drop=True)


def _wide_psa(fname: str, value_col_pat: str) -> pd.Series:
    d = pd.read_csv(RAW / "psa" / fname, dtype=str)
    col = next(c for c in d.columns if re.search(value_col_pat, c))
    s = pd.Series(pd.to_numeric(d[col], errors="coerce").values, index=d.iloc[:, 0].map(norm))
    return s[~s.index.duplicated()]


def _cpi(as_of: pd.Timestamp) -> tuple[pd.DataFrame, int]:
    d = pd.read_csv(RAW / "psa" / "cpi_2012base_1994_2018.csv")
    d["key"] = d["Geolocation"].map(norm)
    last = max(a for a in range(2012, 2019) if pd.Timestamp(f"{a + 1}-02-15") <= as_of)
    return d, last


def _quarterly(fname: str, label_col: str, label: list[str], as_of: pd.Timestamp) -> pd.Series:
    """log(production of the last 4 published quarters / production of 2015), by province."""
    d = pd.read_csv(RAW / "psa" / fname)
    d = d[d[label_col].isin(label)]
    d["key"] = d["Geolocation"].map(norm)
    qcols = [c for c in d.columns if re.match(r"^\d{4} Quarter \d$", c)]
    d[qcols] = d[qcols].apply(pd.to_numeric, errors="coerce")

    def end(c):
        y, q = int(c[:4]), int(c[-1])
        return pd.Timestamp(year=y, month=3 * q, day=1) + pd.offsets.MonthEnd(0)
    pub = [c for c in qcols if end(c) + pd.Timedelta(days=45) <= as_of]
    last4, base = pub[-4:], [c for c in qcols if c.startswith("2015")]
    v = d.groupby("key")[qcols].sum(min_count=1)
    num, den = v[last4].sum(axis=1, min_count=4), v[base].sum(axis=1, min_count=4)
    return np.log(num.where(num > 0) / den.where(den > 0))


def _sws_change(as_of: pd.Timestamp) -> dict:
    from app.fi5.sources import sws_rounds
    r = sws_rounds()
    r["year"] = r["quarter"].str[:4].astype(int)
    out = {}
    for area in ("metro_manila", "balance_luzon", "visayas", "mindanao"):
        known = r[r["published"] <= as_of].dropna(subset=[area])
        recent = known.sort_values("published").tail(4)[area].mean()
        base = known[known["year"] == 2015][area].mean()
        out[area] = float(logit(recent) - logit(base))
    return out


def features(o: pd.DataFrame, lead: int) -> pd.DataFrame:
    """Features for every row as of its issue date: first day of the quarter `lead` quarters before Q1 of its survey year."""
    rows = []
    pov = _wide_psa("poverty_1991_2015.csv", r"Incidence.*2015")
    sub = _wide_psa("subsistence_1991_2015.csv", r"Incidence.*2015")
    for _, r in o.iterrows():
        issue = pd.Timestamp(year=int(r["year"]), month=1, day=1) - pd.DateOffset(months=3 * (lead - 1))
        cpi, last = _cpi(issue)
        k = r["key"]

        def cpi_change(items):
            g = cpi[(cpi["key"] == k) & cpi["Commodity"].isin(items)]
            if g.empty or last <= 2015:
                return np.nan
            a, b = (pd.to_numeric(g[c], errors="coerce").mean() for c in (f"Annual {last}", "Annual 2015"))
            return float(np.log(a / b)) if a > 0 and b > 0 else np.nan
        sws = _sws_change(issue)
        rows.append({
            "key": k, "issue_date": issue.date().isoformat(), "lead": lead, "cpi_year_used": last,
            "y2015_logit": float(logit(r["y2015"])),
            "poverty_2015": float(logit(pov.get(k, np.nan))), "subsistence_2015": float(logit(sub.get(k, np.nan))),
            "rice_cpi_change": cpi_change(["Rice"]),
            "food_cpi_change": cpi_change(["Rice", "Corn", "Fruit (ND)", "Vegetables (ND)", "Meat (ND)",
                                           "Milk, cheese and eggs (ND)", "Fish  and Seafood (ND)"]),
            "fish_cpi_change": cpi_change(["Fish  and Seafood (ND)"]),
            "palay_corn_change": float(_quarterly("palay_corn_quarterly.csv", "Ecosystem/Croptype", ["Palay", "Corn"], issue).get(k, np.nan)),
            "fisheries_change": float(_quarterly("fisheries_quarterly.csv", "Subsector", ["FISHERIES"], issue).get(k, np.nan)),
            "sws_change": sws[r["sws_area"]],
        })
    return o.merge(pd.DataFrame(rows), on="key")
