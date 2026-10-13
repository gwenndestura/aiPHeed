# E3 Report: Compact, Constrained LightGBM (run 20261011T114801Z_E3)

**EXPLORATORY.**

- E3 is the **third model design** evaluated on the same 7 reused quarters.
- Its design was informed by E1, E2 and the diagnosis. **It is neither blind nor an independent validation.**
- **It cannot establish the > 75% requirement.**

This report was added after the run and is not listed in `manifest.json`.

## Configuration (as frozen in `../../E3_PROTOCOL.md`)

| Item | Value |
|---|---|
| Target | Approved Equation 3 binary label, unchanged |
| Primary | **A-origin**, fold-specific training median; pending adviser approval |
| Secondary | **A-global**, 14.345; **leakage-affected** |
| Model | `LGBMClassifier(objective=binary, num_leaves=4, min_child_samples=5, n_estimators=100, learning_rate=0.05, random_state=42)`; `scale_pos_weight` from fold training labels; `monotone_constraints=[+1, +1, 0, 0, 0, 0, 0]` |
| Inputs, in order | `last_published_stress` (+1), `sws_hunger` (+1), `sws_change`, `cpi_rel`, `food_cpi_yoy`, `rice_price_regular_accel`, `unemployment_rate` |
| Constraint check | Column order and constraint enforcement were verified by a synthetic test before the run |
| Sensitivity | **+FSSI**, unconstrained, as input 8 |
| Folds | The 7 E1 test quarters (35 rows), with 8–15 Rule-L-eligible training quarters. The determinism check passed in every fold, and no fold was degenerate. |
| Input availability | All 7 inputs present in every test row (0% missing). Training-row missingness was 7–38%, from the earliest quarters only. **FSSI was missing in 60–100% of test rows** and about 70% of training rows. |
| Pre-run tests | 12 E3 safety tests, plus the full suite (220 passed) |
| Hashes | Protocol, runner, input provenance and versions are in `config.json` |

## Primary: A-origin, base inputs (test set 32 HIGH / 3 LOW)

| Predictor | Correct | Mean-quarter acc. (bootstrap 95% CI) | Balanced acc. | Weighted P / R / F1 | HIGH recall | LOW recall | ROC-AUC | Confusion matrix [[TN,FP],[FN,TP]] |
|---|---|---|---:|---|---:|---:|---:|---|
| **E3 LightGBM** | 32/35 | 0.914 (0.829–0.971) | **0.802** | 0.928 / 0.914 / 0.920 | 0.938 | 0.667 | 0.797 | [[2, 1], [2, 30]] |
| Carry-forward | 30/35 | 0.857 (0.800–0.914) | 0.771 | 0.911 / 0.857 / 0.877 | 0.875 | 0.667 | 0.740 (score: last stress − τ) | [[2, 1], [4, 28]] |
| Equation 3 rule | 29/35 | 0.829 (0.743–0.914) | 0.755 | 0.906 / 0.829 / 0.857 | 0.844 | 0.667 | **0.927** (score: s − τ) | [[2, 1], [5, 27]] |
| Always-HIGH (reference) | 32/35 | 0.914 | 0.500 | 0.836 / 0.914 / 0.873 | 1.000 | 0.000 | undefined (constant) | [[0, 3], [0, 32]] |
| Always-LOW (reference) | 3/35 | 0.086 | 0.500 | 0.007 / 0.086 / 0.014 | 0.000 | 1.000 | undefined (constant) | [[3, 0], [32, 0]] |
| *E1 MODEL-B2 (not refitted)* | *20/35* | *0.571* | *0.615* | — | *0.563* | *0.667* | *0.688* | *[[2, 1], [14, 18]]* |

**E3 Brier score:** 0.072.

**Clopper–Pearson on rows (optimistic):** E3 0.769–0.982.

### Paired quarter bootstrap: balanced accuracy, E3 − baseline

10,000 draws. 209 draws were skipped because the resample contained no LOW row.

| Baseline | Point difference | 95% CI |
|---|---:|---|
| Carry-forward | +0.031 | 0.000 to +0.069 |
| Equation 3 rule | +0.047 | +0.015 to +0.091 |

### Per quarter (E3: correct / predicted HIGH / actual HIGH, out of 5)

| Quarter | E3 |
|---|---|
| 2023-Q4 | 5 / 4 / 4 |
| 2024-Q1 | 4 / 3 / 4 |
| 2024-Q2 | 5 / 5 / 5 |
| 2024-Q3 | 4 / 4 / 5 |
| 2024-Q4 | 5 / 5 / 5 |
| 2025-Q1 | 5 / 5 / 5 |
| 2025-Q4 | 4 / 5 / 4 |

### Decision rule, fixed in advance

| Item | Value |
|---|---|
| Better baseline | Carry-forward (balanced accuracy 0.771) |
| Gain | +0.031 |
| CI | 0.000 to 0.069 |
| Accuracy not below carry-forward | Yes |
| Improvement requires | A gain ≥ 0.10 **and** a CI excluding 0. **Not met.** |
| **Verdict** | **Non-inferiority** |

## Secondary: A-global, threshold 14.345 (LEAKAGE-AFFECTED; test set 30 HIGH / 5 LOW)

| Predictor | Correct | Balanced acc. | HIGH / LOW recall | ROC-AUC | Confusion matrix |
|---|---|---:|---|---:|---|
| E3 LightGBM | 23/35 | 0.633 | 0.667 / 0.600 | 0.667 | [[3, 2], [10, 20]] |
| Carry-forward | 24/35 | 0.650 | 0.700 / 0.600 | 0.713 | [[3, 2], [9, 21]] |
| Equation 3 rule | 22/35 | 0.617 | 0.633 / 0.600 | 0.780 | [[3, 2], [11, 19]] |
| Always-HIGH | 30/35 | 0.500 | 1.0 / 0.0 | undefined | [[0, 5], [0, 30]] |

- E3 minus carry-forward balanced accuracy: −0.017 (CI −0.077 to +0.035).
- **Verdict:** non-inferiority, with accuracy below carry-forward.

## Sensitivity: +FSSI (reported, not substituted)

| Analysis | E3 + FSSI | Balanced acc. | ROC-AUC | Gain vs carry-forward (CI) | Verdict |
|---|---|---:|---:|---|---|
| A-origin | 33/35 | 0.818 | 0.734 | +0.047 (+0.015 to +0.088) | Non-inferiority |
| A-global | 24/35 | 0.650 | 0.613 | 0.000 (−0.103 to +0.100) | Non-inferiority |

**Interpretation limit:** FSSI was missing in most rows (test 60–100%; training about 70%). The thesis's FSSI hypothesis is therefore **not tested** in any meaningful sense.

## Interpretation

**Does LightGBM add value beyond the baselines?**

**Not demonstrably.**

**What E3 shows:**

- The compact, monotone-constrained LightGBM **fixed E1's underperformance**: 20/35 → 32/35, balanced accuracy 0.615 → 0.802, HIGH recall 0.56 → 0.94.
- It is **non-inferior to, and nominally above,** carry-forward and the Equation 3 rule.
- The gain over carry-forward is **2 HIGH rows**. All three predictors caught the same 2 of the 3 LOW rows.
- Its interval reaches 0.

**Ranking quality (AUC):**

- E3's AUC (0.797) is **below the Equation 3 rule's continuous score (0.927)**.
- So E3's advantage lies in threshold placement for HIGH rows, not in better ranking of risk.

**The 91.4% raw accuracy is not evidence for the 75% requirement:**

- It equals always-HIGH's accuracy on the same rows.
- The LOW class has only 3 rows.
- The quarters are reused, and this is the third design tested on them.
- n_eff ≈ 7.
- The optimistic row-level lower bound (0.769) treats the 5 provinces as independent, which they are not.

**Under the leakage-affected global threshold,** E3 is slightly below carry-forward.

**Per the protocol:**

- **This result does not freeze a candidate for 2026 forecasting.**
- **No further model variations were run.**

## What independent prospective evidence is still required for the > 75% requirement

1. **A forecast frozen before its outcome exists.** A separately authorized decision to freeze a configuration, hash it, and issue forecasts before outcomes, for quarters never used in design. The protected 2026-Q3/Q4 quarters qualify (there, 14.345 is leakage-free and equal to τ), but they are only 10 rows and 2 quarters. Even 10/10 gives a 95% lower bound of 0.69.
2. **Enough independent units.** About 13 or more consecutive correct quarters at the quarter level, or province-level outcome data that make rows more independent.
3. **The right measures.** Balanced accuracy and LOW-class recall on a test set with enough LOW rows, plus a margin over carry-forward and Equation 3 whose interval excludes 0.
4. **Verified inputs.** Verified publication dates (not the WD1 proxy) and point-in-time input vintages.
5. **Adviser decisions.** The threshold designation, D3, and WD1/WD2/WD5.

## Integrity

| Check | Result |
|---|---|
| Runner hash guard: 312 protected files (data, models, frozen forecasts, reports, pre-registration and E3 protocol, runners, **E1 and E2 runs**, diagnosis) | **Unchanged** |
| Label access | 28 label reveals, all after that fold's predictions were written |
| No 2026 label or outcome | Enforced |
| Production modules | None loaded |
| Production `backend/` | 54 files re-hashed; served model `cbab63f8…` unchanged. No archive, candidate or pipeline folders. |
| Pipeline, scheduler, scheduled tasks, dashboard, thesis | Untouched. Nothing committed, deployed or promoted. |
| Deviations from protocol | **None.** Two test functions had a fixture-unpacking bug, fixed **before** the run; the runner and protocol were not changed. |
