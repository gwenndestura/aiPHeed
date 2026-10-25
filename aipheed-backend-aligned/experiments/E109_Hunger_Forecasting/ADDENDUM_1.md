# E109 Addendum 1: known-at-issue rule (frozen before any E109 model was scored)

**Date:** 2026-10-25. **Seen:** no E109 result. The defect was found by the leakage test `test_future_sws_rounds_do_not_change_any_forecast`, before the first scoring run.

**Defect.** Protocol §1 counts H_q as known at O(*t*) only if *every* round of *q* was published before O(*t*). This uses future information: whether a further round of the same quarter will be published later.

Example: at the issue date 2025-07-01 the April 2025 round (17.0, published 2025-06-27) was public. The rule hid it because the June round would be published on 2025-08-15. A real-time user would have had 17.0.

**Change.**
- **Value known at issue date O(*t*):** the mean of the primary rounds of quarter *q* published before O(*t*). This is the real-time vintage, identical to the served `thesis_system._posted`.
- **This value is used for:**
  - H_last;
  - the training targets of pairs;
  - MEAN, MA2, SEAS, LL and σ̂.
- **Evaluation outcome:** the final mean of all primary rounds of the target quarter (unchanged).

**Affected quarters.** Only quarters with two primary rounds (2021-Q2, 2022-Q2 and 2025-Q2) can have a vintage different from the final value.

Nothing else changes.
