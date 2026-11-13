# Long-gap correction for the FINAL dashboard preview (locked 2026-11-13, before any corrected number is computed)

## Why
FINAL's live CALABARZON forecasts (issue 2026-Q4, cut-off 2026-11-01) have HIGH probabilities of 0.001–0.006. Two defects, diagnosed earlier the same day (`../aiPHeed_final_7of7_20261113/FINAL_SURVEY_ANCHOR_AND_LONG_GAP_ANALYSIS.md`) and **not** chosen now, make these overconfident:

| Defect | What happens | Live forecasts affected |
|---|---|---|
| **D-A Double-counted elapsed time** | Anchors are refreshed to the latest released round (2021), but RATE scales change by the province's own-survey gap g | Laguna (g = 34), Quezon and Rizal (g = 30), against s = 22 quarters since the 2021 round |
| **D-B Uncertainty does not grow beyond training support** | The forecast spread is the same (about 0.41 logit) at gaps 22, 30 and 34. The longest training gap is 24 | Laguna, Quezon, Rizal |

## Correction (all pieces fixed here, training-based, no outcome read)
1. **D-A.** The FINAL-ETMIX rule already locked and sealed (`../aiPHeed_final_7of7_20261113/FINAL_7_OF_7_IMPROVEMENT_PROTOCOL.md`, sha `a365da1f`):
   > p = ½ · p(g) + ½ · p(s)
   - s = target quarter − reference quarter of the latest survey round released at the origin.
   - Both terms come from the same fitted FINAL models.
2. **D-B.** For each variant and row, the predictive variance gets the RSS anchor's own process noise for the years beyond the fit's longest training gap G_max:
   > sd_adj² = sd² + q · max(0, elapsed − G_max) / 4
   - **sd** is FINAL's spread (from the 90 % half-width ÷ 1.645).
   - **q** is the RSS anchor's per-year process-noise variance, chosen by predictive likelihood on released rounds (`app/e163/model.py RSS._choose_q`).
   - **elapsed** is g or s for the respective variant.
   - **Probability:** p = Φ(mu ÷ sd_adj) when the fit's chosen calibration is "raw" (FINAL's choice in every fit so far). Otherwise the engine's probability is kept and the row is flagged.
3. **Prevalence shown:** mean of the two variants' mu, as % with a 90 % range from the wider sd_adj.
4. **Low-confidence flag:** set when g > G_max or s < g.

## Display basis
- **Headline:** the forecast share of households moderately or severely food insecure (HFIAS), with its 90 % range.
- **Then:** the risk class.
- **Secondary:** the chance of HIGH, to three decimals, never rounded to 0.00.
- Plus the low-confidence flag and the year of each province's last survey.

## Rules
- These corrections are applied **once** and reported whatever they show.
- No parameter is changed afterwards to raise or lower any forecast.
- Labelled as **untested corrections (local preview)** until a new provincial survey round confirms them.
- FINAL, its seals and E196 are unchanged.
