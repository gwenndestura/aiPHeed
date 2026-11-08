# FI9 implementation and deployment

## Components

| Part | File |
|---|---|
| Quarter arithmetic (dynamic, never hardcoded) | `backend/app/fi9/quarters.py` |
| Locked protocol | `backend/app/fi9/protocol.py` → `data/fi9/out/PROTOCOL_LOCK.json` |
| Forecast-time dataset and vintage table | `backend/app/fi9/vintage.py` |
| Training and evaluation script (walk-forward, ablation, selection) | `backend/app/fi9/evaluate.py` |
| Training of the served artifact and pure inference | `backend/app/fi9/serve.py` → `data/fi9/model/lead1_model.json` |
| Independent audit | `backend/app/fi9/audit.py` → `data/fi9/out/audit.json` |
| Reports | `backend/app/fi9/report.py`, `backend/app/fi9/validation_log.py` → `docs/fi9/` |
| API | `backend/app/api/v1/fi9.py` (mounted in `app/api/router.py`) |
| Dashboard card | `frontend/src/components/NextQuarterOutlook.tsx`, hook `useNextQuarterOutlook` in `frontend/src/lib/queries.ts`, placed first in the right column of `MapDashboard.tsx` |
| Tests | `backend/tests/unit/test_fi9.py` (15), plus FI5–FI8 and label tests (83 in total pass) |

Also changed: `app/fi7/design.py`. The last issue quarter now follows the date instead of a fixed 2026-Q4. FI7
results are unchanged and the FI7 tests pass.

## Commands (from `backend/`, Python venv with the backend requirements)

```bash
python -m app.fi9.vintage build          # forecast-time dataset + vintage table + leakage checks
python -m app.fi9.evaluate run           # locked Lead-1 walk-forward (≈1 min on all cores); refuses if the protocol changed
python -m app.fi9.serve issue            # fit the artifact at the issue date, write forecast.json, register, LGU priority
python -m app.fi9.audit run              # independent audit; exit code 1 if any check fails
python -m app.fi9.report                 # regenerate the numeric reports
python -m app.fi9.validation_log         # needs openpyxl (e.g. the aipheed_fi5_xpu venv)
python -m pytest tests/unit/test_fi9.py
```

## Each quarter (operations)

1. After the previous quarter's SWS release, and no later than the last day of the quarter's second month,
   refresh the raw data (FI5/FI7 acquisition) and run `python -m app.fi9.vintage build` and then
   `python -m app.fi9.serve issue`. Then run `python -m app.fi9.audit run`.
2. `serve issue` appends the forecast to `data/fi9/out/PROSPECTIVE_REGISTER.csv`. That register is the only
   untouched evidence. Score it when each target quarter's SWS result is published, and never edit past rows.
3. Do **not** re-run `evaluate run` with a changed protocol. The lock refuses that. A new protocol needs a new
   version and lock.
4. If the issue is skipped, `/fi9/outlook` returns 503 `stale` from the first day of the next quarter, and the card
   shows "Unavailable". An old forecast is never presented as current.

## Deployment (Render API + Vercel frontend)

* The API image must include `backend/data/fi9/` (outputs, model, lock). No new Python dependency is needed for
  serving. `scipy` is already required.
* Set `AIPHEED_NOW` only for replays and tests. In production the clock is today's date.
* Rebuild the frontend. The card calls `/api/v1/fi9/outlook` through the existing `/api` rewrite.

## Verification done (2026-11-03)

* `GET /api/v1/fi9/outlook` on the running API returned 2026-Q4 → 2027-Q1, HIGH, p 0.44, projected 20 %.
* The dashboard (`/dashboard`, dev server) rendered the card with the same values (DOM check: current 2026-Q4,
  target 2027-Q1, class HIGH, 44 %, 20 %).
* Audit: 18/18 checks pass. Tests: 83 pass.
