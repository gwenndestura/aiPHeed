# E9: Limitations, Deviations, Evidence Gaps and Reproducibility

## 1. Limitations

1. **The target is constructed, not observed.**
   - S1 combines Balance-Luzon hunger, a regional survey wider than CALABARZON, with a provincial food-price gap weighted by an unvalidated α = 2.
   - No independent provincial or municipal food-insecurity outcome exists to validate it.
2. **Few independent observations.**
   - 7 test quarters (35 rows, about 7 independent regional observations), 16 labelled quarters in total.
   - Bootstrap intervals over 7 clusters are unstable.
3. **Extreme class imbalance in the test period:** 33 HIGH / 2 LOW, and both LOW rows are Quezon. ROC-AUC and PR-AUC are not meaningful. Accuracy is not informative; always-HIGH scores 0.943.
4. **Reused quarters.** E1–E7 evaluated the same quarters, and E9's arms were informed by them. The final period is untouched *within E9's selection rule* but not by the project's history. **The results are exploratory.**
5. **Proxy-dated inputs.**
   - Provincial CPI release dates are national + 14 days (verified only for 2024-Q4).
   - Unemployment is dated by schedule.
   - No leakage-verified claim is made.
6. **Revised vintages.** Labels and inputs use current CPI values, not the vintages available at each origin.
7. **No prospective or blind test.**
   - 2026-Q3 is exposure-qualified: an aggregate including Q3 rows was printed on 2026-10-11.
   - 2026-Q4 can qualify only if its forecasts are frozen before any Q4 outcome is published and its inputs are dated (E8 review r2, R2). E9 made **no** 2026 forecast.
8. **Uncalibrated probabilities.** The calibration rule was never met. M1 probabilities of 0.98–0.99 are not probabilities of food insecurity.
9. **No LGU (city/municipality) target.** Municipal differences cannot be produced or validated from S1.
10. **Excluded inputs:** news, rice, the `food_cpi` index level, fuel, FX, remittances, climate. Their value is untested in E9.

## 2. Deviations from the frozen protocol (disclosed)

| ID | What happened | Effect |
|---|---|---|
| D1 | **Guard denial in run `20261012T140723Z`.** joblib/loky attempted a `wmic` subprocess to count CPU cores; the guard blocked it and loky fell back to the logical count. The protocol's "stop on any guard denial" rule did not halt the run, because the library caught the exception. | Re-run as `20261012T140816Z` with `LOKY_MAX_CPU_COUNT=21`: **no denial, and all 8 outputs byte-identical.** No data access was involved, and no result changed. The primary run is `140816Z`; `140723Z` is kept. |
| D2 | The runner omitted the pre-specified quarter-cluster bootstrap and the per-quarter and per-province tables | Computed afterwards by `runner/post_analysis.py`, using exactly the pre-specified method (2,000 draws, seed 42), from the run's own `scored_rows.csv` only. Outputs: `post_*.csv`, `post_analysis.json`. |

## 3. Unresolved evidence gaps

- Verified RSSO IV-A provincial CPI release dates. This would upgrade the proxy-dated status; collect them after any blind outcome collection.
- Independent provincial or municipal food-insecurity data, needed to validate α and the target.
- More labelled quarters. Each new quarter is one more independent regional observation.
- An approved 2026 source for the food CPI index level, if that input is wanted.
- Whether the production thesis system (`backend/`) or the isolated backend is the one the thesis evaluates.

## 4. Reproducibility

The interpreter is `backend\venv` (read-only use). From `C:\Users\admin\aipheed\aipheed-backend-aligned`:

```
set LOKY_MAX_CPU_COUNT=21
set PYTHONDONTWRITEBYTECODE=1
..\backend\venv\Scripts\python.exe -B experiments\2026-10-12_E9_S1_safe_training\runner\run_e9.py
..\backend\venv\Scripts\python.exe -B experiments\2026-10-12_E9_S1_safe_training\runner\post_analysis.py <run folder>
```

Synthetic tests (35; no project data). From `experiments\2026-10-12_E9_S1_safe_training\tests`:

```
..\..\..\..\backend\venv\Scripts\python.exe -B -m pytest -c pytest.ini --rootdir . --confcutdir . -q
```

**Expected:**

- τ0 = 10.8433; 16 labelled quarters; tests 2023-Q4 to 2025-Q4;
- `predictions.csv` SHA-256 `67b92ae4…`;
- selection M1.

The run stops on any change to the allowlisted input hashes. Each run writes a new timestamped folder and never overwrites.
