# E180: system architecture (as found, 2026-11-07, branch aiPHeed/e166-drift-average @ a980ccc + uncommitted fixes)

## Components
- **Backend:** FastAPI (`backend/app/main.py`), SQLite (`aipheed.db`, Alembic migrations), APScheduler jobs (`app/tasks/scheduler.py`:
  quarterly cycle, incremental news, monthly refresh, SWS re-issue). Routers under `app/api/v1/` (dashboard, forecast, insights,
  report, thesis, admin/review, auth).
- **Frontend:** React + Vite + shadcn (`frontend/src`), map from `frontend/public/*.json` (81 provinces, 142 CALABARZON municipalities).
  Deployed on Vercel; the API is reached through a `/api` rewrite.
- **Deployment:** `render.yaml`: Docker web service from **branch main**, env `AIPHEED_LEAD2_MODEL=thesis`, `AIPHEED_STRICT_MODEL=1`.
- **Research code:** `backend/app/e1xx/` (experiments), `aipheed-backend-aligned/experiments/` (earlier experiments).
  Many earlier engines remain importable and selectable by env vars (E36/E38, E41/E42 Lead-2, thesis/Chapter I systems).

## Served path for E168 (local, default env)
Raw data → `app/e147/features.gov_row` and `app/e148/panel` (province × quarter inputs as of the issue quarter) and
`app/e151/prov.add_inputs` (news panel `data/e151/out/news_panel.parquet`) and `app/e154` (regional consumption) → training rows
`app/e150/model.Pipeline` (released rounds only) → anchors `app/e164/auto.anchors` → LightGBM survey-error model
`app/e151/prov.Res2` selected by `app/e168/lgbm.procedure` → temperature shrink `app/e166/temperature` → P(HIGH) = Phi(lambda·mu / sd),
HIGH at 0.5 → `app/e168/history.py` writes `data/e168/out/history/<quarter>.json` (forecasts, per-input LightGBM pred_contrib,
142-LGU ranking) → **serving overlay** `app/services/e166_serving.py` (model chosen by `AIPHEED_THESIS_MODEL`, default e168) hooked
into `app/services/dashboard.py` → API (`/provinces`, `/provinces/{id}/municipalities`, `/explainability`, `/quarters`, `/config`,
`/report`, `/thesis/*`) → React dashboard (`MapDashboard`, `LeftPanel`, `PhilippineMap`).

No model runs at request time: the served values are precomputed files. The overlay is **disabled** whenever a Lead-2 research mode is
active (`E41L2.active()`), which is the case under the Render environment (`AIPHEED_LEAD2_MODEL=thesis`); see DEPLOYMENT_RELIABILITY.md.
