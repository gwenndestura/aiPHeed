# Selection Decision and the 2027-Q1 Research Forecast (E18)

## Decision

**No improved model was selected.** The frozen rules keep the baselines:

| Target | Kept |
|---|---|
| Constructed label | Naive persistence |
| H, F, D | Carry-forward |

**No horizon is "supported"** under the E18 working criterion.

## 2027-Q1 research forecast (`runs/20261013T065509Z/forecast_2027Q1.json`)

| Item | Value |
|---|---|
| Information cutoff | 2026-Q2 (authorized Jan–Jun 2026 data) |
| Forecast origin | 2026-10-13 |
| **Horizon** | **h = 3** |

**What each output predicts** (labels exactly as stored):

| Output | Forecast | Label |
|---|---|---|
| **Regional hunger** | **17.3%** (June 2026 SWS value carried forward) | "Research forecast of regional hunger (SWS Balance Luzon, % of families); not a forecast of provincial food insecurity." |
| **Provincial food inflation** (YoY %) | Cavite 4.73 · Laguna 3.97 · Quezon 4.87 · Rizal 4.33 · Batangas 1.43 (2026-Q2 carried forward) | "…not food insecurity." |
| **Relative price pressure** (points) | Cavite +0.87 · Laguna +0.10 · Quezon +1.00 · Rizal +0.47 · Batangas −2.43 | **Backtest note:** "no difference" (0) had the lowest error (1.21 vs 1.75), so province differences at h = 3 should not be read as informative |
| **Constructed label** (persistence of the 2026-Q2 label) | Cavite HIGH · Laguna HIGH · Quezon HIGH · Rizal HIGH · Batangas LOW | "NOT a measurement or forecast of provincial food insecurity." News-based models cannot run: 2026 news is not authorized. |

**Uncertainty:** not adequately quantified. The h = 3 backtest MAE is 5.7 points for H, 3.0 for F and 1.75 for D.

**These are research outputs, not validated or operational forecasts.**
