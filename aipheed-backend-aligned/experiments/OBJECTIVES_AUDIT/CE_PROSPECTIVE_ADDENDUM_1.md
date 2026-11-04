# Addendum 1 to CE_PROSPECTIVE_PLAN.md: add C-B6 (fixed 2026-11-04, before any prospective seal)

`CE_PROSPECTIVE_PLAN.md` (9392917a…) is unchanged and stays in force. No seal exists yet, so adding a model now does not
alter any sealed evidence.

## Model added

| Model | Definition | Pre-registration | Leads sealed |
|---|---|---|---|
| C-B6 | `cb6_model._origin`: C-b's procedure (`run_news_v2._origin`, grid selected on inner folds) + ST1, ST2 | CB6_PREREGISTRATION.md 2efd9677… | 1, 2, 3 |

- **Inputs:** the same rebuilt table, news anomaly and ST1/ST2 rules as C-E6 (plan §3).
- **Sealing:** the same procedure, artifact file and ledger (plan §2, §4). C-B6 rows are added to each
  `sealed_ce_<issue>.csv`.

## Why it is added (development evidence, `FINAL_2026-11-04/CB6_IMPROVEMENT_REPORT.md`)

- **For:** best Brier score of all the models; R1–R7 pass on the 62 development quarters.
- **Against:** the R1–R7 pass comes from one forecast. At origin 2018-Q3, the inner-fold grid selection chose setting 5
  instead of C-b's setting 1. Rice-stock SHAP there is −0.011.
- **Its improvement over C-b is not significant** (p 0.13 / 0.20).
- **Only prospective quarters can tell whether the difference is real.**

## Evaluation added (plan §5 unchanged otherwise)

| Family | Tests | Correction | When |
|---|---|---|---|
| P4 | C-B6 vs the 7 baselines × Leads 1–2 | Holm over 14 | ≥ 20 labelled prospective quarters per lead |
| P5 | C-B6 vs C-b × Leads 1–2 | Holm over 2 | same |

- **Questions:** the same four, separately (probabilities, calls by McNemar, stability from 40 quarters, all-baseline
  superiority).
- **Thresholds and target unchanged:** 11.3% and 0.50.
- **No further change** after the first seal without a new addendum.
PLAN-SHA256: 3cf7930e437b28937ba22d2c1216458e99992554d0342d4466ebbd9e305407cd
