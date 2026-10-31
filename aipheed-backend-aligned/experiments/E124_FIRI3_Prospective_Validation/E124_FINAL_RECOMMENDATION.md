# E124 final recommendation

## Classification: **BLOCKED** (first issuance), with the process ready

**The prospective process is in place and tested:**
- frozen configuration;
- append-only store;
- correction and observation records;
- release monitoring;
- the FIRI v2 comparison.

**The 2026-Q4 forecast cannot be issued today (2026-10-31).** Its issue date is 2027-01-01, and four inputs must be refreshed after their releases.

**Nothing was issued, estimated or fabricated.** The attempt is recorded as blocked in `store/registry.jsonl`.

**Next step.** Once the four refreshes below are done on or after 2027-01-01, rerun the readiness check. If C1–C4 pass, issue. The issued forecast will still carry the warnings below, so its expected classification then is READY WITH WARNINGS.

## Answers

1. **Is the E123 methodology correctly frozen?**
   - **Yes.** `E124_FROZEN_VALIDATION_CONFIGURATION.json` (SHA-256 in `.sha256`) records the version, the protocol and amendment hashes, all 34 features, indicators, weights, aggregation, completeness, bands, cutoff, publication rules, geography, issue rule, issuance conditions, schema and evaluation rules.
   - The runner refuses if the module drifts from it.
   - A fresh run reproduces E123 exactly.

2. **Are Amendments 1 and 2 active?** **Yes.**
   - Hashes match.
   - Amendment 1 rejects 40 CPI rows (73 scores changed vs E121).
   - Amendment 2 uses the latest complete annual year (10 scores changed vs E122).

3. **Are the sources ready for the first prospective forecast?**
   - **Not yet.** 22 features are released and in hand (publication date unverified), and 2 are released and verified.
   - **5 are retrieved but incomplete:** cyclones within 100 km and in PAR for 2026-Q3; LFS 2026-Q3 with 2 of 3 months; provincial 2025 employment, incomplete in the source.
   - **4 need a refresh:** NASA POWER rainfall and heat, provincial and regional.
   - **1 is not applicable** (static poverty).

4. **Which features remain provisional or unverified?**
   - **Verified (4):** cyclones within 100 km, cyclones in PAR, FSSI-v3, GDELT.
   - **Unverified (3):** EHS provincial unemployment and underemployment, PSV poverty. Their dates are assumptions.
   - **Provisionally eligible:** the other 27. This includes CPI, whose day-10 rule is later than some archived PSA releases in 7.8% of rows.

5. **Is the 2027-01-01 issuance condition satisfied?** **No.**
   - C1 (date) is not met.
   - C3 (refreshes) is not met.
   - C2 and C4 are met.

6. **Missing inputs:**
   - NASA POWER monthly rainfall and temperature for 2026 (held to 2025-12);
   - IBTrACS-based cyclone counts for 2026-Q3 (within 100 km and in PAR), recomputed after the quarter closed;
   - the LFS September 2026 national unemployment rate (due 2026-12-01).

   **Not blocking but open:** the 2025 provincial employment values missing in the source (Batangas unemployment, Quezon underemployment).

   **For the following quarter:** collect the news corpus beyond 2026-10-14.

7. **Can the snapshot be reproduced and protected?**
   - **Yes (tested on controlled records).** The canonical content hash is reproducible.
   - A second issue is refused, an edit is detected, and corrections are separate records.

8. **Can later revisions be distinguished from the original forecast?** **Yes.** `Store.observe` records three separate things:
   - forecast stability (original unchanged);
   - data revisions (same period, new value);
   - new information (later periods, availability changes).

9. **Is the FIRI3 vs FIRI v2 comparison reproducible?**
   - **Yes.** `E124_FIRI3_VS_FIRI2_COMPARISON.csv` is built from the stored E121, E122 and E123 outputs and the served v2 history.
   - **Agreement:** 75 matched province-quarters, Spearman −0.28, 40% agreement on the side of 0.5 (v2 HIGH 81%, FIRI3 ≥ 0.5 45%), province-rank ρ −0.07.
   - **Not computable:** 20 v2 rows lack a FIRI3 score.

10. **Is prospective monitoring operational?**
    - **Yes.** `E124_SOURCE_RELEASE_STATUS.csv` covers every feature: rule, needed period, in-hand period, retrieval date and status.
    - Rerun `run_e124.py --today <date>` to update it.

11. **Has any production behaviour changed?**
    - **No.** FIRI v2 files are unchanged by hash; `backend/app`, `frontend/src` and `backend/data` have no changes.
    - Nothing was deployed, pushed or merged.

12. **Status: BLOCKED** for first issuance (date and inputs), with the process ready. Expected to become **READY WITH WARNINGS** after the 2027-01-01 refresh.

## Warnings that will remain at issuance

- **Rule-based dates:** 27 features are provisional and 3 unverified. The CPI rule is sometimes optimistic.
- **Batangas 2024 underemployment (39.5%)** is unverified.
- **Most scores sit near usual:** 88% of provincial historical scores are within chance variation of 0.5.
- **One quarter proves nothing.** FIRI3 is a relative index, not a probability, and has no provincial outcome. A single prospective quarter gives no predictive validity.
- **SWS stays external and descriptive only.**
- **The thesis LightGBM-vs-four-baselines comparison remains a separate experiment.**
