# aiPHeed Risk Scoring: Diagnosis, Candidate Formulas, Recommendation

| Item | Value |
|---|---|
| Date | 2026-10-11 |
| Status | **Candidate for review. Not promoted.** |
| Scope | Isolated work in `aipheed-backend-aligned/`. Production `backend/`, the dashboard, the scheduler, the scheduled tasks and the thesis are unchanged. Nothing was committed or deployed. **No protected 2026 data was inspected or aggregated in this task;** every computation filtered to 2021-Q1 to 2025-Q4 before calculating anything. |
| Protocol | `E5_SCORING_PROTOCOL.md`, fixed before E5 code |
| Run | `runs/20261011T122112Z_E5/` |

## Summary

1. **The thesis `backend/` score overestimates risk.**
   - Its label (`label_cpi`) treats a **rising food price index** as high risk whenever the index is above its trailing average. That is HIGH in **100% of 2024 rows** and 90% of 2025 rows, while food inflation **fell** to 3.6% and 2.7%.
   - **This is a genuine artifact.**
2. **The aligned Equation 3 score does not inflate HIGH beyond its inputs.**
   - It is HIGH in 50% of 2021–2025 rows. HIGH is concentrated in 2024–2025 (90%) because Balance-Luzon hunger was 14.3–25.3%, the highest in the window.
   - **The available evidence does not support a hunger-anchored formula that classifies 2024–2025 as mostly LOW.** Doing so would contradict the hunger data.
3. **Recommended candidate S1:** keep Equation 3's formula and approved weights, but use a frozen point-in-time threshold and treat missing inputs as missing. It removes three defects. **It does not, and should not, make 2024–2025 mostly LOW.**
4. **No reliable absolute risk threshold of official standing can be identified from the available data.** The S1 threshold is empirical (the thesis's median rule).

## 1. Original scoring paths

### Path A: aligned backend (thesis primary target, Equation 3)

| Element | Exact definition | Code |
|---|---|---|
| Score | stress(p, t) = **1**·SWS_t + **2**·(food_cpi_yoy(p, t) − regional_mean_t) | `app/ml/features/label_generator.py` l.131; `ALPHA = 2` |
| SWS_t | Balance-Luzon involuntary-hunger prevalence, % of respondents (household heads to 2024; registered voters / adults in 2025). Mean of the quarter's rounds. Range 2021–2025: 8.7–25.3. | l.142–147 |
| food_cpi_yoy | PSA provincial food CPI, year-on-year %. The index base is 2018 = 100. | l.150–156 |
| regional_mean_t | Mean of the five provinces' food_cpi_yoy in quarter t | l.158–163 |
| Normalization | **None.** Raw hunger % and 2 × CPI percentage points are added. sd of the regional term (rows) = 5.0; sd of the provincial term 2·d = 3.7. | — |
| Missing values | **Filled with 0.0** (l.156, l.183, l.188): latent; not triggered in 2021–2025 | — |
| HIGH/LOW cutoff | HIGH if stress > the median of all labelled rows: **14.345** (80 rows, 2021–2025); 14.6 in the stored 95-row `labels.parquet` | l.222–226 |
| Dashboard | LightGBM P(HIGH) ≥ **0.50** → "high"; ≥ 0.60 → alert | `app/services/reference.py` l.106–117 |

### Path B: thesis-documented `backend/` (served)

| Element | Exact definition | Code |
|---|---|---|
| Label | `label_cpi` = 1 if the **food CPI index level** > its rolling **24-quarter mean + 1·sd** (`min_periods=4`, current quarter included) in the current **and** previous quarter | `label_generator._build_cpi_labels`; `backend/scripts/build_thesis_panel.py` l.60–75 |
| Inputs | PSA provincial food CPI **index** (2018 = 100). No hunger input. | — |
| Normalization | None (a level compared with its own trailing distribution) | — |
| Model | 3-way blend (LightGBM 0.4 + logistic regression 0.4 + weak-trigger logistic regression 0.2) | `backend/models/thesis_food_insecurity_model.joblib` |
| Cutoff | Blend probability ≥ **0.712** (stored bundle threshold) → "HIGH" | `app/ml/inference/thesis_predictor.py` l.116, l.171 |

## 2. Diagnosis (2021–2025 only)

### HIGH share by year

| Year | A: label (14.345) | A: dashboard, in-sample | B: `label_cpi` | B: dashboard, in-sample | Mean provincial food inflation | Balance-Luzon hunger (range) |
|---|---:|---:|---:|---:|---:|---|
| 2021 | 0.27 | 0.13 | 0.25 | 0.00 | 6.0% | 9.2–15.4 |
| 2022 | 0.27 | 0.27 | 0.65 | 0.25 | 4.7% | 9.6–11.8 |
| 2023 | 0.25 | 0.40 | 0.90 | 0.85 | 7.3% | 8.7–14.3 |
| 2024 | 0.90 | 0.90 | **1.00** | **1.00** | 3.6% | 15.3–25.3 |
| 2025 | 0.90 | 0.90 | 0.90 | 0.85 | 2.7% | 16.7–24.0 |
| All years | 0.50 | 0.51 | 0.74 | 0.59 | — | — |

**By province (path A label):** Cavite 0.31, Laguna 0.50, Quezon 0.38, Rizal 0.81, Batangas 0.50.

**By province (path B label):** Cavite 0.80, Laguna 0.75, Quezon 0.60, Rizal 0.70, Batangas 0.85.

Per-quarter counts are in `runs/20261011T122112Z_E5/metrics.json` and in E4.

### Path B: rising price index read as risk (confirmed)

| Evidence | Value |
|---|---|
| Quarter-to-quarter steps in which the food CPI index rose | 77% |
| Of 74 HIGH rows, rows with food inflation **decelerating** | **34** |
| Of 74 HIGH rows, rows with food inflation **below 2%** | **12** |
| Of 74 HIGH rows, rows with food inflation **≤ 0%** | **2** |
| Correlation of `label_cpi` with the actual food inflation rate | 0.25 |
| HIGH share in 2024–2025, when inflation was the lowest of the window | 90–100% |

**Conclusion:** the label measures "prices are higher than they used to be", which is almost always true for a price index. It does not measure price stress, and it contains no hunger information.

### Path A: answers to the four questions

| Question | Answer |
|---|---|
| Does the regional hunger component dominate? | **Yes.** All five provinces share it, and it carries 65% of score variance. |
| Is the provincial deviation scaled appropriately? | The ×2 weight has **no derivation** in the thesis ("amplifying"). No evidence was found to set a different weight. |
| What does the score measure? | **Absolute regional hunger plus relative provincial food-price pressure.** Not change over time. |
| Do normalization or the threshold cause excess HIGH? | **The threshold choice changes counts; the data cause the 2024–2025 concentration.** The full-sample median is leaky, and the fold median drifts. Under every leakage-free fixed threshold, 2024–2025 is mostly HIGH because hunger was high. |

## 3. Candidates (rationale fixed before evaluation in `E5_SCORING_PROTOCOL.md`)

**Reference parameters:** all come from data **published before 2023-10-01** and are frozen. No test-quarter data, no tuning, no 2026 data.

| ID | Formula | Weights and normalization | Cutoff and its source | All 2021–2025 rows (H / L) | Test rows (H / L) |
|---|---|---|---|---|---|
| S0 (current A) | 1·SWS + 2·d | Raw units | Median of all 80 rows = 14.345 (**leaky** on 2021–2025) | 40 / 40 | 30 / 5 |
| **S1 (recommended)** | 1·SWS + 2·d, **NaN-safe** | Raw units (approved) | Median of labels published before the as-of date, **frozen**: 10.843 at 2023-10-01; **14.345** for prospective use | 56 / 24 at τ0; 40 / 40 at 14.345 | 33 / 2 at τ0 |
| S2 | z = (SWS − 10.944) / 1.959 + d / 1.734 | Standardized; **equal weights** (composite-indicator default) | Median z of the reference rows = −0.246, frozen | 58 / 22 | **35 / 0** |
| P0 (current B) | Index level > trailing mean + 1σ, 2 quarters | — | — | 74 / 26 (`backend/` panel) | — |
| P1 | Food **inflation rate** > r_ref in quarter t and t−1 | Raw % | r_ref = median food YoY over the reference rows = **6.35%**, frozen | 19 / 76 | 3 / 32 |
| C1 | Year-over-year change in stress > 0 | — | 0 (natural) | Not evaluated: only 3 eligible folds; measures worsening | — |

### Evaluation

Evaluated once per candidate on the 7 reused test quarters (35 rows; n_eff ≈ 7). The model is the E3 LightGBM configuration (`num_leaves=4`, `min_child_samples=5`, 100 trees, learning rate 0.05, seed 42, `scale_pos_weight` from training labels). S1 and S0 come from E4 (not re-run). S2 and P1 come from E5.

**False HIGH = FP; missed HIGH = FN.**

| Candidate | Predictor | Balanced acc. | HIGH precision | HIGH recall | LOW recall | ROC-AUC | [[TN,FP],[FN,TP]] |
|---|---|---:|---:|---:|---:|---:|---|
| S1 (E4 D-C) | LightGBM | 0.985 | 1.000 | 0.970 | 1.00 (2/2) | 0.977 | [[2,0],[1,32]] |
| | Carry-forward | 0.939 | 1.000 | 0.879 | 1.00 | 1.000 | [[2,0],[4,29]] |
| | Equation 3 rule | 0.939 | 1.000 | 0.879 | 1.00 | 1.000 | [[2,0],[4,29]] |
| | Always-HIGH | 0.500 | 0.943 | 1.000 | 0.00 | undefined | [[0,2],[0,33]] |
| S0 (E4 D-A, leaky) | LightGBM | 0.633 | 0.909 | 0.667 | 0.60 | 0.667 | [[3,2],[10,20]] |
| | Carry-forward | 0.650 | 0.913 | 0.700 | 0.60 | 0.713 | [[3,2],[9,21]] |
| S2 | LightGBM | **undefined** (no LOW row) | 1.000 | 0.914 | undefined | undefined | [[0,0],[3,32]] |
| | Carry-forward | undefined | 1.000 | 0.886 | undefined | undefined | [[0,0],[4,31]] |
| | Always-HIGH | undefined | 1.000 | 1.000 | undefined | undefined | [[0,0],[0,35]] |
| P1 | LightGBM | 0.557 | 0.125 | 0.333 | 0.781 | 0.531 | [[25,7],[2,1]] |
| | Carry-forward | 0.573 | 0.143 | 0.333 | 0.813 | not computed (binary) | [[26,6],[2,1]] |
| | Origin rule (latest food YoY > 6.35%) | **0.740** | 0.250 | 0.667 | 0.813 | 0.563 | [[26,6],[1,2]] |
| | Always-LOW | 0.500 | — | 0.000 | 1.000 | undefined | [[32,0],[3,0]] |

**Verdicts, LightGBM vs the better baseline:**

| Candidate | Verdict |
|---|---|
| S1 | Non-inferior (+0.045; CI 0.015 to 0.088) |
| S0 | Non-inferior (−0.017) |
| S2 | **Not evaluable**: one class |
| P1 | **No demonstrated improvement** (−0.182 against the origin rule; CI −0.529 to 0.000) |

**No candidate's test set has enough minority-class rows for a reliable result:**

| Candidate | Minority-class rows | Quarters containing them |
|---|---:|---:|
| S1 | 2 LOW | 2 |
| S2 | 0 LOW | 0 |
| P1 | 3 HIGH | 3 |
| S0 | 5 LOW | 4 |

## 4. Recommendation: candidate S1

### Formula and weights

**stress(p, t) = SWS_t + 2 × (food_cpi_yoy(p, t) − regional_mean_t)**

- Weights: 1 (regional hunger) and 2 (provincial food-price deviation). These are the **approved weights, unchanged**.
- Normalization: none. Units are hunger percentage points; the provincial term is scaled by α = 2.
- **Missing inputs:**
  - Any missing SWS or provincial CPI value gives **NaN**, labelled "insufficient data".
  - The regional mean exists only when all five provinces are present.
  - **There is no zero-fill.**

### Cutoff

**HIGH if stress > τ_ref; LOW if stress ≤ τ_ref.**

- **τ_ref** = the median stress of all complete quarters whose labels were **published before a stated as-of date** (Rule L publication dates; an unknown date means excluded), with at least 8 quarters. It is then **frozen** until a scheduled, documented review.

| Use | τ_ref |
|---|---|
| Retrospective evaluation from 2023-Q4 | 10.843 |
| **Prospective use from 2026-Q3** (all 16 labelled quarters of 2021–2025 published) | **14.345**, the approved value |

**Dashboard display:** model P(stress > τ_ref) ≥ 0.50 → HIGH, the existing convention.

### Why S1, by the pre-fixed criteria in `E5_SCORING_PROTOCOL.md` §4

| Criterion | S1 | S2 | P1 | S0 | P0 |
|---|---|---|---|---|---|
| 1. Hunger-anchored | ✔ | ✔ | ✘ (price only) | ✔ | ✘ |
| 2. Fixed meaning and point-in-time threshold | ✔ | ✔ | ✔ | ✘ (leaky) | ✘ |
| 3. No mechanical artifact | ✔ | ✔ | ✔ | ✘ (zero-fill) | ✘ (index trend) |
| 4. Weights justified a priori | ✔ (approved) | Convention only | n/a | ✔ | n/a |
| 5. Classification moves with its source | ✔ | ✔ | ✔ | ✔ | ✘ |

**S1 and S2 both meet 1–5.** The tie-break keeps the approved weights, because equal weighting has no stronger documented justification than α = 2. S2 also **increases** HIGH (58/80; 100% in 2024–2025).

**Model results were not used to rank candidates.**

### What S1 does not do

S1 does not reduce the 2024–2025 HIGH share. Against the 2021–2023 reference that share is 100%; against 14.345 it is 90%. **The hunger data show 2024–2025 as the highest-stress period in the window.** A formula that called it LOW would be manufacturing a result.

**If DA needs a price-stress signal, use P1, not the current `label_cpi`.** P1 correctly shows food-price stress concentrated in 2023 (50% HIGH) and easing in 2024–2025 (10% and 5%). But it is not a food-insecurity measure, and LightGBM did not predict it better than a simple rule. **Adviser decision.**

## 5. Implementation (isolated)

**`app/ml/features/risk_score_v2.py` (new; not imported by any label, training or serving code):**

| Function | Purpose |
|---|---|
| `compute_stress()` | NaN-safe Equation 3 |
| `reference_threshold()` | Frozen point-in-time median; publication-date gate; minimum 8 quarters; unknown dates excluded |
| `classify()` | Strict `>` boundary; NaN → `None` |
| `classify_probability()` | ≥ 0.50; range-checked |

**`tests/unit/test_risk_score_v2.py` (12 tests, all passing):**

- the hand-calculated score;
- two SWS rounds averaged;
- **agreement with `label_generator` on all 80 approved rows** (max difference < 0.001; formula preserved);
- a missing provincial CPI value gives NaN, not zero;
- missing SWS gives NaN;
- the boundary (= threshold → LOW; > → HIGH);
- both HIGH and LOW outputs;
- probability boundaries and range;
- point-in-time reference (later data cannot move it);
- unknown publication dates excluded, and the minimum enforced;
- reproduces τ0 = 10.843 (as of 2023-10-01, 8 quarters) and **14.345** (as of 2026-07-01, 16 quarters);
- **isolation:** not imported by `app/services`, `app/api`, `app/main.py`, `label_generator.py` or `app/ml/training`.

**E5 experiment files:**

| File | Purpose |
|---|---|
| `experiments/2026-10-11_devprotocol/E5_SCORING_PROTOCOL.md` | Protocol |
| `runner/run_e5_scoring.py` | Runner |
| `tests/unit/test_e5_scoring.py` | 11 tests |
| `runs/20261011T122112Z_E5/` | 18 files: configuration, predictions, metrics, manifest |
| `SCORING_FORMULA_REPORT.md` | This report |

**Test results:**

- Full suite: **253 passed**.
- Two test-only bugs were fixed before acceptance: a date string in a synthetic fixture, and an as-of date that gave 7 quarters (the module correctly refused it). **The module itself was not changed to pass the tests.**

**Files changed outside the new files:** none. `label_generator.py`, the services, the dashboard, the models and data are unchanged.

## 6. Integrity

| Check | Result |
|---|---|
| E5 hash guard | 385 protected files unchanged, including the E1–E4 runs |
| Label access | 14 label reveals, all after that fold's predictions were written |
| Production `backend/` | 54 files re-hashed; unchanged. No archive, candidate or pipeline-run folders. Its git status is identical to the start of the session. |
| `backend/` in-sample dashboard check | The served predictor's panel was filtered to ≤ 2025-Q4 **before** scoring. No 2026 row was scored or aggregated. |
| Disclosures | E5 is the **fifth analysis** on these reused quarters. Earlier designs and results informed the candidate set. |

## 7. Limitations

- **Small effective sample:** about 7 test quarters, with 0–5 minority-class rows depending on the definition. **No definition's predictive comparison is reliable.**
- **Shared regional SWS:** provinces share it, so the hunger-anchored score cannot separate provinces when regional hunger is far from the threshold. Province differentiation comes only from relative food prices (E2/E4: not predictable beyond carry-forward).
- **Respondent populations:** SWS respondents changed in 2025 (registered voters, then adults); see D3.
- **Proxy publication dates:** provincial CPI publication dates are proxies (WD1).
- **No official cutoff:** the S1 threshold is empirical. **No DA or government risk cutoff exists in the evidence.**
- **Retrospective numbers depend on the reference:** they reflect τ0 = 10.843 (the 2021–2023 reference). Prospectively, the approved 14.345 applies.

## 8. Decisions before any promotion (stop for review)

| # | Decision | Owner |
|---|---|---|
| 1 | Adopt S1 (approved formula, NaN-safe, frozen point-in-time threshold; 14.345 prospectively) and the review schedule for the reference | Adviser |
| 2 | Path B: retire `label_cpi` as a risk label. If a price signal is wanted, consider P1 as a separate, clearly named indicator. | Adviser and researcher |
| 3 | Whether the served `backend/` model should be retrained on S1 labels. This needs separate authorization and a fresh protected evaluation; **not done.** | Researcher |
| 4 | Wiring `risk_score_v2` into label building or the aligned dashboard. **Not done.** | Researcher, after review |
| 5 | Handling of the 2026 CPI rows already present in production `backend/` data (reported in `RISK_CLASSIFICATION_REPORT.md`) | Researcher |
