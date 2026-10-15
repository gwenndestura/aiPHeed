"""E39 (revised 2026-10-15): write label_v2_spec.json, scoring_v2_spec.json and label_v2.csv, then freeze their
SHA-256 in frozen/E39_FREEZE.json. Run once, before any model is fitted. Refuses to overwrite a freeze.

    <backend venv python> -B runner/e39_build_specs_and_label.py

Food Price Pressure (exploratory). It measures food price pressure, not food insecurity. The 4% rule is a
tool-adopted default, not adviser-endorsed and not validated. No pre-2021 data is used; no constant is set by anyone
other than the single documented external constant (the BSP inflation-target ceiling).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

E39 = Path(__file__).resolve().parents[1]
ROOT = E39.parents[2]
INP = ROOT / "backend" / "data" / "inputs"
RAW_2026 = E39.parent / "E31_Chapter1_Completion" / "data_acquired" / "cpi" / "provincial_food_cpi_yoy_2026_raw.csv"
E12 = E39.parent / "E25_Reliable_Forecasts_2021_2026" / "inputs" / "e12" / "realized_components_2021_2025.csv"
FROZEN = E39 / "frozen"
NAMES = {"PH040100000": "Cavite", "PH040200000": "Laguna", "PH040300000": "Quezon", "PH040400000": "Rizal",
         "PH040500000": "Batangas"}
THRESHOLD = 4.0
NAME = "Food Price Pressure (exploratory)"
NOTE = ("Food Price Pressure (exploratory) measures provincial food price pressure, not food insecurity. HIGH means "
        "the province's food inflation (PSA, year on year) was above 4 percent, the ceiling of the BSP inflation "
        "target, which is a headline-inflation target and not a food-specific one. The 4 percent rule is a "
        "tool-adopted default; it is not adviser-endorsed and not validated. High food inflation does not prove "
        "hunger, and low food inflation does not prove adequate food.")


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def label_spec() -> dict:
    return {
        "name": NAME, "version": "label-v2.0 (revised 2026-10-15; supersedes the withdrawn FSI anchor design)",
        "data_cutoff": "2026-10-14 (researcher authorization; nothing before 2021-01 is used)",
        "framing": NOTE,
        "not_measured": ["food insecurity", "hunger prevalence", "adequacy of food"],
        "units": {"F": "percent, year-on-year change of the provincial food CPI (01.1 FOOD)",
                  "H": "percent of families (SWS self-rated involuntary hunger, Balance Luzon)"},
        "sources": {
            "F": {"what": "PSA provincial food CPI (01.1 FOOD) year-on-year rate as PUBLISHED by PSA (one decimal, "
                          "monthly); quarter value = mean of the quarter's three published monthly rates",
                  "files": {"backend/data/inputs/d_quarterly_panel.csv (column F)": sha(INP / "d_quarterly_panel.csv"),
                            "E31 data_acquired/cpi/provincial_food_cpi_yoy_2026_raw.csv (2026 monthly published)": sha(RAW_2026),
                            "E25 inputs/e12/realized_components_2021_2025.csv (2021-2025 published quarter means)": sha(E12)},
                  "table": "PSA OpenStat 0012M4ACP23 (2026) / the same published series for 2021-2025",
                  "release_timing": "monthly CPI is released by PSA in the first week of the following month; the "
                                    "quarter value of quarter q is treated as available only at origins O(t) with "
                                    "t >= q + 1 (conservative: all three months published before the origin)",
                  "coverage": "2021-Q1 .. 2026-Q3, 5 provinces, no gap"},
            "H": {"what": "SWS Balance Luzon hunger, approved series only (definition_A = True); quarter value = "
                          "mean of the quarter's approved rounds",
                  "file": {"backend/data/inputs/sws_rounds.csv": sha(INP / "sws_rounds.csv")},
                  "missing_quarters_never_imputed": ["2021-Q1", "2022-Q1", "2025-Q2", "2025-Q3"],
                  "availability": "a quarter's H is usable only after ALL its approved rounds were posted (posted "
                                  "date in the file)"},
            "D": {"what": "F minus the five-province mean of F (informational only; not part of any target)"}},
        "label_A": {"name": "Food Price Pressure HIGH", "rule": "HIGH if F_pq > 4.0, else NOT HIGH; missing F -> no label",
                    "threshold": THRESHOLD,
                    "threshold_source": "Bangko Sentral ng Pilipinas inflation-targeting framework: the inflation "
                                        "target of 3.0 percent +/- 1.0 percentage point set by the Development Budget "
                                        "Coordination Committee; 4.0 percent is its ceiling. It is a HEADLINE CPI "
                                        "target, not a food-specific one. (Cited from the BSP framework; the page was "
                                        "not re-fetched in this run.)",
                    "status": "tool-adopted default; not adviser-endorsed; not validated; not tuned or selected from "
                              "any result",
                    "sensitivity_for_information_only": [3.0, 5.0],
                    "no_weights_tiers_or_severity_anchors": True},
        "target_B": {"name": "Provincial food CPI YoY (continuous)", "value": "F_pq", "threshold": None},
        "target_C": {"name": "Regional SWS hunger H (continuous)", "value": "H_q (one value shared by all five "
                     "provinces)", "threshold": None, "missing_quarters": "not imputed; not scored"},
        "provincial_ranking": {"rule": "rank provinces within a quarter by F (descending: rank 1 = highest food "
                                       "inflation); ties share the average rank and carry a tied flag",
                               "vulnerability_weights": "not part of any label; used only by the existing LGU "
                                                        "ranking (PSA 2021 SAE, POPCEN 2024)"},
        "no_leakage": "every label value uses only data of its own quarter; no reference window, no anchor fitted "
                      "to data, no constant other than 4.0",
        "pre_2021_data": "none",
        "evaluation_dependence": "the five provinces share H (target C is regional) but differ in F; scoring is "
                                 "date-level (see scoring_v2_spec.json)",
    }


HP = {
    "lead1_E36_operational": {"feature_set": "COMB (13 E36 features)", "num_leaves": 4, "max_depth": -1,
                              "min_child_samples": 5, "n_estimators": 150, "learning_rate": 0.05, "reg_lambda": 0.0,
                              "colsample_bytree": 0.8, "seed": 36, "deterministic": True, "n_jobs": 1},
    "lead2_E38_operational": {"feature_set": "COMPACT (6 E36 features)", "num_leaves": 2, "max_depth": 1,
                              "min_child_samples": 10, "n_estimators": 60, "learning_rate": 0.05, "reg_lambda": 5.0,
                              "reg_alpha": 1.0, "colsample_bytree": 1.0, "seed": 36, "deterministic": True,
                              "n_jobs": 1, "note": "E38's prior-shift adjustment is NOT used: calibration is now "
                                                    "procedure E"},
}


def scoring_spec() -> dict:
    return {
        "name": f"scoring-v2 for {NAME}", "version": "scoring-v2.0 (revised 2026-10-15)",
        "status": "frozen before any model run; run exactly once; no rerun after results",
        "origins_and_leads": {"origin": "O(t) = 00:00 PHT on the first day of quarter t+1",
                              "lead_k": "target quarter t+k; k = 1 (the quarter under way at the origin) and k = 2 "
                                        "(the next calendar quarter, the dashboard target)",
                              "information": "only data published before O(t): SWS rounds by posted date, CPI of "
                                             "quarters <= t-1 (labels) and months 1-2 of t (Dnow, rice), news of "
                                             "quarter t (E31 FORECAST rule)"},
        "features": {"definition": "E36 as-of features (E32 construction, unchanged): H_last, H_gap, H_trend, "
                                   "H_margin, D_last, Dnow, rice_rel, news_n, news_reg, news_direct_share, fssi_v2, "
                                   "fssi_missing, y_last",
                     "y_last_redefined": "the target's own latest published value at the origin: A -> 1[F(t-1) > "
                                         "4]; B -> F(t-1); C -> H of the latest quarter whose approved rounds were "
                                         "all posted before the origin",
                     "groups": {"GOV": ["H_last", "H_gap", "H_trend", "H_margin", "D_last", "Dnow", "rice_rel", "y_last"],
                                "NLP": ["news_n", "news_reg", "news_direct_share", "fssi_v2", "fssi_missing"],
                                "COMB": "GOV + NLP", "COMPACT": ["H_margin", "H_trend", "D_last", "Dnow", "news_reg", "fssi_v2"]},
                     "limitation_declared_now": "the absolute food-inflation level enters only through y_last; the "
                                                "lead-2 COMPACT set has no level feature at all"},
        "training_rows": "all pairs (X(t'), target of t'+k) with t'+k <= t-1 and the target available before O(t) "
                         "(A/B: CPI quarter <= t-1; C: all approved rounds posted); rows with a missing feature of the "
                         "procedure's set are dropped",
        "procedures": {
            "A_binary": {"model": "LightGBM classifier, objective binary", "hyperparameters": HP,
                         "tuning": "none"},
            "B_C_continuous": {"model": "LightGBM regressor, objective regression (L2), same hyperparameters as A per "
                                         "lead", "tuning": "none"},
            "C_interval": "chronological split-conformal 80% interval: q = the ceil(0.8 (n+1))-th smallest absolute "
                          "residual of the procedure's own earlier out-of-sample forecasts whose outcomes were "
                          "available before the origin; issued only with >= 8 prior residual DATES, else 'no interval'",
            "D_coherence": "A's P(HIGH) and B's predicted F are separate outputs; report how often 1[P>=0.5] and "
                           "1[F_hat > 4] disagree; no coherence is claimed",
            "E_calibration": "Platt scaling: logistic regression (L2, C = 1.0) of the outcome on logit(raw P), fitted "
                             "only on the procedure's earlier walk-forward predictions whose outcomes were available "
                             "before the origin; needs >= 8 such prior dates and both classes, otherwise shrinkage: "
                             "P = 0.5 x raw P + 0.5 x climatology (training HIGH rate, Laplace). No isotonic. Display "
                             "clipping to [0.02, 0.98] is not calibration and is applied only in displays.",
            "F_withhold": "no forecast (and no baseline score) for an origin whose training rows cover fewer than 8 "
                          "distinct target quarters",
            "G_ranking": "rank provinces within a quarter by B's predicted F; ties share the average rank (tied flag)"},
        "baselines": {
            "fitted_on": "training rows of the origin only",
            "primary_comparators": ["persistence", "climatology"],
            "secondary": ["seasonal_naive", "AR1", "always_LOW (A only)", "always_HIGH (A only)",
                          "B2_LR_COMB", "B3_LR_GOV", "B4_LR_NLP", "B5_LGBM_GOV", "B6_LGBM_NLP"],
            "definitions": {
                "persistence": "the target's latest published value at the origin (A: 1[F(t-1)>4]; B: F(t-1); C: "
                               "latest posted H)",
                "seasonal_naive": "the target's value four quarters before the target, if available at the origin, "
                                  "else persistence (flagged)",
                "AR1": "A: logistic regression on y_last; B/C: OLS of the target on y_last, training rows only",
                "climatology": "A: training HIGH rate (Laplace); B/C: training mean",
                "six_thesis_baselines": "A: logistic regression (L2, C=1, standardized, training-mean imputation) on "
                                        "COMB/GOV/NLP and the LightGBM classifier on GOV/NLP with the lead's "
                                        "hyperparameters; B/C: ridge regression (alpha=1, standardized) on "
                                        "COMB/GOV/NLP and the LightGBM regressor on GOV/NLP"}},
        "unit": "the DATE (target quarter). Per-date values first, then averaged over eligible dates. Missing-target "
                "quarters and forecast-only quarters are 'Not scored', never errors.",
        "metrics": {
            "A": {"brier": "B_d = mean over scored provinces of (P - y)^2; Brier = mean of B_d over dates",
                  "brier_skill": "BSS_ref = 1 - Brier_model / Brier_ref over the same dates",
                  "auc": "pooled over eligible province-quarters; date-clustered bootstrap CI; 'not evaluable' with "
                         "one class; never computed within a date",
                  "pooled_with_date_bootstrap": ["balanced_accuracy", "HIGH_recall", "HIGH_precision"],
                  "accuracy": "diagnostic only, beside always-LOW and always-HIGH; never a headline"},
            "B_C": {"MAE_d / RMSE_d": "per date, averaged over dates",
                    "MASE": "MAE / mean absolute error of the persistence forecast on the origin's training rows "
                            "(naive scale from training data only), averaged over dates",
                    "skill": "1 - MAE_model / MAE_ref over the same dates",
                    "coverage": "share of scored rows inside the 80% interval; date-clustered bootstrap"},
            "ranking": {"spearman": "per date between predicted and observed F (average ranks), only on dates with "
                                    "variation in both; averaged", "top2": "|predicted top-2 & observed top-2| / 2 per "
                        "date, averaged; compared with the 40% chance level",
                        "note": "H is shared, so ranking skill can only come from price differences"}},
        "inference": {"ci": "date-clustered percentile bootstrap, 2000 resamples, seed 20261015",
                      "paired_test": "exact sign-flip test (two-sided) on per-date loss differences (Brier for A, "
                                     "absolute error for B/C) between the model and each comparator",
                      "multiplicity": "Holm over the declared comparison set (primary + secondary, per target and lead)"},
        "success_rule": "skill is SHOWN only if the skill score against EACH primary comparator (persistence, "
                        "climatology) is > 0 AND its Holm-adjusted p < 0.05; otherwise 'not demonstrated'. Label A is "
                        "'not evaluable' at a lead if HIGH occurs on fewer than 3 independent scored dates; then only B "
                        "and C are evaluated. No accuracy target; no constant is adjusted.",
        "power_note": "about 7-9 independent scored dates per lead and target after withholding; small samples",
        "ledger": "runner/e39_ledger.py records every issued forecast (sha256), observed values when released, "
                  "baseline predictions and per-date scores; scoring a new quarter is mechanical",
    }


def label_table() -> pd.DataFrame:
    d = pd.read_csv(INP / "d_quarterly_panel.csv", dtype={"province_code": str})
    r = pd.read_csv(INP / "sws_rounds.csv")
    a = r[r["definition_A"].astype(str) == "True"]
    H = a.groupby("quarter")["H"].mean()
    posted = a.groupby("quarter")["published"].max()
    rounds = a.groupby("quarter")["round"].apply(lambda s: " | ".join(s))
    raw = pd.read_csv(RAW_2026, dtype={"province_code": str})
    raw["quarter"] = raw["reference_month"].str[:4] + "-Q" + ((raw["reference_month"].str[5:7].astype(int) - 1) // 3 + 1).astype(str)
    m26 = raw.groupby(["province_code", "quarter"])["food_cpi_yoy_pct_raw"].agg(["mean", "size"])
    for (p, q), v in m26.iterrows():               # the 2026 served F must equal the mean of PSA's published months
        if v["size"] == 3:
            f = float(d[(d.province_code == p) & (d.quarter == q)]["F"].iloc[0])
            assert abs(f - v["mean"]) < 1e-9, (p, q, f, v["mean"])
    out = d.assign(province=d["province_code"].map(NAMES), H=d["quarter"].map(H), H_rounds=d["quarter"].map(rounds),
                   H_posted=d["quarter"].map(posted))
    out["label_A"] = (out["F"] > THRESHOLD).map({True: "HIGH", False: "NOT HIGH"})
    out["label_A_3pct_info"] = (out["F"] > 3.0).map({True: "HIGH", False: "NOT HIGH"})
    out["label_A_5pct_info"] = (out["F"] > 5.0).map({True: "HIGH", False: "NOT HIGH"})
    out["F_rank_in_quarter"] = out.groupby("quarter")["F"].rank(ascending=False, method="average")
    out["F_rank_tied"] = out.groupby("quarter")["F"].transform(lambda s: s.duplicated(keep=False))
    out["cpi_release_note"] = "PSA monthly CPI, released in the first week of the following month"
    cols = ["quarter", "province_code", "province", "F", "D", "label_A", "label_A_3pct_info", "label_A_5pct_info",
            "F_rank_in_quarter", "F_rank_tied", "H", "H_rounds", "H_posted", "cpi_release_note"]
    return out[cols].sort_values(["quarter", "province_code"]).reset_index(drop=True)


def main():
    FROZEN.mkdir(exist_ok=True)
    if (FROZEN / "E39_FREEZE.json").exists():
        raise SystemExit("already frozen; refusing to overwrite")
    ls, ss, lt = label_spec(), scoring_spec(), label_table()
    files = {E39 / "label_v2_spec.json": json.dumps(ls, indent=1).encode(),
             E39 / "scoring_v2_spec.json": json.dumps(ss, indent=1).encode(),
             E39 / "label_v2.csv": lt.to_csv(index=False, float_format="%.10g", lineterminator="\n").encode()}
    for p, b in files.items():
        p.write_bytes(b)
    freeze = {"frozen_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "before_any_model_run": True, "sha256": {p.name: sha(p) for p in files}}
    (FROZEN / "E39_FREEZE.json").write_bytes(json.dumps(freeze, indent=1).encode())
    print(json.dumps(freeze, indent=1))
    print(lt.groupby("quarter")["label_A"].apply(lambda s: (s == "HIGH").sum()).to_dict())


if __name__ == "__main__":
    main()
