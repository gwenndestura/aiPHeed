# E83 protocol: deep reconstruction of the aiPHeed forecast (frozen before any E83 result)

Branch `e83-deep-research-reconstruction`, cut from `final-system-v2` at 7774e30 on 2026-10-21. Earlier work
(E40–E82) is cited where it is reused; E76–E82 are **not** merged here (user decision of 2026-10-21).

This file is frozen by the SHA-256 hash recorded in `PROTOCOL.sha256`, which is committed before any E83 model is
scored. Every change after that point goes into `DEVIATIONS.md` with its reason.

## 1. Requirement basis

- **Authority.** The controlling requirements are the Chapter I objectives and the user's E83 directive of
  2026-10-21.
- **Accuracy threshold.** The directive sets accuracy **strictly greater than 75%** as the mandatory minimum and 80% as
  the target. Two-quarter-ahead forecasting is required.
  - Earlier sessions recorded that Chapter I states no numeric threshold (memory `thesis-chapter1-only`). The directive
    supersedes that for E83. The conflict is reported, not hidden.
- **Data window.** 2021-Q1 to data published by 2026-10-14 (`config/authorization.json`).
- **Excluded data.** No pre-2021 value. Nothing published after 2026-10-14.

## 2. Target (approved, unchanged)

**T43** (E43, built from the E40 signals) is assigned per province-quarter:

- **HIGH** when Balance Luzon SWS involuntary hunger exceeds 11.3 **and** at least one price signal is high:
  - province food CPI YoY (quarter mean) exceeds the province's P60, or
  - food minus headline YoY exceeds the province's P60.
- **LOW** otherwise.
- **No label** for a quarter with no approved SWS round. Such a quarter is never zero-filled.
- **Thresholds.** Frozen on 2021-Q1..2022-Q4 and never recomputed.

T43 is a **constructed proxy** of food-insecurity risk. It is not an observed food-insecurity rate.

An audit of whether T43 represents multidimensional food insecurity is a deliverable (§9). Any alternative target is
reported beside T43 and never replaces it.

## 3. Timing (unchanged from E41/E43, audited in E47/E59)

- **Origin.** O(t) is 00:00 PHT on the first day of quarter t+1.
- **Inputs available at O(t):**

  | Input | Available at O(t) |
  |---|---|
  | CPI | to month 2 of quarter t |
  | SWS | rounds posted before O(t) |
  | Production | to t−1 |
  | Labour force (LFS) | to t−1 |
  | Rice prices, remittances, FX, ENSO | to t−1 |
  | Typhoons | to t |
  | News | articles published before O(t) |
  | Rice-policy events | announced before O(t) |

- **Lead k** targets quarter t+k:

  | Lead | Target | Meaning |
  |---|---|---|
  | 0 | t | nowcast of the quarter that just ended |
  | 1 | t+1 | the quarter in which the forecast is issued |
  | 2 | t+2 | the next quarter, three months after issue |
  | 3 | t+3 | two full quarters after the issue quarter |

- **Primary horizon.** Lead 2 is the thesis's "Lead-2". Lead 3 is reported so that a stricter reading of
  "two quarters ahead" is also answered.

## 4. Evaluation set (fixed now)

- **Rows.** Every T43-labelled province-quarter with a target from **2023-Q1** through 2026-Q3, for each lead.
- **Origins.** t = target − k. All arms are scored on the **same rows**.
- **When a learner is ineligible.** If a learner cannot be fitted at an origin (fewer than 6 label quarters or fewer
  than 5 HIGH training labels), its rows are reported as "not issued". It is then compared with the baselines on its
  issued rows only, and its coverage is stated.
- **Status of these quarters.** None of them is unseen: E57–E82 have scored them. The only genuinely unseen
  quarters are 2026-Q4 and 2027-Q1, which E83 seals prospectively (§8).

## 5. Arms (pre-registered; nothing is added after results without a DEVIATIONS entry)

### Baselines

| Arm | Rule |
|---|---|
| B-PERSIST | the latest label available at O(t), per province |
| B-STATE | T43 computed from the latest posted H and the latest two published months of food and headline YoY |
| B-MAJ | the training-period majority class (labels available at O(t)) |
| B-CLIM | P = the training-period HIGH share |
| B-AH | always HIGH |
| B-AL | always LOW |
| B-PSA | logistic regression on the price-driver features only (Objective-4 "PSA-only") |
| B-NLP | logistic regression on news features only (Objective-4 "NLP-only") |

### Candidates

| Arm | Description |
|---|---|
| S-SIM | Structural simulation: H random walk × province price paths (e83_lib.simulate). No fitted parameters. |
| M-LR-ALL | L2 logistic regression on all five drivers plus H history |
| M-GB-ALL | Constrained LightGBM (depth 2, 4 leaves, λ = 5, 100 trees, lr 0.05, balanced weights) on the same features |
| M-GB-S | M-GB-ALL with the S-SIM probability added as a feature (structural prior plus learned correction) |
| R-I7 | E46 I7, the best earlier component model (Lead 2 only; its stored predictions) — reference only |

### News ablation (Lead 2 and Lead 1, on the best of M-LR-ALL / M-GB-ALL)

| Arm | Features |
|---|---|
| A | approved non-news features (D1–D4 plus H history) |
| B | A + the existing news features (D5_news_v0) |
| C | A + the lead-text features (N1) |
| D | A + the de-duplicated event-level features (N2) |
| E | A + the best single news representation among B–D (selected on Lead-1 rows only, then applied to Lead 2) |
| F | all drivers + E |

### Driver ablation

Drop one group at a time from the best learner, and run each group alone. The effect is measured as the change in
Brier and in accuracy on identical rows. Group permutation importance uses 200 within-quarter permutations.

## 6. Metrics and pass rule (Lead 2 primary; every lead reported)

- **Reported for every arm and lead:**
  - n issued, correct and incorrect;
  - accuracy, balanced accuracy, precision, recall (HIGH), F1, Brier, log-loss and calibration-in-the-large;
  - ROC-AUC when both classes have at least 5 rows;
  - per province, per year, and on rising rows (y(t+k) = 1 while the latest known label was 0);
  - 95% date-block bootstrap intervals.
- **PASS (Lead k qualifies)** requires all four of:
  1. accuracy > 0.75 on all evaluation rows (the arm must issue all rows, or its unissued rows count as wrong);
  2. balanced accuracy > that of every baseline;
  3. Brier lower than B-PERSIST, B-CLIM and B-AH, with a paired per-date sign-flip p < 0.10 (one-sided, Holm across
     baselines);
  4. recall(HIGH) ≥ 0.5.
- **TARGET.** PASS with accuracy ≥ 0.80.
- **Longest qualifying lead.** The largest k such that every lead from 2 to k passes.
- **Selection rule.** The served candidate is the arm that passes at Lead 2 with the lowest Brier. If none passes, the
  served model stays as it is, and the best arm is reported as "not validated".

## 7. Leakage guards

- **Runtime asserts:**
  - no row before 2021-Q1;
  - every training label quarter is ≤ t−1 and was posted before O(t);
  - every feature is computed from `d.cut(t)`.
- **News features** use only articles with `ph_date < O(t)`. Lead text is attached to those same articles; its
  retrieval date (2026-10-21) is later than O(t), so lead text is a re-collection of content that was public at
  publication. This is disclosed as a limitation (real-time availability).
- **Fitting inside each origin.** Thresholds, scalers, imputers and hyper-parameters are fixed or fitted inside each
  origin only. No tuning on evaluation rows. Any tuning is nested within the training pairs of each origin.
- **Placebo.** The best arm is re-run with labels shifted by +4 quarters and with permuted province labels; skill must
  vanish.

## 8. Prospective seal

The selected (or best) arm's 2026-Q4 and 2027-Q1 forecasts are written to `sealed/` with a SHA-256 hash before any
outcome for those quarters is published.

## 9. Other deliverables

- Lead-text extraction status report.
- Data dictionary.
- T43 validity audit.
- SHAP (TreeSHAP for the served LightGBM; additivity checked to 1e-6 on the log-odds scale) and plain-language text.
- LGU estimates labelled as derived.
- Refresh and archive checks.
- Tests.
