# E37 protocol: the next-calendar-quarter forecast the dashboard shows, evaluated against the six thesis baselines

**Status: FROZEN before any lead-2 E37 arm was fitted or scored.** The SHA-256 is in `runner/PROTOCOL_SHA256.txt`; the commit is recorded in `FINAL_REPORT.md`. Written 2026-10-15.

## 1. Why this protocol exists

The researcher requires the dashboard to target **the calendar quarter after the one in which it is viewed** (Asia/Manila). On 2026-10-15 that is 2027-Q1.

Forecasts are issued at fixed **quarter-start origins**: O = 00:00 PHT on the first day of the current quarter. This gives one stable record per quarter: no duplicate or conflicting records on refresh, and a reproducible cutoff.

| Viewing date (PHT) | Current quarter q | Origin | Latest data quarter t = q−1 | Next-quarter target q+1 = t+2 |
|---|---|---|---|---|
| 2026-10-15 | 2026-Q4 | 2026-10-01 | 2026-Q3 | **2027-Q1** |
| 2027-01-xx | 2027-Q1 | 2027-01-01 | 2026-Q4 | 2027-Q2 |

In the E32/E36 convention the next-quarter target is therefore **lead k = 2** from O(t). The current quarter q is lead 1, already evaluated in E36. Information released after the origin (for example the SWS September 2026 round, posted 2026-10-14) enters at the next origin.

E36 evaluated lead 1 only, so lead-2 skill must be evaluated before the dashboard's next-quarter estimate can be described.

## 2. Target, inputs and cutoffs

Unchanged from E36 (`../E36_LightGBM_One_Quarter_Ahead/PROTOCOL.md` §1, §3):

- **Target:** T1, S1 = H + 2D, HIGH if S1 > τ(t); τ is the trailing median of labels posted before O(t).
- **Features:** E32 as-of features X(t, k=2): `H_gap` = t+2 − (latest posted H quarter).
- **Feature sets:** GOV, NLP, COMB, COMPACT.
- **Window:** 2021-Q1 to the 2026-10-14 authorization.
- **Training rows at O(t):** (X(t′, 2), label of t′+2 at τ(t′)) for t′+2 ≤ t−1 with every round of t′+2 posted before O(t). Rows with a missing COMB value are dropped, the same rows for every arm.

## 3. Evaluation dates

- Every lead-2 target from 2022-Q4 to 2026-Q3 that has a released definition-A label and whose origin O(target−2) has **at least 10 complete training rows with both classes**. The list is produced by the code, not chosen by hand.
- **Every one of these dates was examined in earlier experiments** (E25, E32, E35 evaluated lead 2): development evidence, not an untouched test.
- **Final (prospective) test:** 2027-Q1 from O = 2026-10-01, frozen before its outcome exists.

## 4. Arms (identical to E36 §4–§5, with k = 2)

- **Proposed:** E36-LGBM procedure, pool {COMPACT, COMB} × {G1, G4, G3, G2}, nested rule.
  - Eligible prior dates are lead-2 dates whose target label was posted before O(t); fewer than 3 → COMB×G1.
  - Tie 0.002 → simpler.
- **The six formal thesis baselines** (the only formal comparisons):
  1. B1 naive persistence (latest published label at O(t));
  2. B2 LR combined;
  3. B3 LR government only;
  4. B4 LR NLP only;
  5. B5 LightGBM government only (nested over G1–G4);
  6. B6 LightGBM NLP only (nested over G1–G4).
- **Supplementary diagnostics** (reported apart, never as thesis baselines): always-HIGH and climatology, to read accuracy against the class balance.

## 5. Metrics and dependence

Reported for all arms, on identical rows:
- accuracy with correct/n; confusion matrix; precision, recall, F1;
- per-class recall and balanced accuracy;
- Brier, calibration-in-the-large, ECE;
- ROC-AUC and PR-AUC, flagged UNSTABLE when the minority class has < 5 rows.

**Dependence:** five provinces share one regional H per date. Uncertainty is therefore a **date-cluster bootstrap**, paired tests are **per-date** (sign-flip on per-date Brier), and the number of independent dates is reported next to the row count.

## 6. 75% reading

Same as E36 §7:
1. point accuracy ≥ 0.75;
2. date-bootstrap lower bound ≥ 0.75 ("demonstrated");
3. skill relative to the six baselines and balanced accuracy.

**Predictive validation status** is one of:
- **RELIABLE** — needs (2), no significant loss to any baseline, and an untouched (prospective) confirmation;
- **NOT DEMONSTRATED**;
- **INCONCLUSIVE / INSUFFICIENT EVIDENCE** — when the minority class has fewer than 5 rows or fewer than 8 dates exist.

## 7. Integrity

- Seeds fixed; one repeat must be byte-identical.
- No change after freezing except through `DEVIATIONS.md`.
- No pre-2021 data; no fabricated labels.
- A period with no label is excluded and listed, never counted.
- Frozen records of E25/E31/E32/E35/E36 are verified by hash and not modified.
