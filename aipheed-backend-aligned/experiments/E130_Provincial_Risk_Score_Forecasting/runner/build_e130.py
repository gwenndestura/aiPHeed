"""
E130 stage 1 (no model, no new data): starting-state manifest, data inventory, provincial reference score data and
its uncertainty, provincial feature availability, the issue-date and operational-lead mapping, and the target gate.

Run:  python runner/build_e130.py      (backend venv; about 10 s)
"""
from __future__ import annotations

import platform
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e130_lib as L  # noqa: E402

ROOT, EXP, REPO, OUT = L.ROOT, L.EXP, L.REPO, L.OUT


# ------------------------------------------------------------------ manifest
def _git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout.strip()


INPUTS = {
    "subsistence": L.SUBSISTENCE, "e119_provincial_panel": L.PANEL, "e119_provincial_annual": L.ANNUAL,
    "e119_indicator_mapping": L.INDICATORS, "e119_geography": L.GEOGRAPHY, "sws_rounds": L.SWS,
    "remittances": L.REMITTANCES,
    "e128_protocol": L.E128 / "E128_FROZEN_EXPERIMENT_PROTOCOL.md", "e128_summary": L.E128 / "out" / "summary.json",
    "e128_lead_mapping": L.E128 / "E128_ISSUE_DATE_AND_LEAD_MAPPING.csv",
    "e129_decision": L.E129 / "E129_FINAL_DECISION.md", "e129_summary": L.E129 / "out" / "e129_summary.json",
    "e129_inventory": L.E129 / "E129_PROVINCIAL_TARGET_INVENTORY.csv",
    "frozen_r1_r7": EXP / "FINAL_THESIS_OBJECTIVES" / "FINAL_TARGET_AND_EVALUATION_PROTOCOL.md",
    "firi_v2_code": REPO / "backend" / "app" / "ml" / "inference" / "firi.py",
    "firi3_code": REPO / "backend" / "app" / "ml" / "inference" / "firi3.py",
    "dashboard_clock_code": REPO / "backend" / "app" / "quarterly" / "target.py",
}


def manifest() -> dict:
    """The starting state is recorded once (first build); a rebuild keeps it and adds its own stamp."""
    import lightgbm
    import shap
    import sklearn
    import scipy
    prev = L.json.load(open(OUT / "e130_manifest.json", encoding="utf-8")) if (OUT / "e130_manifest.json").exists() else {}
    start = {k: prev[k] for k in ("built_utc", "starting_commit", "branch", "untracked_from_other_sessions_preserved") if k in prev}
    m = {
        "experiment": "E130 Provincial Risk-Score Forecasting",
        "built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "starting_commit": _git("rev-parse", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "untracked_from_other_sessions_preserved": [l[3:] for l in _git("status", "--porcelain").splitlines()
                                                     if l.startswith("??") and "E130_" not in l],
        "inputs_sha256": {k: L.sha256(p) for k, p in INPUTS.items()},
        "data_limit": L.DATA_LIMIT.isoformat(), "window_start": L.WINDOW_START.isoformat(), "seed": L.SEED,
        "python": platform.python_version(),
        "libraries": {"numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__,
                      "scikit-learn": sklearn.__version__, "lightgbm": lightgbm.__version__, "shap": shap.__version__},
        "experiment_versions": {"E128_protocol_sha256": L.sha256(INPUTS["e128_protocol"]),
                                "FIRI3": "v1.3 (configuration 64a7d7df, frozen; not used as a target)",
                                "FIRI_v2": "served index (not used as a target)"},
    }
    if start:
        m.update(start)
        m["rebuilt_utc"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        m["head_at_rebuild"] = _git("rev-parse", "HEAD")
    L.dump(m, OUT / "e130_manifest.json")
    return m


# ------------------------------------------------------------------ provincial reference score and uncertainty
def sws_quarter_means() -> pd.DataFrame:
    s = pd.read_csv(L.SWS)
    s = s[~s["commissioned"].astype(bool)].copy()
    s["published"] = pd.to_datetime(s["published"]).dt.date
    q = s.groupby("quarter").agg(bl=("balance_luzon", "mean"), published=("published", "max"),
                                 rounds=("balance_luzon", "size")).reset_index()
    assert (q["quarter"].map(L.qi) >= L.qi("2021-Q1")).all()
    return q


def reference() -> dict:
    ref = L.load_reference()
    ch = L.change_tests(ref)
    het = {y: L.heterogeneity(ref[ref.survey_year == y]["pfdr_pct"].to_numpy(), ref[ref.survey_year == y]["se_pp"].to_numpy())
           for y in (2021, 2023)}
    # rank stability under sampling error (normal, truncated at 0), 20,000 draws
    rng = np.random.default_rng(L.SEED)
    ranks = {}
    draws = {}
    for y in (2021, 2023):
        r = ref[ref.survey_year == y].set_index("province").loc[list(L.PROVINCES)]
        d = np.clip(r["pfdr_pct"].to_numpy() + rng.standard_normal((20000, 5)) * r["se_pp"].to_numpy(), 0, None)
        draws[y] = d
        top = np.bincount(d.argmax(axis=1), minlength=5) / len(d)
        ranks[y] = {p: float(t) for p, t in zip(L.PROVINCES, top)}
    rho_obs = float(stats.spearmanr(ref[ref.survey_year == 2021].set_index("province").loc[list(L.PROVINCES), "pfdr_pct"],
                                    ref[ref.survey_year == 2023].set_index("province").loc[list(L.PROVINCES), "pfdr_pct"])[0])
    r21 = ref[ref.survey_year == 2021].set_index("province").loc[list(L.PROVINCES)]
    r23_ = ref[ref.survey_year == 2023].set_index("province").loc[list(L.PROVINCES)]
    p_rank = L.rank_stability_p(r21["pfdr_pct"], r21["se_pp"], r23_["pfdr_pct"], r23_["se_pp"])
    # construct coherence: PSA FIES 2023 food share against 2023 subsistence (both PSA, same survey)
    ann = pd.read_csv(L.ANNUAL)
    fs = ann[ann.feature == "fies_food_share_of_expenditure_pct"].set_index("province")["value"]
    sub23 = ref[ref.survey_year == 2023].set_index("province")["pfdr_pct"]
    rho_fs = float(stats.spearmanr(fs.loc[list(L.PROVINCES)], sub23.loc[list(L.PROVINCES)])[0])
    # empirical-Bayes shrinkage of the 2023 cross-section (used by the sealed survey-year forecaster S3)
    r23 = ref[ref.survey_year == 2023].set_index("province").loc[list(L.PROVINCES)]
    tau2 = max(0.0, float(np.var(r23["pfdr_pct"], ddof=1) - np.mean(r23["se_pp"] ** 2)))
    w = tau2 / (tau2 + r23["se_pp"] ** 2)
    need = L.required_forecast_sd_over_se(0.75)
    out = {
        "n_reference_observations": int(len(ref)), "n_provinces": int(ref.province.nunique()),
        "survey_years": sorted(int(y) for y in ref.survey_year.unique()),
        "independent_changes": int(len(ch)),
        "changes": ch.to_dict(orient="records"),
        "n_changes_exceeding_sampling_error_90": int(ch["exceeds_sampling_error_90"].sum()),
        "heterogeneity": {str(k): v for k, v in het.items()},
        "p_highest": {str(k): v for k, v in ranks.items()},
        "spearman_2021_vs_2023_observed": rho_obs,
        "rank_stability_p_if_no_true_change": p_rank,
        "n_changes_exceeding_sampling_error_95": int(ch["exceeds_sampling_error_95"].sum()),
        "spearman_food_share_vs_subsistence_2023": rho_fs,
        "cv_range_pct": [float(ref.cv_pct.min()), float(ref.cv_pct.max())],
        "se_range_pp": [float(ref.se_pp.min()), float(ref.se_pp.max())],
        "tolerance_range_pp": [float(ref.tolerance_pp.min()), float(ref.tolerance_pp.max())],
        "required_forecast_sd_over_se_for_75pct_within": need,
        "required_forecast_rmse_pp": {f"{r.province} {r.survey_year}": float(need * r.se_pp) for r in ref.itertuples()},
        "eb_2023": {"tau2": tau2, "mean": float(r23["pfdr_pct"].mean()), "weights": {p: float(v) for p, v in w.items()}},
        "fnri_fies_2021": {p: {"value": v[0], "ci90": [v[1], v[2]], "se": (v[2] - v[1]) / (2 * L.Z90)}
                           for p, v in L.FNRI_FIES_2021.items()},
        "fnri_cis_overlap": bool(L.FNRI_FIES_2021["Batangas"][2] >= L.FNRI_FIES_2021["Cavite"][1]),
    }
    L.dump(out, OUT / "reference_uncertainty.json")

    # E130_REFERENCE_SCORE_DATA.csv: provincial reference rows, then cross-check and regional rows kept apart
    rows = []
    for r in ref.itertuples():
        rows.append({"reference_id": f"PFDR-{r.province}-{r.survey_year}", "role": "provincial food-deprivation reference (owner, 2026-10-31)",
                     "construct": "food deprivation: share of the population whose per-capita income is below the provincial food threshold",
                     "geography": "province" + (" (excl. Lucena City)" if r.province == "Quezon" else ""), "province": r.province,
                     "period": str(r.survey_year), "frequency": "FIES survey year (2021, 2023)", "value": r.pfdr_pct, "unit": "% of population",
                     "cv_pct": r.cv_pct, "se": round(r.se_pp, 4), "ci90_lo": round(r.ci90_lo, 4), "ci90_hi": round(r.ci90_hi, 4),
                     "tolerance": round(r.tolerance_pp, 4), "publication_date": r.publication_date,
                     "source": "PSA official poverty statistics (OpenSTAT), vintage published 2024-08-15",
                     "used_as": "reference score (PFDR v1); never a quarterly label"})
    for p, (v, lo, hi) in L.FNRI_FIES_2021.items():
        rows.append({"reference_id": f"FIES-{p}-2021", "role": "household food-insecurity reference (owner)",
                     "construct": "moderate or severe household food insecurity (FIES 8 items)", "geography": "province (ENNS 2021 domain)",
                     "province": p, "period": "2021", "frequency": "one round", "value": v, "unit": "% of households",
                     "cv_pct": "", "se": round((hi - lo) / (2 * L.Z90), 4), "ci90_lo": lo, "ci90_hi": hi, "tolerance": "",
                     "publication_date": "2022 (FNRI dissemination deck)", "source": "DOST-FNRI ENNS 2021",
                     "used_as": "construct cross-check only (2 provinces)"})
    for y, v in L.FNRI_REGIONAL.items():
        rows.append({"reference_id": f"FIES-CALABARZON-{y}", "role": "regional context", "construct": "moderate or severe food insecurity (FIES)",
                     "geography": "region (CALABARZON)", "province": "", "period": str(y), "frequency": "periodic",
                     "value": v, "unit": "%", "cv_pct": "", "se": "", "ci90_lo": "", "ci90_hi": "", "tolerance": "",
                     "publication_date": str(y + 1), "source": "DOST-FNRI " + ("NNS 2023" if y == 2023 else "2025 updating survey"),
                     "used_as": "regional context; never copied to provinces"})
    q = sws_quarter_means()
    q["year"] = q["quarter"].str[:4].astype(int)
    for y, g in q.groupby("year"):
        rows.append({"reference_id": f"SWS-BL-{y}", "role": "regional hunger reference (owner)", "construct": "involuntary hunger, past 3 months",
                     "geography": "Balance Luzon (regional)", "province": "", "period": str(y),
                     "frequency": f"quarterly ({len(g)} quarter means in {y})", "value": round(float(g["bl"].mean()), 4),
                     "unit": "% of families", "cv_pct": "", "se": "", "ci90_lo": "", "ci90_hi": "", "tolerance": "",
                     "publication_date": max(g["published"]).isoformat(), "source": "SWS releases (non-commissioned rounds)",
                     "used_as": "regional pattern only; never copied to provinces"})
    pd.DataFrame(rows).to_csv(ROOT / "E130_REFERENCE_SCORE_DATA.csv", index=False)
    return out


# ------------------------------------------------------------------ data inventory
def _held(rel: str | None) -> tuple[str, str]:
    if not rel:
        return "", ""
    p = REPO / rel
    return (rel, L.sha256(p)) if p.exists() else (rel + " (missing)", "")


E118C = "aipheed-backend-aligned/experiments/E118_FAO_Data_Discovery/data/clean/"
INVENTORY = [
    # id, dataset, agency, role, trigger_group, construct, geography, frequency, in_window_periods, held_path, e130_use
    ("D01", "Subsistence incidence among the population (food poverty)", "PSA", "reference: provincial food deprivation (owner)", "5 Poverty and social vulnerability",
     "food deprivation (income below the food threshold)", "province (Quezon excl. Lucena)", "FIES survey years", "2021, 2023",
     "backend/data/inputs/psa_subsistence_population_2021_2023.csv", "PFDR v1 reference score (survey-year resolution only); lagged value as persistence input"),
    ("D02", "ENNS 2021 household FIES (moderate or severe)", "DOST-FNRI", "reference: household food insecurity (owner)", "reference",
     "experienced food insecurity", "province (Batangas, Cavite only)", "one round", "2021", None,
     "construct cross-check (values from the FNRI deck, E129 Addendum 1)"),
    ("D03", "2022 ENNS household FIES", "DOST-FNRI", "reference candidate", "reference", "experienced food insecurity",
     "province (CALABARZON coverage unverified)", "one round", "2022", None, "not held (request B unsent; eNutrition 503)"),
    ("D04", "NNS 2023 and 2025 updating survey FIES", "DOST-FNRI", "regional context", "reference", "experienced food insecurity",
     "region", "periodic", "2023, 2025", None, "regional context only"),
    ("D05", "CBMS 2024 FIES (SDG 2.1.2.p1)", "PSA / LGUs", "reference candidate", "reference", "experienced food insecurity",
     "barangay / city-municipal (142 LGUs)", "one window", "Jul 2023 - Jun 2024", None, "not held (requests unsent); cross-sectional validation only"),
    ("D06", "SWS involuntary hunger, Balance Luzon", "SWS", "reference: regional hunger (owner)", "food-insecurity history (regional)",
     "experienced hunger", "region (Balance Luzon)", "quarterly", "20 quarters 2021-Q2..2026-Q3",
     "aipheed-backend-aligned/experiments/FINAL_FOOD_INSECURITY_LIGHTGBM/data/sws_area_rounds_2021.csv", "regional reference; never copied to provinces"),
    ("D07", "SWS microdata with province codes", "SWS", "reference candidate", "reference", "experienced hunger",
     "province (about 20-75 respondents per province-round)", "quarterly", "up to 22 quarters", None, "not held; too few respondents per province-round"),
    ("D08", "Operation Timbang Plus (underweight, stunting, wasting 0-59 months)", "NNC / LGUs", "proxy candidate", "5 Poverty and social vulnerability",
     "child undernutrition (utilization outcome)", "province, municipality", "annual", "2021-2025", None, "not held (NNC 403); not a food-insecurity measure"),
    ("D09", "FIES 2023 public-use file: food share of expenditure", "PSA", "proxy (economic access)", "5 Poverty and social vulnerability",
     "food share of family expenditure", "province (Quezon excl. Lucena)", "FIES survey year", "2023",
     "aipheed-backend-aligned/experiments/E119_Preprocessing/E119_PROVINCIAL_ANNUAL_INDICATORS.csv", "construct-coherence check; candidate predictor"),
    ("D10", "2021 city/municipal poverty SAE and POPCEN 2024 (V1 profile)", "PSA", "predictor", "5 Poverty and social vulnerability",
     "poverty (structural vulnerability)", "LGU aggregated to province", "static", "2021 SAE / 2024 POPCEN", "backend/data/inputs/lgu_vulnerability.csv",
     "static predictor (no time variation)"),
    ("D11", "Provincial CPI, food and all items (YoY)", "PSA", "predictor (owner)", "1 Market and food prices", "food-price condition",
     "province", "monthly (quarterly mean)", "2021-01..2026-08", "aipheed-backend-aligned/experiments/E119_Preprocessing/E119_PROVINCIAL_VULNERABILITY_DATASET.csv",
     "predictor; never a target (owner)"),
    ("D12", "Bottom-30% income-group food CPI", "PSA", "predictor", "1 Market and food prices", "food-price condition (poor households)",
     "province", "monthly", "2021+", E118C + "cpi_bottom30_yoy.csv", "predictor (r = 0.94 with all-income food CPI)"),
    ("D13", "Wholesale, retail and farmgate food prices (rice, chicken, pork, tilapia, palay)", "PSA", "predictor", "1 Market and food prices",
     "food prices", "province", "monthly", "2021+", E118C + "retail_cereals.csv", "predictor"),
    ("D14", "Region IV-A CPI", "PSA", "predictor (regional)", "1 Market and food prices", "food-price condition", "region",
     "monthly", "2021+", None, "regional predictor (identical for all provinces)"),
    ("D15", "NASA POWER rainfall and temperature (province centroids)", "NASA", "predictor", "2 Climate and environmental stress",
     "rainfall and temperature anomalies", "province (centroid point)", "monthly", "2021-01..2026-09", E118C + "nasa_power_monthly.csv", "predictor"),
    ("D16", "IBTrACS tropical cyclone tracks (300 km, local 100 km, PAR)", "NOAA", "predictor", "2 Climate and environmental stress",
     "typhoon exposure", "province buffers; PAR national", "quarterly counts", "2021-Q1..2026-Q3", None, "predictor (local counts mostly 0)"),
    ("D17", "ONI / El Nino flag", "NOAA", "predictor (global)", "2 Climate and environmental stress", "ENSO state", "global",
     "monthly", "2021+", None, "shared predictor; E128 found it acts as a period marker"),
    ("D18", "Palay and corn production", "PSA", "predictor", "2 Climate and environmental stress", "agricultural production disruption",
     "province", "quarterly", "2021+", E118C + "prod_palay_corn.csv", "predictor (C3)"),
    ("D19", "Fisheries and aquaculture production", "PSA", "predictor", "2 Climate and environmental stress", "fisheries production disruption",
     "province", "quarterly", "2021+", E118C + "prod_fisheries.csv", "predictor (C4)"),
    ("D20", "Vegetables, root crops, chicken and livestock production", "PSA", "predictor", "2 Climate and environmental stress",
     "food production", "province", "quarterly", "2021+", E118C + "prod_vegetables_rootcrops.csv", "predictor"),
    ("D21", "Provincial unemployment and underemployment (LFS)", "PSA", "predictor", "3 Employment and OFW remittances",
     "labour-market conditions", "province", "annual", "2021-2025 (2025 partial)", "aipheed-backend-aligned/experiments/E119_Preprocessing/E119_PROVINCIAL_ANNUAL_INDICATORS.csv",
     "predictor (annual; stale at quarterly issue dates)"),
    ("D22", "Regional / national LFS (monthly, quarterly)", "PSA", "predictor (regional)", "3 Employment and OFW remittances",
     "labour-market conditions", "region / nation", "quarterly", "2021+", None, "shared predictor"),
    ("D23", "OFW cash remittances", "BSP", "predictor (national)", "3 Employment and OFW remittances", "household income transfers",
     "national", "monthly (quarterly)", "2021+", "aipheed-backend-aligned/experiments/CORRECTED_PIPELINE/out/remittances_quarterly_corrected.csv",
     "shared predictor (no provincial detail)"),
    ("D24", "FSSI v3 news (XLM-R scored, province-tagged articles)", "aiPHeed news pipeline", "predictor", "4 News and NLP",
     "reported food-supply stress", "province (article tags)", "quarterly", "2022-Q4..2026-Q2", None, "predictor (sparse provincially)"),
    ("D25", "GDELT DOC topic shares (shortage, agri supply, jobs, assistance)", "GDELT", "predictor (national)", "4 News and NLP",
     "news attention", "national", "quarterly", "2021+", None, "shared predictor"),
    ("D26", "BERTopic topics on the news corpus (E64)", "aiPHeed news pipeline", "predictor", "4 News and NLP", "news topics",
     "mostly national / regional", "quarterly", "2021+", None, "E64: no forecast gain"),
    ("D27", "Provincial food CPI YoY as a target", "PSA", "rejected target", "1 Market and food prices", "food-price condition", "province",
     "quarterly", "23 quarters", "aipheed-backend-aligned/experiments/E119_Preprocessing/E119_PROVINCIAL_VULNERABILITY_DATASET.csv",
     "same data as D11; rejected as target (owner: predictor; not food insecurity)"),
    ("D28", "FIRI v2 and FIRI3 provincial scores", "aiPHeed", "rejected target", "constructed index", "index built from the predictors",
     "province", "quarterly", "2021+", "backend/app/ml/inference/firi3.py", "rejected as supervised ground truth (circular)"),
    ("D29", "Subsistence incidence 2025 round (2025 Full Year Poverty Statistics, released 2026-08-21)", "PSA",
     "reference: provincial food deprivation (owner), third round", "5 Poverty and social vulnerability",
     "food deprivation (income below the food threshold)", "province", "FIES survey year", "2025", None,
     "not held: PSA PDF behind a bot check (not bypassed), OpenSTAT not updated; scores the E130 seal once the owner supplies it"),
    ("D30", "2025 Full Year Official Poverty Statistics workbook (Tables 1, 2, 5, 6, 15: poverty incidence, magnitudes, groupings; 2021, 2023, 2025)",
     "PSA (owner-supplied 2026-10-31)", "provenance only", "5 Poverty and social vulnerability", "poverty (food and non-food needs), not PFDR",
     "region, province", "FIES survey year", "2021, 2023, 2025",
     "aipheed-backend-aligned/experiments/E130_Provincial_Risk_Score_Forecasting/data/owner_supplied/psa_2025_fy_workbook/2025 Full Year Official Poverty Statistics_24Aug2026_0.xlsx",
     "no subsistence table, so the seal stays unscored; no value extracted (poverty is not the PFDR target)"),
]


def inventory() -> pd.DataFrame:
    cols = ["dataset_id", "dataset", "agency", "role", "trigger_group", "construct", "geography", "frequency",
            "in_window_periods", "held_path", "e130_use"]
    df = pd.DataFrame(INVENTORY, columns=cols)
    paths, hashes = zip(*(_held(p) for p in df["held_path"]))
    df["held_path"], df["sha256"] = paths, hashes
    df["held"] = np.where(df["sha256"] != "", "yes", np.where(df["dataset_id"].isin(["D02", "D04", "D14", "D16", "D17", "D22", "D24", "D25", "D26"]),
                                                              "yes (values in E-series outputs)", "no"))
    df.to_csv(ROOT / "E130_DATA_INVENTORY.csv", index=False)
    return df


# ------------------------------------------------------------------ provincial feature availability
GROUP = {"A": "1 Market and food prices", "C2": "2 Climate and environmental stress", "C3": "2 Climate and environmental stress (production)",
         "C4": "2 Climate and environmental stress (production)", "N1": "4 News and NLP"}
FAMILY = {"A1_food_projection_asof": "A1", "A1_gap_projection_asof": "A1", "A2_headline_above_usual_asof": "A2",
          "cpi_food_yoy_pct": "A1", "cpi_headline_yoy_pct": "A2", "rice_wholesale_yoy_pct": "A3", "retail_rice_regular_yoy_pct": "A3",
          "retail_rice_regular_price_php_kg": "A3", "retail_rice_regular_volatility_cv": "A3", "farmgate_palay_yoy_pct": "A3",
          "retail_chicken_yoy_pct": "A1", "retail_pork_yoy_pct": "A1", "retail_tilapia_yoy_pct": "A1", "cpi_bottom30_food_yoy_pct": "A1",
          "C2_typhoons_300km": "C2", "typhoons_local_100km": "C2", "C3_palay_corn_drop": "C3", "C4_fisheries_drop": "C4",
          "aquaculture_production_yoy_pct": "C4", "N1_fssi_v3": "N1", "N1_admitted_articles": "N1",
          "rainfall_total_mm": "climate (no FIRI family)", "rainfall_anomaly_mm": "climate (no FIRI family)",
          "temperature_anomaly_c": "climate (no FIRI family)", "vegetables_rootcrops_production_yoy_pct": "production (no FIRI family)",
          "chicken_production_yoy_pct": "production (no FIRI family)", "livestock_production_yoy_pct": "production (no FIRI family)"}


def _group(f: str, fam: str) -> str:
    if fam.startswith("A"):
        return GROUP["A"]
    if fam in GROUP:
        return GROUP[fam]
    return "2 Climate and environmental stress" + (" (production)" if fam.startswith("production") else "")


def _period_end(p: str) -> date | None:
    if not isinstance(p, str) or not p:
        return None
    if "-Q" in p:
        return L.qend(p)
    y, m = int(p[:4]), int(p[5:7])
    return (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))


def _period_quarter(p: str) -> str | None:
    if not isinstance(p, str) or not p:
        return None
    return p if "-Q" in p else L.quarter_of(date(int(p[:4]), int(p[5:7]), 1))


def decompose(v: pd.DataFrame) -> dict:
    """v: origins x provinces. Variance shares: common quarter mean, persistent province mean, province-quarter rest."""
    x = v.dropna(how="any")
    if len(x) < 3:
        return {"share_time": np.nan, "share_province_persistent": np.nan, "share_province_quarter": np.nan}
    g = x.values.mean()
    tot = ((x.values - g) ** 2).sum()
    if tot == 0:
        return {"share_time": np.nan, "share_province_persistent": np.nan, "share_province_quarter": np.nan}
    tm = x.mean(axis=1).values[:, None]
    dev = x.values - tm
    pm = dev.mean(axis=0)[None, :]
    st = (x.shape[1] * ((tm - g) ** 2).sum()) / tot
    sp = (x.shape[0] * (pm ** 2).sum()) / tot
    return {"share_time": float(st), "share_province_persistent": float(sp), "share_province_quarter": float(1 - st - sp)}


def feature_availability() -> pd.DataFrame:
    p = pd.read_csv(L.PANEL)
    p["issue"] = pd.to_datetime(p["issue_date"]).dt.date
    rows = []
    for f, fam in FAMILY.items():
        st_col = "A_status" if f.startswith(("A1_", "A2_")) else f + "__status"
        pe_col = "A_cpi_month" if f.startswith(("A1_", "A2_")) else f + "__period"
        val = p[f]
        st = p[st_col].fillna("missing (none available before issue)")
        per = p[pe_col]
        avail = val.notna()
        lag_days = [(i - _period_end(q)).days for i, q, a in zip(p["issue"], per, avail) if a and _period_end(q)]
        stale_q = [L.qi(L.quarter_of(i)) - L.qi(_period_quarter(q)) for i, q, a in zip(p["issue"], per, avail) if a and _period_quarter(q)]
        wide = p.pivot(index="origin", columns="province", values=f)
        same = wide.dropna().nunique(axis=1).eq(1).mean() if len(wide.dropna()) else np.nan
        dec = decompose(wide)
        acf = np.nan
        if dec["share_time"] == dec["share_time"]:
            dev = (wide.sub(wide.mean(axis=1), axis=0)).dropna()
            if len(dev) > 4:
                acf = float(np.nanmean([dev[c].autocorr(lag=2) for c in dev.columns]))
        rows.append({
            "feature": f, "firi_v2_family": fam, "trigger_group": _group(f, fam), "resolution": "province",
            "observation_period_first": per[avail].min() if avail.any() else "", "observation_period_last": per[avail].max() if avail.any() else "",
            "rows": int(len(p)), "available_rows": int(avail.sum()), "missing_pct": round(100 * (1 - avail.mean()), 1),
            "verified_rows": int((st == "verified").sum()),
            "rule_unverified_rows": int((st == "rule_unverified").sum()),
            "median_days_period_end_to_issue": float(np.median(lag_days)) if lag_days else np.nan,
            "median_quarters_behind_issue_quarter": float(np.median(stale_q)) if stale_q else np.nan,
            "information_horizon_at_lead2_quarters": float(np.median(stale_q)) + 1 if stale_q else np.nan,
            "identical_across_provinces_share": round(float(same), 3) if same == same else np.nan,
            "share_common_quarter_effect": round(dec["share_time"], 3) if dec["share_time"] == dec["share_time"] else np.nan,
            "share_persistent_province_effect": round(dec["share_province_persistent"], 3) if dec["share_province_persistent"] == dec["share_province_persistent"] else np.nan,
            "share_province_quarter_specific": round(dec["share_province_quarter"], 3) if dec["share_province_quarter"] == dec["share_province_quarter"] else np.nan,
            "province_deviation_autocorr_lag2": round(acf, 3) if acf == acf else np.nan,
            "publication_date_status": "verified dates" if (st == "verified").any() and not (st == "rule_unverified").any() else
                                       ("rule-based (unverified) dates" if (st == "rule_unverified").any() else "n/a"),
            "revision_status": "as published; archived vintage where verified (E119/E122)",
            "source": "E119 point-in-time provincial dataset",
            "eligible_as_predictor": "yes (point-in-time)" if avail.mean() >= 0.5 else "limited (sparse)",
        })
    # features outside the provincial quarterly panel
    ann = pd.read_csv(L.ANNUAL)
    for feat, label in (("provincial_unemployment_rate_pct_annual", "E1"), ("provincial_underemployment_rate_pct_annual", "E1")):
        a = ann[ann.feature == feat].pivot(index="reference_year", columns="province", values="value")
        dec = decompose(a)
        rows.append({"feature": feat, "firi_v2_family": label, "trigger_group": "3 Employment and OFW remittances", "resolution": "province, annual",
                     "observation_period_first": str(a.index.min()), "observation_period_last": str(a.index.max()), "rows": int(a.size),
                     "available_rows": int(a.notna().sum().sum()), "missing_pct": round(100 * float(a.isna().mean().mean()), 1),
                     "verified_rows": 0, "rule_unverified_rows": int(a.notna().sum().sum()),
                     "median_days_period_end_to_issue": np.nan, "median_quarters_behind_issue_quarter": np.nan,
                     "information_horizon_at_lead2_quarters": "6-9 (annual, published by 30 June of the next year)",
                     "identical_across_provinces_share": 0.0,
                     "share_common_quarter_effect": round(dec["share_time"], 3), "share_persistent_province_effect": round(dec["share_province_persistent"], 3),
                     "share_province_quarter_specific": round(dec["share_province_quarter"], 3), "province_deviation_autocorr_lag2": np.nan,
                     "publication_date_status": "rule-based (unverified) dates", "revision_status": "as published",
                     "source": "PSA LFS provincial annual (E119)", "eligible_as_predictor": "yes (annual, stale)"})
    shared = [("E2_remittance_decline_pct", "E2", "3 Employment and OFW remittances", "national, quarterly"),
              ("unemployment_rate_pct (regional/national)", "E1", "3 Employment and OFW remittances", "region / nation, quarterly"),
              ("oni_quarter_mean", "C1", "2 Climate and environmental stress", "global"),
              ("typhoons_PAR", "C2", "2 Climate and environmental stress", "national"),
              ("region_cpi_food_yoy_pct", "A1", "1 Market and food prices", "region"),
              ("news_gdelt_*_share", "N1", "4 News and NLP", "national"),
              ("H1_bl_latest (SWS Balance Luzon hunger)", "H1", "food-insecurity history (regional reference)", "region (Balance Luzon)"),
              ("V1_vulnerability_profile", "V1", "5 Poverty and social vulnerability", "province, static (2021 SAE / 2024 POPCEN)"),
              ("subsistence_incidence_pct (lagged reference)", "V1", "5 Poverty and social vulnerability", "province, survey years 2021/2023"),
              ("fies_food_share_of_expenditure_pct", "V1", "5 Poverty and social vulnerability", "province, 2023 only")]
    for feat, fam, grp, res in shared:
        prov = res.startswith("province")
        rows.append({"feature": feat, "firi_v2_family": fam, "trigger_group": grp, "resolution": res, "rows": "", "available_rows": "",
                     "missing_pct": "", "identical_across_provinces_share": 0.0 if prov else 1.0,
                     "share_common_quarter_effect": 0.0 if prov else 1.0,
                     "share_persistent_province_effect": 1.0 if prov else 0.0, "share_province_quarter_specific": 0.0,
                     "publication_date_status": "see E119 / CORRECTED_PIPELINE", "revision_status": "as published",
                     "source": "E119 regional dataset / CORRECTED_PIPELINE / PSA", "information_horizon_at_lead2_quarters": "",
                     "eligible_as_predictor": "yes, but identical for all provinces" if not prov else "yes, but static or survey-year only"})
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "E130_PROVINCIAL_FEATURE_AVAILABILITY.csv", index=False)
    return df


# ------------------------------------------------------------------ issue dates and operational leads
def mapping() -> pd.DataFrame:
    p = pd.read_csv(L.PANEL)
    s = pd.read_csv(L.SWS)
    s = s[~s["commissioned"].astype(bool)].copy()
    s["published"] = pd.to_datetime(s["published"]).dt.date
    held_vintage = date(2024, 8, 15)
    rows = []
    for r in p.sort_values(["origin", "province"]).itertuples():
        D = L.qs(L.qi(r.origin) + 1)
        issue = L.qstart(D)
        assert r.issue_date == issue.isoformat(), (r.origin, r.issue_date)
        known = s[s["published"] < issue]
        sws_newest = max(known["quarter"], key=L.qi) if len(known) else None
        prev = s[s["quarter"] == r.origin]
        anchored = None
        if len(prev):
            d = prev["published"].max()
            if L.qstart(D) <= d <= L.qend(D):
                anchored = d + timedelta(days=1)
        lfs = max([y for y in range(2021, 2027) if date(y + 1, 6, 30) < issue], default=None)
        pfdr = 2023 if issue > held_vintage else None
        for k in L.LEADS:
            tgt = L.operational_target(D, k)
            tq = L.qi(tgt)
            rows.append({
                "dashboard_quarter": D, "province": r.province, "issue_date": issue.isoformat(),
                "issue_rule": "dashboard (app/quarterly/target.py): 00:00 PHT on the first day of the dashboard quarter",
                "latest_complete_calendar_quarter": r.origin, "operational_lead": k, "target_quarter": tgt,
                "operational_meaning": {1: "current dashboard quarter (incomplete)", 2: "next quarter = dashboard forecast target (minimum operational)",
                                        3: "two quarters after the dashboard quarter", 4: "three quarters after the dashboard quarter"}[k],
                "meets_minimum_operational_horizon": k >= 2,
                "internal_model_lead": k, "e128_origin": r.origin, "e128_lead": k,
                "months_issue_to_target_end": 3 * k,
                "sws_newest_quarter_at_issue": sws_newest or "", "sws_newest_published": known["published"].max().isoformat() if len(known) else "",
                "sws_information_horizon_q": (tq - L.qi(sws_newest)) if sws_newest else "",
                "release_anchored_issue_date": anchored.isoformat() if anchored else "",
                "sws_information_horizon_release_anchored_q": k if anchored else "",
                "pfdr_newest_survey_year_at_issue_held_vintage": pfdr or "",
                "pfdr_information_horizon_q": (tq - L.qi(f"{pfdr}-Q4")) if pfdr else "",
                "target_quarter_has_provincial_reference": False,
                "target_in_pfdr_survey_year": tgt[:4] in ("2021", "2023"),
                "latest_cpi_month": r.A_cpi_month, "cpi_status": r.A_status if isinstance(r.A_status, str) else "missing",
                "latest_lfs_provincial_year": lfs or "", "lfs_status": "rule_unverified (by 30 June of the next year)",
                "latest_news_quarter": r.N1_fssi_v3__period if isinstance(r.N1_fssi_v3__period, str) else "",
                "latest_rainfall_quarter": r.rainfall_total_mm__period if isinstance(r.rainfall_total_mm__period, str) else "",
                "latest_typhoon_quarter": r.typhoons_local_100km__period if isinstance(r.typhoons_local_100km__period, str) else "",
                "latest_production_quarter": r.C3_palay_corn_drop__period if isinstance(r.C3_palay_corn_drop__period, str) else "",
                "evaluable_provincial_target": False,
            })
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "E130_ISSUE_DATE_AND_OPERATIONAL_LEAD_MAPPING.csv", index=False)
    # summary: SWS information horizon by lead, both issue policies; the E128 cross-check
    one = df[df.province == L.PROVINCES[0]]
    summ = {"dashboard_quarters": [one.dashboard_quarter.min(), one.dashboard_quarter.max()], "rows": int(len(df)),
            "sws_horizon_quarter_start": {}, "sws_horizon_release_anchored": {},
            "release_anchored_available_share": float((one[one.operational_lead == 1]["release_anchored_issue_date"] != "").mean()),
            "median_release_day_in_quarter": None}
    for k in L.LEADS:
        h = pd.to_numeric(one[one.operational_lead == k]["sws_information_horizon_q"], errors="coerce").dropna()
        summ["sws_horizon_quarter_start"][str(k)] = {str(int(v)): int(c) for v, c in h.value_counts().sort_index().items()}
        a = pd.to_numeric(one[one.operational_lead == k]["sws_information_horizon_release_anchored_q"], errors="coerce").dropna()
        summ["sws_horizon_release_anchored"][str(k)] = {str(int(v)): int(c) for v, c in a.value_counts().sort_index().items()}
    days = [(date.fromisoformat(a) - L.qstart(q)).days for a, q in
            zip(one[one.operational_lead == 1]["release_anchored_issue_date"], one[one.operational_lead == 1]["dashboard_quarter"]) if a]
    summ["median_release_day_in_quarter"] = float(np.median(days)) if days else None
    e128 = pd.read_csv(L.E128 / "E128_ISSUE_DATE_AND_LEAD_MAPPING.csv")
    e = e128.merge(one.rename(columns={"e128_origin": "origin", "e128_lead": "lead"})[["origin", "lead", "target_quarter", "sws_information_horizon_q"]],
                   on=["origin", "lead"], suffixes=("_e128", "_e130"))
    summ["e128_cross_check"] = {"rows_compared": int(len(e)),
                                "target_quarters_identical": bool((e["target_quarter_e128"] == e["target_quarter_e130"]).all()),
                                "sws_horizons_identical": bool((pd.to_numeric(e["true_sws_horizon_q"], errors="coerce").fillna(-1)
                                                                == pd.to_numeric(e["sws_information_horizon_q"], errors="coerce").fillna(-1)).all())}
    L.dump(summ, OUT / "mapping_summary.json")
    return df


# ------------------------------------------------------------------ target gate
CANDIDATES = [
    # id, name, owner role, construct, G1 FI/deprivation, provinces with values, in-window periods per province,
    # quarterly, dated, held, independent of predictors, numeric with uncertainty
    ("C1", "PSA provincial subsistence incidence (PFDR v1)", "provincial food-deprivation reference", "food deprivation (income below the food threshold)",
     True, 5, 2, False, True, True, True, True),
    ("C2", "FNRI ENNS 2021 household FIES", "household food-insecurity reference", "experienced food insecurity", True, 2, 1, False, True, True, True, True),
    ("C3", "FNRI 2022 ENNS household FIES", "household food-insecurity reference", "experienced food insecurity", True, 0, 1, False, True, False, True, True),
    ("C4", "PSA CBMS 2024 FIES (142 LGUs)", "household food-insecurity reference (candidate)", "experienced food insecurity", True, 5, 1, False, True, False, True, True),
    ("C5", "SWS Balance Luzon involuntary hunger", "regional hunger reference", "experienced hunger", True, 0, 20, True, True, True, True, True),
    ("C6", "SWS microdata with province codes", "none (not held)", "experienced hunger", True, 5, 20, True, False, False, True, False),
    ("C7", "NNC Operation Timbang Plus", "none", "child undernutrition (utilization)", False, 5, 5, False, True, False, True, False),
    ("C8", "PSA FIES 2023 food share of expenditure", "none", "economic-access proxy", False, 5, 1, False, False, True, True, False),
    ("C9", "Composite of C1 + C2 (+ C8)", "none", "mixed constructs; no defensible aggregation", False, 2, 1, False, True, True, True, False),
    ("C10", "Provincial food CPI YoY", "predictor (owner)", "food-price condition", False, 5, 23, True, True, True, False, False),
    ("C11", "FIRI3 / FIRI v2 provincial scores", "none", "constructed index built from the predictors", False, 5, 23, True, True, True, False, False),
]


def gate() -> dict:
    cols = ["id", "candidate", "owner_role", "construct", "g1_fi_or_deprivation", "provinces_with_values", "periods_in_window",
            "quarterly", "dated", "held", "independent_of_predictors", "numeric_with_uncertainty"]
    c = pd.DataFrame(CANDIDATES, columns=cols)
    c["G1_construct"] = c["g1_fi_or_deprivation"]
    c["G2_all_five_provinces"] = c["provinces_with_values"] == 5
    c["G3_repeated_10_periods"] = c["periods_in_window"] >= 10
    c["G4_dated_publication"] = c["dated"]
    c["G5_held"] = c["held"]
    c["G6_not_built_from_predictors"] = c["independent_of_predictors"]
    c["G7_numeric_with_uncertainty"] = c["numeric_with_uncertainty"]
    c["G8_quarterly_lead2_evaluable"] = c["quarterly"] & c["G2_all_five_provinces"] & c["G3_repeated_10_periods"]
    gs = [g for g in c.columns if g.startswith("G") and g[1].isdigit()]
    c["passes_all"] = c[gs].all(axis=1)
    c["failed_criteria"] = c[gs].apply(lambda r: ", ".join(g.split("_")[0] for g in gs if not r[g]), axis=1)
    c.to_csv(OUT / "gate_candidates.csv", index=False)
    res = {"criteria": gs, "any_candidate_passes": bool(c["passes_all"].any()),
           "decision": "BLOCKED: no quarterly provincial reference passes G1-G8; provincial model training is not authorized",
           "pfdr_valid_survey_year_reference": bool(c.set_index("id").loc["C1", ["G1_construct", "G2_all_five_provinces", "G4_dated_publication",
                                                                             "G5_held", "G6_not_built_from_predictors", "G7_numeric_with_uncertainty"]].all()),
           "candidates": c[["id", "candidate", "passes_all", "failed_criteria"]].to_dict(orient="records")}
    L.dump(res, OUT / "gate.json")
    return res


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    manifest()
    r = reference()
    inv = inventory()
    fa = feature_availability()
    mp = mapping()
    g = gate()
    print("reference:", r["n_reference_observations"], "obs;", r["n_changes_exceeding_sampling_error_90"], "real changes")
    print("inventory:", len(inv), "datasets; features:", len(fa), "; mapping rows:", len(mp))
    print("gate:", g["decision"])
