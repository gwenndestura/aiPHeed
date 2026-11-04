# R1–R7 validation (C-E2; `out/ce2_results.json`, reproduced byte-identically)

| Rule | What it requires | Lead 1 | Lead 2 |
|---|---|---|---|
| R1 | Full coverage of the verdict window | ✅ 62 quarters, 62 rows | ✅ 62 / 62 |
| R2 | Accuracy ≥ 0.75 | ✅ 0.774 | ✅ 0.758 |
| R3 | Balanced accuracy ≥ 0.70 | ❌ **0.690** | ❌ **0.679** |
| R4 | Accuracy > always-LOW and > persistence | ✅ 0.774 vs 0.307 / 0.661 | ✅ 0.758 vs 0.307 / 0.661 |
| R5 | Brier < persistence and < climatology, one-sided cluster p < 0.10 | ✅ PERSIST −0.151 (p 0.001); CLIM −0.033 (p 0.049) | ✅ −0.151 (p 0.000); −0.034 (p 0.041) |
| R6 | Precision ≥ 0.60 and recall ≥ 0.60 | ✅ P 0.796, R 0.907 | ✅ P 0.792, R 0.884 |
| R7 | Stable over time (thirds; leave-one-quarter-out) | ❌ **thirds 0.952 / 0.524 / 0.850**; LOQO min 0.770; alternative split 0.950 / 0.524 / 0.857 | ❌ **0.952 / 0.524 / 0.800**; LOQO min 0.754 |

**Confusion matrices (TP/FP/FN/TN):** Lead 1 39/10/4/9; Lead 2 38/10/5/9.

**Calibration (ECE, 10 bins):** Lead 1 0.169, Lead 2 0.122. Calibration bins are in `FORECASTING_FAILURE_ANALYSIS.md` §3.

**Causes:** see `FORECASTING_FAILURE_ANALYSIS.md`.
- R3 comes from LOW recall of 0.47 (a HIGH bias).
- R7 comes from the 2015–2020 regime: every model fails that third.
- **The rules were not weakened.**
