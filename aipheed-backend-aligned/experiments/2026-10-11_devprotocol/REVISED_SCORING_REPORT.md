# Revised Risk Scoring for DA CALABARZON: Root Cause, Redesign, Validation

| Item | Value |
|---|---|
| Date | 2026-10-12 |
| Scope | Isolated development backend `aipheed-backend-aligned/` only |
| Protocol | `E6_REVISED_SCORING_PROTOCOL.md`, frozen before any revised forecast was generated |
| Final evaluation | `runs/20261012T083041Z_E6/`, run once |
| Classification rule | Fixed throughout: **HIGH if final probability ≥ 0.50; LOW if < 0.50; INSUFFICIENT_DATA if required data are missing or stale** |

---

## A. Root cause

### Aligned backend (Equation 3 target; probability ≥ 0.50 → HIGH)

| # | Finding | Code | Evidence (2021–2025 only) |
|---|---|---|---|
| A1 | **The HIGH concentration comes from the target, not from inflated probabilities.** Equation 3 adds one regional SWS value (Balance Luzon, shared by all 5 provinces) to 2 × the provincial food-inflation gap, then thresholds at a full-sample median. | `app/ml/features/label_generator.py` l.131, l.222–226 | The regional term carries **65%** of stress variance. **81%** of labels equal the regional-only call. HIGH share by year: 2021 0.27, 2022 0.27, 2023 0.25, **2024 0.90, 2025 0.90**, tracking Balance-Luzon hunger (8.7–15.4% before 2023-Q4; 15.3–25.3% in 2024–2025). |
| A2 | **The coefficient 2 is not the cause.** | — | At 14.345, HIGH rows in 2024–2025 (of 30): α = 0 → **30**; α = 1 → 29; α = 2 → 27; α = 2.74 → 27; α = 4 → 24. Even with no provincial term, every 2024–2025 row is HIGH. |
| A3 | **Dashboard probabilities are in-sample fits.** The served model was fitted on every quarter it displays: Optuna-tuned, learning rate 0.297, 499 trees, `class_weight="balanced"`, lead time 0 (same-quarter inputs), and no SWS input although the label is 65% SWS. | `models/lgbm_best.pkl`; `app/ml/inference/predictor.py` | Median in-sample probability: 2021 0.18; 2024 **0.85** (18/20 HIGH); 2025 **0.85** (17/20 HIGH) |
| A4 | **Missing data are made to look measured.** Gaps are forward-filled indefinitely, then zero-filled. | `app/ml/features/feature_matrix.py` l.532, l.619 | FSSI forward-filled in **77/120** province-quarters plus 10 zero-filled. `FSSI_lag1`/`FSSI_lag2` zero-filled 15/20. `cpi_dev` zero-filled 10. No INSUFFICIENT state exists. |
| A5 | **The label threshold includes out-of-window rows.** | `labels.parquet` | Threshold 14.6 is the median of 95 rows including 2020. The approved 2021–2025 median is 14.345. |

**There is no calibration step and no score blending on this path.**

**The 0.50 cutoff is applied consistently:**

- `predictor.py` `RISK_CUTOFF`;
- `app/services/reference.py` `RISK_DISPLAY_CUTOFF`;
- the frontend reads `riskLevel` from the API and does not recompute it (`frontend/src/lib/adapters.ts`).

**Direct test of the "inflated probability" hypothesis**, on the same 35 test rows (E6):

| Model | Classification | Median probability |
|---|---|---|
| Old served model (in-sample) | 32 HIGH / 3 LOW | 0.85 |
| Revised time-valid model (out-of-sample) | 32 HIGH / 3 LOW | 0.99 |

- Against the approved 14.345, the revised out-of-sample probabilities were **too low**, not too high: rows given a mean probability of 0.15 were 77% HIGH.

### Thesis `backend/` path (served; reused from E5)

| # | Finding | Code | Evidence |
|---|---|---|---|
| A6 | **`label_cpi` treats a rising food price index as risk:** index > trailing 24-quarter mean + 1σ, in 2 consecutive quarters. | `label_generator._build_cpi_labels`; `backend/scripts/build_thesis_panel.py` | HIGH: 2024 **100%**, 2025 90%, while mean food inflation fell to 3.6% and 2.7%. Of 74 HIGH rows, 34 had decelerating inflation, 12 had inflation < 2%, and 2 had inflation ≤ 0. **A genuine inflation artifact.** |
| A7 | **Its classification uses a blend-probability cutoff of 0.712, not 0.50.** | `backend/app/ml/inference/thesis_predictor.py` l.116, l.171 | Conflicts with the mandated 0.50 rule. **Production was not changed (out of scope).** |

## B. Formula alternatives

All candidates were fixed before their evaluation. E4/E5 results are reused; E6 evaluated only the final pipeline.

| Candidate | What it measures | Result | Decision |
|---|---|---|---|
| Original Eq. 3 (α = 2, full-sample median) | Regional hunger + relative provincial food-price gap | Leaky threshold; zero-fill; regional dominance | **Keep the formula; fix the mechanics** (C) |
| α changed (1, 2.74, 4) | Same, with more or less provincial weight | 2024–2025 HIGH: 29 / 27 / 24 of 30. No outcome exists to estimate α. Equal-variance α is 1.13 or 2.74 depending on the reference period. | Not justified; α = 2 kept as a **documented, unvalidated** parameter |
| S2: standardized, equal weights | Regional anomaly z + provincial z | 35/35 test rows HIGH; balanced accuracy undefined | Rejected (no more defensible; more HIGH) |
| P1: food inflation rate > reference | Current provincial price pressure only | Fixes the index artifact. But it is not hunger, slowing inflation reads as LOW, and LightGBM balanced accuracy was 0.557 vs a rule's 0.740. | Not a food-insecurity target. A possible separate price indicator. |
| D-D: two conditions (stress > reference **and** above-average price pressure) | Provincial priority within an elevated region | Separates provinces, but LightGBM balanced accuracy 0.535, below the baselines | Rejected as the forecast target |
| Year-over-year change in stress | Worsening | Only 3 eligible folds | Rejected |
| **Separate dimensions** (regional hunger; provincial price evidence) | Each meaning kept intact | No weights invented | **Adopted for the supporting indicators** (not probabilities) |

**Why the original formula is kept as the forecast target:**

- None of the alternatives was more defensible.
- None was forecast better.
- No data exist to estimate weights.
- The coefficient does not drive the HIGH concentration (A2).

The corrections address what was demonstrably wrong: leakage, zero-fill, in-sample display, stale inputs, the missing regional input, and conflating regional and provincial evidence.

## C. Final method (implemented in isolation)

### 1. Target event: "stress exceeds the frozen reference"

**stress(p, t) = SWS_t + 2 × (food_cpi_yoy(p, t) − mean over the five provinces of food_cpi_yoy(t))**

| Variable | Meaning and unit |
|---|---|
| SWS_t | Balance-Luzon involuntary hunger, % of respondents (rounds in a quarter averaged). **Regional; shared by all five provinces.** |
| food_cpi_yoy | PSA provincial food CPI, year-on-year % |
| 2 | Documented, unvalidated coefficient |

**Rules:**

- **Missing data:** any missing input gives NaN, never 0. The regional mean exists only when all five provinces are present.
- **Negative values:** valid. Deviations below the mean lower stress; the deviations sum to zero within a quarter.
- **Reference τ:** the median stress of complete quarters whose labels were published before the as-of date (Rule L), with at least 8 quarters, then frozen.

| Use | τ | Basis |
|---|---|---|
| Served historical forecasts | **10.843** | As of 2023-10-01 |
| Prospective use | **14.345** | As of 2026-07-01 |

Both are empirical (the thesis median rule). **Neither is an official DA cutoff.**

### 2. Forecast (primary): LightGBM probability of the event

| Item | Specification |
|---|---|
| Inputs | Last published stress, latest published SWS, SWS change, latest provincial CPI deviation, food inflation level, rice-price acceleration, unemployment. All as published before the forecast origin (development frame, Rule L). |
| Model | `num_leaves=4`, `min_child_samples=5`, 100 trees, `learning_rate=0.05`, seed 42 |
| Monotone constraints | +1 on last published stress and SWS; 0 on the rest |
| Class weighting | **None** |
| Training labels | Only labels published before the origin |
| Calibration | Platt scaling only with ≥ 8 inner out-of-fold quarters and ≥ 10 rows per class. **Never met, so probabilities are uncalibrated.** |
| Final probability | The LightGBM probability. **Nothing is blended in.** |

**INSUFFICIENT_DATA applies when:**

- a required input is missing (last published stress, SWS, `cpi_rel` or food inflation); or
- the SWS input is more than 3 quarters old (it is normally 1–2); or
- there are fewer than 8 eligible training quarters; or
- the training labels contain one class only.

### 3. Supporting indicators (shown separately; not probabilities)

- **Regional hunger signal:** value, round, publication date, age, and the scope statement "Balance Luzon … NOT a province-specific measurement".
- **Provincial food-price evidence:** inflation rate, relative pressure (pp vs the five-province mean), inflation change (pp), and the index level, labelled as a level rather than current pressure.
- **Supporting stress score:** the last published stress, split into its regional and provincial components.

## D. Before and after (2021–2025; permitted data only)

### Labels (80 rows)

| Definition | HIGH |
|---|---:|
| Old `label_stress` (14.6, includes 2020 rows) | 39 |
| S1 at retrospective τ0 = 10.843 | 56 |
| S1 at approved 14.345 | 40 |

### Probabilities

| | Old served (in-sample, 100 rows) | Revised (time-valid) |
|---|---|---|
| Rows with a probability | 100 | 45 (2023-Q4 to 2025-Q4) |
| Rows marked INSUFFICIENT_DATA | — | 50: 2021-Q2 to 2023-Q3 (too little training history or no published stress) |
| Range | 0.002–0.979 | 0.019–0.998 |
| Median | 0.519 | 0.988 |
| Share ≥ 0.9 | 13% | 87% |
| HIGH / LOW / INSUFFICIENT | 51 / 49 / – | 42 / 3 / 50 |

**By year:**

| Year | Old served (HIGH of 20) | Revised (H / L / I) |
|---|---:|---|
| 2021 | 3 | 0 / 0 / 15 |
| 2022 | 5 | 0 / 0 / 20 |
| 2023 | 8 | 4 / 1 / 15 |
| 2024 | 18 | 18 / 2 / 0 |
| 2025 | 17 | 20 / 0 / 0 |

**On the 35 test rows,** both systems classify 32 HIGH and 3 LOW.

**The revision does not reduce HIGH counts, and is not presented as doing so.** It replaces in-sample fits and imputed inputs with time-valid forecasts, and shows INSUFFICIENT_DATA where the evidence is inadequate.

## E. Validation (E6; 7 reused test quarters; 35 rows; n_eff ≈ 7)

### Served reference τ0 = 10.843 (leakage-free)

Reference labels: 33 HIGH / 2 LOW. No INSUFFICIENT_DATA predictions on the test rows.

| Predictor | Acc. | Balanced acc. | HIGH precision | HIGH recall | LOW recall | False HIGH | False LOW | ROC-AUC | PR-AUC | Brier | Log loss |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **Revised LightGBM** | 0.971 | **0.985** | 1.00 | 0.970 | 1.00 (2/2) | 0 | 1 | 0.992 | 0.999 | **0.035** | 0.139 |
| Carry-forward | 0.886 | 0.939 | 1.00 | 0.879 | 1.00 | 0 | 4 | 1.000 | 1.000 | — | — |
| Equation 3 rule | 0.886 | 0.939 | 1.00 | 0.879 | 1.00 | 0 | 4 | 1.000 | 1.000 | — | — |
| Regional-only rule | 0.857 | 0.689 | 0.967 | 0.879 | 0.50 | 1 | 4 | 0.879 | 0.989 | — | — |
| Always-HIGH | 0.943 | 0.500 | 0.943 | 1.00 | 0.00 | 2 | 0 | — | — | — | — |
| E3, class-weighted (reference, E4 D-C) | 0.971 | 0.985 | — | — | — | — | — | 0.977 | — | 0.036 | — |

**Per quarter (revised: correct / predicted HIGH / reference HIGH):**

| Quarter | Revised |
|---|---|
| 2023-Q4 | 5/4/4 |
| 2024-Q1 | 4/3/4 |
| 2024-Q2 | 5/5/5 |
| 2024-Q3 | 5/5/5 |
| 2024-Q4 | 5/5/5 |
| 2025-Q1 | 5/5/5 |
| 2025-Q4 | 5/5/5 |

**Uncertainty and calibration:**

| Measure | Value |
|---|---|
| Balanced-accuracy gain vs carry-forward | +0.045 (95% CI +0.015 to +0.088). 950 of 10,000 resamples skipped for lacking a LOW row. |
| Balanced-accuracy gain vs regional-only rule | +0.296 (CI +0.044 to +0.500) |
| Reliability | 29 rows at mean p 0.988 → 100% HIGH. 3 rows at mean p 0.03 → 1 of 3 HIGH. |

**Verdict: non-inferiority, not improvement** (the gain is below 0.10).

### Approved 14.345 (evaluation only; leakage-affected)

Reference labels: 30 HIGH / 5 LOW.

| Predictor | Correct | Balanced acc. | HIGH recall | LOW recall | False HIGH | False LOW | ROC-AUC | PR-AUC | Brier | Log loss |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Revised LightGBM | 23 | 0.633 | 0.667 | 0.60 | 2 | 10 | 0.640 | 0.885 | **0.276** | 0.999 |
| Carry-forward | 24 | 0.650 | 0.700 | 0.60 | 2 | 9 | 0.713 | 0.927 | — | — |
| Equation 3 rule | 22 | 0.617 | 0.633 | 0.60 | 2 | 11 | 0.780 | 0.959 | — | — |
| Regional-only rule | 21 | 0.600 | 0.600 | 0.60 | 2 | 12 | 0.700 | 0.928 | — | — |
| E3, class-weighted (reference, E4 D-A) | 23 | 0.633 | — | — | — | — | 0.667 | — | **0.245** | — |

**Reliability:** probabilities are too low in the low bin (13 rows at mean p 0.15 → 77% HIGH). The model under-predicts the 2024–2025 rise relative to its earlier training labels.

**Verdict: non-inferiority. Calibration is worse than the class-weighted reference.**

### What the evaluation shows

| Claim | Status |
|---|---|
| Demonstrated predictive improvement | **No** |
| Non-inferiority to carry-forward and the Equation 3 rule | Yes, under both references |
| Better calibration | **Not established.** Brier 0.035 vs 0.036 at τ0 (negligible); 0.276 vs 0.245 at 14.345 (worse). |
| Better class balance | Not claimed; HIGH counts are unchanged |

**Limitations:**

- 7 reused quarters (the sixth analysis on them), with about 7 effective units.
- Only 2 LOW labels at τ0 and 5 at 14.345.
- One shared regional SWS value per quarter, repeated across 5 provinces.
- Proxy CPI publication dates.
- No province-level outcome.

## F. DA usefulness

**Revised served forecasts.** Each cell: probability, class, and the province's food inflation / relative pressure in the CPI reference quarter.

| Quarter (regional SWS) | Cavite | Laguna | Quezon | Rizal | Batangas |
|---|---|---|---|---|---|
| 2023-Q4 (11.3) | 0.99 H (8.1% / +1.1) | 0.82 H (6.1 / −0.9) | **0.02 L** (3.8 / −3.2) | 0.98 H | 0.96 H |
| 2024-Q1 (10.3) | 0.98 H | **0.03 L** (6.2 / −1.4) | **0.03 L** (4.5 / −3.1) | 0.99 H | 0.98 H |
| 2024-Q2 (14.3) | 0.99 H | 1.00 H | 0.73 H (1.4 / −2.4) | 0.99 H | 0.99 H |
| 2024-Q3 (15.3) | 0.98 H | 1.00 H | 0.59 H (−0.2 / −2.3) | 1.00 H | 1.00 H |
| 2024-Q4 to 2025-Q4 (15.3–24.0) | All HIGH, p 0.91–1.00 | | | | |

### What it can support

- **Provinces can differ when the evidence differs.** In 2023-Q4 and 2024-Q1 regional hunger was near the reference, and provinces with clearly below-average food-price pressure were LOW.
- **It does not treat slowing inflation as low risk.** Cavite's food inflation fell to 1.2% in 2025-Q1 yet stayed HIGH, because regional hunger was 18.1%. Quezon's probability fell (0.59) when its inflation turned negative, but did not flip.
- **When regional hunger is far above the reference (2024-Q2 onward), all provinces are HIGH.** The payload says this follows the shared regional signal, not five province-specific findings.
- **Every assessment shows:**
  - the probability, its class and the fixed rule;
  - the forecast origin and horizon;
  - the regional signal with its scope and date;
  - provincial price evidence with publication date and date type;
  - the supporting stress decomposition;
  - the top LightGBM factors;
  - missing-data warnings;
  - a rationale;
  - limitations.
- **2021-Q2 to 2023-Q3 are visibly INSUFFICIENT_DATA**, not LOW.

### What it cannot establish

- **That a specific province has a higher food-insecurity rate.** The only province-specific evidence is relative food prices, and no tested model forecasts the provincial ordering better than carry-forward (E2: Spearman ρ 0.20 vs 0.38; E4 D-D: balanced accuracy 0.535).
- **That probabilities are calibrated.** That needs more LOW cases and more quarters.
- **Anything about 2026.** No 2026 forecast is generated here; that belongs to the separately authorized protected evaluation.

## G. Implementation and tests

### Files created (aligned only)

| File | Purpose |
|---|---|
| `app/ml/training/revised_trainer.py` | Time-valid LightGBM forecaster, INSUFFICIENT_DATA rules, calibration check, price evidence |
| `scripts/build_revised_forecasts.py` | Builds forecast artifacts; refuses to overwrite |
| `data/revised/revised_forecasts_retrospective.parquet` (+ `_meta.json`) | Served artifact. SHA-256 `7135eb68…`; τ 10.843 |
| `app/services/assessment.py` | Province assessment payloads |
| `app/api/v1/assessments.py` | Three endpoints: `GET /api/v1/assessments/quarters`, `GET /api/v1/assessments?quarter=`, `GET /api/v1/assessments/methodology` |
| `tests/unit/test_revised_scoring.py` | 17 tests |
| `tests/integration/test_api_assessments.py` | 8 tests |
| `experiments/2026-10-11_devprotocol/E6_REVISED_SCORING_PROTOCOL.md` | Protocol |
| `runner/run_e6_final_evaluation.py` | One-time evaluation runner |
| `runs/20261012T083041Z_E6/` | Evaluation output, including the evaluation-only 14.345 artifact |
| `REVISED_SCORING_REPORT.md` | This report |

### Files modified (aligned only)

| File | Change |
|---|---|
| `app/ml/features/risk_score_v2.py` | Added `INSUFFICIENT_DATA`, `SWS_MAX_AGE_QUARTERS`, `decompose_stress`, `price_pressure_indicators`, `final_classification`. Existing functions unchanged. |
| `app/api/router.py` | Registers the assessments router |
| `app/services/reference.py` | `risk_level()` now delegates to the single shared rule. Same outputs for every probability. |
| `tests/unit/test_risk_score_v2.py` | The test "not imported by serving code" (written under yesterday's "keep unwired" instruction) became "not imported by the legacy label, trainer, feature-matrix or served-predictor code". **Wiring the revised path is authorized by this task; the protection of the legacy model path is kept.** |

**Not modified:** `label_generator.py`, `feature_matrix.py`, `trainer.py`, `predictor.py`, `models/lgbm_best.pkl` and all `data/processed/*` files (hash-checked by the E6 runner).

### Tests

| Run | Result |
|---|---|
| New scoring and forecaster tests | 29/29 passed |
| New API tests | 8/8 passed |
| **Full aligned suite** | **278 passed, 0 failed** (253 existing + 25 new) |
| E6 runner hash guard | 409 protected files unchanged |

**What the new tests cover:**

- 0.50 → HIGH; above → HIGH; below → LOW;
- missing or stale → INSUFFICIENT_DATA; no zero-fill;
- negative and positive deviations;
- level, rate and change distinguished;
- training and inference inputs identical;
- no future information (perturbing later labels leaves forecasts unchanged);
- calibration uses training quarters only;
- the regional input is identical across provinces;
- the model is LightGBM, unweighted, with the fixed configuration;
- the API and dashboard use the same rule;
- the artifact matches its hash and contains no 2026 forecast.

### Unresolved issues (for review; nothing changed after the evaluation)

1. **Calibration:** never supportable on the available sample. Against the approved 14.345, the unweighted model under-predicts HIGH (Brier 0.276 vs 0.245 with class weights). **This needs review before any prospective use.**
2. **Reference for display:** served history uses τ0 = 10.843, the leakage-free reference for 2023–2025. Prospective use would switch to 14.345. **Adviser decision.**
3. **Coefficient 2:** remains unvalidated. Province-level outcome data are needed to estimate it.
4. **Production `backend/`:** still serves `label_cpi` with a 0.712 cutoff, which conflicts with the 0.50 rule. **Production change is out of scope.**
5. **Production frontend:** not updated (prohibited). The new endpoint is not yet consumed by any UI.
6. **Code dependency:** the revised trainer depends on the experimental timing modules in `scripts/supplementary/`.
7. **Scheduled tasks:** the two daily Claude scheduled tasks are still active and ran again today; they were not paused (your decision). Production `backend/` data already contains 2026-Q3/Q4 CPI rows (reported 2026-10-11).

## H. Safety confirmation

| Item | Status |
|---|---|
| Production `backend/` | Not modified. 54 files re-hashed: unchanged. No archive, candidate or pipeline folders. |
| Production repositories | `backend/` and `frontend/` git status identical to the start of the session (20 entries) |
| Deployment, commits, pushes, merges | **None** |
| Protected 2026 outcomes | **Not inspected or used.** All labels and forecasts are limited to 2021–2025. Confirmed from code and artifact contents, without opening protected data. |
| Scheduled tasks | Not modified |
| Thesis files | Not modified |
