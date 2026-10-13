# E9: The Improved Scoring Formula (S1) and How the Targets Were Generated

## 1. Which formula, and why this one

**Selected: S1.** It is the corrected Equation 3, implemented in `app/ml/features/risk_score_v2.py`.

| Step | Record |
|---|---|
| Diagnosis and candidates | `experiments/2026-10-11_devprotocol/SCORING_FORMULA_REPORT.md` and `E5_SCORING_PROTOCOL.md` (2026-10-11) |
| Recommended as the label computation | `RISK_SCORING_DECISION_REPORT.md` §4 |
| **Adopted as the target** | E6 (`E6_REVISED_SCORING_PROTOCOL.md` §1; `REVISED_SCORING_REPORT.md` §C, 2026-10-12) |
| Kept unchanged | E7 (`INDICATOR_EVIDENCE_REPORT.md` §1, §4) |

**Candidates evaluated and rejected in those records** (so no ambiguity remained):

| Candidate | Reason |
|---|---|
| S2 (standardized, equal weights) | 35/35 test rows HIGH |
| P1 (inflation-rate rule) | Measures price pressure, not hunger |
| D-D (two-condition rule) | Not predictable (balanced accuracy 0.535) |
| Year-over-year stress change | Too few folds |
| α = 1, 2.74, 4 | No outcome exists to justify a change |

**The production `label_cpi` (index-trend rule) is the old path.** It was not used. Production scoring is unchanged.

## 2. Exact specification

**stress(p, t) = SWS_t + α × ( food_cpi_yoy(p, t) − (1/5) × Σ over the five provinces of food_cpi_yoy(t) )**, with **α = 2**

| Element | Specification |
|---|---|
| SWS_t | Balance-Luzon involuntary hunger (% of respondents) of the quarter. Several definition-A rounds in one quarter are averaged. **Regional: one value shared by all five provinces.** |
| food_cpi_yoy(p, t) | PSA provincial food CPI, year-on-year %, 2018 base |
| Weights | 1 on SWS; **α = 2 on the provincial deviation**, a documented, unvalidated design parameter |
| Normalization | None. The deviations of a complete quarter sum to zero. |
| Missing data | Any missing input gives NaN, never 0. The regional mean exists only when all five provinces have a value. Only quarters with all five provinces scored are labels. |
| Event | **HIGH if stress > τ** (strict); stress = τ is LOW |
| τ (threshold) | **Frozen point-in-time median:** the median stress of complete quarters whose labels were published before the as-of date (Rule L1; at least 8 quarters) |
| τ used in E9 | **τ0 = 10.8433, as of 2023-10-01**, from 8 quarters: 2021-Q2–Q4, 2022-Q2–Q4, 2023-Q1–Q2 |

**Why τ0 and not 14.345.** E9's first test origin is 2023-10-01, so τ0 uses only information available before any test quarter. The approved prospective 14.345 is the median of labels through 2025-Q4. On 2023–2025 test quarters it would leak test-period information, so it is **not** used for evaluation.

**Version and implementation:**

- implementation: `risk_score_v2.py` (S1);
- version: the file whose SHA-256 is recorded in the run manifest (`code_sha256`), equal to the hash in the served-artifact metadata (`5b6c83d6…`);
- functions used: `compute_stress`, `reference_threshold`, `classify`, `final_classification`.

## 3. The three components are kept separate

| Component | What it is | What it is not |
|---|---|---|
| **Scoring formula (S1)** | Computes the historical stress indicator from published SWS and CPI | Not a forecast, and not an observed food-insecurity measurement |
| **Forecasting model** | Predicts the target quarter's S1 stress, or the probability that it exceeds τ0, from information published before the origin | Not evidence that the formula is valid |
| **Classification rule** | Probability ≥ 0.50 → HIGH; < 0.50 → LOW. For stress outputs: predicted stress > τ0 → HIGH. INSUFFICIENT_DATA when a required input is missing or stale. | Not tuned. 0.50 and τ0 are fixed. |

**A high S1 value is not evidence that a model is accurate,** and the S1 indicator is **constructed, not independently observed food insecurity**.

## 4. Target-generation steps (E9 run `20261012T140816Z`)

1. **SWS rounds:** from the code registry (`devprotocol_rule_l.sws_rounds()`), keeping rounds with quarter ≤ 2025-Q4. Definition-A rounds feed the label; the supplementary 2025 rounds are inputs only.
2. **Provincial food CPI YoY:** from `psa_indicators.parquet`, through the guard: hash-verified, filtered to quarter ≤ 2025-Q4 during the scan, pre-2021 rows dropped.
3. **Stress:** `compute_stress(SWS, CPI)` gives stress and its components (`sws_hunger_pct`, `regional_mean`, `deviation`). Only complete quarters are kept.
4. **Cross-check:** against `labels.parquet` `stress_score`. **80 of 80 rows match, maximum absolute difference 0.000033** (tolerance 0.001).
5. **Labelled quarters (16):** 2021-Q2–Q4, 2022-Q2–Q4, 2023-Q1–Q4, 2024-Q1–Q4, 2025-Q1, 2025-Q4.
   - 2021-Q1 and 2022-Q1 have no SWS round in the registry.
   - 2025-Q2/Q3 have only supplementary rounds (inputs only, not definition A).

   Checked 2026-10-12 from registry quarter keys only.
6. **Label publication dates:** Rule L1 (`label_published`). Each label is available once its SWS round **and** its provincial CPI final month have been published. The provincial CPI date is a **proxy** (national release + 14 days) except for 2024-Q4.
7. **Event:** HIGH if stress > τ0.

**Outputs:**

- `runs/20261012T140816Z/s1_targets_2021_2025.csv`: 80 rows; the S1 components are included.

**Event distribution at τ0 (all labels, 2021–2025):**

| Year | HIGH / rows |
|---|---|
| 2021 | 8/15 |
| 2022 | 8/15 |
| 2023 | 11/20 |
| 2024 | **19/20** |
| 2025 | **10/10** |

## 5. What was not done

- The formula was not changed.
- No class was rebalanced.
- τ was not tuned.
- No 2026 label was built.
- Production `label_cpi` and the served classifications were not touched.
