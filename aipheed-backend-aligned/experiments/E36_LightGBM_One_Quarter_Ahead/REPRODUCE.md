# E36 reproduction

PY = C:\Users\admin\aipheed\backend\venv\Scripts\python.exe. Run from this folder unless noted.

| Step | Command | Output |
|---|---|---|
| 1 | `PY -B runner/e36_label_probe.py` | label/training-size probe (docs/LABEL_PROBE.txt) |
| 2 | `PY -B -m pytest -c tests/pytest.ini tests` | 14 leakage/timing tests |
| 3 | `PY -B runner/e36_evaluate.py` (twice; `cmp` the two predictions.csv) | runs/<stamp>/ predictions.csv, results.json; byte-identical |
| 4 | `PY -B runner/e36_freeze.py runs/20261015T023921Z` | models/, frozen/ (refuses to overwrite) |
| 5 | `PY -B runner/e36_diagnostics.py runs/20261015T023921Z`; `PY -B runner/e36_tables.py runs/20261015T023921Z` | runs/e36_diagnostics.json, docs/TABLES.md |
| 6 | in backend/: `PY -B scripts/build_lgu_psa_2021_2024.py --sae "<Downloads>/2018 - 2021 SAE_with PSGC_noHUC.xlsx" --pop "<Downloads>/3_Table B - ... rev_0.xlsx"` | PSA 2021 SAE + POPCEN 2024 inputs |
| 7 | in backend/: `PY -B scripts/build_record_e36.py` | data/e36/e36_record.json + PDF, frontend/public/e36_record.json |
| 8 | in backend/: `DATABASE_URL=sqlite+aiosqlite:///C:/nonexistent/x.db PY -B -m pytest tests -p no:cacheprovider` | 163 passed, 18 skipped |
| 9 | in E31: `PY -B -m pytest -c tests/pytest.ini tests` and with `AIPHEED_TEST_BACKEND=C:/Users/admin/aipheed/backend AIPHEED_E31_RECORD=data/e31/e31_record.json AIPHEED_E31_PDF=data/e31/aiPHeed_E31_assessment_report.pdf` | 138 passed, 16 skipped each |
| 10 | E35 suite with the E31 record pinned (as step 9) | 28 passed, 1 xfailed (D2) |
| 11 | in frontend/: `npx vitest run`; `npx vite build` | 51 passed; build OK |
| 12 | local preview: launch config `aipheed-e36-api` (runner/serve_local.py, scratch DB) + `aipheed-frontend` | http://localhost:8080 |
