# E47 protocol: cutoff-verified candidates for HIGH/LOW discrimination (frozen before any E47 score)

**Written:** 2026-10-17 on branch `e46-lead2-policy`, from 74031cf.
**Freeze:** SHA-256 (LF) in `runner/PROTOCOL_SHA256.txt`, committed with code, data and tests before any E47 candidate is fitted. Run once, then a byte-identical repeat.

## 0. Evidence status, stated before any result

Every 2022–2026 quarter was examined in E41–E46, including all of S44's rows. **No historical score from E47 can be independent validation.** The only independent evaluation is prospective (section 7).

What I looked at before writing this, all diagnostics (`runs/diagnostics.json`, `runs/verify_e46_metrics.json`):

**T43 label support:**
- 18 HIGH labels in 19 labelled quarters: 12 switched on by the gap rule alone, 5 by both rules, 1 by food alone.
- Rizal is never HIGH.
- 47% of label variance lies within quarters.

**I7's errors:**
- I7's 9 missed HIGHs in 2024-Q2..2026-Q3 break down as:
  - 4 hunger misses in 2024-Q2, where the price parts were right;
  - 4 gap misses in 2024-Q4/2025-Q1, where the gap was forecast below threshold;
  - 1 food miss (Cavite 2026-Q2, 0.02 points above threshold).
- I7's 0.800 on S44: 24 of its 28 correct rows are LOW calls, and always-LOW scores 0.743.

**Trigger coverage:**
- Employment, OFW, ENSO, hunger and policy inputs are identical for all provinces.
- Remittances are missing for 2026.
- The news OFW share is always 0.

## 1. Cutoff convention (audited)

- **Issue time:** I7's convention, 00:00 on day 1 of quarter t+1.
- **Audit:** `runner/e47_cutoff_audit.py i7` found every input at every origin 2021-Q3..2026-Q3 published before the issue time. The minimum margin is 18 days for provincial CPI and 3 days for SWS (exact posting dates).
- **I8 (15th of the month):** it also passes, but its September CPI margin is about 2 days, with no per-month provincial release log. I8 is therefore kept as a **reference only**.

## 2. Energy input (new data; one justified addition)

**Weakness addressed:**
- The gap rule (food − headline) switches on 17 of the 18 HIGH labels.
- Headline inflation's non-food part moves with fuel and transport prices.
- None of the five groups carries an energy price.

**Data:**
- **Series:** FRED DCOILBRENTEU (Brent spot, daily, from EIA), 2021-01-04 to 2026-09-30, `data/brent_daily_fred_raw.csv` (provenance and sha256 in `data/PROVENANCE.md`). No pre-2021 observation.
- **As-of rule:** only the 30 days ending **10 days before** each issue date, which covers EIA's publication lag of a few days.
- **Features:** `brent_yoy` (window vs the same window a year earlier) and `brent_mom3` (vs the window 3 months earlier).
- **Grouping:** energy is a market and price input (Market / Prices group).

## 3. Candidates (fixed now)

| Arm | Weakness addressed | Specification |
|---|---|---|
| **I7-E** | gap misses (headline unmodelled) | E46 I7 exactly, with `brent_yoy`, `brent_mom3` added to both price residual inputs |
| **SL-P** (price-only, simple) | the bivariate-normal mapping and fixed 0.5 cut; sample size | L2 logistic (C = 1) on as-of margins against the T43 thresholds: food and gap base projections at drift 1.0 and 0.0, and H_last − 11.3. The model learns the drift and the price/hunger weighting from labels. |
| **SL-5T** (five-trigger, simple) | does any trigger add to price-only? | SL-P margins + `rice_whsl_yoy`, `brent_yoy` (market); `tc_count`, `enso`, `palay_yoy` (climate); `fish_yoy` (fisheries); `ur_yoy` (employment); `remit_php_yoy`, `fx_yoy` (OFW); L2 logistic, C = 0.1 |
| **LGBM-C** (corrected LightGBM) | the "best corrected LightGBM" comparison | the SL-5T inputs; LightGBM, 3 leaves, depth 2, ≥ 8 rows per leaf, 150 trees, learning rate 0.03, λ = 10; monotone increasing in the five margins |

**Shared rules for SL-P, SL-5T and LGBM-C:**
- **Training pairs:** origins t′ with t′ + 2 ≤ t − 1, with T43 labels available at O(t).
- **Eligibility:** both classes, ≥ 3 HIGH, ≥ 6 target quarters.
- **Preprocessing:** median imputation + missing flags + standardisation, fitted on the training rows only.
- **Decision threshold, training data only:**
  - embargoed forward chaining inside the training pairs: the fold at q is fitted on targets ≤ q − 3, using the last 6 folds;
  - pooled out-of-fold balanced accuracy over {0.15, 0.20, …, 0.60}, with ties going to the cut closest to 0.5;
  - 0.5 if the pooled out-of-fold set has < 3 HIGH or < 3 LOW rows.
- **No resampling** across time.

**References** (committed predictions, not refitted): I7, I8, I2 (E44), and BASE-m1.0 (the structural signal at the E41 default drift).

**Baselines:** always-LOW, persistence, E38-served, E41-M1.

## 4. Evaluation

- **Rows:** every labelled target ≤ 2026-Q3 for which all arms exist (identical rows). The number of independent quarters and of province-quarter rows are both reported.
- **Metrics:** accuracy (date-cluster CI), balanced accuracy, both recalls, precision, F1, Brier, AUC, confusion matrix, share of LOW calls, by quarter.
- **Stability:** leave-one-quarter-out and by province.
- **Significance:** paired date-level tests with Holm correction.

## 5. Selection rule (fixed now)

**Track record available at the 2027-Q1 issue date:**
- **Arms considered:** the five-trigger arms {I7, I7-E, SL-5T, LGBM-C}.
- **Criterion:** the lowest Brier score on the labelled targets ≤ 2026-Q2. Ties go to the listed order.
- **Why:** this is the choice a forecaster could make on 2026-10-01 from as-of forecasts only.
- **Caveat:** these are mostly the rows the result is reported on, so the selected model's historical score is development evidence.

## 6. Development criteria and serving

**The selected arm meets the development criteria only if both hold:**
1. it passes E44 gates A0–A4 on the evaluation rows: accuracy ≥ 0.75; balanced accuracy ≥ 0.70 with both recalls ≥ 0.60; Brier better than always-LOW and persistence; calibration-in-the-large CI contains 0;
2. its minimum leave-one-quarter-out accuracy is ≥ 0.70.

**If it meets them:**
- a versioned record is served behind `AIPHEED_LEAD2_MODEL=e47` (experimental);
- `e46` and every frozen forecast stay unchanged;
- production stays E38.

**Otherwise:** nothing new is served.

`forecasting_acceptance_met` stays false either way.

## 7. Prospective freeze and acceptance

- **Freeze:** every E47 arm's 2027-Q1 forecast (O = 2026-10-01, CPI through 2026-08, Brent window ending 2026-09-21) goes to `frozen/E47_PROSPECTIVE_2027Q1.json` (sha256), together with the selected arm.
- **Rule:** acceptance follows the E46 PROTOCOL §5 rule. Over 2027-Q1..Q4 (20 province-quarters):
  - accuracy ≥ 0.75;
  - balanced accuracy ≥ 0.70;
  - both recalls ≥ 0.60;
  - Brier better than always-LOW and persistence.
- **Nothing is reselected on outcomes.**
