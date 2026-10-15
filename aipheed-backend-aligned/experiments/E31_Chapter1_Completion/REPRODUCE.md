# E31 reproduction

Interpreter: `C:\Users\admin\aipheed\backend\venv\Scripts\python.exe -B` (shown as `PY`). Run from the E31 folder.

| Step | Command | Output |
|---|---|---|
| 1 | `PY runner/e31_freeze_q3.py --verify` / `PY runner/e31_freeze_q3_p45.py` | frozen 2026-Q3 records reproduce (git 70d8770, bbbe104) |
| 2 | `PY runner/e31_score_q3.py` | `runs/e31_q3_scores.json` |
| 3 | `PY runner/e31_extend_inputs.py` | input vintage 2 (+2026-Q3); vintage 1 kept in `backend_dev/data/inputs_vintage1_e29/` |
| 4 | `PY runner/news_cli.py backfill --store data/news_e31 --from 2026-Q3 --to 2026-Q4` (live), then `score` | `backend_dev/data/news_e31/` |
| 5 | `PY runner/e31_relevance_sample.py`; `PY runner/e31_relevance_holdout.py`; `PY runner/e31_relevance_eval.py dev` | `validation/` (labels are in `labels_annotator_claude.txt`) |
| 6 | `PY runner/e31_fssi_v2.py` | FSSI-v1 and FSSI-v2 panels |
| 7 | `PY runner/e31_eval_fssi_v2.py v1` and `v2` | `runs/e31_eval_v1/`, `runs/e31_eval_v2/` |
| 8 | `PY runner/e31_operational.py`; `PY runner/build_record_e31.py` | `backend_dev/data/e31/` record and PDF, `dashboard_dev/public/e31_record.json` |
| 9 | `PY -m pytest -c tests/pytest.ini tests` | 141 passed, 2 skipped |
| 10 | `SP=<dir> bash runner/start_e2e_server.sh 8031`; `scripts/create_admin.py`; `scripts/stage_alerts_e31.py`; then `AIPHEED_E2E_ADMIN_EMAIL=… AIPHEED_E2E_ADMIN_PASSWORD=… PY -m pytest -c tests/pytest.ini tests/test_e31_e2e_live.py` | 13 passed |
| 11 | in `dashboard_dev/`: `npx vitest run`; `npx vite build` | 42 passed; build OK |

Deployment (backend): set `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`; run `alembic upgrade head`; create admins with `scripts/create_admin.py`; serve `uvicorn app.main:app`. The E31 record path is `AIPHEED_E31_RECORD` (default `data/e31/e31_record.json`); `AIPHEED_DATA_LAYER=legacy` restores the pre-E31 model.
