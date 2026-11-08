# Lead 1 and Lead 2 reliability (E117)

**Target.** SWS Total Hunger level by area (regional).

**Periods.** All historical periods have been inspected before:
- P1 2003-12;
- P2 2013-20;
- P3 2021-26;
- pooled 2003-26: 90 quarters, 360 area-quarters per lead.

**Unit of evidence.** Differences are averaged by quarter before testing, so the four areas are not counted as independent.

## Level forecasts, pooled 2003-2026

| Model | Lead 1 MSE (MAE) | vs persistence (p) | Lead 2 MSE (MAE) | vs persistence (p) |
|---|---|---|---|---|
| Persistence (latest reading) | 35.3 (4.56) | – | 42.2 (4.94) | – |
| Climatology (known mean) | 41.2 (5.21) | worse | 42.2 (5.29) | equal |
| Mean reversion (DAMP) | **29.4 (4.26)** | −5.8 (0.002) | 35.3 (4.68) | −6.9 (0.053) |
| AR(1) | 30.5 (4.38) | −4.8 (0.035) | **34.1 (4.66)** | −8.1 (0.033) |
| Ridge, all features | 30.6 (4.42) | −4.6 (0.107) | 36.4 (4.68) | −5.8 (0.110) |
| LightGBM base (hunger history; strict = provisional) | 29.8 (4.30) | −5.5 (< 0.001) | 34.6 (4.59) | −7.6 (0.001) |
| LightGBM all testable domains (H) | 29.6 (4.28) | −5.7 (< 0.001) | 35.2 (4.59) | −7.0 (0.001) |
| LightGBM full (I, with news) | 31.1 (4.38) | −4.1 (0.002) | 36.8 (4.70) | −5.4 (0.006) |
| LightGBM strict all (base + news + typhoons) | 31.2 (4.36) | −4.0 (0.002) | 37.7 (4.79) | −4.4 (0.012) |

**What this shows.**
- At both leads, every model that uses hunger history beats persistence on level error.
- The LightGBM is no better than the simple statistical models: mean reversion at Lead 1, AR(1) at Lead 2.
- Adding the domains does not lower pooled error. Adding news raises it.

**By period (Lead 2 MSE).**

| Model | P1 2003-12 | P2 2013-20 | P3 2021-26 |
|---|---|---|---|
| LightGBM base | 35.2 | 32.9 | 35.9 |
| H (all domains) | 35.6 | 34.9 | 34.7 |
| Mean reversion | 41.9 | 27.0 | 34.4 |
| Persistence | 42.8 | 37.8 | 47.5 |

The best model changes from period to period. No single model is reliably best.

## "Above usual" event (pooled)

| Model | Lead 1 bal. acc. / Brier / cal. slope | Lead 2 bal. acc. / Brier / cal. slope |
|---|---|---|
| Persistence | **0.711** / 0.182 / 0.71 | **0.714** / 0.192 / 0.60 |
| LightGBM base | 0.698 / 0.187 / 0.95 | 0.635 / 0.203 / 0.73 |
| H | 0.704 / **0.179** / 0.90 | 0.659 / 0.199 / 0.69 |
| Ridge | 0.702 / **0.176** / 1.00 | 0.684 / **0.189** / 0.75 |
| Mean reversion | 0.715 / 0.181 / 1.38 | 0.677 / 0.204 / 2.39 |

**Reading.**
- No model classifies the event clearly better than persistence.
- At Lead 2, persistence has the best balanced accuracy.
- The level-error gains do **not** become reliable HIGH/LOW predictions.

## Reliability verdict

**Lead 1 (regional).**
- Level forecasts beat persistence in development evidence. Hunger history (mean reversion) drives this.
- Palay/corn production (C3) adds a small, consistent improvement. It is provisional, because palay release timing is unverified.

**Lead 2 (regional).**
- Level forecasts beat persistence. No domain adds information.
- Event classification is no better than persistence.

**Untouched confirmation.** None yet. 12 forecasts are sealed (`out/prospective_forecasts.csv`, SHA-256 in the `.sha256` file):
- all variants;
- targets 2026-Q4 (Lead 1 and Lead 2) and 2027-Q1 (Lead 2);
- sealed 2026-10-31 02:10 UTC.

They are to be scored when SWS publishes those rounds. One or two quarters cannot establish reliability. At least 8 scored quarters per lead are needed (as pre-declared in E115).
