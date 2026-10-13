# Data Dictionary (E13)

## 1. Inputs (see `INPUT_ALLOWLIST.md` for the hashes)

| Variable | Source file | Unit | Definition | Level | Coverage |
|---|---|---|---|---|---|
| `F` | `realized_components_2021_2025.csv` | % YoY | PSA provincial food CPI, year-on-year change, quarterly | Province | 2021-Q1..2025-Q4, 100/100 |
| `mean5` | Same | % YoY | Mean of the five provinces' F in the quarter | Region (5 provinces) | 20/20 quarters |
| `D` | Same | percentage points | F − mean5 (relative food-price pressure; sums to 0 within a quarter) | Province | 100/100 |
| `H` | Same | % of families | SWS Balance-Luzon involuntary hunger (production rounds only); one value per quarter | Balance Luzon | 16 quarters |
| `S1` | Same | index | H + 2D (aiPHeed Equation 3, full precision) | Province | 80 rows |
| SWS round (`H`, `published`, `date_type`, `definition_A`, `source`, `round`) | `details.json` → `two_layer.regional_layer_rounds` | % of families; date | One row per SWS round, with the fieldwork quarter E12 assigned and the publication date | Balance Luzon | 21 rounds, 2021-Q2..2025-Q4 |
| τ0 | `details.json` | index | 10.84335 (recorded; median S1 of 2021-Q2..2023-Q2) | — | — |
| `fies_moderate_severe_pct` | `nns_fies.parquet` | % of households | FNRI NNS 2025 FIES moderate or severe, CALABARZON. **The 5 rows repeat one regional value.** | Region | 2025 |
| `subsistence_pct`, `subsistence_cv`, CI | `psa_subsistence.parquet` | % of families; % | PSA subsistence incidence among families, with its coefficient of variation | Province, region | 2021, 2023 |
| `poverty_incidence_pct` | `lgu_poverty.parquet` | % of population | PSA 2021 small-area poverty estimate. 126 of 142 rows are province-mean fallbacks; 16 are LGU-specific. | LGU | 2021 |

## 2. Derived variables (computed in `runner/e13_lib.py`)

| Variable | Definition | Known at origin(T)? |
|---|---|---|
| `origin(T)` | First day of quarter T | — |
| `H_last` | Mean of the published rounds of the most recent fieldwork quarter with a round published **before** origin(T) | Yes, by construction |
| `H_last_quarter`, `H_age` | That quarter; T minus it, in quarters (1 or 2 in every test quarter) | Yes |
| `F5_lag2` | mean5 of quarter T−2 | Yes (calendar rule) |
| `F_lag2`, `D_lag2` | F and D of the province in quarter T−2 | Yes |
| `Fbar_p`, `Dbar_p` | Mean of F or D for the province over 2021-Q1..T−2 | Yes |
| Quarterly H target (A) | Mean of all rounds assigned to quarter T (primary). Production rounds only for S-A1. | Realized value, joined after the seal |
| `event_y`, `event_pred`, `event_score` | Secondary events (protocol §5): A: H[T] > H_last; B1: F > 4.0; B2: D > 0 | — |
| `status` | `OK` or `INSUFFICIENT_DATA` (never converted to LOW or 0). **No test row was INSUFFICIENT_DATA.** | — |

## 3. Output files

| File | Content |
|---|---|
| `runs/inspect_20261013T022045Z/input_inventory.json` | Input structure and outcome-audit values (no comparisons) |
| `runs/20261013T022702Z/predictions.csv` | All forecasts (no realized values). SHA-256 in `SEAL.json`. |
| `runs/…/scored_rows.csv` | Forecasts + realized `y`, `error`, event columns |
| `runs/…/metrics.json` | Every metric, comparison, skip, perturbation check, diagnosis, external comparison and coefficient |
| `runs/…/baseline_comparison.csv`, `model_comparison.csv` | Identical to the root `BASELINE_COMPARISON.csv` and `MODEL_COMPARISON.csv` |
| `runs/…/raw_coefficients.csv` | Raw-unit coefficients of the linear provincial arms per test quarter (post-analysis) |
| `runs/…/province_event_tables.csv`, `quarter_event_tables.csv` | Per-province and per-quarter errors and event counts (post-analysis) |
| `runs/…/manifest.json` | Hashes of the protocol, inputs (start and end), code and outputs; environment; guard access log |
| `runs/20261013T023112Z/` | Replicate run (no root deliverables) |

## 4. Column guide for `BASELINE_COMPARISON.csv` and `MODEL_COMPARISON.csv`

| Column | Meaning |
|---|---|
| `target` | A (regional hunger), B1 (provincial food inflation), B2 (relative provincial food-price pressure) |
| `analysis` | `primary`, `S-A1_definition_A_only` or `S-B1_E9_test_quarters`. **The rule applies only to `primary`.** |
| `MAE`, `RMSE`, `bias` | In the target's units (percentage points for B1 and B2; percent of families for A). Bias = mean(forecast − realized). |
| `mean_kendall_tau` | Mean within-quarter Kendall τ between forecast and realized values across the 5 provinces. Empty when the forecast is constant across provinces. |
| `event_*` | Secondary event counts, balanced accuracy, ROC-AUC and PR-AUC (protocol §5) |
| `best_baseline`, `MAE_diff_vs_best`, `ci_low`, `ci_high` | Comparison with the lowest-MAE baseline (quarter-cluster bootstrap, 10,000 draws) |
| `quarters_better`, `p_signflip`, `p_holm`, `loqo_better` | Per-quarter wins, the exact one-sided sign-flip p, Holm-adjusted p, and leave-one-quarter-out wins |
| `cond1`..`cond4`, `improvement_established` | The four frozen conditions (protocol §4) and their conjunction |
