"""E120: offline computation of the proposed consolidated FIRI (six indicators) for review. No model is trained.

Level 1 features (as of each issue, 2021+ only) -> direction-aligned expanding-window percentiles (dynamic) or
cross-province mid-ranks (annual / structural) -> Level 2 component and indicator scores -> Level 3 FIRI.
Provincial FIRI uses provincial observations only; regional FIRI uses Region IV-A / Balance Luzon / national series.
Inputs are read only (E118, E119, E119-R2 helpers, firi.py, the served FIRI v2 history for comparison).

    python e120.py
"""
from __future__ import annotations

import hashlib
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
REPO = EXP.parent.parent
sys.path.insert(0, str(EXP / "E119R2_Indicator_Framework_Redesign" / "runner"))
import analyze as R2     # noqa: E402  (E119-R2 loaders, which use the E119 helpers)

P, FI = R2.P, R2.FI
PROVS = P.PROVS
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
ORIGINS = list(range(P.START_Q, 2026 * 4 + 3))          # 2021-Q1 .. 2026-Q3
MIN_PRIOR = 8                                           # as FIRI v2
MAX_STALE = 3                                           # quarters between origin and observed quarter (normal lag 1-2)

INDICATORS = {
    "FMA": "Food Market Accessibility and Affordability",
    "AFP": "Agricultural and Fisheries Production",
    "CEC": "Climate and Environmental Conditions",
    "EHS": "Employment and Household Economic Stability",
    "PSV": "Household Poverty and Social Vulnerability",
    "FIS": "Food Insecurity Early-Warning Signals",
}

# Level 1 features scored in the FIRI.
#   code, indicator, component, scope (P provincial / R regional), series feature, series unit (None = the province),
#   direction (+1 higher = more risk, -1 lower = more risk), transform, normalization, dataset id (E119-R2), note
F = [
    # FMA: price pressure on household purchasing power (structural affordability is PSV)
    ("FMA_food_cpi", "FMA", "food inflation", "P", "cpi_food_yoy_pct", None, 1, "none", "pct", "D01", "PSA-published provincial CPI food YoY"),
    ("FMA_headline_cpi", "FMA", "cost of living", "P", "cpi_headline_yoy_pct", None, 1, "none", "pct", "D02", "headline CPI YoY (non-food costs also squeeze food budgets)"),
    ("FMA_rice_wholesale", "FMA", "rice price", "P", "rice_wholesale_yoy_pct", None, 1, "none", "pct", "D05", "primary rice series; retail (r 0.86) and farmgate (r 0.79) are alternatives"),
    ("FMA_chicken", "FMA", "protein prices", "P", "retail_chicken_yoy_pct", None, 1, "none", "pct", "D08", "retail broiler"),
    ("FMA_pork", "FMA", "protein prices", "P", "retail_pork_yoy_pct", None, 1, "none", "pct", "D09", "retail pork kasim"),
    ("FMA_tilapia", "FMA", "protein prices", "P", "retail_tilapia_yoy_pct", None, 1, "none", "pct", "D10", "retail tilapia"),
    ("FMA_food_cpi_R", "FMA", "food inflation", "R", "region_cpi_food_yoy_pct", "Region IV-A", 1, "none", "pct", "D03", "Region IV-A CPI food YoY (from 2021+ index)"),
    ("FMA_headline_cpi_R", "FMA", "cost of living", "R", "region_cpi_headline_yoy_pct", "Region IV-A", 1, "none", "pct", "D03", "Region IV-A headline YoY"),
    ("FMA_rice_R", "FMA", "rice price", "R", "farmgate_palay_yoy_pct", "Region IV-A", 1, "none", "pct", "D07", "only rice price with a Region IV-A row (r 0.79 with wholesale)"),
    # AFP: lower production = more risk
    ("AFP_palay", "AFP", "cereals", "P", "palay_production_yoy_pct", None, -1, "none", "pct", "D20", "palay production YoY"),
    ("AFP_corn", "AFP", "cereals", "P", "corn_production_yoy_pct", None, -1, "none", "pct", "D21", "corn production YoY (small bases: rank-based score limits extremes)"),
    ("AFP_vegetables", "AFP", "vegetables", "P", "vegetables_only_production_yoy_pct", None, -1, "none", "pct", "D22", "non-root vegetables YoY"),
    ("AFP_rootcrops", "AFP", "root crops", "P", "rootcrops_only_production_yoy_pct", None, -1, "none", "pct", "D23", "root and tuber crops YoY"),
    ("AFP_fisheries", "AFP", "fisheries", "P", "fisheries_production_yoy_pct", None, -1, "none", "pct", "D24", "total fisheries YoY (aquaculture is part of it)"),
    ("AFP_chicken", "AFP", "poultry and livestock", "P", "chicken_production_yoy_pct", None, -1, "none", "pct", "D26", "from 2024 (series start 2023)"),
    ("AFP_livestock", "AFP", "poultry and livestock", "P", "livestock_production_yoy_pct", None, -1, "none", "pct", "D27", "from 2024 (series start 2023)"),
    ("AFP_palay_R", "AFP", "cereals", "R", "palay_production_yoy_pct", "Region IV-A", -1, "none", "pct", "D20", "Region IV-A"),
    ("AFP_corn_R", "AFP", "cereals", "R", "corn_production_yoy_pct", "Region IV-A", -1, "none", "pct", "D21", "Region IV-A"),
    ("AFP_vegetables_R", "AFP", "vegetables", "R", "vegetables_only_production_yoy_pct", "Region IV-A", -1, "none", "pct", "D22", "Region IV-A"),
    ("AFP_rootcrops_R", "AFP", "root crops", "R", "rootcrops_only_production_yoy_pct", "Region IV-A", -1, "none", "pct", "D23", "Region IV-A"),
    ("AFP_fisheries_R", "AFP", "fisheries", "R", "fisheries_production_yoy_pct", "Region IV-A", -1, "none", "pct", "D24", "Region IV-A"),
    # CEC: exposure; rainfall departures in either direction (drought or flood) = more risk
    ("CEC_rain_departure", "CEC", "rainfall", "P", "rainfall_anomaly_mm", None, 1, "abs", "pct", "D36", "|quarterly rainfall - mean of the same quarter in earlier 2021+ years|"),
    ("CEC_heat", "CEC", "temperature", "P", "temperature_anomaly_c", None, 1, "none", "pct", "D37", "temperature above the earlier same-quarter mean"),
    ("CEC_cyclones_100km", "CEC", "cyclones", "P", "typhoons_local_100km", None, 1, "none", "pct", "D33", "province-specific cyclone exposure (verified)"),
    ("CEC_rain_departure_R", "CEC", "rainfall", "R", "rainfall_anomaly_mm", "CALABARZON (mean of 5 province points)", 1, "abs", "pct", "D36", "regional proxy"),
    ("CEC_heat_R", "CEC", "temperature", "R", "temperature_anomaly_c", "CALABARZON (mean of 5 province points)", 1, "none", "pct", "D37", "regional proxy"),
    ("CEC_cyclones_R", "CEC", "cyclones", "R", "typhoons_PAR", "PHILIPPINES", 1, "none", "pct", "D34", "cyclones in PAR (verified)"),
    # EHS
    ("EHS_unemployment_prov", "EHS", "employment", "P", "provincial_unemployment_rate_pct_annual", None, 1, "none", "rank5", "D41", "latest published annual rate (year shown); not spread into quarters"),
    ("EHS_underemployment_prov", "EHS", "employment", "P", "provincial_underemployment_rate_pct_annual", None, 1, "none", "rank5", "D41", "latest published annual rate"),
    ("EHS_unemployment_change_R", "EHS", "employment", "R", "E1_unemployment_change_pp", "PHILIPPINES", 1, "none", "pct", "D40", "national (regional FIRI only)"),
    ("EHS_remittance_decline_R", "EHS", "remittances", "R", "E2_remittance_decline_pct", "PHILIPPINES", 1, "none", "pct", "D42", "national (regional FIRI only)"),
    # PSV (provincial, structural): cross-province mid-rank of the latest published value
    ("PSV_poverty", "PSV", "poverty", "P", "poverty_incidence_popweighted_pct", None, 1, "none", "rank5", "D50", "SAE 2021, population-weighted mean of LGU estimates; available from 2025-07-01 (V1 rule)"),
    # FIS
    ("FIS_fssi", "FIS", "local news", "P", "N1_fssi_v3", None, 1, "none", "pct", "D60", "needs >= 5 admitted articles in the quarter"),
    ("FIS_shortage_news_R", "FIS", "national news", "R", "news_gdelt_shortage_share", "PHILIPPINES", 1, "none", "pct", "D62", "primary of the shortage / agri-supply pair (r 0.93)"),
]
# Level 1 features kept in the indicators but NOT scored (profile, context or alternative), with the reason
NOT_SCORED = [
    ("PSV_subsistence", "PSV", "food poverty", "P", "subsistence_incidence_pct", "D52", "profile",
     "9 of 10 provincial estimates have CV > 20% (only Quezon 2021, 17.4%); ranks reverse between 2021 and 2023 (rank r = -0.82): too imprecise to rank provinces"),
    ("PSV_fies_food_share", "PSV", "food expenditure", "P", "fies_food_share_of_expenditure_pct", "D53", "profile",
     "FIES 2023 food share (all, bottom 30%): publication date not in the file, so it cannot be dated before an issue; profile until the date is verified"),
    ("PSV_density", "PSV", "density", "P", "density_per_km2", "D51", "context", "measures urban market dependence, not deprivation (rank r -0.40 with food share)"),
    ("FMA_bottom30_cpi", "FMA", "food inflation", "P", "cpi_bottom30_food_yoy_pct", "D04", "alternative", "r 0.94 with CPI food: same signal"),
    ("FMA_retail_rice", "FMA", "rice price", "P", "retail_rice_regular_yoy_pct", "D06", "alternative", "r 0.86 with wholesale rice"),
    ("FMA_farmgate_palay", "FMA", "rice price", "P", "farmgate_palay_yoy_pct", "D07", "alternative", "r 0.79 with wholesale rice (used as the regional rice series)"),
    ("FMA_vegetable_prices", "FMA", "vegetable prices", "P", "retail_tomato/cabbage/cassava/carrot_yoy_pct", "D11/D12", "profile",
     "items unrelated to each other (cassava vs carrot r 0.00) and volatile; a basket needs weights not available"),
    ("FMA_farmgate_hog", "FMA", "producer prices", "P", "farmgate_hog_yoy_pct", "D13", "profile", "producer-side; r 0.58 with retail pork"),
    ("AFP_aquaculture", "AFP", "fisheries", "P", "aquaculture_production_yoy_pct", "D25", "alternative", "part of the fisheries total (30-65%)"),
    ("CEC_cyclones_300km", "CEC", "cyclones", "P", "C2_typhoons_300km", "D32", "alternative", "identical across the five provinces in 64% of quarters; 100 km count used"),
    ("CEC_rain_total", "CEC", "rainfall", "P", "rainfall_total_mm", "D35", "alternative", "the departure is derived from it (r 0.59)"),
    ("CEC_enso", "CEC", "ENSO", "R", "oni_quarter_mean / C1_el_nino_in_force", "D30/D31", "context",
     "national/global; direction ambiguous (El Nino drought vs La Nina flood); about no effect (E65)"),
    ("EHS_unemployment_rate_R", "EHS", "employment", "R", "unemployment_rate_pct", "D40", "alternative", "level; the change (E1) is scored"),
    ("FIS_agri_supply_news", "FIS", "national news", "R", "news_gdelt_agri_supply_share", "D62", "alternative", "r 0.93 with the shortage share"),
    ("FIS_jobs_income_news", "FIS", "national news", "R", "news_gdelt_jobs_income_share", "D62", "context", "direction not established; r -0.88 with the unemployment change (shared trend)"),
    ("FIS_assistance_news", "FIS", "national news", "R", "news_gdelt_assistance_share", "D62", "context", "assistance news may mean relief as well as need: direction not established"),
    ("FIS_article_count", "FIS", "local news", "P", "N1_admitted_articles", "D61", "context", "coverage measure for FSSI"),
    ("SWS_hunger", "outside FIRI", "outcome", "R", "SWS Balance Luzon total hunger", "D70", "target",
     "the regional forecasting target: not a FIRI input (it would make the index partly the outcome it is checked against); shown beside the FIRI as observed regional hunger"),
    ("FIRI_v2_A1", "outside FIRI", "model output", "P", "LightGBM price-pressure probability", "D16", "excluded", "a model forecast, not an observation"),
]
FEAT = pd.DataFrame(F, columns=["feature", "indicator", "component", "scope", "series", "series_unit", "direction", "transform", "normalization", "dataset_id", "note"])


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ inputs
def load():
    L = pd.concat([R2.e119_long(), R2.extra_series()])
    assert (L["period"] >= P.START_Q).all()
    A = pd.read_csv(R2.E119 / "E119_PROVINCIAL_ANNUAL_INDICATORS.csv")
    vul = pd.read_csv(P.INPUTS["vuln"])
    vul = vul[vul["poverty_lgu_estimate"].notna()]
    pov = vul.groupby("province").apply(lambda g: float(np.average(g["poverty_lgu_estimate"], weights=g["population_2024"])), include_groups=False)
    ann = []
    for f in ("provincial_unemployment_rate_pct_annual", "provincial_underemployment_rate_pct_annual"):
        for r in A[A["feature"] == f].itertuples():
            ann.append({"feature": f, "unit": r.province, "ref": str(r.reference_year), "value": r.value, "avail": f"{int(r.reference_year) + 1}-06-30",
                        "status": "rule_unverified"})
    for r in A[A["feature"] == "subsistence_incidence_pct"].itertuples():
        ann.append({"feature": "subsistence_incidence_pct", "unit": r.province, "ref": str(r.reference_year), "value": r.value, "avail": r.published, "status": "verified"})
    for p, v in pov.items():
        ann.append({"feature": "poverty_incidence_popweighted_pct", "unit": p, "ref": "2021", "value": v, "avail": FI.V_AVAILABLE_FROM, "status": "verified"})
    return L, pd.DataFrame(ann)


def issue(t: int) -> str:
    return P.qstart(t + 1).isoformat()


# ------------------------------------------------------------------------------------------------ Level 1
def asof_dynamic(L, f, t):
    """Feature f at origin t for every unit in its scope: latest observed quarter available before the issue, its
    direction-aligned value, and the percentile among earlier available observations (pooled over the scope's units)."""
    iss = issue(t)
    units = PROVS if f.scope == "P" else [f.series_unit]
    s = L[(L["feature"] == f.series) & L["unit"].isin(units) & (L["avail"].astype(str) < iss)].copy()
    s["x"] = f.direction * (s["value"].abs() if f.transform == "abs" else s["value"])
    out = {}
    for u in units:
        su = s[s["unit"] == u]
        if su.empty:
            out[u] = {"x": None, "period": None, "score": None, "status": "missing"}
            continue
        cur = su.loc[su["period"].idxmax()]
        if t - int(cur["period"]) > MAX_STALE:
            out[u] = {"x": float(cur["x"]), "period": P.qs(int(cur["period"])), "score": None, "status": "stale"}
            continue
        prior = s[s["period"] < cur["period"]]["x"].dropna().to_numpy()   # earlier observations, all units in scope
        if len(prior) < MIN_PRIOR:
            out[u] = {"x": float(cur["x"]), "period": P.qs(int(cur["period"])), "score": None, "status": "insufficient_history"}
            continue
        x = float(cur["x"])
        sc = ((prior < x).sum() + 0.5 * (prior == x).sum()) / len(prior)
        out[u] = {"x": x, "period": P.qs(int(cur["period"])), "score": float(sc), "status": cur["status"]}
    return out


def asof_rank5(ann, f, t):
    """Annual / structural feature: the latest reference year published before the issue, scored by its mid-rank among
    the five provinces for that year: (rank - 0.5) / 5 in {0.1, 0.3, 0.5, 0.7, 0.9}."""
    iss = issue(t)
    a = ann[(ann["feature"] == f.series) & (ann["avail"].astype(str) < iss)]
    if a.empty:
        return {u: {"x": None, "period": None, "score": None, "status": "unavailable_at_issue"} for u in PROVS}
    ref = a["ref"].max()
    a = a[a["ref"] == ref].set_index("unit")
    if set(a.index) != set(PROVS):
        return {u: {"x": None, "period": ref, "score": None, "status": "incomplete_year"} for u in PROVS}
    x = f.direction * a["value"]
    rk = x.rank(method="average")
    return {u: {"x": float(x[u]), "period": ref, "score": float((rk[u] - 0.5) / 5), "status": a.loc[u, "status"]} for u in PROVS}


def level1(L, ann):
    rows = []
    for t in ORIGINS:
        for f in FEAT.itertuples():
            res = asof_rank5(ann, f, t) if f.normalization == "rank5" else asof_dynamic(L, f, t)
            for u, r in res.items():
                rows.append({"origin": P.qs(t), "t": t, "issue_date": issue(t), "scope": "provincial" if f.scope == "P" else "regional",
                             "unit": u if f.scope == "P" else "CALABARZON (regional)", "feature": f.feature, "indicator": f.indicator,
                             "component": f.component, **r})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------------------ Level 2 and 3
def indicator_scores(S1, drop_features=()):
    s = S1[~S1["feature"].isin(drop_features)]
    comp = s.groupby(["scope", "unit", "t", "indicator", "component"])["score"].mean().reset_index()   # mean of available feature scores
    ncomp = FEAT[~FEAT["feature"].isin(drop_features)].assign(scope=lambda d: d["scope"].map({"P": "provincial", "R": "regional"})).groupby(
        ["scope", "indicator"])["component"].nunique()
    g = comp.groupby(["scope", "unit", "t", "indicator"])
    ind = g["score"].agg(["mean", "count"]).reset_index().rename(columns={"mean": "score", "count": "components_available"})
    ind["components_total"] = [ncomp.get((sc, i), 0) for sc, i in zip(ind["scope"], ind["indicator"])]
    ind["available"] = ind["components_available"] >= np.ceil(ind["components_total"] / 2)
    ind.loc[~ind["available"], "score"] = np.nan
    return ind


def firi(ind, weights=None, min_share=2 / 3, drop_indicators=()):
    """Weighted mean of the available indicator scores; weights renormalized over the available ones; needs at least
    ceil(2/3 of the indicators defined for the scope) (provincial 4 of 6, regional 4 of 5)."""
    d = ind[~ind["indicator"].isin(drop_indicators)]
    out = []
    for (sc, u, t), g in d.groupby(["scope", "unit", "t"]):
        total = d[d["scope"] == sc]["indicator"].nunique()
        a = g[g["available"] & g["score"].notna()]
        need = math.ceil(min_share * total)
        if len(a) < need:
            out.append({"scope": sc, "unit": u, "t": t, "firi": np.nan, "indicators_available": len(a), "indicators_total": total})
            continue
        w = np.array([(weights or {}).get(i, 1.0) for i in a["indicator"]], float)
        w = w / w.sum()
        out.append({"scope": sc, "unit": u, "t": t, "firi": float((w * a["score"]).sum()), "indicators_available": len(a), "indicators_total": total})
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------ analysis
def compare(base, alt, label):
    m = base.merge(alt, on=["scope", "unit", "t"], suffixes=("", "_alt")).dropna(subset=["firi", "firi_alt"])
    rk = []
    for (sc, t), g in m[m["scope"] == "provincial"].groupby(["scope", "t"]):
        if len(g) == 5 and g["firi"].nunique() > 1 and g["firi_alt"].nunique() > 1:
            rk.append(g["firi"].corr(g["firi_alt"], method="spearman"))
    return {"variant": label, "rows": int(len(m)), "mean_abs_change": round(float((m["firi"] - m["firi_alt"]).abs().mean()), 4),
            "max_abs_change": round(float((m["firi"] - m["firi_alt"]).abs().max()), 4),
            "class_flip_pct": round(100 * float(((m["firi"] >= .5) != (m["firi_alt"] >= .5)).mean()), 1),
            "province_rank_spearman_mean": round(float(np.mean(rk)), 3) if rk else None}


def main():
    inputs = sorted([*R2.E118C.glob("*.csv"), *(R2.E119 / "out" / "indicators").glob("*/observations_clean.csv"), R2.E119 / "E119_PROVINCIAL_ANNUAL_INDICATORS.csv",
                     P.INPUTS["vuln"], REPO / "backend" / "data" / "thesis" / "firi2_history.csv", REPO / "backend" / "app" / "ml" / "inference" / "firi.py"])
    before = {str(p.relative_to(REPO)): sha(p) for p in inputs}
    L, ann = load()
    S1 = level1(L, ann)
    IND = indicator_scores(S1)
    W1 = firi(IND)
    S1.to_csv(OUT / "level1_feature_scores.csv", index=False, lineterminator="\n", float_format="%.6g")
    IND.to_csv(OUT / "level2_indicator_scores.csv", index=False, lineterminator="\n", float_format="%.6g")
    W1.to_csv(OUT / "level3_firi_equal.csv", index=False, lineterminator="\n", float_format="%.6g")

    # ---------------- weighting alternatives
    pv = IND.pivot_table(index=["scope", "unit", "t"], columns="indicator", values="score")
    alts = {}
    # W2 component-count weights (each component one vote)
    FP_ = FEAT[FEAT["scope"] == "P"]                                   # provincial definitions (sensitivity is read on provincial rows)
    alts["W2 component-count"] = FP_.groupby("indicator")["component"].nunique().to_dict()
    # W3 feature-count weights (each feature one vote, FIRI v2 style counting)
    alts["W3 feature-count"] = FP_.groupby("indicator")["feature"].count().to_dict()
    # W4 redundancy-adjusted (FIRI v2 C2 rule, full-period Spearman of provincial indicator scores; descriptive)
    pc = pv.loc["provincial"].corr(method="spearman")
    alts["W4 redundancy-adjusted"] = {d: 1 / (1 + sum(max(0, pc.loc[d, e]) for e in pc.columns if e != d and not np.isnan(pc.loc[d, e]))) for d in pc.columns}
    # W5 first principal component of provincial indicator scores (complete rows; descriptive)
    pp = pv.loc["provincial"]
    cc = pp[[c for c in pp.columns if pp[c].notna().mean() >= .3]].dropna()      # FIS (FSSI) too sparse for complete rows
    if len(cc) >= 10:
        ev, evec = np.linalg.eigh(cc.corr().to_numpy())
        v = np.abs(evec[:, -1])
        alts["W5 PCA first component"] = {**dict(zip(cc.columns, v / v.sum())), **{c: 1 / len(cc.columns) for c in pp.columns if c not in cc.columns}}
        pca_info = {"rows": int(len(cc)), "explained_share_pc1": round(float(ev[-1] / ev.sum()), 3), "loadings": dict(zip(cc.columns, evec[:, -1].round(3).tolist()))}
    else:
        pca_info = {"rows": int(len(cc))}
    sens = [compare(W1, firi(IND, w), k) for k, w in alts.items()]
    # random weights (Dirichlet) to bound sensitivity
    rng = np.random.default_rng(120)
    rnd = [compare(W1, firi(IND, dict(zip(INDICATORS, rng.dirichlet(np.ones(6))))), "random") for _ in range(200)]
    sens.append({"variant": "W6 random Dirichlet(1) weights, 200 draws (median)", "rows": rnd[0]["rows"],
                 **{k: float(np.median([r[k] for r in rnd if r[k] is not None])) for k in ("mean_abs_change", "max_abs_change", "class_flip_pct", "province_rank_spearman_mean")}})
    # leave-one-indicator-out and leave-one-feature-out
    loio = [compare(W1, firi(IND, drop_indicators=(i,)), f"without indicator {i}") for i in INDICATORS]
    lofo = []
    for f in FEAT["feature"]:
        alt = firi(indicator_scores(S1, drop_features=(f,)))
        lofo.append({**compare(W1, alt, f"without feature {f}"), "indicator": FEAT.set_index("feature").loc[f, "indicator"]})
    # indicator score change when one of its features is removed
    ind_change = []
    for f in FEAT.itertuples():
        a = indicator_scores(S1, drop_features=(f.feature,))
        sc_ = "provincial" if f.scope == "P" else "regional"
        base_i = IND[(IND["indicator"] == f.indicator) & (IND["scope"] == sc_)]
        m = base_i.merge(a[(a["indicator"] == f.indicator) & (a["scope"] == sc_)], on=["scope", "unit", "t", "indicator"], how="left", suffixes=("", "_alt"))
        m = m.dropna(subset=["score"])
        ind_change.append({"feature": f.feature, "indicator": f.indicator, "scope": sc_, "rows": int(len(m)),
                           "indicator_becomes_unavailable_pct": round(100 * float(m["score_alt"].isna().mean()), 1) if len(m) else None,
                           "mean_abs_indicator_change": round(float((m["score"] - m["score_alt"]).abs().mean()), 4) if m["score_alt"].notna().any() else None})
    pd.DataFrame(sens + loio + lofo).to_csv(OUT / "sensitivity.csv", index=False, lineterminator="\n")
    pd.DataFrame(ind_change).to_csv(OUT / "indicator_feature_removal.csv", index=False, lineterminator="\n")

    # ---------------- coverage
    cov = []
    for (sc, i), g in IND.groupby(["scope", "indicator"]):
        n_units = 5 if sc == "provincial" else 1
        cov.append({"scope": sc, "indicator": i, "name": INDICATORS[i], "unit_origins_possible": n_units * len(ORIGINS),
                    "available": int(g["available"].sum()), "available_pct": round(100 * float(g["available"].sum()) / (n_units * len(ORIGINS)), 1),
                    "first_available": P.qs(int(g.loc[g["available"], "t"].min())) if g["available"].any() else "",
                    "provinces_with_any": int(g.loc[g["available"], "unit"].nunique()) if sc == "provincial" else None})
    for sc in ("provincial", "regional"):
        w = W1[W1["scope"] == sc]
        n_units = 5 if sc == "provincial" else 1
        cov.append({"scope": sc, "indicator": "FIRI", "name": "overall (equal weights, >= 2/3 of indicators)", "unit_origins_possible": n_units * len(ORIGINS),
                    "available": int(w["firi"].notna().sum()), "available_pct": round(100 * float(w["firi"].notna().sum()) / (n_units * len(ORIGINS)), 1),
                    "first_available": P.qs(int(w.loc[w["firi"].notna(), "t"].min())) if w["firi"].notna().any() else "", "provinces_with_any": None})
    COV = pd.DataFrame(cov)
    fcov = S1.groupby(["scope", "feature"]).agg(rows=("status", "size"), scored=("score", lambda s: int(s.notna().sum())),
                                                 statuses=("status", lambda s: "; ".join(f"{k}: {v}" for k, v in s.value_counts().items()))).reset_index()
    fcov["scored_pct"] = (100 * fcov["scored"] / fcov["rows"]).round(1)

    # ---------------- redundancy between indicator scores and between features within indicators
    ind_corr = {sc: pv.loc[sc].corr(method="spearman").round(3) for sc in ("provincial", "regional")}
    fw = S1.pivot_table(index=["scope", "unit", "t"], columns="feature", values="score")
    within = []
    for i in INDICATORS:
        for sc, tag in (("provincial", "P"), ("regional", "R")):
            fs = FEAT[(FEAT["indicator"] == i) & (FEAT["scope"] == tag)]["feature"].tolist()
            if sc not in fw.index.get_level_values(0):
                continue
            X = fw.loc[sc][[c for c in fs if c in fw.columns]]
            for a, b in itertools.combinations(X.columns, 2):
                d = X[[a, b]].dropna()
                within.append({"scope": sc, "indicator": i, "a": a, "b": b, "n": len(d),
                               "spearman": round(float(d[a].corr(d[b], method="spearman")), 3) if len(d) >= 8 else None})
    pd.DataFrame(within).to_csv(OUT / "within_indicator_feature_correlation.csv", index=False, lineterminator="\n")
    for sc, c in ind_corr.items():
        c.to_csv(OUT / f"indicator_score_correlation_{sc}.csv", lineterminator="\n")

    # ---------------- stability, province consistency, distribution
    stab = []
    for (sc, u), g in W1.dropna(subset=["firi"]).sort_values("t").groupby(["scope", "unit"]):
        x = g.set_index("t")["firi"]
        consecutive = x[x.index.to_series().diff() == 1]
        dif = x.diff()[x.index.to_series().diff() == 1].abs()
        stab.append({"scope": sc, "unit": u, "quarters": int(len(x)), "mean": round(float(x.mean()), 3), "sd": round(float(x.std()), 3),
                     "mean_abs_quarter_change": round(float(dif.mean()), 3) if len(dif) else None,
                     "lag1_autocorrelation": round(float(x.autocorr()), 3) if len(x) > 3 else None, "share_ge_0_5": round(float((x >= .5).mean()), 3)})
    STAB = pd.DataFrame(stab)
    dist = W1.dropna(subset=["firi"]).groupby("scope")["firi"].describe(percentiles=[.1, .25, .5, .75, .9]).round(3)
    # chance bands: if every available indicator sat at a random typical level (uniform score), the mean of k scores has
    # sd = sqrt(1/12)/sqrt(k); "above usual" from 0.5, "elevated" beyond +1 sd, "high" beyond +1.645 sd (one-sided 5%)
    W1["sd_chance"] = np.sqrt(1 / 12) / np.sqrt(W1["indicators_available"].clip(lower=1))
    W1["band"] = np.where(W1["firi"].isna(), "not computable", np.where(W1["firi"] >= .5 + 1.645 * W1["sd_chance"], "high",
                          np.where(W1["firi"] >= .5 + W1["sd_chance"], "elevated", np.where(W1["firi"] >= .5, "above usual", "usual or below"))))
    bands = W1.groupby(["scope", "band"]).size().unstack(fill_value=0)
    W1.to_csv(OUT / "level3_firi_equal.csv", index=False, lineterminator="\n", float_format="%.6g")
    prov_means = IND[IND["scope"] == "provincial"].pivot_table(index="unit", columns="indicator", values="score", aggfunc="mean").round(3)
    prov_means["FIRI"] = W1[W1["scope"] == "provincial"].groupby("unit")["firi"].mean().round(3)
    prov_means.to_csv(OUT / "province_mean_scores.csv", lineterminator="\n")

    # ---------------- comparison with served FIRI v2 (history), provincial rows only
    h = pd.read_csv(REPO / "backend" / "data" / "thesis" / "firi2_history.csv")
    h = h[h["FIRI"].notna()].copy()
    h["t"] = h["origin_quarter"].map(lambda s: int(s[:4]) * 4 + int(s[-1]) - 1)
    h["unit"] = h["province_code"].map(FI.PROVINCES)
    m = W1[W1["scope"] == "provincial"].merge(h[["t", "unit", "FIRI", "class"]], on=["t", "unit"]).dropna(subset=["firi"])
    v2cmp = {"rows": int(len(m)), "spearman": round(float(m["firi"].corr(m["FIRI"], method="spearman")), 3) if len(m) > 5 else None,
             "class_agreement_pct": round(100 * float(((m["firi"] >= .5) == (m["class"] == "HIGH")).mean()), 1) if len(m) else None,
             "share_high_v2": round(float((m["class"] == "HIGH").mean()), 3) if len(m) else None,
             "share_ge_0_5_new": round(float((m["firi"] >= .5).mean()), 3) if len(m) else None,
             "v2_history_rows_total": int(len(h)), "v2_kinds": h["kind"].value_counts().to_dict()}
    rk = []
    for t, g in m.groupby("t"):
        if len(g) == 5 and g["firi"].nunique() > 1 and g["FIRI"].nunique() > 1:
            rk.append(g["firi"].corr(g["FIRI"], method="spearman"))
    v2cmp["province_rank_spearman_mean"] = round(float(np.mean(rk)), 3) if rk else None
    v2cmp["quarters_compared"] = int(m["t"].nunique())

    after = {k: sha(REPO / k) for k in before}
    assert before == after, "an input changed"
    summary = {"inputs_sha256": before, "pca": pca_info, "weights": {k: {i: round(float(x), 4) for i, x in w.items()} for k, w in alts.items()},
               "distribution": dist.to_dict(), "bands": bands.to_dict(), "v2_comparison": v2cmp, "level1_rows": len(S1)}
    json.dump(summary, open(OUT / "summary.json", "w"), indent=1, default=float)
    COV.to_csv(OUT / "indicator_coverage.csv", index=False, lineterminator="\n")
    fcov.to_csv(OUT / "feature_coverage.csv", index=False, lineterminator="\n")
    STAB.to_csv(OUT / "stability.csv", index=False, lineterminator="\n")
    pd.set_option("display.width", 250)
    print(COV.to_string()); print(fcov.to_string()); print(pd.DataFrame(sens + loio).to_string())
    print(pd.DataFrame(lofo).sort_values("mean_abs_change", ascending=False).head(10).to_string())
    print(pd.DataFrame(ind_change).to_string())
    for sc, c in ind_corr.items():
        print(sc); print(c.to_string())
    print(STAB.to_string()); print(dist.to_string()); print(bands.to_string()); print(prov_means.to_string()); print(json.dumps(v2cmp, indent=1)); print(json.dumps(pca_info, indent=1))
    print(json.dumps(summary["weights"], indent=1))


if __name__ == "__main__":
    main()
