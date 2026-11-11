# E181: exploratory search over synthetic-augmentation variants. EXPLORATORY: the winner is chosen on the test rows.

Written 2026-11-09 at the owner's request ("make it higher … make sure it is still balanced"). Committed before any E181
output existed.

## Read this first
- E181 **selects a variant by its score on the 72 real outer rows**, the same rows it is then reported on. Its headline
  number is therefore **optimistic by construction** and is **not** evidence that the model improved.
- Every variant tried (129) and its score are recorded. The report states the number tried.
- To show how much of the gain is real, E181 also runs a **chronological check**: the variant is selected on earlier
  survey rounds only and tested on the next round. That number is the honest estimate.
- Production stays E168. Nothing is registered or promoted.

## Variants
- **Construction.** Each variant is E168's selected configuration (Stage A of E179, unchanged) plus one fixed
  augmentation setting from E179's grid: 128 settings, plus "none" = E168.
- **Fit.** The final fit uses the job's real training rows plus synthetic rows from them. The calibration layer is
  chosen as in E168, on real inner out-of-fold rows.
- **Seeds.** Each variant's forecast is the **mean over generator seeds 17901–17905** (as E180), so the search ranks
  settings, not seed luck.
- **Synthetic rows** are class-balanced as in E178/E179 (minority class first). Synthetic rows are never scored.

## "Balanced" selection rule (fixed now)
1. **Eligible:** HIGH recall ≥ E168's at both Lead 1 and Lead 2 (0.88). Balance cannot be traded for accuracy by missing
   HIGH provinces.
2. **Ranked by:** mean balanced accuracy over Leads 1 and 2, i.e. the mean of HIGH recall and LOW recall.
3. **Ties broken by:** mean Brier score over Leads 1 and 2 (lower first), then by grid order.

## Chronological check (the honest estimate)
- **Step 1.** Select by the rule above using only ENNS2018 rows (Leads 1 and 2), then score that variant on ENNS2019.
- **Step 2.** Select using ENNS2018 + ENNS2019 rows, then score that variant on ENNS2021.
- **Report.** Accuracy, balanced accuracy, HIGH recall and Brier on the 2019 + 2021 rows (50 per lead), for E168 and
  for this "select-then-test" procedure.

## Outputs
- `backend/data/e181/out/`: `variant_rows.csv` (every variant's outer forecasts), `variant_scores.csv`,
  `results.json`, `run_log.jsonl` and `hashes.json`.
- The report is `docs/e181/REPORT.md`, with the EXPLORATORY label at the top.
