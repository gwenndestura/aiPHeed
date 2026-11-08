# Frontend model verification: branch `aiPHeed/e158-thesis-model`

**Date:** 2026-11-07, updated 2026-11-08
**Checkout:** `C:\Users\admin\aipheed_e145`, based on HEAD `d8806524d789953e285380894efbde0ab7d05ac8`. The changes in §E are committed on `aiPHeed/e158-thesis-model` and pushed to that branch (owner instruction, 2026-11-08). `main` and the public site are unchanged.

**Naming.** The *branch* is called `e158-thesis-model`. The *model* it serves is **E168** (registry `e168-lgbm-1.0`), which the owner approved on 2026-11-07 to replace E158. The owner confirmed on 2026-11-07 that E168 stays. No code or artifact from branch `e168-system-fixes` was used.

## A. Executive verdict

### VERIFIED WITH LIMITATIONS

Every model-driven value the dashboard shows comes from the E168 artifact, through the registry and the production API, unchanged.
- **Province forecasts:** 15/15 province-quarters, Leads 1–3.
- **Municipal priorities:** 41/41 Quezon cities and municipalities.
- **Driver bars, Data page, Visualization chart, About window and History window:** all E168.

Before this work, eight user-visible places described the retired price-pressure / FIRI system or misstated the trigger groups. They are fixed (§E).

**Limitations (§H):**
- Not deployed: the public site still serves FIRI v2.
- The basemap tile file is not on this machine; it must be provided separately (`docs/basemap.md`).
- The admin pages and the downloaded PDF file itself were not opened in the browser.

## B. Frontend inventory

| Page / component | Model-driven? | Inspected in browser | Notes |
|---|---|---|---|
| `/` Landing (`pages/Landing.tsx`): about, data sources, method steps, accuracy tables, limitations, FAQ | text + metrics | yes | Data-source table, step 3 and limitations fixed |
| `/dashboard` `MapDashboard` → `PhilippineMap` (province colours, municipal colours) | yes | yes | Colours = API `riskLevel` |
| `LeftPanel` → `RfiiScoreCardBody` (regional card, High/Low/Limited counts) | yes | yes | 0.03 = mean of the 5 API probabilities |
| `LeftPanel` → `RiskDriversCardBody` (Relative model influence) | yes | yes | Now includes "Other model inputs"; adds to 100 |
| `LeftPanel` → `ProvinceRankingCardBody` | yes | yes | Labels fixed; missing forecast shown as "No forecast" |
| `LeftPanel` → `TriggerCompositionBar` (province view) | yes | yes | Now includes "Other model inputs" |
| Province view: score card, municipalities list | yes | yes | 41/41 Quezon LGUs = API |
| `RightAnalyticsPanel` (summary, factor cards, news) | yes | yes | Plain names disclose national figures and the fish-kill substitute |
| `FoodInsecurityStatus` ("About this forecast" box, top right) | yes | yes | Rendered (an earlier version of this report wrongly listed it as unused). Rewritten in plain words; the pending state no longer mentions the price index |
| `MapLegend` (tooltip) | definition | yes (aria-label) | Old "regional hunger above 11.3% …" definition replaced |
| `QuarterTimeSlider` + quarter selection | quarter state | yes | Q1/Q2/Q3 2027 each refetched all panels |
| `ForecastHistoryModal` (View history) | yes | yes | "Index" header → "Probability"; description fixed |
| `AboutModal` | yes | yes | Data-source list fixed; overview text fixed (backend) |
| `GlossaryPanel` | text | code + test | Fish-kill proxy, national series, Other inputs added |
| `MapTour`, `PageTours` | text | code | Tour step 1 already E168; "topics such as fish kill" refers to news topics (unchanged) |
| `/data` Data page | yes | yes | Q1 table = API |
| `/visualization`: trend chart, Feature Contribution chart, PDF download | yes | yes (charts); PDF via API | Other bar added; PDF text fixed at `/report/data` |
| `/admin` | review queue | no (needs admin login) | Unused mock-data import removed |
| Unused, removed (no importer): `AnimatedStatWidgets`, `EmphasisAlerts`, `NationalTrendChart`, `RegionalRankingsTable`, `SidebarPeek`, `ForecastBanner`, `lib/pdfReport.ts`, `data/mockData.ts` | static demo predictions | – | Deleted with `git rm` (restorable) |
| Unused, kept deliberately: `NextQuarterOutlook`, `ProvincialOutlook` | legacy endpoints | – | Not rendered; a test guards that the dashboard never mounts them |

## C. Model-to-UI traceability

| Frontend page/component | API endpoint | Model identifier | Source field | Rendered value verified? | Status |
|---|---|---|---|---|---|
| Map colours, ranking, regional counts | `GET /api/v1/provinces?quarter=…&horizon=nowcast` | `e168_food_insecurity_risk` (indicator id) | `data[].riskScore`, `riskLevel` | yes, Q1–Q3 | ✅ |
| Regional card | `GET /api/v1/forecast?scope=region&id=calabarzon` | E168 | `riskScore` (mean of 5) | yes (0.03) | ✅ |
| Relative model influence, province trigger bar, factor cards, Visualization chart | `GET /api/v1/explainability` | E168 rows (`dashboard_rows.csv`, LightGBM `pred_contrib`) | `triggers[].pct`, `label`, `otherPct` | yes (sums 100) | ✅ fixed |
| Right panel "Food-insecurity forecast" | `GET /api/v1/final/food-insecurity/outlook` | `e168-lgbm-1.0` | `model`, `name` | yes | ✅ |
| Municipalities | `GET /api/v1/provinces/{id}/municipalities` | `e168_food_insecurity_risk` | `data[].riskIndex` | yes (41/41 Quezon) | ✅ |
| Data page | `GET /api/v1/provinces` | E168 | `riskScore`, `riskLevel` | yes | ✅ |
| History window | `GET /api/v1/final/risk/rows`, `/forecast/timeseries` | `e168-lgbm-1.0` | rows | yes | ✅ |
| About: accuracy | `GET /api/v1/final/risk/evaluation` | `e168-lgbm-1.0` | `leads[].metrics` | yes | ✅ (confusion counts corrected) |
| About: SWS context + local evidence | `GET /api/v1/final/overview` | – (context) | `regionalHunger`, `localEvidence` | yes | ✅ fixed |
| PDF report (Visualization → Download PDF) | `GET /api/v1/report/data` | E168 via map engine | `metadata`, `blocks` | API text only | ✅ fixed (file not opened) |
| (not displayed) | `GET /api/v1/config` → `modelPerformance`, `servingModel` | still FIRI v2 text | – | API | ⚠ open (not shown to users) |
| Registry | `GET /api/v1/final/model-registry` | `e168-lgbm-1.0`, artifact `data/e168/out/live_2027.json` SHA-256 `0d3b41ae…` | `production` | API | ✅ |

## D. Five-province verification

**Stages:** artifact `live_2027.json` → API `/provinces` (production environment: Dockerfile `AIPHEED_LEAD2_MODEL=thesis`, `AIPHEED_STRICT_MODEL=1`) → browser ranking text.

**Tolerance:** API = artifact exactly; rendered = API rounded to 2 decimals.

| Quarter | Province | Artifact p_high / class | API riskScore / level | Rendered | Match |
|---|---|---|---|---|---|
| 2027-Q1 | Quezon | 0.076 / LOW | 0.076 / low | 0.08 Low food-insecurity risk | ✅ |
| 2027-Q1 | Rizal | 0.068 / LOW | 0.068 / low | 0.07 Low | ✅ |
| 2027-Q1 | Laguna | 0.016 / LOW | 0.016 / low | 0.02 Low | ✅ |
| 2027-Q1 | Cavite | 0.009 / LOW | 0.009 / low | 0.01 Low | ✅ |
| 2027-Q1 | Batangas | 0.003 / LOW | 0.003 / low | 0.00 Low | ✅ |
| 2027-Q2 | Quezon / Rizal / Laguna / Cavite / Batangas | 0.076 / 0.068 / 0.016 / 0.009 / 0.002, all LOW | same | 0.08 / 0.07 / 0.02 / 0.01 / 0.00 | ✅ |
| 2027-Q3 | Quezon / Rizal / Laguna / Cavite / Batangas | 0.076 / 0.068 / 0.017 / 0.009 / 0.002, all LOW | same | 0.08 / 0.07 / 0.02 / 0.01 / 0.00 | ✅ |

Reproduce with:

`python backend/scripts/verify_e168_model_to_ui.py docs/e158_frontend_verification/evidence/rendered_ranking_values.json`

It exits 0, with `problems: []`. Output: `evidence/model_to_ui_check.json`.

## E. Problems found and fixes

| # | Problem (user-visible) | Root cause | Files changed | Fix | Test evidence |
|---|---|---|---|---|---|
| 1 | Province ranking labelled every province "Low **Price** Risk" | `RISK_LABELS` kept from the price-pressure system | `frontend/src/data/types.ts` | "Low / High food-insecurity risk" | `e168ModelToUi.test.tsx` (labels, ranking) |
| 2 | Map legend defined High as "regional hunger above 11.3% and unusually fast food-price rises" | Old CH1 definition | `components/MapLegend.tsx` | E168 / FNRI HFIAS definition | `e168ModelToUi.test.tsx` (legend) |
| 3 | PDF report said "price-pressure risk index; **not a food-insecurity forecast**" | Report text hard-coded the Chapter I noun whenever the map engine was on | `backend/app/services/report_data_e31.py`, `app/ml/inference/e168_system.py` | The noun comes from the served engine (`REPORT_NOUN`); E168 says food-insecurity risk | `test_report_and_config_describe_e168_not_the_retired_index` |
| 4 | About window: "The map shows an **indicator-based priority score**…", and wrongly "no provincial figure in 2021-2026" | Stale constant | `backend/app/services/final_engine.py` | Accurate text (FNRI 2021 exists; province values are forecasts) | same test + `test_api_final_system.py` (assertion updated to the corrected meaning) |
| 5 | Driver bars rescaled the five groups to 100 %, hiding ~25–40 % of attribution (poverty, density, timing) | Shares computed over five groups only; `otherPct` dropped by the schema | `services/dashboard.py`, `schemas/public.py`, `api/v1/insights.py`, `LeftPanel.tsx` (2 places), `Visualization.tsx`, `apiTypes.ts` | Shares over all \|contributions\|; "Other model inputs" shown; five + other = 100 | `test_driver_shares_include_other_and_add_to_100`, `e168ModelToUi.test.tsx` |
| 6 | Fish kill shown as "Fisheries production" without saying it is a proxy; national series not flagged | Labels | `e168_system.py` (labels, evidence text, indicator definition), `driverCopy.ts`, `GlossaryPanel.tsx`, `Landing.tsx` | "Fish Kill (fisheries production proxy)", "Employment (national)", "OFW Remittance (national)", plus disclosure text | `test_five_triggers_labelled_honestly`, `test_fish_kill_bar_is_disclosed_as_a_proxy`, updated driver-copy tests |
| 7 | Landing data-source table and About source list described the retired system (World Bank Pink Sheet, PAGASA advisories, "9,667 Google News headlines", periods from 2021); NASA rainfall/soil missing | Not updated when E168 was adopted | `Landing.tsx`, `AboutModal.tsx` | Rebuilt from E168's actual inputs (`lgbm_only.FS`) | `landing.test.tsx` (updated) |
| 8 | Landing: "news classifier was checked by the system author, not by an independent reviewer" | Predates the DA sign-off | `Landing.tsx` | States the DA dataset sign-off and that no item-level second annotation was done | landing text |
| 9 | Missing province forecast would display as 0.00 / Low and be counted as Low | `provinceToRegion` used `?? 0` / `?? "low"` | `lib/adapters.ts`, `data/types.ts`, `MapDashboard.tsx`, `LeftPanel.tsx` | `hasForecast` flag; grey on the map, "No forecast" / "—" in the ranking, excluded from High/Low counts | `e168ModelToUi.test.tsx` (no-forecast case) |
| 10 | Mock prediction data compiled into the app (Admin imported `SidebarPeek` → `mockData`); 6 TypeScript errors in `mockData.ts` | Dead demo components | 8 files removed; `Admin.tsx` import removed | `git rm` (restorable); TypeScript now 0 errors | `e168ModelToUi.test.tsx` (import scan) |
| 11 | `/config` `modelPerformance` / `servingModel` still describe "thesis system v3: FIRI v2" (not displayed) | PDF report code reads that structure | none (attempted, reverted: it broke 16 report tests) | **Open**: needs a report-safe change | – |
| 12 | `/final/risk/evaluation` confusion counts: `tp` = number correct, `tn` = 0 | Bug in `evaluation()` | `e168_system.py` | TP/FP/FN/TN derived from stored HIGH count, recall and precision (Lead 1: 22/15/3/32) | `test_evaluation_confusion_matrix_is_consistent` |
| 13 | History window header "Index" and "past … the newest PSA has published" text | Old wording | `ForecastHistoryModal.tsx` | "Probability"; issue-date description | browser |
| 14 | Silent fallback: if the registry stopped naming `e168-lgbm-1.0` or `dashboard_rows.csv` were missing, the map engine served the Chapter I price index, and strict start-up only checked the old FIRI v2 system | Strict check never looked at E168 | `app/main.py`, `e168_system.py` (`not_served_reasons`) | Strict start-up refuses to run and names the reason; the start-up message names `e168-lgbm-1.0` | `test_strict_start_refuses_when_e168_is_not_served` |
| 15 | Dashboard wording too technical for the general public ("Relative model influence", "probability", "proxy", "PSA LFS", "ONI deg C", "acceptance rule", …) | Written for researchers | `driverCopy.ts` (one shared list of plain names), `LeftPanel.tsx`, `RightAnalyticsPanel.tsx`, `FoodInsecurityStatus.tsx`, `MapLegend.tsx`, `MapTour.tsx`, `Data.tsx`, `Visualization.tsx`, `data/types.ts`, `e168_system.py` (evidence lines, summary sentence, data status) | "Why is this at risk?", "Chance of high food insecurity", "Jobs (national figures)", "Fish catch (instead of fish-kill reports)", "Other factors (poverty, population, timing)", "What is raising / lowering the risk", plain evidence and summary sentences. Same facts and disclosures; no numbers changed | updated frontend tests; browser (`07_plain_language_dashboard.jpg`) |

**Trigger groups.** Per the owner's specification, the five groups are Market / Prices, Climate Stress, Employment (national), OFW Remittance (national) and Fish Kill (fisheries production proxy); the dashboard shows them as Food prices, Weather and farm supply, Jobs (national figures), Money sent home by OFWs (national figures) and Fish catch (instead of fish-kill reports). An earlier uncommitted variant replaced Fish Kill with Poverty; it was reverted. Poverty is shown inside "Other model inputs".

## F. Test results (actual runs, 2026-11-07)

| Check | Result |
|---|---|
| Frontend unit + integration (`vitest run`) | **97 / 97 passed**, 19 files (9 new tests in `src/test/e168ModelToUi.test.tsx`) |
| TypeScript (`tsc --noEmit -p tsconfig.app.json`) | **0 errors** (was 6) |
| ESLint | 24 errors, 17 warnings, all pre-existing (same count as the unchanged branch; none in changed lines) |
| Production build (`vite build`) | success |
| Backend E168 / final-system / report tests | **72 passed, 4 skipped** (6 new) |
| Backend full suite | **1667 passed, 18 failed, 20 skipped**. The 18 failures are exactly the ones present before this work (legacy experiment locks E125–E144 and HFIAS, the two news-export guards, the v2 working-directory test); no new failures (log: `evidence/pytest_backend_final.log`) |
| End-to-end artifact → API → browser | 15 / 15 province-quarters match (`verify_e168_model_to_ui.py`, exit 0) |
| Browser verification | Dashboard (Q1, Q2, Q3), province view + 41 LGUs, Data page, Visualization chart, About, History, Landing, legend: done |
| Playwright / Cypress | none configured in the project; browser checks done in the built-in browser |

## G. Evidence (`docs/e158_frontend_verification/evidence/`)

- `01_dashboard_2027Q1.jpg`, `02_dashboard_2027Q2.jpg`, `03_dashboard_2027Q3.jpg`: dashboard per quarter.
- `04_quezon_province_and_lgus.jpg`: province view, trigger bar with Other, municipalities.
- `05_visualization_feature_contributions.jpg`, `06_about_window.jpg` (before the plain-language pass), `07_plain_language_dashboard.jpg` (after).
- `api_*.json`: production-env API responses (registry, provinces, explainability province and region, report data, overview, config).
- `model_to_ui_check.json`, `rendered_ranking_values.json`: end-to-end comparison.

## H. Remaining limitations

1. **Not deployed.** `origin/main` is `0239273d` (2026-10-22); the public Render API still serves FIRI v2. Nothing here changes that until `main` is updated (owner decision).
2. **Fixed (item 14):** strict start-up now refuses to run when E168 is not served. Without strict mode (development), the map engine still falls back to the Chapter I index by design.
3. **Basemap tiles.** `/basemap.pmtiles` is not on this machine (console: "Wrong magic number for PMTiles archive"). Province and municipal shapes and colours still render. It has to be built or downloaded separately (`docs/basemap.md`).
4. **Not opened in the browser:**
   - the downloaded PDF file (its text was verified at `/report/data`);
   - `/admin` (needs an admin login);
   - phone layout;
   - municipalities of provinces other than Quezon.
5. **Kept deliberately:** `NextQuarterOutlook` and `ProvincialOutlook` are not rendered; a test guards that.
6. **"Equal share" line** in the Visualization chart is a reference for five equal groups; with the Other bar it is only a visual guide.
7. **`/config` model fields** (`modelPerformance`, `servingModel`) still describe FIRI v2; the PDF report code depends on that structure, and the frontend does not display them (item 11).

## I. Deployment recommendation

**Ready to deploy once the owner approves updating `main`.** The blocking item (silent fallback) is fixed, and the branch is committed and pushed.
- **To deploy:** fast-forward `main` to `aiPHeed/e158-thesis-model` and push, so Render and Vercel rebuild. **Only with the owner's explicit approval.**
- **After deploying:** check that the live start-up message names `e168-lgbm-1.0` and that `/api/v1/provinces?quarter=2027-Q1` returns the five values in §D.
- **Also needed:** provide `basemap.pmtiles` for the map background.
