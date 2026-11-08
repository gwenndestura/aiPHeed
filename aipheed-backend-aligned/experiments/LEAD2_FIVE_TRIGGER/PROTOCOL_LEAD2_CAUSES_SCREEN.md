# LEAD2_CAUSES: development-only screen for the one unused provincial source (frozen before running)

**Branch:** `aiPHeed/forecast-research`, continuing from `fc90202`. **Written:** 2026-10-28. The SHA-256 goes in `runner/CAUSES_SHA256.txt`; both are committed before `runner/rain_screen.py` runs.

**Why a screen and not a model.**
- The source inventory (`LEAD2_THESIS_PACKAGE.md` §15) found one predictor source with a theoretical link to the price-side errors that has never entered the T43c Lead-2 model family: **NASA POWER provincial rainfall anomaly** (`backend/data/processed/province_rainfall.parquet`; PRECTOTCORR, 6 points per province, vs the 1991-2020 normal; 2021-Q1..2026-Q2).
- Its five provinces correlate at 0.95, and the climate group already adds noise at Lead 2. A full candidate is therefore justified only if the signal first shows a development-period link to the error it is meant to fix.

**Hypothesis.** Rainfall deficits or excesses in the origin quarter disturb fresh-food supply (vegetables, fish) and move provincial food prices over the following two quarters, beyond what the flat CPI projection already holds.

**Screen (development rows only: Lead 2, targets ≤ 2024-Q4; the later evaluation rows are not read).**
- **Outcome:** the projection error e = realised price margin − projected price margin (max over food and gap), i.e. what the flat projection misses.
- **Signals:**
  - (a) the province's rainfall anomaly in the origin quarter;
  - (b) the same minus the five-province mean (its provincial part);
  - (c) the absolute anomaly (a shock in either direction).
- **Availability:** the origin quarter has ended before every Lead-2 issue date (issues fall 3+ weeks into the next quarter; NASA POWER monthly values are posted after month end). The file is a 2026-09 vintage; NASA POWER revisions are small, and this is disclosed.
- **Statistic:** Spearman ρ between each signal and e, with a 90% quarter-block bootstrap CI (2,000 draws, seed 2031).

**Rule (fixed now).**
- Proceed to a frozen LightGBM candidate only if some signal has |ρ| ≥ 0.30 **and** a 90% CI excluding 0.
- Otherwise **stop**: no candidate is built, and P0H4-U is retained.
- Three signals are screened, so the 0.30 bar is deliberately higher than a single-test bar.

**Not allowed:** reading the CONF/evaluation rows (targets ≥ 2025-Q1) in the screen; adding signals or lags after running; any change to the target, timing, criteria, served model or seals.
