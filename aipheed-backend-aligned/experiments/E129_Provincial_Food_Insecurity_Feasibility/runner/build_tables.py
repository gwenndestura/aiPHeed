"""E129 feasibility tables (read only; no model fitting).

    python build_tables.py
Writes E129_PROVINCIAL_TARGET_INVENTORY.csv, E129_PROVINCIAL_DATA_AVAILABILITY.csv, E129_FIVE_TRIGGER_GROUP_GEOGRAPHIC_AUDIT.csv,
E129_PROVINCIAL_PANEL_FEASIBILITY.csv, E129_LEAD_1_TO_4_DATA_SUFFICIENCY.csv and out/e129_summary.json.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "out"
X = ROOT.parent
PROVS = ["Batangas", "Cavite", "Laguna", "Quezon", "Rizal"]
E128 = X / "E128_Food_Insecurity_ML_Development"
INPUTS = {
    "e119_provincial": X / "E119_Preprocessing/E119_PROVINCIAL_VULNERABILITY_DATASET.csv",
    "e119_geography": X / "E119_Preprocessing/E119_GEOGRAPHIC_ALIGNMENT_REPORT.csv",
    "outcome_register": X / "OUTCOME_GAP_RESOLUTION/OFFICIAL_OUTCOME_SOURCE_REGISTER.csv",
    "e118_targets": X / "E118_FAO_Data_Discovery/DIRECT_FOOD_INSECURITY_TARGETS.csv",
    "sws_2021": X / "FINAL_FOOD_INSECURITY_LIGHTGBM/data/sws_area_rounds_2021.csv",
    "sws_full": X / "E114_Final_Run/data/sws_area_rounds_full.csv",
    "e128_protocol": E128 / "E128_FROZEN_EXPERIMENT_PROTOCOL.md",
    "e128_summary": E128 / "out/summary.json",
}

# Candidate targets. "measures" distinguishes measured food insecurity / proxy / constructed index / food-price condition.
TARGETS = [
    # id, indicator, agency, geography, level, period_2021plus, release, frequency, sample, measures, binary_or_continuous,
    # history, independence, lead_support, held, access, decision
    ("P1", "Household moderate-or-severe food insecurity (FIES 8 items), ENNS 2021 provincial dissemination", "DOST-FNRI",
     "Batangas, Cavite, Lucena (HUC) only", "provincial (2 of 5 provinces)", "2021 (one round)", "2022 (dissemination deck)", "one round per domain",
     "provincial domain samples; 90% CI e.g. Cavite 31.7 [27.0-36.4]", "measured food insecurity", "continuous (prevalence); binary only with an external threshold",
     "no in-window repeat; 2018/2019 rounds pre-window", "independent across provinces; 1 period", "no (no time series)", "yes (local deck values)", "held", "cross-sectional validation only (2 provinces)"),
    ("P2", "Household food insecurity (FIES), 2022 ENNS (20 provinces/HUCs)", "DOST-FNRI", "unverified whether Laguna, Quezon, Rizal were domains",
     "provincial (coverage unverified)", "Jul-Dec 2022", "unverified", "one round", "~30,000 households nationally", "measured food insecurity", "continuous",
     "single round", "1 period", "no", "no", "FNRI request (E87 request B drafted, not sent); eNutrition 503 on 10-27/28", "cross-sectional only, if covered"),
    ("P3", "SDG 2.1.2.p1 prevalence of moderate or severe household food insecurity (FIES), 2024 POPCEN-CBMS", "PSA / LGUs",
     "all CALABARZON cities/municipalities that ran CBMS (142 LGUs if released)", "barangay / city-municipal (aggregable to province)", "Jul 2023 - Jun 2024 (one window)",
     "LGU preliminary results presented from Aug-Sep 2025 (RSSO IV-A Batangas briefings); tables not public", "one round; next round not scheduled in sources",
     "census of households in participating LGUs", "measured food insecurity", "continuous (LGU prevalence)", "single window", "142 LGUs x 1 period; spatially correlated",
     "no (cross-section)", "no", "PSA CPCD / RSSO IV-A request (E87 request A drafted, not sent); RSSO pages 403 to automated reading",
     "strongest provincial/LGU validation source; cross-sectional only"),
    ("P4", "Moderate-or-severe household FIES, 2023 National Nutrition Survey", "DOST-FNRI", "CALABARZON (n 1,752 households)", "regional",
     "2023", "2024", "every ~5 years", "1,752 households", "measured food insecurity", "continuous", "1 point", "1 regional value", "no", "yes (local PDF)", "held", "regional context"),
    ("P5", "Moderate-or-severe FI in the population (FIES, Rasch), 2025 Updating Survey", "DOST-FNRI", "CALABARZON 22.6%", "regional", "2025", "2026",
     "periodic", "regional sample", "measured food insecurity", "continuous", "1 point", "1 regional value", "no", "yes (local PDF)", "held", "regional context"),
    ("P6", "SWS involuntary hunger, Balance Luzon", "Social Weather Stations (private)", "Balance Luzon (Luzon outside NCR)", "regional",
     "2021-Q2 .. 2026-Q3 (20 quarters)", "1-3 months after fieldwork (dated)", "quarterly (irregular)", "BL ~600-900 per round (MOE +-4 to +-6)",
     "measured (experienced hunger)", "continuous; binary only with a project threshold (11.3)", "1998-Q3+ held (E114), owner window 2021+",
     "20 independent quarters; one area", "regional only (E128)", "yes", "held", "regional reference; never copied to provinces"),
    ("P7", "SWS hunger for CALABARZON respondents by province (microdata)", "SWS Survey Data Library", "respondent province coded (expected)",
     "provincial (if released)", "per round", "microdata release lag unknown", "quarterly", "est. ~100-230 CALABARZON respondents per round, ~20-75 per province (estimate)",
     "measured (experienced hunger)", "continuous with very wide intervals (+-11 to +-22 pts per province-round, estimate)", "possibly 2021+ rounds",
     "province-rounds independent samples, but tiny", "not with useful precision unless pooled to annual", "no", "request drafted (E87 request C), not sent", "possible but noisy; needs data and a pooling design"),
    ("P8", "Families that experienced hunger with nothing to eat (APIS)", "PSA", "region (survey designed for regional estimates)", "regional", "2022 (PSADA)",
     "~1 year", "annual (non-FIES years)", "regional design", "measured (hunger item)", "continuous", "<= 2 in-window points", "regional", "no", "no", "PSADA microdata", "regional context"),
    ("P9", "Subsistence incidence (families/population below the food threshold)", "PSA", "province (Quezon excl. Lucena)", "provincial", "2021, 2023",
     "2024-08-15 (2021 and 2023 in the repository file)", "triennial", "FIES-based; CV up to 88% (Cavite)", "proxy (income-based food poverty, not experienced FI)",
     "continuous", "2 in-window points per province", "5 x 2", "no", "yes", "held", "structural vulnerability; not a quarterly label"),
    ("P10", "Food share of family expenditure; bottom-30% share (FIES 2023 PUF)", "PSA", "province", "provincial", "2023 (2021 tables)", "~1 year", "triennial",
     "163,268 records nationally", "proxy (economic access / vulnerability); no FI items", "continuous", "1-2 in-window points", "5 x 1-2", "no", "yes (PUF, Downloads)", "held",
     "structural vulnerability only"),
    ("P11", "Underweight / stunting / wasting 0-59 months (Operation Timbang Plus)", "National Nutrition Council / LGUs", "province and municipality", "provincial",
     "annual 2021-2025 (per NNC releases)", "~6-12 months", "annual (Jan-Mar weighing)", "LGU weighing coverage varies", "proxy (nutrition/utilization outcome, not FI)",
     "continuous", "~5 in-window years", "5 x 5 annual", "annual only (no quarterly lead)", "no", "NNC site 403 to automated access; FOI request needed", "candidate annual utilization proxy; not FI"),
    ("P12", "DSWD programme data (4Ps, Supplementary Feeding, Walang Gutom food stamps, AICS)", "DSWD", "province / municipality (beneficiary lists)", "provincial",
     "programme years", "varies", "administrative", "beneficiary counts", "programme exposure/outputs, not a food-insecurity measurement (targeting and budget driven)",
     "counts", "partial", "not independent of policy", "no", "no", "not public in usable series", "not suitable as a label"),
    ("P13", "Provincial food CPI YoY (and food-headline gap)", "PSA", "province (5)", "provincial", "2021-01 .. 2026-09 monthly (23 complete quarters)",
     "~day 5 of month m+1 (ledger: 32 of 180 verified)", "monthly", "price index (not a survey of households)", "food-price condition (not food insecurity)",
     "continuous; binary only with a threshold", "full 2021+", "5 x 23 province-quarters; 74% of variance shared across provinces", "yes (Leads 1-4 data sufficient)",
     "yes", "held", "defensible forecasting target for provincial FOOD-PRICE PRESSURE only; never labelled food insecurity"),
    ("P14", "T43c province-quarter risk class (SWS BL > 11.3 AND province price condition)", "aiPHeed (Chapter I definition)", "province (5)", "mixed (regional hunger copied)",
     "2021-Q2 .. 2026-Q3", "as SWS + CPI", "quarterly", "derived", "constructed label: regional hunger copied to provinces x provincial price condition",
     "binary", "20 hunger quarters", "hunger term not independent across provinces", "no (E128 §2: not admissible)", "yes", "held", "rejected as a provincial FI label"),
    ("P15", "FIRI3 / FIRI v2 provincial scores and bands", "aiPHeed", "province (5) and region", "provincial", "2021+", "issue date", "quarterly", "composite",
     "constructed risk index (not measured FI)", "continuous / bands", "2021+", "built from the predictors themselves", "not a label (E128 §2)", "yes", "held", "excluded as ground truth"),
]
TCOLS = ["id", "indicator", "source_agency", "geographic_coverage", "level", "observation_period_2021plus", "release_date", "frequency", "sample_or_coverage",
         "what_it_measures", "binary_or_continuous", "historical_observations", "independence_across_provinces_and_periods", "supports_lead_1_4_evaluation",
         "in_repository", "access_status", "e129_assessment"]

GROUP = {"A1": "1 market and food prices", "A2": "1 market and food prices", "A3": "1 market and food prices", "C3": "1 market and food prices (agricultural supply)",
         "C4": "1 market and food prices (fish supply)", "UNASSIGNED": None, "C1": "2 climate and environmental stress", "C2": "2 climate and environmental stress",
         "E1": "3 employment and OFW remittances", "E2": "3 employment and OFW remittances", "N1": "4 news and NLP", "V1": "5 poverty and social vulnerability"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def group_of(feature, ind):
    g = GROUP.get(ind)
    if g:
        return g
    if feature.startswith(("rainfall", "temperature")):
        return "2 climate and environmental stress"
    return "1 market and food prices (agricultural supply)"


def geographic_audit():
    geo = pd.read_csv(INPUTS["e119_geography"])
    prov = pd.read_csv(INPUTS["e119_provincial"])
    rows = []
    for _, g in geo.iterrows():
        f = g["feature"]
        ident = np.nan
        nobs = 0
        if f in prov.columns:
            w = prov.pivot_table(index="origin", columns="province", values=f)
            w = w.dropna(how="any")
            nobs = len(w)
            ident = float((w.nunique(axis=1) == 1).mean()) if len(w) else np.nan
        res = str(g["source_resolution"])
        if not res.startswith("province"):
            genuine = "no"
        elif ident != ident:
            genuine = "yes (provincial source; not in the as-of dataset, identity not tested)"
        else:
            genuine = "yes" if ident < 0.5 else f"weak ({ident:.0%} of quarters identical across provinces)"
        if res.startswith("province (centroid"):
            kind = "provincial point estimate (NASA POWER grid at the province centroid; not an area average)"
        elif res.startswith("province"):
            kind = "provincial observation"
        else:
            kind = f"{res} value: shared by all five provinces"
        rows.append(dict(trigger_group=group_of(f, g["indicator"]), feature=f, firi_indicator=g["indicator"], actual_resolution=res, interpretation=kind,
                         quarters_with_all_five_provinces=nobs, share_quarters_identical_across_provinces=ident,
                         genuinely_varies_across_provinces=genuine, copied_across_provinces_in_e119=bool(g["copied_across_provinces"]),
                         note=g["note"]))
    extra = [
        dict(trigger_group="3 employment and OFW remittances", feature="provincial_unemployment_rate_pct_annual (owner-collected LFS)", firi_indicator="E1",
             actual_resolution="province (annual)", interpretation="provincial observation, annual; 2025 incomplete; Batangas 2024/2025 unverified",
             quarters_with_all_five_provinces=0, share_quarters_identical_across_provinces=np.nan, genuinely_varies_across_provinces="yes (annual or static)",
             copied_across_provinces_in_e119=False, note="annual only; no quarterly provincial LFS on OpenSTAT (E118)"),
        dict(trigger_group="3 employment and OFW remittances", feature="OFW remittances (BSP)", firi_indicator="E2", actual_resolution="national",
             interpretation="national value: shared by all five provinces", quarters_with_all_five_provinces=0, share_quarters_identical_across_provinces=1.0,
             genuinely_varies_across_provinces="no", copied_across_provinces_in_e119=False, note="no provincial remittance series; BSP 403 to automated access"),
        dict(trigger_group="5 poverty and social vulnerability", feature="V1 vulnerability profile (SAE 2021 poverty x POPCEN 2024 density)", firi_indicator="V1",
             actual_resolution="province (from 142 LGUs)", interpretation="provincial, static (published 2025-07-01)", quarters_with_all_five_provinces=0,
             share_quarters_identical_across_provinces=np.nan, genuinely_varies_across_provinces="yes (annual or static)", copied_across_provinces_in_e119=False,
             note="varies across provinces but not over time; cannot inform quarter-to-quarter change"),
        dict(trigger_group="5 poverty and social vulnerability", feature="subsistence incidence 2021/2023", firi_indicator="V1", actual_resolution="province",
             interpretation="provincial, triennial", quarters_with_all_five_provinces=0, share_quarters_identical_across_provinces=np.nan,
             genuinely_varies_across_provinces="yes (annual or static)", copied_across_provinces_in_e119=False, note="2 in-window points; both published 2024-08-15"),
        dict(trigger_group="4 news and NLP", feature="GDELT food-news shares (4)", firi_indicator="N1", actual_resolution="national",
             interpretation="national value: shared by all five provinces", quarters_with_all_five_provinces=0, share_quarters_identical_across_provinces=1.0,
             genuinely_varies_across_provinces="no", copied_across_provinces_in_e119=False, note="must not be given provincial relevance"),
    ]
    return pd.concat([pd.DataFrame(rows), pd.DataFrame(extra)], ignore_index=True)


def data_availability(geo):
    prov = pd.read_csv(INPUTS["e119_provincial"])
    rows = []
    for f in [c for c in prov.columns if not c.endswith(("__status", "__period")) and c not in ("province", "province_code", "origin", "t", "issue_date",
                                                                                                 "A_status", "A_cpi_month")]:
        for p in PROVS:
            s = prov[prov["province"] == p].set_index("origin")[f]
            st = prov[prov["province"] == p][f + "__status"] if f + "__status" in prov.columns else None
            rows.append(dict(feature=f, province=p, origins=len(s), available=int(s.notna().sum()), missing_pct=round(100 * s.isna().mean(), 1),
                             first_available=s.first_valid_index() or "", last_available=s.last_valid_index() or "",
                             verified=int(st.astype(str).str.startswith("verified").sum()) if st is not None else "",
                             rule_unverified=int(st.astype(str).str.startswith("rule").sum()) if st is not None else "",
                             resolution=geo.set_index("feature")["actual_resolution"].get(f, "")))
    return pd.DataFrame(rows)


def panel_feasibility():
    s = pd.read_csv(INPUTS["sws_2021"])
    nq_sws = s[~s["commissioned"].astype(bool)]["quarter"].nunique()
    rows = [
        dict(option="A direct provincial FI labels (FNRI ENNS 2021 + 2022 + CBMS 2024)", provinces_with_valid_obs="2 held (Batangas, Cavite); up to 5 if CBMS/ENNS 2022 obtained",
             periods_per_province="1 (ENNS) + 1 (CBMS) at most", province_period_obs_held=2, province_period_obs_obtainable="<= 10-12",
             independent_obs_note="independent samples, but 1-2 periods: no within-province time variation", time_series_panel=False,
             lead_1_4_evaluable=False, verdict="no forecasting panel; cross-sectional validation only"),
        dict(option="B provincial survey estimates (SWS microdata by province)", provinces_with_valid_obs="5 (if released)", periods_per_province=f"<= {nq_sws} rounds-quarters 2021+",
             province_period_obs_held=0, province_period_obs_obtainable=f"<= {5 * nq_sws}",
             independent_obs_note="independent per round but ~20-75 respondents per province (est.); MOE ~+-11 to +-22 points", time_series_panel=True,
             lead_1_4_evaluable="only after pooling (e.g. annual), which leaves ~5 years x 5 provinces", verdict="not held; precision likely inadequate quarterly"),
        dict(option="C official proxy (subsistence incidence / OPT Plus / FIES food share)", provinces_with_valid_obs="5", periods_per_province="2 (subsistence), ~5 annual (OPT, not held), 1-2 (FIES)",
             province_period_obs_held=10, province_period_obs_obtainable="<= 25 annual (OPT Plus)", independent_obs_note="independent, but not quarterly and not FI",
             time_series_panel=False, lead_1_4_evaluable=False, verdict="no quarterly panel; proxies of a different concept"),
        dict(option="D continuous provincial target", provinces_with_valid_obs="0 for FI; 5 for food CPI (price condition)", periods_per_province="23 complete quarters (food CPI)",
             province_period_obs_held=115, province_period_obs_obtainable=115, independent_obs_note="5 x 23, but 74% of variance shared across provinces; effective n ~29 (design effect)",
             time_series_panel=True, lead_1_4_evaluable=True, verdict="valid panel for a FOOD-PRICE target only; not food insecurity"),
        dict(option="E constructed provincial risk index", provinces_with_valid_obs="5", periods_per_province="23", province_period_obs_held=115, province_period_obs_obtainable=115,
             independent_obs_note="constructed from the same predictor families; forecasting it validates the index, not household FI", time_series_panel=True,
             lead_1_4_evaluable="technically yes, scientifically circular", verdict="only as a declared index (FIRI3 exists); never as FI ground truth"),
        dict(option="SWS regional reference (E128)", provinces_with_valid_obs="0 (regional)", periods_per_province=f"{nq_sws} quarters, one area", province_period_obs_held=0,
             province_period_obs_obtainable=0, independent_obs_note="five copies would be 1 observation each quarter", time_series_panel=False,
             lead_1_4_evaluable="regional only (E128: no reliable lead)", verdict="keep as regional reference"),
    ]
    return pd.DataFrame(rows)


def lead_sufficiency():
    rows = []
    MIN_TRAIN_Q = 8
    for k in (1, 2, 3, 4):
        # food CPI provincial (price condition): 23 complete quarters 2021-Q1..2026-Q3; targets t+k; training needs >= 8 earlier target quarters
        nq = 23 - k
        ev_q = max(0, nq - MIN_TRAIN_Q)
        rows.append(dict(candidate="P13 provincial food CPI YoY (food-price condition)", lead=k, labelled_province_quarters=5 * nq, independent_target_quarters=nq,
                         evaluation_quarters_after_8_training=ev_q, evaluation_rows=5 * ev_q, R1_quarters_ge_10=ev_q >= 10, R1_rows_ge_40=5 * ev_q >= 40,
                         effective_rows_design_effect=round(5 * ev_q / (1 + 4 * 0.743), 1),
                         note="province deviation autocorrelation at this lag: " + {1: "0.74", 2: "0.55", 3: "0.29", 4: "-0.05"}[k]))
        rows.append(dict(candidate="P6 SWS Balance Luzon (regional, E128 T1)", lead=k, labelled_province_quarters=0, independent_target_quarters={1: 20, 2: 19, 3: 18, 4: 17}[k],
                         evaluation_quarters_after_8_training={1: 13, 2: 8, 3: 7, 4: 6}[k], evaluation_rows={1: 13, 2: 8, 3: 7, 4: 6}[k],
                         R1_quarters_ge_10=k == 1, R1_rows_ge_40=False, effective_rows_design_effect="", note="regional; E128 actual outer rows; saturated after 2023-Q4"))
        rows.append(dict(candidate="P1-P3 FNRI ENNS / CBMS provincial FIES", lead=k, labelled_province_quarters=0, independent_target_quarters=0,
                         evaluation_quarters_after_8_training=0, evaluation_rows=0, R1_quarters_ge_10=False, R1_rows_ge_40=False, effective_rows_design_effect="",
                         note="cross-sections (1-2 periods); no lead can be formed"))
        rows.append(dict(candidate="P7 SWS microdata by province (if obtained)", lead=k, labelled_province_quarters=5 * (20 - k), independent_target_quarters=20 - k,
                         evaluation_quarters_after_8_training=max(0, 20 - k - 8), evaluation_rows=5 * max(0, 20 - k - 8), R1_quarters_ge_10=(20 - k - 8) >= 10,
                         R1_rows_ge_40=5 * (20 - k - 8) >= 40, effective_rows_design_effect="", note="counts only; per-province MOE ~+-11 to +-22 pts makes quarterly labels mostly noise"))
        rows.append(dict(candidate="P11 OPT Plus annual (if obtained)", lead=k, labelled_province_quarters=0, independent_target_quarters=0, evaluation_quarters_after_8_training=0,
                         evaluation_rows=0, R1_quarters_ge_10=False, R1_rows_ge_40=False, effective_rows_design_effect="", note="annual: ~5 years x 5 provinces; quarterly leads undefined"))
    return pd.DataFrame(rows)


def main():
    OUT.mkdir(exist_ok=True)
    pd.DataFrame(TARGETS, columns=TCOLS).to_csv(ROOT / "E129_PROVINCIAL_TARGET_INVENTORY.csv", index=False)
    geo = geographic_audit()
    geo.to_csv(ROOT / "E129_FIVE_TRIGGER_GROUP_GEOGRAPHIC_AUDIT.csv", index=False)
    data_availability(geo).to_csv(ROOT / "E129_PROVINCIAL_DATA_AVAILABILITY.csv", index=False)
    panel_feasibility().to_csv(ROOT / "E129_PROVINCIAL_PANEL_FEASIBILITY.csv", index=False)
    lead_sufficiency().to_csv(ROOT / "E129_LEAD_1_TO_4_DATA_SUFFICIENCY.csv", index=False)
    g = geo.assign(v=geo["genuinely_varies_across_provinces"].str.startswith("yes")).groupby("trigger_group")["v"].agg(["sum", "size"]).to_dict("index")
    json.dump(dict(inputs={k: sha(v) for k, v in INPUTS.items()}, e128_protocol_sha256=sha(INPUTS["e128_protocol"]),
                   trigger_groups_genuinely_provincial=g, n_targets=len(TARGETS)), open(OUT / "e129_summary.json", "w"), indent=2, default=int)
    print(geo[["trigger_group", "feature", "actual_resolution", "share_quarters_identical_across_provinces", "genuinely_varies_across_provinces"]].to_string())


if __name__ == "__main__":
    main()
