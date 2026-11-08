# Deliverable 10. Final methodology recommendation

**FI12** · protocol `2949208888f5` locked 2026-11-03T02:31:10+00:00 · Evidence tags: [V] verified against a primary source in this repository; [S] secondary source, not verified; [R] computed by FI12 under the locked protocol; [F] read from an earlier study's result file.

The simplest methodology the evidence supports:

| Element | Recommendation |
|---|---|
| What is predicted | (1) **Next-quarter Balance Luzon hunger** above its normal (measured food insecurity, regional). (2) **Provincial food-price pressure** next quarter (a driver, labelled as such). Neither is presented as a provincial food-insecurity rate |
| Outcome labels | SWS hunger for (1); PSA provincial food CPI for (2). FNRI/ENNS and PSA subsistence are **external validation references**, never training labels |
| Predictors | Latest SWS reading (persistence) for (1); FI10 trigger groups for (2) |
| Five provinces | Shown through price pressure (forecast), poverty and food-poverty context (latest PSA wave with its CI), and the 2015 FNRI and ENNS values as dated, labelled references. Provinces are not ranked by a "food-insecurity forecast" |
| 12 FIRI families | Descriptive context. Five families have no provincial variation; none is associated with provincial outcomes; none is a validated provincial food-insecurity predictor |
| Prediction | FI9 damped persistence + conformal interval; FI10 pooled model per lead |
| Uncertainty | Conformal interval for SWS; probability and track record for FI10; published CIs for every survey value |
| Validation | Prospective register (FI9, FI10) plus FI12 re-run whenever a new provincial wave appears (PSA 2026 FIES; FNRI NNS) |
| Lead time | Regional hunger: one quarter (persistence). Provincial food insecurity: **none verified** |
| Limitations | No repeated, comparable provincial food-insecurity series; provinces not distinguishable in the only verified FI wave; food-poverty ordering unstable between waves; price pressure is negatively related to provincial food poverty |

**Not recommended:** a provincial food-insecurity model trained on the workbook (five rows per wave), any HIGH/LOW label
from these percentages, or using P0H4's provincial ranking as a ranking of food insecurity.

**What would make provincial forecasting testable** (public data only, no requests):
- FNRI ENNS 2018–2021 and NNS 2023 household public-use files (blocked from this network; downloadable by the owner from
  another network) → provincial FIES estimates with SEs for 2018, 2019, 2021, 2023: four comparable waves.
- PSA 2026 FIES provincial poverty and subsistence (expected 2027).
- Approximate requirement: detecting a true provincial rank correlation of 0.6 at α = 0.05 with 80 % power needs about
  16 independent province-wave pairs (Fisher z), i.e. at least four comparable waves of five provinces; 0.4 needs about
  eight waves.
