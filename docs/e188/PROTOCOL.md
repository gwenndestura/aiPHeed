# E188: better synthetic data for E184. More draws, and survey-noise synthetic rows. Fixed before results.

Written 2026-11-10 at the owner's request ("make the synthetic data better"). Committed before any E188 output existed.

## Why these two variants
- **What was ruled out.**
  - The training rows already contain each province's real past snapshots at Leads 1–8 (`e150.model.Pipeline`), so
    extra real snapshots cannot be added.
  - Jitter, SMOTE, copula, ratio, weight and focus settings were searched in E179–E185.
- **Two weaknesses of E184's synthetic rows remain:**
  1. **Only five random draws.** E184 averages five synthetic draws (seeds 17901–17905), so part of its forecast is
     random noise from those draws.
  2. **Inputs are shaken with artificial noise** (0.5 SD per input). That noise is not real. The one uncertainty that
     is known and real is the survey's own sampling error (`se_true`), which E184 also uses for the target.

## Variants (everything else is E184 exactly: E168's selection, 50/50 rows, weight 1.0, boundary focus)
| Arm | Synthetic rows | Draws |
|---|---|---|
| E184 (reference, re-run here) | jitter: inputs + N(0, 0.5 SD), target + N(0, se) | seeds 17901–17905 |
| **E188a** "more draws" | the same as E184 | seeds 17901–17920 (20) |
| **E188b** "survey-noise" | inputs exactly as the parent real row; target redrawn from the survey's own sampling error, y + N(0, se) | seeds 17901–17920 (20) |

- **E188b keeps the inputs as exact copies on purpose.** E178's copy check therefore does not apply to it.
- **What E188b is.** It is equivalent to training on the survey's sampling distribution of each outcome. No input
  values are made up.

## Test
- **Rows.** Leads 1–6 for ENNS2018, 2019 and 2021, with 72 real outer rows per lead. Synthetic rows stay inside the
  inner and final fit sets only, as in E184.
- **Reproduction check.** The E184 arm must equal the stored E184 rows (`data/e184/out/all_rows.csv`, `lead3_rows.csv`,
  `data/e187/out/lead4_6_rows.csv`).
- **Reported per lead.**
  - Accuracy, balanced accuracy, HIGH recall and precision, false alarms and Brier.
  - Brier difference against E184 with a 95 % region-cluster bootstrap CI (2,000 draws, seed 188).
  - An exact McNemar test against E184.
  - The owner rule: accuracy ≥ 75 % and Brier CI upper bound against persistence < 0.
- **Decision.** A variant is preferred to E184 only if all three hold:
  - at **all six leads** its accuracy is ≥ E184's;
  - at all six leads its Brier is ≤ E184's;
  - its accuracy is strictly higher at at least one lead.
  If both variants qualify, the one with the lower mean Brier is preferred. Otherwise E184 stays.
- **Scope.** Nothing is staged or deployed. The outcome is reported whatever it shows.

## Outputs
- `backend/data/e188/out/` (`rows.csv`, `results.json`, run log and hashes).
- `docs/e188/REPORT.md`.
