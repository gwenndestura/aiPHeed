# E34 reproduction

`PY` = `C:\Users\admin\aipheed\backend\venv\Scripts\python.exe`. `SP` = any scratch directory. Run from `E34_Completion_Audit/` unless noted.

| Step | Command | Output |
|---|---|---|
| 1 | `PY -B runner/e34_news_audit.py` | `runs/e34_news_audit.json` (news audit C1–C6) |
| 2 | `PY -B runner/e34_model_audit.py` | `runs/e34_model_audit.json` (accuracy CIs, balanced accuracy, McNemar, nested selection, power) |
| 3 | in `../E32_New_Model`: `PY -B runner/e32_evaluate.py`, then `cmp runs/<new>/predictions.csv runs/20261014T165201Z/predictions.csv` | byte-identical (moved to `runs/e32_repro_*`) |
| 4 | `PY -B runner/e34_promote_frontend.py` (dry run) / `--apply` | `runs/e34_frontend_promotion*.json` |
| 5 | `PY -B runner/e34_promote_backend.py` (dry run) / `--apply` | `runs/e34_backend_promotion*.json`; refuses if the new data folders already exist |
| 6 | `PY -B runner/e34_patch_timeline.py <backend_dev> <backend>`; `PY -B runner/e34_patch_alerts.py <backend_dev> <backend>` | D1/D2 and D3 (idempotent) |
| 7 | in `../E31_Chapter1_Completion`: `PY -B -m pytest -c tests/pytest.ini tests`, and again with `AIPHEED_TEST_BACKEND=C:/Users/admin/aipheed/backend` | 138 passed, 16 skipped each |
| 8 | in `backend/`: `PY -B -m pytest tests -p no:cacheprovider` | 150 passed, 18 skipped (listed in `tests/conftest.py`) |
| 9 | `SP=<dir> bash runner/e34_live_e2e.sh ../E31_Chapter1_Completion/backend_dev 8031 e31_backend_dev`; `SP=<dir> bash runner/e34_live_e2e.sh C:/Users/admin/aipheed/backend 8032 main_backend_promoted` | `runs/e2e_*.log`: 16/16 each. Fresh SQLite in SP; random key and admin password; production `aipheed.db` untouched |
| 10 | `SP=<dir> bash runner/e34_screenshots.sh` | `runs/screenshots/*.png`, `api_calls.txt` |
| 11 | in `frontend/`: `npx vitest run`; `npx vite build` | 43/43; build OK |
| 12 | in `../E32_New_Model`: `PY -B -m pytest -c tests/pytest.ini tests` | 16/16 |
