# Five provincial forecasts

Full traceable record per province: `backend/data/e150/out/issue/province_trace.json`. All leads: `issue/five_province_forecasts.csv`. Series: `issue/quarterly_series.csv`. Seal of these forecasts, for later scoring: `issue/sealed_forecast_2027-Q1.json`, SHA-256 `f773fbff…`.

**Status: research candidate, not validated, not deployed. Issue date 2026-10-01. Target Q1 2027 (Lead 1).**

## Forecast table

| Province | Latest measured (HFIAS any-level) | A-H forecast | 90 % interval | P(HIGH ≥ 50) | Class | A-G (uses all five groups) | Risk score B (not %) |
|---|---|---|---|---|---|---|---|
| Quezon | 61.9 (2019) | 39.8 | 23.3 to 59.0 | 0.18 | LOW | 49.8 | 61.2 |
| Rizal | 56.6 (2019) | 37.0 | 21.3 to 56.1 | 0.13 | LOW | 50.5 | 74.4 |
| Cavite | 50.2 (2021) | 36.7 | 21.0 to 55.8 | 0.12 | LOW | 42.4 | 56.5 |
| Laguna | 39.3 (2018) | 35.0 | 19.9 to 54.0 | 0.09 | LOW | 42.9 | 57.0 |
| Batangas | 56.9 (2021) | 34.5 | 19.5 to 53.4 | 0.08 | LOW | 37.4 | 70.1 |

## Please do not use these numbers operationally yet

1. **The A-H values are probably too low.** They fall 13.5 to 22.4 points below the latest measurements in four provinces (Laguna only 4.3), partly from the poverty double-count described in `METHODOLOGY_REDESIGN.md`. The post-hoc correction gives 40.2 to 43.7. FIES did fall in this period (CALABARZON 19.1 % in 2023), but that is a different instrument and doesn't confirm these values.
2. **All five intervals include 50 %.** No class is firm.
3. **Models disagree.** Rizal is LOW under A-H but HIGH under A-G. That disagreement is itself the honest message.
4. **No pair of provinces is separated:** 0 of 10 pairs exceed their uncertainty. Batangas forecasts below Laguna although it last measured 17.6 points higher.

## Why the provinces differ (model arithmetic, not causes)

Logit contributions, A-H.

| Province | Shared level | Structural level | Measured deviation after shrinkage | Main structural inputs (SHAP) |
|---|---|---|---|---|
| Quezon | +0.048 | −0.341 | −0.122 | Poverty −0.084, gap −0.104, Radimer −0.150 |
| Rizal | +0.048 | −0.507 | −0.072 | Poverty −0.231, gap −0.100, Radimer −0.146 |
| Cavite | +0.048 | −0.531 | −0.061 | Poverty −0.240, gap −0.109, Radimer −0.152 |
| Laguna | +0.048 | −0.493 | −0.173 | Poverty −0.226, gap −0.106, Radimer −0.142 |
| Batangas | +0.048 | −0.504 | −0.186 | Poverty −0.230, gap −0.106, Radimer −0.152 |

**Quezon ranks highest because its poverty term is much less negative** (about 0.15 logit, consistent with its 18 % poverty against 6 to 10 %). The other four are nearly the same on structure, which is why they barely separate.

## Five trigger groups at the issue date

| Province | Food CPI y/y | Rice CPI y/y | Cyclones, 4Q | Soil anomaly | Poverty (logit) | Quarters since survey |
|---|---|---|---|---|---|---|
| Quezon | 3.5 | 20.0 | 1 | −2.09 | −2.18 | 30 |
| Rizal | 2.0 | 17.7 | 1 | −2.11 | −2.38 | 30 |
| Cavite | 1.5 | 20.4 | 1 | −1.81 | −2.63 | 22 |
| Laguna | 2.2 | 6.2 | 1 | −2.11 | −2.46 | 34 |
| Batangas | 0.1 | 9.0 | 1 | −2.18 | −2.50 | 22 |

Employment and remittances are the same for every province, because the history is national. Rain is **missing** live, and regional unemployment is missing at this issue date in the file used. CPI is current at its release rule. Full values and news indicators are in the trace file.

**Rice CPI (6 to 20 % year on year) is a real, current stress signal, which A-H doesn't use.** It enters only through the quarterly response signal and the A-G residual, where its SHAP share is small, and the survey-fitted loading on that signal is 0 at this issue.

## Quarterly movement

| Arm | Mean absolute quarter change | Mean spread across provinces | Province co-movement |
|---|---|---|---|
| A-H | 0.9 to 1.2 points | 10.4 points | 0.88 |
| A-Hh | 1.0 to 1.3 | 10.4 | 0.89 |
| **A-G** | **2.4 to 2.8** | **17.0** | 0.72 |

Part of that movement in the backtest comes from new survey releases and model refits, not only input changes. A-G's series moves by province. For example, in 2026 Q1 to Q4, Rizal goes 52.9, 50.5, 50.3, 50.4, and Batangas 41.0, 38.1, 38.0, 37.7. Its movement has **not** been validated against a provincial measurement.

## Separation of evidence

The trace file keeps these apart: (1) officially measured values, (2) observed government indicators, (3) NLP-derived indicators, (4) model forecast and its parts, (5) calibrated probability. LGU rankings (6) are in a separate file. **SHAP values describe the model and are not causal proof.**

## Performance by province

CALABARZON measured rows in the tests are few: Laguna 2018, Quezon and Rizal 2019, Batangas and Cavite 2021 at Lead 1, each once.

| Row | Measured | A-H P(HIGH) | Result | Persistence P | E149 P |
|---|---|---|---|---|---|
| Laguna 2018 | 39.3 LOW | 0.46 | Correct | 0.59 (wrong) | 0.61 (wrong) |
| Quezon 2019 | 61.9 HIGH | 0.77 | Correct | 0.77 | 0.87 |
| Rizal 2019 | 56.6 HIGH | 0.40 | **Wrong** | 0.61 | 0.52 |
| Batangas 2021 | 56.9 HIGH | 0.50 | Correct, barely | 0.67 | 0.38 (wrong) |
| Cavite 2021 | 50.2 HIGH | 0.51 | Correct, barely | 0.66 | 0.38 (wrong) |

A-H gets 4 of 5 right, with several close to 0.50. Five rows can't establish provincial reliability.
