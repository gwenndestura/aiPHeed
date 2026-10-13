# Target and Timing Audit (E13, Amendment 1)

**Purpose.** For every target and input, this audit records:

- what it is and where it comes from;
- when it became available;
- whether it was available at each forecast origin.

The E13 outcome audit is treated as an **initial assessment**. Each claim below is marked **verified** (checked against a project file in this experiment), **recorded** (taken from an earlier project record and not re-checked), or **unverified**.

**Forecast origin.** origin(T) is the first day of target quarter T. All inputs must be published strictly before it.

## 1. Targets

| Target | Source file and column | Level and unit | Observation period | Constructed from predictors? | Independent of what it is evaluated against? |
|---|---|---|---|---|---|
| **A**: regional hunger H[T] | `details.json` → `two_layer.regional_layer_rounds` (`H`, `published`, `quarter`); quarterly mean of rounds | Balance Luzon; % of families | 18 quarters, 2021-Q2..2025-Q4 (none in 2021-Q1, 2022-Q1) | No. Predictors are earlier rounds of the same series. | Yes. A survey measurement, independent of CPI. |
| **B1**: provincial food inflation F[p,T] | `realized_components_2021_2025.csv` → `F` | Province; % year-on-year | 2021-Q1..2025-Q4, 100/100 cells | No. Predictors are F two quarters earlier. | It is a PSA measurement. **It is not food insecurity.** |
| **B2**: relative pressure D[p,T] | Same file → `D` (= F − `mean5`) | Province; percentage points | 100/100 cells | **Derived from F** (the target quarter's own five F values). Predictors are D of earlier quarters. | It is a derived price indicator. **It is not food insecurity.** |
| (Reference) S1 | Same file → `S1` | Province; index | 80 rows | **Constructed from H and D** | **Not independent.** Not a target in E13. |

## 2. Inputs and their availability at the origin

| Input | Used by | Reference period relative to T | Publication evidence | Available at origin(T)? |
|---|---|---|---|---|
| SWS round values | A (`H_last`, `A_mean`, `A_drift`, training targets) | Rounds published before origin(T); in practice 1–2 quarters old | **Verified per round in the project record**: 18 `verified`, 3 `verified-single`. This experiment re-checked them programmatically (`published < origin`). | **Established** (code-enforced) |
| SWS fieldwork quarter | A (which quarter a round counts as) | — | Assigned by E12 from the round names. The 2025-Q2 and 2025-Q3 rounds come from the 2026-10-09 supplementary collection. `docs/DATA_AVAILABILITY.md` recorded those quarters as having no round. | **Recorded; the disagreement is unresolved** (see the sensitivity S-A1 in v1) |
| Provincial F, D, mean5 at **T−1** | none | — | The last month of T−1 ends the day before origin(T), so no release can precede the origin | **Certainly unavailable. Never used.** |
| Provincial F, D, mean5 at **T−2** | B1, B2 (all primary arms); A_ridge_HF | Quarter ended about 3 months before the origin | **Proxy date:** national release + 14 days. The national and regional release dates are recorded as verified in E9. The provincial date is verified only for 2024-Q4. The margin from the proxy to origin(T) is about 10 weeks in every documented case. | **Not established.** All Task B results and A_ridge_HF are labelled **exploratory (timing)**. |
| Provincial F, D, mean5 at **T−3** | Sensitivity S-T3 | Quarter ended about 6 months before the origin | Same proxy; margin about 5 months | **Not verified**, but would need a delay of more than 5 months to fail |
| Province historical means (`Fbar_p`, `Dbar_p`) | B1_pmean, B2_pmean, B2_ridge_DP | 2021-Q1..T−2 (or T−3) | As above | Same classification as T−2 (or T−3) |
| Training targets for B | All fitted B arms | q ≤ T−2 (primary); q ≤ T−3 (S-T3) | As above | Same classification |

**What the timing tests show.** The future-perturbation checks overwrite every value not allowed at the origin with 999. They returned identical forecasts for all v1 arms (27 quarter checks), all A1 arms and all S-T3 arms. **This proves the code follows the availability rules. It does not prove the rules match real release dates.**

## 3. Vintages and revisions

- **Current vintage only.** The stored CPI values are the current ones. First-release values were not reconstructed.
- **Base changes:** any change of the CPI base, or revisions after release, would make early training values differ from what a forecaster saw at the time. **This is unverified and unquantified.**
- **SWS:** values as published, with no revisions recorded.

## 4. Missing data and preprocessing

| Item | Handling |
|---|---|
| SWS quarters with no round (2021-Q1, 2022-Q1) | **Not imputed.** They are skipped as targets. The trend in `A_drift` uses the first and last complete quarters. |
| Provincial F | **Complete** (100/100). The rule exists all the same: a quarter with fewer than 5 provinces is INSUFFICIENT_DATA for D and its rank, never 0. **No test row was INSUFFICIENT_DATA.** |
| Scaling | Ridge features are standardized with **training-row** means and SDs at each origin. Trees and LightGBM are unscaled. |
| Hyperparameters | **Fixed in advance** (ridge α = 1; tree depth 2 and leaf 5; LightGBM settings in Amendment 1 §3). **No tuning**, so no nested validation was needed. |
| Folds | Expanding window by quarter. All five provinces of a quarter are in the same fold. **No random splits.** |

## 5. Consequences

| Task | Timing status | How results are labelled |
|---|---|---|
| A: regional hunger | Established, apart from the quarter assignment of the 3 supplementary rounds | Small sample, previously explored quarters |
| B1, B2: provincial prices | **Not established** (proxy dates) | **Exploratory (timing)** and previously explored. S-T3 tests robustness under a far more conservative rule. |
| C: official comparisons | Not a forecasting task | Descriptive |
