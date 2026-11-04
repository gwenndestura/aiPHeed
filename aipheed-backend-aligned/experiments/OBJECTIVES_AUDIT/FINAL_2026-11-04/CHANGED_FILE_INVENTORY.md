# Changed-file inventory (this task, 2026-11-04)

**Backups:** `OBJECTIVES_AUDIT/backup/backend_2026-11-04/`. It holds `foodinsecurity_system.py` (8f586d8e…),
`dashboard.py` (d0177ca5…), `test_foodinsecurity_mode.py`, `export_ce2.py` (a101362a…) and the previous
`foodinsecurity_engine_ce2/`.

## Backend application (authorized `/api/v1/config` correction)

| File | Change | SHA-256 after |
|---|---|---|
| `backend/app/ml/inference/foodinsecurity_system.py` | `indicator()` / `INDICATOR`, `model_performance()`, `serving_model()`, `horizon()` derived from evaluation | 27ade694… |
| `backend/app/services/dashboard.py` | Food-insecurity mode delegates `serving_model` / `model_performance` | 0b2f1f53… |
| `backend/tests/integration/test_foodinsecurity_config_metadata.py` | New (5 tests) | 94435117… |

## Research data (local demo export, not production)

| File | Change | SHA-256 after |
|---|---|---|
| `backend/data/foodinsecurity_engine_ce2/evaluation.json` | + Lead 4, `model_description`, `sources_extra`, ablation text | 1b30ee11… |
| `backend/data/foodinsecurity_engine_ce2/rows.csv` | **Unchanged** (byte-identical) | 10cef6e2… |

## Research scripts (`OBJECTIVES_AUDIT/runner/`)

| File | Change | SHA-256 |
|---|---|---|
| `export_ce2.py` | Leads to the first failing lead; metadata fields | c8d335da… |
| `obj1_annotation_v2.py` | New: adjudication, full metrics, selftest | 582a8abf… |
| `obj1_fssi_redundancy.py` | New | 291749b0… |
| `obj2_label_uncertainty.py` | New: error-level dataset, label uncertainty | f2de1c4f… |
| `obj3_exposure.py` | + bottom-5 and rank changes | 10e1365f… |
| `obj4_power.py` | New | 222d8979… |
| `seal_ce2_dryrun.py` | New (dry run only) | 50da8a7b… |

## Outputs (`OBJECTIVES_AUDIT/out/`)

| File | SHA-256 |
|---|---|
| `obj2_error_level.csv` | ba424bd2… |
| `obj2_label_uncertainty.json` | 09cb7b30… |
| `obj1_fssi_redundancy.json` | 7786947e… |
| `obj3_exposure.json` | 3fa7cda9… |
| `obj4_power.json` | 0224e305… |

## Reports

- `OBJECTIVES_AUDIT/FINAL_2026-11-04/*.md` (22 files).
- `EXPERIMENT_REGISTRY.md` notes C-w.

## Outside the repository

- Seal dry-run outputs and the demo database: the session scratchpad only.

## Earlier today (previous requests, already reported in `CE2_IMPROVEMENT_REPORT_2026-11-04.md`)

- CE3/CE4/CE5 plans and runners;
- `obj2_diagnostics.py`, `obj4_table.py`;
- the `REGISTRY.csv` append;
- `public.py` (optional `probabilityPricePressure`).
