# E34 working notes (facts as found; written so a compaction never needs a transcript read)

Started 2026-10-15 on branch e31-chapter1-completion (HEAD ea94b7e). Brief: audit master-prompt completion, fix gaps.
Master prompt text is NOT stored in the repo; requirements reconstructed from: this brief (Steps 1-4), E31 authorizations
(memory e31_authorizations: data to 2026-10-14; lead text robots-compliant; integrate into backend/ + frontend/ on a NEW
branch; no push/deploy without asking), and Chapter I (E25 thesis_source/CHAPTER_I_EXTRACTION_E23.md, verbatim).

## Environment damage found (from E33 git-clean incident, 2026-10-15 01:13)
- backend/venv: no pyvenv.cfg, Scripts/ only python.exe, 29 native site-packages dirs -> rebuilt from pinned
  backend/requirements.txt with Python 3.13.2 (runs/venv_restore.log).
- frontend/node_modules: 3 entries (@esbuild @rollup @swc) -> `npm ci` OK (377 entries). E31 dashboard_dev/node_modules is a
  JUNCTION to frontend/node_modules.
- corpus_geocoded.parquet: copies in aipheed-backend-aligned/data/processed and archive/2026-10-07 do NOT match the
  recorded hash ebce1199…; not restorable exactly.

## Integration state
- backend/ is clean vs git and is a DIFFERENT lineage (eee269b thesis-connected) from E31 backend_dev (aligned backend).
  86 paths differ. backend/ has only-in-main: thesis_predictor, thesis_explainer, forecaster, e20_forecast, plain_report,
  plain_text; data e20/e21/e22.
- E31 dashboard_dev base = frontend commit 1658d31 (131/139 identical files). Main frontend commits after base:
  702adb4 (lakes, component-city names, glossary) and 2f22552 (About title) touch AboutModal, GlossaryPanel,
  PhilippineMap, calabarzon-municities.json, + calabarzon-lakes.json.
- E33 promote_e31.py overlay was run then reverted (that revert caused the git clean). No E33 report.

## External sources
- psa.gov.ph is behind a Cloudflare JS challenge -> 2024 POPCEN Table B (CALABARZON, by city/mun) and 2021 municipal
  poverty SAE tables need a manual download by the researcher. POPCEN 2024 declared official by Proclamation 973 (11 Jul
  2025); CALABARZON 16,933,234 (PSA highlights page).
- GDELT DOC API: "Please limit requests" on every probe (also E28: 429 always) -> cross-source completeness BLOCKED.
- Google News robots.txt disallows /rss for Claude agents (E31) -> no new Google News requests in E34.
- NNS: backend/data/e22/nns_fies_verified.json: CALABARZON 2023 FIES 19.1% (95% CI 17.0-21.1), lowest region; Batangas
  2021 29.7, Cavite 2021 31.7; no single-year 2019 regional figure exists.

## Model audit (runner/e34_model_audit.py -> runs/e34_model_audit.json), lead 1, 50 rows, 10 dates, 46 HIGH / 4 LOW
- accuracy: ALWAYS_HIGH .92 (p>.75 .002); ENS .92; PCF21 .88 (Wilson .762-.944); B1 .90; PCFN .86 (Wilson .738-.931,
  p .045); LR .88; LGBM .86; P45 .822 (45 rows, p .17).
- balanced accuracy: PCFN .696, PCF21 .707, ENS .842, LR .821, B1 .832, ALWAYS_HIGH .5 (4 LOW rows -> unstable).
- nested online selection over E32 candidates: Brier .1114 (> persistence .100); with baselines in pool it picks
  ALWAYS_HIGH from 2024-Q3 on (Brier .1094).
- McNemar: no model differs from ALWAYS_HIGH or B1 (all p >= .25).
- power: to detect a .02 Brier gain vs B1 needs ~62-64 dates; vs B1p ~22-26; .05 gain ~10-11 dates.
- conclusion: another model fitted on the same 10 dates cannot be validated; only prospective dates can.

## Exposure log
- 2026-10-15 ~08:10-08:19 PHT: an in-process API probe (main backend/) and a first draft of
  test_e34_timeline_and_forecast_flag.py called /forecast/timeseries without a DB override, so the app ran a read-only
  SELECT on review_records (rejected province-quarters) in the production backend/aipheed.db. No row was printed or
  stored; the file is unchanged (mtime 2026-10-06 20:16). The test now uses an in-memory DB. The backend_dev run
  created an empty 0-byte backend_dev/aipheed.db; removed by explicit path. No SWS/CPI value was involved.

## Fixes made
- D0 backend_dev/scripts/create_admin.py: settings.ADMIN_EMAIL_DOMAIN -> admin_email_domains (crashed on rejection).
- D1 /quarters lists every quarter in range; gaps "unavailable" with data-derived reason (2025-Q2/Q3 supplementary SWS;
  2026-Q4 in the forecast view -> nowcast view). Schema Quarter.reason restored.
- D2 isForecast on /forecast and /forecast/timeseries follows the row mode (2026-Q4, 2027-Q1 true).
- psutil reinstalled (remnant namespace dir shadowed it; not in the pinned freeze).
