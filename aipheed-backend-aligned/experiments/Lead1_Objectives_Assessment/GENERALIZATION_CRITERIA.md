# Lead-1 cross-quarter generalization: criteria fixed before any quarter-level result is examined

**Written 2026-10-21, before computing per-quarter Lead-1 metrics.** Only pooled Lead-1 figures had been seen at that
point. Committed before the analysis runs.

## Models assessed

All are walk-forward, on the E83/E84 rows: 65 Lead-1 forecasts, 13 target quarters × 5 provinces.

| Arm | Description |
|---|---|
| S-SIM | Pre-registered in E83. The source of the 84.6% figure. |
| LightGBM (`M-GB-ALL`) | The proposed model, on its 30 issued rows |
| HYB-GBA-SIM | Post-hoc |
| ENS-ROLL | E88, pre-registered |

**Baselines:**
- naive persistence (latest label available at the origin);
- the PSA-only and NLP-only logistic baselines;
- the all-feature logistic regression;
- climatology / training majority;
- always-LOW.

## Unit of analysis

The **target quarter**. Each quarter has 5 province rows that share one regional hunger reading, so the rows are not
independent.
- Uncertainty uses a bootstrap that resamples whole quarters (2,000 draws).
- Tests compare models quarter by quarter, never row by row.

## Pre-set definitions

| Term | Definition |
|---|---|
| Quarter correct-majority | A quarter where at least 3 of the 5 provinces are classified correctly (quarter accuracy ≥ 0.6). With 5 rows per quarter, 3/5 is the smallest majority. |
| Early period | Targets 2023-Q1 .. 2024-Q4 (8 quarters) |
| Late period | Targets 2025-Q1 .. 2026-Q3 (5 quarters) |
| Changing-risk rows | Rows whose label differs from the latest label known at the origin: **rising** (0 to 1) and **falling** (1 to 0) |

## Verdict rules (applied to S-SIM, the model behind the reported 84.6%)

1. **Consistent across quarters** requires all of:
   - (a) quarter correct-majority in at least 80% of evaluated quarters;
   - (b) accuracy at least 0.75 in **both** the early and the late period;
   - (c) per-quarter accuracy ≥ persistence's in more quarters than it is lower (ties excluded), with a one-sided sign
     test p < 0.10;
   - (d) HIGH recall ≥ 0.5 pooled, and at least one HIGH row caught in each period that contains HIGH rows;
   - (e) on changing-risk rows, accuracy above persistence's (persistence is wrong on them by construction) and at
     least 0.5.
2. **Partially generalized:** criterion (a) holds for at least 60% of quarters, but one or more of (b)–(e) fails.
3. **Not demonstrated to generalize:** (a) holds for fewer than 60% of quarters, **or** a leakage defect is found that
   cannot be corrected.

## Separate question: food-insecurity versus proxy

Generalization to **food insecurity** is claimed only if it is shown against an independent food-insecurity
measurement. At Lead 1 the only quarterly one is regional SWS hunger (13 quarters). Province-level T43 accuracy is
reported as **proxy-target** performance.
