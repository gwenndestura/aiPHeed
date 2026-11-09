# E182: the E181 jitter-2× candidate, fixed and fully tested. Fixed before results.

Written 2026-11-09 at the owner's request ("more improve it, maintain the whole process"). Committed before any E182
output existed.

## Honesty statement
- **Where the setting came from.** It was found by E181's post-hoc check, after the 72 outer rows had been seen. Its
  score on those rows is therefore **optimistic**. The honest estimates are E181's forward-in-time check (+1 province
  per lead on 2019 + 2021) and, later, the ENNS 2022 seal.
- **What E182 adds.** It fixes the setting and runs everything E181 skipped: the leakage and shuffled-trigger controls,
  the shared evaluation with the strict decision rule, and a sealed ENNS 2022 forecast.
- **Reporting.** E182 is reported whatever it shows. E168 stays in production unless the owner decides otherwise.
  Nothing is registered or promoted by this experiment.

## The candidate (no free choices)
- **Stage A.** E168's selection on real rows, unchanged (`app.e168.lgbm_only.run_proc`'s loop): anchor, feature set,
  pruning and LightGBM settings.
- **Augmentation, fixed.**
  - generator jitter;
  - r = 2.0 × the real training rows;
  - synthetic weight α = 1.0;
  - jitter size 0.5 × input SD;
  - parents drawn with the "boundary" focus (weight exp(−|y|/0.5));
  - class-balanced (minority first).
- **Where synthetic rows go.** They are generated from each inner fold's training rows (for the inner out-of-fold
  forecasts) and from the job's training rows (for the final model), and only ever added to fit sets.
- **Calibration.** E168's three layers, chosen on real inner out-of-fold rows.
- **Forecast.** The mean over generator seeds 17901–17905 of `mu`, `p` and `half` (as E180).
- **Consistency check.** E182's main-job forecasts must equal E181's recorded forecasts for this variant.

## Evaluation
- **Rows.** The 72 real outer rows per lead (ENNS2018, 2019 and 2021 at Leads 1 and 2).
- **Code.** The shared evaluation (`app.e178.retrain.evaluate`, name `E182`).
- **Controls at Lead 1, each with the same five seeds averaged:**
  - `shuf1`–`shuf3`, applied before augmentation;
  - `corrupt`, using the main jobs' random streams (deviation D3 of E179).
- **Decision rule (unchanged, strict).** E182 is better than E168 only if all of these hold:
  1. the upper bound of the Brier-difference CI is below 0 at Leads 1 and 2;
  2. accuracy is ≥ E168's at both leads;
  3. leakage is below 1e-9;
  4. the upper bound of the E182 − shuffled Brier CI is below 0.
- **Also reported:** the "balanced" view (balanced accuracy and HIGH recall against E168), and the E181 forward check
  for reference.

## ENNS 2022 seal
- **Construction.** As E180: frames from `app.e168.enns2022_seal`, unchanged; the E168 forecasts must match its seal.
- **Contents.** E182's forecasts for every ENNS 2022 province at Leads 1–2.
- **Where.** Written once to `backend/data/e182/out/sealed_enns2022.json`, never overwritten; the SHA-256 is logged and
  committed.
- **Scoring rule.** Score once FNRI's provincial HFIAS moderate+severe results are public and verified comparable, with
  no re-fitting.

## Outputs
- `backend/data/e182/out/`: `all_rows.csv`, `results.json`, `sealed_enns2022.json`, `run_log.jsonl` and `hashes.json`.
- Code: `backend/app/e182/candidate.py`.
- Tests: `backend/tests/unit/test_e182_candidate.py`.
- Report: `docs/e182/REPORT.md`.
