# E11 Model Selection

## Decision

**Primary forecasting method: the S1 formula rule.** It is presented as a formula-based forecast, not a learned model. **LightGBM remains experimental.**

This follows the prespecified rule (`E11_PROTOCOL.md` §6): no nested LightGBM candidate met all four criteria against the S1 rule. It is also consistent with the evidence below.

## Evidence for each question

| Question | Answer | Basis |
|---|---|---|
| Does LightGBM improve over carry-forward? | **Yes, for two candidates.** Direct core: −0.43 [−0.78, −0.08], 6/7 quarters. Residual: −1.48 [−2.79, −0.17], 5/7. | `RESULTS_SUMMARY.md` §2 |
| Over regional hunger alone? | **Not established.** The best is residual at −0.72 [−2.18, +0.48], 3/7 quarters. | Same |
| Over the S1 rule? | **Not established.** The best is residual at −0.80 [−2.20, +0.29], 4/7 quarters, with the gain concentrated in 2024-Q4 and 2025-Q1 and a loss in 2025-Q4. Direct models are worse than S1 (+0.24 to +1.11). | Same |
| Across many quarters, or one period? | The residual gain is **two quarters** (the peak) | Per-quarter differences |
| Provincial differentiation? | **Direct models: no** (spread collapses). Residual: kept (0.629). Decomposed: best ranking (0.707), but no error gain. | `PROVINCIAL_DIFFERENTIATION.md` |
| Stable across training windows? | Same direction under the rolling window, but smaller (residual −0.53 vs S1). Nested choices change fold to fold, and the rolling window has only 1 inner quarter. | `MODEL_CONFIGURATIONS.md` §3 |
| Uncertainty | **Too large for a reliable conclusion.** 7 reused quarters; intervals cross zero against S1. | — |

## What this means for the thesis

- **The cleanest ML result is "LightGBM beats carry-forward".** It does **not** beat the transparent S1 rule reliably.
- **The residual design (S1 rule + LightGBM correction) is the most promising experimental variant.** Its lower average error (3.74 vs 4.55) is **not established:** the improvement sits in two peak quarters and reverses at the turning point. It is worth testing on new quarters, starting with the sealed 2026-Q4 forecast cycle and later quarters, **before** any claim.
- **No non-inferiority claim is made,** because no margin was prespecified.
- **Model selection did not use the 75% accuracy target.**
