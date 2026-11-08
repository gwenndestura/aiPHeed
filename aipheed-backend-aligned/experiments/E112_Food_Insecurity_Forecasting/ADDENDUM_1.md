# E112 Addendum 1: the two remaining Chapter I Objective-4 baselines

**When.** Written after the main E112 scoring run and before these two arms were computed. Nothing in `PROTOCOL.md` changes: candidates, tests, reliability rule and final-method decision rule are untouched.

**Why.** Chapter I Objective 4 compares the proposed LightGBM with four baselines: persistence, PSA-only, NLP-only and logistic regression. The frozen protocol covers two of them:
- persistence = RW;
- NLP-only = NEWS-C and NEWS-G.

The other two were missing. For the continuous outcome they are defined as follows.

| Id | Definition |
|---|---|
| PSA-R | **PSA-only baseline.** Latest reading + ridge (E110 `_ridge`, alpha 10) on the PSA-sourced columns: A1_food, A1_gap, A2 (CPI), A3 (wholesale rice), C3 (palay/corn), C4 (fisheries), E1 (LFS unemployment). Same E109 training pairs. |
| RIDGE13 | **Linear-regression baseline.** E109 `forecast("RIDGE")` unchanged: ridge on all 13 columns. A logistic regression needs a binary outcome, and E109 showed the binary readings have one-class evaluation sets. The linear model on the continuous outcome is therefore the regression baseline. |

**How they are used.**
- Both arms are comparison baselines only. They are **not** added to the final-method order (PROTOCOL §5).
- Reported per lead:
  - MAE;
  - one-sided Newey–West DM vs RW;
  - DM of LGBM12 and LGBM12N against each, with H1 that the LightGBM is better.
- Holm correction over the 4 leads within each comparison.
