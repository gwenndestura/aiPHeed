# E125 final recommendation

## Readiness: **BLOCKED**

**Why:**
- the planned issue date (2027-01-01) has not arrived;
- the September 2026 LFS month is not yet published.

**Status of the other inputs:**
- **Refreshed:** NASA POWER and the 2026-Q3 cyclone counts.
- **Need no refresh:** every other source.
- **Rules:** cutoff and publication rules hold.
- **Scores:** reproducible.
- **Store:** unchanged.

**No forecast was issued. No owner authorization is requested yet.**

## Answers

1. **Were all four outstanding inputs refreshed?**
   - **Three of four.**
     - NASA POWER: 2026-01..09, all five centroids, 0 revisions.
     - Cyclones within 100 km for 2026-Q3: 0 in every province.
     - Cyclones in PAR for 2026-Q3: 7, after removing a split-ID double count.
   - **The fourth, September 2026 LFS, is not published.** PSA's table shows "." on 2026-10-31; it is due by 2026-12-01.

2. **Are all required 2026-Q4 inputs complete?** **No.** The national unemployment quarter has 2 of 3 months. Everything else is complete for the periods its release rule makes available before 2027-01-01.

3. **Which features are ready?**
   - **READY (4):** both cyclone counts, FSSI-v3, GDELT.
   - **READY WITH WARNING (29).**
   - **BLOCKED (1):** EHS_unemployment_change_R.

4. **Which remain provisional or unverified?**
   - **Provisional (26):** all FMA, AFP, CEC rainfall/heat and regional EHS features. Their dates rest on release rules.
   - **Unverified (3):** EHS provincial unemployment and underemployment, and PSV poverty, whose dates are assumptions.
   - **Nothing was promoted.**

5. **Did refreshed data change FIRI3 scores?**
   - **Yes:** 12 of 138 historical unit-origins (10 provincial, 2 regional; origins 2026-Q2 and 2026-Q3).
   - Max |Δ| 0.055, with 3 band changes. Example: the regional 2026-Q3 score moves from above usual to elevated.
   - These are reconciliation results only. **The E121–E124 outputs and snapshots are not changed.**

6. **Can every difference be explained?** **Yes.** All 12 come from **newly available observations**: NASA POWER 2026 months that the E118 retrieval did not contain. There are no revisions, no eligibility changes and no calculation defects in the changed rows.

7. **Are the cutoff and publication-date rules satisfied?**
   - **Yes, for every scored value:** 2021+, with Amendment 1 bases and Amendment 2 years; available before the issue; geography correct.
   - **CPI:** 13 of 32 archived releases came later than the day-10 rule, but no FIRI3 use is affected (margin ≥ 71 days; 0 uses with evidence on or after the issue).

8. **Is the frozen configuration unchanged?** **Yes.** The canonical hash equals the frozen value and matches `firi3` v1.2.

9. **Is the snapshot store reproducible and immutable?**
   - **Yes.** The real store holds no forecast and one blocked attempt.
   - Early and duplicate issuance are refused (tested on a copy).
   - Content hashes are reproducible.

10. **Is the first forecast ready for owner authorization?** **No.** Not before 2027-01-01, and not before the September LFS is retrieved.

11. **Exact blockers:**
    - **B1:** the date (before 2027-01-01).
    - **B2:** the September 2026 national unemployment rate (PSA LFS), due by 2026-12-01.

    **Not blocking, but open:**
    - **D-E125-2** (owner approval): PAR zero-storm quarters are missing instead of 0. Effect: 9 regional historical scores, max 0.042, 1 band change. 2026-Q4 is unaffected.
    - **2025 provincial employment** is incomplete in the source (Batangas unemployment, Quezon underemployment). 2024 is used.
    - **Provisional and unverified publication dates** (PSA release calendars still needed).
    - **IBTrACS 2026 tracks are provisional** (best-track not final).

## Next steps

1. **On or after 2026-12-01:** re-query the LFS (`runner/refresh.py`); confirm September.
2. **Owner decision on D-E125-2** (zero-storm quarters).
3. **On or after 2027-01-01:**
   - refresh all sources (revision check);
   - rerun `run_e125.py --today <date>`;
   - if every condition passes, request owner authorization;
   - then issue through the E124 store.
