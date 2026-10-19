# E60 final accuracy-optimization report

**Branch:** `e60-accuracy-optimization` (local, from 88d5266). **Nothing committed, pushed, deployed or switched.** E38 stays the code default.

**Freeze record:**
- Protocol sha `bdf358ea…`, frozen 2026-10-18T15:38:12Z before any candidate score.
- Classifier v2 sha `327f9431…`, frozen 2026-10-19T08:54 Z, before the EVAL half was scored and before any feature was built.
- Annotation hashes in `annotation/ANNOTATIONS_SHA256.txt`.
- Sealed candidates sha in `sealed/candidates.csv.sha256`.
- Because you asked for no commits, these are hash records, not git commits.

**Which results are which:**

| Kind | Content |
|---|---|
| Exploratory | the miss analysis (section 2); the case review |
| Used for selection | the DEV quarters 2024-Q2..2025-Q3 (Brier, final-candidate rule) and the DEV annotation half (classifier v2) |
| "Untouched" by E60 | TEST quarters 2025-Q4..2026-Q3 (1 HIGH of 20) and the EVAL annotation half. Earlier experiments did examine the TEST quarters. **No historical quarter is untouched by the project.** |

## 1. Target (`TARGET_VALIDITY_AND_DATA_GAPS.md`)

**Equivalence:** T43 equals provincial food-price pressure (PS) on all 50 evaluation rows.
- The hunger condition held in every quarter from 2023-Q4.
- It changed state only before any evaluable forecast.

**What decides HIGH:** 13 of 18 HIGH rows are set by the food-minus-headline inflation gap alone, against province thresholds of −0.56 to +0.92 points.

**Strongest defensible target:**
- No provincial food-insecurity outcome exists in the data (CBMS and provincial FIES are unavailable). The strongest defensible target is therefore **T43, named a "food-stress risk indicator"**, with PS as the training label of the price learner.
- The target was **not** changed in E60.

## 2. Why the model misses cases (root causes)

| Case(s) | Cause category | Evidence | Solvable? |
|---|---|---|---|
| 2024-Q2 Batangas, Cavite, Laguna, Quezon (E56 misses; E58-EW catches) | **2: stale input.** The 2023-Q4 SWS round was posted 2024-01-22, after the 2024-01-01 issue date. | P_price 0.81–0.96 vs P_hunger 0.21 | **Partly.** The E58-EW decision rule, or a later issue date (E59 sensitivity S1), fixes it. |
| 2024-Q4 Cavite, Laguna (missed by all) | **8: unanticipatable event** + **4: missing information.** Food-minus-headline gap rose after the issue date (2024-07-01); typhoons Kristine and Pepito struck in Oct–Nov 2024. | No attributed relevant news before issue (Laguna: 2 unrelated climate items) | **No** with data available at issue |
| 2026-Q2 Cavite (missed by all) | **1: label knife-edge** (food YoY 4.73 vs threshold 4.71) + **8** | 1 thin news item (Kadiwa outlet) | **No** |
| 2025-Q1 Batangas (E56 / EW miss; not an onset) | **7: threshold.** P = 0.45, just under 0.5. | | Only by threshold tuning on these rows (not allowed) |
| 7 false alarms (2024-Q2 Rizal; 2024-Q3 Cavite, Laguna; 2025-Q2 Cavite; 2025-Q3 Batangas, Cavite; 2026-Q3 Quezon) | **6: model limitation.** The base-effect CPI projection over-shot after the 2024–25 rice tariff cut and import suspensions. 2024-Q2 Rizal comes from regional EMERGING applied to every province. | CITL −0.10 | Partly (the E60 A candidate removes 1) |
| Price pressure without a risk-label change (2021–2023: 24 of 29 PS-HIGH rows were T43 LOW) | **1: target limitation** | | Not on this target |
| Weak province separation (within-quarter AUC 0.71; Cavite accuracy 0.4–0.5) | **1 + 4:** provincial content comes only from CPI deviations; news is thin per province | | Needs provincial outcome data |
| Old news features ~0 (OFW 0/105) | **4 + 5:** retrieval never queried those triggers; v1 keyword rules | E60 N1 | **Yes, fixed** in E60 (sections 3–4) |

## 3. News (`NEWS_PIPELINE_AUDIT.md`, `NEWS_CLASSIFICATION_EVALUATION.csv`, `NEWS_ABLATION_RESULTS.csv`)

**Retrieval:**
- 2,070 trigger-specific requests added 1,347 unique articles (title, outlet, date, URL; Google News RSS; approved domain policy v1).
- The corpus now holds 9,667 titles, 697 relevant under v2.

**Classification** (EVAL, 77 titles, 16 relevant; AI annotation pending human check):

| Classifier | Precision | Recall | F1 |
|---|---|---|---|
| v1 (deployed keywords) | 0.28 | 0.56 | 0.38 |
| **v2 (E60)** | **0.92** | **0.75** | **0.83** |

The geocoder attributed 27 of 27 province-specific titles correctly.

**Features:** province-quarters with a nonzero signal rose from 6 to 18 (market), 7 to 22 (fish kill) and 1 to 13 (employment). OFW news is national only.

**Forecast value** (C vs A, same 50 rows): paired Brier **+0.003 [−0.018, +0.027]**. **No measurable gain.**
- News trades HIGH recall for fewer false alarms: in the warning form, C has HIGH recall 0.611 and false-alarm rate 0.125, against A's 0.778 and 0.188.
- News alone (B) has no signal: ROC-AUC 0.48–0.58.

**Why news does not help:**
1. The target's variation is a CPI quantity seven months ahead, which headlines about past events do not predict better than the CPI projection.
2. The rising cases still missed had no attributed news before the issue date.
3. 50 rows cannot detect a small gain.

## 4. Model comparison (`MODEL_CANDIDATE_COMPARISON.csv`, `QUARTERLY_AND_PROVINCE_RESULTS.csv`)

**All 50 rows, 10 quarters, 18 HIGH:**

| Model | Acc | Bal | HIGH prec / rec | LOW prec / rec | FP rate | Brier | ROC-AUC | PR-AUC | Onsets | Quarters ≥ 0.75 |
|---|---|---|---|---|---|---|---|---|---|---|
| **A gov-only (warning)**, E60 final | **0.80** | **0.795** | 0.70 / 0.778 | 0.87 / 0.81 | 0.19 | **0.180** | 0.790 | 0.727 | **7/10** | **8/10** |
| C gov + news (warning) | 0.78 | 0.743 | 0.73 / 0.611 | 0.80 / 0.875 | **0.125** | 0.178 | 0.795 | 0.717 | 6/10 | 7/10 |
| D + history (warning) | 0.68 | 0.641 | 0.56 / 0.50 | – / 0.78 | 0.22 | 0.190 | 0.759 | 0.663 | 4/10 | 4/10 |
| B news-only | 0.40 | 0.495 | 0.36 / 0.833 | – / 0.16 | 0.84 | 0.407 | 0.583 | 0.536 | 8/10 | 0/10 |
| F E58-EW (reference) | 0.78 | 0.780 | 0.67 / 0.778 | 0.86 / 0.78 | 0.22 | 0.182 | 0.786 | 0.722 | 7/10 | 7/10 |
| E E56 (forecast) | 0.72 | 0.684 | 0.63 / 0.556 | – / 0.81 | 0.19 | 0.214 | 0.649 | 0.644 | 3/10 | 6/10 |
| G price projection | 0.74 | 0.748 | 0.61 / 0.778 | – / 0.72 | 0.28 | 0.188 | 0.788 | 0.700 | 7/10 | 7/10 |
| H persistence | 0.56 | 0.535 | | | 0.38 | – | | | 0/10 | 3/10 |
| H majority (LOW) | 0.64 | 0.500 | | | 0 | 0.360 | | | 0/10 | 5/10 |

**Against the six SOP-Q3 baselines** (45 rows): A's forecast form scores 0.80, balanced 0.776. The best baseline is NLP-only LR at 0.667, balanced 0.523; persistence scores 0.600.

**DEV / TEST split:**
- DEV (30 rows): A warning 0.733 vs E58-EW 0.700.
- TEST (20 rows, 1 HIGH): A 0.90, majority class 0.95. TEST cannot assess HIGH detection.

**Final-candidate rule (DEV Brier):** A 0.265, C 0.270, D 0.277, so the **final E60 candidate is A**.
- A is E56's procedure without the old (near-empty) news columns.

**Improved over E58-EW?** **No, by the pre-registered rule.**
- Paired Brier −0.0017 [−0.0058, +0.0008].
- A beats E58-EW on every point estimate, but **the two differ in exactly one province-quarter** (2025-Q3 Batangas, a false alarm removed).
- By quarter, A is better in 8 and worse in 2 (sign test p = 0.11).
- Leave-one-quarter-out accuracy: A 0.778–0.822; E58-EW 0.756–0.800.

## 5. Rising stress (`RISING_STRESS_CASE_REVIEW.csv`)

| Model | Onsets caught | Notes |
|---|---|---|
| E58-EW | 7 of 10 | |
| A | 7 of 10 | the same 7 |
| C | 6 of 10 | |

**No candidate detects rising stress earlier or more often than E58-EW.**

Warnings are issued 6.3–7.7 months before the outcome is observable. For 2024-Q2 Cavite, the fish-kill reports of November 2023 were published before the issue date, but they did not change the forecast.

## 6. Answers

1. **Does the target validly represent food-insecurity risk?** Partially. It combines the two sources Chapter I names, but in 2024–26 it measures provincial food-price pressure (mainly food inflation running ahead of headline inflation), and it is not validated against any food-insecurity outcome.
2. **Strongest defensible target:** T43 kept as a clearly named food-stress risk indicator, with regional hunger shown separately and PS as the training label. No stronger outcome exists in the data.
3. **Does news improve forecasting over government indicators?** No. C vs A Brier +0.003 [−0.018, +0.027]; news alone has no signal.
4. **Useful sources, triggers, features:** none significantly. In C's trees, market and fish-kill shares and regional market shares were used at a few origins without a net gain. Fish-kill reports are the most concrete local signal found.
5. **Does the improved model beat E56, E58-EW and the baselines?**
   - E56: yes on point estimates (0.80 vs 0.72), but via the warning form already in E58-EW.
   - E58-EW: not demonstrated (1 row).
   - The six baselines: yes, on 45 rows.
6. **75%?** Yes, 0.80 pooled; 8 of 10 quarters ≥ 0.75. These are development rows, and the accuracy CI is about ±0.09.
7. **HIGH risk without excessive false alarms?** A: HIGH recall 0.778, false-alarm rate 0.19 (6 of 32 LOW rows). Moderate.
8. **Earlier detection of rising stress?** No. Same 7 of 10 onsets as E58-EW, same lead time.
9. **Reproducible and leakage-free?** Yes for what was tested:
   - E60 tests pass (5): frozen hashes, news timing, history timing, reproduction of a sealed candidate.
   - The E56 timing audit carries over.
   - **Caveat:** the news corpus was collected retrospectively, so its completeness at past issue dates is unknown.
10. **Statistically supported improvement?** No.
11. **Generalization:** Not established. One hunger regime, 10 design-informed quarters; the frozen 2027 forecasts are the test.
12. **What the model predicts:** food-price pressure under elevated regional hunger, presented as a food-stress risk indicator. It does not predict confirmed food insecurity.
13. **Before "validated":**
    - prospective quarters scored against frozen forecasts;
    - a provincial food-insecurity outcome (CBMS or provincial FIES/NNS);
    - human verification of the news annotations;
    - DA IV-A evaluation;
    - a lead-time study.
14. **Experimental, or recommended for controlled deployment:** experimental. See `FINAL_RECOMMENDATION.md`.

## 7. Files

**Experiment folder** (`E60_E58_Accuracy_Optimization/`):
- The 13 deliverables.
- `runner/`:
  - n1 corpus audit; n2 collection; n3 sampling; n4 classifier v2; n5 features; n6 classifier evaluation;
  - t1 target; c1 candidates; c2 scoring; c3 cases;
  - protocol and classifier hashes.
- `annotation/` (sheets, keys, hashes), `data/` (E60 news store, features, classified articles), `sealed/`, `out/`, `tests/`.

**Earlier experiments:** E56–E58 are untouched. E59 has one appended correction about the remote branch.
