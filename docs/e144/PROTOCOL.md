# E144: label-borrowing, news-fed LightGBM forecasting of food-insecurity risk. Protocol E144-P2

* **Locked before any E144 result is computed:** `data/e144/out/PROTOCOL_LOCK.json`.
* **Revision P2 (2026-11-04):**
  * P1 was locked at 03:11 UTC (`PROTOCOL_LOCK_P1_superseded.json`). GDELT then refused every request from this connection (HTTP 429), so 16 of its 24 news files could not be collected.
  * **No P1 result was ever computed.**
  * On the owner's instruction, P2 replaces the news source with the project's existing Google News RSS source for all four areas.
  * Everything else is unchanged: labels, models, parameters, baselines, link, end-to-end check, thresholds and decisions.
* **Methodology:** `docs/research/AIPHEED_METHODOLOGY_LABEL_SCARCE_FORECASTING.md`.
* **Owner decision (2026-11-04):** SWS area history from 2010 may be used.
* **Untouched:** E137–E143.

## 1. Hypotheses

1. **H-A.** A LightGBM model pooled over the four SWS areas, with area news and a nowcast of the unpublished quarter, forecasts above-normal area hunger at the dashboard horizon and beyond. The dashboard horizon is h = 1: issue at the start of the viewing quarter, target the next quarter.
2. **H-N.** Adding area news lowers the expected Brier score versus the same model without news.
3. **H-C.** Measured provincial HFIAS food insecurity moves with the hunger of the province's SWS area, beyond the province's structural and anchored relative risk (E143 C4).
4. **H-E2E.** The full chain (Stage A → Stage C with C4) forecasts the measured provincial survey rounds better than C4 alone.

## 2. Data, as of each issue date

**Labels:**
* SWS involuntary hunger per area: NCR, Balance Luzon, Visayas, Mindanao (`data/fi5/raw/sws/sws_area_rounds_full.csv`).
* Several rounds in one quarter are averaged. A quarter without a round has no label.
* Labels from 2010-Q1 onward. Earlier readings are used only as history and baseline inputs, never as labels.

**HIGH, area-quarter (FEWS NET / GIEWS "worse than normal"; the FI5 definition):** hunger above the mean of the area's readings in the preceding 20 quarters, with at least 8 readings.

**Issue:**
* Issue date d = the last day of quarter i (equivalently, the start of viewing quarter V = i + 1).
* Targets T = V + h, for h = 1, 2, 3, 4.
* A value is usable only if it was published or released on or before d. SWS uses the `published` date. National indicators use the FI5 release rules (`app.fi5.sources`).

**Features (Stage A):**

| Group | Features |
|---|---|
| Label history (area) | hunger_last (latest published reading); hunger_last_anom (vs the as-of 20-quarter mean); hunger_age_q (T minus the quarter of the last reading) |
| Nowcast (area) | A0 nowcast of quarter i, and its anomaly vs the as-of mean |
| News (area; Google News RSS, `app.news.sources.GoogleNewsRSS`; credible domains only; SWS-reporting articles excluded) | For quarter i: theme shares (market, climate, hunger, jobs), each as unique items over the area's unique food-security items in the quarter; attention = log(1 + unique items). Each is z-scored against the area's own earlier quarters (as-of; at least 4 earlier quarters). Collected 2021-01 to 2026-09, so missing before 2021 |
| National | ONI; unemployment rate and its year-on-year change; remittances year-on-year (as-of) |
| Horizon | h |

Government indicators that exist only for Region IV-A (CPI, NASA POWER, IBTrACS within 600 km) are **not** Stage A inputs, because they are not available for all four areas. They remain in Stage B.

## 3. Models

**A0, real-time nowcast.**
* For each quarter q, a LightGBM regressor of area hunger in q is fitted on area-quarters published on or before q_end(q).
* Its features are hunger_last as of q_end(q), news of quarter q, and national indicators as of q_end(q).
* It is fitted once per q (expanding window), so the nowcast series is as-of by construction.

**A, LightGBM.**
* A binary classifier (HIGH) with the four areas and the four horizons pooled.
* Fixed parameters, no tuning: `n_estimators=200, learning_rate=0.03, num_leaves=7, max_depth=3, min_child_samples=20, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, seed=144`. No monotone constraints.
* A LightGBM regressor of logit(area hunger), with the same features and parameters, feeds Stage C. Its predictive SD per horizon is the SD of its out-of-fold residuals in training (5 folds grouped by issue quarter).

**Walk-forward.**
* At issue i, train on every row (area, i', h) whose target label was published on or before q_end(i).
* Predict the rows of issue i.

**Baselines (identical rows):**

| Code | Baseline |
|---|---|
| B1 | Persistence: the training rate of HIGH given the last published reading's class |
| B2 | Logistic regression, combined features |
| B3 | Logistic regression, government and label-history features only |
| B4 | Logistic regression, news only |
| B5 | LightGBM without news and nowcast |
| B6 | LightGBM, news only |
| Climatology | Training HIGH rate |

Logistic models: standardized inputs, training-median imputation plus missing flags, C = 1.0.

**C, link.** On every province-round (E141 panel, 203 rows):
* Model: logit(p) = α + γ·logit(H̄_a) + δ·r̂ + ε, weighted by 1/(se² + s²), where:
  * p is the measured HFIAS moderate-or-severe prevalence;
  * H̄_a is the SWS hunger of the province's area in the survey reference quarter (Q3), or the survey-year mean if Q3 has no round;
  * r̂ is C4's out-of-fold relative logit (rolling origins for 2015, 2018 and 2019; the 2013 structural estimate trained on later rounds).
* M0 is the same model without γ.

**E2E.** For each survey round with an earlier round (2015, 2018, 2019):
* Stage A is issued at the end of the quarter before the survey reference quarter (h = 1), giving the area hunger forecast.
* C4's rolling r̂ is used.
* Link parameters come from earlier rounds only.
* Output: P(province prevalence > τ*), with τ* = the national HFIAS moderate-or-severe of the latest round (42.8 %). The soft label is computed with the survey SE.
* Compared with C4 alone, mapped through the same link with γ = 0, and with persistence of the previous round's prevalence.

## 4. Evaluation

**Windows.**
* Primary: issues from 2022-Q1 to the last issue whose targets were published by 2026-10-01. The news collection starts in 2021-Q1, and z-scored news needs 4 earlier quarters.
* Secondary: issues from 2014-Q1.

**Metrics per horizon:** n, n_HIGH, accuracy, balanced accuracy, precision, HIGH recall, F1, AUC (block-bootstrap CI), Brier score, ECE (5 bins).

**Inference.** Block bootstrap by issue quarter (all areas of one issue resampled together), 2000 draws, seed 144.

**Reliability at horizon h (all required):**

| Check | Requirement |
|---|---|
| R1 | AUC ≥ 0.70 and the AUC 95 % CI lower bound > 0.50 |
| R2 | HIGH recall ≥ 0.50 and precision ≥ 0.50 |
| R3 | Brier score below climatology |
| R4 | Brier score below B1 persistence, with the 95 % CI of the difference below 0 |
| R5 | ECE ≤ 0.10 |

**Maximum reliable lead time:** the largest h such that every h' ≤ h passes. It is 0 if h = 1 fails.

**News contribution:**
* Brier(A) − Brier(B5) per horizon, with block-bootstrap 95 % CI.
* Holm correction across the four horizons; h = 1 is primary.

**Link:**
* γ with a bootstrap 95 % CI, resampling provinces within rounds.
* Leave-one-round-out weighted RMSE of logit(p) and EB of "p > τ*" for M1 vs M0.

**E2E:** EB, AUC and accuracy on the 125 rolling rows; differences vs C4-only and persistence, with the E141 region-cluster bootstrap.

## 5. Decisions (pre-stated)

| Outcome | Wording that will be used |
|---|---|
| H-A supported at h | Reliability R1–R5 holds; the lead time is stated as the maximum reliable lead time |
| H-N supported | The h = 1 Brier difference CI is below 0 after Holm. Otherwise: "news is an input but did not measurably improve the forecast" |
| H-C supported | The γ CI excludes 0 and leave-round-out RMSE(M1) < RMSE(M0). Otherwise the provincial forecast has no validated time signal and reduces to C4 |
| H-E2E supported | EB(E2E) < EB(C4-only), with the CI below 0 |

* **Adoption as a validated forecast** requires H-A at h = 1, H-C and H-E2E.
* **Otherwise** the E144 output is issued as a candidate (admin routes, sealed).
* **The production pointer is never changed by E144.**

## Deviation D1 (2026-11-04, fix-only)

The first P2 run computed every result, then crashed while writing `results.json`, because some link tables are keyed by tuples. No result had been printed or read. The save step now converts dictionary keys to strings, and `lock()` accepts `--deviation-d1`. The earlier lock is kept as `PROTOCOL_LOCK_P2_before_json_fix.json`. Data, models, thresholds and decisions are unchanged. The rerun is deterministic.
