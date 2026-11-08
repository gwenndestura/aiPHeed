# E111 Addendum 1: Diebold–Mariano variance (written after the first scoring; a correction, not a design change)

**Date:** 2026-10-25.

**Defect.** The protocol (§3, inherited from E110) specifies a one-sided HLN-corrected Diebold–Mariano test with **Newey–West** variance at lag *k* − 1.
- The helper inherited from E110 (`e110_lib._dm_signed`, and E109's `dm_test`) sums the autocovariances with **uniform weights**. That is the truncated kernel, not Newey–West.
- Its variance estimate can be negative. In that case the helper returns p = 0, which happened at Leads 4–6 (BRK, LLR) in the first E111 scoring.
- At Lead 1 (lag 0) the two estimators are identical.

**Correction.** The variance is computed with Bartlett weights, 1 − *j*/(lag + 1), which is the standard Newey–West estimator and is non-negative. Everything else is unchanged:
- the HLN factor;
- the t distribution with *n* − 1 degrees of freedom;
- the one-sided alternative.

**Scope.**
- E111 decisions are recomputed with the corrected test. Both the first-scoring and the corrected results are kept (`out/results_first_scoring.json`, `out/results.json`).
- The effect on E109/E110 p-values is reported in the audit (`out/audit_dm_kernel.json`).
- E109 and E110 files are not modified.

**Not changed.** Methods, rows, criteria and thresholds.
