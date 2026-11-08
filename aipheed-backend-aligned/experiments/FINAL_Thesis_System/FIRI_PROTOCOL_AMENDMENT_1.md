# FIRI v1, amendment 1 (made before any FIRI value or label was scored)

**Date:** 2026-10-20. This amendment is frozen before scoring; its SHA-256 is in `runner/FIRI_AMENDMENT_1_SHA256.txt`.

## Why

Computing the anchors under the original section 3 (window 2021-Q3..2022-Q4; `out/firi_anchors_v0_original_window.json`, kept unchanged) made two problems visible. No label was loaded, and no FIRI value was computed.

1. **Two domains disappeared.**
   - The national employment (E1) and remittance (E2) series have only 3 values in that window, because they start in 2022-Q1 in the feature table.
   - FSSI-v3 (N1) has 1 SUFFICIENT province-quarter.
   - The section 3 rule (at least 5 values) therefore removes domains E and N entirely.
2. **Most origins became unscorable.** With V withheld before 2025-07-01 (section 5), only domains A, C and H remain at the six origins issued before 2025-07-01. The section 4 minimum of 4 domains then makes FIRI INSUFFICIENT DATA at 6 of the 10 Lead-2 evaluation origins.

These are feasibility failures of the rules, not results. The amendment changes data coverage only. Weights, threshold, directions and the scoring formula are unchanged.

## Changes

| Section | Original | Amended |
|---|---|---|
| Section 3 anchor window | 2021-Q3..2022-Q4 | **2021-Q3..2023-Q4** for every continuous indicator |
| Section 5, V1 | missing before 2025-07-01 | **static** structural profile at every origin |
| Sensitivity | — | strict V1 timing (the original rule) |

**Anchor window.** The new window ends at the first Lead-2 evaluation origin (2023-Q4, issued 2024-01-01). No origin's anchors use predictor values from after that origin. The anchors still use predictors only, never labels.

**V1.** PSA 2021 SAE poverty and POPCEN 2024 density are used as a static structural profile at every origin: the province's long-run poverty and population structure, the same at every quarter. This is a **publication-timing deviation** for origins before their release, and it is disclosed.

**Strict V1 sensitivity.** The original section 5 rule is reported as a sensitivity:
- FIRI is computed with V1 missing before 2025-07-01;
- origins left with fewer than 4 domains are reported as not computable;
- it is never used to select anything.

Everything else in FIRI_PROTOCOL.md is unchanged.
