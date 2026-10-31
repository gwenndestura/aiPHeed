# E121 FIRI3 final recommendation

**Decision requested from the owner.** FIRI3 is implemented and validated as a **candidate**. **Do not replace FIRI v2 yet.**

**Recommended:**
1. Approve or reject the design issues DI-1 to DI-3 (a new protocol version if any are accepted).
2. Run FIRI3 prospectively beside FIRI v2 from origin 2026-Q4.
3. Decide on adoption only after several prospective quarters and a check of the Batangas employment data (DI-6).

## Answers

1. **Implemented successfully?**
   - **Yes.** `backend/app/ml/inference/firi3.py` implements the frozen protocol and reproduces the E120 design exactly (138 of 138 unit-origins).
   - The protocol hash is checked on every run.
   - Results are deterministic.

2. **All six indicators functioning?**
   - **Yes.** All six are computed.
   - **PSV** is available only from 2025-Q3 (its release date), in 22% of province-quarters.
   - **FIS** is available in 12% of province-quarters (FSSI needs at least 5 articles).
   - **EHS** is lost from 2026-Q2 under the frozen latest-complete-year rule (DI-3).

3. **How many scores?**
   - **Provincial:** 75 of 115 (2023-Q1+); 54 rest on 4 indicators, 13 on 5, 8 on 6.
   - **Regional:** 10 of 23 (2024-Q2+).

4. **Stable under missing data and weighting?**
   - **The score level: yes.** Reasonable weight changes move scores by 0.005–0.03 on average. Redundancy-adjusted weights flip 1.3%.
   - **Composition: not fully.** Indicator joins shift single provinces by up to ±0.10.
   - **The band near 0.5: no.** Arbitrary weights change 16–27% of bands, and the leave-one-out range (≈ 0.13) is as wide as a band step.

5. **Does anything dominate?**
   - **No single feature.** No removal moves a score by more than 0.11.
   - **Province differences are dominated by two indicators,** EHS and PSV ranks (DI-1). Batangas ranks highest mainly through its reported 31–40% underemployment.
   - **Regional scores** are most sensitive to the national EHS and GDELT series.

6. **Leakage and tests?**
   - All 15 leakage checks pass.
   - The full suite passes: 1096 passed, 18 skipped.

7. **How it differs from FIRI v2:**
   - **No SWS**, no model output, and no SWS-learned weights.
   - **Provincial data only** in provincial scores.
   - **Equal weights** and chance bands.
   - **A regional index** (v2 has none).
   - **Agreement with v2:** ρ −0.30, explained by v2's regional-hunger domain (ρ −0.35 with FIRI3) and national domains. With those removed, ρ +0.10; with v2's provincial A and V domains only, +0.29.
   - **v2 is HIGH in 81% of matched rows;** FIRI3 is ≥ 0.5 in 44%.

8. **Ready for prospective validation?**
   - **The mechanism is ready:** immutable, hash-manifested snapshots, with FIRI v2 stored beside them.
   - **The first prospective quarter is 2026-Q4** (issue 2027-01-01), after the inputs are refreshed with that quarter's releases.
   - The 23 existing snapshots are retrospective.
   - SWS comparisons will be descriptive only.

## Before adoption (owner decisions)

| Item | Recommendation |
|---|---|
| DI-1 structural vs conditions | Show a conditions score (FMA, AFP, CEC, FIS) and a structural score (EHS, PSV) beside the overall FIRI3 |
| DI-2 indicator-set changes | Always show the common-core score and flag set changes |
| DI-3 incomplete annual year | Fall back to the latest complete year, with the year shown |
| DI-4 verification | Request PSA release calendars |
| DI-6 Batangas underemployment | Verify against PSA provincial LFS tables |
| Dashboard | No change until approved. The approved design and colours stay. |
