# STAB-TUNE: careful, stable nested tuning of C-B6 and C-B6E (pre-registration, fixed before any fit, 2026-11-04)

**Owner directive (2026-11-04):** "optimize the model, tune it carefully, analyze deeply".

**Development evidence:** attempts 28–29 on the same 62 quarters, disclosed as such.

## Diagnosis that motivates the design (computed before this plan; no model was fitted for it)

1. **Selection is unstable.** C-b/C-B6 choose 1 of 8 settings at each origin from only the last 4 training origins.
   - In the 68 evaluation-era origins the choice switches 26 times (C-B6), and 25 times for C-B6E.
   - C-B6's R1–R7 pass rests on one such switch (origin 2018-Q3, `out/obj2_cb6_fragility.json`).
2. **E1 and E2 carry little and unstable signal** at Lead 1 (Spearman, 62 quarters):

   | Input | vs the label | vs the change from the latest reading |
   |---|---|---|
   | E1 | +0.24 (p 0.06) | −0.07 |
   | E2 | −0.12 | 0.00 |

   - The sign of each against the change flips across the three eras.
3. **The strongest predictable part is mean reversion:** h_last vs the change, ρ −0.41 (p 0.001).

**Therefore:** reduce selection variance (longer validation, averaging) and widen the search carefully. Selection still
never touches the outer verdict quarters.

## Procedure (identical for both arms)

### Inner validation

- The **last 12** training origins (instead of 4), each held out and fitted on rows whose target precedes it (the
  `hr_lib.inner_folds` rule).
- Folds need at least 3 target quarters and both classes; at least 3 valid folds are required, else `hr_lib.GRID[0]`.

### Search space: 32 settings

- **The 8 `hr_lib.GRID` settings**, as served.
- **24 random draws** (numpy default_rng seed 2036, without replacement over the full product) from:
  - learning_rate {0.02, 0.05, 0.1};
  - n_estimators {50, 100, 150, 300};
  - max_depth {1, 2, 3}, with num_leaves = 2^depth;
  - min_child_samples {10, 15, 30, 50};
  - reg_lambda {1, 5, 20};
  - colsample_bytree {0.6, 0.8, 1.0};
  - class_weight {None, balanced};
  - direction constraints {off, on}.
- **Direction constraints:** E1 +1, E2 +1, ST1 −1, others 0. In the arm without E1/E2, only ST1 −1.
- **Fixed for all:** LightGBM binary, deterministic, seed 2027, n_jobs 1.

### Scoring and prediction

- **Score:** mean log loss on the held-out inner origins.
- **Prediction:** the **mean probability of the top 3 settings** by inner log loss (ties: lower setting id).
  Averaging the best few reduces the variance of picking one.
- **SHAP:** the mean of the three models' TreeSHAP values.

### Arms

- **T-B6** = C-B6's 23 inputs.
- **T-B6E** = C-B6E's 25 inputs (+ E1, E2).

**No further variant** will be tried after seeing the results.

## Evaluation

- **Sample:** 62 verdict quarters, Leads 1–2 (Leads 1–8 for Algorithm 3).
- **Reported:**
  - all metrics, R1–R7 and thirds;
  - paired Brier of each arm vs C-B6, and T-B6E vs T-B6 (the value of E1/E2 under the same tuning);
  - the 14-test Holm family with PERSIST-P;
  - selection stability: switches of the top-1 setting in the evaluation era;
  - SHAP shares of E1, E2, ST1 and ST2;
  - leave-one-quarter-out robustness of R7 (minimum middle-third accuracy when any one verdict quarter is removed).

## Serving rule (fixed)

1. **T-B6E is served** (all five driver groups as inputs) if it passes R1–R7 at Leads 1 and 2 and has accuracy
   ≥ 0.75 at both leads.
2. **Else, T-B6 is served** in place of C-B6 if it passes R1–R7 at Leads 1–2, has accuracy ≥ 0.75, **and** its
   Brier ≤ C-B6's at both leads.
3. **Else, C-B6 stays.** The trade-off goes to the owner.

"Employment and remittances improve the forecast" is claimed only if T-B6E's Brier < T-B6's at Lead 1 with one-sided
p < 0.05.

**Reported whatever the result.**
PLAN-SHA256: 0e6c5053b16acdccccc957073ccf8c70a4406c40bbd3d9e3ce756982cccc63a7
