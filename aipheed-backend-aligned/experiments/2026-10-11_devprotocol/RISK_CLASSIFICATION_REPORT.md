# aiPHeed HIGH/LOW Risk Classification: Problem, Revised Definitions, Evidence

| Item | Value |
|---|---|
| Date | 2026-10-11 |
| Scope | Isolated experiment only. Production, the dashboard, the thesis and the scheduled tasks are untouched. |
| Protocol | `E4_RISK_DEFINITION_PROTOCOL.md`, fixed before any E4 code was written |
| Run | `runs/20261011T120714Z_E4/` |
| Status | Every definition below is **empirical**. **None is an official DA or government risk classification.** **Nothing has been promoted to production.** |

---

## 1. How HIGH/LOW is produced today

### Equation 3 stress score

**Formula:** stress(p, t) = SWS(t) + 2 × (food_cpi_yoy(p, t) − mean over the 5 provinces of food_cpi_yoy(t))

| Location in `aipheed-backend-aligned/app/ml/features/label_generator.py` | What it does |
|---|---|
| l.10–12, l.131 | Defines the formula; `ALPHA = 2` |
| l.142–147 | SWS(t): Balance-Luzon involuntary-hunger %, averaged when a quarter has two rounds |
| l.158–163 | Regional mean: the cross-province mean of food CPI YoY for the same quarter |

**Units:** hunger percentage points, plus 2 × percentage points of food-inflation deviation. The two terms are added as one "stress" number.

**Structure:** the deviation term sums to zero across the five provinces, so **the quarter mean of stress equals SWS exactly**:

- **65%** of stress variance is between quarters (regional);
- **35%** is within quarters (provincial food prices).

**Mathematical errors:** none found in the formula.

**Latent defect (not active in 2021–2025):** missing CPI is filled with **0.0** (l.156, l.183, l.188). A missing province would be recorded as 0% food inflation, which would distort both its deviation and the regional mean. All 100 province-quarters in 2021–2025 are present, so no label was affected. **This should be fixed in any future label build.**

### The HIGH/LOW label

| Version | Rule | Notes |
|---|---|---|
| Thesis code (l.222–226) | `stress > median(all labelled rows)` | — |
| Production `labels.parquet` | Same rule over 95 rows (2020–2025) | Threshold 14.6; 39 of the 80 rows from 2021–2025 are HIGH |
| Approved window (2021–2025) | Same rule over 80 rows | Threshold **14.345**; 40 HIGH, 40 LOW |
| Experiments E1/E3, A-origin | Training-fold median τ_T (10.84 → 14.11) | Used for both training and retrospective test labels |
| Experiments E1/E3, A-global | 14.345 | Same |

### Model and dashboards

**Model:** LightGBM predicts P(HIGH); HIGH if p ≥ 0.50.

**Dashboard paths:**

| System | Rule and code location | What its HIGH means |
|---|---|---|
| Aligned backend (`aipheed-backend-aligned/`) | `app/services/reference.py` l.106–117: model probability ≥ 0.50 → "high"; ≥ 0.60 → alert. Indicator text (`app/services/dashboard.py` l.45–56): "thresholded at the global median (Equation 3)"; caveat: rankings are "relative ordinal". | The Equation 3 label |
| **Thesis-documented `backend/` (served)** | `app/ml/inference/thesis_predictor.py` l.116 and l.171: blend probability ≥ **0.712** (bundle threshold) → "HIGH". The model is trained on **`label_cpi`** (Equation 4), **not** Equation 3: the food CPI **index level** is above its trailing 24-quarter mean + 1σ in 2 consecutive quarters (`label_generator._build_cpi_labels`; `backend/scripts/build_thesis_panel.py`). | Not Equation 3 |

## 2. Why so many rows are HIGH

1. **The regional level dominates.** All five provinces share the SWS term. Balance-Luzon hunger was 8.7–15.4% from 2021-Q2 to 2023-Q3, then **14.3–25.3%** from 2023-Q4 to 2025-Q4.

   Every threshold derived from earlier data sits below most test-period levels:

   | Threshold | Value |
   |---|---|
   | τ_T | 10.8–14.1 |
   | τ0 | 10.84 |

   The provincial term is usually too small to pull a province back under the threshold: median |2d| is 2.4 points, maximum 10.4.

2. **Partly a real signal, not a bug.** Under a fixed, leakage-free absolute reference (D-C below), **33 of the 35** test province-quarters are above the 2021–2023 typical stress level. Regional hunger really was higher in 2024–2025.

   The consequence: **the Equation 3 label cannot separate provinces when regional hunger is far from the threshold.** That was true for most of 2024–2025.

3. **The served `backend/` label is HIGH almost always for a mechanical reason.** A price **index** rises over time, so in an inflationary period it is usually above its own trailing mean + 1σ. Its HIGH share by year:

   | Year | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 |
   |---|---:|---:|---:|---:|---:|---:|
   | HIGH share | 0% | 25% | 65% | 90% | **100%** | 90% |

   This tracks the price trend, not food insecurity, and it is not the thesis's primary Equation 3 label. **Reported for review; not changed.**

## 3. Can an absolute threshold be justified?

**No official cutoff exists in the available evidence.**

- The thesis defines HIGH as "above the global median", which is sample-relative.
- No DA or government cutoff for SWS hunger or the stress score was found in the project.
- IPC and FIES thresholds belong to other instruments.
- No new SWS material was retrieved.

**What can be justified empirically is a frozen-reference rule.**

- **Rule:** use the thesis's own statistic (the median), computed **once** from the labels published before evaluation starts, then held fixed. HIGH then means the same absolute stress level in every quarter.
- **Values:**

  | Evaluation | Labels used | Threshold |
  |---|---|---|
  | Retrospective, starting 2023-Q4 | 40 labels (2021-Q2 to 2023-Q2) | **τ0 = 10.843** |
  | Prospective, starting 2026-Q3 | All 80 labels | **14.345**, the approved value |

- **What it is not:**
  - It is an empirical reference: "above the typical stress level of the period before evaluation".
  - It is **not** an official food-insecurity cutoff.
  - The choice of reference period remains an adviser decision.

## 4. Candidate definitions compared (E4)

All four keep the Equation 3 formula.

**How the thresholds were selected (none used test labels):**

| Definition | Selection |
|---|---|
| D-A | Thesis global median |
| D-B | Each fold's training median |
| D-C and D-D | Labels published before 2023-10-01 |

**Each definition was evaluated once, with the unchanged E3 LightGBM configuration.**

| | **D-A** approved | **D-B** fold median | **D-C** frozen reference | **D-D** frozen reference + provincial priority |
|---|---|---|---|---|
| Rule | stress > 14.345 | stress > τ_T | stress > τ0 = 10.843 | stress > max(τ0, SWS_t), i.e. above τ0 **and** above the regional food-price mean |
| Fixed meaning over time | Yes | **No** (drifts) | Yes | Yes |
| Leakage-free on 2023–2025 | **No** | Yes | Yes | Yes |
| All 80 rows (H / L) | 40 / 40 | varies by fold | 56 / 24 | 33 / 47 |
| Quarters with mixed labels (of 16) | 11 | — | 10 | **16** |
| Test rows (H / L) | 30 / 5 | 32 / 3 | 33 / **2** | 13 / 22 |
| Test quarters with mixed labels (of 7) | 4 | 3 | 2 | **7** |

### Results on the 7 test quarters (35 rows; n_eff ≈ 7 quarters)

| Definition | Predictor | Correct | Balanced acc. | HIGH precision | HIGH recall | LOW recall | ROC-AUC | [[TN,FP],[FN,TP]] | Test quarters with mixed **predictions** |
|---|---|---|---:|---:|---:|---:|---:|---|---:|
| **D-A** (leaky) | LightGBM | 23 | 0.633 | 0.909 | 0.667 | 0.60 | 0.667 | [[3,2],[10,20]] | 2 |
| | Carry-forward | 24 | 0.650 | 0.913 | 0.700 | 0.60 | 0.713 | [[3,2],[9,21]] | 5 |
| | Equation 3 rule | 22 | 0.617 | 0.905 | 0.633 | 0.60 | 0.780 | [[3,2],[11,19]] | 6 |
| | Always-HIGH | 30 | 0.500 | 0.857 | 1.000 | 0.00 | undefined | [[0,5],[0,30]] | 0 |
| **D-B** | LightGBM | 32 | 0.802 | 0.968 | 0.938 | 0.67 | 0.797 | [[2,1],[2,30]] | 3 |
| | Carry-forward | 30 | 0.771 | 0.966 | 0.875 | 0.67 | 0.740 | [[2,1],[4,28]] | 4 |
| | Equation 3 rule | 29 | 0.755 | 0.964 | 0.844 | 0.67 | 0.927 | [[2,1],[5,27]] | 5 |
| | Always-HIGH | 32 | 0.500 | 0.914 | 1.000 | 0.00 | undefined | [[0,3],[0,32]] | 0 |
| **D-C** | LightGBM | 34 | 0.985 | 1.000 | 0.970 | 1.00 (2/2) | 0.977 | [[2,0],[1,32]] | 2 |
| | Carry-forward | 31 | 0.939 | 1.000 | 0.879 | 1.00 | 1.000 | [[2,0],[4,29]] | 4 |
| | Equation 3 rule | 31 | 0.939 | 1.000 | 0.879 | 1.00 | 1.000 | [[2,0],[4,29]] | 4 |
| | Always-HIGH | 33 | 0.500 | 0.943 | 1.000 | 0.00 | undefined | [[0,2],[0,33]] | 0 |
| **D-D** | LightGBM | 18 | **0.535** | 0.400 | 0.615 | 0.45 | 0.577 | [[10,12],[5,8]] | **3** |
| | Carry-forward | 20 | 0.565 | 0.438 | 0.538 | 0.59 | not computed (two-condition rule) | [[13,9],[6,7]] | 7 |
| | Equation 3 rule | 21 | 0.603 | 0.471 | 0.615 | 0.59 | not computed (two-condition rule) | [[13,9],[5,8]] | 7 |
| | Always-LOW | 22 | 0.500 | — | 0.000 | 1.00 | undefined | [[22,0],[13,0]] | 0 |

**Pre-registered decision rule, LightGBM vs the better baseline:**

| Definition | Gain | 95% CI | Verdict |
|---|---:|---|---|
| D-A | −0.017 | — | Non-inferiority |
| D-B | +0.031 | 0.000 to 0.069 | Non-inferiority |
| D-C | +0.045 | 0.015 to 0.088 | Non-inferiority |
| D-D | **−0.068** | −0.200 to +0.047 | **No demonstrated improvement** |

**Note on D-C's bootstrap:** 950 of 10,000 resamples were skipped because they contained no LOW row.

**Consistency check:** D-A and D-B reproduce the E3 results exactly. E4's pipeline is consistent with E3.

**D-D quarter-level results.** For each predictor: correct / predicted HIGH, out of 5.

| Quarter | Actual HIGH | LightGBM | Carry-forward | Equation 3 |
|---|---:|---|---|---|
| 2023-Q4 | 3 | 3 / 3 | 3 / 3 | 3 / 3 |
| 2024-Q1 | 3 | 3 / 3 | 3 / 3 | 3 / 3 |
| 2024-Q2 | 1 | 1 / **5** | 1 / 3 | 1 / 3 |
| 2024-Q3 | 2 | 2 / **5** | 2 / 3 | 2 / 3 |
| 2024-Q4 | 1 | 4 / **0** | 5 / 1 | 5 / 1 |
| 2025-Q1 | 1 | 2 / 4 | 4 / 2 | 4 / 2 |
| 2025-Q4 | 2 | 3 / **0** | 2 / 1 | 3 / 2 |

## 5. Interpretation

**D-B (current exploratory primary).** Its threshold drifts, so HIGH means different absolute levels across quarters. It produced 32/35 HIGH. **Not recommended as the risk definition.**

**D-C (frozen absolute reference).** This is the most defensible **absolute** definition on the Equation 3 scale: fixed meaning, leakage-free, approved statistic.

- **Its finding:** in 2024–2025, **essentially every province was HIGH**. That reflects real regional hunger, not a modelling defect.
- **Its evaluation is uninformative:** only **2 LOW test rows**, and the simple baselines already rank perfectly (AUC 1.0).
- **LightGBM's 34/35 (balanced accuracy 0.985) must not be presented as success.** Always-HIGH scores 33/35.

**D-D (frozen reference + provincial priority).** This is the only definition that **separates provinces in every quarter**: 7 of 7 test quarters are mixed.

- **LightGBM cannot predict it:** balanced accuracy 0.535, AUC 0.577. That is **below** carry-forward (0.565) and the Equation 3 rule (0.603), and they are weak too.
- **LightGBM collapses to the regional level.** It predicted all five provinces HIGH in 2024-Q2 and 2024-Q3, and none in 2024-Q4 and 2025-Q4. It labels provinces together; it does not rank them.
- **This matches E2:** no predictor forecast the next quarter's provincial food-price ordering reliably.

**Which provinces are higher-risk?** **The evidence is insufficient to determine which provinces are genuinely at higher food-insecurity risk.**

- The only province-specific component in the data is relative food-price pressure.
- Its ordering shifted over time:
  - over 2021–2025, D-D HIGH counts were Rizal 9, Batangas 8, Quezon 6, Cavite 5 and Laguna 5;
  - in the 2023-Q4 to 2025 test quarters, Laguna and Quezon led with 4 each.
- No province-level hunger outcome exists.
- **Model output must not be presented as confirmed provincial risk.**

**How much evidence supports this:**

| Definition | Independent test quarters | Test LOW cases |
|---|---:|---:|
| D-A | 7 (reused) | 5 |
| D-B | 7 (reused) | 3 |
| D-C | 7 (reused) | 2 |
| D-D | 7 (reused) | 22, but across only 7 quarters |

**E4 is the fourth analysis on these quarters.**

## 6. Proposal for review (not implemented in production)

**Report two clearly separated indicators instead of one HIGH/LOW label:**

1. **Regional food-stress status (absolute):** D-C's frozen-reference rule.
   - Prospectively, with the 2021–2025 reference, this is the approved 14.345.
   - Wording: "above / not above the typical 2021–2025 stress level".
   - It applies to all provinces jointly when SWS dominates.
2. **Provincial relative food-price pressure (relative, descriptive):** whether a province's food inflation is above the regional mean.
   - It should be shown **as observed data with a lag, not as a model forecast**, because no tested predictor forecasts it reliably.
   - It must be labelled "relative food-price pressure", **not** "food insecurity".

**Keep LightGBM as the primary model** for the regional status (D-C/D-A). Report it against carry-forward and the Equation 3 rule. Do not claim a provincial-ranking capability that E2 and E4 did not find.

## 7. Unresolved decisions

| # | Decision | Owner |
|---|---|---|
| 1 | Adopt a frozen-reference absolute rule (D-C), and confirm the reference period (2021–2025 → 14.345 prospectively). Not an official cutoff. | Adviser |
| 2 | Present a two-tier indicator (regional status + relative provincial food-price pressure) instead of a single provincial HIGH/LOW | Adviser |
| 3 | The served `backend/` dashboard uses `label_cpi`, a trend-driven index flag (HIGH 90–100% in 2023–2025), not Equation 3. Whether that meaning is acceptable for DA. | Adviser and researcher |
| 4 | Fix the latent `fillna(0.0)` CPI handling in `label_generator.py` before any future label build | Researcher (code change; not made) |
| 5 | Obtain province-level outcome data (2021–2026), which is required to identify genuinely higher-risk provinces | Researcher |
| 6 | **Exposure found during the trace:** production `backend/data/processed/psa_indicators.parquet` runs through **2026-Q4**, and `backend/data/thesis/panel.parquet` through **2026-Q3** (files dated 2026-10-06 and 2026-10-10). These are food CPI rows that are components of the protected 2026-Q3/Q4 outcomes. Only the quarter list was then examined, but one aggregate (the 2026-Q1 to Q3 `label_cpi` HIGH share, 0.93) was printed while checking the served label. **No value was used in E4.** The protected-evaluation plan must account for this. | Researcher |

## 8. Integrity of E4

| Check | Result |
|---|---|
| Protocol | Fixed before any E4 code |
| Tests | 10 new E4 tests; full suite 230 passed before execution |
| Runner hash guard | 350 protected files unchanged, including the E1, E2 and E3 runs |
| Label access | 28 label reveals, all after that fold's predictions were written |
| 2026 data | No 2026 label or outcome used |
| Production modules | None loaded |
| Production `backend/` | 54 files re-hashed; unchanged. No archive, candidate or pipeline-run folders. |
| Model configuration | The E3 LightGBM configuration, unchanged; no tuning |
| Definition choice | Made on a-priori criteria (§4 of the protocol), not on model results |
