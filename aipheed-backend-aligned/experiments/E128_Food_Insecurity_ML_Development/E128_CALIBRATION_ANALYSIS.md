# E128 calibration analysis

**Source.** `out/calibration_bins.csv` (5 probability bins, outer rows), plus Brier in `E128_LEAD_1_TO_4_COMPARISON.csv`.

**Brier score** is the mean squared difference between the forecast probability and the 0/1 outcome:
- 0 is perfect;
- 0.25 is a constant 0.5 forecast;
- lower is better.

It rewards honest probabilities, not just correct classes.

## LightGBM reliability table (T1)

| Lead | Bin | n | Mean probability | Observed HIGH share |
|---|---|---|---|---|
| 1 | 0.0–0.2 | 4 | 0.12 | **1.00** |
| 1 | 0.2–0.4 | 3 | 0.30 | 0.33 |
| 1 | 0.6–0.8 | 4 | 0.75 | 1.00 |
| 1 | 0.8–1.0 | 1 | 0.88 | 1.00 |
| 2 | 0.8–1.0 | 7 | 0.91 | 1.00 |
| 3 | 0.4–0.6 | 4 | 0.56 | 1.00 |
| 4 | 0.0–0.2 | 4 | 0.07 | **1.00** |

## Brier by model (T1)

| Lead | LightGBM | Persistence | CLIM | PSA-only | NLP-only | LR |
|---|---|---|---|---|---|---|
| 1 | 0.332 | **0.154** | 0.294 | 0.305 | 0.235 | 0.311 |
| 2 | 0.082 | **0.000** | 0.334 | 0.077 | 0.097 | 0.039 |
| 3 | 0.208 | **0.000** | 0.302 | 0.478 | 0.116 | 0.219 |
| 4 | 0.704 | **0.000** | 0.256 | 0.571 | 0.249 | 0.904 |

## Brier by model (T4)

| Lead | LightGBM | Persistence | CLIM | PSA-only | NLP-only | LR |
|---|---|---|---|---|---|---|
| 1 | 0.207 | 0.182 | 0.306 | **0.156** | 0.220 | 0.276 |
| 2 | 0.395 | 0.500 | **0.306** | 0.378 | 0.415 | 0.379 |
| 3 | 0.521 | 0.286 | 0.294 | 0.548 | **0.241** | 0.352 |
| 4 | 0.526 | 0.333 | 0.301 | 0.561 | **0.250** | 0.609 |

## Findings

**Calibration is not acceptable.**
- At T1 Leads 1 and 4, LightGBM gives probabilities below 0.2 to quarters that were all HIGH.
- Its Brier is **worse than climatology** at Leads 1 and 4 (0.332 vs 0.294; 0.704 vs 0.256).

**Persistence has the lowest T1 Brier at every lead.** That is a property of the saturated target, not skill: a 0/1 call is perfect while the class never changes.

**Under T4, no model beats both persistence and climatology at Leads 2–4.** PSA-only has the best T4 Lead-1 Brier (0.156). It beats CLIM (one-sided bootstrap p 0.043) but is not significantly better than persistence (p 0.42), so R5 fails; n = 11.

**Recalibration was not attempted.** Fitting a calibrator needs held-out rows the folds do not have (6–18 training rows). Fitting it on outer rows is forbidden. Earlier E53 and LEAD2 C5 calibrations made Brier worse.
