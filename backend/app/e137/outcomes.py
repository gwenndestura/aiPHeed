"""
E137 outcomes: HFIAS province-rounds with survey uncertainty (no quarterly label is created).

Audit (docs/e137/OUTCOME_AUDIT.md):
    * FNRI 2015 FSS and ENNS 2018/2019 both use HFIAS: 9 items, 30-day recall, FNRI scoring after Coates et al. 2007
      into secure / mild / moderate / severe. The unit is the household; the denominator is respondent households.
    * Moderate-or-severe = moderate + severe as printed. Its SE is not printed. 2015 (n printed): SE from the design
      effect, se = sqrt(deff x p(1-p)/n) with deff = the largest design effect implied by the three printed binary
      splits of the same province (secure, moderate, severe), capped at the conservative sum of the two printed SEs.
      ENNS (n not printed): the conservative sum of the two printed SEs (ignores their negative covariance: too wide,
      never too narrow).
    * 2015: SE printed (95 % CI). ENNS 2018 tables and 2019 decks: 90 % CI printed; SE = CI width / (2 x 1.645).
      Five 2019 decks print only the any-level headline: no moderate-or-severe value, so those rows are INSUFFICIENT.
    * The "Philippines" value printed in each ENNS provincial report is that round's own estimate (2018 subset 53.9 %
      any-level, 2019 subset 64.1 %), not the pooled rolling-survey national value (56.0 %). The pooled 2018-2019 value
      from FNRI's dissemination deck is the primary reference; the round-printed value is a sensitivity analysis.
    * HUCs and NCR towns are separate ENNS domains with no provincial predictors: excluded.

Target for each row:  y = logit(p_province) - logit(p_reference)   (relative logit, risk not prevalence)
                      se_y = se_p / (p (1 - p))                     (delta method; reference error added in quadrature)
Status:  ELEVATED  z >= 1.96 | LOWER  z <= -1.96 | NOT_DISTINGUISHABLE  |z| < 1.96 |
         INSUFFICIENT  no category breakdown, no printed interval, or 95 % half-width of p > 10 percentage points.
Soft label q = Phi(y / se_y) = probability that the true relative logit is above 0 given the survey.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

from app.hfias import CLEAN as HFIAS_CLEAN
from app.hfias.panel import SWS_AREA, ISLAND, norm as key

# FNRI 2018-2019 ENNS dissemination deck ("Proportion of households by food security status: Philippines, 2018-2019").
POOLED_ENNS = {"food_secure": 44.0, "mild": 13.3, "moderate": 29.8, "severe": 13.0}
REF_SE_PCT = 0.5          # national estimates (n > 20,000 households): SE about 0.5 pp; printed 0.5 for 2015 mod-sev
Z = 1.959964
MAX_HALF_WIDTH = 10.0
OUTCOMES = {"mod_sev": "moderate-or-severe (primary)", "insecure": "any level (secondary)"}
REGION_2015 = {}          # filled by load(): province key -> FNRI 2015 region


def _logit(p):
    p = np.clip(np.asarray(p, float) / 100, 1e-4, 1 - 1e-4)
    return np.log(p / (1 - p))


def _rel(p, se, ref, ref_se=REF_SE_PCT):
    p, se = np.asarray(p, float), np.asarray(se, float)
    pp, rr = p / 100, ref / 100
    y = _logit(p) - _logit(ref)
    se_y = np.sqrt((se / 100 / (pp * (1 - pp))) ** 2 + (ref_se / 100 / (rr * (1 - rr))) ** 2)
    return y, se_y


def status(y, se_y, half_width, has_value) -> np.ndarray:
    z = np.asarray(y) / np.asarray(se_y)
    out = np.where(z >= Z, "ELEVATED", np.where(z <= -Z, "LOWER", "NOT_DISTINGUISHABLE")).astype(object)
    bad = (~np.asarray(has_value, bool)) | ~np.isfinite(z) | (np.asarray(half_width, float) > MAX_HALF_WIDTH)
    out[bad] = "INSUFFICIENT"
    return out


def load(outcome: str = "mod_sev", reference: str = "pooled") -> pd.DataFrame:
    """One row per (province, survey). reference: 'pooled' (primary) or 'round' (ENNS round-printed national)."""
    f = pd.read_csv(HFIAS_CLEAN / "fnri2015_hfias.csv")
    nat15 = f[f["level"] == "national"].iloc[0]
    p15 = f[f["level"] == "province"].copy()
    p15["key"] = p15["name"].map(key)
    REGION_2015.update(dict(zip(p15["key"], p15["region"])))
    p15["insecure_se"] = p15["food_secure_se"]
    deff = pd.concat([p15[f"{c}_se"] ** 2 / (p15[f"{c}_pct"] * (100 - p15[f"{c}_pct"]) / p15["n"])
                      for c in ("food_secure", "moderate", "severe")], axis=1).max(axis=1)
    ms = p15["mod_sev_pct"]
    p15["mod_sev_se"] = np.minimum(np.sqrt(deff * ms * (100 - ms) / p15["n"]), p15["mod_sev_se"])
    rows = []
    ref15 = nat15[f"{outcome}_pct"]
    for _, r in p15.iterrows():
        p, se = r[f"{outcome}_pct"], r[f"{outcome}_se"]
        rows.append({"key": r["key"], "province": r["name"], "region": r["region"], "survey": "FNRI2015", "year": 2015,
                     "ref_quarter": "2015-Q3", "p": p, "se_p": se, "ref": ref15, "has_value": pd.notna(p) and pd.notna(se),
                     "se_imputed": False, "source": "FNRI 2015 FSS Appendices 1-4"})
    e = pd.read_csv(HFIAS_CLEAN / "enns_hfias.csv")
    e["key"] = e["area"].map(key)
    e = e[~e["key"].str.contains(r"\bcity\b") & ~e["key"].isin(["pateros"])].copy()
    e["insecure_se"] = e["food_secure_se"]
    pooled = {"mod_sev": POOLED_ENNS["moderate"] + POOLED_ENNS["severe"], "insecure": 100 - POOLED_ENNS["food_secure"]}
    e["ph_insecure_pct"] = 100 - e["ph_food_secure_pct"]
    for _, r in e.iterrows():
        p, se = r.get(f"{outcome}_pct"), r.get(f"{outcome}_se")
        ref = pooled[outcome] if reference == "pooled" else r.get(f"ph_{outcome}_pct")
        rows.append({"key": r["key"], "province": r["area"], "region": REGION_2015.get(r["key"]), "survey": f"ENNS{int(r['year'])}",
                     "year": int(r["year"]), "ref_quarter": f"{int(r['year'])}-Q3", "p": p, "se_p": se, "ref": ref,
                     "has_value": pd.notna(p) and pd.notna(se), "se_imputed": False, "source": r["file"]})
    d = pd.DataFrame(rows)
    d = d[d["region"].notna()].reset_index(drop=True)            # provinces created after 2015 have no region/predictors
    y, se_y = _rel(d["p"], d["se_p"], d["ref"].astype(float))
    d["y"], d["se_y"] = y, se_y
    d["half_width"] = Z * d["se_p"]
    d["status"] = status(d["y"], d["se_y"], d["half_width"], d["has_value"])
    d["q"] = np.where(d["has_value"] & np.isfinite(d["y"] / d["se_y"]), norm.cdf(d["y"] / d["se_y"]), np.nan)   # wide rows keep q
    d["sws_area"] = d["region"].map(SWS_AREA)
    d["island"] = d["sws_area"].map(ISLAND).where(d["region"].isin(["NCR", "CAR", "Ilocos", "Cagayan Valley", "Central Luzon",
                                                                       "CALABARZON", "MIMAROPA", "Bicol"]) | True)
    d["island"] = np.where(d["region"].isin(["Western Visayas", "Central Visayas", "Eastern Visayas"]), "Visayas",
                           np.where(d["sws_area"] == "mindanao", "Mindanao", "Luzon"))
    d["outcome"] = outcome
    d["reference"] = reference
    prev = d[d["survey"] == "FNRI2015"].set_index("key")
    d["prev_y"] = np.where(d["survey"] != "FNRI2015", d["key"].map(prev["y"]), np.nan)
    d["prev_se_y"] = np.where(d["survey"] != "FNRI2015", d["key"].map(prev["se_y"]), np.nan)
    return d


def summary(d: pd.DataFrame) -> pd.DataFrame:
    return d.groupby(["survey", "status"]).size().unstack(fill_value=0)
