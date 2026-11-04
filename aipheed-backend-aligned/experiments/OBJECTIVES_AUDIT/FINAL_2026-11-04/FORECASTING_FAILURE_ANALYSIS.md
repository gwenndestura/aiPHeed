# Forecasting failure analysis (why C-E2 fails R3 and R7)

**Data:**
- `out/obj2_error_level.csv`: one row per lead × verdict quarter (124 rows). Columns: origin, lead, p, predicted and
  actual class, |p − 0.5|, observed H and its distance from 11.3, rounds, P(true HIGH), uncertain-label flag, label
  change, third, inputs available, error category, and the C-b / LOGIT / persistence probabilities.
- `out/obj2_label_uncertainty.json`, `out/obj2_diagnostics.json`.
- **Scripts:** `runner/obj2_label_uncertainty.py`, `runner/obj2_diagnostics.py` (analysis only; nothing fitted).

## 1. Survey-label uncertainty (separating model error from label noise)

**SWS design:** Balance Luzon has 600 respondents per round, ±4% (SWS Q3 2026 release, in the repository). The quarter
label is the mean of its rounds, so its sampling SE is √(H(1−H)/(600·r)). n = 300 is a sensitivity scenario for older
rounds. Simple random sampling is assumed and design effects are ignored, so the true SE is larger.

| | Lead 1 | Lead 2 |
|---|---|---|
| Labels with P(true HIGH) between 0.10 and 0.90 (n = 600 / 300) | 13 / 20 of 62 | 13 / 20 of 62 |
| Accuracy ceiling of a perfect forecaster of true hunger (n = 600 / 300) | **0.925 / 0.897** | 0.925 / 0.897 |
| C-E2 accuracy on certain labels | 0.857 | 0.796 |
| C-E2 accuracy on uncertain labels | **0.462** | 0.615 |

**Errors by category** (rules fixed in the script; the first matching category wins):

| Category | Lead 1 | Lead 2 |
|---|---|---|
| Label-uncertain | **7 of 14** | 5 of 15 |
| Label change | 3 | 4 |
| Regime 2015–2020 | 3 | 4 |
| Other | 1 | 2 |

**Brier against the hard labels vs the sampling-probability (soft) labels.** This is analysis only; the soft labels
are never used for training.

| | C-E2 | C-b | LOGIT | Persistence |
|---|---|---|---|---|
| Lead 1 hard / soft | 0.188 / 0.128 | 0.187 / 0.130 | 0.193 / **0.122** | 0.339 / 0.265 |
| Lead 2 hard / soft | 0.188 / 0.136 | 0.184 / **0.133** | 0.234 / 0.186 | 0.339 / 0.276 |

**Reading:**
- About half of the Lead-1 errors are on labels that SWS's own sampling error could flip.
- On soft labels, LOGIT is slightly better than C-E2 at Lead 1. Their difference is within the label noise.

## 2. Regime change (R7)

| Third | Share HIGH | C-E2 L1 accuracy | C-E2 LOW recall | C-b | LOGIT | Persistence |
|---|---|---|---|---|---|---|
| 2010-Q1..2015-Q1 | 0.95 | 0.952 | 0 of 1 | 0.952 | 1.000 | 0.905 |
| 2015-Q2..2020-Q4 | **0.48** | **0.524** | 0.36 | 0.571 | 0.381 | 0.429 |
| 2021-Q2..2026-Q3 | 0.65 | 0.850 | 0.71 | 0.850 | 0.750 | 0.650 |

**Every model fails the middle third.** After 12 years of mostly-HIGH hunger, the series fell below the line about half
the time.

## 3. Bias, calibration and transitions (R3)

- **HIGH bias:** the mean p on LOW quarters is 0.60 (0.73 on HIGH). LOW recall is 0.474 (9 of 19).
- **Calibration (Lead 1):** forecasts of 0.3–0.5 came true 0.31 of the time (mean p 0.42). Forecasts of 0.5–0.7 came
  true 0.87 of the time (mean p 0.61): under-confident. 0.7–0.85: 0.63 (mean p 0.79). 0.85–1.0: 0.89 (mean p 0.88).
- **Transitions:** on the 13 quarters whose label changed, accuracy is 0.462; on repeats it is 0.857. A label change is
  hard to see from inputs dominated by the last SWS reading (about 60% of SHAP).

## 4. Other causes checked

| Cause | Finding |
|---|---|
| Feature coverage | 21–22 of 22 inputs available at every scored origin; not a cause |
| National-to-regional mismatch | E1 and E2 are national and together carry 5.1% of SHAP (Lead 2). C-b, without them, passes R3 (0.717) and still fails R7. So the national series cost about 0.03 balanced accuracy (part of it from averaging vs selecting) and do not cause R7 |
| Class imbalance | 69% HIGH. Balanced class weights are in the averaged grid; recency and calibration fixes made it worse |
| Survey methodology | Sample sizes changed over time (older rounds possibly n = 300), which widens label uncertainty early on |
| Sample size | 62 quarters, 21 per third. One quarter moves a third's accuracy by 0.048, so R7 is decided by 1–2 quarters (S1 passed R7 by one forecast) |

## Conclusion

The R3/R7 failures come from four sources:
1. survey-label noise near 11.3% (irreducible by any model);
2. one regime change in 2015–2020 that every model misses;
3. a history-driven HIGH bias;
4. too few quarters to separate a real improvement from one flipped call.

Five pre-registered fixes (S1, C-E3, C-E4, C-E5R, C-E5C) failed to pass R3/R7 with a supported improvement. No further
fit on these 62 quarters is justified (`EXPERIMENT_REGISTRY.md`).
