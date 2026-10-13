# Test results (E24, executed 2026-10-14)

## Python: `pytest -q --noconftest -c tests/pytest.ini --rootdir tests tests/` → **49 passed**

| Area | Tests (file) |
|---|---|
| Statistics (AUC vs scikit-learn; vectorised permutation = brute force; sign-flip; Holm; confusion counts; grid size) | `test_e23_lib.py` (6) |
| Forecast cutoff, publication-time (PHT) quarter assignment, news eligibility, retrieval date never used, authorization (BLOCKED), hash and vintage handling, idempotent archive, stale and late data, missing data, cutoff not reached, 2027-Q1 → 2027-Q2 transition, completeness (missing ≠ zero), API record = stored record | `test_quarterly_pipeline.py` (25) |
| Missing province → unavailable (not zero); disaggregator values; poverty fallback flag | `test_disaggregator_fix.py` (2) |
| NLP stage (eligible articles only; LIMITED_SIGNAL; 0.30 relevance gate); schema/duplicate/conflict checks; model version record; PSGC conversion (incl. Excel-numeric codes); PSA SAE workbook ingestion and validation; ranking labels substitutes; deterministic ties; persistence block uses only published labels (leakage); prospective sealing refuses without authorized 2026 features | `test_e24_additions.py` (11) |
| Questionnaire scorer (synthetic responses inside the test only): favorable vs neutral, ≥ 30 valid, consent exclusion, no imputation, **refuses non-Forms exports** | `test_score_responses.py` (5) |

## Frontend (`dashboard_dev/`): `npx vitest run` → **14 passed** (3 files)

`src/test/e24.test.tsx` (6) checks, on the **actual** `e24_dashboard.json`:

- the periods are consistent (2027-Q1 target, 2026-Q4 news);
- there is no forecast and no target-quarter ranking while data are insufficient;
- the goal is never shown as met while C9 is not assessable;
- all 142 LGUs are present and every province-mean substitute is labelled;
- the news window filter works;
- the PDF exists for the same quarter.

**Rendered-page test (jsdom + Testing Library).** The page shows:

- the banner text;
- INSUFFICIENT_DATA;
- 0 articles;
- "Goal NOT met";
- 142 ranking rows, filtering to 41 for Quezon;
- the C9 criterion on T2.

`npx tsc --noEmit -p tsconfig.app.json` reports no errors in E24 files. The two pre-existing errors are in `src/data/mockData.ts`.

`npx vite build --outDir dist-e24` builds (chunk-size warning only).

**Served check (vite preview, port 8100):** `/forecast-period`, `/e24_dashboard.json` and the PDF all return HTTP 200 with the correct content types. The PDF text contains the target, news and cutoff strings, INSUFFICIENT_DATA, "province-mean substitute" and "not assessable".

## Reproducibility and integrity checks

| Check | Result |
|---|---|
| E23 metrics recomputed from the sealed predictions | max abs diff **0.0**; identical rows across all models (asserted) |
| E24 required models vs E23 sealed predictions | max abs diff **0.0** |
| E24 run repeated (`20261013T160107Z` vs `20261013T160749Z`) | **Byte-identical seals:** T1 `effd3f4a…`, T2 `043d541f…` |
| Leakage assertions in every fold | Pass (training labels published before the origin; no training target ≥ test target; features of t / t−1) |
| LGU identity: census = poverty = reference (codes, names, population); density recomputed | All true; max diff 0.0 |
| LGU risk index vs E23 | max abs diff 0.0 |
| Chapter I re-extraction | Same PDF SHA-256 (`88dd0b62…`); text identical to E23 |
| 2027-Q1 quarterly cycle from the isolated copy | INSUFFICIENT_DATA, same missing items |

## Blocked tests (not run, and why)

| Test | Reason |
|---|---|
| Full backend pytest suite (`aipheed-backend-aligned/tests`, `backend/tests`) | Its `conftest.py` imports `app.main`, whose startup reads `aipheed.db`, model files and mixed parquet files. These are hash-only (not authorized). |
| Live API (`/api/v1/*` against the served model) | Same reason. The new quarterly endpoint is tested with an isolated FastAPI app. |
| Real-browser (Playwright/Chromium) checks | No browser automation is installed in this environment. The jsdom render test and the HTTP checks were used instead. **The page was not inspected visually.** |
| PSA SAE ingestion on the real workbook | The workbook is not obtainable (HTTP 403); only synthetic fixtures were tested |
| Prospective sealed forecasts | Need authorized 2026 features (`seal_prospective.py` correctly refuses, exit 2) |
