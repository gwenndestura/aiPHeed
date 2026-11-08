"""FI6 features: 18 a-priori features built on FI5's as-of rows (same release-date rules, same no-future tests).

Each feature has a stated expected direction for the change in hunger; LightGBM is constrained to that direction
(+1 / -1), or left free (0) where the literature does not fix the sign.

    outcome     hunger_last (0), hunger_last_anom (-1: high readings tend to fall back), hunger_age_q (0)
    market      cpi_food_yoy (+1), cpi_rice_yoy (+1), palay_yoy (-1) | news_market (+1)
    climate     rain_anom_3m (0), tc_exposure_q (+1), oni (0)        | news_climate (+1)
    employment  unemp_rate (+1), unemp_yoy (+1)                       | news_employment (+1)
    remittance  remit_yoy (-1)                                        | news_remittance (+1)
    poverty     poverty_inc (+1)                                      | news_poverty (+1)

News composites: the mean of the available as-of z-scores of that domain's news signals (GDELT theme volume 2017+,
bias-corrected FSSI 2021+, and for poverty also the share of actual hunger reports). One composite per domain keeps
the feature count small. BERTopic topic shares stay an Objective 1 output and are not model inputs: they measure
how much a theme is covered, not whether conditions worsen, and FI5 found no gain from them.

Dropped from FI5 (a priori): cpi_food_rel and cpi_food_accel (derived from the CPI series already kept),
tmax_anom_3m (no established link to quarterly hunger in the reviewed studies), tc_exposure_4q (overlaps
tc_exposure_q and the latest hunger reading).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.fi5.features import FeatureBuilder
from app.fi5.target import q_end, qindex
from app.fi6.target import AREA, labels, quarterly

MONOTONE = {
    "hunger_last": 0, "hunger_last_anom": -1, "hunger_age_q": 0,
    "cpi_food_yoy": 1, "cpi_rice_yoy": 1, "palay_yoy": -1, "news_market": 1,
    "rain_anom_3m": 0, "tc_exposure_q": 1, "oni": 0, "news_climate": 1,
    "unemp_rate": 1, "unemp_yoy": 1, "news_employment": 1,
    "remit_yoy": -1, "news_remittance": 1,
    "poverty_inc": 1, "news_poverty": 1,
}
DOMAIN = {
    "hunger_last": "outcome", "hunger_last_anom": "outcome", "hunger_age_q": "outcome",
    "cpi_food_yoy": "market", "cpi_rice_yoy": "market", "palay_yoy": "market", "news_market": "market",
    "rain_anom_3m": "climate", "tc_exposure_q": "climate", "oni": "climate", "news_climate": "climate",
    "unemp_rate": "employment", "unemp_yoy": "employment", "news_employment": "employment",
    "remit_yoy": "remittance", "news_remittance": "remittance",
    "poverty_inc": "poverty", "news_poverty": "poverty",
}
NEWS_PARTS = {
    "news_market": ["gdelt_shortage", "gdelt_agri_supply", "fssi_market"],
    "news_climate": ["fssi_climate"],
    "news_employment": ["gdelt_jobs_income", "fssi_employment"],
    "news_remittance": ["fssi_remittance"],
    "news_poverty": ["gdelt_assistance", "fssi_poverty", "hunger_news_share"],
}
OUTCOME = ["hunger_last", "hunger_last_anom", "hunger_age_q"]
NEWS = list(NEWS_PARTS)
GOV = [f for f in MONOTONE if f not in OUTCOME and f not in NEWS]
ALL = list(MONOTONE)
SETS = {
    "full": ALL,
    "gov_only": OUTCOME + GOV,            # government indicators + latest reading (news removed)
    "psa_only": GOV,                      # baseline 2: government indicators only
    "nlp_only": NEWS,                     # baseline 3: news composites only
    **{f"minus_{n}": [f for f in ALL if f != n] for n in NEWS},
    **{f"minus_domain_{d}": [f for f in ALL if DOMAIN[f] != d] for d in ["market", "climate", "employment", "remittance", "poverty"]},
}
FIRST_ISSUE = "1999-Q1"


def design(lead: int, fb: FeatureBuilder | None = None, lab: pd.DataFrame | None = None) -> pd.DataFrame:
    fb = fb or FeatureBuilder()
    lab = labels() if lab is None else lab
    q = quarterly(AREA)
    last_target = int(lab["qi"].max())
    X = fb.matrix(lead, qindex(FIRST_ISSUE), last_target - lead)
    for k, parts in NEWS_PARTS.items():
        X[k] = X[parts].mean(axis=1, skipna=True)
    L = lab.set_index("quarter")
    X["tqi"] = X["target_quarter"].map(qindex)
    X["issue_ts"] = pd.to_datetime(X["issue_date"])
    for c, src in [("y", "y"), ("hunger_target", "hunger"), ("threshold_actual", "threshold"),
                   ("p_flip", "p_flip"), ("target_published", "published"), ("normal_actual", "normal")]:
        X[c] = X["target_quarter"].map(L[src]) if src in L else np.nan
    # Threshold as it can be known at the issue date: published-readings normal + the latest round's margin.
    moe_last = []
    for d in X["issue_ts"]:
        pub = q[q["published"] <= d]
        moe_last.append(float(pub["moe"].iloc[-1]) if len(pub) else np.nan)
    X["moe_last"] = moe_last
    X["threshold_known"] = X["baseline_known"] + X["moe_last"]
    X["delta_target"] = X["hunger_target"] - X["hunger_last"]
    return X


def live_row(issue_qi: int, lead: int, fb: FeatureBuilder | None = None) -> pd.DataFrame:
    fb = fb or FeatureBuilder()
    r = pd.DataFrame([fb.row(issue_qi, issue_qi + lead)])
    for k, parts in NEWS_PARTS.items():
        r[k] = r[[p for p in parts if p in r]].mean(axis=1, skipna=True) if any(p in r for p in parts) else np.nan
    for c in ALL:
        if c not in r:
            r[c] = np.nan
    q = quarterly(AREA)
    pub = q[q["published"] <= q_end(issue_qi)]
    r["moe_last"] = float(pub["moe"].iloc[-1])
    r["threshold_known"] = r["baseline_known"] + r["moe_last"]
    return r
