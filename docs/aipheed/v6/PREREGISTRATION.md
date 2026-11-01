# v6 Pre-registration (Stage 5)

**Status:** committed **before** any v6 model is fitted. The SHA-256 (LF-normalised) is frozen in `backend/tests/unit/test_v6_preregistration.py`. Changes after fitting go to `v6/DEVIATIONS.md`; affected results are labelled EXPLORATORY.

**Basis:** `CONSTRUCT.md`, `DATA_AUDIT.md`, `FEASIBILITY.md` (Gate 2: no route passes the 0.85 oracle filter at Lead 2), `METHOD_SOURCES.md`. Frozen values (`../PROTOCOL_LOCK.md`, `8bae6962…dd0d3`) are read-only.

## 1. Target and tolerances

- **Target:** SWS involuntary hunger by SWS area (lock T1); P-DASH; Lead k = D − 1 + k; **Lead 2 primary**; Leads 1–4 reported. The claim scope is "SWS area (Balance Luzon contains CALABARZON)", never provincial.
- **Primary tolerance: FROZEN**, 1.645 × binomial SE (lock T1–T4).
- **Proposed amendment (R3): NOT ADOPTED.**
  - Formula: tol = 1.96 × SE_pub, the published 95 % margin (FEASIBILITY R3).
  - Status: `PROPOSED_NOT_ADOPTED`. Adviser sign-off `________`, date `________`.
  - Scope: future quarters only.
  - Always reported beside the frozen result.

## 2. Candidates (4, simplest first)

| # | Name | Definition |
|---|---|---|
| 1 | PERSIST | Latest quarter value known at the issue |
| 2 | LL-K | v2 local level with noise multiplier (unchanged code) |
| 3 | **LGBM-D** | PERSIST + LightGBM-predicted change. Pooled panel over the 4 areas, one model per lead. |
| 4 | **LGBM-D-S** | PERSIST + w × LGBM-D change, with w ∈ {0, 0.25, 0.5, 0.75, 1} chosen on the inner early-stopping fold by MAE (ties → smaller w). This is learned shrinkage toward persistence. |

### 2.1 LightGBM features (per area row; all point-in-time)

| Feature | Definition |
|---|---|
| `last_change` | Latest minus previous known quarter value (`as_of`) |
| `dev_mean` | Latest known value minus the expanding mean of known values |
| `h` | Quarters from the latest reading to the target |
| Area dummies (3) | Metro Manila, Visayas, Mindanao (Balance Luzon = reference). Native categorical handling is off. |
| Exogenous features | The v4 snapshot features (`rice_yoy`, `typhoons_PAR`, `oni_quarter_mean`, `E1_unemployment_change_pp`, `news_gdelt_shortage_share`, `poverty`), admitted **in-fold** by the v4 stability rule (≥ 6 issues, \|ρ\| ≥ 0.30, sign stable in both halves; `app.forecasting.v4.models.stable`). At most 6. Missing values are left missing (LightGBM handles NaN natively). |

### 2.2 LightGBM configuration (fixed; LightGBM docs, "Deal with Over-fitting")

| Setting | Value |
|---|---|
| Objective | L2 |
| `num_leaves` | 4 |
| `max_depth` | 2 |
| `min_data_in_leaf` | 10 |
| `learning_rate` | 0.05 |
| `lambda_l1` | 1 |
| `lambda_l2` | 5 |
| `feature_fraction` | 0.8 |
| `bagging_fraction` | 0.8 |
| `bagging_freq` | 1 |
| `max_bin` | 63 |
| `min_gain_to_split` | 0 |
| `deterministic` | True |
| `force_row_wise` | True |
| `seed` | 2026 |
| `verbose` | −1 |
| `n_estimators` | ≤ 200 |

**Early stopping (20 rounds):**
- **Inner fold:** the chronologically last 25 % of the training issues (at least 2 issues).
- **Refit:** on all training rows with the best iteration.
- **Fallbacks:**
  - fewer than 30 training rows → change = 0;
  - best iteration 0 → change = 0.

**Not used** (no out-of-sample-supported mechanism sign; FEASIBILITY c):
- `linear_tree`;
- `monotone_constraints`.

**Training rows at issue I, lead k:**
- lead-k P-DASH rows with issue < I, n_obs ≥ 4, and truth known at I (`as_of`);
- target = truth − latest reading.

### 2.3 Baselines (same rows; never selectable)

| Baseline | Development rows | Sealed forecasts |
|---|---|---|
| PERSIST | Candidate | Candidate |
| TREND-D | E136 | v4 seal |
| CLIM | E136 | v4 seal |
| RIDGE-ALL | E136 / E132 | **`v6/sealed/V6_BASELINE_SEAL.csv`** (reproduced exactly) |
| HFM-X | E136 | **`V6_BASELINE_SEAL.csv`** (same P-DASH cutoff) |
| SEAS-LLM | E136 | v4 seal |
| V2 | v2 outer predictions | v2 seal |
| V4 | v4 development-test predictions | v4 seal |

## 3. Tiers

| Tier | Contents |
|---|---|
| TRAIN | As v4 `tiers/TRAIN_rows.csv`, hash-checked |
| DEVELOPMENT-TEST | As v4 `tiers/DEVTEST_rows.csv`, the S-U rows; non-confirmatory |
| SEALED | Future targets (2026-Q4 onward) only: `v6/sealed/V6_PROSPECTIVE_SEAL.csv` (V6, the candidates and LGBM explanation totals at 2026-07-01 / 2026-10-01) plus the baseline seals above. Every scoring run is logged in `v6/sealed/ACCESS_LOG.md`. **No withheld historical quarters** (0 unseen, < 6). **No held-out areas** (all 4 areas seen). Leave-one-area-out is a development check only. |

## 4. Selection rule (mechanical)

- **Incumbent:** PERSIST.
- **Procedure:** challengers in the order LL-K, LGBM-D, LGBM-D-S. A challenger replaces the incumbent only if the paired cluster-bootstrap 95 % CI (2 000 draws, seed 2026) of the inner Lead-2 Δ within (frozen tolerance) lies entirely above 0, with ≥ 6 inner target quarters.
- **V6** = the selection at each issue.
- **Served V6** = the selection at 2026-10-01.

## 5. Metrics and tests

**Primary:** Lead-2 share within the frozen tolerance, with a moving-block bootstrap CI (block 3 target quarters, 10 000 draws, seed 2026).

**Superiority ("beats every other model"):**
- For each of the 8 baselines: one-sided paired moving-block bootstrap p for within(V6) − within(b) > 0.
- Holm correction across the 8 at α = 0.05.
- YES only if all 8 adjusted p < 0.05.
- **Secondary:** the DM test with the HLN correction on squared error per baseline (reported only).

**Also reported:**
- MAE, RMSE, bias, high-tercile bias;
- sharp-increase detection;
- variance ratio, correlation;
- 80 % split-conformal coverage and width;
- train / inner / outer MAE;
- results by period (pre-surge, 2024, 2025–26);
- training-window sensitivity (start 2022-Q1);
- leave-one-area-out;
- everything under the proposed R3 tolerance (labelled).

**Reliability:** frozen N1–N7 (`e130_lib`).

**Explanation:** if an LGBM candidate is served, LightGBM's native TreeSHAP (`pred_contrib=True`) per feature, summed to the five groups plus "history" and "area". Contributions + expected value = predicted change, exactly (tested). They are labelled model attributions, not causes.

## 6. Mechanical verdict table

Code: `app.forecasting.v4.verdict` (unchanged).

| Claim | DEVELOPMENT-TEST | SEALED, < 10 quarters or < 40 rows | SEALED, N1 met |
|---|---|---|---|
| 75 % (frozen / proposed) | `DEVELOPMENT_ONLY` | `NOT_YET_TESTABLE` | `CONFIRMED` if the one-sided 95 % lower bound ≥ 0.75; `REJECTED` if the upper bound < 0.75; else `INCONCLUSIVE` |
| Beats all 8 | Holm rule (development, non-confirmatory) | `NOT_YET_TESTABLE` | Holm rule |
| Lead k reliable | N1–N7 label (development) | `NOT_YET_TESTABLE` | N1–N7 |

## 7. Sanity controls (must behave as stated)

| Control | Expected |
|---|---|
| Shuffle-target (values permuted within area; full procedure rerun) | LGBM gains nothing over PERSIST |
| Future shift (cutoff after the target's publication) | The within share rises far above the honest run |
| Injected round on or after the issue | Forecast unchanged |
| Snapshot used at another issue | `LeakageError` |

## 8. Failure

- **Research failure:** on sealed data, once testable, `REJECTED` for 75 % or `NO` for beats-all. On development data, < 0.75 is expected (Gate 2), is reported, and leads to no redesign.
- **LightGBM failure:** if neither LGBM candidate is selected at the served issue, LightGBM is reported as **not supported**, and the simpler selected model is served.
