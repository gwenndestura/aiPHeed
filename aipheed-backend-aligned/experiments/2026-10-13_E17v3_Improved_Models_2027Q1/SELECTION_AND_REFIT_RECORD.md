# Final Selection and Refit Record

| Target | Frozen rule result at h = 5 | Configuration kept | Evidence label |
|---|---|---|---|
| Regional hunger H | **No candidate passes.** Drift has the lowest MAE on 3 origins, but wins only 1 of 3 and depends on one quarter. | **C1 Carry-forward** | Exploratory only (3 origins) |
| Food inflation F | No candidate passes | **F1 Carry-forward** | Exploratory only (5 origins) |
| Relative pressure D | No candidate passes. The ridge models beat carry-forward but not zero. | **D1 Carry-forward**, as the rule says. **Descriptive note:** D2 (zero) had the lowest error. | Exploratory only (5 origins) |
| Thesis risk label | Not run (Phase 0) | — | — |

**No improved model was established.**

## Refit at the 2027-Q1 origin

| Item | Value |
|---|---|
| Data | All approved observations ≤ 2025-Q4. The information set is the same as in the backtest, with T = 2027-Q1 and h = 5. |
| Refit | Carry-forward needs none. The fitted candidates were refit on all pairs with target quarters ≤ 2025-Q4 and reported **only as experimental outputs**. |
| Model coefficients | Saved in `runs/20261013T035829Z/forecast_2027Q1.json` → `artifacts`: ridge means, SDs, standardized betas, intercepts and n |
| Code | `runner/v3_lib.py`, `runner/run_v3.py` (hashes in the run `manifest.json`) |
| Training data identifiers | The three allowlisted files (`DATA_AUTHORIZATION_AND_ALLOWLIST.md`) |
| Forecast cutoff | 2025-Q4 observations (published by mid-January 2026) |

**No 2026 data was used. Nothing in this refit was tuned on any outcome.**
