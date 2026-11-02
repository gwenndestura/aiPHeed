# v10 Annotation protocol (for human annotators; nothing here is filled in by the system)

**Status:** ready to use. **No labels exist.** Labels must come from people. The system never fills, predicts or imputes them.

**Reuse:** the existing guide `aipheed-backend-aligned/experiments/FINAL_SYSTEM_SELECTION/annotation/NEWS_ANNOTATION_GUIDE.md` and its four labels (TYPE, RELEVANT, GEO, EVIDENCE) and the 126-row `news_review_human_TEMPLATE.csv` remain valid.

## Why it matters

It is the only way to measure XLM-R on Filipino-English headlines, the food-nexus guard, and province assignment, none of which has a human measurement.

## Sampling plan (seeded, fixed: seed 2026)

Target 400 headlines, development window only, drawn by a committed script before any annotator starts:

| Stratum | n | Reason |
|---|---|---|
| Scored relevant (≥ 0.30), province tagged | 100 | Precision |
| Scored not relevant, province tagged | 100 | Recall |
| Failed food-nexus guard | 80 | Guard's misses |
| No province assigned | 60 | National scope and geo recall |
| Any title with ≥ 1 Tagalog token | 60 | Language subgroup (oversampled: only 1.9 % of corpus) |

Keep strata weights so population estimates can be reweighted. 174 rows after 2026-09-30 are excluded.

## Procedure

1. **Two annotators** label independently; a third settles disagreements.
2. **Blind:** no machine score, no model output, no target data. Headline, date and outlet only (the system also sees only headlines).
3. Calibrate on 20 extra rows not counted in the results.
4. Add one label: `province` (one of the 5, or NONE).

## Metrics

Per label: Cohen's kappa between annotators (reported first). Against the system: precision, recall, F1, kappa with bootstrap CIs, reweighted by stratum, and separately for Tagalog-token titles. Thresholds are **not** changed after seeing results without a new protocol version.

## Effort

About 400 headlines × 2 annotators at about 30 seconds each: roughly 3.5 hours each, plus calibration.
