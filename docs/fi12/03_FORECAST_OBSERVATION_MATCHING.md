# Deliverable 3. Forecast-to-observation matching dataset

**FI12** · protocol `2949208888f5` locked 2026-11-03T02:31:10+00:00 · Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file.

**Rule.** For province p, reference year Y and lead L, a model's score is the mean of its out-of-sample quarterly scores
whose target quarter lies in calendar year Y and that were issued L quarters ahead. Every contributing forecast was
issued before its target quarter began (asserted in `match.py`). Survey **reference years** are used, never publication
years. ENNS values are matched province by province to their own year. "Partial" = fewer than four quarters.

**Files.** `backend/data/fi12/out/forecast_observation_matches.csv` (1070 outcome × model-score rows; every
outcome record appears, with no model where none exists) and `model_scores_by_reference_year.csv`.

## Models with provincial forecasts
| model | file | column / config | what it is |
|---|---|---|---|
| P0H4 | aipheed-backend-aligned\experiments\LEAD2_FIVE_TRIGGER\out\asof_reeval_rows.csv | P0H4_p | served P0H4 (T43c probability); file of LEAD2 as-of re-evaluation |
| P0H4_price | aipheed-backend-aligned\experiments\LEAD2_FIVE_TRIGGER\out\asof_reeval_rows.csv | P0H4_price | P0H4 price part pi_P |
| CR | aipheed-backend-aligned\experiments\LEAD2_FIVE_TRIGGER\out\asof_reeval_rows.csv | CR_p | CR candidate |
| CR-ANC | aipheed-backend-aligned\experiments\LEAD2_FIVE_TRIGGER\out\asof_reeval_rows.csv | CRANC_p | CR-ANC candidate |
| P0H4-U | aipheed-backend-aligned\experiments\LEAD2_FIVE_TRIGGER\out\candidates.csv | P0H4U_p | P0H4-U (schedule B) |
| UNI-FINAL | aipheed-backend-aligned\experiments\FINAL_UNIFIED_LGBM\out\predictions.csv | UNI_p | unified LightGBM x hunger term |
| CH1-LGBM | aipheed-backend-aligned\experiments\FINAL_UNIFIED_LGBM\out\predictions.csv | CH1-LEAD_p | per-lead LightGBM x hunger term |
| E108 | aipheed-backend-aligned\experiments\E108_Best_Defensible_Forecasting\out\predictions_T43_lead1.csv | F1_p | E108 factored LightGBM (Lead 1 only) |
| FI10_L1sel | backend/data/fi10/out/predictions.csv | LightGBM regression (tuned) | FI10 locked Lead-1 selection |
| FI10_L2sel | backend/data/fi10/out/predictions.csv | Ensemble: mean of ridge (partial pooling) and LightGBM regression | FI10 locked Lead-2 selection |
| FI10_damped | backend/data/fi10/out/predictions.csv | Damped persistence | FI10 damped persistence of price pressure |
| FI10_naive | backend/data/fi10/out/predictions.csv | Naive persistence | FI10 naive persistence of price pressure |

## Coverage
| model|lead | reference years matched |
|---|---|
| CH1-LGBM · L1 | 2023 |
| CH1-LGBM · L2 | 2023 |
| CR · L1 | 2023 |
| CR · L2 | 2023 |
| CR · L3 | 2023 |
| CR · L4 | 2023 |
| CR-ANC · L1 | 2023 |
| CR-ANC · L2 | 2023 |
| CR-ANC · L3 | 2023 |
| CR-ANC · L4 | 2023 |
| E108 · L1 | 2023 |
| FI10_L1sel · L1 | 2015, 2018, 2019, 2021, 2023 |
| FI10_L1sel · L2 | 2015, 2018, 2019, 2021, 2023 |
| FI10_L1sel · L3 | 2015, 2018, 2019, 2021, 2023 |
| FI10_L1sel · L4 | 2015, 2018, 2019, 2021, 2023 |
| FI10_L2sel · L1 | 2015, 2018, 2019, 2021, 2023 |
| FI10_L2sel · L2 | 2015, 2018, 2019, 2021, 2023 |
| FI10_L2sel · L3 | 2015, 2018, 2019, 2021, 2023 |
| FI10_L2sel · L4 | 2015, 2018, 2019, 2021, 2023 |
| FI10_damped · L1 | 2015, 2018, 2019, 2021, 2023 |
| FI10_damped · L2 | 2015, 2018, 2019, 2021, 2023 |
| FI10_damped · L3 | 2015, 2018, 2019, 2021, 2023 |
| FI10_damped · L4 | 2015, 2018, 2019, 2021, 2023 |
| FI10_naive · L1 | 2015, 2018, 2019, 2021, 2023 |
| FI10_naive · L2 | 2015, 2018, 2019, 2021, 2023 |
| FI10_naive · L3 | 2015, 2018, 2019, 2021, 2023 |
| FI10_naive · L4 | 2015, 2018, 2019, 2021, 2023 |
| P0H4 · L1 | 2023 |
| P0H4 · L2 | 2023 |
| P0H4 · L3 | 2023 |
| P0H4 · L4 | 2023 |
| P0H4-U · L1 | 2023 |
| P0H4-U · L2 | 2023 |
| P0H4-U · L3 | 2023 |
| P0H4-U · L4 | 2023 |
| P0H4_price · L1 | 2023 |
| P0H4_price · L2 | 2023 |
| P0H4_price · L3 | 2023 |
| P0H4_price · L4 | 2023 |
| UNI-FINAL · L1 | 2023 |
| UNI-FINAL · L2 | 2023 |
| UNI-FINAL · L3 | 2023 |
| UNI-FINAL · L4 | 2023 |

**Consequence.** Only FI10 (food-price pressure) has historical provincial forecasts for 2015, 2018, 2019 and 2021. Every
P0H4-family model (P0H4, P0H4-U, CR, CR-ANC, UNI-FINAL, CH1-LGBM, E108) starts at target quarter 2023-Q1, so the only
outcome it can be matched to is **PSA food poverty 2023 (five values)**. No P0H4-family forecast exists for any direct
food-insecurity observation; none can be reconstructed without information that was not available then.

The served P0H4 Lead-1 2023 scores in the matching file equal `backend/data/ch1_engine/rows.csv` exactly.

## Not matchable
| model | why not matchable |
|---|---|
| FI7 | regional SWS Balance Luzon forecast: one value for all five provinces |
| FI9 C0 | regional SWS Balance Luzon forecast: one value for all five provinces |
| FI11 | regional SWS Balance Luzon forecast: one value for all five provinces |
| FIRI v2 / FIRI3 | an index, not a forecast; no saved out-of-sample provincial history before 2021 (FIRI3 prospective only) |
| E56-TUNED / E83 / E93 | T43 targets 2023-Q1+ only; superseded by the P0H4 family files above |

## Example rows (PSA 2023, served P0H4, Lead 1)
| province | reference_year | value | model | lead | first_issue | last_issue | score | coverage |
|---|---|---|---|---|---|---|---|---|
| Batangas | 2023 | 0.80 | P0H4 | 1 | 2022-Q4 | 2023-Q3 | 0.21 | full |
| Cavite | 2023 | 0.40 | P0H4 | 1 | 2022-Q4 | 2023-Q3 | 0.21 | full |
| Laguna | 2023 | 0.80 | P0H4 | 1 | 2022-Q4 | 2023-Q3 | 0.22 | full |
| Quezon | 2023 | 0.50 | P0H4 | 1 | 2022-Q4 | 2023-Q3 | 0.18 | full |
| Rizal | 2023 | 1.50 | P0H4 | 1 | 2022-Q4 | 2023-Q3 | 0.22 | full |
