# NOISE_W: results (EXPLORATORY, one candidate)

**Plan:** `PLAN.md`, SHA-256 `0c00cedd…831e`, committed before the fit (`4f6b1d7`).

**Check:** the same code with all weights = 1 reproduces the stored C-b (904 rows, max |Δp| = 1.1e-16).

## Decision (fixed rule)

**C-w does not improve C-b, and it does not beat all six baselines.** C-b stays the main model.

| | C-w L1 | C-b L1 | C-w L2 | C-b L2 |
|---|---|---|---|---|
| Accuracy | 0.790 | 0.790 | 0.790 | 0.790 |
| Balanced accuracy | 0.717 | 0.717 | 0.717 | 0.717 |
| Precision / recall | 0.812 / 0.907 | same | 0.812 / 0.907 | same |
| F1 | 0.857 | 0.857 | 0.857 | 0.857 |
| AUC | 0.691 | 0.702 | 0.696 | 0.704 |
| Brier | 0.181 | 0.187 | 0.178 | 0.184 |
| Rules failed | R7 | R7 | R7 | R7 |

- **C-w vs C-b:** Brier −0.007 (p 0.208) at Lead 1 and −0.005 (p 0.284) at Lead 2; **0 calls changed**. Algorithm 3:
  MRLT 2 for both.
- **H3** (C-w minus comparator, Holm):
  - Lead 1: persistence −0.158 (0.001), NLP-only −0.189 (0.004), **PSA-only −0.027 (0.380)**, **LOGIT −0.012
    (0.380)**, LightGBM government-only −0.052 (0.028), LightGBM NLP-only −0.143 (0.006).
  - Lead 2: PSA-only −0.061 (0.069), LOGIT −0.056 (0.083), LightGBM NLP-only −0.123 (0.069).

  The two logistic regressions are still not beaten significantly.

**Reading.**
- Down-weighting the near-threshold quarters slightly sharpens the probabilities (lower Brier) and costs a little AUC.
- It changes no HIGH/LOW call, so it cannot touch R7.
- With 62 quarters the gap to the logistic regressions stays inside noise.
