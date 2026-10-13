# Evidence-Based Indicator Influence for aiPHeed: Government and News Indicators

| Item | Value |
|---|---|
| Date | 2026-10-12 |
| Scope | Isolated development backend `aipheed-backend-aligned/` only |
| Protocol | `E7_INDICATOR_EVIDENCE_PROTOCOL.md`, frozen before any code ran |
| Audit | `indicator_audit_20261012/` |
| Evaluation | `runs/20261012T090522Z_E7/`, run once |
| Classification rule | Fixed throughout: HIGH if final probability ≥ 0.50; LOW if < 0.50; INSUFFICIENT_DATA if required data are missing or stale. Probabilities are **uncalibrated** (labelled as such). |

---

## 1. Trace and the key constraint

**Current pipeline (traced in E6):**

- Equation 3 defines the outcome: stress = SWS + 2 × provincial food-inflation gap; HIGH if stress > τ (`label_generator.py` l.131, l.222–226).
- The served legacy model is LightGBM on 12 inputs. Its features are forward-filled and zero-filled (`feature_matrix.py` l.532, l.619).
- The E6 revised forecaster uses 7 fixed inputs.

**Equation 3's weights cannot be learned from data.** The equation *is* the outcome, and no independent food-insecurity outcome exists, so fitting α against a target defined by α is circular.

**What can be learned is how much each predictor contributes to forecasting the outcome.** That is what this work does:

- LightGBM learns the (nonlinear) contributions;
- a training-only procedure decides which indicator groups enter;
- ablation and permutation on unseen quarters report whether each group helps.

## 2. Indicator audit (leakage-safe)

**Method:**

- Missingness, province variation and redundancy come from the inputs only (2021–2025).
- The relationship with the outcome uses **only the 8 quarters published before the first evaluation origin** (40 rows; 25–40 non-missing per feature).
- Full table: `indicator_audit_20261012/indicator_audit.csv`.

| Group | Indicator | What it measures | Missing | Province-specific variance | Pre-evaluation ρ with stress | Assessment |
|---|---|---|---:|---:|---:|---|
| R | `last_published_stress` | Lagged outcome (persistence) | 21% | 31% | **0.81** | Strongest. Persistence, not new evidence. |
| R | `sws_hunger`, `sws_change` | Regional hunger (Balance Luzon) | 11% | **0%** (shared) | −0.10 / 0.10 | Defines the level of the target. Little variation in 2021–2023. **One value for all provinces.** |
| GP | `cpi_rel` | Provincial food-inflation gap (T−2) | 21% | 100% | **0.73** | The only strong **province-specific** signal. It is the lagged provincial component of the target. |
| GP | `food_cpi` (level) | Price-index level | 21% | 26% | 0.45 | A level, not current pressure. Trends upward over time. |
| GP | `food_cpi_yoy` (rate), `_lag1`, `_accel` | Inflation rate and change | 21% | 18–31% | 0.39 / 0.29 / 0.18 | Weaker than the gap |
| GP | Rice price (+lag, accel) | Wholesale rice | 5–11% | 16–43% | −0.29 to −0.17 | Weak and negative. Its schedule is only partly documented. |
| GP | `poverty_incidence` | Provincial poverty | **37%** | 91% | −0.61 (10 rows) | Static, sparse and released rarely |
| GN | Unemployment, remittances, fuel, FX, Brent, headline CPI, food-minus-headline, ONI/drought, typhoons, rainfall | National or regional context | 5–32% | **0–11%** | −0.15 to 0.30 (mostly ~0) | Shared by all provinces; near-zero association. Fuel and Brent are redundant (ρ 0.91–0.95). Climate series are revised vintages. |
| N | FSSI (+lags, accel) | Bias-weighted XLM-RoBERTa food-stress score | **73–94%** | 71–75% | Based on 2–10 rows | Unusable coverage |
| N | `fssi_article_count`, `news_ph_count`, `news_ph_fssi` | Article volume and national news score | 0–11% | 0–69% | ≈ 0 | Measures volume, not events |
| N | `trigger_market`, `trigger_climate`, `trigger_fish_kill` | Shares of article topics | 4% | 78–83% | −0.21 to 0.17 | Mostly 0 (51–94% zeros) |
| N | `trigger_employment`, `trigger_ofw_remittance` | Topic shares | 4% | — | — | **Constant** (never vary) |

### News pipeline (`corpus_geocoded.parquet`, 2021–2025)

| Measure | Value |
|---|---|
| Articles | 4,366 |
| Rated relevant by XLM-RoBERTa | **1.8%** |
| Geocoded to a province | 14.7% |
| Both relevant and province-geocoded | **36 articles** over 5 years × 5 provinces (median 1 per province-quarter where any exist) |
| Province-quarters meeting the pipeline's own 5-article sufficiency minimum | **0** |
| Exact duplicate titles | 35 |
| Parseable publication dates | 67% |

- The FSSI formula (`fssi_builder.py`) averages the maximum hypothesis score over the geocoded articles in a quarter. With 0–2 relevant articles, it is effectively noise.
- The served legacy features hide this by forward-filling FSSI in 77 of 120 province-quarters.
- **Missing news is not evidence that food insecurity is absent.** The revised pipeline keeps it as NaN, and the training-only filter drops news features that are missing in more than 50% of a fold's training rows.

## 3. How indicator contributions are learned (implemented)

The implementation is `app/ml/training/datadriven_trainer.py` (model M6).

**At every forecast origin, using training data only:**

1. **Filter features:** drop features missing in more than 50% of the fold's training rows, or constant in them.
2. **Choose groups:** try R plus every subset of {GP, GN, N} (8 candidates) in an **inner walk-forward over the training quarters**. Keep the set with the lowest mean inner log loss; ties go to fewer groups. With fewer than 3 inner quarters, fall back to R.
3. **Fit LightGBM.** Settings: `num_leaves=4`, `min_child_samples=5`, 100 trees, `learning_rate=0.05`, seed 42; no class weights; monotone +1 only on `sws_hunger` and `last_published_stress`. LightGBM learns nonlinear interactions, such as a high price level combined with falling inflation.
4. **Record per forecast:** the selected groups, and each group's summed log-odds contribution (SHAP-type `pred_contrib`). **Contributions describe the fitted model; they are not causal.**

**Groups selected, by forecast quarter:**

| Forecast quarter | Selected | Inner evidence |
|---|---|---|
| 2023-Q4, 2024-Q1 | R (fallback) | 1–2 inner quarters |
| 2024-Q2 onward | R + GN + N | 3–8 inner quarters |

## 4. Equation 3 (final)

**Kept as the outcome definition:**

> **stress(p, t) = SWS_t + 2 × (food_cpi_yoy(p, t) − five-province mean food_cpi_yoy(t))**
>
> The event is stress > τ, with τ = 10.843 frozen as of 2023-10-01 (retrospective) or 14.345 as of 2026-07-01 (prospective).

**Rules:**

- **Missing data:** any missing input gives NaN, never 0. The regional mean exists only when all five provinces are present.
- **Negative deviations:** valid; they lower stress.
- **α = 2:** documented as unvalidated (§1).

**Indicator influence** is no longer a fixed coefficient in a formula. It is learned per origin by the forecaster (§3), and every forecast reports it.

**Alternatives rejected:**

| Alternative | Why rejected |
|---|---|
| Estimated α | Circular |
| PCA or variance weights | Measure variance, not food-insecurity relevance |
| Equal-weight z-composite (E5 S2) | 35/35 HIGH |
| Inflation-rate-only (E5 P1) | Not hunger; slowing inflation reads as LOW |

## 5. Evaluation (E7; 7 reused test quarters, 35 rows, n_eff ≈ 7)

### Primary: τ0 = 10.843 (reference labels 33 HIGH / 2 LOW)

| Config | Balanced acc. | HIGH precision | HIGH recall | LOW recall | False HIGH | False LOW | ROC-AUC | Brier | Log loss |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| M0 existing (12 inputs, served params, balanced) | 0.674 | 0.966 | 0.848 | 0.50 | 1 | 5 | 0.811 | 0.141 | 0.443 |
| **M1 R (core)** | **0.985** | 1.00 | 0.970 | 1.00 | 0 | 1 | 0.977 | **0.029** | **0.134** |
| M2 government (GP + GN) | 0.939 | 1.00 | 0.879 | 1.00 | 0 | 4 | 0.985 | 0.119 | 0.467 |
| M3 news | 0.553 | 0.952 | 0.606 | 0.50 | 1 | 13 | 0.788 | 0.198 | 0.574 |
| M4 government + news | 0.939 | 1.00 | 0.879 | 1.00 | 0 | 4 | 1.000 | 0.123 | 0.463 |
| M5 full | 0.970 | 1.00 | 0.939 | 1.00 | 0 | 2 | 0.985 | 0.063 | 0.260 |
| **M6 training-only selection (served)** | **0.985** | 1.00 | 0.970 | 1.00 | 0 | 1 | 0.977 | 0.033 | 0.155 |
| Carry-forward | 0.939 | 1.00 | 0.879 | 1.00 | 0 | 4 | 1.000 | — | — |
| Equation 3 rule | 0.939 | 1.00 | 0.879 | 1.00 | 0 | 4 | 1.000 | — | — |
| Always-HIGH | 0.500 | 0.943 | 1.00 | 0.00 | 2 | 0 | — | — | — |

- **M6 per quarter** (correct / predicted HIGH / reference HIGH): 2023-Q4 5/4/4; 2024-Q1 4/3/4; the other five quarters 5/5/5.
- **Balanced-accuracy gain over carry-forward:** M1 and M6 +0.045 (CI +0.015 to +0.088); M5 +0.030 (CI 0 to 0.061); M2 and M4 0.

### Secondary: 14.345 (leakage-affected; reference labels 30 HIGH / 5 LOW)

| Config | Balanced acc. | False HIGH | False LOW | Brier | Log loss |
|---|---:|---:|---:|---:|---:|
| M0 | 0.600 | 3 | 6 | 0.172 | 0.546 |
| **M1 R** | **0.733** | 2 | 4 | **0.147** | **0.492** |
| M2 government | 0.733 | 1 | 10 | 0.283 | 1.099 |
| M3 news | 0.567 | 1 | 20 | 0.389 | 1.089 |
| M4 government + news | 0.733 | 1 | 10 | 0.291 | 1.104 |
| M5 full | 0.683 | 2 | 7 | 0.224 | 0.826 |
| M6 served | 0.700 | 2 | 6 | 0.166 | 0.535 |
| Carry-forward | 0.650 | 2 | 9 | — | — |
| Equation 3 rule | 0.617 | 2 | 11 | — | — |

Balanced-accuracy gain over carry-forward: M1 +0.083 (CI +0.016 to +0.156); M6 +0.050 (CI 0 to 0.12); M2 and M4 +0.083 (CI −0.12 to +0.37).

### Tertiary: continuous next-quarter stress (the most informative about indicator value)

| Predictor | RMSE | MAE | Within-quarter ρ (province ranking) |
|---|---:|---:|---:|
| SWS input only | **5.87** | 4.47 | — |
| Equation 3 origin estimate | 5.92 | 4.55 | 0.286 |
| M1 R | 6.11 | 4.54 | 0.094 |
| M5 full | 6.53 | 4.92 | 0.230 |
| Carry-forward stress | 6.76 | 5.22 | 0.286 |
| M6 served | 7.13 | 5.65 | 0.241 |
| M2 government | 8.28 | 6.24 | **0.399** |
| M4 government + news | 8.35 | 6.36 | 0.363 |
| M3 news | 8.65 | 6.96 | −0.085 |

**Group comparisons** (quarter bootstrap 95% CI of the RMSE difference):

| Comparison | RMSE difference | 95% CI |
|---|---:|---|
| Adding news to government (M4 − M2) | +0.065 | −0.05 to +0.22 |
| Adding government to news (M4 − M3) | −0.30 | −2.0 to +1.4 |
| Adding all non-core groups to core (M5 − M1) | +0.41 | −1.0 to +1.6 |

**Permutation importance on unseen data** (M5; mean increase in loss with the 5th–95th percentile range):

| Group | Regression ΔRMSE | Classifier Δlog-loss (τ0) |
|---|---|---|
| R | +0.16 (−0.19 to 0.58) | +0.015 (−0.06 to 0.09) |
| GP | +0.21 (−0.14 to 0.54) | +0.008 (−0.10 to 0.11) |
| GN | −0.12 (−0.31 to 0.09) | −0.012 |
| **N** | **−0.12 (−0.23 to −0.02)** | −0.002 |

For news, shuffling the inputs *lowered* the error.

## 6. Findings

1. **Indicators that genuinely contribute predictive information:**
   - **Regional hunger and persistence (R)** carry nearly all the forecastable signal. M1 (R alone) is the best or tied-best configuration on every outcome. Even so, it is non-inferior to the simple rules, not demonstrably better: its 95% CI against carry-forward on continuous stress includes 0.
   - **Provincial government indicators (GP), especially `cpi_rel`,** are the only source of **province ranking** (within-quarter ρ 0.40 for the government model, against 0.09 for R). Used alone they forecast the stress **level** worse (RMSE 8.3 vs 6.1).
2. **Indicators that are redundant, unreliable, stale or unhelpful:**
   - **News (N):** no predictive value. News-only is the worst model on every outcome. Adding news to government changed nothing. Permuting news *reduced* error. Coverage is too thin for meaningful signal (36 relevant geocoded articles in 5 years).
   - **National/regional government (GN):** no demonstrated value. These series are shared across provinces, show near-zero association, include a redundant fuel/Brent cluster, and include revised climate vintages.
   - **Poverty:** sparse (37% missing). **Constant triggers:** removed by the training-only filter.
3. **No group's added value meets the pre-registered "demonstrated" rule.** That rule requires agreeing ablation and permutation evidence **plus** a continuous-outcome CI excluding 0. With about 7 independent quarters, **reliable indicator weights cannot be determined.** Precise weights are not reported, because they would be manufactured.
4. **The training-only selection (M6) is unstable on this sample.** From 2024-Q2 on, its inner validation (3–8 quarters) chose R + GN + N, the groups the outer evaluation found unhelpful.
   - M6 equals M1 on the primary binary outcome.
   - It is worse on the secondary outcome (balanced accuracy 0.700 vs 0.733; Brier 0.166 vs 0.147).
   - It is worse on continuous stress (RMSE 7.13 vs 6.11).
   - **The procedure is defensible in principle; its inner evidence is too small to choose reliably.**
5. **The existing configuration (M0)** is the weakest LightGBM on the primary outcome (balanced accuracy 0.674; Brier 0.141).

### Before and after (served forecasts, 2021–2025)

| | E6 (fixed 7 inputs) | E7 M6 (data-driven) |
|---|---|---|
| Rows with a probability | 45 | 45 |
| Median probability | 0.988 | 0.989 |
| HIGH / LOW / INSUFFICIENT | 42 / 3 / 50 | 42 / 3 / 50 |
| By year | Identical | Identical |

The legacy served model (in-sample) gave 51 HIGH / 49 LOW over 100 rows; its 2024–2025 medians were 0.85.

**No configuration changes the near-universal HIGH in 2024–2025 under τ0.** The regional hunger level drives it (E6, A2).

## 7. Are the probabilities defensible, and useful for DA?

**Probabilities:**

- They are LightGBM outputs for a defined event, trained only on information published before each origin.
- They are **uncalibrated**: the training-only calibration check never had enough evidence.
- At τ0 their Brier score is low (0.03), but that rests on 2 LOW labels.
- At 14.345 they under-predict HIGH.
- **They must not be presented as a proven chance of food insecurity.**

**What DA can use:**

1. **The regional hunger signal:** clearly labelled as Balance Luzon and shared by all provinces.
2. **Provincial food-price evidence,** especially relative pressure (`cpi_rel`): the only indicator that ranks provinces at all (ρ about 0.3–0.4), and still not better than carry-forward of the observed gap.
3. **The forecast with per-group contributions:** shows how much of each province's probability comes from regional hunger/persistence and how much from provincial or national indicators.

**What cannot be established:**

- province-level food-insecurity rates;
- causal influence of any indicator;
- precise indicator weights;
- a reliable news-based signal.

## 8. Implementation (isolated)

**Created:**

| File | Purpose |
|---|---|
| `app/ml/training/datadriven_trainer.py` | Data-driven forecaster (§3) |
| `tests/unit/test_datadriven_trainer.py` | 10 tests |
| `data/revised/datadriven_forecasts_retrospective.parquet` (+ `_meta.json`) | Served artifact |
| `experiments/2026-10-11_devprotocol/E7_INDICATOR_EVIDENCE_PROTOCOL.md` | Protocol |
| `runner/audit_indicators.py` | Leakage-safe audit |
| `runner/run_e7_indicator_evidence.py` | One-time evaluation runner |
| `indicator_audit_20261012/` | Audit outputs |
| `runs/20261012T090522Z_E7/` | Evaluation outputs |
| `INDICATOR_EVIDENCE_REPORT.md` | This report |

**Modified:**

| File | Change |
|---|---|
| `scripts/build_revised_forecasts.py` | `--model datadriven` option; selection metadata |
| `app/services/assessment.py` | Serves the M6 artifact (the E6 artifact is kept). Adds `evidenceContributions`, with each group's label, inclusion and log-odds contribution, separating regional hunger evidence, provincial government, national government, news and the final forecast. Adds news and contribution limitations. |
| `tests/integration/test_api_assessments.py` | Reads the service's artifact path; checks the contribution payload |

**Tests:**

- **Full aligned suite: 288 passed, 0 failed** (278 earlier + 10 new).
- **What the new tests cover:**
  - candidate sets always include R;
  - groups don't overlap;
  - the training-only filter;
  - monotone constraints only on R;
  - the model is LightGBM, unweighted;
  - contributions reconstruct the raw score;
  - fallback to R in early folds;
  - selection and forecast unchanged when target and later labels are perturbed;
  - selection uses only training quarters;
  - the shared classification and INSUFFICIENT_DATA rules;
  - the regression path is label-free.

### Run defect (disclosed)

- **What happened:** E7's protected-file guard raised at the end. My pattern `runs/20261012T*/*` (meant to protect E6) also matched E7's own folder, so the guard flagged E7's new outputs.
- **What was affected:** all computation and `metrics.json` completed; `manifest.json` was not written.
- **Independent verification:**
  - 100/100 recorded input files unchanged;
  - E1–E6 outputs unchanged against their manifests;
  - both served artifacts match their metadata;
  - production `backend/` 54/54 unchanged;
  - prediction files were written (17:08–17:15) before the scored files (17:17–17:21).
- **Records:** `manifest_posthoc.json`. The glob is fixed for future runs; **E7 was not re-run.**

### Unresolved

1. **Served model choice.** The protocol fixed M6 as the served model, and it is served. The outer evidence favours the simpler **R core (M1)**. Switching requires a new, separately authorized protocol; changing it now would be selection on the test quarters.
2. **News data.** The pipeline needs far more relevant, province-geocoded articles before news can be evaluated meaningfully. That is a data-collection issue, not a weighting issue.
3. **Earlier open items:**
   - calibration;
   - the reference period (τ0 vs 14.345);
   - production's `label_cpi` and 0.712 cutoff;
   - the production frontend not consuming the new endpoint;
   - 2026 CPI rows in production data;
   - the active daily scheduled tasks.

## 9. Safety

| Item | Status |
|---|---|
| Production `backend/` and production frontend | Not modified |
| Deployments, commits, pushes, merges | None |
| Protected 2026 outcome data | Not inspected or used. Every label and forecast is limited to 2021–2025. |
| Existing artifacts | Preserved: E6 artifact, legacy model, all earlier runs |
| Scheduled tasks | Not modified |
| Thesis | Not modified |
