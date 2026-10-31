# FIRI3 protocol, Amendment 3: zero-storm quarters in the PAR count (APPROVED 2026-10-31)

**Status.** **Approved by the owner** (E127 instruction, §1), on the E126 evidence (`E126_D_E125_2_IMPACT_ANALYSIS.md`, `E126_PAR_ZERO_STORM_VERIFICATION.csv`). It is in force from FIRI3 version 1.3.

**Hashes.** This file's SHA-256 is in `firi3.AMENDMENT_3_SHA256` and `runner/AMENDMENT_3_SHA256.txt`.

**Amends.** The E121 protocol (8a431a9d…), Amendment 1 (4fd05309…) and Amendment 2 (8b5f729c…), all unchanged. The proposal text is `E126_AMENDMENT_3_PROPOSAL.md` (a359c6cf…).

> **Event-count inputs: a quarter with no event is an observation of 0.**
>
> **Scope.** The cyclone count in PAR (`typhoons_PAR`, feature `CEC_cyclones_R`) is built per quarter from IBTrACS:
> - boundary: the approved box 5–25°N, 115–135°E;
> - assignment: storms counted in the quarter of their first fix inside the box;
> - storms counted once: one key per IBTrACS SID, its JTWC ATCF id where present, otherwise the SID.
>
> **Coverage.** A quarter is *covered* when the IBTrACS file's first fix is on or before the quarter's start and its last fix is after the quarter's end.
>
> **Rule.** Every covered quarter from 2021-Q1 is recorded:
> - with its count of storms;
> - **as 0 when no storm qualifies**;
> - with status `verified` and availability at the start of the next quarter.
>
> **Not covered.** A quarter that is not covered is **not** recorded and stays missing. **No quarter is filled.**
>
> **Local counts.** The within-100-km counts already record zero quarters, so they are unchanged.

**Effect.** In 2021–2026 the rule adds exactly three zero quarters (2023-Q1, 2024-Q1, 2025-Q1). It changes no count in any quarter with storms.

**Unchanged:**
- the six indicators and 34 features;
- directions, normalization, aggregation, completeness, bands and weights;
- the cutoff, Amendment 1 and Amendment 2;
- the unemployment calculation.
