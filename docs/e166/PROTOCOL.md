# E166: E164 with nested source selection. Fixed before results.

Written 2026-11-06. **Owner request:** "it should be E164 since it added meaningful input — make it trustworthy and reliable."

## Problems with E164 (from the E165 audit)
1. **Test-influenced feature selection.** The consumption inputs (`income_growth`, `income_rel`) were chosen in E157 by ranking 5 downloaded sources on the 72 test rows.
2. **Not available at the live issue date.** `regional_income_long.csv` ends in 2023. The as-of rule (year Y is public from Q3 of Y+1) needs 2025 at issue 2026-Q4, so both inputs are missing in the live 2027-Q1 forecast.

## Fix for problem 1 (this experiment)
Move the source choice **inside** E164's training-only selection.
- **Candidate sources** are the same five downloaded before E157 ranked them, with the same column definitions:

| Source | Columns |
|---|---|
| Farmgate palay | `l_fg_yoy`, `l_fg_rel`, `r_fg_yoy` |
| Wholesale rice | `l_rice_yoy`, `l_rice_rel`, `r_rice_yoy`, `l_terms` |
| NASA rainfall | `l_rain3`, `l_rain6`, `r_rain3` |
| Regional consumption | `income_growth`, `income_rel` |
| SunStar headlines | `SUNCOLS` |

- **Feature sets:** {GOV, FULL} built on `Pv.GNT_COLS` (the E151 columns), each with **one** of {none, palay, rice, rainfall, consumption, SunStar} added.
- **Everything else is E164 unchanged:**
  - anchors {H, RP, OH, RSS};
  - learners {NONE, RIDGE, ENET, RF, LGBM};
  - region GroupKFold(5);
  - inner weighted logit SSE;
  - calibration {id, lin};
  - P(HIGH) ≥ 0.5.
- The source is therefore picked per issue date from training rows only. **The score is that of the complete procedure, including the source choice.**

## Validation
- Leads 1 and 2, outer rounds 2018, 2019 and 2021 (72 rows).
- **Controls at Lead 1:**
  - all trigger and source inputs shuffled across provinces within survey-lead (seeds 1–3);
  - unreleased-round corruption.

## Gates
**The E165 gates F1–F10, unchanged** (`docs/e165/PROTOCOL.md` §5), applied to this procedure. E158 is the comparator.

## Fix for problem 2 (owner action, not part of this run)
- **If this procedure passes F1–F9**, its live use needs PSA regional household final consumption per capita (constant prices) for 2024 and 2025 added to `backend/data/e154/raw/regional_income_long.csv`.
- **The owner downloads it manually,** because PSA blocks scripts. **No value will be extrapolated or filled from 2023.**
- Until then, any source whose live inputs are missing is reported as **unavailable at issue**, and the live forecast discloses it.
