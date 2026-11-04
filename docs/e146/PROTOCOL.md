# E146: quarterly survey-anchored forecast of provincial food insecurity. Protocol E146-P1

Locked before any E146 result is computed (`backend/data/e146/out/PROTOCOL_LOCK.json`). A smoke run may execute the code first to catch crashes. It prints and saves no metric.

All HFIAS rows here were seen by E137 to E144, so results are development evidence, never "validated".

## 1. Quarterly forecast

For province p and target quarter T:

    logit(p_pT) = alpha + gamma * logit(H_area,T) + delta * r_p + s_pT

| Part | What it carries | Learned from | Model |
|---|---|---|---|
| `H_area,T` | Quarter-to-quarter movement common to the SWS area | Quarterly SWS hunger, 4 areas | E144 Stage A LightGBM level forecast at lead h |
| `r_p` | The province's lasting position | Earlier survey rounds | E143 C4: cross-fitted LightGBM + hierarchical anchor |
| `alpha, gamma, delta` | The link between scales | Earlier survey rounds | E144 weighted link |
| `s_pT` | Province-specific shock in that quarter | **Real survey rows only** | LightGBM on link residuals, with a learned option of no shock |

**Why not train on estimated quarterly labels.** A label estimated between surveys contains no province-specific movement over time, because that movement is exactly what was not measured. A model trained on such labels can only reproduce the interpolation. Province-specific shocks are therefore learned only where a survey measured them.

## 2. Timing

The issue date of lead h is the first day of the quarter h quarters before the target quarter. In Q4 2026, Lead 1 is Q1 2027. Leads 1 to 4 are evaluated, since Stage A forecasts four horizons. A value is used only if published before the issue date.

## 3. Correction to E144

E144's end-to-end check fed the link 2013 provincial estimates trained on later rounds, which is look-ahead. E144's locked decision stays on record, but its H-E2E pass is not treated as clean. Here, `r_p` for training rows is the out-of-fold level from a model fitted only on rounds before the target (`E2E-clean`).

## 4. Inputs to the shock model (province, as of the issue date)

* `c_soil_anom_3m`: NASA POWER root-zone soil wetness (GWETROOT), mean of the 3 months ending 2 full months before the issue date, as a standardised anomaly against the same months of 2000 to 2009, at the province centroid.
* From E137, unchanged: `c_rain_anom_6m`, `c_tc_4q`, `c_agri_yoy`, `c_fish_yoy`.
* News arm only, from E145: `nb_fssi`, `nb_attention`, `nb_fssi_delta`.

Settings: E140 `GBC` parameters and tree grid, fixed. Inside each training set, region-grouped folds compare the trees with a zero shock. Trees are used only if their weighted error is lower.

## 5. Target and class

* **Target.** Measured HFIAS moderate-or-severe prevalence by province, on the 125 rolling rows (2015, 2018, 2019), from `app.e144.link`.
* **HIGH.** Prevalence above 42.8 %, the pooled national ENNS 2018-2019 value used in E144. `q*` is the probability of this given sampling error. Decisive rows: |logit(p) − logit(0.428)| > 1.645 × SE.
* **Sensitivity (reported, never used to select).** The same rows relative to each round's national value. For CALABARZON, a within-region ranking, because no province there has measured above national.

## 6. Arms and baselines (identical rows)

| Arm | Definition |
|---|---|
| E2E-clean | Area forecast + link + `r_p`, no shock |
| QS | E2E-clean + shock model with soil, rain, typhoon, production |
| QS-nosoil | QS without soil (the soil ablation) |
| QS-N | QS + news |
| C4-link | Link without gamma (no time signal) |
| B1 PERS | Naive persistence of the previous round (E144 form) |
| B2 LR-PSA | Soft logistic, poverty indicators |
| B3 LR-NLP | Soft logistic, news only |
| B4 LR-ALL | Soft logistic, government + news |

## 7. Evaluation

**Metrics, per lead and arm:** accuracy with Wilson interval, precision, recall, F1, AUC-ROC, false-alarm rate and confusion matrix on decisive rows. Expected Brier (EB) and ECE on all rows. By origin. CALABARZON rows listed. Region-cluster bootstrap, 2000 draws, seed 146.

**Time points.** Three origins exist. A second bootstrap resamples area x round cells for the difference from C4-link, because that is the unit at which a time signal is identified.

**Reliability at lead h (all required):** R1 accuracy ≥ 0.75. R2 AUC ≥ 0.70, interval lower bound > 0.50. R3 recall and precision ≥ 0.50. R4 EB below persistence, 95 % interval below 0. R5 ECE ≤ 0.10. R6 Spearman between predicted and measured change from the previous round, interval lower bound > 0.

**Maximum reliable lead:** the largest h with every lead up to h passing, for the selected arm. It is 0 if lead 1 fails.

**Selection, fixed here.** Default arm: E2E-clean. QS replaces it only if QS minus E2E-clean has a 95 % EB interval below 0 at lead 1. QS-N replaces the current arm only if its difference has a 95 % interval below 0 at lead 1.

**Time-signal claim.** Requires the arm minus C4-link to have an interval below 0 under both bootstraps.

## 8. FIES bridge (agreement only)

The 2019 ENNS decks print HFIAS and FIES for the same areas. Spearman on `enns_hfias.csv` rows with both values, with a bootstrap interval. The bridge is usable for updating live estimates only if the lower bound exceeds 0.50. FIES is never a training label here. 2021 and 2023 FIES values have been seen, so they are direction checks, not tests.

## 9. Quarterly output

One table per province and quarter, each row marked **measured**, **estimated** or **forecast**:

* Measured: a survey round.
* Estimated: past quarters with no provincial measurement. Never scored as accuracy.
* Forecast: issued quarters, sealed by hash.

Each row carries an interval.

## 10. Limits stated in advance

* Province-quarter accuracy exists only in surveyed quarters.
* Quarter-to-quarter movement is largely shared within an SWS area, and Balance Luzon is wider than CALABARZON.
* The time signal rests on 12 area-round cells.
* No CALABARZON row is above national, so high-risk recall cannot be tested there under this class.
* Production and the dashboard are not changed by E146.
