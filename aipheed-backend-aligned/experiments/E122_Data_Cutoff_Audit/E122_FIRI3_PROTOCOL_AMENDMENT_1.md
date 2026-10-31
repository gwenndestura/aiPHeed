# FIRI3 protocol, Amendment 1: 2021+ comparison base (2026-10-31)

**Amends.** `E121_FIRI3_PROTOCOL.md` (SHA-256 8a431a9d…), which stays unchanged on disk. This file's SHA-256 is in `firi3.AMENDMENT_1_SHA256` and in `runner/AMENDMENT_1_SHA256.txt`.

**Authority.** The owner's E122 instruction:
- §1: "a feature may use an observation from 2021 only if the required calculation can be performed using eligible observations from 2021 onward";
- §5A: "if a 2021 observation requires a 2020 comparison value, do not use that comparison";
- §9.6: correct the calculation without changing the methodology.

**Change to section 3.2 (inputs).** Added after the pre-2021 rejection:

> Every **change-type** series must have a comparison base inside the window. These are all scored dynamic series except the four level series (`typhoons_local_100km`, `typhoons_PAR`, `N1_fssi_v3`, `news_gdelt_shortage_share`):
> - year-on-year changes, production drops, the unemployment change, the remittance decline;
> - rainfall and temperature anomalies, which are compared with earlier same-quarter years.
>
> A change-type observation of period q is admitted only if q − 4 ≥ 2021-Q1, that is, q ≥ 2022-Q1. Earlier rows are **rejected before scoring and normalization**, and counted. In particular, PSA-published 2021 CPI year-on-year values (based on 2020 prices) are no longer admitted. The E119/E120 "declared exception" is withdrawn for FIRI3.

**Unchanged:**
- the six indicators, the 34 features and their components;
- directions;
- the expanding-window percentile (≥ 8 earlier available observations) and the cross-province ranks;
- the aggregation, completeness rules and bands;
- equal weights.

**Records.** The E121 snapshots (`E121_FIRI3_Implementation/snapshots/`) stay as the pre-amendment record. Amended results are written under `E122_Data_Cutoff_Audit/`.
