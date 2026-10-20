# E62: robustness tests of the served E49 family (lead 1). Report only; nothing adopted or served.

## Pre-registration (written 2026-10-18, before any E62 number was computed)

**What was looked at before writing this.** Only which stored fields exist:
- the record keeps each lead-1 row's `model_config` (COMB_T5xG1 ... COMB_T5xG2 at the 2026-Q4 origin);
- the frozen bundle `data/e49/model/E48_SERVING_BUNDLE.json` keeps every backtest row's six baseline probabilities.

No statistic was computed.

**Data**
- The served record is `data/e49/e49_record.json`, read only.
- The "65 development rows" are the 13 lead-1 backtest dates (2023-Q1..2026-Q3, without 2025-Q2/Q3) x 5 provinces.
- The 70 lead-1 rows are those 65 plus the 2026-Q4 forecast.
- The 7 protected md5s are checked at the start and the end of the run; it stops on any mismatch.

### Test 1: H1 permutation test of mean |SHAP| (Dnow, D_last, fssi_v2)

**Observed statistic**
- For each input: mean |SHAP contribution| (log-odds, the raw LightGBM, as stored) over the 70 lead-1 rows, from the
  record's stored drivers.
- Rank: rank of that mean among all 18 inputs (1 = largest).

**Null: input-value permutation (chosen, not the fallback).**
- At each of the 14 origins (13 backtests + the operational 2026-Q4 origin), the input's values are permuted
  across that origin's **training rows**. The model is refitted with **that origin's served configuration**, as
  stored in `model_config`; the other inputs and the labels are unchanged.
- TreeSHAP is recomputed on the origin's real test rows. The input's mean |SHAP| over the 70 rows is the null draw.
- B = 200 draws; numpy seed 62; a new permutation per origin per draw.

**Why this null**
- It needs 3 inputs x 200 x 14 = 8,400 fits of 75-row, 150-tree models, which is feasible. So the requested
  input-permutation null is used, not the label-permutation fallback.
- The nested configuration choice is **not** redone inside each permutation. Redoing it would need every pool
  configuration at every origin (about 8 x 13 x 200 x 3 = 62,400 fits). The configurations are therefore held at the
  served choices, and that is a stated limitation.

**Check before the test.** Refitting each origin's served configuration on unpermuted data must reproduce the
stored TreeSHAP contributions (max |difference| <= 1e-6). Otherwise the run stops.

**p-values**
- Primary: p = (1 + #{null >= observed}) / (B + 1).
- Also reported: a rank p = (1 + #{null rank <= observed rank}) / (B + 1), where the null rank is the input's rank
  among the 18 inputs in the permuted fits.
- Holm correction over the three primary p-values.

**Reading.** p_holm < 0.05 means the input's attribution is larger than it would be with its link to the outcome
broken, i.e. its rank does not arise by chance.

### Test 2: H3 power analysis (sign-flip test, 13 dates)

**Observed differences.** For each baseline B1..B6, d = per-date mean Brier(baseline) - per-date mean Brier(E49) over
the 5 provinces, on the 13 dates (positive = E49 better):
- E49's probabilities are the record's `p_high`; the baselines' are the bundle's `baselines_p_high`.
- **Check:** mean(d) must equal the record's `paired_vs_baselines[b].mean_brier_gain_vs_ref` within 1e-4, or the
  run stops.

**Simulation**
- For a true mean gain delta, draw 13 values with replacement from (d - mean(d)) + delta.
- Apply the exact two-sided sign-flip test (`e36_evaluate.signflip_two`: 2 x the smaller one-sided exact p, capped at
  1; 2^13 sign patterns).
- Power = the share of 5,000 draws (numpy seed 62) with p < 0.05.
- Grid delta = 0.000, 0.001, ..., 0.200.
- **MDE** (minimum detectable gain) = the smallest delta on the grid with power >= 0.80, or "> 0.200".

**Reported:** the observed gain, the observed two-sided p, the per-date SD of d and the MDE, per baseline.

**Reading.** An MDE much larger than plausible gains means "not significantly better" (H3 not rejected) cannot
exclude small real gains: the test has low power.

### Test 3: seed stability (E59 k = 1 harness)

**Method**
- `e59_run.run_lead(d, 1)` with pool E48-T5, nested selection, C2 and threshold 0.5. The only change is the
  LightGBM seed in `e36_lib._BASE`: seeds 1..10, plus 36 as the reference.
- Seed 36 must reproduce E49 (accuracy 0.846, balanced accuracy 0.841, AUC 0.855), or the run stops.

**Reported:** accuracy, balanced accuracy, AUC and Brier per seed; mean / min / max over seeds 1..10.

**Reading.** The 75% point conclusion is called seed-robust if every seed has accuracy >= 0.75. Otherwise it is
called seed-dependent.

### Test 4: per province (65 development rows)

**Reported**, for each province:
- served E49: n, accuracy at 0.5, LOW recall (LOW rows predicted < 0.5 / LOW rows) and Brier;
- the same for persistence, using the record's stored `persistence_p`.

Descriptive; no test.

### Test 5: calibration, raw (C0) vs C2 (65 development rows)

**Data**
- C0 = arm `C0` and C2 = arm `C2` of `experiments/e49/runs/20261015T215405Z/predictions.csv`.
- C2 must equal the record's `p_high` within 1e-4, or the run stops.

**Reliability table.** 10 equal-width bins [0, 0.1), ..., [0.9, 1.0]; each bin's n, mean predicted p and observed
HIGH share.

**ECE.** ECE = sum over bins of (n_bin / 65) x |mean p - observed share|.

**Uncertainty**
- Date-cluster bootstrap: 2,000 resamples of the 13 dates with replacement, numpy seed 62.
- Percentile 95% CIs for ECE(C0), ECE(C2) and the paired difference ECE(C2) - ECE(C0) (same resample).

**Reading.** If the 95% CI of the difference includes 0, there is no evidence that C2 changes calibration error.

## Results

(Appended after the run; nothing above this line is edited.)

### Protocol deviation 1 (recorded 2026-10-18T08:44:56Z, before any Test 1 permutation statistic existed)

- **What happened.** The Test 1 pre-check stopped the first run (`run_log_shap_seeds.txt`): refitting each origin's
  served configuration reproduced the stored TreeSHAP contributions with a max |difference| of 4.98e-05. The
  pre-registered tolerance was 1e-06.
- **Cause.** All 1,120 stored lead-1 contributions in `e49_record.json` are rounded to 4 decimals. A difference
  below 5e-05 is exactly that rounding; the refit models are the served ones.
- **Change.** The 1e-06 tolerance was set without accounting for the record's rounding, so it is replaced by 5e-05
  (half a unit in the 4th decimal). Nothing else changes.
- **Effect on the other tests.** Test 3 (seeds) had not started, because the run stopped at Test 1. Tests 2, 4 and 5
  had already completed before this, unaffected.

### Runs
- Tests 4, 5 and 2: one run. Tests 1 and 3: one run after deviation 1.
- Protected md5s were identical at the start and the end of both runs: True.
- Pre-registration md5 `9fc262d1a4cec7dc5674ecf26f2bbfa1`, stamped 2026-10-18T08:19:27Z; the pre-registration text above is unchanged.

### Test 1: H1 permutation test (input-value permutation, B = 200, seed 62, 70 lead-1 rows)

Pre-check: refit vs stored TreeSHAP max |difference| 4.98e-05 (<= 5e-05, deviation 1).

| Input | Rank (of 18) | Observed mean abs SHAP | Null mean (95th pct) | p | p (Holm, 3) | Rank p |
|---|---|---|---|---|---|---|
| Dnow | 1 | 1.564 | 0.179 (0.254) | 0.005 | 0.015 | 0.005 |
| D_last | 7 | 0.152 | 0.144 (0.209) | 0.363 | 0.363 | 0.647 |
| fssi_v2 | 8 | 0.143 | 0.061 (0.123) | 0.020 | 0.040 | 0.124 |

The smallest attainable p is 1/201 = 0.005.

- **Dnow:** its rank-1 attribution is far above its null (p = 0.005, Holm 0.015).
- **fssi_v2:** its attribution is above its null on mean |SHAP| (p = 0.020, Holm 0.040). Its 8th rank, though, is not unusual (rank p = 0.12; null median rank 10).
- **D_last:** its attribution is not distinguishable from its null (p = 0.36).

**What it means:** H1's reading stands.
- Food-price pressure (Dnow) is the strongest input, and that is not chance.
- The FSSI carries a small attribution above chance, but it is still not among the strongest inputs.

### Test 2: H3 power (13 dates, exact two-sided sign-flip, alpha 0.05, 5,000 draws, seed 62)

| Baseline | Observed gain (Brier, + = E49 better) | Observed p | Per-date SD | Minimum detectable gain (80% power) |
|---|---|---|---|---|
| B1_PERSISTENCE | -0.0278 | 0.416 | 0.118 | 0.085 |
| B2_LR_COMB | -0.0310 | 0.243 | 0.091 | 0.077 |
| B3_LR_GOV | -0.0490 | 0.090 | 0.095 | 0.08 |
| B4_LR_NLP | +0.0467 | 0.207 | 0.123 | 0.09 |
| B5_LGBM_GOV | -0.0060 | 0.357 | 0.021 | 0.019 |
| B6_LGBM_NLP | +0.0444 | 0.097 | 0.089 | 0.062 |

Reference: E49's own Brier is 0.151.

**What it means:** H3's "not significantly better" is only informative against large gains.
- Against B1-B4 and B6, the test could detect only gains of 0.062-0.090 Brier (40-60% of E49's Brier), so small real gains cannot be excluded.
- The observed gains are negative against B1, B2, B3 and B5.
- Against B5 (government-only LightGBM), the test could detect a 0.019 gain and observed -0.006. That is fairly direct evidence that E49 is not better than the government-only model, i.e. news adds no measurable skill.

### Test 3: seed stability (E59 k = 1 harness)

| Seed | Accuracy | Balanced | AUC | Brier |
|---|---|---|---|---|
| 36 (served) | 0.846 | 0.841 | 0.8546 | 0.1509 |
| 1 | 0.846 | 0.841 | 0.8546 | 0.1515 |
| 2 | 0.846 | 0.841 | 0.8577 | 0.1501 |
| 3 | 0.846 | 0.841 | 0.8546 | 0.1501 |
| 4 | 0.846 | 0.841 | 0.8577 | 0.1497 |
| 5 | 0.846 | 0.841 | 0.8561 | 0.1509 |
| 6 | 0.846 | 0.841 | 0.8561 | 0.1509 |
| 7 | 0.846 | 0.841 | 0.8577 | 0.1500 |
| 8 | 0.846 | 0.841 | 0.8546 | 0.1512 |
| 9 | 0.846 | 0.841 | 0.8561 | 0.1502 |
| 10 | 0.846 | 0.841 | 0.8577 | 0.1510 |
| seeds 1-10 mean / min / max | 0.846 / 0.846 / 0.846 | 0.841 / 0.841 / 0.841 | 0.8563 / 0.8546 / 0.8577 | 0.1506 / 0.1497 / 0.1515 |

**What it means:** the 0.846 accuracy and the 75% result are **seed-robust**.
- Every seed gives the same 55/65 classifications.
- AUC varies only between 0.855 and 0.858, and Brier between 0.150 and 0.152.

### Test 4: per province (65 development rows)

| Province | n | LOW rows | E49 accuracy | E49 LOW recall | E49 Brier | Persistence accuracy | Persistence LOW recall | Persistence Brier |
|---|---|---|---|---|---|---|---|---|
| Cavite | 13 | 1 | 0.769 | 1/1 | 0.209 | 0.923 | 1/1 | 0.077 |
| Laguna | 13 | 3 | 0.769 | 3/3 | 0.201 | 0.846 | 3/3 | 0.154 |
| Quezon | 13 | 5 | 0.923 | 5/5 | 0.079 | 0.846 | 5/5 | 0.154 |
| Rizal | 13 | 0 | 0.923 | 0/0 | 0.080 | 1.000 | 0/0 | 0.000 |
| Batangas | 13 | 3 | 0.846 | 1/3 | 0.185 | 0.769 | 1/3 | 0.231 |

**What it means:** E49 is not better than persistence everywhere.
- Better in Quezon and Batangas.
- Worse in Cavite, Laguna and Rizal (Rizal has no LOW quarter).
- It catches the same LOW quarters as persistence in every province (Batangas 1 of 3 for both).
- So the region-level "below persistence" finding comes from Cavite, Laguna and Rizal.

### Test 5: calibration, C0 (raw) vs C2 (10 equal-width bins, 65 rows; date bootstrap B = 2,000, seed 62)

| Bin | C0 n | C0 mean p | C0 observed HIGH | C2 n | C2 mean p | C2 observed HIGH |
|---|---|---|---|---|---|---|
| 0.0-0.1 | 9 | 0.050 | 0.333 | 9 | 0.050 | 0.333 |
| 0.1-0.2 | 3 | 0.157 | 1.000 | 2 | 0.154 | 1.000 |
| 0.2-0.3 | 0 | - | - | 1 | 0.220 | 1.000 |
| 0.3-0.4 | 1 | 0.320 | 1.000 | 1 | 0.389 | 1.000 |
| 0.4-0.5 | 7 | 0.421 | 0.429 | 5 | 0.400 | 0.200 |
| 0.5-0.6 | 3 | 0.509 | 1.000 | 5 | 0.508 | 1.000 |
| 0.6-0.7 | 3 | 0.641 | 1.000 | 3 | 0.628 | 1.000 |
| 0.7-0.8 | 3 | 0.764 | 1.000 | 3 | 0.748 | 1.000 |
| 0.8-0.9 | 8 | 0.878 | 0.875 | 15 | 0.862 | 0.933 |
| 0.9-1.0 | 28 | 0.979 | 0.964 | 21 | 0.916 | 0.952 |

| | ECE | 95% CI |
|---|---|---|
| C0 (raw) | 0.146 | 0.103-0.268 |
| C2 (served) | 0.197 | 0.113-0.294 |
| C2 - C0 | +0.051 | -0.034 to +0.076 |

Note: the earlier audit (`e57/paper_alignment_final.md`) reported ECE 0.156 / 0.178 with right-closed bins. This pre-registered [lo, hi) binning gives 0.147 / 0.197; the difference is the bin-edge convention (e.g. p = 0.40 exactly).

**What it means:** C2's higher ECE (+0.051) is not distinguishable from no change (95% CI -0.034 to +0.076).
- With 65 rows, the data cannot show whether C2 improves or worsens calibration error.
- Its justification rests on the slightly lower Brier and log loss, not on ECE.

**Nothing is adopted or served.**
