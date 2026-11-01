# v4 deviations from the pre-registration

| # | When | What | Substantive? | Effect |
|---|---|---|---|---|
| 1 | First validation run | `fit_delta` crashed on an empty training set (the earliest issues have no inner rows). A guard now returns "no feature, change 0", which is the pre-registered behaviour when nothing passes. | No (bug fix to the stated rule) | No result changes, because the run had not completed before the fix |
| 2 | After the run | Removed a dead no-op line in the shuffle control of `v4_validate.py` | No | Results byte-identical on rerun |
| 3 | Seal | **Sealed baselines.** HFM-X on sealed rows comes from the E134 seal, issued 2026-11-01. That issue had **more** information (the 2026-Q3 round) than the P-DASH issue, so beating it is harder for V4: a conservative comparison. RIDGE-ALL has no prospective forecast, so "beats all" on sealed data can be YES only once it is supplied. | Yes (scope of the sealed test) | `v4_score_sealed.py` reports RIDGE-ALL as NOT_AVAILABLE |
| 4 | EVALUATION_DESIGN | The Balance-Luzon-only counts were rounded down (72 / 32); the computed ceiling is 73 / 33 | No | Doc corrected |
