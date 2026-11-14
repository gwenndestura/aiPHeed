# Food Insecurity Risk (%): methodology and implementation (2026-11-14)

Branch `aiPHeed/food-insecurity-risk-relabel`, from production `origin/main` 9b4d2b62. Not committed or deployed.

## 1. What food insecurity risk means here
**Food insecurity risk** of a province in a forecast quarter is the probability that a randomly selected household in the province is
moderately or severely food insecure (FNRI Household Food Insecurity Access Scale, HFIAS) in that quarter, given the information published
before the issue date.

This is risk in the epidemiological sense, the probability of the outcome for a member of the population in a period. It is the same
construction FAO uses for SDG 2.1.1: the prevalence of undernourishment is defined as the probability that a randomly selected individual
consumes less than the minimum dietary energy requirement, estimated from a probability distribution rather than a headcount. HFIAS
measures the FAO **access** dimension of food security (Coates, Swindale and Bilinsky 2007). The model's inputs cover availability (harvests),
access (prices, jobs, regional income) and stability (weather, typhoons) as drivers; HFIAS does not measure utilisation.

It is not the probability of HIGH, not a share of provinces, and not an arbitrary score: it is a probability of a defined household-level
outcome, and it is what FINAL's training target (the provincial HFIAS moderate+severe proportion) estimates.

## 2. What the backend served before
`riskScore = sigmoid(mu)`, with mu the 5-seed mean forecast log-odds of the provincial HFIAS proportion (`app/final/serving.py::_served_rows`,
`score_pct / 100`). That is the **median** of the forecast distribution of the proportion. It is a forecast of household prevalence, but
it ignores the forecast's own uncertainty, so it is not the probability for a random household.

## 3. Method and formula
FINAL's forecast distribution: `logit(P) ~ Normal(mu, sd^2)`, where `mu` and `sd` are the model's own outputs (sd is FINAL's forecast-error
scale for the elapsed time, `app.e164.auto.scale`; stored per province and quarter as `sd_mean` in `shap_live_summary.csv`).

By the law of total probability:

    Food insecurity risk = E[P] = integral of sigmoid(z) * Normal(z; mu, sd^2) dz      (Gauss-Hermite quadrature, 64 nodes)

**Classification:** HIGH RISK when risk >= 50%. Because the normal is symmetric and `sigmoid(-z) = 1 - sigmoid(z)`, `E[P] >= 0.5` exactly when
`mu >= 0`, so every class is identical to FINAL's validated class (P(HIGH) >= 0.5). The threshold is FNRI's own "half of households" line.

No model, training, input, threshold or issue file changed. This is the correct expectation of the model's existing predictive distribution, not a rescaling.

## 4. Real example: Quezon, Jan–Mar 2027 (issue 2026-11)
| Quantity | Value |
|---|---|
| mu (anchor -0.716 + expected change -0.477 + inputs +0.186) | -1.0065 |
| sd (forecast-error scale, 30 quarters since the survey) | 0.411 |
| Old served value, sigmoid(mu) | 26.8% |
| **Food insecurity risk, E[P]** | **27.5%** |
| Probability of HIGH (not displayed) | 0.7% |
| Class | LOW |

## 5. API before and after (2027-Q1)
| Province | Before (live) | After |
|---|---|---|
| Quezon | 0.268 low | 0.275 low |
| Rizal | 0.246 low | 0.254 low |
| Cavite | 0.243 low | 0.251 low |
| Laguna | 0.237 low | 0.244 low |
| Batangas | 0.232 low | 0.240 low |
| CALABARZON (mean of provinces) | 0.2452 | 0.2528 |

Town priority uses the province risk as its multiplier: Lipa 0.1608 -> 0.1663; ranks unchanged (1 in Batangas, 35 in the region).

## 6. Walk-forward validation (no refit; ENNS 2018, 2019, 2021; 72 province-rounds per lead)
`docs/food_insecurity_risk/validate_risk.py` -> `walk_forward_results.json`, `walk_forward_rows.csv`. Observed value = the survey's HFIAS
moderate+severe proportion. Household Brier and log loss treat the risk as a probability for every household of the province.

| Lead 1 | MAE (pp) | RMSE (pp) | Bias (pp) | Household Brier | Household log loss | Class accuracy |
|---|---|---|---|---|---|---|
| **Food insecurity risk E[P]** | **7.54** | **9.15** | -0.27 | **0.2408** | **0.6748** | 0.861 |
| Old value sigmoid(mu) | 7.73 | 9.43 | -0.51 | 0.2414 | 0.6761 | 0.861 |
| Persistence (latest survey) | 11.16 | 13.85 | +9.51 | 0.2517 | 0.6979 | 0.625 |

Lead 2: risk MAE 7.87 / RMSE 9.69 vs old 8.20 / 10.06 vs persistence 11.16 / 13.85. By round (Lead 1 MAE): 2018 7.18, 2019 7.81,
2021 7.60 (persistence 11.09, 8.83, 13.56). Every class agrees with FINAL's (`class_agrees_with_mu_sign` true).

The 2021 folds chose linear/Platt calibration, so their sd is not stored; the 2019 fold's sd was used. Sensitivity (sd 0.40 or 0.70):
Lead-1 MAE 7.61 or 7.44, so conclusions do not depend on it.

## 7. Files modified
- `backend/app/final/risk.py` (new): `expected_risk`, `risk_from_record`.
- `backend/app/final/serving.py`: `issue_risks`, `_served_rows` (served value = risk), outlook `risk_pct`, confidence statement.
- `backend/app/final/shap_api.py`: `riskPct` in payloads; summary sentences use it.
- `backend/app/final/report.py`, `report_data.py`: PDFs and Visualization report use `risk_pct`.
- `backend/app/api/v1/final_realtime.py`: `risk_pct` in `/final/forecast-history`.
- `backend/app/ml/inference/hcw_system.py`: headline sentence uses the risk.
- `frontend/src/components/LeftPanel.tsx`, `FinalShapExplanation.tsx`, `ForecastHistoryModal.tsx`, `lib/apiTypes.ts`, `lib/finalShap.ts`.
- Tests: `backend/tests/unit/test_final_realtime.py` (`test_served_food_insecurity_risk_is_the_expected_household_risk`,
  `test_expected_risk_function`; visualization test now compares with `risk_pct`).
- Plus the earlier wording-only relabel ("forecast share" -> "food insecurity risk") on the same branch.

## 8. Tests
Backend FINAL tests: 60 passed, 1 skipped, 1 failed (`test_corrected_forecast_regenerates_exactly`: needs the gitignored raw news file
`data/e155/raw/sunstar.parquet`; fails the same way on unmodified main). Frontend: 106/106 passed; typecheck clean.

## 9. Limitations
- Retrospective validation only (72 province-rounds from rounds also examined during development); only 5 CALABARZON rows, all LOW.
- HFIAS measures access; it is the only provincial food-insecurity measurement with history, so the risk is about access-type food insecurity.
- The risk is for the province as a whole; city and municipal values remain priority scores, not risks.
- Observed survey proportions carry sampling error (published 90% CIs), which inflates the measured MAE.
- HIGH detection remains weak in 2021 (1 of 4), unchanged by this step.

## Sources
- FAO, SDG indicator 2.1.1 Prevalence of undernourishment, methodology: https://www.fao.org/fileadmin/templates/ess/documents/apcas25/APCAS-14-8.2-PoU-Method.pdf
- World Bank SDG metadata 2.1.1: https://worldbank.github.io/sdg-metadata/phase-2/metadata/en/2-1-1
- Cafiero, Viviani & Nord (2018), Food security measurement in a global context: the FIES, Measurement 116: https://microdata.fao.org/index.php/citations/5
- Coates, Swindale & Bilinsky (2007), HFIAS Indicator Guide v3, FANTA: https://www.fantaproject.org/monitoring-and-evaluation/household-food-insecurity-access-scale-hfias
