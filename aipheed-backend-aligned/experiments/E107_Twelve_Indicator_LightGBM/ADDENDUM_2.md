# E107 Addendum 2: one exploratory revision. Frozen after the development results, before the final block

**Date:** 2026-10-25.

**What had been seen.** The development-block metrics (`out/dev/metrics.json`) and the per-origin split gains.

- T43 Lead 1, E107-LGBM: accuracy 0.60, AUC 0.83, HIGH recall 0.42 on 20 rows. On the same rows RULE scores 0.85 and E56 0.85.
- R Lead 1: accuracy 0.50, Brier 0.30, against H1-alone 0.75 / 0.12.
- The final block (2025-Q4..2026-Q3) has not been scored by any E107 model.

**Diagnosis (mechanism, not a code defect).**

1. **Spurious splits in tiny training sets.**
   - At the first T43 Lead-1 origins (50–55 rows, 5 HIGH), the largest gain is on E2, whose missing pattern separates 2021 rows from 2023 rows.
   - The R model (6–13 rows) splits on A3, A2 or C4, almost never on H1.
2. **The learner must rediscover the label's own structure from very few HIGH rows.** T43 is HIGH when hunger is above 11.3 **and** prices are above the province threshold. A plain booster starts from the training base rate (mostly LOW before 2023-Q4). The structural information in A1 and H1 is then learned only through a handful of splits.

**The one revision (arm SP, "structural prior").** LightGBM boosts **from** the definition's structural probability, instead of from the base rate.

- **T43 prior:** p0 = H1 × [1 − (1 − Φ(A1_food / σ_F)) (1 − Φ(A1_gap / σ_G))].
  - σ_F and σ_G are the RMSE of the projection's own errors on the fit rows. These are the realised minus projected distance to the threshold, using labels known at the origin. With fewer than 4 fit quarters, σ = 2.0.
  - This is the H1 construction (latest value plus the spread of its own past errors) applied to the price condition.
- **R prior:** p0 = H1.
- **Model:** the same 13 columns, grid, nested selection (σ recomputed on each inner fit set), threshold 0.5 and seed as E107-LGBM.
  - `init_score` = logit(clip(p0, 0.01, 0.99)) in both fit and prediction.
  - Missing p0 is replaced by the training HIGH share.
- **STRUCT:** p0 alone, with no learning. Reported as a baseline.

**Status and rules.**

- **SP is exploratory.** It was designed after the development results, so its development-block metrics are not evidence.
- **Its clean evidence is:**
  - the final block, scored once, in the same run as E107-LGBM;
  - the sealed prospective forecasts.
- The §8 criteria are computed for SP on combined rows and on the final block, and labelled "exploratory (development rows seen)".
- The final block has 4 quarters, below R1's 6. **SP therefore cannot be declared reliable from E107 data.** It can become a candidate for prospective validation only.
- **The primary decision is unchanged:** E107-LGBM is judged by §8 as frozen.
- No further model revision is made in E107.
