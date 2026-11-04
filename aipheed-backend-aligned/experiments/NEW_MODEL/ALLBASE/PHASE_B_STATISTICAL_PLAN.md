# ALLBASE, Phase B: statistical plan

## 1. The single family of 42 tests (fixed)

**Comparators**, the stored implementations, unchanged:
1. naive persistence;
2. PSA/government-only logistic regression;
3. combined logistic regression (LOGIT);
4. NLP-only logistic regression;
5. government-only LightGBM;
6. NLP-only LightGBM;
7. always-HIGH.

This gives **3 candidates × 7 comparators × Lead 1 and Lead 2 = 42 tests, with one Holm correction across all 42**
(revision approved at the Phase C authorization). The family is not split by candidate or lead and no comparator is
removed.

## 2. Each test

- **Statistic:** the mean over paired quarters of BS_candidate(q) − BS_comparator(q), with BS(q) = (p(q) − y(q))².
- **Pairing:** only quarters where both forecasts exist and the label exists:
  - comparators 1, 2, 3, 5 and 7: the full 62-quarter window;
  - comparators 4 and 6 (news only): the news-era quarters, origins ≥ 2021-Q1 (20 at Lead 1, 19 at Lead 2).
- **One-sided p** (H₀: the candidate is not better): the share of 5000 cluster-bootstrap resamples of quarters (seed
  2036; `hr_lib.boot_mean`, verified equal to the original `pd.concat` bootstrap in SENIOR_REVIEW D1) whose mean
  difference is ≥ 0.
- **Holm:** sort the 42 raw p ascending; adjusted p_(i) = max over j ≤ i of min(1, (42 − j + 1) × p_(j)).
  Significant if adjusted p < 0.05 **and** the difference is < 0.
- **Reported per test:**
  - the candidate's and the comparator's Brier;
  - the difference;
  - its 95% percentile bootstrap interval;
  - the Brier skill score (1 − BS_cand / BS_comp);
  - raw p, Holm p, n;
  - the conclusion ("significantly better" / "not significantly different").

## 3. Interpretation rules

- **A non-significant difference is reported as "not significantly different"**, never as "equivalent" and never as
  "better".
- **Power is reported with every non-significant result:** the number of quarters needed at the observed effect (as in
  Phase A §3C). At Lead 1 against LOGIT the observed effect needs about 16,000 quarters at Holm's strictest step for a family of 6
  (Phase A); with 42 tests (strictest step 0.05/42) the number is higher still.
- **No other test, metric, family or threshold** is substituted after results are seen.

## 4. Secondary metrics (descriptive, no inference)

The following are reported per lead and per R7 third, for C-b, K1–K3 and all comparators where defined:
- accuracy, balanced accuracy, precision, recall, F1, AUC;
- the confusion matrix and the false-positive / false-negative rates;
- ECE (10 bins) and the reliability-diagram points;
- reversal recall and non-reversal accuracy.

## 5. Multiplicity across candidates

- **All three candidates are in the single 42-test family** (Phase C revision). G1 for a candidate requires all 14 of
  its comparisons to be significant with the 42-test Holm-adjusted p.
- Selection among K1–K3 still uses fold S only and is disclosed; the fold-E results are shown.

## 6. Prospective statistics (after 2027)

- **Algorithm 4** on the first four sealed 2027 quarters per lead: F1 and AUC as point values only. Four observations
  give **no meaningful significance**, and AUC is undefined if all four are one class. This is stated with the result.
- **The 42-test family (3 candidates × 7 baselines × 2 leads) is repeated prospectively, as a separate family from
  the historical one,** once each lead has at least 20 labelled prospective quarters, the
  minimum at which the strongest Phase A effects (persistence, always-HIGH, government-only LightGBM) become testable.
  It is reported every year after that.
- **The R1–R7 verdict** stays as in `SENIOR_REVIEW/PROSPECTIVE_PLAN.md`: 40 quarters per lead, a single look.
