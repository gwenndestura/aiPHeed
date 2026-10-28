# Lead-2 valid-outcome protocol (frozen before any outcome is scored)

**Branch:** `aiPHeed/forecast-research`. **Written:** 2026-10-28. The SHA-256 goes in `runner/PROTOCOL_SHA256.txt` and is committed before any track below is scored.
**Basis:** `OUTCOME_DATA_FEASIBILITY.md`. No valid quarterly provincial outcome exists, so this protocol fixes in advance:
- **Track A:** a prospective regional test;
- **Track B:** a cross-sectional validity check, run only if CBMS 2024 or FNRI provincial data arrive.

Neither track tunes a model, and neither selects a threshold.

## 0. Rules that apply to both tracks

- **The proxy stays a comparator.** T43c, P0H4, P0H4-U and Z0-U are comparators. T43c is never called measured food insecurity.
- **No manufactured labels.** No interpolation, no repetition of a regional or annual value across provinces, LGUs or quarters to create rows.
- **Shared measurements count once.** A regional measurement shared by all five provinces counts as one observation per quarter.
- **Separate roles.** No threshold, model or hyperparameter is chosen on the rows used to report performance.
- **No new model training.** E109-E113 and FORECAST_RESEARCH_II found that nothing beats the newest SWS reading for regional hunger, and that no family adds held-out value. New models need new evidence, i.e. at least the Track A untouched quarters.

## Track A: prospective regional Lead-2 test against measured hunger

| Item | Definition |
|---|---|
| Outcome (authoritative source) | SWS involuntary hunger, Balance Luzon: the mean of the quarter's non-commissioned rounds, as first published by SWS (O1) |
| Continuous outcome (primary) | H_q in percentage points |
| Binary outcome (secondary) | HIGH = H_q > 11.3. This threshold was frozen on 2026-10-15 (E40 `label_spec.json`, P60 of 2021-Q1..2022-Q4) and is **not re-selected**. It is a relative regional threshold, not an official food-insecurity standard. |
| Unit | Balance Luzon × quarter: **one row per quarter** |
| Lead-2 issue date and cutoff | The day after SWS publishes quarter t's Balance Luzon reading, at the latest day 1 of month 3 of quarter t+1 (schedule B). Information cutoff = everything published before the issue date. Target = quarter t+2. |
| Forecasts scored | Already sealed; nothing is re-fitted. **F-A1** = π_H of P0H4-U / Z0-U (identical in both; seals bd6572e1 and b7162a63), issued 2026-10-15 for 2027-Q1. **Point forecast** = the newest published reading at the issue date (23.6 for 2027-Q1). |
| Baselines | Persistence (the newest reading) is itself the forecast here. **Climatology** = the share of published quarters above 11.3, and their mean. |
| Training / validation / test | No training or validation. The **untouched test set** is every Balance Luzon quarter from 2027-Q1 onward whose Lead-2 forecast was sealed before SWS published that quarter. 2026-Q4 is a Lead-1 target of the October 2026 issue and is scored only as Lead 1. |
| Metrics | Primary: mean absolute error of the point forecast vs the climatology mean. Secondary: Brier score and log loss of π_H; accuracy, HIGH precision and recall at 0.50; calibration once ≥ 20 quarters exist. |
| Reliability rule | The FR R1-R7 rules with rows = quarters. R1 needs ≥ 10 untouched quarters. Superiority over climatology needs a one-sided quarter-block bootstrap p < 0.10, as in R5. |
| Earliest decision | 10 untouched quarters means 2027-Q1..2029-Q2 published, around the third quarter of 2029 |
| Each new quarter | Append to `out/track_a_log.csv` with the SWS publication date. Never edit an earlier row. |

**What Track A can show.** Whether the system's Lead-2 hunger forecast anticipates **regional experienced hunger**. That is a legitimate food-access outcome, but regional. It **cannot** show provincial food insecurity.

## Track B: cross-sectional validity check (run only after request A or B returns data)

| Item | Definition |
|---|---|
| Outcome (authoritative source) | PSA CBMS 2024 SDG 2.1.2.p1: the share of households with moderate or severe food insecurity (FIES), reference period 1 July 2023 - 30 June 2024, by city/municipality and province (O8). Alternatively, FNRI ENNS provincial FIES (O3/O5) for the domains and years FNRI reports. |
| Units | 5 provinces; 142 cities/municipalities, analysed only within provinces |
| Forecasts compared | For each province: the mean of the four quarterly Lead-2 probabilities for the target quarters 2023-Q3..2024-Q2, from each comparator's walk-forward predictions (`FORECAST_RESEARCH_II/out/predictions_ii.csv`), plus the T43c HIGH share of those quarters. For each LGU: the served priority index for the same quarters. |
| Statistic | Spearman ρ, with no threshold. Provinces: n = 5, descriptive only (no p-value claimed). LGUs: within-province Spearman, pooled by Fisher z across provinces, with the poverty-only ranking as a baseline (the LGU index embeds 2021 poverty). |
| Interpretation fixed now | A positive ρ for the provinces *does not* demonstrate Lead-2 reliability: it is one 12-month window and n = 5. An LGU result beating the poverty-only baseline would show the province layer adds information; otherwise the ranking is just poverty. |
| Not allowed | Making quarterly labels from the annual values; choosing a FIES cut-off to define HIGH after seeing the forecasts |

## Comparators (Priority 3)

- P0H4, P0H4-U and Z0-U were reproduced from their saved walk-forward predictions (`out/comparators_reproduced.json`; every exported Lead-1/Lead-2 metric matches).
- Against T43c (the proxy) they score as follows: Lead 2 0.769 / 0.800 / 0.800, all failing at least one of R1-R7. That evidence concerns the proxy, not food insecurity.
- On Track A all three share the same hunger part, so they cannot differ on the regional hunger outcome.

## Decision rule (fixed now)

| Decision | Condition |
|---|---|
| **RELIABILITY DEMONSTRATED AGAINST VALID OUTCOME** | Track A passes R1-R7 on ≥ 10 untouched quarters **and** Track B (if obtained) is not contradictory. It applies only to regional hunger unless a provincial quarterly outcome is obtained. |
| **EXPERIMENTAL — INSUFFICIENT VALIDATION** | A valid outcome exists and is being scored, but fewer than 10 untouched quarters are scored, or a criterion fails |
| **NOT EVALUABLE — REQUIRED OUTCOME DATA UNAVAILABLE** | No valid outcome exists at the forecast's unit (province × quarter), or no untouched quarter of a valid outcome has been published |
