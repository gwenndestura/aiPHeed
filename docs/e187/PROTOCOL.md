# E187: more tests of E184. (A) longer leads 4–6; (B) HIGH cut-off tuned on training folds. Fixed before results.

Written 2026-11-10 at the owner's request ("improve, run more test"). Committed before any E187 output existed.

## Honesty statement
- **What the rows are.** The outer rows (72 per lead) are the same survey rounds as before.
- **Fixed in advance.** E184's model is unchanged in (A). In (B), the cut-off is chosen on training folds only.
- **Reporting.** Both parts are run once and reported whatever they show. Nothing is staged or deployed.

## (A) E184 at Leads 4, 5 and 6
- **Model.** E184 exactly (`docs/e184/PROTOCOL.md`): E168 selection plus synthetic rows 50/50, mean of seeds 17901–17905.
  It is run at Leads 4–6 for ENNS2018, 2019 and 2021, giving 72 rows per lead.
- **Comparison.** E168's own Lead 4–6 rows (`data/e168/out/all_rows_l3_8.csv`, from `app.e168.longer_leads`) and
  persistence.
- **Rule per lead (the owner's serving rule).** Accuracy ≥ 75 % **and** the upper bound of the Brier CI against
  persistence is below 0.
- **Served horizon.** E184's served horizon is the longest lead L such that Leads 1…L all pass. E168's horizon is 3
  (Lead 4 is 73.6 %).
- **Reported.** Accuracy, balanced accuracy, HIGH recall and precision, AUC and Brier; Brier CIs against E168 and
  persistence.

## (B) E187 = E184 with a HIGH cut-off chosen on training folds
- **Threshold choice.**
  - For each outer job, the real training rows' inner out-of-fold P(HIGH) is taken from the raw layer, averaged over the
    five seeds.
  - The cut-off is chosen from {0.30, 0.35, …, 0.60} to **maximise balanced accuracy** on those training rows.
  - Ties go to the cut-off closest to 0.50.
- **Forecasts.** E184's probabilities are unchanged; only the HIGH/LOW decision uses the chosen cut-off.
- **Evaluation at Leads 1–3 (72 real rows each).** Accuracy, balanced accuracy, HIGH recall, precision and false alarms,
  compared with E184 at 0.50 and E168, plus exact McNemar tests against E184.
- **Decision.** E187 is preferred to E184 only if **balanced accuracy is ≥ E184's at all three leads and HIGH recall is
  ≥ E184's at all three leads**. Otherwise E184 keeps 0.50.

## Outputs
- `backend/data/e187/out/` (`lead4_6_rows.csv`, `threshold_rows.csv`, `results.json`, run log and hashes).
- `docs/e187/REPORT.md`.
