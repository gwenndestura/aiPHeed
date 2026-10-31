"""
E130 diagnostics D1-D15 (protocol section 10) and the planning simulation (section 11). No model is fitted to any
provincial target; the simulation uses synthetic data only and is labelled as such everywhere it is reported.

Run:  python runner/diagnostics_e130.py      (backend venv; about 1 minute)
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e130_lib as L  # noqa: E402

ROOT, OUT = L.ROOT, L.OUT


def _load(name):
    return json.load(open(OUT / name, encoding="utf-8"))


def gate_recheck() -> dict:
    """Section 6 re-check: the 2025 PSA provincial round was found published but not obtainable (bot check, OpenSTAT
    not updated). It is added as candidate C12 under the same G1-G8; the frozen gate.json is not modified."""
    c = pd.read_csv(OUT / "gate_candidates.csv")
    new = {"id": "C12", "candidate": "PSA provincial subsistence 2025 round (published 2026-08-21; PDF behind a bot check; not on OpenSTAT)",
           "owner_role": "provincial food-deprivation reference", "construct": "food deprivation (income below the food threshold)",
           "g1_fi_or_deprivation": True, "provinces_with_values": 5, "periods_in_window": 3, "quarterly": False, "dated": True,
           "held": False, "independent_of_predictors": True, "numeric_with_uncertainty": True}
    new.update({"G1_construct": True, "G2_all_five_provinces": True, "G3_repeated_10_periods": False, "G4_dated_publication": True,
                "G5_held": False, "G6_not_built_from_predictors": True, "G7_numeric_with_uncertainty": True,
                "G8_quarterly_lead2_evaluable": False, "passes_all": False, "failed_criteria": "G3, G5, G8"})
    c = pd.concat([c, pd.DataFrame([new])], ignore_index=True)
    c.to_csv(OUT / "gate_recheck_candidates.csv", index=False)
    res = {"any_candidate_passes": bool(c["passes_all"].any()), "decision_unchanged": not bool(c["passes_all"].any()),
           "new_candidates": ["C12"],
           "pfdr_rounds_per_province": {"held": 2, "published_not_held": 1, "survey_frequency_years": 2},
           "first_survey_year_with_10_rounds": 2021 + 2 * 9,
           "note": "biennial rounds never give a quarterly label; 10 rounds per province would be reached with survey year 2039"}
    L.dump(res, OUT / "gate_recheck.json")
    return res


def cpi_by_period(panel: pd.DataFrame, col: str = "cpi_food_yoy_pct") -> pd.DataFrame:
    """Each province's quarterly value of `col` by observation period, read where that period first became the newest
    available at an issue date (point-in-time first release in the E119 panel)."""
    d = panel[panel[col].notna()][["province", col, col + "__period", "issue_date"]].sort_values("issue_date")
    d = d.drop_duplicates(["province", col + "__period"], keep="first")
    return d.pivot(index=col + "__period", columns="province", values=col)


def diagnostics() -> dict:
    panel = pd.read_csv(L.PANEL)
    ref = L.load_reference()
    ru = _load("reference_uncertainty.json")
    fa = pd.read_csv(ROOT / "E130_PROVINCIAL_FEATURE_AVAILABILITY.csv")
    mp = pd.read_csv(ROOT / "E130_ISSUE_DATE_AND_OPERATIONAL_LEAD_MAPPING.csv")
    ann = pd.read_csv(L.ANNUAL)
    D = {}

    # D2 / D11 / D12 reference variation and noise
    het = ru["heterogeneity"]
    D["D2_variation"] = {"changes_beyond_90pct_sampling_error": ru["n_changes_exceeding_sampling_error_90"],
                         "changes_beyond_95pct_sampling_error": ru["n_changes_exceeding_sampling_error_95"],
                         "rank_reversal_spearman": ru["spearman_2021_vs_2023_observed"],
                         "rank_stability_p_if_no_true_change": ru["rank_stability_p_if_no_true_change"]}
    D["D11_noise"] = {"cv_range_pct": ru["cv_range_pct"],
                      "signal_to_noise": {y: float(np.sqrt(h["tau2_dl"]) / h["mean_sampling_se"]) for y, h in het.items()}}
    D["D12_province_differences"] = {y: {"Q": h["Q"], "p": h["p"]} for y, h in het.items()}

    # D3 / D13 / D14 observations against N1
    D["D3_observations"] = {"provincial_reference_values": ru["n_reference_observations"], "independent_changes": ru["independent_changes"],
                            "quarterly_provincial_reference_values": 0, "N1_needs": {"target_quarters": 10, "rows": 40}}
    D["D13_lead2_support"] = {"evaluable_lead2_rows": int(mp[(mp.operational_lead == 2) & mp.evaluable_provincial_target].shape[0]),
                              "lead2_rows_in_mapping": int((mp.operational_lead == 2).sum())}
    D["D14_rules"] = {"N1": "fails (0 quarterly target observations)", "N2-N7": "not evaluable without a target",
                      "R1-R7": "not evaluable (no target; no approved category thresholds)"}

    # D4 CPI dominance and effective sample size
    cpi = fa.set_index("feature").loc["cpi_food_yoy_pct"]
    icc = float(cpi["share_common_quarter_effect"])
    D["D4_cpi"] = {"share_common_quarter_effect": icc, "share_persistent_province_effect": float(cpi["share_persistent_province_effect"]),
                   "share_province_quarter_specific": float(cpi["share_province_quarter_specific"]),
                   "province_deviation_autocorr_lag2": float(cpi["province_deviation_autocorr_lag2"]),
                   "effective_rows_of_115": float(115 / (1 + (5 - 1) * icc))}

    # D5 food prices vs food deprivation (descriptive, N = 5)
    w = cpi_by_period(panel)
    infl = w.loc[[q for q in w.index if "2022-Q1" <= q <= "2023-Q4"]]
    cum = (infl.groupby(infl.index.str[:4]).mean() / 100 + 1).prod() - 1
    ch = pd.DataFrame(ru["changes"]).set_index("province")
    un = ann[ann.feature == "provincial_unemployment_rate_pct_annual"].pivot(index="province", columns="reference_year", values="value")
    un.columns = un.columns.astype(str)
    d_un = (un["2023"].astype(float) - un["2021"].astype(float)).loc[list(L.PROVINCES)]
    rows = [{"province": p, "pfdr_2021": ch.loc[p, "value_y0"], "pfdr_2023": ch.loc[p, "value_y1"], "pfdr_change_pp": ch.loc[p, "change_pp"],
             "pfdr_change_z": ch.loc[p, "z"], "food_cpi_mean_yoy_2022_pct": float(infl.loc[[q for q in infl.index if q.startswith("2022")], p].mean()),
             "food_cpi_mean_yoy_2023_pct": float(infl.loc[[q for q in infl.index if q.startswith("2023")], p].mean()),
             "food_price_rise_2021_to_2023_pct": float(100 * cum[p]), "unemployment_change_2021_to_2023_pp": float(d_un[p])}
            for p in L.PROVINCES]
    d5 = pd.DataFrame(rows)
    d5.to_csv(OUT / "d5_prices_vs_deprivation.csv", index=False)
    D["D5_prices_vs_deprivation"] = {
        "provinces_with_food_inflation_positive": int((d5.food_price_rise_2021_to_2023_pct > 0).sum()),
        "provinces_where_pfdr_fell": int((d5.pfdr_change_pp < 0).sum()),
        "spearman_food_price_rise_vs_pfdr_change": float(stats.spearmanr(d5.food_price_rise_2021_to_2023_pct, d5.pfdr_change_pp)[0]),
        "spearman_unemployment_change_vs_pfdr_change": float(stats.spearmanr(d5.unemployment_change_2021_to_2023_pp, d5.pfdr_change_pp)[0]),
        "food_price_rise_range_pct": [float(d5.food_price_rise_2021_to_2023_pct.min()), float(d5.food_price_rise_2021_to_2023_pct.max())],
        "note": "N = 5 provinces, one change each: descriptive only, no inference"}
    sws = pd.read_csv(ROOT / "E130_REFERENCE_SCORE_DATA.csv")
    sws = sws[sws.reference_id.str.startswith("SWS-BL")].set_index("period")["value"]
    D["D5_prices_vs_deprivation"]["sws_balance_luzon_annual_mean"] = {str(k): float(v) for k, v in sws.items()}

    # D6 staleness at operational Lead 2 (from the mapping; one province, all dashboard quarters)
    one = mp[(mp.province == L.PROVINCES[0]) & (mp.operational_lead == 2)].copy()
    lfs_h = [L.qi(t) - L.qi(f"{int(y)}-Q4") for t, y in zip(one.target_quarter, one.latest_lfs_provincial_year) if y == y and str(y) != ""]
    pf_h = pd.to_numeric(one.pfdr_information_horizon_q, errors="coerce").dropna()
    v1_h = [L.qi(t) - L.qi("2021-Q4") for t in one.target_quarter]
    D["D6_staleness_lead2_quarters"] = {
        "provincial_lfs_annual": {"min": int(min(lfs_h)), "median": float(np.median(lfs_h)), "max": int(max(lfs_h)), "n_quarters": len(lfs_h)},
        "pfdr_survey_year": {"min": int(pf_h.min()), "median": float(pf_h.median()), "max": int(pf_h.max()),
                             "dashboard_quarters_with_any_pfdr": int(len(pf_h)), "of": int(len(one))},
        "v1_static_2021": {"min": int(min(v1_h)), "median": float(np.median(v1_h)), "max": int(max(v1_h))}}

    # D7 / D8 / D9 / D10 predictor geography and period markers
    fa_i = fa.set_index("feature")
    loc = panel.pivot(index="origin", columns="province", values="typhoons_local_100km")
    D["D7_climate"] = {"typhoon_local_identical_across_provinces_share": float(fa_i.loc["typhoons_local_100km", "identical_across_provinces_share"]),
                       "typhoon_local_zero_share": float((loc.fillna(0) == 0).to_numpy().mean()),
                       "rainfall_quarters_behind_issue": float(fa_i.loc["rainfall_total_mm", "median_quarters_behind_issue_quarter"]),
                       "rainfall_common_quarter_share": float(fa_i.loc["rainfall_total_mm", "share_common_quarter_effect"]),
                       "oni_par_provincial_variation": "none (national/global)"}
    D["D8_remittances"] = {"geography": "national", "identical_across_provinces_share": 1.0}
    art = panel.pivot(index="origin", columns="province", values="N1_admitted_articles")
    D["D9_news"] = {"fssi_v3_missing_pct": float(fa_i.loc["N1_fssi_v3", "missing_pct"]),
                    "fssi_v3_persistent_province_share": float(fa_i.loc["N1_fssi_v3", "share_persistent_province_effect"]),
                    "articles_per_province_quarter_median": float(np.nanmedian(art.to_numpy())),
                    "province_quarters_with_zero_articles_share": float(np.nanmean(art.to_numpy() == 0)),
                    "articles_by_province_mean": {p: float(art[p].mean()) for p in L.PROVINCES}}
    prov = fa[(fa.resolution == "province") & fa.share_common_quarter_effect.notna()]
    D["D10_period_markers"] = {"provincial_predictors": int(len(prov)),
                               "median_common_quarter_share": float(prov.share_common_quarter_effect.median()),
                               "predictors_with_common_share_above_0_7": int((prov.share_common_quarter_effect > 0.7).sum()),
                               "e128_shap": "ONI acted as a period marker on the regional target (E128_SHAP_EXPLANATIONS.md)"}

    # D15 capacity
    n_pred = int(len(fa))
    D["D15_capacity"] = {"candidate_predictors": n_pred, "provincial_reference_values": 10, "independent_changes": 5,
                         "predictors_per_change": n_pred / 5}
    return D


def simulation() -> pd.DataFrame:
    grid = list(itertools.product((10, 20, 40), (0.25, 0.5, 1.0, 2.0), (0.6, 0.9), (0.0, 0.25, 0.5, 0.75), (2, 3)))
    rows = [L.simulate_panel(n, r, rho, r2, h, seed=L.SEED + i) for i, (n, r, rho, r2, h) in enumerate(grid)]
    sim = pd.DataFrame(rows)
    sim.insert(0, "label", "SYNTHETIC PLANNING SIMULATION - not model performance")
    sim.to_csv(OUT / "planning_simulation.csv", index=False)
    return sim


def simulation_summary(sim: pd.DataFrame) -> dict:
    out = {"cells": int(len(sim)), "sims_per_cell": 300, "required_forecast_sd_over_se": L.required_forecast_sd_over_se(0.75)}
    ok = sim[sim.p_pass_N2_and_N4 >= 0.8]
    out["cells_with_pass_prob_ge_0_8"] = int(len(ok))
    out["min_quarters_for_pass_prob_ge_0_8"] = {f"h{h}": (int(ok[ok.info_horizon_h == h].n_quarters.min()) if (ok.info_horizon_h == h).any() else None)
                                                for h in (2, 3)}
    out["persistence_within75_prob_by_noise"] = sim.groupby("noise_ratio_r")["p_within75_persistence"].mean().round(3).to_dict()
    out["informed_within75_prob_by_r2_noise"] = sim.groupby(["r2", "noise_ratio_r"])["p_within75_informed"].mean().round(3).unstack().to_dict()
    out["pass_prob_by_r2_n_h2_rho09"] = (sim[(sim.info_horizon_h == 2) & (sim.rho == 0.9)]
                                         .groupby(["r2", "n_quarters"])["p_pass_N2_and_N4"].max().round(3).unstack().to_dict())
    out["conditions_for_pass_prob_ge_0_8"] = ok[["n_quarters", "noise_ratio_r", "rho", "r2", "info_horizon_h", "p_pass_N2_and_N4"]].to_dict(orient="records")
    return out


if __name__ == "__main__":
    g = gate_recheck()
    d = diagnostics()
    sim = simulation()
    s = simulation_summary(sim)
    L.dump({"gate_recheck": g, "diagnostics": d, "simulation_summary": s}, OUT / "diagnostics.json")
    print(json.dumps(g, indent=1)[:400])
    print(json.dumps(d["D5_prices_vs_deprivation"], indent=1))
    print(json.dumps(d["D6_staleness_lead2_quarters"], indent=1))
    print(json.dumps({k: d[k] for k in ("D4_cpi", "D7_climate", "D9_news", "D10_period_markers", "D11_noise")}, indent=1)[:2500])
    print(json.dumps({k: v for k, v in s.items() if k != "conditions_for_pass_prob_ge_0_8"}, indent=1)[:3000])
    print("conditions:", s["conditions_for_pass_prob_ge_0_8"][:12])
