"""
app/ml/inference/firi3.py
-------------------------
aiPHeed Food-Insecurity Risk Index, candidate version 3 (FIRI3), frozen in
aipheed-backend-aligned/experiments/E121_FIRI3_Implementation/E121_FIRI3_PROTOCOL.md (sha in PROTOCOL_SHA256).

A relative composite on a 0-1 scale (not a probability, not a validated provincial food-insecurity prediction) of
six indicators: FMA market affordability, AFP agricultural and fisheries production, CEC climate, EHS employment and
household economy, PSV poverty, FIS early-warning news. Level 1: each feature's as-of value at the issue date
(2021+ observations, availability date before the issue, at most 3 quarters old; change-type series only from
2022-Q1, so that every comparison base is 2021+: Amendment 1, E122), direction-aligned, scored by its
mid-rank percentile among earlier available observations (>= 8) or, for annual / structural features, by its mid-rank
among the five provinces. Level 2: features -> components (each counts once) -> indicator (>= half of components).
Level 3: equal-weighted mean of available indicators (provincial >= 4 of 6, regional >= 4 of 5); 0.5 = usual level;
chance bands. SWS hunger and FIRI v2 are never inputs; provincial scores use provincial observations only.

Independent of firi.py (FIRI v2, the served index). Pure computation: callers pass the observation tables.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

PROTOCOL_SHA256 = "8a431a9ddb1efc0515e1b539924562b65119649edf44dfac8e4c878c2bf4b717"
AMENDMENT_1_SHA256 = "4fd05309c3dee0800693e9a12b92ed112aebef35f9a219a8a620c88860050549"   # E122: change-type series need a 2021+ base
AMENDMENT_2_SHA256 = "8b5f729cc34790e00dbadbc5ce02bfd050ca31dc665fd049bff9e38675f7711b"   # E123: latest complete annual year; CCS / SVS / common core
VERSION = "FIRI3-candidate-1.2"
START_Q = 2021 * 4                      # 2021-Q1 as a quarter index (year * 4 + quarter - 1)
MIN_PRIOR = 8
MAX_STALE = 3
MIN_SHARE = 2 / 3
PROVINCES = ("Cavite", "Laguna", "Batangas", "Rizal", "Quezon")
REGIONAL_UNITS = ("Region IV-A", "CALABARZON (mean of 5 province points)", "PHILIPPINES")
REGION_LABEL = "CALABARZON (regional)"
FORBIDDEN = ("sws", "hunger", "h1_", "firi")      # target and index series are refused as inputs

INDICATORS = {
    "FMA": "Food Market Accessibility and Affordability",
    "AFP": "Agricultural and Fisheries Production",
    "CEC": "Climate and Environmental Conditions",
    "EHS": "Employment and Household Economic Stability",
    "PSV": "Household Poverty and Social Vulnerability",
    "FIS": "Food Insecurity Early-Warning Signals",
}


@dataclass(frozen=True)
class Feature:
    code: str
    indicator: str
    component: str
    scope: str              # "P" provincial, "R" regional
    series: str
    unit: str | None        # None: the province itself
    direction: int          # +1 higher = more risk, -1 lower = more risk
    transform: str          # "none" or "abs"
    normalization: str      # "pct" (expanding percentile) or "rank5" (cross-province mid-rank)
    dataset: str


_RA, _CP, _PH = "Region IV-A", "CALABARZON (mean of 5 province points)", "PHILIPPINES"
FEATURES = (
    Feature("FMA_food_cpi", "FMA", "food inflation", "P", "cpi_food_yoy_pct", None, 1, "none", "pct", "D01"),
    Feature("FMA_headline_cpi", "FMA", "cost of living", "P", "cpi_headline_yoy_pct", None, 1, "none", "pct", "D02"),
    Feature("FMA_rice_wholesale", "FMA", "rice price", "P", "rice_wholesale_yoy_pct", None, 1, "none", "pct", "D05"),
    Feature("FMA_chicken", "FMA", "protein prices", "P", "retail_chicken_yoy_pct", None, 1, "none", "pct", "D08"),
    Feature("FMA_pork", "FMA", "protein prices", "P", "retail_pork_yoy_pct", None, 1, "none", "pct", "D09"),
    Feature("FMA_tilapia", "FMA", "protein prices", "P", "retail_tilapia_yoy_pct", None, 1, "none", "pct", "D10"),
    Feature("FMA_food_cpi_R", "FMA", "food inflation", "R", "region_cpi_food_yoy_pct", _RA, 1, "none", "pct", "D03"),
    Feature("FMA_headline_cpi_R", "FMA", "cost of living", "R", "region_cpi_headline_yoy_pct", _RA, 1, "none", "pct", "D03"),
    Feature("FMA_rice_R", "FMA", "rice price", "R", "farmgate_palay_yoy_pct", _RA, 1, "none", "pct", "D07"),
    Feature("AFP_palay", "AFP", "cereals", "P", "palay_production_yoy_pct", None, -1, "none", "pct", "D20"),
    Feature("AFP_corn", "AFP", "cereals", "P", "corn_production_yoy_pct", None, -1, "none", "pct", "D21"),
    Feature("AFP_vegetables", "AFP", "vegetables", "P", "vegetables_only_production_yoy_pct", None, -1, "none", "pct", "D22"),
    Feature("AFP_rootcrops", "AFP", "root crops", "P", "rootcrops_only_production_yoy_pct", None, -1, "none", "pct", "D23"),
    Feature("AFP_fisheries", "AFP", "fisheries", "P", "fisheries_production_yoy_pct", None, -1, "none", "pct", "D24"),
    Feature("AFP_chicken", "AFP", "poultry and livestock", "P", "chicken_production_yoy_pct", None, -1, "none", "pct", "D26"),
    Feature("AFP_livestock", "AFP", "poultry and livestock", "P", "livestock_production_yoy_pct", None, -1, "none", "pct", "D27"),
    Feature("AFP_palay_R", "AFP", "cereals", "R", "palay_production_yoy_pct", _RA, -1, "none", "pct", "D20"),
    Feature("AFP_corn_R", "AFP", "cereals", "R", "corn_production_yoy_pct", _RA, -1, "none", "pct", "D21"),
    Feature("AFP_vegetables_R", "AFP", "vegetables", "R", "vegetables_only_production_yoy_pct", _RA, -1, "none", "pct", "D22"),
    Feature("AFP_rootcrops_R", "AFP", "root crops", "R", "rootcrops_only_production_yoy_pct", _RA, -1, "none", "pct", "D23"),
    Feature("AFP_fisheries_R", "AFP", "fisheries", "R", "fisheries_production_yoy_pct", _RA, -1, "none", "pct", "D24"),
    Feature("CEC_rain_departure", "CEC", "rainfall", "P", "rainfall_anomaly_mm", None, 1, "abs", "pct", "D36"),
    Feature("CEC_heat", "CEC", "temperature", "P", "temperature_anomaly_c", None, 1, "none", "pct", "D37"),
    Feature("CEC_cyclones_100km", "CEC", "cyclones", "P", "typhoons_local_100km", None, 1, "none", "pct", "D33"),
    Feature("CEC_rain_departure_R", "CEC", "rainfall", "R", "rainfall_anomaly_mm", _CP, 1, "abs", "pct", "D36"),
    Feature("CEC_heat_R", "CEC", "temperature", "R", "temperature_anomaly_c", _CP, 1, "none", "pct", "D37"),
    Feature("CEC_cyclones_R", "CEC", "cyclones", "R", "typhoons_PAR", _PH, 1, "none", "pct", "D34"),
    Feature("EHS_unemployment_prov", "EHS", "employment", "P", "provincial_unemployment_rate_pct_annual", None, 1, "none", "rank5", "D41"),
    Feature("EHS_underemployment_prov", "EHS", "employment", "P", "provincial_underemployment_rate_pct_annual", None, 1, "none", "rank5", "D41"),
    Feature("EHS_unemployment_change_R", "EHS", "employment", "R", "E1_unemployment_change_pp", _PH, 1, "none", "pct", "D40"),
    Feature("EHS_remittance_decline_R", "EHS", "remittances", "R", "E2_remittance_decline_pct", _PH, 1, "none", "pct", "D42"),
    Feature("PSV_poverty", "PSV", "poverty", "P", "poverty_incidence_popweighted_pct", None, 1, "none", "rank5", "D50"),
    Feature("FIS_fssi", "FIS", "local news", "P", "N1_fssi_v3", None, 1, "none", "pct", "D60"),
    Feature("FIS_shortage_news_R", "FIS", "national news", "R", "news_gdelt_shortage_share", _PH, 1, "none", "pct", "D62"),
)
LEVEL_SERIES = frozenset({"typhoons_local_100km", "typhoons_PAR", "N1_fssi_v3", "news_gdelt_shortage_share"})
# Amendment 1: every other scored dynamic series is a change against an earlier period (YoY, drop, pp change, anomaly
# vs earlier same-quarter years) and is admitted only when its base is inside the window: period >= 2022-Q1
BASE_REQUIRED = frozenset(f.series for f in FEATURES if f.normalization == "pct" and f.series not in LEVEL_SERIES)
FIRST_CHANGE_Q = START_Q + 4
EXCLUDED = {
    "cpi_bottom30_food_yoy_pct": "alternative: r 0.94 with CPI food",
    "retail_rice_regular_yoy_pct": "alternative: r 0.86 with wholesale rice",
    "farmgate_palay_yoy_pct (provincial)": "alternative: r 0.79 with wholesale rice",
    "retail vegetable / root-crop prices": "profile: unrelated, volatile items; no basket weights",
    "farmgate_hog_yoy_pct": "profile: producer-side price",
    "aquaculture_production_yoy_pct": "alternative: part of the fisheries total",
    "C2_typhoons_300km": "alternative: identical across provinces in 64% of quarters",
    "rainfall_total_mm": "alternative: the departure is derived from it",
    "oni_quarter_mean / C1_el_nino_in_force": "context: national/global, direction ambiguous",
    "unemployment_rate_pct": "alternative: the change is scored",
    "news_gdelt_agri_supply_share": "alternative: r 0.93 with the shortage share",
    "news_gdelt_jobs_income_share / news_gdelt_assistance_share": "context: direction not established",
    "N1_admitted_articles": "context: FSSI coverage",
    "subsistence_incidence_pct": "profile: 9 of 10 provincial CVs > 20%",
    "fies_food_share_of_expenditure_pct": "profile: publication date unknown",
    "density": "context: urban market dependence, not deprivation",
    "SWS Balance Luzon hunger": "target: never a FIRI3 input",
    "FIRI v2 / A1 price-pressure probability": "excluded: index / model output",
}


# ------------------------------------------------------------------------------------------------ helpers
def qlabel(t: int) -> str:
    return f"{t // 4}-Q{t % 4 + 1}"


def qindex(label: str) -> int:
    return int(label[:4]) * 4 + int(label[-1]) - 1


def issue_date(t: int) -> str:
    """O(t): the first day of the quarter after origin t."""
    n = t + 1
    return date(n // 4, (n % 4) * 3 + 1, 1).isoformat()


def components(indicator: str, scope: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(f.component for f in FEATURES if f.indicator == indicator and f.scope == scope))


def indicators(scope: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(f.indicator for f in FEATURES if f.scope == scope))


def chance_sd(k: int) -> float:
    return math.sqrt(1 / 12) / math.sqrt(max(k, 1))


def band(score: float | None, k: int) -> str:
    if score is None or (isinstance(score, float) and math.isnan(score)):
        return "not_computable"
    sd = chance_sd(k)
    if score < 0.5:
        return "usual or below"
    if score < 0.5 + sd:
        return "above usual"
    if score < 0.5 + 1.645 * sd:
        return "elevated"
    return "high"


def midrank(x: float, prior: np.ndarray) -> float:
    return float(((prior < x).sum() + 0.5 * (prior == x).sum()) / len(prior))


# ------------------------------------------------------------------------------------------------ input validation
def validate_inputs(obs: pd.DataFrame, ann: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Refuse target / index series; reject pre-2021 rows; check geography. Returns cleaned tables and a log."""
    for name, d in (("observations", obs), ("annual", ann)):
        bad = [s for s in d["feature"].astype(str).unique() if any(k in s.lower() for k in FORBIDDEN)]
        if bad:
            raise ValueError(f"{name}: target or index series refused as FIRI3 input: {bad}")
    prov_series = {f.series for f in FEATURES if f.scope == "P"}
    po = obs[obs["feature"].isin(prov_series) & ~obs["unit"].isin(REGIONAL_UNITS)]       # geography first: a wrong unit always stops the run
    if not set(po["unit"]) <= set(PROVINCES):
        raise ValueError(f"unknown provincial units: {sorted(set(po['unit']) - set(PROVINCES))}")
    log = {"pre2021_rows_rejected": int((obs["period"] < START_Q).sum())}
    obs = obs[obs["period"] >= START_Q]
    base = obs["feature"].isin(BASE_REQUIRED) & (obs["period"] < FIRST_CHANGE_Q)            # Amendment 1: pre-2021 comparison base
    log["pre2021_base_rows_rejected"] = int(base.sum())
    log["pre2021_base_rows_by_series"] = {k: int(v) for k, v in obs.loc[base, "feature"].value_counts().items()}
    obs = obs[~base]
    ref = pd.to_numeric(ann["ref"].astype(str).str[:4], errors="coerce")
    log["pre2021_annual_rows_rejected"] = int((ref < 2021).sum())
    ann = ann[ref >= 2021]
    used = {f.series for f in FEATURES}
    if not set(ann["unit"]) <= set(PROVINCES):
        raise ValueError("annual inputs must be provincial")
    log["series_used"] = sorted(used & set(obs["feature"]) | used & set(ann["feature"]))
    return obs, ann, log


# ------------------------------------------------------------------------------------------------ Level 1
def _dynamic(obs: pd.DataFrame, f: Feature, t: int) -> list[dict]:
    iss = issue_date(t)
    units = PROVINCES if f.scope == "P" else (f.unit,)
    s = obs[(obs["feature"] == f.series) & obs["unit"].isin(units) & (obs["avail"].astype(str) < iss)].copy()
    s["x"] = f.direction * (s["value"].abs() if f.transform == "abs" else s["value"])
    out = []
    for u in units:
        su = s[s["unit"] == u]
        rec = {"unit": u, "raw_value": None, "aligned_value": None, "period": None, "avail_date": None, "status": "missing",
               "prior_n": 0, "score": None, "source": None}
        if not su.empty:
            cur = su.iloc[int(np.argmax(su["period"].to_numpy()))]               # first latest row by position (index labels may repeat)
            rec.update(raw_value=float(cur["value"]), aligned_value=float(cur["x"]), period=qlabel(int(cur["period"])), avail_date=str(cur["avail"]),
                       source=cur.get("source"))
            prior = s.loc[s["period"] < cur["period"], "x"].dropna().to_numpy()
            rec["prior_n"] = int(len(prior))
            if t - int(cur["period"]) > MAX_STALE:
                rec["status"] = "stale"
            elif len(prior) < MIN_PRIOR:
                rec["status"] = "insufficient_history"
            else:
                rec.update(status=str(cur["status"]), score=midrank(float(cur["x"]), prior))
        out.append(rec)
    return out


def _rank5(ann: pd.DataFrame, f: Feature, t: int) -> list[dict]:
    iss = issue_date(t)
    a = ann[(ann["feature"] == f.series) & (ann["avail"].astype(str) < iss)]
    base = {"aligned_value": None, "raw_value": None, "period": None, "avail_date": None, "prior_n": None, "score": None, "source": None}
    if a.empty:
        return [{**base, "unit": u, "status": "unavailable_at_issue"} for u in PROVINCES]
    years = a.groupby(a["ref"].astype(str))["unit"].agg(lambda s: set(s.dropna()) >= set(PROVINCES))
    complete = sorted(y for y, ok in years.items() if ok)
    if not complete:                                    # Amendment 2: no complete published year at the issue
        return [{**base, "unit": u, "period": max(years.index), "status": "incomplete_year"} for u in PROVINCES]
    ref = complete[-1]                                  # latest COMPLETE published year; newer incomplete years skipped
    skipped = sorted(y for y in years.index if y > ref)
    a = a[a["ref"].astype(str) == ref].set_index("unit")
    x = f.direction * a["value"]
    rk = x.rank(method="average")
    return [{"unit": u, "raw_value": float(a.loc[u, "value"]), "aligned_value": float(x[u]), "period": ref, "avail_date": str(a.loc[u, "avail"]),
             "status": str(a.loc[u, "status"]), "prior_n": None, "score": float((rk[u] - 0.5) / 5), "source": a.loc[u].get("source"),
             "note": f"newer incomplete year(s) skipped: {', '.join(skipped)}" if skipped else ""} for u in PROVINCES]


def feature_scores(obs: pd.DataFrame, ann: pd.DataFrame, origins, drop_features=()) -> pd.DataFrame:
    rows = []
    for t in origins:
        for f in FEATURES:
            if f.code in drop_features:
                continue
            for r in (_rank5(ann, f, t) if f.normalization == "rank5" else _dynamic(obs, f, t)):
                rows.append({"origin": qlabel(t), "t": t, "issue_date": issue_date(t), "scope": "provincial" if f.scope == "P" else "regional",
                             "unit": r.pop("unit") if f.scope == "P" else REGION_LABEL, "series_unit": f.unit or "province", **{k: v for k, v in r.items() if k != "unit"},
                             "feature": f.code, "series": f.series, "indicator": f.indicator, "component": f.component, "direction": f.direction,
                             "transform": f.transform, "normalization": f.normalization, "dataset": f.dataset})
    out = pd.DataFrame(rows)
    out["score"] = pd.to_numeric(out["score"], errors="coerce")
    return out


# ------------------------------------------------------------------------------------------------ Level 2
def indicator_scores(fs: pd.DataFrame, drop_features=()) -> pd.DataFrame:
    s = fs[~fs["feature"].isin(drop_features)]
    comp = s.groupby(["scope", "unit", "t", "indicator", "component"], sort=True).agg(
        score=("score", "mean"), features_scored=("score", lambda v: int(v.notna().sum())), features_defined=("score", "size")).reset_index()
    rows = []
    for (sc, u, t, i), g in comp.groupby(["scope", "unit", "t", "indicator"], sort=True):
        ncomp = len([c for c in components(i, "P" if sc == "provincial" else "R")
                     if not all(f.code in drop_features for f in FEATURES if f.indicator == i and f.component == c and f.scope == ("P" if sc == "provincial" else "R"))])
        got = g[g["score"].notna()]
        ok = len(got) >= math.ceil(ncomp / 2) and len(got) > 0
        rows.append({"scope": sc, "unit": u, "t": t, "origin": qlabel(t), "indicator": i, "score": float(got["score"].mean()) if ok else None,
                     "available": ok, "components_available": int(len(got)), "components_defined": ncomp,
                     "features_scored": int(g["features_scored"].sum()), "features_defined": int(g["features_defined"].sum()),
                     "component_scores": {c: (None if pd.isna(v) else round(float(v), 10)) for c, v in zip(g["component"], g["score"])}})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ Level 3
def overall(ind: pd.DataFrame, fs: pd.DataFrame | None = None, weights: dict | None = None, drop_indicators=()) -> pd.DataFrame:
    rows = []
    d = ind[~ind["indicator"].isin(drop_indicators)]
    for (sc, u, t), g in d.groupby(["scope", "unit", "t"], sort=True):
        defined = [i for i in indicators("P" if sc == "provincial" else "R") if i not in drop_indicators]
        need = math.ceil(MIN_SHARE * len(defined))
        a = g[g["available"]]
        rec = {"scope": sc, "unit": u, "t": t, "origin": qlabel(t), "issue_date": issue_date(t), "indicators_defined": len(defined),
               "indicators_available": int(len(a)), "indicators_used": " ".join(a["indicator"]),
               "indicators_missing": " ".join(i for i in defined if i not in set(a["indicator"])), "firi3": None, "band": "not_computable",
               "status": "not_computable", "loo_min": None, "loo_max": None, "verification_share": None, "contributing_features": ""}
        if len(a) >= need:
            w = np.array([(weights or {}).get(i, 1.0) for i in a["indicator"]], float)
            sc_ = a["score"].to_numpy(float)
            val = float((w * sc_).sum() / w.sum())
            loo = [float(np.delete(sc_, j).mean()) for j in range(len(sc_))] if len(sc_) >= 2 else []
            rec.update(firi3=val, band=band(val, len(a)), status="computed", loo_min=min(loo) if loo else None, loo_max=max(loo) if loo else None)
            if fs is not None:
                c = fs[(fs["scope"] == sc) & (fs["unit"] == u) & (fs["t"] == t) & fs["indicator"].isin(a["indicator"]) & fs["score"].notna()]
                rec["verification_share"] = round(float((c["status"] == "verified").mean()), 4) if len(c) else None
                rec["contributing_features"] = " ".join(c["feature"])
        rows.append(rec)
    return pd.DataFrame(rows)


def compute(obs: pd.DataFrame, ann: pd.DataFrame, origins) -> dict:
    """Full FIRI3 for the given origins: {'features', 'indicators', 'overall', 'log'}."""
    obs, ann, log = validate_inputs(obs, ann)
    fs = feature_scores(obs, ann, origins)
    ind = indicator_scores(fs)
    return {"features": fs, "indicators": ind, "overall": overall(ind, fs), "log": log}


# ------------------------------------------------------------------------------------------------ Amendment 2: supplementary scores
CONDITIONS = ("FMA", "AFP", "CEC", "FIS")
STRUCTURAL = ("EHS", "PSV")
CORE = ("FMA", "AFP", "CEC", "EHS")


def subscore(ind: pd.DataFrame, members: tuple, name: str, scopes=("provincial", "regional")) -> pd.DataFrame:
    """Equal mean of the available member indicators; needs ceil(2/3 x defined members). Defined members per scope:
    CCS = FMA AFP CEC FIS in both scopes; SVS = EHS PSV, provincial only (regional EHS is national shocks, not structure)."""
    rows = []
    for (sc, u, t), g in ind.groupby(["scope", "unit", "t"], sort=True):
        defined = [i for i in members if i in indicators("P" if sc == "provincial" else "R")]
        if name == "SVS" and sc == "regional":
            defined = []
        rec = {"scope": sc, "unit": u, "t": t, "origin": qlabel(t), "issue_date": issue_date(t), "score_name": name, "members_defined": " ".join(defined)}
        if sc not in scopes or not defined:
            rows.append({**rec, "score": None, "members_available": 0, "members_used": "", "members_missing": "", "status": "not_defined", "band": None})
            continue
        a = g[g["indicator"].isin(defined) & g["available"]]
        need = math.ceil(MIN_SHARE * len(defined))
        ok = len(a) >= need
        val = float(a["score"].mean()) if ok else None
        rows.append({**rec, "score": val, "members_available": int(len(a)), "members_used": " ".join(a["indicator"]),
                     "members_missing": " ".join(i for i in defined if i not in set(a["indicator"])),
                     "status": "computed" if ok else "not_computable",
                     "band": (band(val, len(a)) if name == "CCS" else ("above provincial middle" if val > 0.5 else "at or below provincial middle")) if ok else None})
    return pd.DataFrame(rows)


def common_core(ind: pd.DataFrame, overall_df: pd.DataFrame) -> pd.DataFrame:
    """Fixed core (FMA AFP CEC EHS, all four required) and the per-origin cross-province core (indicators available for
    all five provinces; >= 3), beside the overall FIRI3. Missing indicators are never filled."""
    rows = []
    av = ind[ind["available"]]
    for (sc, u, t), g in ind.groupby(["scope", "unit", "t"], sort=True):
        s = g[g["available"]].set_index("indicator")["score"]
        fixed = float(s[list(CORE)].mean()) if set(CORE) <= set(s.index) else None
        rec = {"scope": sc, "unit": u, "t": t, "origin": qlabel(t), "fixed_core": fixed, "fixed_core_status": "computed" if fixed is not None else "core_incomplete",
               "fixed_core_missing": " ".join(i for i in CORE if i not in set(s.index))}
        if sc == "provincial":
            sets = [set(av[(av["scope"] == sc) & (av["t"] == t) & (av["unit"] == p)]["indicator"]) for p in PROVINCES]
            inter = sorted(set.intersection(*sets)) if all(sets) else []
            ok = len(inter) >= 3
            rec.update(cross_core_indicators=" ".join(inter), cross_core=float(s[inter].mean()) if ok else None,
                       cross_core_status="computed" if ok else "comparison_not_possible")
        else:
            rec.update(cross_core_indicators="", cross_core=None, cross_core_status="not_applicable (one regional unit)")
        rows.append(rec)
    cc = pd.DataFrame(rows)
    o = overall_df[["scope", "unit", "t", "firi3", "indicators_available", "indicators_used"]]
    return o.merge(cc, on=["scope", "unit", "t"], how="right")
