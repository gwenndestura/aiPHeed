# Model report and reliability verdict (phases 5–6)

**All numbers VERIFIED.**
- **Command:** `python -I backend/scripts/model_report.py`
- **Outputs:**
  - `docs/aipheed/results/metrics.csv`, `selection.csv`, `reliability.csv`, `reliability_verdict.csv`;
  - `run_config.json` (seed 2026, 10 000 bootstrap draws; SHA-256 of the rule, script, predictions and data);
  - `model_report_run.txt` (console output).

**Rule:** `SELECTION_RULE.md`, committed before the first run (`c07324e`).

**Data status.** Every SWS value from 2021 to 2026-Q3 had been seen in earlier experiments, so this is **development evidence**.

## Validation design (protocol lock E1, E2)

**Chronological, expanding window.** At each quarter start (P-DASH):
- every model is re-estimated from SWS rounds published before that day;
- it then forecasts Leads 1–4 (Lead k = dashboard quarter − 1 + k).

**PERSIST, TREND-D and SEAS-LLM** are recomputed by the backend's own code. They equal the research predictions to < 1e-9; the script asserts this.

**No hyperparameters are tuned**, so there are no inner folds. Outer rows are scored once.

**Sets:**

| Set | Rows (Leads 1–4) | Target quarters | Coverage |
|---|---|---|---|
| S-U (primary) | 44 / 40 / 36 / 32 | 11 / 10 / 9 / 8 | 2024-Q1 … 2026-Q3 at Lead 2 |
| S-E132 | 28 rows at Lead 2 | 7 | Rows where the learned E132 models exist |

## Results, S-U, P-DASH

The 95 % CI is a block bootstrap over target quarters.

| Model | Lead | n eligible | n within | % within [95 % CI] | MAE | RMSE | Bias | High-tercile bias | Sharp increases within | 80 % coverage |
|---|---|---|---|---|---|---|---|---|---|---|
| PERSIST | 1 | 44 | 21 | 47.7 [31.8, 65.9] | 5.05 | 6.76 | −2.38 | −6.75 | 0/15 | 0.66 |
| PERSIST | 2 | 40 | 16 | 40.0 [25.0, 57.5] | 5.98 | 7.71 | −3.07 | −7.77 | 0/16 | 0.70 |
| PERSIST | 3 | 36 | 13 | 36.1 [16.7, 58.3] | 6.46 | 8.49 | −3.83 | −9.45 | 0/15 | 0.64 |
| PERSIST | 4 | 32 | 12 | 37.5 [12.5, 62.5] | 6.51 | 8.99 | −4.56 | −10.05 | 0/15 | 0.69 |
| TREND-D | 2 | 40 | 12 | 30.0 [20.0, 42.5] | 7.17 | 8.87 | −2.90 | −7.48 | 1/16 | n/a |
| SEAS-LLM | 1 | 44 | 17 | 38.6 [25.0, 52.3] | 5.49 | 6.96 | −2.56 | −7.20 | 2/15 | 0.66 |
| SEAS-LLM | 2 | 40 | 18 | 45.0 [22.5, 67.5] | 5.72 | 7.58 | −3.19 | −7.64 | 3/16 | 0.73 |
| SEAS-LLM | 3 | 36 | 12 | 33.3 [13.8, 55.6] | 6.23 | 8.33 | −3.96 | −9.40 | 1/15 | 0.72 |
| SEAS-LLM | 4 | 32 | 14 | 43.8 [15.6, 71.9] | 6.30 | 8.84 | −4.72 | −10.21 | 2/15 | 0.72 |
| HFM-X | 1 | 44 | 24 | 54.5 [43.2, 65.9] | 4.70 | 6.13 | −1.68 | −6.35 | 6/15 | 0.70 |
| HFM-X | 2 | 40 | 20 | 50.0 [32.5, 67.5] | 4.87 | 6.42 | −2.53 | −7.14 | 8/16 | 0.75 |
| HFM-X | 3 | 36 | 18 | 50.0 [30.6, 69.4] | 5.10 | 6.56 | −3.44 | −7.65 | 5/15 | 0.69 |
| HFM-X | 4 | 32 | 10 | 31.2 [15.6, 46.9] | 5.51 | 6.80 | −3.62 | −7.42 | 3/15 | 0.75 |
| X-RED (reported only) | 2 | 40 | 19 | 47.5 [30.0, 65.0] | 4.79 | 6.23 | −2.97 | −7.38 | 3/16 | 0.75 |
| SIMPLE (reported only) | 2 | 40 | 19 | 47.5 [30.0, 65.0] | 4.75 | 6.15 | −2.98 | −7.29 | 3/16 | 0.80 |

**Lead 2 diagnostics:**

| Model | Prediction variance ÷ target variance | Correlation with the target |
|---|---|---|
| PERSIST | 1.94 | 0.20 |
| SEAS-LLM | 1.90 | 0.23 |
| HFM-X | 0.80 | 0.07 |
| SIMPLE | 0.85 | 0.25 |

**Train-versus-test gap** is recorded only for ridge (S-E132, Lead 2): test MAE 7.36 against training MAE 2.08, a gap of +5.28. **It overfits.** Ridge reaches 39.3 % within [25.0, 53.6].

**SEAS-LLM intervals** are the backend's Kalman predictive intervals, which is what is served. The earlier research runs used empirical intervals, which covered 0.55 at Lead 2.

## Selection (mechanical, SELECTION_RULE.md)

The paired 95 % CI below is of the difference in within share against the incumbent (S-U, Lead 2, 40 rows over 10 quarters):

| Candidate vs incumbent | Δ within | Paired 95 % CI | Replaces? |
|---|---|---|---|
| TREND-D vs PERSIST | −0.100 | [−0.200, 0.000] | No |
| SEAS-LLM vs PERSIST | +0.050 | [−0.100, +0.200] | No |
| HFM-X vs PERSIST | +0.100 | [−0.125, +0.325] | No |

**Selected: PERSIST.** No candidate's gain over persistence is distinguishable from zero on 10 target quarters. This is a negative result, and it is reported as such.

**It differs from the owner-approved prospective primary.** E134 Addendum 2 makes SEAS-LLM the primary.
- The backend's `/api/v1/hunger-forecast` serves SEAS-LLM under that approval.
- The persistence value equals each record's latest SWS reading, which is shown alongside it.
- Changing the served candidate to PERSIST is **the owner's decision** (FINAL_REPORT).

## Phase 6: Lead 1–4 reliability verdict

**Applied mechanically by code:** `e130_lib.numeric_reliability`, `reliability.csv` (P = pass, F = fail).
- **Rows:** issue = first day of the dashboard quarter, target = D − 1 + k, cutoff = issue 00:00 PHT (exclusive).
- **Alignment:** target quarter values from rounds published by the scoring date.
- **Leakage tests:** `tests/unit/test_forecasting_core.py`.

| Model | Lead | N1 | N2 | N3 | N4 | N5 | N6 | N7 | Reliable |
|---|---|---|---|---|---|---|---|---|---|
| PERSIST (selected) | 1 | P | F | P | F | F | P | F | **No** |
| PERSIST (selected) | 2 | P | F | P | F | F | P | P | **No** |
| PERSIST (selected) | 3 | F | F | P | F | F | P | F | **No** |
| PERSIST (selected) | 4 | F | F | P | F | F | P | F | **No** |
| SEAS-LLM | 1 | P | F | F | F | F | F | F | No |
| SEAS-LLM | 2 | P | F | P | F | F | F | P | No |
| SEAS-LLM | 3 | F | F | P | F | F | F | P | No |
| SEAS-LLM | 4 | F | F | P | F | F | F | P | No |
| HFM-X | 1 | P | F | P | P | F | F | P | No |
| HFM-X | 2 | P | F | P | P | F | P | P | No |
| HFM-X | 3 | F | F | P | F | F | F | F | No |
| HFM-X | 4 | F | F | P | F | F | F | P | No |

**Maximum reliable lead: none** (`run_config.json`). **Lead 2 is not reliable for any model.**

**Blocking factors at Lead 2, specifically:**
1. **Signal absent:**
   - The best within share is 50 % (20/40); N2 needs 75 % (30/40).
   - Correlation between forecasts and outcomes is ≤ 0.25.
   - No model beats persistence with a CI excluding zero.
   - The true change over the horizon (SD about 4.6 pp) exceeds the tolerance (about ±3.2 pp) (E133 D1).
2. **Target lag:** at a quarter-start issue the newest SWS value is three quarters before the Lead-2 target (h = 3).
3. **Stability (N5):** results swing between the 2024 surge and the 2025–26 post-break period.
4. **n is too small for Leads 3–4 (N1):** 9 and 8 target quarters, against the 10 required.

**Evidence that would be needed:**
- **≥ 10 unseen Lead-2 target quarters** (SWS 2026-Q4 onward; earliest 2029-Q3), scored by `E136 runner/score_e136.py`;
- **a leading indicator of hunger change** at SWS-area level. Regional quarterly LFS is the untested candidate (E136 §F).
