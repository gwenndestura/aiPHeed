# 2027-Q1 Research Forecast (exploratory; not validated)

| Item | Value |
|---|---|
| Generated | 2026-10-13 (run `runs/20261013T035829Z`; timestamp in `forecast_2027Q1.json`) |
| Target quarter | **2027-Q1** |
| Forecast origin | 2026-10-13 |
| Information cutoff | Approved observations ≤ **2025-Q4**. 2026 data are not authorized. |
| Horizon | **h = 5 quarters** (latest eligible observation 2025-Q4 → 2027-Q1). The same convention was used in the backtest. |
| Evidence at this horizon | 3 (H) and 5 (F, D) backtest origins, all previously explored. **Exploratory only; not validated.** |
| Uncertainty | **Not adequately quantified.** No interval is given. |

## 1. Regional hunger

**Research forecast of regional hunger; this is not a forecast of provincial food insecurity.**

| Item | Value |
|---|---|
| Geography | SWS Balance Luzon, wider than CALABARZON. **One value for the region**, not five provincial values. |
| Target | Share of families experiencing involuntary hunger in the past 3 months, 2027-Q1 |
| Latest input | 2025-Q4: 16.7% (November 2025 SWS survey; published 2026-01-14, verified-single) |
| **Forecast (frozen rule: carry-forward)** | **16.7%** |
| Experimental outputs (not selected) | Drift 17.1; damped trend 17.2; ridge AR(1) 18.0; ridge AR two lags 15.9; ridge + indicators 17.0; historical mean 15.1 |
| Past carry-forward errors at h = 5 (descriptive, 3 origins) | 0.85, 4.20, 1.40 points. **The E13 one-quarter-ahead errors were up to 7.9 points.** |

## 2. Provincial food inflation

**Research forecast of provincial food inflation (year on year); not a forecast of food insecurity.**

Frozen rule: carry-forward of the 2025-Q4 value (CPI dates are proxies).

| Province | Forecast for 2027-Q1, % (= 2025-Q4 value) |
|---|---|
| Cavite | 1.90 |
| Laguna | 2.77 |
| Quezon | 1.20 |
| Rizal | 1.23 |
| Batangas | −0.50 |

**Backtest MAE at h = 5: 2.95 points** (5 origins).

## 3. Relative provincial food-price pressure

**Research forecast of relative food-price pressure (points against the unweighted five-province mean); not a forecast of food insecurity.**

| Province | Frozen-rule output (carry-forward, 2025-Q4) | "No difference" baseline (lowest backtest error) |
|---|---|---|
| Cavite | +0.58 | 0 |
| Laguna | +1.45 | 0 |
| Quezon | −0.12 | 0 |
| Rizal | −0.09 | 0 |
| Batangas | −1.82 | 0 |

**Backtest at h = 5:** carry-forward MAE 2.37; zero 1.27.

**Over a five-quarter gap the evidence favours "no provincial difference".** A province ranking for 2027-Q1 **should not be read as informative.** A ranking always produces a top province even when the expected differences are zero.

## 4. Not produced

**Thesis risk classification (HIGH/LOW per province) for 2027-Q1: not produced.**

- It would need 2026 news inputs, which are not authorized.
- Too few evaluation origins exist at that lead time.
- The classifier did not beat simple baselines at any evaluable lead time (E17).
