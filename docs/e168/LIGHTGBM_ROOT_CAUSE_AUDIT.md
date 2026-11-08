# LightGBM root-cause audit

**Reproduced from saved forecasts:** `docs/final/FINAL_FAILURE_AUDIT.md` and `backend/tests/unit/test_final_audit.py`. This document covers only the LightGBM-specific findings.

| Finding | Evidence |
|---|---|
| E158's LightGBM residual adds little province-level signal | E161: E158 real − shuffled inputs −0.037 [−0.090, +0.014], not significant |
| Flexible LightGBM residuals memorise province noise | E163 C2 and E167 LightGBM: real inputs worse than shuffled. E161: RP+R's residual was worse than shuffled (+0.011 [+0.001, +0.024]) |
| Most of the gain comes from the survey baseline, not the trees | E165: with E158's anchor only, Brier 0.163; with own-history anchors, 0.121 |
| C1 at Lead 1 is a sample-size limit | Effective n 45.5; 56 of 72 correct needed |
| C4 is round-level shift, not tree mis-specification | Slope by round: 1.15 / 0.91 / 0.62. Error by round: +6.8 / +5.4 / −2.0. A chronological recalibration failed (`docs/e166/C1_C4_ANALYSIS.md`) |
| LightGBM is not over-biased toward LOW | HIGH recall 0.84–0.92 for every LightGBM model; observed-HIGH error −0.7 to −1.6 points |

**Implication for E168:** the only legitimate LightGBM improvements are:
- a better baseline for LightGBM to correct (baseline-plus-change);
- heavier regularisation and feature pruning, chosen inside training;
- a calibration layer, also chosen inside training.

**No LightGBM setting can recover the 2015→2018 national fall, because no training row at the 2018/2019 origins contains it.**
