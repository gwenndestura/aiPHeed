# E126 September 2026 LFS refresh readiness

**Process:** `runner/lfs_refresh.py` (tested). **Result on 2026-10-31: BLOCKED.**

## Process

1. **Query** the two PSA OpenSTAT tables with the E114 client:
   - `1B/LFS/0021B3FKEI2.px` (rates; the frozen source);
   - `1B/LFS/0011B3FKEI1.px` (levels: persons in the labour force, unemployed persons, both sexes).
2. **Save** both raw files with fetch time and SHA-256 (`data/raw/`, `data/lfs_refresh_result.json`).
3. **Check** that July, August and September 2026 all carry values. **If any is missing, stop:** status BLOCKED, nothing recomputed.
4. **When complete,** compute the 2026-Q3 national unemployment rate two ways and report both:
   - **frozen E119 method:** mean of the three monthly rates (what every historical FIRI3 value uses);
   - **level-based:** 100 × Σ unemployed ÷ Σ labour force over the three months.
5. **Recompute `E1_unemployment_change_pp`** for 2026-Q3 with the frozen method (vs 2025-Q3), and compare it with the 2-month partial value.
6. **Mark the feature** READY WITH WARNING: its publication date stays rule-based unless a dated release is archived. Then rerun the readiness check.

## Result on 2026-10-31 (07:00 UTC)

| Item | Value |
|---|---|
| Table titles | "Rates Key Employment Indicators: April 2005 to **August 2026**"; "Levels of Key Employment Indicators: April 2005 to August 2026" |
| 2026-Q3 months present | July (6.005), August (5.269); September "." |
| Status | **BLOCKED** (1 of 3 months not published) |
| Raw SHA-256 | rates `88acc6df…`, levels `53c0507f…` |

## Methodology note (for the owner; no change made)

**Your instruction** asked not to assume that monthly rates can simply be averaged. PSA publishes monthly rates and monthly levels. The retrieved tables do not state a PSA method for aggregating months into a quarter.

**Two options:**
- **Level-based rate:** the ratio definition (Σ unemployed ÷ Σ labour force), consistent with how the rate itself is defined;
- **Mean of the monthly rates:** the frozen E119 approach.

Which one PSA uses for quarterly figures should be confirmed from its methodology note before any change.

**What FIRI3 uses.** The frozen E119 input is the mean of the monthly rates. It equals the stored series exactly (checked).

**The difference, on all 22 complete quarters 2021–2026-Q2:**

| Measure | Max \|difference\| | Mean \|difference\| |
|---|---|---|
| Quarterly rate | **0.021 pp** | 0.006 pp |
| Year-on-year change | 0.018 pp | — |

**Effect on FIRI3 of switching to level-based rates:** 0 scores and 0 bands change, because percentile ranks are unchanged.

**Recommendation.** Keep the frozen method (no protocol change). If the owner prefers the level-based definition, it would be a separate amendment; it has no effect on any score so far.

## Definition

| Item | Value |
|---|---|
| Unemployment rate | Unemployed persons as % of the labour force, 15 years and over, both sexes, Philippines (PSA LFS) |
| Reference period | Survey month |
| Publication date | Not archived. Rule: first day of m+3, so September is due by 2026-12-01. |
