# E110 Final recommendation

## What improved

- **Outcome data.** All 23 Balance Luzon values are now matched to SWS releases. The in-window area series for Metro Manila, Visayas and Mindanao were added, with sample sizes and margins per round.
- **Diagnosis.**
  - "Lead 1" is effectively two quarters ahead because of SWS's publication lag.
  - 40–90% of quarter-to-quarter change is survey noise.
  - The 2025 survey changes split the series.
- **Testing.** Every method was tested on 4 areas and by period, direction and influence, not on one aggregate number.

## What did not improve

- **Lead 1:** no method beats the latest published reading, including the 12-indicator LightGBM.
- **Lead 2:** smoothing helps on average but fails during surges, so it is not adopted.
- **Indicators:** national indicators make hunger forecasts worse; the 12-family model has too few evaluable quarters to judge.

## Supported horizon

**None is established.**
- **Usable outlook:** the latest reading as a one-quarter outlook (average error about 3.7–3.9 points, near the ±4 survey margin), shown as unvalidated.
- **Unconfirmed:** everything. The sealed E107–E110 forecasts become scorable from SWS 2026-Q4, expected around January 2027.

## Recommendation for the thesis

Adopt the simple method in `E110_FINAL_METHODOLOGY.md`, and report the negative lead-time result honestly. It is a finding about what 2021+ SWS data can support, not a failure of implementation.

**Production is unchanged.** Any dashboard change needs your authorization. One option is to show the latest SWS reading with its margin and its validation status, instead of a risk probability.
