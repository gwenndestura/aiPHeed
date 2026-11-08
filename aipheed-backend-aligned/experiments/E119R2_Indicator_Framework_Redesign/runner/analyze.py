"""E119-R2: measure coverage, redundancy and eligibility of every dataset under the proposed framework; write the CSV deliverables.

No model is trained. Inputs are read only (E118 clean tables, E119 outputs, firi.py). 2021+ only, through the E119 helpers.
    python analyze.py
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXP = ROOT.parent
E118C = EXP / "E118_FAO_Data_Discovery" / "data" / "clean"
E119 = EXP / "E119_Preprocessing"
sys.path.insert(0, str(E119 / "runner"))
import preprocess as P            # noqa: E402  (E119 helpers: monthly_to_q, yoy, mday, qs, START_Q)
import framework as F             # noqa: E402

FI = P.FI
PROVS = P.PROVS
OUT = ROOT / "out"
OUT.mkdir(exist_ok=True)
LAST_Q = 2026 * 4 + 2             # 2026-Q3


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ series
def e119_long() -> pd.DataFrame:
    parts = [pd.read_csv(f) for f in (E119 / "out" / "indicators").glob("*/observations_clean.csv") if f.parent.name not in ("H1", "V1")]
    d = pd.concat(parts)[["feature", "unit", "period", "value", "avail", "status", "resolution"]]
    # E119 labels resolution per feature, so its Region IV-A rows carry "province"; resolution here follows the unit
    d.loc[d["unit"] == "Region IV-A", "resolution"] = "region"
    d.loc[d["unit"].str.startswith("CALABARZON"), "resolution"] = "region proxy"
    return d


def extra_series() -> pd.DataFrame:
    """Datasets E119 did not process: same rules (2021+, 3 published months per quarter, YoY on a 2021+ base)."""
    rows = []

    def monthly(table, item, feat):
        d = pd.read_csv(E118C / f"{table}.csv")
        d = d[d["item"].str.strip() == item]
        for u, g in d.groupby("unit"):
            m = pd.DataFrame({"period": g["period"].astype(int), "value": g["value"]}).dropna()
            m["avail"], m["status"] = m["period"].map(lambda x: P.mday(x, 15)), "rule_unverified"
            q = P.monthly_to_q(m)[["period", "value", "avail", "status", "obs_label"]]
            for f, s in ((f"{feat}_price", q), (f"{feat}_yoy_pct", P.yoy(q))):
                rows.append(s.assign(feature=f, unit=u, resolution="region" if u == "Region IV-A" else "province"))

    for table, item, feat in (("retail_fruit_veg", "TOMATO, 1 KG", "retail_tomato"), ("retail_leafy_veg", "CABBAGE, 1 KG", "retail_cabbage"),
                              ("retail_fruit_veg", "EGGPLANT, LONG, PURPLE, 1 KG", "retail_eggplant"),
                              ("retail_rootcrops", "CASSAVA (KAMOTENG KAHOY), 1 KG", "retail_cassava"), ("retail_rootcrops", "CARROT, 1 KG", "retail_carrot"),
                              ("farmgate_livestock_household", "Hog for Slaughter", "farmgate_hog"),
                              ("wholesale_cereals", "Corngrits Yellow", "wholesale_corngrits"), ("wholesale_fish", "Galunggong [Roundscad]", "wholesale_galunggong")):
        monthly(table, item, feat)
    # vegetables vs root crops production (top-level crop rows only; "tops" are leaves, counted as vegetables)
    d = pd.read_csv(E118C / "prod_vegetables_rootcrops.csv")
    d = d[~d["item"].str.startswith("..")]
    root = d["item"].map(lambda x: any(x.startswith(r) for r in F.ROOT_CROPS) and "tops" not in x)
    for grp, sub in (("vegetables", d[~root]), ("rootcrops", d[root])):
        for u, g in sub.groupby("unit"):
            q = g.groupby("period")["value"].sum(min_count=1).reset_index()
            q["period"] = q["period"].astype(int)
            q = q[q["period"] >= P.START_Q].dropna()
            q["avail"], q["status"], q["obs_label"] = q["period"].map(lambda x: P.qstart(x + 2).isoformat()), "rule_unverified", q["period"].map(P.qs)
            for f, s in ((f"{grp}_only_production_t", q), (f"{grp}_only_production_yoy_pct", P.yoy(q))):
                rows.append(s.assign(feature=f, unit=u, resolution="region" if u == "Region IV-A" else "province"))
    return pd.concat(rows)[["feature", "unit", "period", "value", "avail", "status", "resolution"]]


def fies_bottom30() -> pd.DataFrame:
    f = pd.read_csv(P.INPUTS["fies2023"], encoding="latin-1")
    f = f[f.iloc[:, 0] != "Quezon City"]
    name = {"BATANGAS": "Batangas", "CAVITE": "Cavite", "LAGUNA": "Laguna", "QUEZON (Excluding City of Lucena)": "Quezon", "RIZAL": "Rizal"}
    out = []
    for prov, g in f.groupby(f.columns[0]):
        g = g.set_index(f.columns[1])
        dec = ["1st Decile", "2nd Decile", "3rd Decile"]
        # group rows are % of total family expenditure; the bottom-30% share is weighted by each decile's total expenditure
        tot = pd.to_numeric(g.loc["Total Family Expenditure (in millions)", dec], errors="coerce")
        food = pd.to_numeric(g.loc["Food and Non-Alcoholic Beverages", dec], errors="coerce")
        out.append({"province": name[prov], "fies_food_share_all_pct": float(g.loc["Food and Non-Alcoholic Beverages", "All Income Groups"]),
                    "fies_food_share_bottom30_pct": float((food * tot).sum() / tot.sum())})
    return pd.DataFrame(out)


# ------------------------------------------------------------------------------------------------ analysis helpers
def panel(L, feats, units):
    d = L[L["feature"].isin(feats) & L["unit"].isin(units)]
    return d.pivot_table(index=["unit", "period"], columns="feature", values="value")


def pair_table(X, block, level):
    rows = []
    cols = list(X.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            d = X[[a, b]].dropna()
            if len(d) < 12:
                rows.append({"block": block, "level": level, "a": a, "b": b, "n": len(d), "pearson": None, "spearman": None})
                continue
            rows.append({"block": block, "level": level, "a": a, "b": b, "n": len(d), "pearson": round(float(d[a].corr(d[b])), 3),
                         "spearman": round(float(d[a].corr(d[b], method="spearman")), 3)})
    return rows


def participation(X):
    """Effective number of independent components: (sum eigenvalues)^2 / sum eigenvalues^2 of the Spearman correlation matrix."""
    d = X.dropna()
    if len(d) < 12 or d.shape[1] < 2:
        return None, len(d)
    c = d.rank().corr().to_numpy()
    ev = np.clip(np.linalg.eigvalsh(c), 0, None)
    return round(float(ev.sum() ** 2 / (ev ** 2).sum()), 2), len(d)


# ------------------------------------------------------------------------------------------------ main
def main():
    inputs = sorted([*E118C.glob("*.csv"), *(E119 / "out" / "indicators").glob("*/observations_clean.csv"), E119 / "E119_PROVINCIAL_ANNUAL_INDICATORS.csv",
                     E119 / "E119_PROVINCIAL_VULNERABILITY_DATASET.csv", E119 / "E119_REGIONAL_MODELING_DATASET.csv", P.INPUTS["fies2023"], P.INPUTS["vuln"]])
    before = {str(p.relative_to(EXP.parent.parent) if str(p).startswith(str(EXP.parent.parent)) else p): sha(p) for p in inputs}
    L = pd.concat([e119_long(), extra_series()])
    assert (L["period"] >= P.START_Q).all(), "pre-2021 period"
    A = pd.read_csv(E119 / "E119_PROVINCIAL_ANNUAL_INDICATORS.csv")
    R = pd.read_csv(E119 / "E119_REGIONAL_MODELING_DATASET.csv")
    Pv = pd.read_csv(E119 / "E119_PROVINCIAL_VULNERABILITY_DATASET.csv")
    fb = fies_bottom30()
    vul = pd.read_csv(P.INPUTS["vuln"])
    dens = vul.groupby("province").apply(lambda g: g["population_2024"].sum() / g["land_area_km2"].sum(), include_groups=False).rename("density_per_km2")
    pov = vul.groupby("province")["poverty_lgu_estimate"].mean().rename("poverty_incidence_mean_lgu_pct")

    # ---------------- existing 12-indicator review
    ex = []
    ipr = pd.read_csv(E119 / "E119_INDICATOR_PREPROCESSING_REPORT.csv").set_index("indicator")
    new_of = {"A1": "FP", "A2": "FP", "A3": "FP", "V1": "SV", "C1": "CH", "C2": "CH", "C3": "PS", "C4": "PS", "E1": "HI", "E2": "HI", "N1": "NS", "H1": "EH"}
    for code, dom, rule, geo, lim in F.EXISTING:
        ex.append({"indicator": code, "label": FI.LABELS[code], "code_domain": f"{dom} ({FI.DOMAINS[dom]})", "definition_in_firi_py": rule,
                   "geography_as_served": geo, "continuous_or_binary": "continuous (percentile)" if code in FI.CONTINUOUS else "0-1 as is",
                   "e119_clean_obs_2021plus": int(ipr.loc[code, "clean_observations_2021plus"]), "e119_verified_share": ipr.loc[code, "verified_share_obs"],
                   "limitation": lim, "proposed_indicator": new_of[code]})
    pd.DataFrame(ex).to_csv(ROOT / "E119R2_EXISTING_12_INDICATOR_REVIEW.csv", index=False, lineterminator="\n")

    # ---------------- per-dataset coverage
    feat_of = {}
    for row in F.DATASETS:
        src = row[8]
        if src[0] == "e119":
            feat_of[row[0]] = src[1]
        elif src[0] == "e118":
            feat_of[row[0]] = {"TOMATO, 1 KG": "retail_tomato_yoy_pct", "CASSAVA (KAMOTENG KAHOY), 1 KG": "retail_cassava_yoy_pct", "Hog for Slaughter": "farmgate_hog_yoy_pct",
                               "Corngrits Yellow": "wholesale_corngrits_yoy_pct", "Galunggong [Roundscad]": "wholesale_galunggong_yoy_pct"}[src[2]]
        elif src[0] == "veg":
            feat_of[row[0]] = f"{src[1]}_only_production_yoy_pct"
    inv, geo = [], []
    for (did, name, source, ind, comp, firi, geog, freq, src, role, reason) in F.DATASETS:
        f = feat_of.get(did)
        cov = {"units_2021plus": "", "provinces_2021plus": 0, "first_period": "", "last_period": "", "observations_2021plus": 0, "missing_pct_province_quarters": None,
               "verified_share": None, "identical_across_provinces_share": None}
        if f:
            d = L[L["feature"] == f]
            pq = d[d["unit"].isin(PROVS)]
            units = sorted(d["unit"].unique())
            first, last = (int(d["period"].min()), int(d["period"].max())) if len(d) else (None, None)
            span = (LAST_Q - P.START_Q + 1)
            cov.update(units_2021plus="; ".join(units), provinces_2021plus=int(pq["unit"].nunique()), first_period=P.qs(first) if first is not None else "",
                       last_period=P.qs(last) if last is not None else "", observations_2021plus=int(len(d)),
                       missing_pct_province_quarters=round(100 * (1 - len(pq) / (5 * span)), 1) if pq["unit"].nunique() else None,
                       verified_share=round(float((d["status"] == "verified").mean()), 3) if len(d) else None)
            if f in Pv.columns:
                g = Pv.groupby("origin")[f].agg(lambda s: (s.nunique() == 1) if s.notna().sum() == 5 else np.nan).dropna()
                cov["identical_across_provinces_share"] = round(float(g.mean()), 2) if len(g) else None
        elif src[0] == "annual":
            g = A[A["feature"] == src[1]]
            cov.update(units_2021plus="; ".join(sorted(g["province"].unique())), provinces_2021plus=int(g["province"].nunique()),
                       first_period=str(g["reference_year"].min()), last_period=str(g["reference_year"].max()), observations_2021plus=int(len(g)),
                       verified_share=round(float(g["status"].str.startswith("verified").mean()), 3))
        elif src[0] == "h1":
            h = pd.read_csv(E119 / "out" / "indicators" / "H1" / "observations_clean.csv")
            cov.update(units_2021plus="Balance Luzon", first_period=P.qs(int(h["period"].min())), last_period=P.qs(int(h["period"].max())),
                       observations_2021plus=int(len(h)), verified_share=1.0)
        if did == "D51":
            cov.update(units_2021plus="; ".join(PROVS), provinces_2021plus=5, first_period="2024", last_period="2024", observations_2021plus=5, verified_share=1.0)
        if did == "D53":
            cov.update(observations_2021plus=10, units_2021plus="; ".join(PROVS))
        avail_rel = ("verified (dated source)" if cov["verified_share"] is not None and cov["verified_share"] >= .9 else
                     "partly verified" if cov["verified_share"] else "rule-based (unverified)" if f or src[0] == "annual" else "n/a")
        inv.append({"dataset_id": did, "dataset": name, "source": source, "proposed_indicator": ind, "component": comp, "original_firi": firi,
                    "geography": geog, "frequency": freq, "acquired": "yes" if src[0] != "none" or did in ("D16", "D17", "D51", "D71", "D72", "D73") else "no",      # in the repository without an E119 series
                    "availability_reliability": avail_rel, **cov, "role": role, "reason": reason})
    INV = pd.DataFrame(inv)
    INV.to_csv(ROOT / "E119R2_COMPLETE_DATASET_INVENTORY.csv", index=False, lineterminator="\n")
    INV[["dataset_id", "dataset", "proposed_indicator", "geography", "frequency", "units_2021plus", "provinces_2021plus", "first_period", "last_period",
         "observations_2021plus", "missing_pct_province_quarters", "identical_across_provinces_share", "availability_reliability"]].assign(
        national_or_regional_copied_to_provinces=False,
        annual_spread_to_quarters=False).to_csv(ROOT / "E119R2_GEOGRAPHIC_AND_TEMPORAL_COVERAGE.csv", index=False, lineterminator="\n")
    INV[["dataset_id", "dataset", "proposed_indicator", "component", "original_firi", "role", "reason"]].rename(columns={"role": "relationship_or_role"}).to_csv(
        ROOT / "E119R2_DATASET_TO_INDICATOR_MAPPING.csv", index=False, lineterminator="\n")

    # ---------------- redundancy and correlation
    blocks = {
        "FP": ["cpi_food_yoy_pct", "cpi_headline_yoy_pct", "cpi_bottom30_food_yoy_pct", "rice_wholesale_yoy_pct", "retail_rice_regular_yoy_pct", "farmgate_palay_yoy_pct",
               "retail_chicken_yoy_pct", "retail_pork_yoy_pct", "retail_tilapia_yoy_pct", "retail_tomato_yoy_pct", "retail_cabbage_yoy_pct", "retail_cassava_yoy_pct",
               "retail_carrot_yoy_pct", "farmgate_hog_yoy_pct"],
        "PS": ["palay_production_yoy_pct", "corn_production_yoy_pct", "vegetables_only_production_yoy_pct", "rootcrops_only_production_yoy_pct",
               "fisheries_production_yoy_pct", "aquaculture_production_yoy_pct", "chicken_production_yoy_pct", "livestock_production_yoy_pct"],
        "CH": ["rainfall_total_mm", "rainfall_anomaly_mm", "temperature_anomaly_c", "C2_typhoons_300km", "typhoons_local_100km"],
        "NS": ["N1_fssi_v3", "N1_admitted_articles"],
        "cross": ["cpi_food_yoy_pct", "rice_wholesale_yoy_pct", "palay_production_yoy_pct", "fisheries_production_yoy_pct", "retail_tilapia_yoy_pct",
                  "rainfall_anomaly_mm", "typhoons_local_100km", "N1_fssi_v3"],
    }
    pairs, part = [], []
    for b, fs in blocks.items():
        X = panel(L, fs, PROVS)
        pairs += pair_table(X, b, "province-quarter (pooled 5 provinces)")
        if b != "cross":
            core = [c for c in X.columns if X[c].notna().mean() > .6]
            pr, n = participation(X[core])
            part.append({"block": b, "features": len(core), "effective_independent_components": pr, "complete_rows": n, "features_used": "; ".join(core)})
    # national / regional quarterly block (one value per quarter)
    nat_feats = {("unemployment_rate_pct", "PHILIPPINES"), ("E1_unemployment_change_pp", "PHILIPPINES"), ("E2_remittance_decline_pct", "PHILIPPINES"),
                 ("oni_quarter_mean", "GLOBAL"), ("typhoons_PAR", "PHILIPPINES"), ("region_cpi_food_yoy_pct", "Region IV-A"), ("region_cpi_headline_yoy_pct", "Region IV-A"),
                 ("farmgate_palay_yoy_pct", "Region IV-A"), ("rainfall_anomaly_mm", "CALABARZON (mean of 5 province points)"),
                 ("news_gdelt_shortage_share", "PHILIPPINES"), ("news_gdelt_agri_supply_share", "PHILIPPINES"), ("news_gdelt_jobs_income_share", "PHILIPPINES"),
                 ("news_gdelt_assistance_share", "PHILIPPINES")}
    nl = L[[(f, u) in nat_feats or (f == "oni_quarter_mean") for f, u in zip(L["feature"], L["unit"])]]
    Xn = nl.pivot_table(index="period", columns="feature", values="value")
    pairs += pair_table(Xn, "national/regional", "quarter (one value per quarter)")
    gd = [c for c in Xn.columns if c.startswith("news_gdelt")]
    pr, n = participation(Xn[gd])
    part.append({"block": "NS (GDELT national)", "features": len(gd), "effective_independent_components": pr, "complete_rows": n, "features_used": "; ".join(gd)})
    # annual provincial (5 provinces: rank agreement only)
    an = A.pivot_table(index="province", columns=["feature", "reference_year"], values="value")
    an.columns = [f"{a}_{b}" for a, b in an.columns]
    an = an.join(fb.set_index("province")).join(dens).join(pov)
    keep = ["poverty_incidence_mean_lgu_pct", "subsistence_incidence_pct_2021", "subsistence_incidence_pct_2023", "fies_food_share_all_pct",
            "fies_food_share_bottom30_pct", "density_per_km2", "provincial_unemployment_rate_pct_annual_2023", "provincial_underemployment_rate_pct_annual_2023"]
    an = an[[c for c in keep if c in an.columns]]
    ann_rank = an.rank().corr(method="pearson").round(2)
    ann_rank.to_csv(OUT / "annual_rank_correlation.csv", lineterminator="\n")
    an.round(3).to_csv(OUT / "annual_profile_values.csv", lineterminator="\n")
    PT = pd.DataFrame(pairs)
    PT.to_csv(OUT / "pairwise_correlations.csv", index=False, lineterminator="\n")
    pd.DataFrame(part).to_csv(OUT / "effective_components.csv", index=False, lineterminator="\n")
    # between-province identity of provincial features
    ident = {c: round(float(Pv.groupby("origin")[c].agg(lambda s: (s.nunique() == 1) if s.notna().sum() == 5 else np.nan).dropna().mean()), 2)
             for c in Pv.columns if not c.endswith(("__status", "__period")) and c not in ("province", "province_code", "origin", "t", "issue_date", "A_status", "A_cpi_month")}
    json.dump(ident, open(OUT / "identical_across_provinces.json", "w"), indent=1)

    # ---------------- proposed framework, FAO, eligibility
    rows = []
    for I in F.INDICATORS:
        ds = INV[INV["proposed_indicator"] == I["code"]]
        acq = ds[ds["acquired"] == "yes"]
        prov = acq[acq["provinces_2021plus"] == 5]
        rows.append({**{k: v for k, v in I.items()}, "datasets_assigned": int(len(ds)), "datasets_acquired": int(len(acq)),
                     "dataset_ids": " ".join(ds["dataset_id"]),
                     "geographic_coverage": "five provinces + regional/national" if len(prov) and (acq["provinces_2021plus"] < 5).any() else
                                            "five provinces" if len(prov) else "regional / national only",
                     "temporal_coverage": f"{acq['first_period'].replace('', np.nan).dropna().min()} to {acq['last_period'].replace('', np.nan).dropna().max()}",
                     "frequencies": "; ".join(sorted(set(acq["frequency"]))),
                     "median_missing_pct": float(acq["missing_pct_province_quarters"].dropna().median()) if acq["missing_pct_province_quarters"].notna().any() else None,
                     "verified_share_mean": round(float(acq["verified_share"].dropna().mean()), 3) if acq["verified_share"].notna().any() else None,
                     "roles": "; ".join(f"{k}: {v}" for k, v in ds["role"].value_counts().items()),
                     "primary_use": {"FP": "forecasting + provincial profiling", "PS": "forecasting + provincial profiling", "CH": "forecasting + provincial profiling",
                                     "HI": "forecasting (national) + provincial profiling (annual)", "SV": "provincial vulnerability profiling only",
                                     "NS": "candidate predictor (to be tested) + context", "EH": "regional forecasting target + its own history"}[I["code"]]})
    pd.DataFrame(rows).to_csv(ROOT / "E119R2_PROPOSED_INDICATOR_FRAMEWORK.csv", index=False, lineterminator="\n")
    dims = ["Availability", "Access", "Utilization", "Stability"]
    fao = []
    for I in F.INDICATORS:
        lv = F.FAO_LEVELS[I["code"]]
        fao.append({"indicator": I["code"], "name": I["name"], **{d: lv.get(d, "") for d in dims}, "justification": F.FAO_WHY[I["code"]]})
    FAO = pd.DataFrame(fao)
    FAO.to_csv(ROOT / "E119R2_FAO_DIMENSION_MAPPING.csv", index=False, lineterminator="\n")
    el = INV[["dataset_id", "dataset", "proposed_indicator", "geography", "frequency", "observations_2021plus", "missing_pct_province_quarters",
              "availability_reliability", "role", "reason"]].copy()
    el["strict_mode_eligible"] = el["availability_reliability"].str.startswith("verified")
    # quarters per unit: provincial series are compared on province-quarters, regional / national ones on quarters (the target has 23)
    nunits = INV["units_2021plus"].map(lambda u: max(1, len([x for x in str(u).split("; ") if x])) if isinstance(u, str) and u else 1)
    q_per_unit = list(el["observations_2021plus"] / nunits)
    el["quarters_per_unit"] = [round(q, 1) for q in q_per_unit]
    el["sufficient_observations"] = [("yes" if q >= 16 else "limited" if q >= 8 else "no") if not str(fr).startswith(("static", "triennial", "annual")) else
                                     "annual (profile only)" for q, fr in zip(q_per_unit, el["frequency"])]
    el.to_csv(ROOT / "E119R2_FORECASTING_ELIGIBILITY.csv", index=False, lineterminator="\n")

    after = {k: sha(Path(EXP.parent.parent / k) if not Path(k).is_absolute() else Path(k)) for k in before}
    assert before == after, "an input changed"
    json.dump({"inputs_sha256": before, "datasets": len(INV), "indicators": len(F.INDICATORS), "pairs": len(PT)}, open(OUT / "manifest.json", "w"), indent=1)
    pd.set_option("display.width", 250)
    print(pd.DataFrame(part).to_string())
    print(PT[PT["pearson"].abs() >= .6].to_string())
    print(ann_rank.to_string())
    print(an.round(2).to_string())
    print(INV[["dataset_id", "provinces_2021plus", "first_period", "last_period", "observations_2021plus", "missing_pct_province_quarters", "verified_share", "identical_across_provinces_share", "role"]].to_string())


if __name__ == "__main__":
    main()
