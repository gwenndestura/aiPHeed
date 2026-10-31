# E130 · Provincial food-insecurity risk-score forecasting

**Outcome: BLOCKED.** Start with `E130_RELIABILITY_DECISION.md` and `E130_FINAL_RECOMMENDATION.md`.

- **Branch:** `aiPHeed/corrected-data-pipeline`; starting commit `99358f0`.
- **Protocol:** frozen at `b58c48e` (sha256 in `runner/PROTOCOL_SHA256.txt`).
- **Scope:** offline research only. No production, dashboard, FIRI v2, FIRI3, E128 or E129 change. Nothing pushed.

## Reproduce

Use the backend virtual environment (Python 3.13, pandas, scipy, scikit-learn, lightgbm, shap). Run from this folder:

```
python runner/build_e130.py        # inventory, reference data and uncertainty, feature availability, lead mapping, gate (~10 s)
python runner/seal_e130.py         # survey-year seal; refuses to overwrite the existing seal
python runner/diagnostics_e130.py  # D1-D15, gate re-check, planning simulation (~10 s)
python runner/report_e130.py       # tabular deliverables (splits, results, predictions, comparisons, ablation)
python runner/score_e130.py        # scores the seal once data/owner_supplied/psa_subsistence_population_2025.csv exists
```

Tests: `backend/tests/unit/test_e130_provincial.py`.

## Files

| Kind | Files |
|---|---|
| Protocol and logs | `E130_FROZEN_EXPERIMENT_PROTOCOL.md`, `DEVIATIONS.md`, `CONTAMINATION_LOG.md`, `sources/SOURCES_LOG.md` |
| Target | `E130_PROVINCIAL_TARGET_VALIDITY_AUDIT.md`, `E130_REFERENCE_RISK_SCORE_METHODOLOGY.md`, `E130_REFERENCE_SCORE_DATA.csv`, `E130_TARGET_UNCERTAINTY_AUDIT.md` |
| Data and timing | `E130_DATA_INVENTORY.csv`, `E130_PROVINCIAL_FEATURE_AVAILABILITY.csv`, `E130_ISSUE_DATE_AND_OPERATIONAL_LEAD_MAPPING.csv` |
| Evaluation records | `E130_WALK_FORWARD_SPLITS.csv`, `E130_MODEL_TRAINING_RESULTS.csv`, `E130_NUMERICAL_RISK_SCORE_PREDICTIONS.csv`, `E130_LEAD_1_TO_4_NUMERICAL_COMPARISON.csv`, `E130_BASELINE_COMPARISON.csv`, `E130_FEATURE_GROUP_ABLATION.csv`, `E130_RELIABLE_HORIZON_COMPARISON.csv` |
| Analyses | `E130_R1_R7_RELIABILITY_AUDIT.md`, `E130_SCORE_AGREEMENT_ANALYSIS.md`, `E130_OVERFITTING_ANALYSIS.md`, `E130_PROVINCIAL_BIAS_AND_GENERALIZATION.md`, `E130_CALIBRATION_AND_UNCERTAINTY.md`, `E130_MAXIMUM_RELIABLE_LEAD_TIME_REPORT.md`, `E130_FIRST_UNRELIABLE_LEAD_ANALYSIS.md`, `E130_SHAP_EXPLANATIONS.md`, `E130_MODEL_COMPARISON.md` |
| Decision | `E130_RELIABILITY_DECISION.md`, `E130_FINAL_RECOMMENDATION.md` |
| Sealed | `sealed/E130_SURVEY_YEAR_SEAL.csv` (sha256 `94a08cd1…`, in `sealed/E130_SURVEY_YEAR_SEAL_SHA256.txt`) |

**Machine outputs** (`out/`):

| File | Contents |
|---|---|
| `e130_manifest.json` | Starting commit, input hashes, library versions |
| `gate.json`, `gate_candidates.csv` | The frozen gate |
| `gate_recheck*.json` | The gate after the search |
| `reference_uncertainty.json` | Reference uncertainty |
| `mapping_summary.json` | Lead mapping summary |
| `diagnostics.json`, `d5_prices_vs_deprivation.csv` | Diagnostics |
| `planning_simulation.csv` | Synthetic only |

## What was not produced, and why

Each item below has its own report or CSV saying why:

| Item | Why not |
|---|---|
| Model artifacts | No model was trained: the gate is BLOCKED, and the survey-year task has 5 training rows |
| Fitted preprocessing pipelines | None fitted |
| SHAP values | No trained model to explain |
| Quarterly predictions and metrics | No quarterly provincial target to score |

What does exist:
- training configurations (protocol §5);
- the feature manifest (`E130_PROVINCIAL_FEATURE_AVAILABILITY.csv`);
- the target construction code (`runner/e130_lib.py: load_reference`).

## Scoring the seal

1. Download manually PSA's 2025 table "Annual Per Capita Food Threshold and Subsistence Incidence Among Population … by Region and Province" (Table 4).
   - The 2026-10-31 workbook `2025 Full Year Official Poverty Statistics_24Aug2026_0.xlsx` does **not** contain it: it has poverty Tables 1, 2, 5, 6 and 15 only.
2. Run `python -I runner/extract_psa_2025.py <workbook.xlsx>`.
   - It hashes the workbook, reads only the header rows and the five provinces' 2023/2025 estimate and CV cells, and writes `data/owner_supplied/psa_subsistence_population_2025.csv`.
   - Alternatively, write that CSV by hand with the columns `province, survey_year, subsistence_incidence_pct, cv_pct, source, publication_date` (subsistence among the **population**).
3. Run `python runner/score_e130.py`.

The result is five provinces in one fold: descriptive only.
