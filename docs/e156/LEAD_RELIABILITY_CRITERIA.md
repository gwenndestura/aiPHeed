# Reliability criteria for each forecast lead

Written 2026-11-06 before this evaluation was run. **Disclosed:** E151's headline numbers by lead were already seen in earlier reports, so these criteria are not blind to them. They are fixed here so that the lead decision follows a stated rule, not a choice made per lead.

A lead is **reliable** only if all of these hold on the 72 province rows (50 at Leads 7 and 8):

| # | Criterion | Why |
|---|---|---|
| C1 | Accuracy above the majority-class rule, with the lower end of its 95 % interval above that rule at the effective sample size | Useful classification, not a constant guess |
| C2 | Brier below persistence, 95 % region-bootstrap interval below 0 | Better than the old survey |
| C3 | HIGH recall and LOW recall both at least 0.50 | Both classes meaningful |
| C4 | Calibration slope 95 % interval includes 1 | Probabilities not systematically over- or under-confident |
| C5 | Accuracy at least persistence's in at least 2 of the 3 rounds | Consistent across periods |
| C6 | At least 40 rows | Enough rows for the conclusion |

**Maximum reliable lead** = the longest run of consecutive reliable leads starting at Lead 1. If Lead 1 fails, no lead is reliable and the model has not passed validation. Leads beyond the first failure are reported but not counted.

Lead 1 is mandatory, and no other lead can stand in for it.

Effective sample size for C1 comes from the E156 audit: errors are shared within a round and region (73 % of error variance), so 72 rows count as about 46 independent ones.
