# Phase 2, Addendum A: the price condition at Lead 2 on independent years (Y8)

**Status.** Frozen (SHA-256 in `common/PLAN2A_SHA256.txt`) before Y8 is run.

**Motivation.** Y7, a diagnostic on the official rows, showed the following:

- With the **observed** hunger condition plugged in, none of the 10 existing price terms passes Lead 2. The best, P6, fails R5 and R6.
- With the **observed** price condition, the served hunger term fails only R6 and R7.

The price condition at Lead 2 (target quarter = months 4–7 after the newest CPI month) is therefore a second binding limit. Every earlier price model was developed and scored on 2021+ provincial rows only, because provincial CPI starts in 2021. Region IV-A CPI starts in 1994, so the price side can be tested on independent years.

## Y8 design

### Target

The regional analogue of the T43c price condition for quarter q (Region IV-A, PSA YoY):

- F_q = mean food YoY over the 3 months of q;
- G_q = mean (food YoY − all-items YoY);
- condition = F_q > 6.25 **or** G_q > 0.48.

The two thresholds are the means of the five provincial E40 thresholds. They are fixed here and not tuned.

### Information and rows

- **Issue O(t):** CPI months ≤ m0(t), month 2 of quarter t. Covariates follow Phase-2 section 3. Target quarter q = t + 2.
- **Training rows at O(t):** every earlier origin t′ whose 3 target months are ≤ m0(t), so the label was published. The fit is expanding-window and refitted at every origin. Standardisation and penalty choice happen inside the fold.
- **Development scoring:** targets 2000-Q1 .. 2020-Q4 (84 quarters, one row per quarter).

### Comparators (persistence family)

| Name | Definition |
|---|---|
| PERS-BIN | The condition evaluated on the newest 3 published months (0/1). It is the analogue of PERSIST-SI's price part. |
| PERS-PROB | A logistic model on [F3 − 6.25, G3 − 0.48], where F3 and G3 are the newest 3-month means. It is the calibrated persistence / A1-structural analogue. |

### Candidates

| Name | Definition |
|---|---|
| **AR** | Two direct ridge regressions, for target-quarter F and for target-quarter G. Features: newest month, 3-month mean, change over 3 and 6 months, the value 12 months earlier, national rice YoY. Gaussian residual σ from training residuals. P = 1 − (1 − P_F)(1 − P_G). |
| **LOGX** | An L2 logistic model on the condition. Features: newest F, F3, ΔF over 3 and 6 months, G3, national rice YoY and its 3-month change, ONI latest and 6-month max, typhoons in the previous quarter, palay YoY. The penalty is chosen on the last 25% of training rows. |

### Gate

A candidate passes if both hold, at Lead 2:

| | Condition |
|---|---|
| G1 | Brier lower than PERS-PROB, with a one-sided bootstrap p < 0.10. The bootstrap resamples quarters, and a moving-block (4 quarters) bootstrap is also reported. |
| G2 | Balanced accuracy at 0.50 at least that of PERS-PROB. |

### Y8 confirmation, only if a candidate passes

- The gate-passing candidate with the lowest development Brier is applied to the official 65 Lead-2 rows.
- It is fitted on Region IV-A rows published before O(t), then applied to each province's own F and G features and provincial thresholds (transfer).
- That price term is multiplied by π_H4 (the served hunger term). R1–R7 are applied unchanged, and the result is labelled as in Phase-2 section 5.

**If no candidate passes:** no confirmation is run. The result is reported as evidence on the predictability of the price condition at a 4–7 month horizon.
