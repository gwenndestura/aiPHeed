# Deep Test Results

- **Branch:** `aiPHeed/final-model-completion-20261113`
- **Date:** 14 November 2026
- **Environment:** local, Windows 11. Backend venv `C:\Users\admin\aipheed\backend\venv` (Python 3.13). API preview on 8975, web preview on 8097. Served issue 2026-Q4.

## Totals

| Suite | Command | Result |
|---|---|---|
| Backend, all (`tests/unit` + `tests/integration`) | `cd backend; python -m pytest tests -q -p no:cacheprovider` | **1698 passed, 26 failed, 32 skipped** (9 min 42 s), *before* the demo-route fix below |
| Backend after the fix (accounts integration + FINAL) | `python -m pytest tests/integration/test_api_accounts.py tests/unit/test_final_realtime.py -q` | **107 passed, 0 failed** |
| FINAL real-time, history, reports, audit regressions | `python -m pytest tests/unit/test_final_realtime.py -q` | **38 passed** |
| Frontend (Vitest) | `cd frontend; npx vitest run` | **101 passed** (20 files) |
| Frontend types | `npx tsc --noEmit -p .` | clean |
| End-to-end data trace | `cd backend; PYTHONPATH=. python ../research_notes/audit_20261114/trace_end_to_end.py` | **34 / 34 checks pass** (`trace_results.json`) |
| Browser walk-through | built-in browser on the live preview | see §3 |

### The 26 backend failures

- **22 pre-existing unit failures, none touching FINAL.** They match the categories and count recorded before this work (REALTIME report §10; reproduced then on clean commit `22b8655b`):
  - protocol-lock hash checks: E137, E138, E139, E140, E141, E142, E143, E144 and HFIAS;
  - "production untouched" checks: E125, E128, E129, E130, E131;
  - E144 data and issue checks (4);
  - `test_e168_regenerate::test_outlook_reports_origin_and_threshold` (expects the old 2026-10-01 E168 cut-off);
  - FI9n news pipeline;
  - FI9x news cut-off;
  - `test_v2_paths` (two working directories).
- **2 environment-dependent integration checks:** `test_e119r2_framework`, `test_e120_firi_design`. They assert that the working tree has no uncommitted production-code changes, so they fail while the audit's edits are uncommitted. Re-run after the commit: see §4.
- **1 environment check:** `test_corrected_pipeline::test_raw_inputs_unchanged` needs a git-ignored NOAA IBTrACS file under `aipheed-backend-aligned/…/raw/`, which is not in this worktree.
- **1 real defect caused by this work, fixed:** `test_api_accounts::TestDemoAccount::test_every_admin_write_is_403_for_the_demo_account`. `POST /admin/forecast-outcomes` gave the read-only demo account 422 instead of 403. Fixed by adding the admin router's guards to the route; it now passes.

## 1. Results by category

| Category | Test case | Expected | Actual | Result | Evidence | Corrective action |
|---|---|---|---|---|---|---|
| ML integrity | Frozen artifact sha = issue manifest | equal | `e1f8675f…` both | PASS | trace | — |
| ML integrity | One fit per seed × served lead | 10 fits | 10 | PASS | trace | — |
| ML integrity | Re-predict the 2026-Q4 issue from the frozen model | identical | Δ share 0.0000; Δ P(HIGH) 0.000000 | PASS | trace | — |
| ML integrity | Training-row change stops an issue | `RetrainingRequired` | raised | PASS | `test_new_survey_round_stops_the_issue` | — |
| Data timing | An issue uses only figures online before its cut-off | refused otherwise | **2026-Q4 used Oct CPI and Sep LFS (published by 8 Nov)** | FAIL → guarded | `live_data` first-seen 2026-11-08; `check_information_rule` | Guard, cycle fix, disclosure (C1). Issue not rewritten (owner decision R1). |
| Data timing | Late inputs could change a class | no | ≤ 1.9 points; all LOW | PASS | audit §4 | — |
| Data timing | Harvest window shown = window used | equal | was Oct 2025–Sep 2026 vs Q3 2025–Q2 2026 | FAIL → fixed | `test_harvest_period_shown_is_the_one_the_inputs_used` | Display uses the inputs' 45-day rule |
| Issue rules | Leads ≤ validated max (2) | 1–2 | 1–2 | PASS | trace | — |
| Issue rules | Five CALABARZON provinces per quarter | 5 | 5 | PASS | trace | — |
| Issue rules | Class HIGH iff share ≥ 50% | all rows | all rows | PASS | trace | — |
| Issue rules | Cut-off = 1st of 2nd month, PHT | 2026-11-01 | 2026-11-01 | PASS | trace | — |
| History | Ledger hash chain | intact | intact (10 records) | PASS | trace | — |
| History | Ledger = issue rows | equal | equal | PASS | trace | — |
| History | No overwrite / tamper detected / outcome needs a hash | refused / detected | as expected | PASS | `test_history_*`, `test_tampering_is_detected`, `test_outcome_association_and_evaluation` | — |
| Database | Single Alembic head | 1 | `f6a7b8c9d0e1` | PASS | head scan | — |
| Database | Mirror inserts once, never overwrites | yes | yes | PASS | `test_database_mirror_inserts_once_and_never_overwrites` | — |
| API | Outlook = issue rows (10) | equal | equal | PASS | trace | — |
| API | `/provinces` riskScore and riskLevel = issue (Q1, Q2) | equal | equal | PASS | trace | — |
| API | Region value = mean of 5 shares (Q1, Q2) | 0.2452 / 0.2432 | 0.2452 / 0.2432 | PASS | trace | — |
| API | Timeseries = issue share | 0.268 / 0.266 | 0.268 / 0.266 | PASS | trace | — |
| API | `/forecast-period` names the served issue | 2026-Q4 | 2026-Q4 | PASS | trace | — |
| API | `/explainability` = `/final/shap` groups | equal | equal | PASS | `test_visualization_explanation_and_pdf_match_the_dashboard` | (fixed `8986e840`) |
| API | News count = stories read | 307 | 307 | PASS | `test_news_panel_lists_every_story_the_served_issue_read` | (fixed `579eb041`) |
| API | `/final/risk/rows` horizon note is FINAL's | Lead 3 reason | was Setup H "Lead 18" | FAIL → fixed | `test_rows_endpoint_horizon_note_is_finals_own` | patched `HS.horizon` |
| Towns | 142 towns, 5 provinces | 142 | 142 | PASS | trace | — |
| Towns | Each town carries its own province's share | yes | yes | PASS | trace | — |
| Towns | Vulnerability recomputed from displayed inputs | ≈ served | **0.131 off (Lucena)** | FAIL → fixed | trace | Panel shows the value the rank used |
| Towns | Priority = share × vulnerability | ≤ 1e-4 | 5e-5 | PASS | trace | — |
| Towns | Higher priority never ranked lower | yes | yes | PASS | trace | — |
| PDFs | PDF population = dashboard | 2,260,669 | was 1,980,338 | FAIL → fixed | `test_pdf_population_matches_the_dashboard` | — |
| PDFs | Disclosure in both PDFs, outlook, history | present | present | PASS | `test_issue_disclosure_reaches_every_surface` | — |
| Scheduler | Quarter transitions in PHT (Q4→Q1 across the year, Q1→Q2, Q2→Q3, Q3→Q4, issue day) | correct issue and targets | correct | PASS | `test_quarter_transitions` (8 cases) | — |
| Scheduler | One issue per quarter; repeat run up to date; failed run keeps the last issue; concurrent run skipped | yes | yes | PASS | `test_cycle_*`, `test_failed_run_*`, `test_concurrent_run_is_skipped` | — |
| Scheduler | Cycle never carries a later published-by date | dropped | dropped | PASS | `test_the_cycle_never_carries_a_later_published_by_date` | new guard |
| Security | Cron endpoint without / with a wrong token | 401 | 401 / 401 | PASS | curl | — |
| Security | Admin endpoints without login | 401 | 401 | PASS | curl | — |
| Security | Demo account writes | 403 | outcomes route gave 422 | FAIL → fixed | `test_every_admin_write_is_403_for_the_demo_account` | admin guards on the route |
| Security | Committed secrets | placeholders only | placeholders only; signing refused on default key | PASS | grep, `security._assert_signable` | — |
| Performance | 200 requests, 20 concurrent | all 200, stable | all 200, identical; p50 0.42–0.92 s, max 1.28 s | PASS | load script | — |

## 2. Frontend tests added or changed

| Test | What it guards |
|---|---|
| `e168ModelToUi`: "the ranking shows the SELECTED quarter's values" | H1: Q2 list showed Q1 shares |
| `e168ModelToUi`: "top five API groups … Poverty only when the API lists it" | Owner rule: Poverty and Vulnerability shown only when used |
| `driverWording`: glossary risk wording | The glossary describes a share in %, not a 0–1 probability |

## 3. Browser walk-through (actual backend, no mocks)

| Page / action | Expected | Observed | Result |
|---|---|---|---|
| Landing | no raw input names; anchors work | none; `#methodology #about #accuracy #disclaimer #faq` exist | PASS |
| Dashboard, Q1 2027 | region 25%; list 26.8 / 24.6 / 24.3 / 23.7 / 23.2; 307 news; disclosure | as expected | PASS |
| Province (Quezon) | 26.8%; LIMITED_SIGNAL; 244 stories; groups 41 / 38 / 12 / 2 / 2 + Other 5 | as expected | PASS |
| Town (Lucena, via search) | rank 5 of 41; priority 18.5%; poverty 10% | as expected (was "16.8% substitute") | PASS after fix |
| Switch to Q2 2027 | region 24%; list 26.6 / 24.4 / 24.1 / 23.5 / 23 | list showed Q1 before the fix; correct after | PASS after fix |
| Forecast history | 10 forecasts; disclosure under Q4 2026; "awaiting outcome" | as expected | PASS |
| About & Methodology | no "probability" for the map value; leads 1–2 reliable | corrected | PASS after fix |
| Data page | "Food insecurity risk", "Local news reports" | was "Chance of high risk" | PASS after fix |
| Visualization, both tabs | same values and groups as the dashboard | as expected | PASS |
| `/admin` while logged out | redirect to login | `/login` | PASS |
| Phone width 375 px (landing, dashboard, data, visualization) | no horizontal scroll | scrollWidth = 375 | PASS |
| Network | no failed API call | all 200 (logged-out `auth/refresh` aborted on navigation, 204) | PASS |
| Console | no app errors | only the missing local base-map tile file (preview environment) | PASS |

## 4. Re-runs after the commit

See `REMAINING_ISSUES.md` for anything still open. The two working-tree checks (`test_e119r2_framework`, `test_e120_firi_design`) are re-run after the commit; the result is in the commit report.
