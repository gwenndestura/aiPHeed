# E131 deviations and implementation notes

**No deviation changes any result.** Four implementation details are recorded for transparency.

## V1 · Pre-result fixes

Before the first complete run of `runner/e131_x1.py`, four coding errors were fixed. **No result was produced before these fixes.**
1. A region-name match that would have grouped Regions II, III, IV-A and IX with Region I.
2. A comparison on missing publication dates.
3. Interval calibration that could have used targets not yet published.
4. Selection on an empty mask.

Separately, `runner/e131_acquire.py` first sent an empty province list for the threshold table. It received a header only, and the query was corrected before any value was read.

## V2 · Training rows for the seal's learned models

Protocol §9 does not say which rows train the learned models in the seal. The seal uses every P-DASH issue whose target was published before 2026-10-31, the same construction as the walk-forward.

## V3 · Univariate evaluation set

Protocol §2 evaluates each model where *it* has at least 8 observed quarters. So the univariate models (PERSIST, CLIM, LLM, DLLM) are also reported on their own larger set (`out/x1_univariate_*`). There, N3 compares only against persistence and climatology, because the learned baselines do not exist on the early rows.

## V4 · Selection rule

The selection rule (protocol §5) is applied to the shared rows (`out/e131_summary.json`). It selects LLM.
