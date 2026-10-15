# E41 contamination log

## C-1 (2026-10-15, before the E41 protocol was written)

**What:** while checking the column layout of `backend/data/inputs/sws_rounds.csv`, a `cut` command printed every row of the file, including the SWS Balance Luzon hunger values for the E40 holdout quarters 2025-Q4, 2026-Q1, 2026-Q2 and 2026-Q3.

**Status of those values:** they are not new data. E31 (Q3 2026 scoring) and E36–E38 (v1 label evaluation) already used them, and the user authorized data released up to 2026-10-14 (E31). But E40 designated these four quarters as **untouched holdout for the E40 label**, and the E40 label depends on H.

**Consequence for E41:**
- E41 is not blind to the E40 holdout. It therefore **issues and scores no forecast of the E40 label for 2025-Q4..2026-Q3**. Those quarters remain reserved for E40's own sealed forecasts (`E40_SWS_CPI_Tiers/frozen/E40_HOLDOUT_FORECASTS.json`, issued 09:30:46Z, hash-frozen before this exposure, so they are unaffected).
- E41 scores the E40 label only on E40 development quarters (2023-Q1..2025-Q1).
- No CPI value for the holdout quarters is printed by E41 runners. E41 prints only aggregate metrics over target sets that include them for the price-pressure target, which E39 already scored on those dates.
- The first E41 forecasts that are blind in every sense are 2026-Q4 (lead 1) and 2027-Q1 (lead 2), whose outcomes do not exist yet.
