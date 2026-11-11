# E184: E168 with synthetic training data balanced 50/50 with the real data. Candidate for production. Fixed before results.

Written 2026-11-10 at the owner's request: "add synthetic data too but make sure it is balanced with the dataset currently
in E168". Two owner choices: **"Equal 50/50"** balance, and **"Stage, you approve"** deployment. Committed before any
E184 output existed.

## Honesty statement
- **How the setting was chosen.** E184's setting follows the owner's balance definition and E182's generator family,
  which was itself found post hoc in E181. It was **not** picked for its score: the same setting was among E181's 129
  variants, but its individual score was not inspected.
- **What the rows can and cannot show.** The 72 outer rows have been read by every experiment since E151, so E184's
  scores on them are not independent evidence. The ENNS 2022 seal is the independent test.
- **Who decides.** E184 reaches the dashboard only if the owner runs the promote command. Nothing is promoted by this
  work. E168 stays live until then and can be restored with one command.

## The model (no free choices)
- **Stage A.** E168's selection on real rows, unchanged: anchor, feature set, pruning and LightGBM settings.
- **Synthetic training rows, balanced 50/50 with the real rows:**
  - **Count:** one synthetic row per real training row (r = 1.0), generated from the rows of each training fold only.
  - **Weight:** each synthetic row has the same weight as a real row with the same standard error (α = 1.0), so real
    and synthetic data carry equal total influence.
  - **Classes:** HIGH and LOW are balanced as before (the minority class is filled first, then the real shares).
- **Generator.** As E182: jitter of 0.5 × input SD, near the 50 % line (boundary focus).
- **Seeds.** The forecast is the mean over generator seeds 17901–17905. The SHAP contributions shown on the dashboard
  are the mean of the five models' LightGBM contributions, which stay additive.
- **Missing inputs.** E183's missing-input handling and flag apply, as they do for E168.
- **Calibration.** E168's three layers, chosen on real inner out-of-fold rows.

## Evaluation
- **Rows.** The 72 real outer rows per lead (ENNS2018, 2019 and 2021), at the three served leads 1, 2 and 3.
- **Metrics.** Accuracy, balanced accuracy, HIGH recall and precision, F1, macro-F1, AUC, Brier and calibration slope.
- **Comparisons.**
  - Against **persistence** and **E168**: paired region-cluster bootstrap CIs of the Brier differences (2,000 draws)
    and exact McNemar tests against E168.
  - Controls at Lead 1, five seeds averaged: `shuf1`–`shuf3`, and `corrupt` on the main random streams (leakage).
- **Consistency.** E184's Lead 1–2 forecasts must equal E181's recorded forecasts for the same setting
  (`jitter|r=1|w=1|sd=0.5|boundary`).

## Deployment rule (the owner's production rule, as for E168)
E184 may be staged for promotion only if **all** of these hold:
1. at **each served lead (1, 2, 3)**: accuracy is ≥ 75 % **and** the upper bound of the Brier-difference CI against
   persistence is below 0 (the owner rule of 2026-11-07 that E168 is served under);
2. leakage is below 1e-9;
3. the live forecast passes `app.e168.regenerate.validate`-equivalent checks: all provinces, correct target quarters,
   P(HIGH) within 0–1, and class equal to P ≥ 0.5.

**Also reported, but not a deployment condition:** the strict "better than E168" rule of E178–E182, and the
shuffled-trigger comparison. The owner decides with these in view.

If the rule fails, nothing is staged and the report says so.

## ENNS 2022 seal
- **Construction.** As E182: frames from `app.e168.enns2022_seal`, unchanged; the E168 part must match its seal.
- **Where.** Written once to `backend/data/e184/out/sealed_enns2022.json`, never overwritten; the SHA-256 is logged and
  committed.

## Deployment mechanics (if the rule holds)
- **Staged issue.**
  - Location: `backend/data/e184/issues/<issue>/` (`live.json`, `dashboard_rows.csv`, `manifest.json`), in E168's
    schema.
  - Model id: `e184-lgbm-syn50-1.0`.
  - Information cut-off: the production issue's.
- **Registry.** E184 is registered as a **candidate** with its gate record. The registry's production entry is not
  changed.
- **Owner commands.**
  - Promote: `python -m app.e184.serve promote --approver "<name>"`.
  - Rollback: `python -m app.e184.serve rollback --approver "<name>"`, which re-promotes E168's current issue.
- **Dashboard support.** The adapter serves whichever of the two models is in production, with each model's own
  accuracy and wording.
- **Refresh guard.** While E184 is in production, the monthly E168 refresh stages its issue but does not promote it.

## Outputs
- `backend/data/e184/out/`: `all_rows.csv`, `lead3_rows.csv`, `results.json`, `sealed_enns2022.json`, `run_log.jsonl`
  and `hashes.json`.
- Report: `docs/e184/REPORT.md`.
