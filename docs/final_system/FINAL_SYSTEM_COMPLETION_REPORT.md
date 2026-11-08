# Final system completion report

**Branch:** `aiPHeed/final-system-completion`, built from `ecb18dc`. That commit contains the deployed `final-system-v2` application code plus its later fixes, and E107–E114 and FINAL.

**Status:** nothing has been merged into production or deployed. Every sealed forecast is preserved and hash-verified.

## 1. Component status

| Component | Before | Now | Evidence |
|---|---|---|---|
| Backend API (FastAPI) | Working; FIRI v2 served in thesis mode | Working. Adds read-only `/api/v1/final/*`: overview, evaluation, families, contributions, archive, news, cpi, lgus | 787 passed / 18 skipped (full suite); 15 new API tests |
| Frontend (React/Vite) | Working, approved design | Working, same layout, colours and legend. Changes are wording plus content in two existing dialogs. | 75/75 vitest; production build OK; checked in browser |
| LightGBM forecasting engine | Research-only (experiments), not served | FIL-OA: the 12-family LightGBM forecasting regional SWS hunger. Exported and served with its evaluation, forecasts and archive. | `aipheed-backend-aligned/experiments/FINAL_OBJECTIVE_ACHIEVEMENT/`; `backend/data/final_engine/` |
| News NLP | Feed served; no event-kind distinction | Each served headline carries **Reported event** or **Possible future risk**, plus a context note. The final engine serves de-duplicated, dated food-event news with date cut-offs. | `app/services/final_engine.news_kind`; tests |
| 142-LGU map | Working; LGUs ordered within province | Unchanged map. Labelled as a priority score. `/final/lgus` serves all 142 with "insufficient local outcome evidence", poverty-precision notes and the province food-price squeeze. | test: 142 unique LGUs, no hunger field |
| Indicator contributions | SHAP of FIRI v2 (approved panel) | Unchanged panel ("Factors pushing / pulling the score"). Adds the LightGBM's own driver-group SHAP shares at `/final/contributions`. | test: shares sum to 1 and are not equal splits |
| Forecast archive | Past regional index values | Adds a "Hunger forecasts, Balance Luzon (SWS)" table to View history: forecast, latest reading, published outcome, correct/wrong, and sealed rows | test: retrospective rows have outcomes, prospective rows do not |
| Regional overview | FIRI index only | About & Methodology now shows the latest SWS survey (dates, age, BL and national rates, margin), the next-quarter outlook range, the LightGBM forecast and the evaluation table | Browser check |

## 2. Files changed

### Backend

| File | Change |
|---|---|
| `app/services/final_engine.py` (new) | The served engine (read-only) |
| `app/api/v1/final.py` (new) | The routes |
| `app/api/router.py` | Registers the routes |
| `app/services/dashboard.py` | News items gain an event-kind chip and a context note. No other change. |
| `data/final_engine/` (new) | `engine.json`, `archive.csv`, `news_events.csv`, `predictions_fil_oa.csv`, exported by `export_engine.py` |
| `tests/integration/test_api_final_system.py`, `tests/unit/test_final_objective_achievement.py` (new) | Tests |

### Frontend

These are wording and content changes only: no new colours, legends or components.

| File | Change |
|---|---|
| `components/AboutModal.tsx` | Two new sections inside the existing dialog, using its existing `Section`/`Row` styles; priority wording |
| `components/ForecastHistoryModal.tsx` | A second table in the same style; wording |
| `components/LeftPanel.tsx`, `MapLegend.tsx`, `MapTour.tsx`, `PageTours.tsx`, `GlossaryPanel.tsx`, `RightAnalyticsPanel.tsx`, `ui/status-badge.tsx`, `data/types.ts`, `pages/Data.tsx` | "risk" → "priority" where the FIRI index is shown |
| `lib/apiTypes.ts`, `lib/queries.ts` | Types and hooks for `/final/*` |
| `src/test/landing.test.tsx`, `factorCards.test.tsx` | Updated to the new wording and dialog sections |

### Experiments

| File | Content |
|---|---|
| `FINAL_OBJECTIVE_ACHIEVEMENT/` | Protocol (sha `d94f0c2c…`), library, runner, export, scorer, outputs, seal `03534689…`, local-data search log |

## 3. The model actually used

| Model | What it predicts | Where it is shown | Status |
|---|---|---|---|
| **FIL-OA LightGBM** | SWS involuntary hunger (% of families) for the 4 SWS areas, and ELEVATED (above its past-year average), at Leads 0–4 | About dialog, View history, `/final/*` | Evaluated; 75% not reached; no reliable horizon; best at Lead 0 (MAE 3.47 vs 4.19, p = .025) |
| Latest SWS reading | The same outcome (persistence) | About dialog outlook | The strongest baseline in accuracy |
| **FIRI v2 priority score** (existing) | A 0–1 indicator-based priority for provinces, with the 142 LGUs ordered within each province | The map | Not a probability or a hunger rate; not validated against a local outcome |
| E56 LightGBM price input (existing) | Food-price pressure, used as one FIRI input | Inside FIRI only | Not presented as a hunger forecast |

Full metrics are in `FINAL_MODEL_EVALUATION.md`.

## 4. Tests actually run (2026-10-26)

| Suite | Result |
|---|---|
| Backend full suite (`pytest tests`) | **787 passed, 18 skipped, 0 failed** (`backend_test_suite.txt`) |
| New final-system tests (API, OA, FINAL) | **38 passed**, re-run after the last change |
| Frontend unit tests (`vitest run`) | **75 passed** |
| Frontend production build (`vite build`) | **Succeeded** (pre-existing chunk-size warning) |
| Frontend type check | Only pre-existing errors in the unused `src/data/mockData.ts`; none in changed files |
| OA leakage audit | Passed at 10 origins, with the negative control |

**Manual checks (not automated)**, done in the in-app browser:
- the map page loads with the new wording;
- About & Methodology shows the live SWS reading (2026-Q3, BL 23.6%, 28 days old) and the evaluation table;
- View history shows 11 scored quarters and 1 sealed quarter;
- the news API returns kind chips.

## 5. Remaining issues that affect manuscript accuracy

| # | Issue | Effect |
|---|---|---|
| 1 | The 75% target is not met, and no reliable horizon is established | State this; do not claim otherwise. The validated ceiling explains why. |
| 2 | No provincial or municipal food-insecurity outcome | Objective 3's rankings come from an unvalidated index. Describe them as priority scores. CBMS 2024 LGU data exist but are not public. |
| 3 | Every 2021–2026 result is development evidence | The only untouched test is the seals, scorable from SWS 2026-Q4 (around January 2027). |
| 4 | FINAL's secondary long-history arm uses pre-2021 SWS | Cite it only as a separate sensitivity analysis, with the adviser's approval |
| 5 | The basemap tile file (`frontend/public/basemap.pmtiles`) is not provisioned locally | It is a gitignored deployment asset. Background tiles log errors; province and LGU polygons still render. Provision it per `docs/basemap.md`, or set `VITE_BASEMAP_PMTILES_URL`, before a demo. |
| 6 | ISO/IEC 25010 evaluation with DA evaluators and FNRI face validity not done in this work | Objective 5 remains partial |
