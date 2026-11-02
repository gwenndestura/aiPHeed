"""Candidate government / institutional indicators added in FI7 (each with a conservative release rule).

    world rice price   World Bank Commodity Price Data (Pink Sheet), Rice Thai 5 %, USD/mt, monthly 1960+.
                       The Philippines imports rice; world prices lead domestic rice prices. Released in the first
                       days of the next month -> available month end + 10 days.
    urea price         same source, fertilizer cost of production (availability channel); same rule.
    underemployment    PSA LFS underemployed persons / employed persons (LF - unemployed), Philippines, 2005+
                       (quarterly rounds until 2020, monthly after); available survey month + 45 days.
    fisheries output   PSA quarterly fisheries production, Region IV-A total, 1980+; quarter end + 45 days.
    typhoon intensity  NOAA IBTrACS (PAGASA/JTWC tracks): strongest wind (kt) of any storm passing within 200 km of a
                       CALABARZON province centroid in the issue quarter so far, and count of typhoon-strength
                       (>= 64 kt) passages in the last 4 quarters; real time.

Rejected (documented in docs/fi7): BSP monthly cash remittances (bsp.gov.ph refuses automated download, HTTP 403;
the WDI annual series stays), regional unemployment (IV-A only annual 2021+), NDRRMC agricultural damage (PDF
situation reports, no consistent series), DSWD 4Ps counts (PDF, irregular), regional quarterly GRDP (not published
quarterly for regions).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.fi5.paths import RAW
from app.fi5.sources import CENTROIDS, TC_RADIUS_KM, _haversine, _month_end

MONTHS = {m: i + 1 for i, m in enumerate(["January", "February", "March", "April", "May", "June", "July", "August",
                                          "September", "October", "November", "December"])}
EXP = RAW.parents[3] / "aipheed-backend-aligned" / "experiments"


def world_prices() -> pd.DataFrame:
    d = pd.read_csv(RAW / "wb" / "wb_pinksheet_selected_monthly.csv")
    d.columns = [c.strip() for c in d.columns]
    d["period_end"] = [_month_end(int(p[:4]), int(p[5:])) for p in d["period"]]
    d = d.sort_values("period_end").set_index("period_end")
    out = pd.DataFrame(index=d.index)
    for col, key in [("Rice, Thai 5%", "rice"), ("Urea", "urea")]:
        v = pd.to_numeric(d[col], errors="coerce")
        out[f"world_{key}_yoy"] = 100 * (v / v.shift(12) - 1)
        out[f"world_{key}_3m"] = 100 * (v / v.shift(3) - 1)
    out["available_from"] = out.index + pd.offsets.MonthBegin(1) + pd.Timedelta(days=9)
    return out.dropna(subset=["world_rice_yoy"]).reset_index()


def underemployment() -> pd.DataFrame:
    u = pd.read_csv(RAW / "psa" / "psa_lfs_underemployed_persons.csv", dtype=str, encoding="latin-1")
    lv = pd.read_csv(RAW / "psa" / "lfs_levels_national.csv", dtype=str)
    u = u[u["Month"].isin(MONTHS)]
    lv = lv[lv["Month"].isin(MONTHS)]
    u["under"] = pd.to_numeric(u.iloc[:, 2], errors="coerce")
    lv["lf"] = pd.to_numeric(lv.iloc[:, 2], errors="coerce")
    lv["unemp"] = pd.to_numeric(lv.iloc[:, 3], errors="coerce")
    m = u.merge(lv, on=["Year", "Month"]).dropna(subset=["under", "lf", "unemp"])
    m["period_end"] = [_month_end(int(y), MONTHS[mo]) for y, mo in zip(m["Year"], m["Month"])]
    m = m.sort_values("period_end").set_index("period_end")
    m["underemp_rate"] = 100 * m["under"] / (m["lf"] - m["unemp"])
    prev = m["underemp_rate"].copy()
    prev.index = (prev.index + pd.DateOffset(years=1)) + pd.offsets.MonthEnd(0)
    out = pd.DataFrame({"underemp_rate": m["underemp_rate"], "underemp_yoy": m["underemp_rate"] - prev.reindex(m.index)})
    out["available_from"] = out.index + pd.Timedelta(days=45)
    return out.reset_index()


def fisheries() -> pd.DataFrame:
    d = pd.read_csv(EXP / "E118_FAO_Data_Discovery" / "data" / "clean" / "prod_fisheries.csv")
    d = d[(d["unit"] == "Region IV-A") & (d["item"] == "FISHERIES") & (d["freq"] == "Q")].dropna(subset=["value"])
    d["year"], d["q"] = (d["period"] // 4).astype(int), (d["period"] % 4).astype(int) + 1
    d["period_end"] = [pd.Timestamp(year=y, month=3 * q, day=1) + pd.offsets.MonthEnd(0) for y, q in zip(d["year"], d["q"])]
    d = d.sort_values("period_end").set_index("period_end")
    out = pd.DataFrame({"fish_yoy": 100 * (d["value"] / d["value"].shift(4) - 1)})
    out["available_from"] = out.index + pd.Timedelta(days=45)
    return out.dropna().reset_index()


def typhoon_tracks() -> pd.DataFrame:
    d = pd.read_csv(RAW / "ibtracs" / "ibtracs_calabarzon_600km.csv")
    d["t"] = pd.to_datetime(d["ISO_TIME"], errors="coerce")
    d["wind"] = pd.to_numeric(d["USA_WIND"], errors="coerce").fillna(pd.to_numeric(d["WMO_WIND"], errors="coerce"))
    near = np.zeros(len(d), bool)
    for lat, lon in CENTROIDS.values():
        near |= _haversine(d["LAT"].to_numpy(), d["LON"].to_numpy(), lat, lon) <= TC_RADIUS_KM
    return d[near][["SID", "t", "wind"]].dropna(subset=["t"])


def asof_extra(d: pd.Timestamp, issue_q_start: pd.Timestamp, cache: dict) -> dict:
    """All FI7 candidate government features as known at date d."""
    r = {}
    w = cache["world"][cache["world"]["available_from"] <= d]
    if len(w):
        for k in ["world_rice_yoy", "world_rice_3m", "world_urea_yoy"]:
            r[k] = float(w[k].iloc[-1])
    u = cache["under"][cache["under"]["available_from"] <= d]
    if len(u):
        r["underemp_rate"], r["underemp_yoy"] = float(u["underemp_rate"].iloc[-1]), float(u["underemp_yoy"].iloc[-1])
    f = cache["fish"][cache["fish"]["available_from"] <= d]
    if len(f):
        r["fish_yoy"] = float(f["fish_yoy"].iloc[-1])
    tc = cache["tc"]
    q = tc[(tc["t"] >= issue_q_start) & (tc["t"] <= d)]
    r["tc_max_wind_q"] = float(q["wind"].max()) if len(q) else 0.0
    y = tc[(tc["t"] > d - pd.DateOffset(years=1)) & (tc["t"] <= d)]
    r["typhoon_passages_4q"] = int(y[y["wind"] >= 64]["SID"].nunique())
    return r


def load_cache() -> dict:
    return {"world": world_prices(), "under": underemployment(), "fish": fisheries(), "tc": typhoon_tracks()}
