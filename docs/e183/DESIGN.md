# E183: missing-input robustness of the E168 forecast (production code change, owner-approved)

Written 2026-11-10 at the owner's request ("fix missing-data weakness"). This changes live E168 code, with the owner's
explicit approval. Nothing is re-trained, regenerated, registered or promoted by this change.

## The problem (found by E178 scenario S2)
- **What happened.** When an input had no published value at the issue date, the forecast went **down**, and nothing
  warned.
  - Quezon's P(HIGH) fell from 0.064 to a mean of 0.037 with 25 % of trigger inputs missing, 0.010 with 75 %, and 0.001
    with all of them missing.
  - Its forecast share fell from 35.5 % to 22.7 %.
- **The cause.** LightGBM sends a missing value down the branch it learned for missing values. For an input that was
  **never missing in the training rows**, no such branch exists, so the value is treated as zero. For most E168 inputs
  (year-on-year changes, anomalies, relative levels), zero means "no change", so a missing source looked like calm
  conditions.

## The fix
- **New helper** `app/e168/robust.py`:
  - `fill_unseen_missing(tr, te)`: in the forecast rows only, an input that is missing but was never missing in the
    training rows is filled with its **training median**. Inputs that are sometimes missing in training (news before
    2016, for example) keep LightGBM's learned missing-value handling. Training rows and inner cross-validation are
    untouched.
  - Applied **identically** in validation (`app.e168.lgbm_only.task`) and serving (`app.e168.serve._forecast`), right
    before `run_proc`, so the validation and serving feature paths stay the same.
- **Flag.** Each served forecast row now records:
  - `inputs_filled`: the number of filled inputs that belong to the selected feature set;
  - `inputs_filled_names`;
  - `data_complete`.

  These flow through `app.e168.dashboard_export` (dashboard rows) and `app.e168.regenerate.stage` (the quarterly
  `live.json`).
- **Warning.** `app.ml.inference.e168_system.province_row` appends: *"Data incomplete: N model input(s) had no
  published value at the issue date (…) and were filled with their typical training value; treat this forecast with
  extra caution."* Rows staged before E183 carry no flag and show no warning.
- **Not changed.**
  - The 90 % range.
  - The model, its settings and its selection.
  - The served artifact (`data/e168/issues/2026-Q4_2026-11-01/`) and the registry.

## What must stay identical (checked)
1. **E168's validated results.**
   - Diagnosis: none of the 72 outer rows per lead has an unseen-missing input, so the step is a no-op there.
   - Proof: all 18 E168 jobs (main and controls) re-run through the changed `lgbm_only.task` must equal
     `data/e168/out/all_rows.csv` (same configuration; selected outputs identical).
2. **The current production forecast.** `serve._forecast` at the production cut-off must reproduce the production
   artifact for all 15 province × lead rows.
   - The live rows lack regional consumption (`income_growth`, `income_rel`; the PSA series ends in 2023). The served
     configuration (`RSS|FULL`) does not use those columns, so `inputs_filled` must be 0 and nothing changes.

## What must improve (checked)
- **S2 re-run on the live Lead-1 rows,** with the same masks (seeds 17811–17813) and with all triggers missing,
  comparing:
  - before the fix: masked inputs passed to the model as missing;
  - after the fix: filled by `fill_unseen_missing`.
- **Expected.** After the fix, forecasts with missing inputs stay close to the real-input forecast instead of falling,
  and every masked row is flagged.

## Files
- **Code:** `app/e168/robust.py` (new); small calls in `app/e168/lgbm_only.py`, `app/e168/serve.py`,
  `app/e168/dashboard_export.py`, `app/e168/regenerate.py` and `app/ml/inference/e168_system.py`.
- **Tests:** `tests/unit/test_e183_missing_inputs.py`.
- **Checks:** `backend/data/e183/out/` (`equivalence.json`, `production_check.json`, `s2_before_after.csv` and
  `s2_summary.json`) and `docs/e183/REPORT.md`.
