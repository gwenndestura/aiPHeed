# E179: E168 plus synthetic training rows, with the augmentation tuned inside the training data. Fixed before results.

Written 2026-11-09 at the owner's request ("focus on the tuning of the model by adding the synthetic data"). Committed
before any result of E178 Stage 2, including its exploratory run (deviation D2), and before any E179 output existed.

## Honesty statement
- The 72 outer rows (ENNS2018, 2019 and 2021 at Leads 1 and 2) have been read by E151–E168. The E178 fidelity results
  (training rows only) were known when this design was written; no augmented-model result on the outer rows was.
- **E179 is run once with the settings below. Its result is reported whatever it is.** It is a candidate only. E168
  stays in production unless the owner decides otherwise after the result.

## What changes from E178
E178 used one fixed synthetic weight (0.4), uniform parents, jitter of 0.25 SD, a fidelity gate, and no option to use
no synthetic rows. E179 instead:

1. **Keeps E168's model selection unchanged (Stage A).**
   - The anchor, feature set, pruning and LightGBM settings are chosen exactly as in `app.e168.lgbm_only.run_proc`, on
     real rows.
   - Stage A is therefore identical to E168. Without augmentation, E179's model is E168's model.
2. **Tunes the augmentation on that configuration, inside the training data only (Stage B).** Each candidate setting is
   scored by region GroupKFold(5) on the outer job's training rows. Synthetic rows are generated from each inner fold's
   real training rows and added only to its fit set. The score is the weighted logit SSE on the real held-out rows,
   E168's criterion.

   | Option | Values |
   |---|---|
   | Generator | jitter, SMOTE (as E178) |
   | Synthetic rows r × n_real | 0.25, 0.5, 1.0, 2.0 |
   | Synthetic weight α (× real weight) | 0.2, 0.4, 0.7, 1.0 |
   | Jitter size (× input SD), jitter only | 0.1, 0.25, 0.5 |
   | Parent focus | **uniform** (E178); **boundary**: within class, parents drawn with weight exp(−\|y\|/0.5), so synthetic rows concentrate near the 50 % line where classification errors happen |
   | **None** | no synthetic rows (E168) |

   That is 96 jitter settings, 32 SMOTE settings and "none": 129 candidates.
3. **Uses augmentation only when it clearly helps (one-standard-error rule).**
   - For each setting, compute the per-fold SSE difference against "none".
   - A setting is eligible only if its mean difference plus one standard error is below 0.
   - Among the eligible settings, the lowest inner SSE is chosen (ties go to the earlier setting in the grid order).
   - If none is eligible, **E179 = E168** for that job.
   - The plain lowest-SSE setting, without the rule, is also reported as the descriptive arm `E179_min`.
4. **Replaces E178's fidelity gate with the inner-CV guard plus the one-SE rule.** E178's fidelity statistics are still
   computed and reported, descriptively, for the settings E179 selects.
5. **Keeps everything else as E178:** labels, class balancing (minority first, then real shares), the calibration
   layers on real out-of-fold rows only, and synthetic rows never scored.

## Seeds, jobs and controls
- Generator seeds 17901 (primary) to 17905.
- Jobs: six main jobs (ENNS2018, 2019 and 2021 × Leads 1, 2) at all five seeds. Stage A runs once per job, because it
  does not depend on the generator seed.
- Lead-1 controls at seed 17901: `shuf1`–`shuf3` (`C.shuffle_cols` before augmentation) and `corrupt` (unreleased
  rounds' `y` replaced before `M.Pipeline`).
- Stage A without augmentation is also recorded (`E168_rerun`) and must equal the stored E168 rows' selected outputs.

## Evaluation (unchanged from E178)
- On the 72 real outer rows per lead, with the same code (`app.e178.retrain.evaluate`, name `E179`): accuracy, balanced
  accuracy, HIGH recall and precision, F1, macro-F1, AUC, Brier, calibration slope and reliability bins.
- Paired region-cluster bootstrap CI of the Brier difference E179 − E168 (2,000 draws), exact McNemar test, leakage,
  shuffled triggers, and stability (mean ± SD over the five seeds).

## Decision rule (same as E178, strict)
E179 is **better than E168** only if all of these hold for the primary seed:
1. The upper bound of the Brier-difference CI (E179 − E168) is below 0 **at Lead 1 and at Lead 2**.
2. Accuracy is **≥ E168's at Lead 1 and at Lead 2**.
3. Leakage is below 1e-9.
4. The upper bound of the E179 − shuffled Brier CI is below 0.

Otherwise the result is "tuned synthetic augmentation did not improve the model". If E179 passes, a candidate can be
staged for the owner's decision; nothing is registered or promoted by this experiment.

## Outputs
- `backend/data/e179/out/`: `all_rows.csv`, `selection.csv` (chosen setting per job and seed, with the 1-SE numbers),
  `balance.csv`, `results.json`, `run_log.jsonl` and `hashes.json`.
- Final-fit synthetic rows of the primary seed go to `backend/data/e179/synthetic/train/`.
- The report is `docs/e179/REPORT.md`.
