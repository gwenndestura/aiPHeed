# E3 Protocol: compact, constrained LightGBM classifier

**Status:** fixed before any E3 code was run.

**Basis:** `LIGHTGBM_IMPROVEMENT_PLAN.md` §3.

**Preserved unchanged:** all E1 and E2 artifacts and reports.

## Disclosures

1. **E3 is the third model design evaluated on these reused quarters,** after E1 (44-input MODEL-B2) and earlier 10-08/09 studies, which included ablations.
2. **E3's design was informed by earlier results:**
   - E1's failure;
   - the diagnosis (coarse default trees, level not used, missingness mismatch);
   - E2.

   **E3 is neither blind nor an independent validation. All results are exploratory.**
3. **The approved Equation 3 target is unchanged.** Stress = SWS + 2 × (provincial food CPI YoY − five-province mean); HIGH if stress > threshold.
4. **Thresholds:**
   - **Primary: A-origin**, the fold-specific median of the training rows eligible under Rule L. **Pending adviser approval.**
   - **Secondary: A-global**, 14.345. **Leakage-affected:** the threshold was computed using the test quarters.
5. **Unchanged from E1:**
   - test quarters 2023-Q4, 2024-Q1, 2024-Q2, 2024-Q3, 2024-Q4, 2025-Q1, 2025-Q4 (35 rows);
   - Rule L training eligibility (development protocol);
   - at least 8 eligible training quarters per fold.
6. **Training data only:**
   - Class weights, thresholds and monotone constraints are set from training data or a-priori theory only.
   - There is no preprocessing to fit: NaN is kept and handled natively by LightGBM; there is no scaling or imputation.
   - **No E1 or E2 test performance is used to select anything after this file is fixed.**

## Primary model

LightGBM classifier with one fixed configuration:

```
LGBMClassifier(objective="binary", num_leaves=4, min_child_samples=5, n_estimators=100,
               learning_rate=0.05, random_state=42, verbosity=-1,
               scale_pos_weight=(1-p)/p,   # p = HIGH share of the fold's training labels
               monotone_constraints=[+1, +1, 0, 0, 0, 0, 0])
```

The determinism check from E1 applies: the model is fitted twice per fold and must give identical predictions.

## Inputs, in this order

The monotone-constraint vector is aligned with this column order.

| # | Input | Construction (origin-valid) | Constraint | Justification |
|---|---|---|---|---|
| 1 | `last_published_stress` | Equation 3 stress of the province's latest label **published before that row's own origin** (Rule L) | **+1** | The target is "stress > τ", and stress is persistent; a higher last published stress cannot lower the risk |
| 2 | `sws_hunger` | Latest SWS round published before the origin (development frame) | **+1** | SWS enters Equation 3 with coefficient +1 and is the regional level of the target |
| 3 | `sws_change` | Change between the last two published rounds | 0 | Direction ambiguous (momentum vs mean reversion) |
| 4 | `cpi_rel` | Latest available provincial deviation (WD1 proxy) | 0 | Its relation to the next deviation depends on persistence, an empirical question |
| 5 | `food_cpi_yoy` | Latest available provincial level | 0 | The target uses the deviation, not the level |
| 6 | `rice_price_regular_accel` | Development schedule | 0 | No defensible a-priori direction for a relative-median label |
| 7 | `unemployment_rate` | Development schedule | 0 | Same |

**Missing values:**

- Input 1 is NaN when no earlier label was published before that row's origin. This affects the earliest training quarters only; all test rows have it.
- **No input is replaced by a later value.**

**One pre-declared sensitivity, "+FSSI":** the same model with `FSSI` as input 8, unconstrained. Its missingness is reported. **It never substitutes for the primary model.**

## Baselines and scores for AUC

| Predictor | Class | Continuous score for AUC |
|---|---|---|
| Carry-forward | HIGH if `last_published_stress` > τ | `last_published_stress` − τ (a meaningful margin) |
| Equation 3 rule | HIGH if `sws_hunger + 2·cpi_rel` > τ; missing inputs fall back to the training majority | `sws_hunger + 2·cpi_rel` − τ |
| Always-HIGH and always-LOW | References only | Constant, so **AUC is undefined** |
| E1 MODEL-B2 | Before/after comparison, read from E1 `metrics.json` | Not refitted |

## Metrics

**Per predictor, analysis and sensitivity:**

- mean-quarter accuracy;
- balanced accuracy (headline);
- weighted precision, recall and F1;
- HIGH recall and LOW recall;
- ROC-AUC where a continuous score exists and both classes are present;
- Brier score (LightGBM only);
- confusion matrix and test class counts;
- per-quarter results.

**Uncertainty:**

- **Quarter-cluster bootstrap** (10,000 draws, seed 42):
  - mean-quarter accuracy;
  - the paired difference in pooled balanced accuracy between E3 and each baseline. Draws in which a class is absent are skipped and counted.
- **Clopper–Pearson** on rows, labelled optimistic.

## Decision rule (A-origin, base, 7 quarters; exploratory criteria)

Let **B** = the baseline (carry-forward or Equation 3) with the higher balanced accuracy.

| Outcome | Condition |
|---|---|
| **Improvement** | BA(E3) − BA(B) ≥ 0.10, **and** the quarter-bootstrap 95% CI of that difference excludes 0, **and** mean-quarter accuracy(E3) ≥ carry-forward's |
| **Non-inferiority** | Not an improvement, and BA(E3) ≥ BA(B) − 0.05 |
| **No demonstrated improvement** | Otherwise |

**How the outcome is interpreted:**

- With 7 reused quarters and only 3 LOW rows, these are **exploratory criteria**. Passing them is not proof of generalization.
- **No E3 result freezes a candidate for 2026 forecasting.** That needs a separate decision and authorization.
- **No further model variations are run after the E3 results.**

## Safeguards

| Safeguard | Implementation |
|---|---|
| Isolation | The runner never loads production modules |
| Output | Fresh `runs/<UTC>_E3/` folder; no overwriting |
| Label vault | Training access only to quarters before the target; test labels revealed only after that fold's predictions are written |
| Protected-file hashing | Before and after the run, including the E1 and E2 runs, the diagnosis, plans and runners |
| 2026 data | No 2026 labels or outcomes |
