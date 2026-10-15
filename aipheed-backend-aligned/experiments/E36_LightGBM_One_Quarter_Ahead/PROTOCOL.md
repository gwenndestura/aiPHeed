# E36 protocol: the best defensible one-quarter-ahead LightGBM, against the six Chapter I baselines

**Status: FROZEN before any E36 arm was fitted or scored.** The SHA-256 of this file is in `runner/PROTOCOL_SHA256.txt`, and the commit that freezes it is recorded in `FINAL_REPORT.md`.

**Written 2026-10-15.** Before writing it, only these were looked at: the label table (which quarters have a released label, and how many HIGH/LOW each has) and the size of each origin's training set (`docs/LABEL_PROBE.txt`). No E36 model was fitted and no E36 score was computed.

## 1. Task

| Item | Definition |
|---|---|
| Unit | Province p (Cavite, Laguna, Batangas, Rizal, Quezon) and quarter |
| Target | Chapter I composite label T1: S1 = H + 2D, **HIGH** if S1 > τ, else LOW. H = SWS Balance Luzon hunger (regional), D = province food-CPI deviation from the five-province mean. Unchanged from E23–E35. |
| Threshold τ | Median S1 of the labelled quarters whose SWS rounds were all **posted** before the origin (`pcf_engine.threshold_at`). Each forecast is scored against its own origin's τ. |
| Lead | **1 quarter.** Forecast quarter = t+1. |
| Prediction date (origin) | O(t) = 00:00 PHT on the first day of quarter t+1 |
| Information cutoff | Anything published before O(t): SWS rounds by their verified posting date; D up to quarter t−1; Dnow (food CPI) and rice CPI for months 1–2 of quarter t; validated news of quarter t (E31 FORECAST rule). Nothing else. |
| Data window | 2021-Q1 to the authorized limit 2026-10-14. No row before 2021 is loaded. |

These definitions are those of E32 (`E32_New_Model/runner/e32_lib.py`), reused unchanged so that rows are identical to earlier evidence.

## 2. Evaluation dates (expanding window, rolling origin)

- **Development dates:** every lead-1 target from **2022-Q4 to 2026-Q3** that has a released label and whose origin has **at least 10 training pairs with both classes**: 2022-Q4, 2023-Q1, 2023-Q2, 2023-Q3, 2023-Q4, 2024-Q1–Q4, 2025-Q1, 2025-Q4, 2026-Q1, 2026-Q2, 2026-Q3 (**14 dates, 70 rows**).
  - 2022-Q2 and 2022-Q3 are excluded: their training sets have 5 rows of one class, so no classifier can be fitted. 2022-Q1, 2025-Q2 and 2025-Q3 have no definition-A label.
  - Earlier experiments started at 2023-Q4 (10 dates, 4 LOW rows). Starting at 2022-Q4 is the first date the expanding window allows. It adds 4 dates with 11 LOW rows, which is the only way to obtain a less one-sided test without changing the target.
- **These are development dates, not an untouched test.** Every one of them was examined in E9–E35. They are scored under nested (honest) selection, but no result on them may be called "unseen".
- **Final test (prospective, untouched):** 2026-Q4, lead 1 from O(2026-Q3) = 2026-10-01. The selected model and all six baselines are frozen and hashed in `frozen/` before its outcome exists. It is scored only after the SWS December 2026 round is released.
- **Periods for stability:** P-early = targets 2022-Q4..2023-Q3 (4 dates); P-late = 2023-Q4..2026-Q3 (10 dates, the E32 rows).

## 3. Features (as of O(t); E32 construction)

| Group | Features |
|---|---|
| **GOV** (government statistical indicators) | `H_last`, `H_gap`, `H_trend`, `H_margin` (SWS); `D_last`, `Dnow` (PSA food CPI); `rice_rel` (PSA rice CPI); `y_last` (the label of the latest published quarter, built from SWS and CPI) |
| **NLP** (news-derived) | `news_n`, `news_reg`, `news_direct_share`, `fssi_v2`, `fssi_missing` (E31 R1.1 validated articles; FSSI-v2) |
| **COMB** | GOV + NLP (13 features, = E32 `FEATURES`) |
| **COMPACT** | `H_margin`, `H_trend`, `D_last`, `Dnow`, `news_reg`, `fssi_v2` (6 combined features; the fewest that keep each source) |

**Training rows** at O(t): all pairs (X(t'), label of t'+1 at τ(t')) with t'+1 ≤ t−1 and every round of t'+1 posted before O(t). Rows with a missing value in any COMB feature are dropped, so **every arm at an origin trains on the same rows**.

**Test rows:** LightGBM handles a missing value natively. Logistic regression imputes the training mean (0 after standardization).

## 4. LightGBM hyperparameter grid (fixed, small)

Common settings: `objective=binary`, `n_jobs=1`, `seed=36`, `deterministic=True`, `force_col_wise=True`, `bagging` off, `verbose=-1`.

| Id | num_leaves | max_depth | min_data_in_leaf | n_estimators | learning_rate | lambda_l2 | feature_fraction | class_weight | Complexity rank |
|---|---|---|---|---|---|---|---|---|---|
| G1 stumps | 2 | 1 | 5 | 100 | 0.05 | 1.0 | 1.0 | none | 1 |
| G4 stumps, balanced | 2 | 1 | 5 | 100 | 0.05 | 1.0 | 1.0 | balanced | 2 |
| G3 shallow, regularized | 3 | 2 | 8 | 80 | 0.05 | 5.0 | 0.8 | none | 3 |
| G2 E32 setting | 4 | −1 | 5 | 150 | 0.05 | 0.0 | 0.8 | none | 4 |

Why so small: training sets have 10 to 75 rows from 2 to 15 quarters. Deeper trees cannot be supported. G2 is the setting already used for E32-LGBM.

## 5. Arms

**The proposed model: E36-LGBM (combined LightGBM, nested selection).**
- Pool: {COMPACT, COMB} × {G1, G4, G3, G2} = 8 configurations.
- **Nested rule** at each origin O(t): choose the configuration with the lowest mean per-date Brier on the **eligible prior dates**, i.e. development dates whose target label was posted before O(t). Each prior date's predictions were themselves made at its own origin, so the selection uses only information available at O(t).
- Fewer than 3 eligible prior dates → the declared default **COMB × G1**.
- Ties within 0.002 → the simpler one: COMPACT before COMB, then complexity rank G1 < G4 < G3 < G2.
- **The served model** is the configuration this rule chooses at the operational origin O(2026-Q3) = 2026-10-01, refitted on all training pairs available then.

**The six Chapter I baselines (SOP 3), on identical rows:**

| # | Baseline | Definition |
|---|---|---|
| B1 | Naive persistence | p = `y_last` (1 or 0). Publication-aware. |
| B2 | Logistic regression, combined | L2, C = 1.0, standardized COMB, `max_iter=5000`, no class weight, no tuning |
| B3 | Logistic regression, government only | B2 on GOV |
| B4 | Logistic regression, NLP only | B2 on NLP |
| B5 | LightGBM, government only | Nested rule of §5 over {GOV} × {G1, G4, G3, G2}; default GOV × G1 |
| B6 | LightGBM, NLP only | Nested rule of §5 over {NLP} × {G1, G4, G3, G2}; default NLP × G1 |

B5 and B6 get the same tuning budget per feature set as the proposed model, so the ablation is fair.

**Diagnostics (reported, never substituted for the six baselines):**
- always-HIGH (majority class, p = 1); climatology (training HIGH rate, Laplace-smoothed); calibrated persistence B1p (E32);
- PCF21 (the currently served structural forecaster);
- every fixed configuration of the pool, scored without selection (**optimistic**: shows what picking the best in hindsight would give);
- COMB-noY: COMB without `y_last`, G1 (does the model only repeat the last label?);
- P45 and F12 (existing LightGBM candidates of E25 and the 45-vs-12 selection): their stored predictions on the rows where they exist. They cannot be refitted on E36 inputs (their `features_fused` panel is not E36's input); reported on common rows only.

## 6. Metrics and reporting (lead 1)

For every arm, on all 14 dates and on P-early / P-late:
- n, dates, HIGH/LOW counts; correct/total; **accuracy** with a Wilson 95% interval and a date-bootstrap 95% interval;
- precision, recall and F1 for HIGH; specificity (LOW recall); balanced accuracy; ROC-AUC (UNSTABLE when the minority class has fewer than 5 rows); confusion matrix;
- Brier score, log loss, calibration-in-the-large, 3-bin ECE and reliability table;
- per-date and per-province accuracy and Brier;
- **province discrimination:** mean within-date SD of p; the share of dates where the arm's labels differ across provinces; within-date AUC on dates with mixed labels.

**Paired comparisons** of E36-LGBM against each of B1–B6 and always-HIGH:
- exact sign-flip test on per-date Brier differences (one-sided and two-sided);
- exact McNemar test on row correctness;
- Holm correction across B1–B6.

## 7. The 75% accuracy target (pre-declared reading)

The 75% figure is the researcher's goal, not a Chapter I threshold. Three statements are reported, never merged:

1. **Point:** nested E36-LGBM accuracy on the 70 development rows ≥ 0.75.
2. **Demonstrated:** the date-bootstrap 95% lower bound ≥ 0.75.
3. **Skill:** whether the accuracy exceeds what always-HIGH and persistence reach on the same rows, and its balanced accuracy.

"The target is met" may be written only for statement 1 with statement 3 next to it. "Demonstrated" requires statement 2. A pass on development dates is never called validation; validation needs the prospective 2026-Q4 outcome (and later quarters).

## 8. Leakage controls (automated tests in `tests/`)

1. Scrambling every SWS round posted on or after O(t), every S1 and D of quarters ≥ t, Dnow and rice of quarters > t, and news of quarters > t leaves the feature matrix, the training rows and every arm's prediction at O(t) unchanged.
2. The nested selection at O(t) uses only prior dates whose label was posted before O(t); altering the outcome of a later date changes no earlier selection.
3. No loaded row is before 2021-Q1 or after 2026-Q3 (labels) / 2026-10-14 (publication).
4. Training targets at O(t) are all ≤ t−1 and posted before O(t).
5. The frozen 2026-Q4 forecast uses only information published before 2026-10-01.

## 9. Integration rule

- The served LightGBM is the configuration chosen by §5 at 2026-10-01, whatever its score, labelled **EXPERIMENTAL / NOT VALIDATED**, with its evaluation shown next to it. Failure to beat a baseline is reported, not used alone to discard it (researcher's instruction).
- The served explanation is the exact TreeSHAP of that model (LightGBM `pred_contrib`).
- No HIGH/LOW band is shown as a validated finding; any band says it is the model's estimate.

## 10. Integrity

- Seeds fixed; one run is repeated and must be byte-identical.
- Nothing on the development dates is used to change this protocol after freezing. Any deviation goes to `DEVIATIONS.md` with its reason, and scores from before and after a deviation are both kept.
- No pre-2021 data; no fabricated data; no outcome after 2026-10-14.
