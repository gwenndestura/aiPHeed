# E102: market/price and economic-access indicators

Protocol: `PROTOCOL.md` (SHA-256 in `runner/PROTOCOL_SHA256.txt`, frozen 2026-10-23T11:47:18Z before scoring).
Production (`backend/`, served FIRI v2, E56 LightGBM) is not changed. E100 and E101 files are not modified (they are imported).

## Reproduce

From `backend/`, with the backend virtual environment:

```
venv/Scripts/python.exe -m pytest -q -p no:cacheprovider ../aipheed-backend-aligned/experiments/E102_Market_Access_Forecasting/tests
venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E102_Market_Access_Forecasting/runner/e102_run.py
venv/Scripts/python.exe -B ../aipheed-backend-aligned/experiments/E102_Market_Access_Forecasting/runner/e102_explain.py
```

The run is deterministic; `out/sealed_prospective.csv.sha256` must stay `32c7fe769bdc766c01ba8f34e1a176de6862207ba5d6c1063ab8265729d654f8`.

## Files (all new; nothing else in the repository was changed)

| File | Role |
|---|---|
| `PROTOCOL.md` | Pre-registered design and decision rule |
| `runner/PROTOCOL_SHA256.txt`, `runner/PROTOCOL_FROZEN_AT.txt` | Integrity record |
| `runner/e102_lib.py` | As-of indicators (LVL, REL, PERS, ACC, VOL, LAG), percentiles, posted-outcome training pairs, models, metrics |
| `runner/e102_run.py` | All arms, both leads, ablation, sensitivity, seal |
| `runner/e102_explain.py` | Post-scoring explanation (weights, SHAP shares, coefficients); never used for selection |
| `tests/test_e102.py` | 5 tests: no future CPI, base-period zero, earlier-only percentiles, posted-only training pairs, served FIRI reproduction |
| `out/results.json`, `out/regional_lead1.csv`, `out/regional_lead2.csv` | Results |
| `out/explain.json` | Explanation diagnostics |
| `out/sealed_prospective.csv` (+ `.sha256`) | Prospective seal: Lead 1 2026-Q4; Lead 2 2026-Q4, 2027-Q1 |

Inputs (read only): `backend/data/thesis/firi2_history.csv`, `backend/data/inputs/sws_rounds.csv`, `backend/data/processed/cpi_full.parquet` (year >= 2021), `aipheed-backend-aligned/experiments/E63_Lead_Time_Study/sealed/predictions.csv` (hash-checked).
