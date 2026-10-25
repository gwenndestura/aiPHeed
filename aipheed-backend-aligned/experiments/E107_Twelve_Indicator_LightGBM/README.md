# E107: one LightGBM on the 12 aiPHeed indicators, Leads 1–4

**Branch:** `aipheed/e107-twelve-indicator-lightgbm` (from `aipheed/simple-methodology` @ `9433f9e`).
**Status:** evaluated. Not served; the dashboard is unchanged.

**Result in one line.** All 12 indicators are in the model and leakage-tested. **No reliable forecasting lead time is established.** Lead 1 reaches 0.75 accuracy but fails the significance, recall and generalization checks. Leads 2–4 are worse than "always LOW", and regional hunger is not forecastable beyond its latest reading.

| Deliverable | File |
|---|---|
| A. Methodology audit (written before any change) | `AUDIT.md` |
| B. Revised methodology | `METHODOLOGY.md` |
| C. Forecasting experiment report | `EXPERIMENT_REPORT.md` |
| D. Indicator audit (inventory, coverage, contribution, sensitivities) | `INDICATOR_AUDIT.md` |
| E. Thesis-ready results | `THESIS_RESULTS.md` |
| F. Reproducibility and integration | `REPRODUCIBILITY.md` |
| Pre-registration | `PROTOCOL.md`, `ADDENDUM_1.md`, `ADDENDUM_2.md` (hashes in `runner/`) |
| Outputs | `out/` (predictions, `results.json`, `diagnostics.json`, sealed prospective forecasts) |
