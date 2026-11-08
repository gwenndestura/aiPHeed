# Addendum 2: decision threshold chosen on validation outcomes only (frozen before scoring)

**Written:** 2026-10-28, after the 2026-10-28 brief that explicitly allows "decision thresholds selected using validation data and fixed before final testing". The SHA-256 goes in `runner/ADDENDUM_2_SHA256.txt` before `threshold.py` runs. The model (C0 = served P0H4-U price model × π_H, S-AB schedule) is unchanged. Only the HIGH/LOW decision rule is tested.

## Why

- **All 7 Lead-2 misses have p < 0.5** (CT1).
- **The product rule P = π_H × π_P makes HIGH hard to reach.** Both parts must be high: for example, 0.82 × 0.43 = 0.35.
- **The fixed 0.50 cut-off was never chosen on data.** It is a convention.

A threshold learned from **earlier, already-published outcomes only** is a legitimate part of the model. It is not a change to the evaluation rules: R1-R7 are applied unchanged to the resulting classes.

## Rule (out-of-sample by construction)

At each origin t and lead k:

1. **Validation rows:** the walk-forward forecasts (C0, S-AB) of lead k from earlier origins t' < t whose T43c label was published before the issue date O(t). These come from `FORECAST_RESEARCH/data/known_by_origin.csv` (`y` rows with t = origin).
2. **Candidate thresholds:** 0.10, 0.15, …, 0.50.
3. **Selection:** choose the one that maximises **balanced accuracy** on the validation rows. Ties go to the threshold closest to 0.50.
4. **Minimum evidence:** the validation rows must span ≥ 4 target quarters with ≥ 3 HIGH and ≥ 3 LOW rows. Otherwise the threshold is 0.50.
5. **Application:** forecasts of origin t are classified HIGH when p ≥ the selected threshold.

Thresholds are never moved above 0.50: the aim is the documented HIGH-recall failure, and a higher cut-off cannot raise recall.

## Evaluation

- **Unchanged:** the evaluation rows, R1-R7, the baselines, and the Brier score (which does not depend on the threshold).
- **Reported per lead:** accuracy, balanced accuracy, HIGH precision, recall and F1, the confusion matrix, false alarms, the thresholds used by origin, and the DEV/CONF split.

## Adoption rule (fixed now)

**C0-T** (C0 with the validation threshold) is adopted as the decision rule only if:
- its maximum reliable lead is ≥ C0's;
- Lead 1 still passes R1-R7;
- Lead 2 DEV balanced accuracy is not lower than C0's.

Otherwise the 0.50 rule stays.

A Lead-2 R1-R7 pass by C0-T is reported as **development evidence that the tested rule passes**, not as validated reliability. The prospective quarters remain the only clean test.

## Not allowed

- Choosing a threshold on the evaluation rows themselves.
- Re-running with another objective, grid or minimum after seeing results.
