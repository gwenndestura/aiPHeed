# E11 Target and Features

## 1. The three components (kept separate)

| Component | E11 definition |
|---|---|
| **Scoring formula (S1)** | stress(p, t) = SWS_t + 2 × (food CPI YoY(p, t) − five-province mean_t). Computed by `risk_score_v2.compute_stress`, unchanged (hash `5b6c83d6…`). |
| **Forecasting model** | Predicts next-quarter S1 stress (regressors), or the probability that stress exceeds τ0 (classifiers) |
| **Classification rule** | Probability ≥ 0.50 → HIGH, < 0.50 → LOW. Stress forecasts: > τ0 → HIGH. INSUFFICIENT_DATA when a required input is missing or the SWS input is more than 3 quarters old. |

## 2. S1 verification (before use)

| Check | Result |
|---|---|
| Rebuilt S1 vs stored `stress_score` | 80/80 rows; max difference 0.000033 |
| Missing values | Stay NaN. Verified by reading `compute_stress` and by the existing `test_risk_score_v2` unit test (not re-run in E11). The E9 synthetic test checks the same rule for `cpi_rel`. |
| Five-province mean | Requires all five provinces (tested) |
| τ0 | **10.8433**: median of the 8 labels published before 2023-10-01 (all 8 verified as published before then) |
| Event | Strictly greater than τ0 (`classify`: stress = τ0 is LOW) |

**Limitation, documented and not changed:** the weight of 2 is unvalidated, because no independent provincial outcome exists. S1 stays the primary target.

**The target is constructed.** It is not observed provincial food insecurity.

## 3. Features (values as known at the origin, the first day of the target quarter T)

| Feature | Definition | Varies across provinces? |
|---|---|---|
| `last_published_stress` | S1 of the latest label published before the origin | Partly (31% within-quarter variance) |
| `sws_hunger` | Latest SWS round published before the origin | No (regional) |
| `sws_change` | Last round minus the previous round | No |
| `lps_change` *(new)* | Stress change between the two latest published labels | Partly (48%) |
| `anchor_dev` *(new)* | Provincial deviation d of the latest published label | Yes (100%) |
| `dev_change` *(new)* | Change in d between the two latest published labels | Yes (100%) |
| `cpi_rel`, `cpi_rel_lag1` | YoY minus the five-province mean, at T−2 and T−3 | Yes (100%) |
| `food_cpi_yoy` (+ lag1) | Provincial YoY at T−2 (and T−3) | Partly (about 30%) |
| `cpi_dev` | YoY(T−2) minus the mean of YoY(T−3…T−6), at least 2 quarters | Partly (18%) |
| `poverty_incidence` | Survey vintage released before the origin | Mostly (90%), but static between surveys |
| `headline_cpi`, `food_minus_headline_yoy` (+ lag1) | Regional CPI at T−2 | No |
| `unemployment_rate` | LFS at T−2 | No |

*Within-quarter variance share = the fraction of a feature's variance that lies between provinces in the same quarter (from `diagnostics.json`).*

**For comparison:** the target S1 stress has a within-quarter share of 0.348. **About 65% of its variance is shared regional movement**, and the provincial deviation d is 100% within-quarter by construction.

## 4. Feature sets

| Set | Members | Used in |
|---|---|---|
| core | `last_published_stress`, `sws_hunger`, `sws_change` | Direct regressor, classifier |
| core_plus | core + `lps_change`, `anchor_dev` | Direct regressor |
| compact | core + `cpi_rel`, `cpi_rel_lag1`, `food_cpi_yoy`, `food_cpi_yoy_lag1`, `cpi_dev` | Direct regressor, classifier |
| expanded | compact + poverty, headline CPI, food-minus-headline (+ lag1), unemployment | Direct regressor |
| provincial | `cpi_rel`, `cpi_rel_lag1`, `anchor_dev`, `dev_change`, `cpi_dev`, `food_cpi_yoy`, `food_cpi_yoy_lag1` | Decomposed (predicts d) |
| residual | core_plus + `cpi_rel`, `cpi_rel_lag1`, `cpi_dev` | Residual (predicts stress − S1 rule) |
