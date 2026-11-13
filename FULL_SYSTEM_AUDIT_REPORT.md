# Full System Audit Report

- **Branch:** `aiPHeed/final-model-completion-20261113`
- **Date:** 14 November 2026
- **Scope:** frontend, backend, ledger and database, API, FINAL model, data timing, scheduler, content, security, performance

**Verdict:** NOT declared complete. The integrated system is internally consistent after the corrections below. One critical data-timing finding (C1) affects the forecast already served. It is disclosed and guarded against, but the decision to re-issue belongs to the owner. FINAL is also not yet the registered production model. See `REMAINING_ISSUES.md`.

## 1. Architecture as actually executed

```
PSA / NASA POWER / NOAA / FNRI / news archives
  → data stage: app.e168.live_refresh (news, panels) + app.hcw.inputs        [app.final.cycle.data_stage]
  → frozen FINAL (data/final/model/frozen_final.pkl, 5 seeds × leads 1-2)    [app.final.issue.predict_issue]
  → issue folder data/final/issues/<Q>/ (rows, SHAP, live.json, news_used.json, manifest with sha256)
  → hash-chained ledger data/final/history/ledger.jsonl (+ insert-only DB mirror, Alembic f6a7b8c9d0e1)
  → serving layer app.final.serving (patches hcw_system / hcw.serve / dashboard services to the served issue)
  → /api/v1 routes (dashboard, insights, final, final_realtime, report)
  → React pages (dashboard, data, visualization, admin) via lib/queries.ts
```

- **Scheduling:**
  - in-app APScheduler FINAL daily job;
  - Windows task `backend/scripts/final_daily_cycle.ps1`;
  - GitHub Actions cron calling `POST /api/v1/internal/forecast-cycle` (Bearer token).
- **Legacy implementations:** E168, Setup H (`hcw_system`), CH1 (`map_engine`) and FI9/FI10 remain in the code. FINAL reaches the screen by patching the `hcw_system` interface (`app/final/serving.py`). Every value on screen was traced to FINAL (see `FRONTEND_BACKEND_ALIGNMENT_REPORT.md`). The legacy modules supplied stale text in four places, all corrected below.

## 2. Findings, root causes and corrections

| ID | Severity | Layer | Finding | Root cause | Correction | Regression test |
|---|---|---|---|---|---|---|
| **C1** | Critical | Data timing / ML | The served 2026-Q4 issue used **October 2026 CPI** and **September 2026 LFS**. Both were released after its 1 November cut-off; the forecast says "data published before 1 November". | I built the issue by hand (2026-11-13) on panels from the E168 monthly refresh. That refresh's rule counts a figure downloaded by its refresh day (8 Nov) as available at the cut-off (`e168/live_data.usable`, `state.json served_published_by`). The walk-forward evaluation used the strict rule. Automated cycles were already strict: they set `AIPHEED_LIVE_ASOF` without `AIPHEED_LIVE_PUBLISHED`. | (1) `issue.check_information_rule` refuses to build any issue whose published-by date is after its cut-off. (2) The cycle drops any stray `AIPHEED_LIVE_PUBLISHED`. (3) The issue is not rewritten (issues are immutable); a recorded disclosure in `serving.json → issue_notes` is shown in About this forecast, Forecast history, `/forecast-period`, the outlook and both PDFs. Impact bound: removing every affected input entirely moves each province by ≤ 1.9 points; all stay LOW (§4). | `test_an_issue_cannot_use_figures_published_after_its_cut_off`, `test_the_cycle_never_carries_a_later_published_by_date`, `test_issue_disclosure_reaches_every_surface` |
| H1 | High | Frontend | With **Q2 2027** selected, the province list showed **Q1** shares (Quezon 26.8% instead of 26.6%). | `ProvinceRankingCardBody` read Lead-1 outlook rows (`useShareRows()` with no quarter) instead of the selected quarter's `/provinces` values. | The list now uses the backend's per-quarter `riskScore`. | `e168ModelToUi.test.tsx`: "the ranking shows the SELECTED quarter's values" |
| H2 | High | Frontend | The Data page column "**Chance of high risk**" showed the forecast **share** (26.8%). The real chance of High is ≈1%. | Label from the E168 era (when the value was P(HIGH)). | Renamed "Food insecurity risk" in the table, phone cards, sort menu and CSV. The news column is now "Local news reports". | browser check; label strings |
| H4 | High | Security | The read-only demo account got **422** (its request body was validated) instead of **403** on `POST /admin/forecast-outcomes`. | The route was added on the public router, outside the admin router's blanket `forbid_demo_writes` guard. | The admin guards were added to the route. | `test_api_accounts::test_every_admin_write_is_403_for_the_demo_account` |
| H3 | High | Backend → frontend | The Visualization "Why is this at risk?" chart and its PDF showed Setup H's grouping ("Poverty and vulnerability 41%") next to FINAL's forecast. | `/explainability` was served by the legacy builder. | Served from FINAL's exact SHAP groups (`8986e840`). | `test_visualization_explanation_and_pdf_match_the_dashboard` |
| M1 | Medium | Backend | Lucena's town card showed a **16.8% province substitute**. The note said no city estimate exists, but the rank used PSA's **2021 City of Lucena figure (10%)**. | `municipality_summary` reads poverty from an older table; the ranking (`e145/lgu.BASE`) uses another. | The panel now shows the value and source the rank used, for all 142 towns. | `test_town_panel_shows_the_poverty_value_the_rank_used` |
| M2 | Medium | PDF | Quezon's PDF population was **1,980,338**; the dashboard and the 41 towns give **2,260,669**. | The PDF used the PSA province census row, which excludes the independent city of Lucena. | Both PDFs use the dashboard's population. | `test_pdf_population_matches_the_dashboard` |
| M3 | Medium | Backend | "About this forecast" said harvest **Oct 2025–Sep 2026**; the inputs used **Q3 2025–Q2 2026** (45-day rule). | The display used the E168 download rule; the inputs (`hcw.inputs`) use `_published_quarters` without it. | The display computes the window with the inputs' rule. | `test_harvest_period_shown_is_the_one_the_inputs_used` |
| M4 | Medium | Content | About & Methodology had six stale statements: map value as a "probability"; alert at regional "0.60"; "a stricter rule … holds to 4" (contradicted by "no lead passes in every round"); "a missing figure is left out" (FINAL fills it with the median and a flag); a source comment from Setup H; and an `/final/overview` sentence calling map values probabilities. | Text written for E168 / Setup H. | Corrected to FINAL's facts. | frontend suite; browser read |
| M5 | Medium | Content | Tours and tooltips said "risk probability" and "Each line is a forecast probability of HIGH". The Visualization tour named old tabs. | E168 wording. | Reworded to "food insecurity risk" / "forecast share" and the current tab names. | browser read |
| L1 | Low | API | `/final/risk/rows` explained the horizon with Setup H's "Lead 7 accuracy 74.0% … up to Lead 18". | `hcw_system.horizon` text was not patched. | Uses FINAL's own reason (precision/F1 below 75% from Lead 3). | `test_rows_endpoint_horizon_note_is_finals_own` |
| L2 | Low | API | Town texts (`riskLevelBasis`, `disaggregationLabel`) called the province value a "HIGH probability". | Setup H strings. | FINAL wording (forecast share). | covered in `test_town_panel…` |
| — | — | (earlier this session) | The news panel showed 49 instead of 307 stories; Poverty and Vulnerability was shown when not used. | Missing `news_used.json`; owner rule. | `579eb041`. | `test_news_panel_lists_every_story_the_served_issue_read` |

## 3. Machine-learning integrity

- **Artifact:** `frozen_final.pkl`, sha256 `e1f8675f…`, equal to the issue manifest. It holds 10 fits: seeds {168, 1, 2, 3, 4} × leads {1, 2}, matching `serving.json`.
- **Inference:** the frozen model reproduces all 10 stored forecasts exactly (Δ share 0.0000 points; Δ P(HIGH) 0.000000). It is not a static file, mock or fallback model. `RetrainingRequired` stops an issue if the training rows change (new survey round).
- **Inputs:** the live fit selects 23 inputs (top-25 \|Spearman\| screen plus ρ > 0.95 pruning). Missing values use median fill plus a flag (MIND); monotone constraints apply. Calibration and the HIGH threshold (share ≥ 50%) are as sealed.
- **Poverty and vulnerability:** they are candidate model inputs (`p_poverty`, `p_subsistence`, `p_poverty_gap`, `p_density`, `income_rel`, poverty news). The live screen did not select any of them. The locked study (`bb63c891`) found no poverty or vulnerability arm that replaces FINAL. They are therefore not shown as contributors, and they do rank towns. Shown only when used (owner rule).
- **Geographic resolution:**
  - GRDP is regional: "Regional Economy", "the same for all five provinces".
  - Unemployment is national.
  - CPI, harvests, rainfall and typhoons are provincial.
  - ONI is global and context only: not a selected input; shown as an El Niño note.
- **Leakage:** apart from C1, every input period ends before the cut-off under the strict rule:
  - rainfall Apr–Sep;
  - soil Jun–Aug;
  - local prices May–Jul;
  - harvest to Q2;
  - GRDP 2025 (published Apr 2026);
  - typhoons to October (IBTrACS, near-real-time);
  - news 1 Aug–31 Oct.
- **Leakage beyond C1:** no target or outcome information enters an issue. The 2021 labels are used only for training rounds before the issue.

## 4. C1 impact bound

Method: remove every affected input (`cpi_*`, `mi_cpi_food_accel`, `unemp_rate`) at its exact SHAP contribution. The table gives the share range across adding and subtracting \|Σ SHAP\|.

| Province | Q1 2027 share | Range without the late inputs |
|---|---|---|
| Batangas | 23.2% | 21.4–25.1% |
| Cavite | 24.3% | 24.0–24.7% |
| Laguna | 23.7% | 23.1–24.3% |
| Quezon | 26.8% | 26.3–27.3% |
| Rizal | 24.6% | 24.0–25.3% |

Q2 2027 is the same within 0.1 point. No class can change: the 50% line is more than 20 points away. An exact re-issue under the strict rule would need a strict panel rebuild. That was not run, because it would rewrite shared panel files and the served issue; it is the owner's decision (REMAINING_ISSUES R1).

## 5. Ledger and database

- **Ledger:** 10 records, hash chain intact, equal to the issue rows. Duplicate issue, overwrite and tamper cases are refused or detected (tests `test_history_refuses_to_overwrite…`, `test_tampering_is_detected`).
- **Outcomes:** records added only with a SHA-256 of the source and an authoriser.
- **Database:** Alembic has a single head (`f6a7b8c9d0e1`, 9 revisions). The insert-only mirror has unique (model, issue, target, province) records (`test_database_mirror_inserts_once_and_never_overwrites`).

## 6. Scheduler and automation

- **Clock:** Asia/Manila. Transitions are tested at Q4→Q1 across the year, Q1→Q2, Q2→Q3 (targets crossing the year), Q3→Q4, and on the issue day itself.
- **Duplicates:** one issue per quarter; a repeat run reports "up to date".
- **Concurrency and failure:** a concurrent run is skipped (lock file). A failed run keeps the last valid issue. A new survey round stops the issue for retraining. Annual sources are not fetched every quarter.
- **Staleness:** shown as not fresh.
- **Multi-instance limit:** the lock is a file. Two app instances on separate disks could both start a run. The ledger refuses a second record of the same key, so no duplicate record results (REMAINING_ISSUES L6).

## 7. Content and terminology

- **Labels:** the system is described as forecasting a share and risk class, "not a measured food-insecurity rate or an official statistic", on the landing page, About, Glossary, PDFs and town notes.
- **Terminology:** "probability" now appears only where P(HIGH) is meant (Forecast history "Chance of High"; the RATE/MIND explanation).
- **Raw inputs:** no raw FINAL input names appear on the landing page.
- **Freshness claims:** no real-time claim. Sources are labelled with their real frequencies and "updated quarterly".

## 8. Security and performance

- **Authentication:** unauthenticated calls to `POST /internal/forecast-cycle` (no token or a wrong token), `POST /admin/forecast-outcomes`, `/admin/review` and `/admin/accounts` all return 401. `/admin` redirects to the login.
- **Input validation:** a bad quarter or province returns 404. SQL-like search text is handled safely (200, no error).
- **Secrets:** only placeholders are committed (`changeme`, `your_gnews_api_key_here`). Token signing is refused while SECRET_KEY is the default. The frontend reads only `VITE_API_BASE_URL` and `VITE_BASEMAP_PMTILES_URL`.
- **Performance:** single endpoints answer in 5–240 ms. Under load (200 requests, 20 concurrent, one local worker) all returned 200 with identical bodies; p50 was 0.42–0.92 s and max 1.28 s.
- **Phone layout:** no horizontal overflow at 375 px on the landing, dashboard, Data and Visualization pages.
- **Console:** only errors from the local base-map tile file (no PMTiles file in this preview).
