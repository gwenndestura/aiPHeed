# S3 pre-registration: 0.5 × S1 + 0.5 × combined logistic (fixed before computation, 2026-11-03)

**Status:** development evidence; the **16th historical attempt** on the same 62 quarters. Any gain is exploratory
and must be confirmed prospectively.

## Hypothesis and definition

**Hypothesis:** averaging S1 (the best R1–R7 model) with the combined logistic regression (the best ranking
component: K1 reached AUC 0.786) raises AUC while keeping S1's accuracy.

**Definition:** p_S3 = 0.5 × p_S1 + 0.5 × p_LOGIT, at the same origin and lead, Leads 1–2.
- p_S1 is read from `out/s1_fits.csv`.
- p_LOGIT is the regenerated LOGIT from `NEW_MODEL/ALLBASE/out/fits.csv`, which reproduces the stored one exactly.
- No weight, threshold or input is tuned.

## Evaluation (as Phase C)

- 62 quarters, Leads 1 and 2;
- all metrics, R1–R7, Algorithm 3 (capped at 2, because LOGIT exists for Leads 1–2 only);
- a 14-test Holm family (S3 × 7 baselines × 2 leads, paired Brier, seed 2036, B 5000), reported separately;
- paired Brier against C-b.

## Gates

| Gate | Condition |
|---|---|
| G1 | All 14 comparisons significant |
| G2 | Brier < C-b at both leads, p < 0.10, accuracy not lower |
| G3 | R1–R7 at both leads |
| G4 | MRLT ≥ 2 |
| G5 | R7 fixed |
| **AUC target** (reported, not a gate) | AUC ≥ 0.80 at both leads |

**Adoption:** G2 and G4, plus team and adviser approval. Otherwise **C-b stays**.
PLAN-SHA256: 0358bac23c97ccb49a9b69be2cb8193bcaa395d67c34e242f01e5b9da9c7758d
