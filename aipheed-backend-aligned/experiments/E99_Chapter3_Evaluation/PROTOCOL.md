# E99: Chapter III evaluation, evidence completion and production lock (pre-registered)

**Branch.** `e99-chapter3-evaluation`, from `e98-acceptance-gate` (a42de8c). Frozen before any E99 scoring.

**Production lock.** `final-system-v2` (053a95d on origin) is not modified, merged into or deployed. No Render or Vercel
deployment is triggered.

**Requirements source.** `THESIS 2 (11).pdf`:
- Chapter I: SOP 1–5 and H1–H5.
- Chapter III:
  - §3.3.2.6 label (Eq. 3);
  - Algorithm 3 (lead-time discovery);
  - Algorithm 4 (Optuna TPE, holdout acceptance F1 ≥ 0.75 and AUC ≥ 0.80);
  - §3.4.4 (only a passing lead and model may be published);
  - Stage description (12 final features, blend, blind holdout 2025-Q4..2026-Q3).

**Distinct question (why this is not a repeat).** E83–E98 evaluated the T43 proxy, FIRI v2 and the regional SWS outcome
under criteria added during the E-series. **No experiment has evaluated the thesis's own pipeline as written:** the
Eq. 3 label, Algorithm 3, Algorithm 4, the 12 Chapter III features and the six Chapter I comparators, on identical folds.

**Evidence status.** All quarters to 2026-Q3 were examined in earlier experiments, so E99 results are development
evidence. The Chapter III holdout (2025-Q4..2026-Q3) is untouched by E99 selection (Algorithm 3 and Optuna use only
development targets), but it is not unseen in the project's history. Independent evidence starts with the sealed
2026-Q4 and later targets.

## 1. Target: Chapter III Eq. 3 composite food-stress label (a proxy)

stress(p, t) = sws_hunger(t) + 2 × (food_cpi_yoy(p, t) − mean over the five provinces of food_cpi_yoy(t));
y = 1 if stress > median(stress).

- **sws_hunger(t):** mean of the `definition_A` SWS rounds of quarter t (`data/inputs/sws_rounds.csv`; Balance Luzon,
  identical for all provinces). Quarters without such a round have no label (2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3).
- **food_cpi_yoy:** `data/processed/psa_indicators.parquet`, the source used by `label_generator.py`.
- **Median:** over all labelled province-quarters 2021-Q2..2026-Q3 (95 rows), as Chapter III states (global median).
  - Sensitivity S1: median of the development rows only (targets ≤ 2025-Q1), applied to every row.
- **What it is.** A composite proxy: measured regional hunger plus provincial food-price deviation. It is not a measured
  provincial food-insecurity rate, and it is reported as such.

## 2. Features (Chapter III final 12) and timing

**Source:** `data/processed/features_fused.parquet` (the Chapter III fused matrix, 2021-Q1..2026-Q2), plus food CPI from
`psa_indicators`.

| Group | Features at origin t |
|---|---|
| NLP (9) | FSSI, FSSI_lag1, FSSI_lag2, FSSI_accel; trigger_market, trigger_climate, trigger_employment, trigger_ofw_remittance, trigger_fish_kill |
| Government (3) | food_cpi_dev(t) = food_cpi_yoy(p, t) − provincial mean(t); unemployment_rate(t − 1); rice_change(t − 1) = % change of rice_price_regular from t − 2 to t − 1 |

- **Issue date** of origin t: the 15th of the first month of quarter t + 1 (the Chapter III scheduler).
- **Timing correction (disclosed deviation).** The matrix aligns every series at quarter t. LFS unemployment and PSA
  rice prices for the last month of t are not published by the 15th, so they are taken from t − 1.
- **Missing values (disclosed deviation from "zero-filled").** LightGBM uses native missing handling. Logistic
  regression uses training-median imputation. Missing news is never set to zero stress.

## 3. Folds, availability and leads

- **Lead k:** features at origin t predict y at target q = t + k.
- **Training pairs for a test target q (origin t = q − k, issue I):** pairs (t′, t′ + k) with t′ ≥ 2021-Q1 whose
  target quarter q′ ≤ t has its SWS round posted before I. The PSA CPI of q′ ≤ t is published by I.
- **Fold.** One labelled test target quarter (5 province rows), advancing one quarter per fold (expanding window).
  - A fold needs training pairs covering at least 8 distinct target quarters (Chapter III: minimum training window of
    8 quarters).
  - If the training labels have one class only, every model issues that class with probability equal to the training
    base rate (recorded).
- **Development targets:** labelled quarters ≤ 2025-Q1.
- **Holdout targets:** 2025-Q4, 2026-Q1, 2026-Q2, 2026-Q3 (Chapter III blind four-quarter holdout).

## 4. Algorithm 3: lead-time discovery

- For k = 1..8 on development folds, with **default** LightGBM (`LGBMClassifier(random_state=99, deterministic=True,
  n_jobs=1, verbosity=-1)`, library defaults otherwise) on the 12 features.
- Mean fold accuracy is compared with 0.75. The search advances while it passes and halts at the first k that fails or
  has no fold. **k\* = the last passing k** (0 if k = 1 fails).
- Precision, recall, F1, AUC and the comparators (§6) are recorded at every computed k.
- Sensitivity S2 (reported only): Algorithm 3 with the holdout folds included.

## 5. Algorithm 4: Optuna TPE and holdout acceptance

- Run at k\* if k\* ≥ 1. Also run at k = 2, the dashboard horizon, if k\* ≠ 2; that run is report-only.
- **Study:** 100 trials, `TPESampler(seed=99)`. Objective: mean weighted F1 over the development folds at that k.
- **Nine hyperparameters:**
  - `num_leaves` [4, 32];
  - `max_depth` [2, 6];
  - `learning_rate` [0.01, 0.3] (log scale);
  - `n_estimators` [50, 500];
  - `min_child_samples` [3, 20];
  - `subsample` [0.5, 1.0] with `subsample_freq` = 1;
  - `colsample_bytree` [0.5, 1.0];
  - `reg_alpha` [1e-4, 10] (log scale);
  - `reg_lambda` [1e-4, 10] (log scale).
- **Holdout evaluation, once.** The best parameters are scored walk-forward on the 4 holdout folds (expanding training
  as in §3).
- **Acceptance (Chapter III):** holdout weighted F1 ≥ 0.75 **and** AUC-ROC ≥ 0.80. HIGH-class F1 is also reported.
- **Final model:** retrained on every labelled pair at that k, saved as an E99 research artifact (never served).

## 6. Comparators (Chapter I SOP 4 / H3), identical folds and rows

- **Proposed:** LightGBM, 12 features. Default parameters in Algorithm 3; tuned parameters in Algorithm 4.
- **The six named in Chapter I:**
  1. naive persistence: the province's latest label known at the issue date;
  2. LR combined (12 features);
  3. LR government-only (3 features);
  4. LR NLP-only (9 features);
  5. LightGBM government-only;
  6. LightGBM NLP-only.

  The logistic regressions use L2, C = 1.0, training-standardised. The single-source LightGBM models use default
  parameters.
- **Also reported:**
  - prevalence (training base rate as the probability; class = rate ≥ 0.5);
  - FIRI v2 (province index from `data/thesis/firi2_history.csv`, k = 2 only; HIGH at ≥ 0.5);
  - the Chapter III blend: 0.4 tuned LightGBM + 0.4 LR government + 0.2 LR on trigger_climate, trigger_fish_kill and
    trigger_ofw_remittance; HIGH at ≥ 0.712, the document's fixed cutoff, which is not tuned.
- **Metrics:**
  - accuracy (Wilson), mean fold accuracy, balanced accuracy, HIGH precision/recall/F1, weighted F1, AUC, Brier,
    confusion matrix and class counts, per-fold accuracy;
  - quarter-cluster bootstrap 95% CIs (5,000 draws, seed 99);
  - rising stress: onset rows, where y = 1 and persistence = 0.

## 7. SHAP (SOP 1 / H1)

- TreeExplainer on the final tuned model (k\*, or k = 2 if k\* = 0). Features are ranked by mean |SHAP| over its
  training rows.
- **H1 rejected** iff the best-ranked FSSI feature (FSSI, lag1, lag2 or accel) **and** food_cpi_dev are both in the top
  3 of 12.
- **Stability:** the median rank over the development fold models.
- **Disclosure:** food_cpi_dev also enters the label (Eq. 3), so its strength partly reflects label construction and
  autocorrelation.

## 8. Hypothesis decisions (mechanical)

| Hypothesis | Decision rule |
|---|---|
| H1 | Rejected under the §7 rule. |
| H2 | Rejected iff k\* ≥ 2 **and** the Algorithm 4 model at k\* passes acceptance on the holdout. |
| H3 | **Rejected (descriptive)** iff the tuned LightGBM at k\* has strictly higher accuracy and weighted F1 than each of the six comparators on both the development folds and the holdout. **Rejected (significant)** additionally requires an exact McNemar p < 0.05 vs each comparator on the pooled development + holdout rows. If k\* = 0, H3 is evaluated at k = 2 and labelled as such. |
| H4 | Requires the DA evaluators' vulnerability assessments (questionnaire); **blocked** until responses exist. |
| H5 | Requires the ISO/IEC 25010 responses; **blocked** until responses exist. |

## 9. Prospective seal (independent evidence)

- From the latest origin with complete features (2026-Q2, issue 2026-07-15), the k = 2 Algorithm 4 model predicts
  2026-Q4.
- The predictions, the model parameters, the feature row and the issue date are sealed with SHA-256 before any 2026-Q4
  outcome exists.
- They are scored only when SWS 2026-Q4 and PSA 2026-Q4 CPI are published, with no retraining.
- This is a research seal, **not published** to the dashboard.

## 10. Other E99 work (no model claims)

- **G6 wording.** On this branch only, the province detail states the LightGBM price-pressure output as a "score
  (0–1), not a calibrated probability", not as a percentage. Every dashboard label is audited through the API.
- **Sealed-forecast scoring procedure** for 2026-Q4 and later (FIRI v2 and E99 seals), with a scorer that refuses to
  score before the outcome is posted.
- **ISO/IEC 25010 package:**
  - eligibility (DA Region IV-A only) enforced in the scorer;
  - export-format validation;
  - an H4 ranking task (top 5 LGUs per province) with its scorer: Spearman and top-5 overlap with the served
    vulnerability rank.
- **Feasibility of provincial outcomes** from legitimate sources. Documentation only: no data are requested or
  collected.

## 11. Release gate

The E98 gate (G1–G12) applies unchanged. A missing outcome, missing responses or a failed criterion keeps the release
blocked.
