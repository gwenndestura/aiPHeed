"""E85 GDELT features (PROTOCOL section 3): theme-family shares, volume, tone and affected counts per region and per
province, for quarter t using only records dated before O(t) - 1 day."""
from __future__ import annotations

import math
import re
from pathlib import Path

import numpy as np
import pandas as pd

RAW = Path(__file__).resolve().parents[4] / "backend" / "data" / "gdelt_e85" / "gkg_calabarzon_2021_2026.parquet"
FAMILIES = {
    "PRICE": r"ECON_INFLATION|ECON_PRICE|TAX_FOODSTAPLES|FOOD_STAPLE|SHORTAGE",
    "FOODSEC": r"FOOD_SECURITY|HUNGER|MALNUTRITION|FAMINE",
    "DISASTER": r"NATURAL_DISASTER|FLOOD|TYPHOON|STORM|DROUGHT|EL_NINO",
    "AGRI": r"AGRICULTURE|CROP|FISH",
    "LIVELIHOOD": r"UNEMPLOY|POVERTY|REMITTANCE",
    "RESPONSE": r"(?<![A-Z])AID|RELIEF|HUMANITARIAN",
}
PROV = {"PH040100000": r"Cavite", "PH040200000": r"Laguna", "PH040300000": r"Quezon Province|Lucena|, Quezon, Philippines",
        "PH040400000": r"Rizal", "PH040500000": r"Batangas"}
KAPPA = 20.0
SEVERE_COUNTS = re.compile(r"(?:^|;)(AFFECT|EVACUATION|KILL)#(\d+)#")


def load() -> pd.DataFrame:
    d = pd.read_parquet(RAW)
    d["ts"] = pd.to_datetime(d["DATE"].astype(str), format="%Y%m%d%H%M%S") + pd.Timedelta(hours=8)   # UTC -> PHT
    d = d.sort_values("ts").drop_duplicates("DocumentIdentifier", keep="first")
    assert d["ts"].min() >= pd.Timestamp("2021-01-01")
    d["q"] = d["ts"].dt.year * 4 + (d["ts"].dt.month - 1) // 3
    th = d["V2Themes"].fillna("")
    for f, pat in FAMILIES.items():
        d[f] = th.str.contains(pat, regex=True).astype(int)
    d["tone"] = pd.to_numeric(d["V2Tone"].fillna("").str.split(",").str[0], errors="coerce")
    d["affected"] = d["V2Counts"].fillna("").map(lambda s: sum(int(n) for _, n in SEVERE_COUNTS.findall(s)))
    loc = d["V2Locations"].fillna("")
    for p, pat in PROV.items():
        hit = loc.str.contains(pat, regex=True)
        if p == "PH040300000":
            hit &= ~loc.str.contains("Quezon City", regex=False) | loc.str.contains("Quezon Province|Lucena", regex=True)
        d[p] = hit.astype(int)
    return d


def _agg(g: pd.DataFrame) -> dict:
    n = len(g)
    out = {"n": n}
    for f in FAMILIES:
        out[f"share_{f}"] = float(g[f].mean()) if n else np.nan
    sub = g[(g["DISASTER"] + g["FOODSEC"] + g["PRICE"]) > 0]
    out["tone"] = float(sub["tone"].mean()) if len(sub) else np.nan
    out["affected"] = math.log1p(float(g["affected"].sum()))
    return out


def features(d: pd.DataFrame, origins: list[int], origin_of) -> pd.DataFrame:
    """One row per (t, province): regional g_* (same for all provinces) and province gp_* shrunk to the region."""
    rows = []
    for t in origins:
        cut = origin_of(t) - pd.Timedelta(days=1)
        cur = d[(d["q"] == t) & (d["ts"] < cut)]
        prev = d[(d["q"] == t - 1) & (d["ts"] < cut)]
        R, R1 = _agg(cur), _agg(prev)
        base = {"t": t, "g_logn": math.log1p(R["n"]), "g_tone": R["tone"], "g_affected": R["affected"]}
        for f in FAMILIES:
            base[f"g_share_{f}"] = R[f"share_{f}"]
            base[f"g_d_{f}"] = R[f"share_{f}"] - R1[f"share_{f}"] if R["n"] and R1["n"] else np.nan
        for p in PROV:
            P = _agg(cur[cur[p] == 1])
            r = {**base, "province_code": p, "gp_logn": math.log1p(P["n"])}
            for f in FAMILIES:
                rv, pv = R[f"share_{f}"], P[f"share_{f}"]
                r[f"gp_share_{f}"] = (P["n"] * (pv if P["n"] else 0.0) + KAPPA * rv) / (P["n"] + KAPPA) if pd.notna(rv) else np.nan
            rows.append(r)
    return pd.DataFrame(rows)


G_REGIONAL = ["g_logn", "g_tone", "g_affected"] + [f"g_share_{f}" for f in FAMILIES] + [f"g_d_{f}" for f in FAMILIES]
G_PROVINCE = ["gp_logn"] + [f"gp_share_{f}" for f in FAMILIES]
