# FIRI3 protocol, Amendment 3 (PROPOSAL, not in force): zero-storm quarters in the PAR count

**Status.** PROPOSED. It needs owner approval and is **not implemented** in `firi3.py` or in any input.

**On approval:**
- this text is frozen with its SHA-256;
- the PAR input gains explicit zero rows;
- `firi3` records the amendment hash;
- the frozen configuration gets a new version, and the E124 configuration stays as the v1.2 record.

**Amends.** The E121 protocol plus Amendments 1 and 2. **Evidence:** `E126_D_E125_2_IMPACT_ANALYSIS.md`.

## Text

> **Event-count inputs: a quarter with no event is an observation of 0.**
>
> **Scope.** The cyclone count in PAR (`typhoons_PAR`, feature `CEC_cyclones_R`) is built per quarter from IBTrACS: storms counted in the quarter of their first fix inside 5–25°N, 115–135°E.
>
> **Rule.** For every quarter from 2021-Q1 that the IBTrACS file covers completely (file starts on or before the quarter start; last fix after the quarter end), a quarter with no storm is recorded as **0**, with:
> - status `verified`;
> - availability at the start of the next quarter.
>
> **Excluded.** A quarter the file does not cover completely is **not** recorded. It stays missing.
>
> **Storms.** Counted once per storm: one key per IBTrACS SID, namely its JTWC ATCF id where present, otherwise the SID.
>
> **Local counts.** The within-100-km counts already record zero quarters, so nothing changes for them.

## Not changed

- the six indicators and 34 features;
- directions, normalization, aggregation, completeness, bands and weights;
- the cutoff and Amendments 1 and 2.

## Effect (from the impact analysis, refreshed inputs)

- **Zero quarters added:** 2023-Q1, 2024-Q1, 2025-Q1.
- **Scores:** 9 regional FIRI3 scores change (max |Δ| 0.042), with 1 band change (2025-Q2: above usual → usual or below).
- **Provincial scores:** none change.
- **2026-Q4 issue:** its PAR percentile goes from 0.711 to 0.750, with the same 2026-Q3 count of 7.
