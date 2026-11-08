# v6 API (additive, read-only)

**Router:** `backend/app/api/v1/hunger_forecast.py`.
- The `/hunger-forecast`, `/v2` and `/v4` routes are unchanged.
- The route count is now **115** (VERIFIED by enumerating `app.routes`; 3 new GETs).
- The dashboard's P0H4 value stays labelled a price-pressure index (`ch1_system.INDICATOR`), with its computation unchanged.
- The served dashboard model was not replaced.

| Route | Parameters | 200 | Errors |
|---|---|---|---|
| `GET /api/v1/hunger-forecast/v6` | `issue_date` (optional quarter start) | `{status, key, records[16]}` (4 SWS areas × Leads 1–4) | 422 bad date; 404 none for that issue; 503 none stored |
| `GET /api/v1/hunger-forecast/v6/explanation` | `lead` 1–4, `area` (enum), `issue_date` | `{status, record, explanation}` | 422 / 404 / 503 |
| `GET /api/v1/hunger-forecast/v6/geography` | `lead`, `issue_date` | 5 provinces, 142 LGUs: Balance Luzon value as `broader_area_reference`; own estimate `null` / `AWAITING_GROUND_TRUTH` | As above |

**Record fields:**
- **Identity and timing:** `issue_date`, `feature_cutoff`, `dashboard_quarter`, `target_quarter`, `lead`, `area`.
- **Value:** `score`, `lo80`, `hi80`, `interval_method`, `interval_residuals`, `unit`.
- **Components:** `latest_reading`, `noise_filter_adjustment`, `predicted_change` (TreeSHAP totals by group if LightGBM is served; empty for persistence).
- **Provenance:** `horizon_quarters_from_latest_data`, `latest_data_quarter`, `data_vintage_published`, `method` (AIPHEED-V6), `model`, `model_version`, `artifact_sha256`, `preprocessing_version`.
- **Status:**
  - `evidence_status`, `geography_note`;
  - `reliability_status`, computed: the verdict file value embedded in the artifact;
  - `claims`: sealed 75 % (frozen / proposed), proposed status `PROPOSED_NOT_ADOPTED`, sealed beats-all, development share;
  - `limitation`.

**Explanation:**
- **`predictive_contributions`:** they sum to `score` within 1e-3.
- **`five_group_summary`:** snapshot values, `contribution`, `role`, `data_state`.
- **Also returned:** `missing_information`, `data_quality_warnings`, and `explanation_model_sha256`, which equals the forecast's artifact hash.
- TreeSHAP values, if ever served, are labelled model attributions, not causes.

**Tests:** `backend/tests/unit/test_v6_core.py::test_v6_api` (VERIFIED).
