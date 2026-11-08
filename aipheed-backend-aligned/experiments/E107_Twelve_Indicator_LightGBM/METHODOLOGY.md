# E107 Deliverable B: revised forecasting methodology

**Status:** implemented and evaluated on branch `aipheed/e107-twelve-indicator-lightgbm`. **Not served on the dashboard**, which still shows FIRI v2. The rules are frozen in `PROTOCOL.md` (sha `f652327b…`), `ADDENDUM_1.md` and `ADDENDUM_2.md`. Results are in `EXPERIMENT_REPORT.md`.

## 1. The workflow in one paragraph

Every quarter, on the first day of the new quarter (the **issue date**), aiPHeed builds one row per province. The row holds the 12 indicators as they were published before that day. One LightGBM classifier, trained only on past rows whose outcomes were already published, gives each province a probability that the quarter one, two, three or four quarters ahead will be **HIGH food-insecurity risk**. The same procedure is replayed at every past issue date (rolling origin, expanding window). Each forecast is then compared with what actually happened, against simple baselines, to find the furthest lead at which the forecasts are reliable.

## 2. Workflow table

| Step | What happens | Code |
|---|---|---|
| 1. Load | PSA CPI (monthly index and YoY), PSA production, PSA LFS, BSP remittances, PSA rice prices, IBTrACS typhoons, PAGASA ENSO items, SWS rounds, news headlines. 2021 onward only. | `e41_lib.load`, `e43_lib.load_extra` |
| 2. Cut at the issue date | Drop every value published on or after the issue date O(*t*) | `Data.cut(t)`, `cut_extra`, backend as-of functions |
| 3. Build the 12 indicators | 13 numeric columns (section 3) | `e107_lib.feature_table(k)` |
| 4. Label past rows | T43 (and R) for quarters whose outcome was complete before O(*t*) | `e107_lib.known_labels` |
| 5. Tune and train | Pick 1 of 8 small LightGBM settings by forward validation inside the training rows; refit | `e107_model.select`, `Model` |
| 6. Forecast | P(HIGH) for *t* + 1 … *t* + 4. HIGH if P ≥ 0.5. | `e107_model.run` |
| 7. Explain | TreeSHAP per indicator, summed per indicator and domain | `Model.shap` |
| 8. Evaluate | Rolling origin; the same rows for every model and baseline; reliability rule (section 6) | `run_e107.py` |

## 3. Feature preparation: 12 indicators, 13 columns

Two columns come from indicator A1. All the others are one column each. Full inventory: `INDICATOR_AUDIT.md`.

| Domain | Indicator | Column(s) | Prepared as |
|---|---|---|---|
| Affordability | A1 Food-price-pressure forecast | `A1_food`, `A1_gap` | Projected food YoY (and food − headline YoY) of the target quarter, with the latest published index held flat. Each is minus the province's 2021–22 threshold. |
| | A2 Headline inflation above usual | `A2` | Headline YoY (latest two months) minus the province's 2021–22 P60 |
| | A3 Wholesale rice price change | `A3` | YoY, quarter *t* − 1 |
| Vulnerability | V1 Poverty and density | `V1` | 0.6 poverty + 0.4 density (static) |
| Climate and production | C1 PAGASA El Niño alert/advisory | `C1` | 1/0 at the issue date |
| | C2 Typhoons within 300 km | `C2` | count, quarter *t* |
| | C3 Palay/corn drop | `C3` | −(lower YoY), *t* − 1 |
| | C4 Fisheries drop | `C4` | −YoY, *t* − 1 |
| Household economy | E1 Unemployment change | `E1` | points, *t* − 1 vs *t* − 5 |
| | E2 Remittance decline | `E2` | −YoY, *t* − 1 |
| News | N1 FSSI-v3 | `N1` | Bias-weighted XLM-RoBERTa headline intensity. Missing below 5 headlines. |
| Regional hunger | H1 Hunger outlook | `H1` | P(hunger at the target quarter > 11.3%) from the latest SWS round and its own past errors |

- **Missing values** stay missing. LightGBM routes them natively and nothing is filled with zero.
- **A1** enters as its structural projection, not as the served LightGBM probability. One model's output is never an input of the next.
- **Model-specific columns:** A1 and H1 change with the lead; the other columns do not.

## 4. Target definition

| Name | HIGH when | Level | What it is |
|---|---|---|---|
| **T43 (primary)** | SWS Balance Luzon involuntary hunger > 11.3% **and** the province's food CPI YoY (or food − headline YoY) is above its 2021–22 P60 | province-quarter | The Chapter I §1.7 food-insecurity **risk** definition. A **composite proxy**: one observed food-insecurity measure (regional hunger) combined with one provincial access pressure (prices). It is not a measured provincial prevalence. |
| **R (outcome check)** | SWS Balance Luzon involuntary hunger > 11.3% | region | The only independently observed food-insecurity measure in the project |

Hunger was above 11.3% in every quarter from 2023-Q4 to 2026-Q3. On those rows, T43's variation comes entirely from the price condition. The results are therefore evidence about forecasting **price pressure while hunger is elevated**, not about forecasting hunger itself. R tests hunger itself.

## 5. Training procedure

- **Training rows at issue date O(*t*):** every past row (*t*′, province) whose target quarter *t*′ + *k* is at most *t* − 1 and whose label was complete before O(*t*).
- **When an origin can be trained:** at least 6 target quarters and both classes, as defined in `ADDENDUM_1.md`.
- **Model:** LightGBM, depth 1 or 2, 50 or 150 trees, learning rate 0.05, L2 = 5, class weighting none or balanced. That gives 8 settings.
- **Selection:** the setting with the lowest log loss on the last four training quarters, each predicted from earlier quarters only.
- **No feature selection, no calibration, threshold 0.5.**
- **Exploratory variant SP (`ADDENDUM_2.md`):** the same LightGBM, starting from the structural probability that the definition implies, H1 × P(price above threshold), and learning corrections from the 12 indicators.

## 6. Horizon evaluation and reliability rule

- **Rolling origin** over every issue date from 2021-Q1 to 2026-Q3, for Leads 1–4.
- **Development block:** target quarters before 2025-Q4.
- **Final block:** 2025-Q4 to 2026-Q3. Scored once, after the development results were recorded.
- **Reliable at lead *k*:** all of R1–R7 and G1–G3 in `PROTOCOL.md` §8 hold:
  - ≥ 6 target quarters;
  - accuracy ≥ 0.75;
  - accuracy above persistence and majority;
  - Brier score below persistence and climatology (for R also below H1), with a one-sided quarter-level sign-flip test p < 0.10;
  - both recalls ≥ 0.5;
  - AUC ≥ 0.65;
  - share predicted HIGH between 0.1 and 0.9;
  - quarter-level generalization;
  - better than the best baseline in both halves of the period and in the final block.
- **Maximum reliable lead** = the longest lead *k* such that Leads 1..*k* are all reliable.

## 7. FIRI, rankings and claims

- **FIRI v2** is not the LightGBM target and is not used as a feature. It stays the served dashboard index.
- **LightGBM's own output** in E107 is P(T43 HIGH), which is a risk proxy.
- **Municipal rankings** (Objective 3) would remain a disaggregation of a province forecast by poverty and density weights. They are not independent municipal forecasts.
- **What the system may not claim:**
  - It cannot claim to predict the share of food-insecure households.
  - It cannot claim a reliable lead time unless `EXPERIMENT_REPORT.md` shows one.
