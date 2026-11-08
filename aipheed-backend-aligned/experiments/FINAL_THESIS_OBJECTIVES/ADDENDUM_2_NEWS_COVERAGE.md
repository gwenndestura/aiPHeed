# Addendum 2: news coverage test (regional FSSI-v3)

**Freezing:** this addendum was frozen before the variant below was scored. Its SHA-256 is in `runner/ADDENDUM_2_SHA256.txt`.

## Finding behind it (data audit; no outcome used)

**The provincial FSSI-v3 (N1) is sparse.** It needs at least 5 classifier-admitted headlines tagged to the province in the quarter, and exists in only 20 of 115 province-quarters (17%). Only 33% of headlines carry a province tag.

**Pooled regionally, it would not be.** The same admitted articles, pooled for CALABARZON, reach at least 5 in 20 of 23 quarters. Coverage, not article volume, limits N1.

## Variant: CH1-N1R

**New column, family N1:** `N1R` = the mean XLM-RoBERTa intensity (the FSSI-v3 scorer, no bias weight) of all admitted CALABARZON articles of quarter t published before O(t), whatever their province tag. It is NaN when fewer than 5 articles are scored. It is regional, so every province gets the same value.

**Model:** CH1-LGBM with the audited inputs (Addendum 1) plus `N1R`. Everything else is unchanged.

**Comparison:** against the audited-input CH1-LGBM on the same rows, at Leads 0–4.
- Accuracy and Brier difference (two-sided cluster bootstrap), with Holm correction across leads.
- The reliability rule R1–R7 applied to the variant.

**What it can decide:** news coverage is said to add value only if the variant's Brier score is significantly lower (Holm p < 0.05) at a lead. Otherwise the result is "coverage fixed, no forecast gain". The primary model is not replaced by this variant unless that test passes.
