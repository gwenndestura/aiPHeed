# E48: why province risk scores barely change across quarters

**Branch:** `e46-lead2-policy`, after E47. **Date:** 2026-10-17. E38, E46, E47 and every frozen forecast are unchanged.

## Answer

| Question | Finding |
|---|---|
| Is there a serving, cache, join or frontend defect? | **No.** Each displayed score equals the stored model probability for every province and quarter in both modes. The stored probabilities are the fitted models' own outputs. |
| Where do the scores stop moving? | In the **production default (E38)**, the score is the LightGBM probability of the **v1 label** (S1 = SWS hunger + 2 × the province's food-price deviation; HIGH when S1 > trailing median). |
| Why? | Hunger has been 14–25% since 2023-Q4, so the label is HIGH in **46 of 50** province-quarters. The model learned that base rate, a baseline of +2.0 to +2.7 log-odds (about 0.88–0.94). |
| Result | **90% of E38 scores since 2025-Q4 are ≥ 0.95.** |
| What drives E38 at all? | Its next-quarter model splits on only 3 of its 6 inputs: D_last 22 splits, Dnow 20, H_margin 18; H_trend, news and FSSI have none. Moved one at a time across their full 2023–2026 range, those inputs keep the probability between **0.70 and 0.95**, in 2–4 tree steps. It cannot output LOW for current conditions. |
| Is that a bug? | No. It is the target: the model accurately reproduces a label that is almost always HIGH. |
| Do the corrected model's scores move? | **Yes.** The corrected T43 model (`e46`, I7) changes with every issue date. Quezon goes 0.253 → 0.546 → 0.852 → 0.281 → 0.146 over 2026-Q1..2027-Q1, and no `e46` score since 2025-Q4 is ≥ 0.95. |
| Fix applied | No artificial change. A defensible correction is to make the corrected model the default. That **changes the production default, which needs your authorization**, so it was not done. |

## 1. Source-to-screen trace (E38, the production default)

1. **Target and issue date:** the record (`data/e36/e36_record.json`) stores, for each quarter, the origin, lead, information cutoff and the model's probability `p_high`.
   - 2026-Q4: lead 1, issued 2026-10-01, by the E36 model.
   - 2027-Q1: lead 2, issued 2026-10-01, by the E38 model.
   - Earlier quarters: E36 one-quarter-ahead backtests.
2. **Inputs per province and quarter:** stored as TreeSHAP drivers with values.
   - D_last and Dnow are provincial food-CPI deviations.
   - H_margin and H_trend are the regional SWS hunger inputs, identical for all provinces.
   - news_reg and fssi_v2 are news signals.
3. **Model:** the archived boosters, `data/e36/model/E36-LGBM_O2026-10-01.txt` and `E38-LGBM-NQ_O2026-10-01_lead2.txt` (feature order checked).
4. **Probability:** `sigmoid(base + Σ contributions)` equals `p_high` for every row, maximum difference 5e-5. The E38 booster plus its stated prior shift reproduces 2027-Q1 to 1e-6.
5. **Post-processing:** none beyond the documented prior shift. No cache, override or aggregation changes the value.
6. **API:** `e31_engine.forecast_quarter` passes `p_high` through unchanged.
7. **Frontend:** the map and cards show `riskScore`, the same value.

## 2. Scores by quarter (API values, `runs/api_scores_by_quarter.json`; full table with inputs in `runs/score_change_table.json`)

**E38, production default (v1 label probability):**

| Quarter | Issue | Batangas | Cavite | Laguna | Quezon | Rizal |
|---|---|---|---|---|---|---|
| 2023-Q1 | backtest | 0.400 | 0.400 | 0.400 | 0.400 | 0.400 |
| 2023-Q2 | backtest | 0.945 | 0.945 | 0.047 | 0.047 | 0.945 |
| 2023-Q3 | backtest | 0.507 | 0.507 | 0.031 | 0.031 | 0.705 |
| 2023-Q4 | backtest | 0.785 | 0.873 | 0.081 | 0.081 | 0.873 |
| 2024-Q1 | backtest | 0.904 | 0.055 | 0.055 | 0.055 | 0.852 |
| 2024-Q2 | backtest | 0.864 | 0.181 | 0.924 | 0.127 | 0.924 |
| 2024-Q3 | backtest | 0.616 | 0.513 | 0.162 | 0.899 | 0.616 |
| 2024-Q4 | backtest | 0.527 | 0.297 | 0.832 | 0.954 | 0.527 |
| 2025-Q1 | backtest | 0.736 | 0.491 | 0.958 | 0.974 | 0.491 |
| 2025-Q4 | backtest | 0.996 | 0.999 | 0.999 | 0.999 | 0.995 |
| 2026-Q1 | backtest | 0.993 | 0.999 | 1.000 | 0.998 | 1.000 |
| 2026-Q2 | backtest | 0.649 | 0.965 | 0.979 | 0.968 | 0.973 |
| 2026-Q3 | backtest | 0.995 | 0.984 | 0.999 | 0.995 | 0.985 |
| 2026-Q4 | 2026-10-01, lead 1 | 0.169 | 0.983 | 0.989 | 0.986 | 0.981 |
| 2027-Q1 | 2026-10-01, lead 2 | 0.801 | 0.952 | 0.952 | 0.952 | 0.952 |

**e46, corrected T43 probability:**

| Quarter | Issue | Batangas | Cavite | Laguna | Quezon | Rizal |
|---|---|---|---|---|---|---|
| 2024-Q2 | 2024-01-01 | 0.161 | 0.195 | 0.173 | 0.208 | 0.203 |
| 2024-Q3 | 2024-04-01 | 0.056 | 0.128 | 0.477 | 0.597 | 0.026 |
| 2024-Q4 | 2024-07-01 | 0.157 | 0.057 | 0.086 | 0.956 | 0.002 |
| 2025-Q1 | 2024-10-01 | 0.413 | 0.573 | 0.479 | 0.986 | 0.276 |
| 2025-Q4 | 2025-07-01 | 0.286 | 0.170 | 0.460 | 0.395 | 0.024 |
| 2026-Q1 | 2025-10-01 | 0.390 | 0.185 | 0.240 | 0.253 | 0.242 |
| 2026-Q2 | 2026-01-01 | 0.056 | 0.242 | 0.395 | 0.546 | 0.468 |
| 2026-Q3 | 2026-04-01 | 0.066 | 0.449 | 0.064 | 0.852 | 0.095 |
| 2026-Q4 | 2026-07-01 (earlier forecast) | 0.055 | 0.025 | 0.013 | 0.281 | 0.001 |
| 2027-Q1 | 2026-10-01 (frozen) | 0.039 | 0.061 | 0.051 | 0.146 | 0.030 |

**Unchanged consecutive scores:**
- **Exactly identical:** 0 in either mode.
- **Change < 2 percentage points, E38:** Cavite 3/14 (21%), Laguna 4/14 (29%), Quezon 3/14 (21%), Rizal 3/14 (21%), Batangas 1/14 (7%). All of them fall in the saturated stretch from 2025-Q4 onward.
- **Change < 2 percentage points, e46:** Cavite 1/9, Laguna 1/9, Quezon 0/9, Rizal 0/9, Batangas 3/9.

**Ties across provinces (E38):** 2027-Q1 is 0.9521 for four provinces and 2023-Q1 is 0.4000 for all five. These are LightGBM leaf steps: different inputs fall in the same leaves. In 2023-Q1, the first fit had no split, so every province got the baseline.

## 3. Quarter-specific inputs

| Trigger | E38 (production) inputs | Varies by quarter? | By province? | Enters inference? |
|---|---|---|---|---|
| Market and prices | D_last, Dnow (provincial CPI deviation) | yes | yes | yes (42 splits) |
| Climate | none | – | – | no; shown as "not used in this forecast" |
| Fisheries | none | – | – | no |
| Employment | none | – | – | no |
| OFW remittances | none | – | – | no |
| Hunger (target input) | H_margin, H_trend (SWS) | yes, except when no new approved round was posted (2025-Q4 and 2026-Q1 share the 2025-Q1 round) | no (regional) | H_margin only (18 splits) |
| News | news_reg, fssi_v2 | yes | partly | no (0 splits) |

**The corrected model (`e46`)** uses all five trigger groups plus policy and news, with an issue-date cutoff audit (E47). Each past quarter's five-group attribution comes from the model refitted at that quarter's issue date (E47).

## 4. Controlled diagnostics (`runs/sensitivity_e38_nq.json`; synthetic inputs, not forecasts)

On the served E38 next-quarter booster (60 trees), each input was moved across its 2023–2026 range while the others stayed at each province's 2027-Q1 values:

| Input | Probability range | Distinct outputs |
|---|---|---|
| H_margin | 0.920–0.952 (Cavite) | 2 |
| D_last | 0.891–0.952 | 3 |
| Dnow | 0.907–0.952 | 4 |
| H_trend, news_reg, fssi_v2 | no effect | 1 |

- **Batangas:** 0.700–0.907.
- **Preprocessing** removes no variation: the inputs arrive with their quarter values.
- **The model itself is insensitive,** because its training labels are almost all HIGH.

## 5. Changes made in E48

**No model, API or frontend change was needed for the score path**; no defect was found. I did not add artificial variation, and I did not change the production default.

**Added:**
- `runner/e48_api_scores.py`, `e48_change_table.py`, `e48_sensitivity.py`, and their outputs in `runs/`.
- `backend/tests/integration/test_e48_score_variation.py` (6 tests):
  - API = record for every quarter and province;
  - record = the model's log-odds;
  - the E38 booster reproduces 2027-Q1 in feature order, and responds to price inputs;
  - regional vs provincial inputs joined by quarter and province;
  - the hunger input is unchanged only where SWS has no new round;
  - no exact consecutive repeats;
  - the `e46` scores change with each issue date and match the API.

## 6. Tests and live check

| Suite | Result |
|---|---|
| Backend: `backend/venv/Scripts/python.exe -m pytest -q` (from `backend/`) | **367 passed, 18 skipped** |
| E48 tests | 6 passed |
| Frontend: `npx vitest run` (from `frontend/`) | **45 passed** |

**Live** (API in `e46` mode on 8001, merged tutorial frontend on 8082):
- the dashboard opens on Q1 2027 with the guided tour ("Step 1 of 10");
- the province scores served for 2026-Q1..2027-Q1 match the `e46` table above.

## 7. Model performance (unchanged by E48; no model was refitted)

**Production E36 one-quarter-ahead model, v1 label** (65 rows, 13 quarters, nested rolling origin):

| Arm | Accuracy | Balanced | Precision | Recall | F1 | AUC | Brier |
|---|---|---|---|---|---|---|---|
| E36 LightGBM | **0.815** | 0.822 | 0.956 | 0.811 | 0.878 | 0.850 | 0.154 |
| Persistence | 0.877 | | | | | | 0.123 |
| Always-HIGH | 0.815 | | | | | | |

- **The E38 next-quarter (Lead-2) model:** 0.709.
- **Corrected T43 Lead-2 model (`e46`, I7), development only:**

| Accuracy | Balanced | HIGH recall | LOW recall | Brier | AUC |
|---|---|---|---|---|---|
| 0.800 | 0.684 | 0.44 | 0.92 | 0.174 | 0.735 |

**75% with meaningful HIGH/LOW discrimination is not met** under any target or lead.

## 8. Decision needed

To make the dashboard's default scores respond to quarterly conditions, the production default would switch from E38 (saturated v1 label) to the corrected T43 model (`e46`). That model is experimental: development accuracy 0.800, HIGH recall 0.44, not independently validated. **This needs your explicit authorization**; it was not done.
