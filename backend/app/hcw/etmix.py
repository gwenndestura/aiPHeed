"""
FINAL-ETMIX: the primary research forecasting model (elapsed-time mixture of FINAL). EXPERIMENTAL. NOT THE PRODUCTION MODEL.

Research record: research_notes/aiPHeed_final_7of7_20261113 (FINAL_7_OF_7_IMPROVEMENT_PROTOCOL.md, sha256 a365da1f...; prospective
seal for ENNS 2022: evidence/sealed_enns2022_final_mix.json, sha256 71ebe142...) and research_notes/aiPHeed_final_etmix_20261113
(lead-time, baseline and contributor evidence). E196 stays the production model; this module is not imported by
app.ml.inference.map_engine, the registry or the public routes, and its API (app/api/v1/etmix.py) needs an admin login.

Model (no parameter is estimated from any outcome beyond FINAL's own training-fold procedure):
  * one FINAL fit (app.hcw.final_engine: RATE + MIND, per-fold input selection, three survey anchors, 0.5 cut-off)
  * the fitted model predicts every test row twice, under the two elapsed-time hypotheses that fit all training rows equally:
        g = quarters since the province's OWN latest survey (FINAL)
        s = quarters since the latest RELEASED survey round (FINAL-ET), released = reference quarter + 6 quarters <= origin
    (in every training row g == s, so the data cannot choose between them)
  * p = (p_g + p_s) / 2 ; HIGH when p >= 0.50 ; five seeds (168, 1, 2, 3, 4) averaged
Explanations: exact additive LightGBM contributions (pred_contrib) of the rate model x elapsed time, on the forecast-logit
scale, averaged over the two hypotheses and five seeds. They add up exactly to (forecast logit - survey anchor). They are
model attributions, not causal effects.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.hcw import engine as H
from app.hcw import final_engine as FE

VERSION = "final-etmix-1.0-experimental"
MODEL_ID = VERSION
STATUS = ("experimental research model: retrospective walk-forward results on 72 reused province-rounds only; "
          "no independent validation yet (sealed ENNS 2022 forecasts, sha256 71ebe142, not yet scorable); "
          "not approved for serving; E196 remains production")
SEEDS = H.SEEDS
RQ = {"NNS2013": 8054, "FNRI2015": 8062, "ENNS2018": 8074, "ENNS2019": 8078, "ENNS2021": 8086}   # survey reference quarters (year*4+q-1)
RELEASE_LAG_Q = 6
P_HIGH = 0.50


def stale_q(origin_i: int, target_t: int) -> int:
    """s: target quarter minus the reference quarter of the latest survey round released by the origin."""
    rel = [q for q in RQ.values() if q + RELEASE_LAG_Q <= origin_i]
    if not rel:
        raise ValueError(f"no survey round released by origin {origin_i}")
    return int(target_t - max(rel))


# --------------------------------------------------------------------------------- contributor groups (meaning-based)
def group(c: str) -> str:
    """Meaning-based group of a FINAL candidate input (identical to research_notes/aiPHeed_final_7of7_20261113/scripts/ablation.py)."""
    c = c[3:] if c.startswith("mi_") else c
    if c in ("gap_q", "lead"):
        return "timing"
    if c in ("hh_grdp_g", "hh_grdp_rel", "income_growth", "income_rel"):
        return "regional_accounts"
    if c in ("p_poverty", "p_poverty_gap", "p_subsistence", "p_density"):
        return "poverty_vulnerability"
    if c.startswith(("cpi_", "l_fg", "l_rice", "l_terms")):
        return "market_prices"
    if c.startswith(("c_rain", "c_soil", "c_tc", "rain_", "soil_", "tc_", "vu_")) or c == "oni":
        return "climate"
    if c.startswith("unemp"):
        return "employment"
    if c.startswith(("ag_", "agri_", "c_agri", "l_fish")):
        return "agri_fish_production"
    return "news_nlp"


# Dashboard tiers come from the contributor evidence (FINAL_ETMIX_CONTRIBUTOR_IMPORTANCE_REPORT.md); see DISPLAY_GROUPS.
DISPLAY_GROUPS = {
    "regional_accounts": {"name": "Regional economy (GRDP and household income)", "tier": "core", "resolution": "Region (same value for all five CALABARZON provinces)",
                          "source": "PSA Regional Accounts (GRDP per capita, constant prices); PSA FIES regional income", "regional": True},
    "market_prices": {"name": "Food prices and inflation", "tier": "core", "resolution": "Province (CPI and wholesale/farmgate prices)",
                      "source": "PSA provincial CPI; PSA wholesale and farmgate price surveys", "regional": False},
    "poverty_vulnerability": {"name": "Poverty and social vulnerability", "tier": "supporting", "resolution": "Province",
                              "source": "PSA official poverty statistics (poverty incidence, gap, subsistence); PSA POPCEN density", "regional": False},
    "agri_fish_production": {"name": "Agriculture and fish production", "tier": "supporting", "resolution": "Province",
                             "source": "PSA OpenSTAT palay, corn and fisheries production; farm prices", "regional": False},
    "climate": {"name": "Climate and typhoon exposure", "tier": "contextual", "resolution": "Province (ONI is global)",
                "source": "NASA POWER rainfall/soil moisture; NOAA IBTrACS; NOAA ONI", "regional": False},
    "employment": {"name": "Employment", "tier": "contextual", "resolution": "National/regional before 2022 (provincial LFS only from 2022)",
                   "source": "PSA Labor Force Survey", "regional": True},
    "news_nlp": {"name": "News signals (NLP Food Stress Sentiment Index)", "tier": "contextual", "resolution": "Province with area/national fallback",
                 "source": "aiPHeed news corpus (XLM-RoBERTa zero-shot events, BERTopic topics)", "regional": False},
}
STRUCTURAL = {"anchor": "Latest provincial survey level (FNRI HFIAS, survey anchor)", "timing": "Time since the survey anchor",
              "trend": "Average change since the survey (model baseline rate x elapsed time)"}


# --------------------------------------------------------------------------------------------------------- the model
def fit_predict(tr: pd.DataFrame, te: pd.DataFrame, AN: dict, seed: int) -> dict:
    """One seed of FINAL-ETMIX. tr/te/AN as for app.hcw.final_engine.fit_predict; te must carry 'i' (origin) and 'T' (target).
    Returns p (mixture), p_g, p_s, mu_g, mu_s, half_g, half_s, s, the per-input mixed contributions and the FINAL config."""
    te = te.reset_index(drop=True)
    s = np.array([stale_q(int(i), int(t)) for i, t in zip(te["i"], te["T"])])
    te_s = te.assign(gap_q=s.astype(te["gap_q"].dtype))
    n = len(te)
    T2 = pd.concat([te, te_s], ignore_index=True)
    AN2 = {a: (AN[a][0], np.tile(np.asarray(AN[a][1]), 2)) for a in H.ANC}
    r = FE.fit_predict(tr, T2, AN2, seed)
    C, cols = r["model"].contributions(r["te"])          # (2n, k+1): inputs then bias, logit scale, already x elapsed time
    Cg, Cs = C[:n], C[n:]
    anchor = np.asarray(AN2[r["anchor"]][1], float)[:n]
    return {"p": 0.5 * (r["p"][:n] + r["p"][n:]), "p_g": r["p"][:n], "p_s": r["p"][n:], "mu_g": r["mu"][:n], "mu_s": r["mu"][n:],
            "half_g": r["half"][:n], "half_s": r["half"][n:], "s": s, "g": te["gap_q"].values.astype(int), "anchor_logit": anchor,
            "contrib": 0.5 * (Cg[:, :-1] + Cs[:, :-1]), "bias": 0.5 * (Cg[:, -1] + Cs[:, -1]), "cols": cols, "cfg": r["cfg"], "anchor": r["anchor"],
            "X": r["te"].iloc[:n].reset_index(drop=True), "version": VERSION, "status": STATUS, "missing_flags": r["missing_flags"]}


def group_contributions(contrib: np.ndarray, cols: list[str], bias: np.ndarray) -> pd.DataFrame:
    """Per-row group sums of the exact contributions; 'trend' = model bias term x elapsed time. Rows add to mu - anchor."""
    out = {g: np.zeros(contrib.shape[0]) for g in list(DISPLAY_GROUPS) + ["timing"]}
    for j, c in enumerate(cols):
        out[group(c)] += contrib[:, j]
    out["trend"] = np.asarray(bias, float)
    return pd.DataFrame(out)
