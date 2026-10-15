# E35 deviations and implementation notes

## Before the protocol was frozen (no score had been computed for any non-default configuration)

1. **V4 tolerance.**
   - The first verification run failed V4 by 5.8e-12. E32's `predictions.csv` stores 10 significant digits, while its `results.json` holds full-precision Brier.
   - The tolerance was set to 1e-9, and the reason is written into the check.
   - Arithmetic defect: none.
2. **V6 scramble scope widened.**
   - Besides S1 of quarters ≥ t, the scramble now also covers S1 of earlier quarters whose rounds were not posted at O(t). These values exist in the file but were not public.
   - This makes the test stricter. It still passes (0 of 7,200 probabilities change).
3. **Computability probe.**
   - Every configuration can be computed on exactly E32's dates: lead 1 has 10, lead 2 has 8.
   - Earlier targets fail E32's own data-sufficiency rules (fewer than 2 rounds, or fewer than 25 D pairs and then fewer than 40 for the fallback).
   - So no extra inner dates exist before 2023-Q4. The inner sets are small (0–9 dates), which is why the protocol sets a minimum of 3 inner dates.

## After the first tuning run

4. **Selection-summary labels (reporting only).**
   - **The defect.** The first run (`runs/superseded_prefix/20261015T005237Z`) printed "Full-period best ⟨S-FULL selection⟩ (⟨lowest Brier of the 36⟩)". Those are two different configurations: the tie rule picks `lam1.0|D1|c0.80` (0.0776), while the lowest is `lam1.0|D2|c0.80` (0.0755). Its "optimism" was taken against the lowest configuration.
   - **The fix.** `results.json` now reports both `full_selected_brier` and `min_config`, and both optimism figures: against S-FULL, as PROTOCOL §8.4 says, and against the lowest configuration.
   - **What did not change.** Every prediction, grid, score, inner-score and selection-log file is byte-identical to the first run (checked with `cmp`). The verdict, selections and metrics are unchanged.
   - **Superseded runs.** The three pre-fix runs (`005237Z`, `005340Z`, `005402Z`; the latter two were byte-identical repeats) were moved to `runs/superseded_prefix/`, not deleted.
   - **Primary and repeat.** The primary run is `runs/20261015T005446Z`, and its byte-identical repeat is `runs/20261015T005506Z`.

No other deviation. The 0.5 decision cut, τ, the target, the data window and the grid were never changed. The prospective record was frozen once, from the primary run.
