# E99 reproduction (decision 9): the paper's Chapter III pipeline, rerun exactly

**What was reproduced.** E99 (`37e0f88` protocol, `6da1054` results, branch `origin/e99-chapter3-evaluation`, not merged
into this branch) ran the paper's Chapter III pipeline:
- the Eq. 3 label (SWS hunger + 2 × provincial food-CPI deviation, above the global median);
- the 12 Chapter III features;
- Algorithm 3 (lead-time discovery);
- Algorithm 4 (Optuna TPE, 100 trials, blind 2025-Q4..2026-Q3 holdout, accept if weighted F1 ≥ 0.75 and AUC ≥ 0.80);
- the six Chapter I comparators, plus prevalence, FIRI v2 and the Chapter III blend, on identical folds;
- SHAP for H1.

**How.**
1. E99's commit `6da1054` was checked out in a separate git worktree in the scratchpad. This branch's working tree and
   backend were not touched.
2. Its runner was executed unchanged, from its own `backend/`, as its docstring instructs:
   `python ../aipheed-backend-aligned/experiments/E99_Chapter3_Evaluation/runner/chapter3_eval.py`.
3. Nothing in the method was modified.

**Copied here (read-only reference):**
- `E99_reference/`: the whole E99 folder from `6da1054`;
- `E99_reference/runs/20261102T222949Z_reproduction/`: the rerun's outputs and console.

## Result: reproduced exactly

| Output | Original run (2026-10-22) vs rerun (2026-11-03) |
|---|---|
| `e99_results.json` | **Identical** in every value (tolerance 1e-12). The only differences are the run timestamp and the hash of the pickled model file (next rows). |
| `eq3_labels.csv` | **Byte-identical** |
| `sealed_prospective_2026Q4.csv` and its `.sha256` | **Byte-identical**; SHA-256 `5a9e24c8…` |
| `predictions_dev_k2.csv`, `predictions_holdout_k2.csv` | Same rows, columns and classes; probabilities equal to within **4e-14** (floating-point noise) |
| `lgbm_best_k2.pkl` | The **trained LightGBM booster is identical** (model text equal). The file bytes differ only because the original was pickled under scikit-learn 1.8.0, and this machine has 1.7.2 (version metadata in the pickle). |

**Environment of the rerun:** Python 3.13, LightGBM 4.6.0, Optuna 4.8.0, SHAP 0.51.0, scikit-learn 1.7.2.

## The reproduced numbers

**Window.** E99 used **2021-Q1..2026-Q3**. Rows with an E99 `definition_A` SWS round: 95 province-quarters,
19 quarters. Global median of stress 15.473; 49.5% HIGH. This is E99's window, not decision 1's 2020-Q1..2026-Q3 (see
"What was not run").

**The label regime.** Eq. 3 is HIGH in 2 of 15 rows in 2021, 3 of 15 in 2022 and 2 of 20 in 2023. It is HIGH in 17 of
20 in 2024, 9 of 10 in 2025 and 14 of 15 in 2026. One switch, from LOW years to HIGH years.

| Step | Result | Paper criterion | Pass? |
|---|---|---|---|
| **Algorithm 3**, k = 1 (6 folds, 30 rows: 24 HIGH, 6 LOW) | Mean fold accuracy **0.300**; persistence 0.700 | ≥ 0.75 | **No → Maximum Reliable Lead Time k\* = 0** |
| Sensitivity S1 (median from development rows only) | 0.300 | ≥ 0.75 | No (k\* = 0) |
| Sensitivity S2 (holdout folds included, 10 folds) | 0.360; persistence 0.780 | ≥ 0.75 | No (k\* = 0) |
| **Algorithm 4** at k = 2 (report-only: k\* = 0, so the paper would not tune at all). Optuna best development weighted F1 0.326. | Blind holdout (20 rows, 18 HIGH / 2 LOW): accuracy **0.450**, weighted F1 **0.531**, AUC **0.611** | F1 ≥ 0.75 and AUC ≥ 0.80 | **No → not accepted** |

**Holdout, all models (k = 2):**

| Model | Accuracy | Weighted F1 | AUC | Brier |
|---|---|---|---|---|
| **LightGBM tuned (proposed)** | 0.450 | 0.531 | 0.611 | 0.497 |
| LightGBM default | 0.550 | 0.631 | 0.667 | 0.385 |
| **Naive persistence** | **0.900** | **0.900** | 0.722 | **0.100** |
| LR combined | 0.200 | 0.200 | 0.611 | 0.628 |
| LR government-only | 0.250 | 0.278 | 0.667 | 0.515 |
| LR NLP-only | 0.250 | 0.325 | 0.306 | 0.356 |
| LightGBM government-only | 0.650 | 0.719 | 0.583 | 0.354 |
| LightGBM NLP-only | 0.300 | 0.388 | 0.458 | 0.370 |
| Chapter III blend (0.4 / 0.4 / 0.2, cutoff 0.712) | 0.200 | 0.200 | 0.694 | 0.425 |

**McNemar test** (pooled development + holdout, 40 rows; tuned LightGBM vs each comparator; exact p):
- **persistence better**, p = **0.0003** (LightGBM alone right 1 time, persistence alone right 16 times);
- LR combined, p 0.77;
- LR government-only, p 0.39;
- LightGBM better than LR NLP-only, p **0.039**;
- LightGBM government-only, p 1.0;
- LightGBM NLP-only, p 0.092.

**SHAP rank** (final k = 2 model):
1. unemployment (t − 1);
2. rice price change (t − 1);
3. **food CPI deviation**;
4. **FSSI lag 1** (best FSSI feature);
5. FSSI acceleration;
6. FSSI lag 2;
7. FSSI;
8. climate trigger;
9–12. the other four triggers, with exactly 0 influence.

**Hypotheses (E99's pre-registered rules):**
- **H1 not rejected:** FSSI ranks 4th, outside the top 3.
- **H2 not rejected:** k\* = 0.
- **H3 not rejected:** below persistence (significant).
- **H4 and H5 blocked:** no evaluator responses.

## What was not run (stopped as instructed)

PAPER_ALIGNED's own plan has **not** been written or run. It would use:
- decision 1's 2020-Q1..2026-Q3 window;
- the 45 → 12 selection on training folds;
- the origin-specific median (Rule 3);
- Eq. 5 `CPI_dev`;
- Eq. 3 through `risk_score_v2.py`.

Those choices differ from E99. They do not change the root cause that E99 identified: one LOW-to-HIGH regime switch
within about 19–23 labelled quarters. That run waits for your approval.
