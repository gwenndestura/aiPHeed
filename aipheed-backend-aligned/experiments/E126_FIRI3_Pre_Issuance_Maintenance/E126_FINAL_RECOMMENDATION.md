# E126 final recommendation

## Result: **BLOCKED**

**Blockers:**
- **B1:** the issue date, 2027-01-01, has not arrived.
- **B2:** the September 2026 national unemployment month is still unpublished. PSA's tables end at August 2026, re-queried 2026-10-31.

**Done in E126:**
- **D-E125-2 resolved on evidence:** the three PAR quarters are true zeros. The correction is prepared as Amendment 3 and **awaits approval**.
- **LFS:** the September refresh process is built and tested.
- **Sources:** no new source blocker appeared.

**Not done in E126:** no forecast was issued, and no frozen rule was changed.

## Answers

1. **Does the E125 baseline reproduce?** **Yes.**
   - The configuration, protocol and amendment hashes match.
   - The E125 refreshed inputs reproduce (NASA 2026-01..09; PAR 2026-Q3 = 7; local 2026-Q3 = 0).
   - The store is empty, with one blocked attempt.
   - FIRI v2 is unchanged.

2. **Are both amendments active?** **Yes.** Amendment 1 rejects 40 CPI rows. Amendment 2 uses 2024 for annual employment, because 2025 is incomplete in the source.

3. **Are the three PAR quarters genuinely zero?**
   - **Yes.** E114's full WP IBTrACS file has **no track point anywhere in the Western Pacific** in 2023-Q1, 2024-Q1 and 2025-Q1.
   - The last-3-years file agrees for 2024-Q1 and 2025-Q1. It does not cover all of 2023-Q1.
   - No storm entered under the approved box or the official PAR outline.

4. **Is Amendment 3 justified?**
   - **Yes.** The values are observed zero counts. They were lost through an extraction defect: `groupby(q).size()` has no rows for zero-storm quarters.
   - Without the fix, the as-of rule substitutes an older quarter's count.

5. **Which historical scores and bands would change?**
   - **9 regional FIRI3 scores** (origins 2024-Q2 to 2026-Q3, excluding 2025-Q4), max |Δ| 0.042, with **1 band change**: 2025-Q2, above usual → usual or below.
   - **CCS:** the same 9 rows.
   - **Provincial:** none.
   - **FIRI v2 comparison:** not affected.

6. **Does it affect the 2026-Q4 forecast?**
   - **Yes.** The regional PAR feature's percentile goes from 0.711 to 0.750; the 2026-Q3 count of 7 is unchanged.
   - **Decide before issuance.**

7. **Is the September LFS refresh ready?**
   - **Yes.** `runner/lfs_refresh.py` queries both PSA tables (rates and levels), hashes them, refuses to proceed without all three months, and reports both quarterly methods.
   - **Methods:** the frozen method (mean of monthly rates) stays. The level-based alternative differs by at most 0.021 pp historically and changes no FIRI3 score. Whether PSA's own quarterly aggregation is level-based should be confirmed from its methodology note.

8. **Any additional source blockers?**
   - **No.** The Region IV-A CPI index was re-queried: 0 revisions, no new months.
   - NASA, IBTrACS and the E118 tables were refreshed the same day.
   - Every other feature already holds the period its release rule makes available before 2027-01-01.

9. **Feature status** (for the 2026-Q4 issue):

   | Status | Count | Features |
   |---|---|---|
   | READY | 4 | cyclones ×2, FSSI-v3, GDELT |
   | READY WITH WARNING | 29 | 26 provisional (rule-based) dates; 3 unverified (EHS provincial ×2, PSV) |
   | BLOCKED | 1 | EHS_unemployment_change_R |

10. **Is 2026-Q4 readiness improving?**
    - **Yes.** Since E124:
      - the NASA POWER and cyclone blockers are cleared (E125);
      - 33 of 34 features are already available for the rule-defined periods;
      - the one remaining feature is expected before the issue, by rule 2026-12-01.
    - **Unchanged:** no 2026-Q4 observation is required, because no source's rule makes one available by 2027-01-01.

11. **Is the snapshot store still reproducible and immutable?** **Yes**, retested on controlled records: unique IDs; early and duplicate issues refused; tamper detection; corrections and observations kept separate.

12. **Ready for issuance preparation?**
    - **Not yet.** B1 and B2 remain.
    - The Amendment 3 decision should be taken before the final pre-issuance check, because it changes the 2026-Q4 regional value.

## Also recorded

**C-E126-1.** `firi3._dynamic` now selects the latest row by position, so repeated index labels can't break it. Version 1.2 is unchanged and no result changes.

**Historical versions** are kept side by side in `E126_HISTORICAL_SCORE_RECONCILIATION.csv`, with the cause of each change:

| Version | Change |
|---|---|
| E121 v1.0 → E122 v1.1 | Amendment 1, 73 rows |
| → E123 v1.2 | Amendment 2, 10 rows |
| → E125 refreshed | new NASA observations, 12 rows |
| → E126 proposed | Amendment 3, 9 regional rows; PROPOSED, not applied |

## Next steps

1. **Owner decision on Amendment 3.**
2. **On or after 2026-12-01:** run `runner/lfs_refresh.py`.
3. **On or after 2027-01-01:**
   - refresh all sources;
   - rerun the readiness checks;
   - request owner authorization;
   - issue through the E124 store.
