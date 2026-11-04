"""
Municipal and city vulnerability-weighted priority ranking (Objective 3), from a province-level P(HIGH) by target quarter.

    priority = province P(HIGH) x vulnerability
    vulnerability = 0.6 x poverty percentile + 0.4 x density percentile        (PSA SAE 2021, POPCEN 2024; 142 LGUs)

The poverty and density columns and the 0.6/0.4 weights follow the recorded owner decision (Option A, branch aiPHeed/cb6-fixes).
This ranks LGUs inside a province-level forecast. It is a prioritisation, not a municipal food-insecurity measurement or forecast.
"""
from __future__ import annotations

import pandas as pd

from app.paths import BACKEND_DIR

BASE = BACKEND_DIR / "data" / "e143" / "out" / "issue" / "lgus_next_quarter.csv"
W_POVERTY, W_DENSITY = 0.6, 0.4
LABEL = "LGU vulnerability-weighted priority; not a municipal food-insecurity measurement or forecast"


def rank(province_p: dict[str, float], target_quarter: str) -> pd.DataFrame:
    d = pd.read_csv(BASE)[["province_name", "lgu_psgc", "lgu_name", "lgu_type", "population_2024", "poverty_incidence_2021", "density_2024", "pct_poverty", "pct_density"]].copy()
    d["vulnerability"] = W_POVERTY * d["pct_poverty"] + W_DENSITY * d["pct_density"]
    d["province_p_high"] = d["province_name"].map(province_p)
    d["priority_score"] = d["province_p_high"] * d["vulnerability"]
    d["priority_rank_in_region"] = d["priority_score"].rank(ascending=False, method="first").astype(int)
    d["priority_rank_in_province"] = d.groupby("province_name")["priority_score"].rank(ascending=False, method="first").astype(int)
    d["target_quarter"], d["label"] = target_quarter, LABEL
    return d.sort_values("priority_rank_in_region").reset_index(drop=True)
