# E178 Part B: synthetic-augmented retraining of E168

## Decision: **synthetic augmentation was not adopted. No synthetic generator met the fidelity criteria fixed in advance, so the E178 evaluation (Stage 2) was not run. E168 stays in production.**

This is a valid, pre-registered outcome (`docs/e178/PROTOCOL.md`, committed before any result as `945d953`). The protocol
says:

> A generator that fails any primary criterion in any of the six jobs is rejected and removed from the Stage 2 menu. If
> both are rejected, Stage 2 is not run, and the result is "no synthetic generator met the fidelity criteria".

Both generators failed at least one primary criterion on the small 2018/2019 training sets, so no augmented model was
fitted or scored. No synthetic row ever reached an inner validation fold, an out-of-fold error, a calibration fit or the
72 real outer rows. No E178 accuracy, Brier or recall figure exists to report, and none was computed.

- **Reproduce:**
  - `cd backend; python -m app.e178.retrain equiv` (26 min)
  - `python -m app.e178.retrain fidelity` (about 7 min)
  - `python -m app.e178.retrain eval` (records this outcome)
- **Outputs:** `backend/data/e178/out/`: `fidelity.json`, `results.json`, `balance.csv`, `equivalence.json`,
  `deviations.json`, the logs and `hashes.json`.

## 1. What was tested
- **Question.** Can balanced synthetic training rows improve E168 on the real validation rows?
- **What stays E168's.** Everything except the augmentation:
  - the outer frames (built by running `app.e168.lgbm_only.task` unchanged up to its `run_proc` call);
  - the anchors H, OH and RSS; the feature sets; the 16-point LightGBM grid; the `Pv.SIGN` monotone constraints;
  - seed 168; the calibration options; region GroupKFold(5) inner selection by weighted logit SSE.
- **Two generators,** each fitted only on the rows of one training fold:
  - **jitter (a):** `y' = y + N(0, se_true²)` on the logit scale; continuous inputs `x' = x + N(0, (0.25·SD)²)`, clipped
    to the fold's range. Discrete and zero-inflated inputs, lead, survey age and the anchors are copied from the parent.
  - **smote (b):** interpolation between a row and one of its 5 nearest neighbours of the **same class and lead**, with a
    single λ ~ U(0,1) applied to the inputs, the target, its standard error and the anchors. Convex combinations stay
    within bounds and keep the class.
- **Balance and weight:**
  - synthetic budget `r ∈ {0.25, 0.5, 1.0} × n_real`, with r to be chosen only by inner region GroupKFold;
  - the minority class is filled first, up to parity, then the remainder follows the real class shares;
  - synthetic rows weigh `0.4 × 1/(se² + 0.05)`.
- **Decision rule (fixed in advance)** for the case Stage 2 had run: E178 "better" only if the Brier-difference CI upper
  bound vs E168 is below 0 at Leads 1 and 2, accuracy is ≥ E168's at both leads, leakage is below 1e-9 and it beats
  shuffled triggers.

## 2. Equivalence check (the harness reproduces E168)
- **Method.** All 18 E168 jobs were run through the E178 code with augmentation switched off: 3 surveys × 2 leads, plus
  shuffled ×3 and corrupted at Lead 1. The result was compared with `backend/data/e168/out/all_rows.csv`.

| | Result |
|---|---|
| Rows compared | 432 of 432 |
| Same configuration selected | yes, in every job |
| Selected outputs (`mu`, `p`, `half`; raw layer) | **identical (max \|diff\| = 0.0)** |
| Unselected layers (linear, Platt) | max \|diff\| 2.2 × 10⁻¹⁶ (one floating-point unit) |

- **Deviation D1** (`deviations.json`). The protocol asked for bit-for-bit equality everywhere. The one-unit differences
  in the two calibration layers E168 computes but does not use most likely come from the installed scikit-learn 1.7.2,
  scipy 1.16.3 and joblib 1.5.2, against the pinned 1.8.0, 1.17.1 and 1.5.3.
- **Effect: none on any compared quantity.** The owner decided on 2026-11-09 to proceed and document it.
- The unit test `test_without_synthetic_rows_it_is_e168` shows bit-for-bit equality with `run_proc` in the same
  environment.

## 3. Class balance (before and after)
HIGH = HFIAS moderate + severe ≥ 50 %. The synthetic budget is planned by the stated rule (`balance.csv`):

| Outer training set | Real rows | Real HIGH share | r = 0.25 → HIGH share | r = 0.5 | r = 1.0 |
|---|---|---|---|---|---|
| ENNS2021 (Leads 1, 2) | 532 | 51.9 % | 50.4 % | 50.6 % | 50.9 % |
| ENNS2018 / ENNS2019 (Leads 1, 2) | 156 | 69.2 % | 55.4 % | 51.3 % | 55.8 % |

- The ENNS2018 and ENNS2019 jobs have the same training rows, because ENNS2018 was not yet released at either origin.
- **2021 sets.** These were already balanced; augmentation there only adds rows.
- **2018/2019 sets.** These are mostly HIGH, from the 2015 survey, so balancing means adding mostly LOW rows: 39 LOW at
  r = 0.25; 66 LOW and 12 HIGH at r = 0.5; 90 LOW and 66 HIGH at r = 1.0.
- **Realised classes (r = 1.0).** SMOTE kept the planned classes exactly (66 HIGH, 90 LOW). Jitter's target noise moved
  some rows across the 50 % line (77–88 HIGH).

## 4. Fidelity checks (Stage 1, training rows only, r = 1.0, seed 17801)
Comparisons are within class, weighted by the synthetic class counts. Thresholds:

- median KS ≤ 0.15;
- maximum standardized Wasserstein ≤ 0.50;
- mean |Δ Spearman correlation| ≤ 0.10;
- TSTR/TRTR error ratio ≤ 1.25;
- ≤ 10 % near-copies and no exact copy.

**Bold** marks a failure.

| Outer training set | Generator | Median KS | Max W₁ / SD | Corr. diff. | TSTR / TRTR | Near-copies | Result |
|---|---|---|---|---|---|---|---|
| ENNS2021 L1 | jitter | 0.091 | 0.278 | 0.062 | 1.016 | 0.0 % | pass |
| | smote | 0.069 | 0.235 | 0.056 | 0.998 | 7.1 % | pass |
| ENNS2021 L2 | jitter | 0.081 | 0.207 | 0.059 | 0.966 | 0.0 % | pass |
| | smote | 0.069 | 0.323 | 0.060 | 1.052 | 7.9 % | pass |
| ENNS2019 L1 | jitter | 0.082 | 0.299 | **0.102** | 1.147 | 0.0 % | **fail** |
| | smote | 0.108 | 0.271 | **0.114** | 1.122 | 5.1 % | **fail** |
| ENNS2019 L2 | jitter | 0.053 | 0.303 | 0.096 | **1.287** | 0.0 % | **fail** |
| | smote | 0.109 | 0.282 | 0.091 | 1.199 | 4.5 % | pass |
| ENNS2018 L1 | jitter | 0.068 | 0.268 | **0.105** | 1.096 | 0.0 % | **fail** |
| | smote | 0.106 | 0.296 | **0.106** | 1.117 | 7.7 % | **fail** |
| ENNS2018 L2 | jitter | 0.091 | 0.300 | 0.087 | **1.259** | 0.0 % | **fail** |
| | smote | 0.079 | 0.218 | 0.098 | **1.253** | 3.2 % | **fail** |

**Descriptive: does each sign-constrained input keep the direction of its relationship with the forecast change?**

| | 2021 sets | 2018/2019 sets |
|---|---|---|
| jitter | 91–94 % | 34–56 % |
| smote | 78–88 % | 44–53 % |

- **Reading.** On the 2021 training set (532 rows) both generators reproduce the real data well. On the 2018/2019 set
  (156 rows, about 46 effective) they do not:
  - the correlations between inputs drift past the limit;
  - a model trained only on synthetic rows predicts held-out real regions 10–29 % worse than one trained on real rows
    (25–29 % in the failing cases);
  - the direction of input–outcome relationships is kept only about half the time.
- **Why it matters.** The small, unbalanced early origins are where augmentation would have had to help: E168's C1 and
  C4 failures are sample- and round-limited. Rows generated from 156 real rows cannot add information those rows do not
  contain, and here they also distorted it.
- **Near misses.** Several failures are close to the line (0.102 against 0.10; 1.253 against 1.25). The thresholds were
  fixed before any result and were not moved.

## 5. Results against E168 and persistence
**Not estimated.** Stage 2 did not run, so there is no E178 accuracy, Brier, recall, AUC, calibration slope,
reliability table, bootstrap CI, McNemar test, leakage or shuffled control. For reference, the E168 values that stand
(`backend/data/e168/out/results.json`, 72 real rows per lead):

| | Lead 1 | Lead 2 |
|---|---|---|
| E168 accuracy (persistence) | 0.750 (0.625) | 0.778 (0.625) |
| E168 Brier | 0.1230 | 0.1221 |
| E168 HIGH recall / precision | 0.88 / 0.595 | 0.88 / 0.629 |
| E168 leakage | 0.0 | — |
| E168 − shuffled triggers, Brier | −0.0003 [−0.015, +0.018] (does not beat shuffled) | — |

## 6. Limitations
- **The fidelity gate is strict by design.** One failing training set rejects a generator. A different rule, such as
  per-origin gating, might have let augmentation run at the 2021 origin only. That was not the pre-registered design.
  Changing it now would be a new experiment, not E178.
- **Untested settings.** Only two generators and one synthetic weight (0.4) were specified. A Gaussian copula,
  conditional generators or other weights are untested.
- **Measurement basis.** The fidelity checks measure distributional similarity and predictive usefulness on training
  rows. They cannot show that synthetic rows would or would not have improved the outer metrics. Only Stage 2 could, and
  it was correctly not run.
- **Inputs and environment.** Two gitignored raw inputs were supplied by the owner and hash-checked against their locks.
  The SunStar headline panel is replaced by an empty panel with the same columns; E168 uses none of its columns.
  Package versions differ from the pins (deviation D1).

## 7. What this means for the thesis
- **Augmentation does not fix the data limit.** Synthetic augmentation is not a way around E168's data limitation (three
  validation rounds, about 46 effective training rows at the early origins).
- **Synthetic data fails where it is needed.** Where data is plentiful (2021), synthetic rows are faithful but
  unnecessary. Where data is scarce (2015-based training at the 2018/2019 origins), they are not faithful enough to
  trust.
- **What would help.** As `docs/e168/FINAL_MODEL_REPORT.md` already concludes: more real survey rounds (ENNS 2022 or
  later provincial HFIAS), provincial employment and remittance series, and newer regional consumption data.
- **No candidate staged.** No E178 candidate artifact was staged (`backend/data/e178/candidate/` does not exist). Nothing
  was registered or promoted.
