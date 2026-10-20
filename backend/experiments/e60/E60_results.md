# E60: sensitivity of the served E49 family to three thesis details (report only; nothing is adopted or served)

## Pre-registration (written 2026-10-18, before any E60 result was computed)

**What was looked at before writing this.** The Eq. 4 label counts per quarter (the number of HIGH provinces each
quarter from `app/ml/features/label_generator._build_cpi_labels`). No model was fitted and no E60 metric was computed.

**Purpose.** These are sensitivity checks on three places where the served system differs from THESIS 2 (14):
- **(a)** the secondary label, Eq. 4 (p.51);
- **(b)** Algorithm 3's minimum training window of 8 quarters (pp.41-42);
- **(c)** the FSSI lags and acceleration of Eq. 5 / Table 3.4.2.4 (pp.38, 53).

Each is evaluated once. **Nothing is adopted or served**, whatever the result. No protected file, record or
calibration file is written. The md5s of the 7 protected files are checked at the start and at the end, and the run
stops if either check fails.

### Common to all arms (the served E49 family, as E59 ran it)

**Model and calibration**
- Inputs: E48-A1, i.e. E36's 13 inputs plus the five trigger proportions.
- Pool `E48-T5`: COMPACT_T5 / COMB_T5 x G1/G4/G3/G2.
- Nested selection: lowest mean per-date Brier on eligible earlier dates; tie 0.002 picks the simpler model; seed 36.
- Calibration: E49-C2 shrinkage, p' = a*p + (1-a)*base rate. The base rate is the training HIGH rate at the origin
  (Laplace). a is chosen on eligible earlier dates only; the raw p is used with fewer than 3 such dates.
- Threshold 0.5.

**Harness**
- Lead 1: `e36_lib.walk_forward`. Lead 2: `e37_lib.walk_forward(d, 2)`.
- Calibration follows E59's `run_lead` exactly; the E59 runner is imported, not copied.
- Origins O(t) = first day of quarter t+1. A date is scored only if all five labels exist and the training set has
  at least 10 rows with both classes (the existing rule, except in (b)).

**Reference for "difference vs served E49"**
- Lead 1: the served E49 probabilities, i.e. E59 run `20261017T133518Z` arm `k1` (identical to the record within
  5e-05).
- Lead 2: E59 arm `k2`, the same family at lead 2 with the standard window.

**Reported per arm**
- n dates and rows; LOW rows and LOW caught (true negatives / LOW rows);
- accuracy with its 95% date-bootstrap CI (e36 metrics module), balanced accuracy, precision, recall and F1 (HIGH
  class), AUC (None if one class), Brier;
- naive persistence on the same rows: accuracy, balanced accuracy, Brier;
- the paired comparison with the reference on the common (target quarter, province) rows: mean Brier difference
  (arm minus reference; negative = arm better) and the two-sided sign-flip p over per-date mean Brier differences
  (`e36_evaluate.signflip_two`; exact for up to 13 dates).

### Arm (a): Eq. 4 robustness label in place of L0

**The label**
- y = 1 when the province's food CPI for the quarter exceeds its rolling 24-quarter mean + 1 standard deviation
  (min_periods 4) for two consecutive quarters.
- Computed by the repository function `label_generator._build_cpi_labels` on `data/processed/psa_indicators.parquet`
  (food_cpi, 2020-Q1..2026-Q3).
- The function's quarter list stops at 2025-Q4. For the run only, it is extended in memory to 2026-Q3 so that the
  same 13 target dates can be labelled. The rule itself is unchanged.

**What changes and what doesn't**
- Training and test labels are replaced by Eq. 4.
- Training rows and dates are E49's own: the same publication filter, kept only where Eq. 4 has a value.
- Inputs are unchanged, including `y_last`, which stays the L0 label (an input, not the target).

**Dates.** The same 13 target quarters as E49 (2023-Q1..2026-Q3, without 2025-Q2/Q3).

**Persistence.** The Eq. 4 label of the province in quarter t-1, the last quarter whose CPI months are all published
at O(t).

**Reference.** The served E49 probabilities are scored **against the Eq. 4 labels** on the same rows. This answers
whether training on Eq. 4 predicts Eq. 4 better than the served model does. A comparison with E49 on L0 is not
meaningful, because the targets differ.

**Expected limitation, stated now.** Eq. 4 is HIGH in almost every province from 2022-Q4 on, so LOW rows will be few.
Balanced accuracy and AUC will rest on very few rows and are reported as such.

### Arm (b): Algorithm 3 with a minimum training window of 8 quarters (k = 1 and 2)

**Window rule.** A date is scored only if its training set covers **at least 8 distinct labelled target quarters (40
rows)**. Otherwise its training set is treated as empty, and the existing rule skips the date. Everything else is
unchanged.

**Algorithm 3 as pre-registered in E59**
- A lead passes if it is evaluable (>= 4 scored dates, both classes) and its accuracy is >= 0.75.
- The search halts at the first failure. The Maximum Reliable Lead Time is the last passing k.
- Point rule and CI-lower-bound rule are both reported.

**Reference.** E49 / E59 rows at the same k, on the common rows.

### Arm (c): inputs + FSSI_lag1, FSSI_lag2, FSSI_accel

**Definitions** (`app/ml/features/fssi_builder.py` l.17-19)
- FSSI_lag1(p, t) = FSSI(p, t-1).
- FSSI_lag2(p, t) = FSSI(p, t-2).
- FSSI_accel(p, t) = FSSI(p, t) - FSSI(p, t-1).

**Construction**
- FSSI is the served `fssi_v2` exactly as E36 builds it for a quarter: 0.0 when that quarter has no admitted article.
- At origin O(t), quarters t, t-1 and t-2 are complete and their news published before O(t), so the lags use only
  earlier information.

**Pool `E60-FL`.** COMPACT_T5 + 3 lags and COMB_T5 + 3 lags, x G1/G4/G3/G2, in the same simplicity order. Nested
selection, C2 and the dates are as served.

**Reference.** Served E49 on the same 65 rows.

### How results are read (fixed now)

- **(a)** does not change a thesis conclusion about L0: it is a different target. It is read as a robustness check
  only. It "supports" the L0 findings if the Eq. 4 model is no better than persistence there either; it is reported
  as a contradiction if it is significantly better (two-sided p < 0.05) than both persistence and E49-on-Eq. 4.
- **(b)** changes the RQ2 / H2 conclusion only if the Maximum Reliable Lead Time under the 8-quarter window differs
  from 1.
- **(c)** changes the H1 / SO1 news conclusion ("news adds no measurable skill") only if the lag arm's Brier is
  significantly lower than E49's (two-sided sign-flip p < 0.05). A non-significant difference in either direction
  changes nothing.
- Every arm is reported whatever its result. None is adopted or served.

## Results

(Filled in by the runner output below; nothing above this line is edited after the run.)

**Run.** `20261018T071502Z`. Output: `E60_results.json` and `runs/20261018T071502Z/predictions.csv`.
- **Pre-registration:** md5 `49caf80112af375eec844e7526e85d11`, stamped 2026-10-18T07:09:49Z. It is unchanged at
  the time of this write-up.
- **Protected files:** all 7 md5s are identical at the start and the end of the run.
- **First attempt:** it failed before computing anything (`run_log_attempt1_failed.txt`). The lag pool had been
  registered for every arm, so arms (a) and (b) tried to fit lag columns they do not have. The fix registers the lag
  pool only for arm (c). The protocol is unchanged.

### Results table

| Arm | Dates / rows | LOW rows (caught) | Accuracy (95% CI) | Balanced | Precision / Recall / F1 | AUC | Brier | Persistence acc / bal / Brier (same rows) | vs reference: Brier diff (arm - ref), sign-flip p |
|---|---|---|---|---|---|---|---|---|---|
| (a) Eq. 4 label, k = 1 | 13 / 65 | 3 (0/3) | 0.938 (0.892-0.985) | 0.492 | 0.953 / 0.984 / 0.968 | 0.677 | 0.055 | 0.877 / 0.460 / 0.123 (Eq. 4 at t-1) | vs E49 scored on Eq. 4: -0.154, p = 0.001. vs Eq. 4 persistence: -0.068, p = 0.013 |
| (b) 8-quarter window, k = 1 | 7 / 35 | 2 (0/2) | 0.886 (0.829-0.971) | 0.470 | 0.939 / 0.939 / 0.939 | 0.606 | 0.121 | 0.943 / 0.735 / 0.057 | vs E49 (same rows): +0.007, p = 0.27 (both 0.886) |
| (b) 8-quarter window, k = 2 | 5 / 25 | 2 (0/2) | 0.760 (0.480-0.960) | 0.413 | 0.905 / 0.826 / 0.864 | 0.652 | 0.163 | 0.880 / 0.478 / 0.120 | vs E59 k = 2 (same rows): -0.010, p = 0.69 (both 0.760) |
| (c) + FSSI lag1, lag2, accel, k = 1 | 13 / 65 | 12 (10/12) | 0.846 (0.769-0.923) | 0.841 | 0.957 / 0.849 / 0.900 | 0.851 | 0.151 | 0.877 / 0.860 / 0.123 | vs E49: +0.0002, p = 0.90 (both 0.846) |
| Served E49 (reference) | 13 / 65 | 12 (10/12) | 0.846 (0.769-0.923) | 0.841 | 0.957 / 0.849 / 0.900 | 0.855 | 0.151 | 0.877 / 0.860 / 0.123 | – |

### Algorithm 3 under the 8-quarter window (b)

- **Point rule:** k = 1 0.886 passes; k = 2 0.760 passes. **Maximum Reliable Lead Time = 2.** Only k = 1 and k = 2
  were run, as specified, so k = 3 was not tested and the search did not halt.
- **CI rule:** k = 1 lower bound 0.829 passes; k = 2 lower bound 0.480 fails. **Maximum Reliable Lead Time = 1.**

### Does any result change a thesis conclusion? (by the rules fixed above)

- **(a) Eq. 4.** By the pre-registered rule, this counts as a **contradiction of "no better than persistence"**: the
  Eq. 4 model is significantly better on Brier than both Eq. 4 persistence (p = 0.013) and the served E49 scored on
  Eq. 4 (p = 0.001). What that rests on:
  - Eq. 4 is HIGH for 95% of the rows (62 of 65), and the model catches **0 of the 3 LOW rows**: balanced accuracy
    0.492, AUC 0.677.
  - The gain comes from predicting HIGH confidently on a nearly constant label, not from identifying low-risk
    quarters.
  - As fixed before the run, Eq. 4 is a different target, so **no L0 conclusion changes**: the 75% target, H2, H3
    and the baselines all stay as reported.
  - The Eq. 4 result is not evidence of discrimination: the model did not identify any LOW quarter.
- **(b) 8-quarter window.** By the pre-registered rule, **the RQ2 / H2 conclusion changes under the point rule**:
  the Maximum Reliable Lead Time becomes 2 instead of 1. Under the CI rule it stays 1. What that rests on:
  - The 8-quarter window removes the early dates: 7 dates remain at k = 1 and 5 at k = 2. The removed dates are the
    harder ones; the default-window E59 k = 2 also reaches 0.760 on these same 5 dates.
  - So the higher k = 2 accuracy comes from **which dates are scored, not from a better model**: the paired
    difference vs E59 is -0.010 Brier, p = 0.69.
  - At k = 2: balanced accuracy 0.413, 0 of 2 LOW rows caught, persistence more accurate (0.880), and a 95% CI of
    0.48-0.96.
  - The k = 1 result on 7 dates (0.886) is the same as served E49 on those dates (0.886).
  - **Plain statement:** under the paper's literal 8-quarter window and point rule, Algorithm 3 returns 2 quarters.
    This rests on 5 dates and shows no skill beyond predicting HIGH. With the CI rule it returns 1.
- **(c) FSSI lags.** **No change.** The Brier difference vs E49 is +0.0002 (p = 0.90); accuracy is identical (0.846);
  AUC is 0.851 vs 0.855. Adding FSSI_lag1, FSSI_lag2 and FSSI_accel does not add measurable skill, which is
  consistent with "news adds no measurable skill".

**Nothing is adopted or served.**
