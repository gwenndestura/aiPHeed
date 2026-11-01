# v4 API (additive, read-only)

**Router:** `backend/app/api/v1/hunger_forecast.py`.
- The earlier `/hunger-forecast` (legacy SEAS-LLM) and `/hunger-forecast/v2` routes are unchanged (`../API.md`).
- The route count goes from 109 to **112** (3 new GETs).
- The dashboard's P0H4 value stays labelled a price-pressure risk index (`ch1_system.INDICATOR`).

| Route | Parameters | 200 | Errors |
|---|---|---|---|
| `GET /api/v1/hunger-forecast/v4` | `issue_date` (optional quarter start) | `{status, key, records[16]}` | 422 bad date; 404 none for that issue; 503 none stored |
| `GET /api/v1/hunger-forecast/v4/explanation` | `lead` 1–4, `area` (enum), `issue_date` | `{status, record, explanation}` | 422 / 404 / 503 |
| `GET /api/v1/hunger-forecast/v4/geography` | `lead`, `issue_date` | 5 provinces, 142 LGUs: Balance Luzon value as `broader_area_reference`; own estimate `null` / `AWAITING_GROUND_TRUTH` | As above |

**Record fields:**
- **Identity and timing:** `issue_date`, `feature_cutoff`, `dashboard_quarter`, `target_quarter`, `lead`, `area`.
- **Value:** `score`, `lo80`, `hi80`, `interval_method`, `interval_residuals`, `unit`.
- **Components:** `latest_reading`, `noise_filter_adjustment`, and `predicted_change` by group (empty for persistence).
- **Data provenance:** `horizon_quarters_from_latest_data`, `latest_data_quarter`, `data_vintage_published`.
- **Model provenance:** `method` (AIPHEED-V4), `model`, `model_version`, `artifact_sha256`, `preprocessing_version`.
- **Status:**
  - `evidence_status`;
  - `geography_note`;
  - `reliability_status`, mechanical from `v4_verdict.json` and embedded in the artifact;
  - `claims`: sealed 75 % (frozen / amended), amended status `PROPOSED_NOT_ADOPTED`, sealed beats-all, development share;
  - `limitation`.

**Explanation:**
- **`predictive_contributions`:** they sum to `score` within 1e-3.
- **`five_group_summary`:** the snapshot values for each group, their `contribution` and `role` (model input only when the served model uses it), and `data_state`.
- **Also returned:** `missing_information`, `data_quality_warnings`, and `explanation_model_sha256`, which equals the forecast's artifact hash.

**Tests:** `backend/tests/unit/test_v4_core.py::test_v4_api` (VERIFIED).
