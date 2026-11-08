# E129 R1–R7 provincial applicability

**Frozen rule.** `FINAL_THESIS_OBJECTIVES/FINAL_TARGET_AND_EVALUATION_PROTOCOL.md` §7, as used in E128.

**Nothing is weakened or removed.** Where a panel needs a different reading, an **amendment for owner approval** is proposed. None is applied.

| # | Criterion | Appropriate for a 5-province panel? | Attainable? | Panel-aware interpretation needed | Dependence issue | Per lead? |
|---|---|---|---|---|---|---|
| R1 | ≥ 10 target quarters and ≥ 40 rows | Yes; it was written for province-quarter rows | Food-CPI target: Leads 1–4 give 14 / 13 / 12 / 11 evaluation quarters and 70 / 65 / 60 / 55 rows (8 training quarters). FI targets: no. | **Yes.** The 40 rows must be distinct province observations. Report effective rows (design effect; for example 70 rows ≈ 18 effective at Lead 1). | Same-quarter rows share 74 % of variance | Yes |
| R2 | Accuracy ≥ 0.75 | Binary targets only | — | **A continuous target needs an amendment.** Proposed A-R2c: skill ≥ 0.25 (MAE reduction vs persistence), or interval coverage, fixed before fitting. | — | Yes |
| R3 | Balanced accuracy ≥ 0.70 | Yes (binary). Not evaluable when one class is missing (E128 lesson). | Depends on the class split | Pooled, plus reported per province | — | Yes |
| R4 | Accuracy > majority and > persistence | Yes | — | **Persistence must be per province** (its own last value). A pooled majority is fine. | — | Yes |
| R5 | Brier < persistence and < CLIM, one-sided paired **cluster** bootstrap p < 0.10 | Yes. Already cluster-based. | — | **Clusters must be target quarters, not rows**: a panel row bootstrap overstates n about 4×. CLIM per province (training base rate). | Central | Yes |
| R6 | HIGH precision ≥ 0.60 and recall ≥ 0.60 | Yes (binary) | — | Pooled; per-province reported, not required (≤ 14 rows each) | — | Yes |
| R7 | Accuracy ≥ 0.60 in each third of the quarters; leave-one-quarter-out minimum ≥ 0.70 | Yes. Leave-one-quarter-out removes all 5 provinces of a quarter (correct clustering). | — | **Proposed addition A-R7p** (strengthens, does not weaken): no province with accuracy < 0.50 (or skill < 0) over its rows | Yes | Yes |

## Proposed amendments (owner approval required; none applied)

| Amendment | Change |
|---|---|
| A-R1p | R1 rows count only genuine province-specific target observations. Copied regional values count once per quarter. Effective rows are reported. |
| A-R2c | For a continuous target, replace R2 / R3 / R6 with a pre-registered skill rule (MAE skill vs per-province persistence ≥ 0.25; 80 % interval coverage within 0.70–0.90), with R5 on squared error. |
| A-R4p | Persistence = each province's own latest value. |
| A-R7p | Province-consistency floor (added, not replacing R7). |

**None of these makes a provincial food-insecurity claim possible.** They only define how a valid provincial target would be judged.
