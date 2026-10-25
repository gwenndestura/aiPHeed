# E109: forecasting experienced hunger (SWS Balance Luzon). Pre-registered protocol

**Date:** 2026-10-25. **Branch:** `aiPHeed/e109-hunger-forecasting`, from E108 head `b56d90e`.
**Freezing:** hashed in `runner/PROTOCOL_SHA256.txt` before any E109 model is scored. Later changes go in dated, hashed addenda, and the results they affect are labelled exploratory.

**Already seen before freezing:**
- every SWS value through 2026-Q3;
- the E69, E76, E105, E107 and E108 results on regional hunger (persistence and the latest reading were never beaten);
- the sources in `sources/SOURCES_LOG.md`.

**No historical quarter is unseen**, so every retrospective E109 result is development evidence.

## 1. The outcome (Approach A, primary)

- **Measure:** SWS Total Hunger, the percentage of families answering yes to "In the last three months, did it happen even once that your family experienced hunger and not have anything to eat?" (S1). This is **experienced hunger**, one recognised dimension of food insecurity. It is not the FAO FIES scale, and it is not food poverty.
- **Area:** Balance Luzon (Luzon outside Metro Manila), a **regional** estimate. **There is no provincial or municipal value.**
- **Quarter value H_q:** the mean of the Balance Luzon values of SWS's **non-commissioned** survey rounds whose fieldwork falls in quarter *q* (`data/outcome_rounds.csv`, `in_primary_series`).
  - The commissioned Stratbase-SWS March 2025 round (registered voters) is excluded.
  - This gives 20 quarters, 2021-Q2..2026-Q3, with no value for 2021-Q1, 2022-Q1 or 2025-Q1.
- **Known at issue date O(*t*)** (day 1 of quarter *t* + 1): H_q is known iff every primary round of *q* was published before O(*t*).
- **Sensitivity series:**
  - **S-ALL:** all rounds, including the commissioned one.
  - **S-PROD:** the E107/E108 `definition_A` series.
  - **S-HH:** household-head rounds only (≤ 2024-Q4), because the respondent base changed in 2025.

## 2. Binary outcomes (Approach B, secondary)

SWS publishes **no** LOW/HIGH threshold for total hunger (S1–S6). Moderate and Severe are frequency categories, not prevalence cut-offs. Every threshold here is therefore **research-defined**:

| Rule | HIGH if | Origin |
|---|---|---|
| **B1** | H_{t+k} > 11.3 | E40 research threshold (P60 of 2021–22), frozen 2026-10-15, before E109 |
| B2 | H_{t+k} > 15.0 | round-number sensitivity |
| B3 | H_{t+k} > 20.0 | round-number sensitivity, near SWS's cited 2025 national average of 20.2% (S1) |
| **B4** | H_{t+k} − H_last(*t*) > 4.0 | "a rise larger than SWS's published Balance Luzon margin of error (±4%)" (S1, S3): a worsening signal |

A binary forecast is P(HIGH) = Φ((forecast − c)/σ̂_k), where σ̂_k is the RMSE of that method's own earlier lead-*k* errors known at O(*t*) (≥ 4 pairs, else the training SD of the change), and c is the threshold. For B4, c = H_last + 4.

## 3. Approach C (composite)

T43 (hunger > 11.3 AND provincial price pressure) is **not re-run**. It is reported from E108 as a composite risk proxy. Its price condition is a provincial price measure, so it is not used as the food-insecurity outcome.

## 4. Horizons and origins

- **Leads:** *k* = 1, 2, 3, 4. Target quarter *t* + *k*; issue date O(*t*).
- **Training pairs at origin *t*:** (origin *t*′ < *t*, target *t*′ + *k*), where H_{t′+k} is known at O(*t*) and H_last(*t*′), the latest H known at O(*t*′), exists.
- **Evaluation:** every target quarter with an outcome and an origin with ≥ 8 training pairs.
- **One row per quarter.** Nothing is replicated across provinces.

## 5. Methods (all on identical origins)

**Baselines (no learning):**

| Name | Forecast |
|---|---|
| RW | H_last |
| MEAN | mean of all known H |
| MA2 | mean of the last two known quarters |
| SEAS | H of the same calendar quarter one year before the target, if known; otherwise RW |

**Candidates:**

| Name | Model |
|---|---|
| LL | Local-level (Kalman) filter. Observation variance R = (4/1.96)², from SWS's published Balance Luzon margin. State variance Q = max(var(ΔH between consecutive known quarters) − 2R, 0.25), training data only. Forecast = filtered level. |
| RIDGE | H_last + ridge regression of ΔH = H_{t+k} − H_last on the regional means of the 13 E107 columns (12 families). Standardised, training-median imputation, α = 10 (fixed). |
| **LGBM (primary)** | H_last + LightGBM regressor of ΔH on the same 13 regional columns (all 12 families eligible). Depth 1, num_leaves 2, min_child_samples 3, learning rate 0.05, L2 = 5, trees ∈ {25, 75} chosen by inner MAE on the last 4 training targets; deterministic, seed 109. Starts from 0, i.e. from RW. |

Features are E107's (`e107_lib.feature_table(k)`, issue-date cut, future-perturbation tested) averaged over the five provinces per origin.

## 6. Metrics

- **Continuous:** MAE, RMSE, and skill = 1 − MAE/MAE_RW.
- **Uncertainty and tests:**
  - quarter-block bootstrap 95% CI of MAE (block length *k*, 2,000 draws, seed 2026);
  - the Harvey–Leybourne–Newbold-corrected Diebold–Mariano test on the absolute-error loss differential with Newey–West variance (lag *k* − 1), one-sided.
- **Binary:** accuracy, balanced accuracy, precision, recall, F1, AUC (if both classes have ≥ 2 quarters), Brier, confusion matrix; compared with persistence (classify H_last) and climatology (known HIGH share).

## 7. Reliability rule (frozen now)

**Continuous rule for a candidate at lead *k*:**

| | Criterion |
|---|---|
| C1 | ≥ 8 evaluated quarters |
| C2 | MAE < the lowest MAE among RW, MEAN, MA2 and SEAS, with DM p < 0.10 against that baseline |
| C3 | MAE ≤ 4.0 points, the SWS-published Balance Luzon sampling margin (errors within the survey's own precision) |
| C4 | MAE < the best baseline's MAE in both chronological halves |
| C5 | MAE ≤ the best baseline's MAE on the last 4 evaluated quarters |
| C6 | confirmed on outcomes not seen before freezing (none exist yet) |

**Status:**
- **reliable** = C1–C6;
- **provisional** = C1–C5 pass, C6 pending;
- **not reliable** = C2, C3, C4 or C5 fails with C1 met;
- **insufficient evidence** = C1 fails.

**Baselines** cannot pass C2 by definition. For each baseline only C3 is reported, as "usable accuracy", which is not a reliability claim.

**Binary rule (B1–B4, secondary):** accuracy ≥ 0.75; balanced accuracy ≥ 0.65; both recalls ≥ 0.5, with each class present in ≥ 2 quarters (otherwise insufficient evidence); Brier < persistence and < climatology.
- This is the thesis's 75% requirement plus class balance.
- The same status labels apply: provisional at best until C6.

**Maximum reliable lead** = the largest *k* such that Leads 1..*k* are all reliable. Also reported:
- the maximum provisional lead;
- the maximum lead tested (4).

**Primary decision:** the continuous rule applied to the primary candidate, LGBM. A different candidate is recommended only if it passes more of C1–C5 at Lead 1 **and** its Lead-1 MAE is lower than LGBM's with DM p < 0.10.

## 8. Provinces and LGUs

- The forecast is regional and identical for the five provinces.
- Every one of the 142 LGUs receives the status **"insufficient local evidence: no LGU or provincial hunger observation exists; the regional Balance Luzon forecast is shown"**. No LGU gets a LOW/HIGH label.
- PSA SAE 2021 poverty and subsistence incidence are shown as context only.

## 9. Prospective seal

- Forecasts of every method at Leads 1–4 from origin 2026-Q3 (issue 2026-10-01), with 80% intervals and binary probabilities.
- Recorded with source hashes in `out/sealed_prospective.csv` and its SHA-256.
- The scorer `runner/score_prospective.py` scores them once SWS posts each target quarter. That happens only after the quarter ends and its release is published (about 10 days to 3.5 months after fieldwork).
- The E107 and E108 seals are untouched.

## 10. Tests (`backend/tests/unit/test_e109.py`)

- outcome construction (rounds, commission rule, quarter means);
- known-at-issue rule;
- no future value in training pairs, features, σ̂ or the Kalman parameters (future perturbation);
- thresholds;
- the 12-family column map in the LightGBM;
- reproducibility;
- seal hashes (E107, E108, E109);
- API.
