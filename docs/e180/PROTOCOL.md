# E180: E179 averaged over its five generator seeds, and sealed ENNS 2022 forecasts. Fixed before results.

Written 2026-11-09 at the owner's request ("improve it more"; option "final ensemble + 2022 seal"). Committed before any
E180 output existed.

## Honesty statement (read this first)
- **E180 is designed after E179's results were seen**, including how its accuracy varied between the five generator
  seeds: Lead 1 from 73.6 % to 79.2 %, Lead 2 from 75.0 % to 77.8 %.
- Averaging over seeds is a standard way to remove generator luck. It was not tuned on the outer rows, and it adds no
  free choice. Even so, E180 is **not independent evidence** on the 72 outer rows, which every experiment since E151 has
  read.
- E180 is the **last candidate scored on those 72 rows**. Its result is reported whatever it is.
- **The independent test is the ENNS 2022 seal.** E168 (already sealed, `f8228fae`), E179 and E180 forecasts for every
  ENNS 2022 province are written and hashed now, before any 2022 outcome exists. ENNS 2022 provincial HFIAS has not
  been published (`docs/e168/ENNS_2022_VALIDATION_REPORT.md`). They can be scored on genuinely new data once FNRI
  releases it.

## E180
- **Definition.** E180 = the mean, over generator seeds 17901–17905, of E179's forecast for each outer row: the logit
  forecast `mu`, P(HIGH) `p` and the 90 % half-width `half`. Each seed is E179's procedure unchanged (Stage A = E168's
  selection; Stage B = augmentation tuned on inner folds with the one-standard-error rule). There are no other changes
  and no new options.
- **Main rows.** The five seeds' E179 rows already recorded in `backend/data/e179/out/all_rows.csv` (mode `main`).
- **Controls, Lead 1.**
  - E179's controls ran at seed 17901 only, so they are run again at all five seeds and averaged the same way.
  - `shuf1`–`shuf3`: `C.shuffle_cols` before augmentation.
  - `corrupt`: unreleased rounds' `y` replaced before `M.Pipeline`. Each seed uses the main job's random stream
    (deviation D3 of E179), so that it differs from the main run only by the corruption.
- **Evaluation** uses the same code as E178/E179 (`app.e178.retrain.evaluate`, name `E180`):
  - the 72 real outer rows per lead;
  - accuracy, balanced accuracy, HIGH recall and precision, F1, macro-F1, AUC, Brier, calibration slope and
    reliability bins;
  - paired region-cluster bootstrap CI of the Brier difference E180 − E168 (2,000 draws);
  - exact McNemar test, leakage, and shuffled triggers.
- **Decision rule (unchanged, strict).** E180 is better than E168 only if all of these hold:
  1. the upper bound of the Brier-difference CI is below 0 at Lead 1 **and** Lead 2;
  2. accuracy is ≥ E168's at both leads;
  3. leakage is below 1e-9;
  4. the upper bound of the E180 − shuffled Brier CI is below 0.

  Otherwise the result is "the seed ensemble did not improve the model". E168 stays in production either way until the
  owner decides; nothing is registered or promoted.

## ENNS 2022 seal
- **Construction.** The same as E168's seal (`app.e168.enns2022_seal`): every ENNS 2022 province, Leads 1 and 2, origin
  O3, with only rounds released before each issue (ENNS 2021 not yet released). The frames are taken from that module
  unchanged; only its `run_proc` call is replaced by E179's procedure.
- **Recorded per row:**
  - E168 (Stage A without augmentation; it must match E168's existing seal);
  - E179 (seed 17901);
  - E180 (mean over seeds 17901–17905);
  - each with score, 90 % range, P(HIGH) and class (HIGH at P ≥ 0.5).
- **Sealing.** Written once to `backend/data/e180/out/sealed_enns2022.json`, never overwritten. Its SHA-256 is printed,
  logged and committed.
- **Scoring rule, fixed now.**
  - Score only on HFIAS moderate-or-severe provincial rows, once the outcomes are public and verified as comparable
    HFIAS.
  - Report accuracy, Brier and HIGH recall for E168, E179 and E180, with no re-fitting.

## Outputs
- `backend/data/e180/out/`: `controls_rows.csv`, `controls_selection.csv`, `all_rows.csv`, `results.json`,
  `sealed_enns2022.json`, `run_log.jsonl` and `hashes.json`.
- The report is `docs/e180/REPORT.md`.
