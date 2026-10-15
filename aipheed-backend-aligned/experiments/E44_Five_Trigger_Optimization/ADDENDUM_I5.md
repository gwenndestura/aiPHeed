# E44 addendum: iteration I5 (frozen before any I5 score), the last pre-registered iteration

**Written:** 2026-10-15, after I4 (`runs/i4_*`, commit following 26ea54b).
**Freeze:** SHA-256 of this file (LF) in `runner/ADDENDUM_I5_SHA256.txt`, committed before I5 is fitted. Run once, then a byte-identical repeat.

## Why I5 (diagnosis and disclosure)

**I4** (joint food/gap distribution): accuracy 0.543, balanced 0.438, AUC 0.51. It is worse than I2 (0.686 / 0.716 / 0.60).

**Diagnosis, from I2/I4 selection logs:**
- At **every** origin, the inner selection picked the most flexible residual model: LightGBM with 4 leaves.
- The inner validation was blocked leave-one-target-quarter-out. On a strongly autocorrelated quarterly series, the neighbouring quarters on **both** sides of a held-out quarter inform the fit. Flexible models that track the time path score well inside, then fail forward.
- **This is a methodological flaw of the inner-validation design**, independent of the outer result.

**Disclosure:** I5 is the fifth look at S44. It changes the selection mechanism, not the features, target or outer rows.

## The I5 change (otherwise identical to I4)

1. **Forward-chaining inner validation** everywhere a choice is made inside training, replacing leave-one-quarter-out:
   - the food residual configuration, the gap residual configuration, the hunger ridge α, ρ, the out-of-fold joint probabilities, the threshold, and Platt.
   - The inner test quarters are the latest 6 training target quarters, each predicted from training pairs with earlier target quarters only (at least 4 earlier target quarters).
   - Predictive SDs are the forward RMSEs.
2. **Grid:** ridge α ∈ {1, 10, 100, 1000} (α = 1000 lets the data shrink the trigger effects almost to zero while keeping the five triggers in the model) plus the same LightGBM options. Ties go to the simpler configuration (ridge before LightGBM, larger α first).

**Unchanged:**
- **five triggers mandatory**;
- T43;
- S44 rows;
- gates A0–A4;
- I4-MKT-style variants: I5-MKT and drop-one.

**Final-candidate rule:**
- I5 becomes the final candidate if it passes A0–A4.
- Otherwise the final candidate remains I2, the pre-declared five-trigger design, with **"forecasting acceptance NOT met"**.
- **No further iteration is pre-registered.** If I5 fails, the report documents the blocker with a discrimination-ceiling analysis instead of further looks at S44.

**Prospective freeze:** `frozen/E44_I5_PROSPECTIVE_2027Q1.json` (sha256).
