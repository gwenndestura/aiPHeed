# aiPHeed simple methodology (branch `aipheed/simple-methodology`)

Status: **proposed, not deployed.** The production dashboard is unchanged. Evidence: `backend/data/simple_method/evaluation.json`
(protocol `aipheed-backend-aligned/experiments/E106_Simple_Methodology/PROTOCOL.md` and `ADDENDUM_1.md`, both frozen before scoring).

## In one sentence

Every quarter, aiPHeed forecasts, for each CALABARZON province, the probability that food-insecurity risk will be HIGH one and two
quarters ahead, using only data already published, explains which factors drove the forecast, and ranks the 142 cities and municipalities.

## What "HIGH risk" means (Chapter I §1.7)

A province-quarter is HIGH when two things happen together:

1. **Hunger is high:** SWS Balance Luzon involuntary hunger is above 11.3% (its 2021–22 usual level), and
2. **Food prices are under pressure in the province:** food inflation, or food inflation minus overall inflation, is above the
   province's 2021–22 usual level (PSA CPI).

## Workflow

| Stage | What happens | In | Out |
|---|---|---|---|
| 1. Collect | Fetch PSA CPI, rice prices, harvests, labour, BSP remittances, PAGASA advisories, typhoon tracks, SWS hunger, news headlines | Public sources | Raw tables and headlines |
| 2. Clean and organise | Put every series on province-quarters, record each value's publication date | Raw tables | One dated table per source |
| 3. Prepare indicators | Compute the indicators the model uses, cutting each at the issue date; score headlines with XLM-RoBERTa and build FSSI-v3 | Dated tables, headlines | Indicator row per province and origin |
| 4. Train | Fit one LightGBM on past rows whose outcome was already published | Indicator rows, past labels | Trained model |
| 5. Forecast | Predict Lead 1 (next quarter) and Lead 2 (two quarters ahead) | Today's indicator row | P(HIGH) and HIGH/LOW per province |
| 6. Explain | SHAP values of the model, grouped into the five triggers | Model, today's row | Driver bars per province |
| 7. Display | Map, province card, drivers, news, LGU ranking (province P(HIGH) × poverty and density weight) | Forecast, explanation | Dashboard |
| 8. Evaluate | Compare forecasts with what actually happened, every quarter, against the four Chapter I baselines | Sealed forecasts, outcomes | Accuracy, recall, Brier, AUC |

## The model

One forecast of P(HIGH), answering the two parts of the definition and multiplying them:

- **Hunger part:** a small regional regression of SWS hunger on the latest published SWS reading and indicators (the E46 "I7"
  component, `backend/data/e56/model/hunger.json`).
- **Price part:** a LightGBM that gives the chance of provincial food-price pressure from the latest CPI (including a projection of
  food inflation for the target months), rice prices, harvests, jobs, remittances, El Niño status, typhoons and news.

HIGH if P(HIGH) ≥ 0.5. This is the production model (E56-TUNED); the redesign keeps it as the single forecasting model and removes
the FIRI composite from the forecast path.

Two simpler versions were tested on the same rows:
- **SM** (a re-built LightGBM using only quarterly CPI in the repository, times the latest SWS reading) failed (AUC 0.44–0.47): the
  monthly CPI projection carries the price signal, and that monthly series is not in the repository.
- **SM-B** (the production price part times the latest SWS reading as the hunger part) matched E56 at Lead 1 (accuracy 0.782, Brier
  0.167) and had a slightly lower Brier at Lead 2 (0.181 vs 0.192), but its Lead-2 accuracy (0.711) missed the frozen 0.75 rule.

## Lead 1 and Lead 2

Both are issued on day 1 of a quarter with the same procedure. Lead 1 forecasts the quarter just started; Lead 2 the quarter after.
Only data published before the issue date are used; the model is retrained at every issue date on outcomes already published.

## Results (rolling origin, Chapter I target, identical rows; development evidence)

| | Lead 1 (55 rows, 11 quarters) | Lead 2 (45 rows, 9 quarters) | Lead 3 (40 rows, 8 quarters) |
|---|---|---|---|
| LightGBM (E56) accuracy / bal. acc. / AUC / Brier | 0.764 / 0.731 / 0.819 / 0.167 | **0.756** / 0.726 / 0.703 / 0.192 | 0.600 / 0.564 / 0.575 / 0.273 |
| HIGH recall / LOW recall | 0.65 / 0.82 | 0.63 / 0.83 | 0.46 / 0.67 |
| Naive persistence accuracy | 0.727 | 0.578 | 0.550 |
| Always-LOW accuracy | 0.691 | 0.644 | 0.675 |
| Current headline FIRI v2 accuracy (Lead 2 rows) | — | 0.333 (calls 93% HIGH) | — |

Furthest reliable lead (accuracy > 0.75, above persistence and always-LOW, both recalls ≥ 0.5): **Lead 2**.

## Limitations

The target labels were rebuilt from repository data and agree with the served labels on 37 of 45 rows; every result uses quarters
already examined; the outcome's hunger part is regional; FNRI NNS 2019/2023 anchors and ISO 25010 responses are not in the project.
