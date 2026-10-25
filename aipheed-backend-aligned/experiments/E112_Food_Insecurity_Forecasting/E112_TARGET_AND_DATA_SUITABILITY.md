# E112 Target and data suitability assessment

## 1. What "food insecurity" can be measured with in 2021–2026

| Candidate outcome | Measures food insecurity? | Level | Frequency 2021+ | In the project? | Usable as the forecast target? |
|---|---|---|---|---|---|
| **SWS Total Hunger** (involuntary hunger, past 3 months) | **Yes**: experienced hunger, a severe food-insecurity indicator | Balance Luzon (includes CALABARZON); NCR, Visayas, Mindanao | Quarterly (20 BL quarters 2021-Q2..2026-Q3) | Yes (E109 `outcome_rounds.csv`, E110 `sws_area_rounds.csv`) | **Yes: the only one** |
| PSA FIES (moderate/severe food insecurity) | Yes | National / regional | Annual or less often; not a quarterly series | No | No: too few points for walk-forward evaluation |
| DOST-FNRI ENNS / NNS food-security estimates | Yes | Regional, some provincial | About every 2–3 years | No (E87 request drafted, not sent) | No as a target; useful for validation |
| PSA CBMS 2024 food-security items | Yes | City/municipal, barangay | One round | No (E87 request drafted, not sent) | **Validation of municipal rankings only** |
| PSA poverty incidence (SAE 2021, FIES-based poverty) | No (poverty, not food insecurity) | Province / municipal | Triennial | Yes (V1) | No: a vulnerability weight |
| Food CPI / T43 price pressure (E56–E108) | **No** (price pressure) | Province | Monthly | Yes | **No** (discontinued as the outcome, see the decision record) |
| FIRI v2 composite | No (composite risk proxy, not observed) | Province, LGU | Quarterly | Yes (served) | No: never validated against an outcome |

**Decision.** The forecast target is **SWS Total Hunger for Balance Luzon** (continuous, in percent).
- **Primary rule:** non-commissioned rounds (E109).
- **Generalization panel:** the four SWS areas, used for the panel candidate and E111's panel methods.

## 2. Suitability of the SWS series

| Property | Assessment | Consequence |
|---|---|---|
| **Construct** | Direct measure of experienced hunger | Valid outcome for "food insecurity" in the severe range |
| **Spatial fit** | Balance Luzon is all of Luzon outside Metro Manila; CALABARZON is one of its regions | **A regional forecast, not a CALABARZON, provincial or municipal one** |
| **Length** | 20 BL quarters (2021-Q2..2026-Q3; 2022-Q1 and 2025-Q1 have no round) | 5–9 evaluable quarters per lead after the minimum training window (E109 rule: ≥ 8 pairs) |
| **Noise** | ±4 points (BL, 95%); E111 estimates noise as 17–100% of quarterly change variance | Small true changes are not separable from sampling noise |
| **Timeliness** | Published after the survey quarter ends; for example, 2026-Q3 was published on 2026-10-14 and 2025-Q4 on 2026-01-14 | At an issue date the newest reading is usually 1 quarter old, so Lead 1 = true horizon 2 (E111 `horizon_table.csv`) |
| **Comparability** | Respondent base changed from household heads to adults in 2025; level shift detected (E111, p = .0008) | Mixed regimes inside 20 quarters; the HH sensitivity rule is reported |
| **Binary readings** | Every evaluated BL quarter is above 11.3% (E109: lead-1 B1 has 9 of 9 HIGH) | Accuracy, precision, recall, F1 and AUC of a binary HIGH/LOW class are degenerate (AUC undefined), so the continuous outcome is the primary target |

## 3. The data gap for the 142 cities and municipalities

**No measured food-insecurity outcome exists in the project for any CALABARZON province, city or municipality, for any quarter 2021–2026.** As a result:

- **Forecasts are regional only.** Any provincial or municipal forecast would have to be a regional forecast multiplied by fixed vulnerability weights (poverty, density). Its *differences between places* come only from those weights, never from observed food insecurity. It cannot be validated.
- **The served FIRI v2 LGU ranking** is a vulnerability ranking conditioned on a regional or provincial risk level. Its correct label is "relative vulnerability", not "forecast food insecurity". All 142 LGUs keep the E109 status "INSUFFICIENT LOCAL EVIDENCE" for forecast claims.
- **Data that would close the gap** (none requested or collected under the current no-new-data rule):

| Data | Purpose | Route |
|---|---|---|
| PSA CBMS 2024, LGU-level food-security item aggregates | Cross-sectional validation of the municipal ranking (pre-registered in E79–E82) | E87 request A (draft) |
| DOST-FNRI ENNS 2021–22 / NNS 2023–25, provincial FIES | Provincial calibration | E87 request B |
| SWS microdata with province identifiers | Provincial hunger series | E87 request C |
| Future SWS rounds from 2026-Q4 | Prospective scoring of the sealed forecasts | Public releases |

## 4. Predictor data suitability (12 families + news)

| Family | Level | Missing at Lead-1 evaluation origins | Suitability note |
|---|---|---|---|
| A1 food-price projection, A2 inflation, A3 rice | Province (PSA) | 0% | Timely; price, not hunger |
| V1 vulnerability | Province, static | 0% | Constant over time, so it cannot explain changes |
| C1 El Niño (national), C2 typhoons, C3 crops, C4 fisheries | Mixed | 0% | C3/C4 lag one quarter |
| E1 unemployment, E2 remittances | National | E2 11% | Period markers more than local signals |
| N1 FSSI-v3 | Province | **56%** | Sparse: too few admitted headlines |
| **News category indicators (E112)** | Region (corpus) / CALABARZON (GDELT) | **0%** | Dense; coverage-normalised; de-seasonalised |
| H1 SWS outlook | Region | 0% | Already contains the latest reading |

**Conclusion.**
- The outcome (SWS BL hunger) is valid but short, noisy, late and regional.
- The predictors are timely but mostly about prices and hazards, not hunger itself.
- The data, not the model class, limit what can be shown.
