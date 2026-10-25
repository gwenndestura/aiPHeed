# E110 Final methodology (simplest credible version)

## The workflow

1. **Collect verified hunger outcomes from 2021.** SWS Total Hunger, the % of families that experienced involuntary hunger at least once in the past three months.
   - Balance Luzon is the study's outcome; Metro Manila, Visayas and Mindanao serve as checks.
   - Only non-commissioned rounds, each matched to its SWS release (`data/sws_area_rounds.csv`).
2. **Check quality.** For each round, record:
   - its publication date;
   - its sample size and published margin (±4% at n = 600, ±6% at n = 300);
   - its respondent base (household heads until 2024, adults from April 2025).

   Commissioned and registered-voter rounds are flagged and excluded from the primary series.
3. **Build forecasts from information available at each issue date** (day 1 of the quarter). Use only rounds already published. Because of the publication lag, the latest reading is usually two quarters old.
4. **Forecast.**
   - **Point forecast:** the latest published reading (persistence).
   - **Interval:** ±1.28 × the RMSE of that rule's own past errors (80%), about ±6 points one quarter ahead.
   - The 12 FIRI indicators and the required LightGBM run alongside as research models.
5. **Compare** every method with the latest reading on identical quarters and areas, chronologically.
6. **Test generalization:** by period, rising vs falling hunger, after the 2025 survey change, leave-one-quarter-out, and area by area.
7. **Decide the maximum reliable lead** with the frozen criteria. **Result: none established.**
8. **Explain:**
   - what the number is (regional experienced hunger, not provincial food insecurity);
   - its uncertainty (survey margin plus forecast error);
   - its limits (no lead validated; surges are not anticipated).

## What each component is

| Component | Meaning | Status |
|---|---|---|
| SWS Total Hunger (Balance Luzon) | Observed experienced hunger, regional | Primary outcome |
| Latest-reading forecast | Recommended one-quarter outlook | Best method in E109 and E110 at Lead 1; not "reliable" under the rule |
| LLR / COMB smoothing | Noise-aware averages | Better on average at Lead 2, but fail during surges; not recommended |
| LightGBM with 12 FIRI families | Required research model | Insufficient evidence in E110 (5 quarters); worse than the latest reading in E109 (9 quarters) |
| National indicators (El Niño, jobs, remittances) | Contributing risk factors | Made forecasts worse when added (pooled test) |
| Price-pressure model (E108) | Food-price pressure | Not a hunger forecast |
| FIRI v2 (dashboard) | Risk index | Unchanged; not validated against hunger here |
| LGU status | Contextual (PSA SAE poverty) | "Insufficient local evidence" for all 142 (E109) |

## Why this is the right simple method

- **Simplest:** it needs no parameters.
- **Most accurate:** no tested alternative beat it one quarter ahead over 9–10 quarters and 4 areas.
- **Safest when hunger surges,** which is the case DA most needs.

Smoothing would have understated the 2024 rise by an extra 1–4 points.

## What must not be claimed

- That hunger is forecast reliably at any lead.
- That the 12 indicators improve hunger forecasts.
- Any provincial or municipal hunger values.
- That a research threshold (11.3%, 15% or 20%) is an SWS category.
