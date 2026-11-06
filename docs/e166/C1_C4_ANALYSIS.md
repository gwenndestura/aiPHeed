# Why E166 fails C1 and C4, and whether they can be fixed (diagnosis, 2026-11-06)

Sources: E166's saved out-of-sample forecasts, `data/e166/out/c1_c4_diagnosis.json` and `c4_chronological_recalibration.json`. **The criteria were not changed. No model was refitted.**

## C1: accuracy margin over the majority rule
**Rule:** the lower 95 % bound of accuracy at the effective sample size must exceed the always-LOW rate. Effective n = 72 / (1 + 0.8 × 0.726) = 45.5 independent rows, and always-LOW = 65.3 %.

| Lead | Correct | Lower bound | Needed to pass | Result |
|---|---|---|---|---|
| 1 | 55 / 72 (76.4 %) | 64.1 % | **56 / 72** | **Fails by one forecast** |
| 2 | 57 / 72 (79.2 %) | 67.4 % | 56 / 72 | Passes |

- **C1 is a sample-size limit, not a model defect.** Errors are shared within a region and round, so 72 forecasts carry the evidence of only about 46.
- **One more correct forecast at Lead 1 would pass it.** Each new provincial survey round adds about 25 rows, which narrows the interval.

## C4: calibration slope
**Rule:** the 95 % interval of the slope of observed on predicted (logit scale) must include 1.

**E166 Lead 1:** slope 0.74 [0.53, 0.87]. A slope below 1 means the predictions vary more than the outcomes do.

| Component | Slope | What it shows |
|---|---|---|
| 2018 alone | 1.15 | Good |
| 2019 alone | 0.91 | Good |
| **2021 alone** | **0.62** | **Over-dispersed:** provinces predicted too far apart |
| Within rounds (round means removed) | 0.87 [0.71, 0.97] | Close, but the interval just misses 1 |
| Round-level offsets | 18 % of error variance | |

Round means of predicted vs observed:

| Round | Predicted | Observed | Error |
|---|---|---|---|
| 2018 | 54.2 | 47.4 | **+6.8** |
| 2019 | 54.6 | 49.2 | **+5.4** |
| 2021 | 39.6 | 41.6 | **−2.0** |

**Two causes:**
1. **The error changes sign between rounds.** E166 was too high in 2018 and 2019 (it could not see the 2015→2018 national fall) and too low in 2021. Across rounds, predictions therefore swing more than the outcomes (predicted 54→40, observed 47→42), which pulls the pooled slope below 1.
2. **2021 is over-dispersed within the round** (slope 0.62). 2018 and 2019 were not.

## Test: can a correction learned from earlier rounds fix it? (chronologically valid)
A recalibration y = a + b·mu fitted on the 2018 and 2019 out-of-sample forecasts gives a = −0.26, b = 1.02. Applied to 2021:

| 2021 | Before | After recalibration |
|---|---|---|
| Accuracy | 80 % | 88 % |
| Mean error | −2.0 points | **−7.9 points** |
| Slope | 0.62 | **0.61** (unchanged) |
| Brier | 0.098 | **0.106** (worse) |

- **It fails.** The earlier rounds teach "predict lower", but 2021 needed the opposite. And the 2021 spread problem never appeared in 2018 or 2019, so it cannot be learned from them.
- The higher 2021 accuracy comes with a worse probability score and bias. **It is not a fix.**

## Conclusion
| Criterion | Status | Can it be fixed with existing data? |
|---|---|---|
| C1, Lead 1 | One forecast short | Only with more rows (a new survey round) |
| C1, Lead 2 | Passes | n/a |
| C4, all leads | Fails | **No.** Its causes are round-specific and change sign. A correction learned from past rounds made 2021 worse. Fitting the calibration on the test rounds themselves would be circular |

**What would fix both:**
1. **A new FNRI provincial HFIAS round.** It adds about 25 rows for C1 and a fourth round from which round-to-round calibration can be learned for C4.
2. **A national-level signal available at the issue date** that tracks how the HFIAS level moves between rounds. None exists in the project: SWS hunger moved in the opposite direction in 2020–2021.

**Recommended disclosure:** "C1 is missed by one forecast at Lead 1 and met at Lead 2. C4 is not met because forecast errors shifted direction between survey rounds (over-prediction in 2018–2019, under-prediction in 2021), which cannot be corrected without additional survey rounds."
