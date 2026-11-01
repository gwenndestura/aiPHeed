# API (phase 8)

**Sources:**
- Every route is enumerated by `python -I backend/scripts/api_audit.py` (VERIFIED); the per-route table is `docs/aipheed/results/api_audit.csv`; the run log is `api_audit_run.txt`.
- The frontend contract base path is `/api/v1`; `/v1/health` is kept for probes.

## Audit result

| Check | Result |
|---|---|
| Routes | **106** (method × path) |
| GET routes without path parameters, smoke-tested | **85**: 67 × 200, 7 × 401 (admin, unauthenticated), 4 × 404, 5 × 422 (required query missing), 2 × 503 |
| Unhandled 500 | **0** after fix D10 (before: `/assessments/quarters` and `/assessments/methodology` returned a plain-text 500) |
| Error bodies | All tested 4xx/5xx return JSON with `detail` |
| Secrets in bodies | None matched (`secret`, `password`, `api_key`, `token` followed by a value) |
| Mutating routes without an auth dependency | Only the intentionally public `POST /auth/*` (login, refresh, signup, verify, resend, forgot and reset password) and `POST /feedback`. Every `/admin/*` route carries the admin dependency (16 of 16). |
| Read-only guarantee | Every non-admin GET is read-only (INFERRED from code). The new hunger-forecast routes only read stored files (VERIFIED by test: POST returns 405). |
| API docs exposure | `/docs` and `/openapi.json` are off unless `ENABLE_API_DOCS=true` (INFERRED, `app/main.py`) |

**Not tested:** GET routes with path parameters, and authenticated and admin flows, beyond the existing test suite (`tests/integration/test_api_*.py`).

## Route groups

| Group (`/api/v1/…`) | Routes | Purpose | Notes |
|---|---|---|---|
| `dashboard`, `quarters`, `provinces`, `ranking`, `search`, `forecast`, `explainability`, `report`, `readiness`, `config`, `news` | 13 | **Served dashboard** (P0H4 Chapter I risk probability in thesis mode) | Unchanged |
| `quarterly` | 18 | Forecast period, record and status | Unchanged |
| `assessments` | 3 | Revised province assessments (legacy E7) | **D10 fixed:** a missing artifact now gives 503 + JSON |
| `final`, `lead2`, `simple`, `fpp`, `e107` … `e113`, `forecast-history` | 37 | Read-only experiment exports | Unchanged (AUDIT D6: large surface) |
| **`hunger-forecast`** (new) | 3 | Numerical SWS hunger forecast (SEAS-LLM, E134 Addendum 2 prospective primary) | See below |
| `auth`, `admin`, `alerts`, `rejections`, `feedback`, `health` | 31 | Accounts, publication workflow, alerts, health | Unchanged |

## New: `/api/v1/hunger-forecast` (read-only)

| Route | Parameters | 200 | Errors |
|---|---|---|---|
| `GET /api/v1/hunger-forecast` | `issue_date` (optional, quarter start, YYYY-MM-DD) | `{status, key, records[16]}`: 4 areas × Leads 1–4 | 422 bad date or not a quarter start; 404 none stored for that issue; 503 none stored at all |
| `GET /api/v1/hunger-forecast/explanation` | `lead` 1–4 (default 2), `area` (enum), `issue_date` | Record + exact additive explanation; trigger groups as context | 422 invalid lead or area; 404 / 503 as above |
| `GET /api/v1/hunger-forecast/geography` | `lead`, `issue_date` | 5 provinces and 142 LGUs, each with `broader_area_reference` (Balance Luzon) and estimate `null` / `AWAITING_GROUND_TRUTH` | As above |

**Each record contains:**
- `issue_date`, `feature_cutoff`, `dashboard_quarter`, `target_quarter`, `lead`, `area`;
- `score`, `lo80`, `hi80`, `unit`, `components` (level, design_effect);
- `horizon_quarters_from_latest_data`, `latest_data_quarter`, `data_vintage_published`;
- `model`, `model_version`, `artifact_sha256`, `preprocessing_version`;
- `evidence_status`, `geography_note`, `reliability_status`.

**Every response states** that this is a prospective candidate, not the dashboard's served model, and that no lead has passed N1–N7.
