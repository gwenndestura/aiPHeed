# E165 result: shrink-only score calibration of AUTO (one locked run)

- **Protocol and code:** locked at commit `bb7f9e51` before the run.
- **Output:** `backend/data/e165/out/results.json` and `oof.csv`.

## Decision
**Not adopted.** C4 still fails at Lead 1, so the maximum reliable lead stays **0**. AUTO stays the release candidate and E158 stays the thesis model. No live forecast was sealed.

## Checks
- **Reproduction:** recomputed `mu_AUTO` equals E164's committed values (max difference 4.4e-16). The run is valid.
- **Class identity:** every HIGH/LOW class is identical to AUTO, as designed.

## The shrink factor learned from training rows
| Outer issue | Source | b | Selected configuration |
|---|---|---|---|
| 2018, 2019 (Leads 1–4) | inner region folds (one round, 2015) | 0.949 | OH + ElasticNet + GOV |
| 2021, Leads 1–2 | temporal, 2015→2018 and 2015+2018→2019 | 0.904 | RSS + ElasticNet + FULL |
| 2021, Leads 3–4 | temporal, 2018 only | 1.181, clipped to 1.0 | RSS + RandomForest + FULL |

## Lead 1 (72 rows)
| | AUTO | CAL |
|---|---|---|
| Accuracy | 79.2 % | 79.2 % (identical classes) |
| Brier | 0.1223 | 0.1224 (CAL − AUTO +0.0001 [−0.0012, +0.0012]) |
| Calibration slope 95 % | [0.51, 0.88] | **[0.56, 0.94]**, still excludes 1 |
| Mean error, logit | [+0.03, +0.20] | [+0.04, +0.21] |
| 90 % range coverage | 0.861 | 0.875 |
| Criteria | C4 fails | **C4 fails** |
| Rows predicted 0.4–0.6 | 22, observed HIGH 18 % | 22, observed HIGH 18 % |

Leads 2–4 give the same picture: C4 fails at every lead for both AUTO and CAL.

## Why it failed
1. **The training rows cannot see the overconfidence.**
   - Inside the training rows the scores are close to calibrated: b is 0.95 from region folds, and 0.90 from the only temporal check available.
   - On the outer rows the slope is about 0.7.
   - The overconfidence appears only when a model forecasts a **new survey round**, and at the 2018 and 2019 issues there is only one earlier round to learn that from.
2. **The middle-band problem is a level bias, not a spread problem.**
   - Rows scored near the 50 line are over-predicted: mean error interval above 0, and 18 % observed at a predicted 50 %.
   - Shrinking toward the line cannot move those rows. Correcting a level bias needs an intercept, which moves the HIGH line and changes classes. E156 tried that, and it lost accuracy and Brier.

## What would change this
- **Another survey round in training,** so that drift between rounds can be learned before forecasting. This needs a provincial HFIAS round after 2021.
- **Scoring of the sealed forecasts** (`cbfb61dc`) once a 2027 outcome exists.

Further calibration variants on these 72 rows would be tuning on the test rows and are not run.
