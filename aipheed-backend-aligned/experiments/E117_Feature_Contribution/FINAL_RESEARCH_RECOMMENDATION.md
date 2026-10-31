# E117 final research recommendation

**Protocol.** `EXPERIMENT_PROTOCOL.md`, frozen 8555bc5 before any fit. Branch `aiPHeed/corrected-data-pipeline`, local only.

**Data.** Corrected regional panel. The SHA-256 of the panel and protocol are in `out/e117_results.json`.

**Reproduce.**

```bash
cd aipheed-backend-aligned/experiments/E117_Feature_Contribution/runner && python run_e117.py
```

## Answer

**1. The corrected dataset supports genuine regional hunger forecasting at the level scale, at Lead 1 and Lead 2.**
- Pooled 2003-2026, every model using hunger history beats persistence:
  - LightGBM base: Lead 1 MSE 29.8 vs 35.3; Lead 2 34.6 vs 42.2.
- That gain comes from hunger's own dynamics. Simple statistical models do as well:
  - mean reversion: 29.4 at Lead 1;
  - AR(1): 34.1 at Lead 2.
- It does **not** extend to reliable "above usual" (HIGH/LOW) classification. Persistence has equal or better balanced accuracy.

**2. The five domains do not meaningfully improve the forecasts as a whole.**

| Domain | Lead 1 | Lead 2 | Note |
|---|---|---|---|
| Market and food prices | conditional (2021-26 only: −6.7 MSE) | conditional (2021-26 only: −5.9) | led by rice prices (A3). Regime-specific; needs prospective confirmation. |
| Fish production | conditional (consistent sign, small: −0.54 pooled, CI −1.00 to −0.11; Holm 0.12) | no measurable value | — |
| Climate (group) | no measurable value | no measurable value | but **C3 palay/corn production drop improves Lead 1** (−0.83, CI −1.34 to −0.35, Holm 0.021, all 3 periods) |
| Employment | no measurable value | no measurable value | national series only |
| OFW remittances | **not testable** | not testable | no series before 2021 |
| News / NLP | possible noise (+1.5) | possible noise (+3.0) | coverage only from 2018 |
| All testable domains together | −0.2 (CI −1.9 to +1.4) | +0.6 | no improvement over hunger history |
| Full 12-indicator model | +1.4 | +2.1 | worse than base |

**Interactions.**
- Food prices × employment, fish × climate and climate × prices add nothing at Lead 1. At Lead 2 they slightly worsen the forecast.
- Prices × remittances and poverty × market cannot be tested.

**3. Under strict (verified-only) timing,** the only testable inputs are hunger history, news and typhoons.
- Neither news nor typhoons helps: news is possible noise; typhoons show no measurable value.
- Every domain with a provisional signal (market, fish, palay) depends on release timing that is not yet verified.

## Why the results are limited

1. **The outcome is dominated by its own mean-reverting dynamics and survey noise** (Balance Luzon ±4 pp).
2. **Most predictors are national or area-level series shared by all areas.** They act as quarter markers. The domains halve training error but not test error.
3. **Timing.** Release timing is unverified for every market, production and employment series, so none can enter the strict primary experiment.
4. **Coverage.** OFW remittances and poverty have no historical series. News exists only from 2018.
5. **Regime changes** shift the relationships: the 2023-24 rice-price regime, and the 2025 change in SWS respondents.
6. **No untouched historical period remains.** Only the sealed prospective forecasts can confirm anything.

## Evidence-based improvements, in order

1. **Score the sealed prospective forecasts** (`out/prospective_forecasts.csv`: targets 2026-Q4 and 2027-Q1, all variants) as SWS publishes. Keep issuing and sealing each quarter. At least 8 quarters per lead are needed before any reliability claim.
2. **Verify release dates for palay/corn, fisheries and CPI.** This would let the C3, C4 and market signals enter the strict experiment. Palay is the most promising: it is consistent across all periods at Lead 1.
3. **Obtain the BSP OFW series from 1989** (manual download) so remittances can be tested at all.
4. **Obtain regional quarterly labour-force data** to replace the national unemployment series.
5. **Keep the 12 indicators and five domains in the system.** Present them as monitored drivers, with each one's measured status, not as proven forecast inputs.
6. **For a provincial food-insecurity forecast, obtain a provincial outcome with repeated rounds** (CBMS or FNRI FIES). Until then, provinces get a vulnerability profile only.

## Integration

- **Production integration is not recommended now.**
- **The defensible next production change, for your approval:** a regional Balance Luzon hunger *level* outlook (Leads 1-2, with an uncertainty band), clearly separated from the provincial vulnerability profile. Its candidates would be mean reversion / AR(1), or the LightGBM base with C3. The choice would be made only after prospective scoring.
- **No dashboard, API or model change was made.**
