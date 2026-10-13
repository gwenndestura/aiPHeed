# Test and Reproducibility Report (E13)

## 1. Order of work (local time, 2026-10-13)

| Time | Step | Output |
|---|---|---|
| 10:17 | Start-state integrity recorded (865 hash records; E9–E12 hash lists; git) | Scratchpad `e13_start_integrity.json` |
| 10:18–10:20 | Guard, library and synthetic tests written; **23 tests passed** | `tests/` |
| 10:20 | Input inventory (structure and outcome-audit values only; no comparison) | `runs/inspect_20261013T022045Z/` |
| 10:21–10:24 | `OUTCOME_DATA_AUDIT.md`, `INPUT_ALLOWLIST.md`, `EXPERIMENT_PROTOCOL.md` | — |
| **10:24:32** | **Protocol frozen**: SHA-256 `c379c039…5c2519f3` written to `runner/PROTOCOL_SHA256.txt` | — |
| 10:27–10:29 | Primary run `20261013T022702Z` (writes the root CSV deliverables). Predictions sealed at 10:27:11, before realized values were joined. | `runs/20261013T022702Z/` |
| 10:31–10:33 | Replicate run `20261013T023112Z` (no root deliverables) | `runs/20261013T023112Z/` |
| After 10:33 | Descriptive post-analyses on the primary run's own outputs | `raw_coefficients.csv`, `province_event_tables.csv`, `quarter_event_tables.csv` |

The protocol hash was checked by the runner at the start of both runs, and again at the end of the experiment. **It is unchanged.**

## 2. Tests

| Test | Result |
|---|---|
| Guard decisions, 13 parametrized cases:<br>• denied: reads of `psa_indicators`, `sws_hunger`, `cpi_full`, `labels`, the 2026-H1 CPI file, the E10 sealed Q4 predictions, a non-allowlisted E12 file and `~/.claude`; writes to production code and to the E12 folder<br>• allowed: the 2 allowlisted reads tested and a write inside E13 | Pass |
| No allowlisted file name matches a protected or mixed pattern | Pass |
| `h_last` uses only rounds published before the origin | Pass |
| Target-A training pairs: every target fully published before the origin, and each lies at least 2 quarters before T | Pass |
| B features use only quarter T−2 | Pass |
| **Future-perturbation invariance (synthetic):** A and B training sets and features are unchanged when future values are set to 999 | Pass |
| Ridge recovers a known slope; confusion counts and ROC-AUC correct; sign-flip p and Holm correct; bootstrap of identical arms gives 0 | Pass |
| **Total** | **23 passed** (`tests/pytest_output.txt`; re-run at the end: 23 passed) |

**Runtime checks inside the run:**

- **Future-perturbation check on the real data.** For each test quarter, every value not available at origin(T) was set to 999 and all forecasts were recomputed. All 9 A quarters, all 7 S-A1 quarters and all 11 B quarters gave **identical** forecasts. The runner stops on any difference.
- **Allowlist hashes** were identical at the start and end of each run.
- **The guard** raised no denial. Any denial stops the run, and both runs completed.

## 3. Reproducibility

| File | Primary run | Replicate run | Result |
|---|---|---|---|
| `predictions.csv` | `868581d5…` | `868581d5…` | Identical |
| `scored_rows.csv` | `94e16df4…` | `94e16df4…` | Identical |
| `metrics.json` | `4234d060…` | `4234d060…` | Identical |
| `baseline_comparison.csv` | `a92565f8…` | `a92565f8…` | Identical, and equal to the root `BASELINE_COMPARISON.csv` |
| `model_comparison.csv` | `0c158907…` | `0c158907…` | Identical, and equal to the root `MODEL_COMPARISON.csv` |
| `SEAL.json` | — | — | Differs only in the `sealed_utc` timestamp |

**Environment:** Python 3.13.2, pandas 2.3.3, numpy 2.4.4, scikit-learn 1.8.0, Windows 11. Interpreter: `backend/venv`, read-only.

**Command:**

```
cd aipheed-backend-aligned/experiments/2026-10-13_E13_DA_Predictive_Accuracy
../../../backend/venv/Scripts/python.exe -B runner/run_e13.py
```

The run needs the five allowlisted inputs with their exact hashes.

## 4. Deviations from the protocol

| # | Deviation | Effect |
|---|---|---|
| 1 | Three descriptive post-analyses were added after the primary run. They recover raw coefficients and tabulate errors and events by province and quarter. They read only this experiment's `scored_rows.csv`. | **None on any result.** They describe already computed forecasts and were not used for selection. |
| 2 | Several documentation figures were corrected before finalization: the SWS publication lag, model RMSE and bias, the B2 sign-call changes, the 2024-Q1 error explanation, and one Cavite range. | **None on any computed value** |

No analysis was re-run to change a result. No arm, feature, threshold or setting was added after the freeze.

## 5. Limits of these tests

1. **Release dates are not verified.** The tests show that the code uses only T−2 provincial data and rounds published before the origin. Provincial CPI release dates remain **proxies**.
2. **The data are not real-time vintages.** The stored CPI values are the current ones, not the values as first released.
3. **The test is not independent.** Every test quarter was examined in E1–E12. No test here creates an independent, out-of-sample evaluation.
