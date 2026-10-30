# PROTOCOL_E114: genuine forecasting of SWS hunger with one unified LightGBM (frozen 2026-10-30, before any score)

**Hash.** This file's SHA-256 goes in `runner/PROTOCOL_SHA256.txt`. Both are committed before `runner/run_e114.py` runs.

**Study window.** E114 is the authorized exception to the 2021+ study window: SWS hunger from 1998 is used.

**Unchanged.** The served model, the dashboard, the thesis T43c benchmark, R1-R7 and every seal. This experiment adopts nothing. Any integration needs the owner's approval after the results.

## 1. What is forecast, and what is not

**Outcome.** SWS Total Hunger: the % of families who experienced involuntary hunger at least once in the past 3 months.
- It is reported for four areas: NCR, Balance Luzon (BL, which contains CALABARZON), Visayas and Mindanao.
- Several rounds in a quarter are averaged.
- Source: `data/sws_area_rounds_full.csv` (115 rounds, 106 quarters, 1998-Q3 to 2026-Q3).

**What it is.**
- It is **experienced hunger**, the severe end of food insecurity.
- It is not the broader concept (e.g. FIES moderate-or-severe food insecurity).
- It is **regional**. It supports regional forecasting only. No provincial hunger outcome exists, so no forecast is called provincial.

**The 11.3% line.**
- It is the 60th percentile of 6 BL quarters (2021-22), the lowest-hunger stretch in the record (long-run median 13.8%). SWS publishes no such threshold (E109).
- It is kept only for continuity with T43c.
- The primary probabilistic target is relative to history known at issue: **"above usual"** = the target-quarter reading is above the median of that area's readings published before the issue date.

## 2. Forecast design (point-in-time)

**Origin and leads.**
- Origin t; issue date O(t) = day 1 of quarter t+1 (`e114_lib.issue`).
- Leads k = 1, 2, with target quarter t+k.
- At O(t) the newest published reading is usually quarter t−1. So Lead 2 is about three quarters past the latest reading.

**What counts as published.**
- **SWS readings.** Only rounds published strictly before O(t) (`e114_lib.known`). Pre-2021 publication = label month end + 60 days (a rule; spot evidence in `data/sws_release_date_evidence.csv`). Sensitivity: + 100 days (`sws_area_rounds_full_lag100.csv`).
- **Covariates.** Only values published before O(t), using the `e114_lib` rules:
  - CPI usable from day 10 of the next month;
  - LFS 3 months after the reference month;
  - ONI from day 10;
  - palay t−1;
  - typhoons in quarter t;
  - GDELT news of quarter t, after its quarter ends.

**Training rows at origin t.** Every earlier origin's rows whose target reading was published before O(t), across the four areas.

## 3. Models

### U-LGBM (the candidate)

- One unified LightGBM regressor, pooled over the 4 areas and both leads (lead and area as features).
- **Target:** the change y − h_last from the latest published reading. The model must predict movement; it is not a carried-forward value.

**Features.** Only five-group data that exist as point-in-time series over 1998-2026 are used.

| Group | Features |
|---|---|
| Hunger history | h_last; MR (gap to the area's known mean); d_last (last minus previous reading); staleness (t − q_last) |
| Market / food prices | P-FOOD (national food CPI YoY − 3), P-DFOOD (its 1-year change), P-RICE (rice CPI YoY) |
| Climate | C-ONI, C-TC (typhoon count change), P-PALAY (−palay YoY) |
| Employment | P-UNEMP (unemployment change; 2005+) |
| News / NLP | N-SUP, N-AST (GDELT agri-supply+shortage, and assistance, YoY; 2018+; NaN before) |
| Poverty / remittances | **no point-in-time regional series in the repository**. Not represented; reported as a data gap. Nothing is imputed or fabricated. |

**Fitting.**
- Configuration grid: depth {1, 2} × trees {100, 300}, learning rate 0.03, min_child_samples 20, reg_lambda 5, seed 114.
- The configuration is chosen at each origin by the last 4 inner chronological folds of its own training rows (squared error).
- Missing values use native NaN handling. No scaling.

### Comparators (fitted at each origin on the same rows)

| Code | Model |
|---|---|
| RW | latest reading (persistence) |
| MEAN | area mean of known readings (climatology) |
| DAMP | h_last + 0.5^k·(… ) mean reversion: mean + 0.5^k·(h_last − mean) |
| AR1 | AR(1) on the area's known quarterly series |
| RIDGE | ridge (α = 10, standardized in the fold) on the U-LGBM features, NaN → 0 after standardizing |

### Probabilities

- P(y > c) = 1 − Φ((c − ŷ)/σ), with c = "above usual" (primary) or 11.3 (continuity).
- σ = RMSE of **that model's own earlier out-of-sample errors**: same lead, target published before O(t), at least 8, else the origin is skipped for probabilities.
- No evaluation-period information is used.

## 4. Splits (fixed now)

| Split | Targets | Role |
|---|---|---|
| DEV | 2003-Q1 to 2012-Q4 | sanity, inner-fold selection, nothing else |
| **TEST (untouched)** | **2013-Q1 to 2020-Q4** | no model has ever been scored on these readings; scored **once** |
| SECONDARY | 2021-Q1 to 2026-Q3 | inspected in E109-E113, so reported but not counted as independent; the 2025 respondent-base change (adults) sits here |

Phone-mode rounds in 2020 are kept and flagged.

## 5. Success criteria (TEST, decided now)

**U-LGBM shows genuine forecasting skill at lead k only if all of these hold:**

1. **Area-pooled MSE below RW.** Diebold-Mariano with Newey-West (lag k), one-sided p < 0.10, over quarters.
2. **BL MSE below RW.**
3. **"Above usual" Brier below both RW-probability and MEAN-probability**, area-pooled.
4. **Balanced accuracy of the "above usual" call ≥ RW's.**
5. **The skill is not a single episode.** The MSE gain holds in both halves of TEST (2013-16 and 2017-20).

**Reported regardless of the criteria:**
- MAE and RMSE by area;
- accuracy, balanced accuracy, precision, recall, F1, Brier, calibration slope and calibration-in-the-large;
- a confusion matrix for both thresholds;
- the predicted vs observed "above usual" rate;
- quarter-block bootstrap CIs;
- results by area and by half;
- DEV, TEST and SECONDARY separately.

## 6. Contributions, robustness, leakage

**Group ablation.**
- Each group (hunger history, market, climate, employment, news) is removed and U-LGBM is refitted at every origin.
- Δ MSE on TEST, quarter-block bootstrap 90% CI, Holm correction across the five groups.
- SHAP is reported as description only.

**Robustness.**
- The lag-100 release rule.
- Training on pre-2013 targets only (no expanding into TEST). Reported, not selected.

**Leakage tests.**
- Every reading used has published < issue.
- Every covariate is available before the issue.
- Every training target was published before the issue.
- σ uses only earlier errors.
- "Usual" uses only known readings.

## 7. Provincial layer (no forecast)

- With no provincial hunger outcome, provinces get a **vulnerability profile** (existing V1 and the price-pressure component), not a forecast.
- Any dashboard change that would show a regional forecast separately from provincial vulnerability is proposed only if §5 passes, and requires the owner's approval.
- The approved UI colours are never changed.

## 8. Decision

- **§5 passes at lead k:** "genuine skill at lead k (regional)".
- **§5 fails:** "no genuine skill beyond persistence at lead k". The latest reading remains the honest outlook.
- Either way, the exact blocker is reported.
