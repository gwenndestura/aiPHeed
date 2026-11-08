"""Objective 3: city/municipality priority rankings for all 142 CALABARZON LGUs.

The forecast is made where food insecurity is measured (Balance Luzon hunger, which covers all five provinces), so
every LGU starts from the same validated probability of above-normal hunger. The ranking then says where that risk
would weigh most, using two PSA-published vulnerability weights:

    poverty incidence (PSA 2021 city/municipal small-area estimates; Lucena City, a highly urbanised city that the
                       SAE table excludes, takes PSA's published 2021 HUC estimate, 10 %)
    population density (POPCEN 2024 population / land area, km2)

    V   = 0.5 * percentile_rank(poverty) + 0.5 * percentile_rank(density)       (0..1, within CALABARZON)
    priority score = 100 * P(HIGH) * V

Equal weights are a stated normative choice (no LGU-level food-insecurity outcome exists from which weights could
be estimated; equal weighting is the OECD/JRC composite-indicator default). The sensitivity table reports how much
the order moves under 0.7/0.3, 0.3/0.7, poverty-only and density-only weights. The LGU score is an estimated
priority ranking, not a municipal survey measurement of food insecurity.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from app.fi5.paths import LGU_POVERTY_SAE2021, LGU_REFERENCE

W_POVERTY, W_DENSITY = 0.5, 0.5
LUCENA = {"lgu_psgc": "045624000", "poverty_2021": 10.0,
          "source": "PSA OpenSTAT DB/1F/FY/0041F3DF02A (City of Lucena, 2021, published to whole percent)"}


def lgu_table() -> pd.DataFrame:
    l = pd.read_csv(LGU_REFERENCE, dtype={"lgu_psgc": str, "province_code": str})
    s = pd.read_csv(LGU_POVERTY_SAE2021, dtype={"lgu_code": str})
    t = l.merge(s[["lgu_code", "poverty_incidence_2021", "cv_2021"]], left_on="lgu_psgc", right_on="lgu_code", how="left")
    t["poverty_source"] = np.where(t["poverty_incidence_2021"].notna(), "PSA 2021 small-area estimate", None)
    m = t["lgu_psgc"] == LUCENA["lgu_psgc"]
    t.loc[m & t["poverty_incidence_2021"].isna(), ["poverty_incidence_2021", "poverty_source"]] = \
        [LUCENA["poverty_2021"], LUCENA["source"]]
    t["density_2024"] = t["population_2024"] / t["land_area_km2"]
    return t.drop(columns=["lgu_code"])


def vulnerability(t: pd.DataFrame, wp: float = W_POVERTY, wd: float = W_DENSITY) -> pd.Series:
    return wp * t["poverty_incidence_2021"].rank(pct=True) + wd * t["density_2024"].rank(pct=True)


def rank_lgus(p_high: float, forecast_meta: dict | None = None) -> pd.DataFrame:
    t = lgu_table()
    t["pct_poverty"] = t["poverty_incidence_2021"].rank(pct=True)
    t["pct_density"] = t["density_2024"].rank(pct=True)
    t["vulnerability"] = vulnerability(t)
    t["p_high_region"] = p_high
    t["priority_score"] = 100 * p_high * t["vulnerability"]
    t = t.sort_values(["priority_score", "poverty_incidence_2021"], ascending=False).reset_index(drop=True)
    t["rank"] = np.arange(1, len(t) + 1)
    t["priority_band"] = pd.cut(t["rank"], [0, len(t) / 3, 2 * len(t) / 3, len(t) + 1],
                                labels=["higher", "middle", "lower"]).astype(str)
    for k, v in (forecast_meta or {}).items():
        t[k] = v
    return t


def province_priority(t: pd.DataFrame) -> pd.DataFrame:
    g = t.groupby("province_name").apply(lambda d: pd.Series({
        "n_lgus": len(d), "population_2024": d["population_2024"].sum(),
        "vulnerability_popweighted": float(np.average(d["vulnerability"], weights=d["population_2024"])),
        "poverty_popweighted": float(np.average(d["poverty_incidence_2021"], weights=d["population_2024"])),
        "density_2024": d["population_2024"].sum() / d["land_area_km2"].sum(),
        "lgus_in_top_third": int((d["priority_band"] == "higher").sum())}), include_groups=False)
    g["p_high_region"] = t["p_high_region"].iloc[0]
    g["priority_score"] = 100 * g["p_high_region"] * g["vulnerability_popweighted"]
    return g.sort_values("priority_score", ascending=False).reset_index()


def sensitivity(t: pd.DataFrame) -> pd.DataFrame:
    base = t.set_index("lgu_psgc")["vulnerability"]
    top = set(base.sort_values(ascending=False).index[:47])
    rows = []
    for name, wp, wd in [("0.7 poverty / 0.3 density", .7, .3), ("0.3 poverty / 0.7 density", .3, .7),
                         ("poverty only", 1, 0), ("density only", 0, 1)]:
        alt = vulnerability(t.set_index("lgu_psgc"), wp, wd)
        rho = spearmanr(base, alt.reindex(base.index)).correlation
        alt_top = set(alt.sort_values(ascending=False).index[:47])
        rows.append({"weights": name, "spearman_vs_equal": round(float(rho), 3),
                     "top_third_changed": int(len(top - alt_top))})
    return pd.DataFrame(rows)
