# E147: forecasting food-insecure households on FNRI's public-health scale, with a sealed test on the 2021 round. Protocol E147-P1

Locked before any E147 result is computed and before any 2021 value is read. Lock: `backend/data/e147/out/PROTOCOL_LOCK.json`.

**Sealed labels.** File `backend/data/e147/raw/sealed_2021_labels.csv`, SHA-256 `f15a1977b8c5d5b6c1385890482eed4815351c2afce609dcab33421e09ce4ef5`. Only its area names have been printed. Exceptions: the 2021 FIES decks for Batangas, Cavite and Lucena were read on 2026-11-04, but they use a different instrument, so the HFIAS values remain unread. Its use is one final scoring run, after predictions are sealed.

## 1. Why this differs from E145 and E146

| Failure in E145/E146 | Cause | Correction here |
|---|---|---|
| No HIGH case in CALABARZON | Class defined as above the national level | FNRI's published cut-offs for food-insecure households |
| Four provinces with one forecast | The hierarchical anchor gave the province component zero weight, and the structural level is flat within the region | LightGBM learns the change from each province's own last survey |
| Nothing beat persistence | Models reproduced geographic differences | Target is change, with regression to the mean and time signals as inputs; persistence is the starting point |
| No untouched test | Every label had been seen | ENNS 2021 HFIAS, sealed |
| Decorative trigger groups | Employment and remittances were not model inputs | All five groups are inputs; resolution is disclosed per group |
| Thin news | One outlet, to April 2019 | Four outlets where they answer, to the 2021 issue date |

This does not repeat E145/E146 with new settings: target, class, learning problem and test data all change.

## 2. Target

* **Measure.** Food Insecure Households (any-level HFIAS, 30-day recall): `y = logit(p)`. FNRI methodology: HFIAS was used in 2013, 2015 and ENNS 2018, 2019 and 2021.
* **Published scale, FNRI Heat Map.** Very Low < 20, Low 20 to 39.9, Medium 40 to 59.9, High 60 to 79.9, Very High ≥ 80.
* **HIGH.** p ≥ 60, FNRI's own "High" or above. This cut-off was fixed by FNRI, not by this study. Sensitivity reported, not selected: the five-band scale and moderate-or-severe prevalence.
* **Not targets.** Prices, inflation, poverty, SWS hunger, news, FIES, or estimated quarters. Radimer/Cornell 2011 (3-month recall) is a predictor only.

The target's weakness is stated here: a fixed cut-off on a survey-to-survey series with a downward trend makes base rates shift between rounds.

## 3. Rows and evaluation

| Stage | Train (target, previous survey) | Test | Rows |
|---|---|---|---|
| Dev O2 | 2015 from 2013 | 2018 | 22 (seen) |
| Dev O3 | 2015, 2018 | 2019 | 25 (seen) |
| **Final** | 2015, 2018, 2019 | **2021, sealed** | Provinces among the sealed areas with inputs: 25 listed in `label_audit.json` |

Survey reference quarter: Q3 of the survey year. Cities have no provincial inputs, so they are not scored. They are listed as a limitation.

**Timing.** Lead h issue date = first day of the quarter h quarters before the target. Lead 1 for 2021-Q3 is issued on 2021-04-01. Leads 1 to 4 are evaluated. A value is used only if published before the issue date. Release rules: `app/e147/features.py`.

## 4. Inputs, by trigger group

| Group | Inputs | Resolution |
|---|---|---|
| Market and prices | Food and rice CPI year on year (annual, stale to the 2018 value by 2021); food threshold | Province |
| Climate stress | Soil moisture anomaly, rain anomaly, cyclones within 150 km, ONI; palay, corn and fisheries production | Province; ONI national |
| Employment | Unemployment rate and its change | **National only** in this history |
| OFW remittances | Remittances year on year | **National only** in this history |
| Poverty and vulnerability | Poverty, subsistence, poverty gap, density | Province, by release round |
| News (feeds the groups above) | FSSI, attention, within-province change, topic shares | Province |
| History | Own last survey, gap, distance from region's latest mean, Radimer 2011, SWS area change since the last survey | Province or area |

No share of influence is forced. Groups with no province variation cannot separate provinces, and this is reported.

## 5. Models

**Primary learner: LightGBM on change.** `dy = y − y_previous`, E140 `GBC` parameters, tree count chosen inside training folds by region-grouped error. Forecast = previous value + predicted change. P(HIGH) = Φ((forecast − logit 0.60) / σ), with σ from out-of-fold residuals in training.

| Arm | Inputs |
|---|---|
| G | History + five groups |
| GN | G + raw news |
| GNB | G + bias-corrected news |
| N | News only (LightGBM on `y`) |
| DRIFT | Previous value + training mean change |
| B1 PERS | Naive persistence of the last survey |
| B2 LR-PSA | Logistic, poverty indicators |
| B3 LR-NLP | Logistic, news only |
| B4 LR-ALL | Logistic, all inputs |

**Selection, on development rows only.** Primary = G. GNB replaces G only if its pooled O2 + O3 Brier difference at lead 1 has a 95 % region-bootstrap interval below 0.

**Sealing.** All arms and leads are predicted, written to file and hashed before the sealed labels are opened.

## 6. Reliability on the 2021 test (all required, per lead)

| Check | Requirement |
|---|---|
| R1 | Accuracy ≥ 0.75 |
| R2 | AUC ≥ 0.70 |
| R3 | HIGH recall ≥ 0.50 and precision ≥ 0.50 |
| R4 | Brier below persistence, region-bootstrap 95 % interval below 0 |
| R5 | ECE not above the 95th percentile expected under perfect calibration at this n (simulated, seed 147). Fixed ECE cut-offs are unsuitable at n near 25 |
| R6 | Spearman of predicted and measured change, interval lower bound > 0 |

**Maximum reliable lead:** the largest h with every lead to h passing; 0 if lead 1 fails. Accuracy above 75 % alone is never reported as success. Always-HIGH, always-LOW and base rates are reported beside it.

**News claim.** Requires GNB − G on 2021 at lead 1 with interval below 0, and real news better than at least 95 % of 30 wrong-province placebo draws.

**Differentiation.** On 2021: Spearman of forecast and measured values, overall and within Luzon. Live: spread across the five provinces against the forecast standard error.

**Quarterly evidence.** Surveys measure provinces only in survey quarters. A number for any other quarter is never called validated. The SWS area test (E144) is reported as the only quarterly measured test.

## 7. Limits stated in advance

* One final test round, about 25 rows, in one pandemic year. A pass is one strong result, not proof of stability.
* HFIAS ends in the Heat Map at 2021. Later FNRI rounds reviewed print FIES.
* SE is not published in the Heat Map. Where it is needed for 2021, the mean 2018 to 2019 province SE is used, flagged.
* Sentiment accuracy has no local labelled check, by the owner's rule. Attribution and convergent validity are audited instead.
* Production and the dashboard are not changed by E147.
