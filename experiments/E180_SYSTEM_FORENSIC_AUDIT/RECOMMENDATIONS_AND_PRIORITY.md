# E180: recommendations (in priority order)

## Before thesis submission / demonstration
1. **CRITICAL: make production serve E168 (I01).** Merge `e168-thesis-model` (plus the reviewed service fixes) into `main`, **and**
   change Render's `AIPHEED_LEAD2_MODEL` (or the overlay rule in `e166_serving.enabled()`) so the E168 overlay is active. Verify
   `/api/v1/provinces` returns `e168_high_food_insecurity_probability` on the live URL.
2. **HIGH: fix the driver-share method (I04).** Compute each group's share as Σ|SHAP| of its features ÷ Σ|SHAP| of all served
   features, return `otherPct` (add it to `ExplainabilityResponse`) and show it in the panel, so the five shares plus other sum to 100.
3. **HIGH: correct the frontend descriptions (I02, I03, I09).** Replace "Price-pressure risk" with the E168 indicator name; rewrite
   the Landing/About target, data and seal text for E168; rename "Fish Kill" to "Fish production" (or document it).
4. **HIGH: add the NLP validation (I05).** Put the two annotators' 300-headline files in the repository, compute Cohen's kappa and the
   classifier's precision/recall against the adjudicated labels, and report them; until then call the NLP labels unvalidated.
5. **Thesis wording.** Algorithm 3 (>= 75 %) is the primary reliability rule (E168 reliable to Lead 3); C1-C6 are a supplementary
   check (Lead 1 pass; Lead 2 5 of 6). State that the 72 rows were reused across experiments and that SIMPLE is post hoc.
6. **Qualify drivers (I08):** employment and remittance are national series.

## After submission
7. Unify the news count used by the dashboard and by the model (I10).
8. Regenerate E168 history in the scheduler, or document the manual step.
9. Repair or retire the 27 failing legacy lock tests; stop tests rewriting tracked `.pyc` files.
10. Reconstruct data vintages for CPI, LFS and production where possible (I12).

## Do not change
The E168 model, its locked results, sealed forecast (28f2c918), leakage controls, C1-C6 implementation, the HFIAS target, the map
join, and the LGU ranking formula. These were verified correct.
