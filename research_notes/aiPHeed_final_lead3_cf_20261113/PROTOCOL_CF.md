# PROTOCOL_CF — seasonal-gap carry-forward of local price inputs (written 2026-11-13 BEFORE any CF fit is run or scored)

## Defect (found by inspecting INPUTS, not outcomes)
Local price inputs (`l_fg_yoy`, `l_fg_rel`, `l_terms`, `l_rice_yoy`, `l_rice_rel`, `l_fish_yoy`; app/e152 panel) use the 3 months ending
3 months before the issue date. Every Lead-3 origin is a 1 October issue, so the window is May-July (palay lean season), when several
provinces report no farmgate palay price. Result: at Lead 3 only, 2-5 more test provinces per round (and the matching training rows) have
these inputs missing (2018: +3/+4, 2019: +3, 2021: +5 vs Leads 2/4).

## Correction CF (the only change)
For each province, a missing local-price value at quarter i is replaced by that province's value at quarter i-1 (limit: ONE quarter;
older values stay missing and MIND handles them as before). The quarter i-1 value was itself built from data published before quarter
i-1 began, so it was available at origin i: no future information. Applied identically to every training and test row, every fold, every
lead (1-8), all 5 seeds. Model, settings, threshold (0.50), seeds and everything else: unchanged.

## Decision rule (fixed now; evaluated once)
CF is ADOPTED only if ALL hold (5-seed mean probabilities, thesis definitions):
 1. Algorithm 3 MRLT(CF) >= 5.
 2. For every lead 1-5: mean fold accuracy(CF) >= mean fold accuracy(FINAL) - 0.0133 (one province in one 25-province fold).
 3. Pooled Brier over Leads 1-5: CF <= FINAL.
 4. Every lead in {1, 2, 4} that meets F1 >= 0.75 under FINAL still meets it under CF.
Otherwise FINAL is kept unchanged and Lead 3 remains FAIL on F1. The Lead-3 F1 result is reported either way; it is NOT a criterion.

## Honesty statement
The defect was investigated because Lead 3 failed F1; the fix is a standard data-handling rule chosen from the input pattern, but it is
still evaluated on the same 72 reused outcomes, so any result is retrospective, not independent validation.
