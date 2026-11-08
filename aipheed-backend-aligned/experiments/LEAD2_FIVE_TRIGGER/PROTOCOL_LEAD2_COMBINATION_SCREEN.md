# LEAD2_COMBINATION: does the hunger × price formula restrict ranking? (development-only screen, frozen before running)

**Branch:** `aiPHeed/lead2-lgbm-tuning`. **Written:** 2026-10-28. The SHA-256 goes in `runner/COMBINATION_SHA256.txt`. Both are committed before `runner/comb_screen.py` runs.

**Question.** P = π_H × π_P is the joint probability of the two Chapter I conditions *if they are independent given the inputs*. Any valid joint probability lies between the Fréchet-Hoeffding bounds max(0, π_H + π_P − 1) and min(π_H, π_P).
- If the conditions are **positively** dependent, the product understates the joint probability, and a combination nearer min(π_H, π_P) would rank and classify HIGH cases higher.
- If they are **negatively** dependent, the product already overstates it, and no theory-consistent change raises HIGH probabilities.

**Screen (development data only; no evaluation row with a target after 2024-Q4 is read).**
1. **Dependence:** the φ coefficient between the hunger condition and the price condition over distinct (province, quarter) labels with targets 2021-Q1..2024-Q4 that have a Balance Luzon reading. 90% quarter-block bootstrap CI (2,000 draws, seed 2031).
2. **Ranking and probability check on Lead-2 DEV rows (targets ≤ 2024-Q4):** AUC and Brier for:
   - P0H4-U's product;
   - the upper bound min(π_H, π_P);
   - the lower bound max(0, π_H + π_P − 1).

**Rule (fixed now).** A combination candidate is built **only if**:
- φ > 0 with the 90% CI excluding 0 (dependence supports moving towards the upper bound), **and**
- the upper bound improves Lead-2 DEV Brier by ≥ 0.005 without a lower Lead-2 DEV AUC.

Otherwise **no candidate is built**: the formula is not the restriction, and P0H4-U is retained.

**Not allowed:** reading targets after 2024-Q4; fitting a combination weight; changing the target, timing, criteria, served model or seals.
