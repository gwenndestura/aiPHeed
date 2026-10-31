# E130 overfitting analysis

## Status

**No model was trained** (the gate is BLOCKED), so there are no train-versus-validation errors, seed runs or importance-stability results to report. This file sets out:
- the capacity problem any provincial model would face on today's data;
- the checks the protocol fixes for a future run.

## Capacity: predictors against observations

| Quantity | Value |
|---|---|
| Candidate predictors (`E130_PROVINCIAL_FEATURE_AVAILABILITY.csv`) | 39: 27 provincial quarterly, 2 provincial annual, 10 shared or static |
| Provincial reference values (PFDR v1) | 10 |
| Independent provincial changes | 5 |
| Predictors per independent change | **7.8** |
| Effective rows in a 5-province quarterly CPI panel | 28.8 of 115, because 74.7 % of food-CPI variance is common to all provinces in a quarter |

**Any supervised model on the survey-year target would have more predictors than observations.** LightGBM with the protocol's smallest leaf (min_child_samples = 5) could make at most one split on 5 rows. E130 therefore did not fit it (protocol §7).

## What the data say about memorization risk

| Risk | Evidence | Severity |
|---|---|---|
| **Period markers** | 14 of 27 provincial predictors have more than 70 % of their variance in the common quarter effect (median 0.71). A tree model can use them to recognise *when* rather than *where*. On the regional target, E128's SHAP showed ONI acting as a period marker. | High |
| **Province identity** | Only 0.9 % of food-CPI variance is a persistent province effect, so CPI barely identifies provinces. FSSI v3 is 90 % persistent province effect: it mostly encodes which province, not what changed. | Medium |
| **Target-history regimes** | One province (Quezon 2021) carries 83 % of the squared change in the reference. A model fitted to it would mostly learn that one event. | High |
| **Inflation regimes** | The 2022–2023 food-price surge coincides with the only observed round-to-round change. Price level and period cannot be separated with one interval. | High |

## Regional evidence already on record (E128, not re-run)

On the 20-quarter regional target, E128 found:
- severe overfitting with 25 features on 6–18 training rows;
- regime-shift false negatives;
- LightGBM beating no baseline.

**A provincial survey-year target has fewer independent changes (5) than E128 had training rows.**

## Checks fixed for a future run (protocol §5, §8)

- Training and out-of-sample MAE, RMSE and R² per fold.
- The spread of error across walk-forward origins.
- Seeds 130–134 (sensitivity).
- Number of trees with splits.
- Rank stability of SHAP importance across folds.
- Late unseen periods reported separately.
- Province-level against pooled results.
- A province-held-out supplement.
