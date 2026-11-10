# E186: E184 plus provincial local data (farmgate and rice prices, rainfall). Fixed before results.

Written 2026-11-10 at the owner's request: "improve the model … goal 80 % accuracy", option 2, "provincial data that
varies across provinces". Committed before any E186 output existed.

## Why
- **The problem.** Two of E168's five trigger groups do not vary by province. Unemployment and OFW remittances have one
  national value per quarter. This is consistent with the shuffled-trigger results: scrambling the inputs across
  provinces costs nothing.
- **The data that could help.** The project already holds provincial series that E168 never used, in
  `data/e152/out/local_panel.parquet`, attached to every row by `N.add_sources` but in no E168 feature set:
  - **farmgate palay:** `l_fg_yoy`, `l_fg_rel`, `r_fg_yoy`;
  - **wholesale rice:** `l_rice_yoy`, `l_rice_rel`, `r_rice_yoy`, `l_terms`;
  - **NASA rainfall:** `l_rain3`, `l_rain6`, `r_rain3`.
- **Coverage, 2013–2026.** Rainfall 100 %, farmgate about 80 %, rice about 60 % of province-quarters. Missing values
  keep LightGBM's learned handling, because these columns are missing in training too. `l_fish_yoy` (24 % coverage)
  is not used.

## Honesty statement
- **What the 72 rows are.** They have been read since E151. E186 is run **once** and reported whatever it shows. 80 %
  is the owner's goal, not a criterion that changes how the result is reported.
- **Prior use of these sources.** E166 used them with a nested source selection, which was not LightGBM-only. This is
  the first LightGBM-only use.

## The model (only the feature-set menu changes from E184)
- **Stage A.** E168's selection on real rows, with two more feature sets in the menu, all chosen by the same inner
  region GroupKFold:

  | Feature set | Columns |
  |---|---|
  | GOV | as E168 |
  | FULL | as E168 |
  | GOV+cons | as E168 |
  | FULL+cons | as E168 |
  | **GOV+local** | GOV plus the 10 local columns |
  | **FULL+local** | FULL plus the 10 local columns |

- **Unchanged from E168:** anchors, the HPO grid, pruning options, and monotone constraints (`Pv.SIGN`; the local
  columns are unconstrained).
- **Synthetic training data: exactly E184.** Jitter, r = 1, weight 1.0, 0.5 SD, boundary focus, classes balanced,
  generated per fold over all menu columns (local columns included), mean over seeds 17901–17905.
- **E183** missing-input handling and calibration as E168.

## Evaluation
- **Rows and metrics.** The 72 real outer rows at Leads 1, 2 and 3: accuracy, balanced accuracy, HIGH recall and
  precision, macro-F1, AUC, Brier and calibration slope.
- **Comparisons.** Paired region-cluster bootstrap Brier CIs against persistence, E168 and E184; exact McNemar tests
  against E184.
- **Controls at Lead 1, five-seed means.**
  - Shuffled triggers ×3, with the local columns added to the shuffled set.
  - Corrupted unreleased rounds, on the main random streams.
- **Feature use.** Which feature set Stage A selected per job, and how often a "+local" set was chosen.

## Decision (fixed now)
- **Better than E184** only if both hold:
  - the upper bound of the Brier CI against E184 is below 0 at Leads 1, 2 **and** 3;
  - accuracy is ≥ E184's at each lead.
- **Also reported:**
  - the owner's deployment rule (≥ 75 % and Brier CI vs persistence < 0 at each lead, leakage below 1e-9);
  - whether accuracy reaches 80 % at each lead;
  - whether E186 beats its shuffled control.
- **Otherwise:** "the provincial local data did not improve E184".

## ENNS 2022 seal
- **Construction.** As E184, with the same frames.
- **Where.** Written once to `backend/data/e186/out/sealed_enns2022.json`.

## Outputs
- `backend/data/e186/out/` and `docs/e186/REPORT.md`.
- Nothing is staged or deployed without the owner's instruction.
