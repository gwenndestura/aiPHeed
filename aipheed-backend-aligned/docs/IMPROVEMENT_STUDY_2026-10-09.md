# Improvement Study v2: Data Corrections and a Target-Structured Model (2026-10-09)

**Scope:** an isolated experiment. Production (MODEL-A, the API and the dashboard), `data/processed/`, the models, the governing configuration, earlier evidence and Chapter III are unchanged. Nothing was committed or deployed. Tests pass (147), and the production consistency check passes 39/39.

**Files:**

| Item | Location |
|---|---|
| Pre-registration (written before any run on corrected data) | `experiments/2026-10-09_improvement/PREREGISTRATION_v2.json`, SHA-256 `380c0050…f8ca` |
| Script | `scripts/supplementary/improvement_study.py` (builds the corrected frame in memory only) |
| Tests | `tests/unit/test_improvement_corrections.py` (9 tests: each correction, the timing shift, `cpi_rel` alignment, the rule) |
| Outputs | `results.json` (hashes of 10 source tables, script hash, git HEAD `eee269b`), `P3_nested_predictions.csv`, `fixed_config_predictions.csv` (73 configurations), `FROZEN_P3_CHOICE.json` (SHA-256 `7caa5bda…`), `run.log` |

---

## Bottom line

**The 75% objective is not achieved.** This is not because a better algorithm is missing. What limits the result is the target and the amount of data.

- **The four data corrections were applied as committed in advance**, whatever their effect. Corrected data is the more honest test of the model, and it shows that **part of the earlier accuracy came from data artifacts**:

| Model | Original data | Corrected data |
|---|---:|---:|
| MODEL-B2 | 81.8% | 74.5% |
| MODEL-A configuration | 69.1% | 63.6% |
| Pre-registered nested procedure | 74.5% (P) | **70.9% (P3)** |

- **The most informative result is a diagnostic, not a model.** If next quarter's regional SWS hunger figure were known, the label would be 85.5% predictable. With the SWS value actually available at forecast time, the best achievable is about 76%. The bottleneck is forecasting **one regional SWS number about 2 quarters ahead**. Province data cannot fix that, and with 11 test quarters, model tuning cannot either.
- **The best model for telling provinces apart** is a rule applied straight from Equation 3, with nothing fitted: 76.4% accuracy, AUC 0.85, within-quarter AUC 0.81, HIGH recall 0.73. It ties timing-valid persistence. It is the most defensible candidate, but it does not meet the acceptance rule.

## 1. Root causes, ranked by effect on accuracy

| Rank | Root cause | Evidence | Effect |
|---|---|---|---|
| 1 | **The label is dominated by one regional SWS figure that is forecast about 2.2 quarters ahead** | 66% of stress variance lies between quarters (one Balance-Luzon SWS value per quarter). At forecast time the latest released SWS round is on average **2.0 quarters** (2.2 in the test period) older than the label quarter. Latest-known SWS vs target SWS: r = 0.58, mean absolute miss **3.6 points**. Oracles: true next-quarter SWS + known province term → **85.5%**; known SWS + true province term → 74.5%; origin-known values for both → 76.4%. | Caps accuracy around 76%. This is the dominant limit. |
| 2 | **About 11 independent test units; SWS history starts in 2020** | 19 labelled SWS quarters (2020-Q2 to 2025-Q4; 5 quarters missing). The test spans 11 quarters. At least 47/55 is needed for a confident > 75% claim. | No model can be confirmed above 75%. Hyperparameter search overfits inner folds (many exact ties early on). |
| 3 | **Data artifacts inflated earlier scores** | MODEL-B2 drops from 81.8% to 74.5% once the artifacts are removed. The CPI-derived commodity series acted as fixed province markers, and leading zeros (2020 fuel, FX, ENSO and others) acted as an "early period" marker. | The 81.8% partly reflects artifacts, not food-insecurity signal. |
| 4 | **The news signal (FSSI) is too sparse** | Only **33 of 120** province-quarters have a retained article (69 articles at the approved 0.30 threshold). 38–51 of the 55 outer rows have no FSSI or FSSI lags. 804 geocoded, scored articles exist in the window, but 735 fall below the threshold. | The NLP layer contributes little. Forward-filling had hidden this. |
| 5 | **The province term is only moderately predictable** | `cpi_rel` known at forecast time vs at the target: r = 0.57, within-quarter Spearman 0.46, sign agreement 0.68. | Limits province ranking. It is the smaller error source (oracle 74.5% vs 85.5%). |
| 6 | **The label threshold uses the full period** | 55 of the 95 rows behind the 14.6 median are test-period rows. A training-only median: 70.9% (MODEL-B2), 72.7% (P). | Scores are optimistic against the approved target. |
| 7 | **Smaller data issues** | 2020-Q3 has two SWS rounds (17.8 and 23.8): the label uses their mean (20.8), while the feature uses the first release (17.8). Rice switches from retail to wholesale in 2021. CPI and rainfall are today's revised values. | Training rows only, or small |

## 2. Corrections implemented and the evidence for each

All four corrections were committed **before** any run on corrected data, and kept regardless of outcome (`corrections_log` in `results.json`).

| # | Problem | Correction | Evidence it was a real problem | Effect on accuracy |
|---|---|---|---|---|
| K1 | Missing values stored as 0 | Fuel, Brent, FX, typhoons, drought and ENSO for 2020 (20 cells each) and OFW for 2020–21 (40 cells) become missing. The strict-timing shift no longer zero-fills. Lags are recomputed with missing values handled. | The source tables `oil_prices`, `bsp_macro` and `pagasa_climate` start in **2021-Q1**, so all 200 cells were zeros with no observation behind them. ENSO 0 means "neutral", which is a false reading for 2020. | Removes an "early period" signal. Contributes to the drop from 81.8% to 74.5%. |
| K2 | Rainfall lost in a merge | `rainfall_anomaly_pct` comes from the province-measured NASA POWER table for every quarter | `province_rainfall.parquet` covers 1991–2026. The PAGASA merge dropped 2020, so **20 cells** were zero-filled and are now restored. | Training rows only |
| K3 | Stale news shown as current | FSSI and the triggers are missing where no retained article exists. `fssi_article_count` (a genuine count) is added. FSSI lags are recomputed on the calendar grid. | FSSI had been forward-filled in 77 cells and zero-filled in 10. Only 33 cells are observed. | Removes false continuity. |
| K4 | Derived series presented as observed | The 5 `commodity_*` series are dropped | After 2021 they are rebuilt exactly from **regional** CPI × a fixed 2021-Q4 province anchor (992/992 rows). Every test row is after 2021. | MODEL-B2 loses its province-marker signal. |
| M | Missing province term of the target | `cpi_rel` = province food CPI YoY minus the five-province mean, both at t−1. This is the Eq. 3 term, known at forecast time. | The label's province term uses exactly this series (verified: the label CPI equals `psa_indicators.food_cpi_yoy`, and its regional mean equals the five-province mean). | Basis of the structural rule (within-quarter AUC 0.81) |

Tests in `test_improvement_corrections.py` confirm:

- **K1:** source gaps become NaN and observed cells stay.
- **K2:** rainfall equals the measured source in all 120 cells.
- **K3:** FSSI is present in exactly 33 cells, and the article count is 0 elsewhere.
- **K4:** no commodity columns remain.
- **Timing shift:** the first quarter is NaN, never 0.
- **`cpi_rel`:** equals the previous quarter's cross-section.
- **Structural rule:** applies the Eq. 3 threshold.

## 3. Comparison of models and baselines

Same 55 outer rows (verified identical to the earlier studies); strict timing; Eq. 3 target unchanged.

| Model | Data | Correct | Acc | F1 | AUC | Brier | Within-quarter AUC | HIGH recall | Missed HIGH / false HIGH | 2022 / 2023 / 2024 / 2025 | Rule verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|---|
| **P3: pre-registered nested procedure (primary)** | corrected | 39 | **0.709** | 0.708 | 0.745 | 0.214 | 0.70 | 0.58 | 14 / 2 | 0.80 / 0.75 / 0.65 / 0.70 | **FAILS** |
| Structural rule (Eq. 3 on origin values; nothing fitted) | corrected | 42 | 0.764 | 0.766 | **0.851** | 0.178 | **0.81** | 0.73 | 9 / 4 | 0.80 / 0.80 / 0.65 / 0.90 | OBSERVED_ONLY |
| Structural logistic (2 features, C = 1) | corrected | 36 | 0.655 | 0.652 | 0.763 | 0.225 | 0.81 | 0.52 | 16 / 3 | 0.80 / 0.75 / 0.40 / 0.90 | FAILS |
| MODEL-B2 configuration | corrected | 41 | 0.745 | 0.747 | 0.784 | 0.194 | 0.66 | 0.76 | 8 / 6 | 0.20 / 0.75 / 0.80 / 0.90 | FAILS |
| MODEL-A configuration | corrected | 35 | 0.636 | 0.627 | 0.739 | 0.232 | 0.61 | 0.45 | 18 / 2 | 0.80 / 0.75 / 0.50 / 0.60 | FAILS |
| MODEL-B2 (as reported) | original | 45 | 0.818 | 0.820 | 0.828 | 0.167 | 0.63 | 0.76 | 8 / 2 | 0.80 / 0.90 / 0.70 / 0.90 | OBSERVED_ONLY |
| MODEL-A configuration | original | 38 | 0.691 | 0.688 | 0.758 | 0.222 | 0.79 | n/a | n/a | 0.80 / 0.75 / 0.55 / 0.80 | n/a |
| Clock only | n/a | 43 | 0.782 | 0.784 | 0.886 | 0.153 | n/a | n/a | n/a | 0.80 / 0.75 / 0.75 / 0.90 | n/a |
| Timing-valid persistence | n/a | 42 | 0.764 | 0.766 | n/a | n/a | n/a | n/a | n/a | 0.80 / 0.80 / 0.65 / 0.90 | n/a |

**Across all 73 pool configurations at fixed settings** (descriptive), 4 reach 0.75 and the median is **0.618**. The top three:

| Configuration | Correct | AUC | Within-quarter AUC |
|---|---:|---:|---:|
| `gov_c` logistic, C = 0.01, balanced | 44 | 0.861 | 0.82 |
| `gov_c` logistic, C = 0.1 | 44 | 0.817 | 0.86 |
| Structural rule | 42 | 0.851 | 0.81 |

Promoting any of them now would be selection on the test rows. They are recorded as hypotheses for prospective testing.

**Acceptance (pre-registered C1–C4) for P3:**

| Criterion | Result | Verdict |
|---|---|---|
| C1 accuracy ≥ 0.75 | 0.709 | Fail |
| C2 lower bounds ≥ 0.75 | 0.582 (bootstrap) / 0.592 (exact) | Fail |
| C3 beats persistence and clock | −0.055 vs persistence; −0.073 vs clock | Fail |
| C4 leave-one-year-out ≥ 0.75 | 0.69–0.74 | Fail |

## 4. Chronological fold results

P3 accuracy by outer quarter (`P3_nested_predictions.csv`):

| Quarter | 22-Q4 | 23-Q1 | 23-Q2 | 23-Q3 | 23-Q4 | 24-Q1 | 24-Q2 | 24-Q3 | 24-Q4 | 25-Q1 | 25-Q4 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| HIGH (of 5) | 1 | 0 | 1 | 1 | 3 | 4 | 5 | 4 | 5 | 5 | 4 |
| P3 | 0.8 | 1.0 | 0.8 | 0.8 | 0.4 | **0.2** | 0.6 | 0.8 | 1.0 | 0.6 | 0.8 |
| Configuration chosen in-fold | struct2 logistic (C = 0.01) | ← | ← | ← | ← | ← | eq5_struct LightGBM | eq5_struct LightGBM `spw` | ← | ← | ← |
| Inner ties at the top | 12 | 10 | 6 | 6 | 6 | 6 | 4 | 1 | 1 | 1 | 4 |

**What went wrong:**

- In the early folds, inner validation (3–8 quarters) could not tell configurations apart. The pre-declared order then picked the most heavily regularized model, which stays near the base rate.
- It therefore missed the 2023-Q4 and 2024 rise in HIGH rows (14 missed HIGH, recall 0.58).
- This is the failure mode an early-warning system can least afford.

**Fold accuracies for every configuration** are in `fixed_configurations[*].accuracy_by_quarter`.

## 5. Do predictions tell provinces apart, or mostly reflect time?

| Model | Within-quarter AUC (mixed quarters) | Quarters predicted all-same | Reading |
|---|---:|---:|---|
| Structural rule | **0.81** | 4 / 11 | Ranks provinces using the Eq. 3 province term |
| `gov_c` logistic (C = 0.1) | 0.86 | n/a | Same; selection caveat applies |
| MODEL-B2, original data | 0.63 | 7 / 11 | Mostly the quarter's regime |
| MODEL-B2, corrected data | 0.66 | 8 / 11 | Mostly the quarter's regime |
| P3 | 0.70 | 9 / 11 | Mostly the quarter's regime |
| Clock only | n/a | 11 / 11 | Time only, yet 78.2% |

**Conclusion:** province differences are predictable to a useful degree when the model is given the Eq. 3 province term directly (within-quarter AUC about 0.81). Overall accuracy, however, is set by the quarter-level SWS regime, and that is mostly a time-and-persistence signal. **High accuracy and good province discrimination are separate properties in this data.** The clock-only model has the second best and the worst of them respectively.

**Province-specific information exists, but it can only shift a province across the threshold when the quarter is near it.** Through the Eq. 3 province term (`cpi_rel`), a province 2 points above the regional mean moves its stress score up 4 points.

## 6. Ablation and target diagnostics

**Feature ablations** are in `generalization_study` results (Section 6 of that report). Here, K4 (no commodity) is the key ablation: MODEL-B2 drops 4 rows when the commodity series and the other artifacts are removed.

**Alternative-target diagnostics** (none adopted; proposals for the adviser):

| Alternative | What it represents | Simple origin-known predictor | Result |
|---|---|---|---|
| A. Training-only threshold | Same Eq. 3, with the boundary fixed from the past only | MODEL-B2 / P | 70.9% / 72.7% |
| B. **Regional hunger regime**: SWS(t+1) above the training-period median (one per quarter) | Whether Balance-Luzon hunger is high next quarter | Latest released SWS above the same median | **81.8% of 11 quarters** (n = 11) |
| C. **Province-relative food price stress**: `cpi_rel(t+1) > 0` | Which provinces face above-regional food inflation | `cpi_rel` known at forecast time > 0 | 72.7% of 55 rows; within-quarter Spearman 0.48 |
| D. Current Eq. 3 (combined) | Both terms added | Structural rule | 76.4% |

**What the target diagnostics show:**

- **Eq. 3 mixes a quarter-level outcome (B) with a province-level one (C).** Reporting them separately would show what the system can and cannot forecast:
  - (B) is mostly persistence of a regional survey;
  - (C) is the province-specific signal DA can act on.
- **Neither is a change to adopt without approval.**
- **Eq. 3 contains no province-level hunger measurement at all.** SWS is inherited from the Balance-Luzon stratum. A province-level food-insecurity outcome would need new data (Section 9).

## 7. Strongest defensible candidate

| Purpose | Candidate | Why |
|---|---|---|
| Reported thesis model (governing) | MODEL-B2 (`config/governing_model.json`) | It is the adviser-facing configuration. Report its corrected-data result (74.5%) next to the original 81.8%, and disclose the artifacts. |
| Most defensible forecaster | **Structural rule** (`struct_rule`) | No parameters are fitted, so it carries the least selection exposure on the 55 rows. It follows directly from Eq. 3 and Rule 3. It has the best province ranking among the pre-specified models (AUC 0.85; within-quarter AUC 0.81; recall 0.73). Its 76.4% ties persistence. Caveat: it uses the 14.6 constant, which was computed over the full period. |
| Procedure's frozen choice for prospective testing | `eq5_struct` LightGBM `spw` (`FROZEN_P3_CHOICE.json`; tied at the top with 3 others) | Pre-registered rule |

**None meets the acceptance rule. All three should be scored prospectively** under the existing plan (`experiments/2026-10-09_generalization/PROSPECTIVE_EVALUATION_PLAN.md`), alongside persistence and clock-only.

## 8. Has the 75% objective been achieved?

**No.**

- **Historical test accuracy:** 70.9% for the primary procedure, and 76.4% for the best pre-specified model (the structural rule).
- **Chronological validation:** inner scores 0.73–0.84.
- **Against baselines:** no model beats persistence or clock-only.
- **Generalization:** not established.
- **Prospective performance:** not yet measurable; no labels after 2025-Q4.

## 9. Remaining work, in order of expected gain

1. **Lengthen the SWS history (biggest gain, external data, not yet obtained).**
   - **What:** SWS Social Weather Survey total hunger for the **Balance-Luzon** stratum, quarterly, about 1998–2019. The project currently holds 2020-Q2 to 2025-Q4 only.
   - **Where:** SWS media releases (sws.org.ph); the same article sources as `docs/provenance/sws_hunger_sources.json`.
   - **Why:** the regime component (root cause 1) could then be modeled on roughly 80 rounds instead of 19, and outer validation could include several hunger cycles.
   - **Integration:** extend `sws_hunger.parquet` with release dates for timing alignment, and extend regional CPI from PSA OpenStat (2018=100 back-cast, or the 2012 series) to the same years.
   - **Caveat:** the approved window is 2020–2025, so using earlier years needs adviser approval.
2. **Nowcast SWS between releases** using higher-frequency, origin-known indicators: monthly food CPI and rice prices for the quarter in progress, and news volume. These reduce the effective horizon of about 2.2 quarters.
3. **Province-level outcome data.** Candidates:
   - PSA FIES / food-insecurity prevalence (regional, annual);
   - DOST-FNRI ENNS (provincial, about every 3 years);
   - DSWD 4Ps and SLP caseloads;
   - PSA provincial poverty (triennial).

   Each needs verification of geographic level and release dates before use. None has been obtained.
4. **NLP coverage.** Only 69 of 804 geocoded, scored articles pass the approved 0.30 threshold. Collecting more province-tagged articles, or completing the paused sub-province geocoding run, would make FSSI observable in more than 33 of 120 cells.
5. **Production data fixes (K1–K3)** belong in `feature_matrix.py`, but changing production needs authorization.
6. **Prospective scoring** of the three frozen candidates from 2026-Q1.

## 10. Decisions that need adviser approval

| # | Decision |
|---|---|
| B1 | Adopt data corrections K1–K4 in the production pipeline. They reduce reported accuracy but remove artifacts. |
| B2 | Report the structural rule (Eq. 3 applied to origin-known values) as a reference model, or as the forecaster. It departs from "LightGBM" in Chapter III. |
| B3 | Split or supplement the Eq. 3 target with (B) a regional hunger-regime target and (C) a province-relative food-price-stress target, or add a province-level outcome. Each is a target change. |
| B4 | Training-only threshold vs the approved full-period global median |
| B5 | Use pre-2020 SWS and CPI history. This changes the 2020–2025 window. |
| B6 | How the 75% requirement is judged (point estimate vs confident lower bound), given that the data support neither with confidence |
| B7 | Earlier, still open: Chapter III wording R1–R10, Algorithm 4 / Section 3.4.4, H3 |
