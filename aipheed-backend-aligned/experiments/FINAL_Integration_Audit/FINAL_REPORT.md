# aiPHeed final integration audit: approved frontend + complete backend, dynamic next-quarter forecasting

**Date:** 2026-10-15. **Branch:** `final-aipheed-integration`; the final commit is listed in §A.
**Approved frontend:** `origin/10-15-updated-flexible-ui` @ **`2c45882`** ("Fit the landing and account pages to phones", Princess Gwenn Destura, 2026-10-15 00:33 +08:00).
- Backup tag `approved-frontend-10-15-2c45882` (local).
- Local tracking branch `10-15-updated-flexible-ui`, unchanged.

**Nothing was pushed, merged into a shared branch or deployed.**

## Status in one table

| Category | Status | Evidence |
|---|---|---|
| **A. Technical system completion** | **TECHNICALLY COMPLETE (locally)**, with the open items in §D | Backend 300 passed / 18 skipped (listed superseded); approved frontend 30/30 + build; live E2E 13/13; E31 138 + 138; E32 16; E36 14; E37 8; E38 7; E35 25 + 4 xfail |
| **B. Scientific predictive validation** | **NOT DEMONSTRATED / INCONCLUSIVE.** Next-quarter accuracy 39/55 = 0.709 (< 75%). The current-quarter (lead-1) model reaches 53/65 = 0.815, but always-HIGH matches it. No significant gain over any thesis baseline. | §C |
| **C. External expert/user evaluation** | **PENDING EXTERNAL EVALUATION** (DA Region IV-A, ISO/IEC 25010) | not started |

## A. Branch and frontend preservation

**Construction**
1. Branch `final-aipheed-integration` was cut from `2c45882`.
2. `e36-lgbm-one-quarter-ahead` (E36/E37 backend and experiments) was merged in.
3. `frontend/` was then restored byte-for-byte from `2c45882`. 29 E31–E36 frontend-only files were removed by explicit path; all of them remain on `e36-lgbm-one-quarter-ahead`.
4. E38 was done on `e38-lead2-diagnosis-tuning` and fast-forwarded in.

**Frontend preservation**
- `git diff 2c45882 -- frontend` is **empty**. No frontend file was changed: every integration change is in the backend or its API contract.
- **The five triggers** (Market / Prices, Climate Stress, Fish Kill, Employment, OFW Remittance; keys `market`, `climate`, `fish_kill`, `employment`, `ofw_remittance`) are present and rendered by the approved components (screen check below; test `test_five_triggers_keep_their_identity…`).
- **Approved frontend checks:** vitest 30/30; `vite build` OK; `tsc` 6 errors, all in untouched approved files, identical to `2c45882`.
- **Visual check** (browser pane, approved UI against the integrated backend on a scratch DB):
  - the dashboard opens on **Q1 2027 (Forecast)**, with "Today" at Q4 2026;
  - five triggers are shown; province ranking 0.95 / 0.95 / 0.95 / 0.95 / 0.80;
  - every `/api/v1` request returned 200.
  - The only console errors come from the missing local `public/basemap.pmtiles` (gitignored, not present; §D).

**Backend conflicts resolved** (5 files):
- `main.py`: accounts plus scheduler imports.
- `security.py`: the approved text.
- `review.py`: the approved idempotent approval, using E31 statuses.
- `admin.py`: account and pipeline routes.
- `insights.py`: the approved note plus the served-model note.

## B. Backend integration

| Component | Result | Evidence |
|---|---|---|
| Account system of the approved branch (sign-up, sessions, passwords, demo account, migrations) | Merged; single alembic head `e5f6a7b8c9d0` | `test_api_accounts`, `test_api_sessions`, `test_passwords` |
| Review workflow | Stored as Figure 3.6.3 (Pending / Staged / Published / Archived). The API speaks the approved Admin page's **Staged / Approved / Rejected**. | `review.api_status`; E2E "approve idempotent, shows Approved" |
| **Merge defect fixed:** alert admin routes accepted the read-only demo account | `forbid_demo_writes` added | `test_every_admin_write_is_403_for_the_demo_account` |
| `ADMIN_EMAIL_DOMAIN` (approved) vs `ADMIN_EMAIL_DOMAINS` (E34) | Unified on `admin_email_domains` | sign-up domain tests |
| Served models | Current quarter: **aiPHeed-E36-LGBM** (lead 1, origin 2026-10-01). Next quarter (dashboard target): **aiPHeed-E38-LGBM-NQ** (lead 2, origin 2026-10-01, COMPACT × G5 + prior shift, threshold 0.5) | `data/e36/e36_record.json`; `data/e36/model/*` |
| Model loading and reproduction | Both booster files reproduce every served probability from the recorded feature values | `test_model_artifact_matches…`, `test_next_quarter_forecast_is_frozen_reproducible…` |
| SHAP | Exact TreeSHAP of the served model; additivity checked for every row | `test_shap_drivers_add_up_exactly…` |
| Five triggers | E20 convention: the group SHAP of the model inputs (only Market / Prices has inputs: D_last, Dnow, rice_rel). The other four have no input, so 0. The rest is `otherPct`. Measured news trigger shares come from the existing classifier. | `e31_engine.five_trigger_drivers` |
| LGU ranking | PSA 2021 SAE 141/142 + POPCEN 2024 142/142, computed on the target quarter; record = API = PDF | `test_on_15_october_2026_every_surface_targets_2027_q1` |
| Alerts | Staged only for the target quarter; public only after an administrator confirms | `test_alert_candidates_use_only_the_target_quarter`; E2E |
| Production DB | Never opened by tests: a global in-memory `get_db` override, verified by pointing `DATABASE_URL` at a non-existent path | `tests/conftest.py` |

## Dynamic next-quarter target

**The function:** `backend/app/quarterly/target.py::forecast_target(now=None)`. It runs on Asia/Manila time, takes a controllable clock (`now` or `AIPHEED_NOW`), and nothing is hard-coded.

| Viewed | Target | Tested |
|---|---|---|
| 2026-10-15 | **2027-Q1** | yes |
| 2027-01-15 / 2027-04-01 / 2027-07-20 / 2027-10-05 | 2027-Q2 / Q3 / Q4 / 2028-Q1 | yes |
| 31 Dec 23:59:59 PHT → 1 Jan 00:00 PHT; UTC 16:30 on 31 Dec | Q1 → Q2 rollover in Manila time | yes |

**How it is used**
- `/quarters` (`current`, `forecastTarget`), `/config` (`quarterRange.forecastTarget`), the default quarter of provinces, the map, municipalities, explanations, news and the PDF, and alert staging all derive from this one function.
- **Genuine, not relabelled:**
  - 2027-Q1 is the frozen E38 forecast (`E38_PROSPECTIVE_2027Q1.json`, sha `9549071c…`), issued at 2026-10-01 with information published before it.
  - When the target has no forecast (for example viewed in January 2027, target 2027-Q2), `/quarters` lists it as `unavailable` with its reason, and `/provinces?quarter=2027-Q2` returns 404 (test).
- **Issue rule:** one forecast per quarter, at the quarter-start origin, so there are no duplicate records on refresh. The 2026-10-14 SWS round enters at the 2027-01-01 origin.
- **Not automated:** generating the next target's forecast at 2027-01-01. It needs the inputs published by then (Q4 CPI, December SWS round, Q4 news) authorized, then `E38…/runner/e38_freeze.py` re-run at the new origin and the record rebuilt (§D).

## C. Scientific evaluation (actual SWS and PSA labels only)

**Labels** (`backend/data/inputs`; E31 vintage 2):

| Component | Source | Level | Schedule and release | Used as |
|---|---|---|---|---|
| H | SWS self-rated hunger, **Balance Luzon** (`sws_rounds.csv`: quarter, round, H, published date, definition_A) | Regional, one value for all five provinces | Quarterly rounds. Posting dates verified (for example the Sept 2026 round was posted 2026-10-14). 2025-Q2/Q3 rounds are supplementary (definition_A = False), so those quarters have no label. | Label component; lagged rounds also as predictors |
| D | PSA provincial food CPI YoY (OpenStat 0012M4ACP23) minus the five-province mean (`d_quarterly_panel.csv`) | Provincial | Monthly, released about a month after the reference month | Label component; lagged D and months 1–2 (Dnow) as predictors |
| Label | S1 = H + 2D (`s1_labels.csv`, 95 province-quarters, 19 quarters 2021-Q2..2026-Q3); HIGH if S1 > τ, the median S1 of quarters whose rounds were posted before the origin | Province-quarter | – | Target |
| DOST-FNRI FIES (NNS 2023, CALABARZON 19.1%) | `data/e22/nns_fies_verified.json` | Regional, annual, absolute prevalence | – | **Face validity only.** Not a label, not interchangeable with the relative quarterly label. |

**Missing label periods:** 2021-Q1, 2022-Q1, 2025-Q2, 2025-Q3. These are never counted.

**The label is relative** (trailing median), regionally dominated (70% of the variance is the shared H), and **not an absolute food-insecurity measure**.

**Independence from predictors:** predictors use only rounds, labels and prices published before the origin (tests in E36/E37/E38). The target quarter's own round and CPI are never available at the origin.

| Horizon | Dates (independent regional observations) | Rows | HIGH/LOW | Proposed model | Persistence | Best other thesis model | 75%? |
|---|---|---|---|---|---|---|---|
| Current quarter (lead 1; E36) | 13 | 65 | 53/12 | 53/65 = 0.815 (CI 0.738–0.892), balanced 0.822, Brier 0.154 | 57/65 = 0.877 | LR-government Brier 0.102 | Point yes; **not demonstrated** (CI) |
| **Next quarter, dashboard target (lead 2; E37 → E38)** | 11 | 55 | 49/6 | **39/55 = 0.709** (CI 0.582–0.836), balanced 0.544, LOW recall 2/6, Brier 0.200 | 44/55 = 0.800 | – | **No** |

**Six thesis baselines**
- Reported for both horizons: `E36…/docs/TABLES.md` and `E38…/FINAL_REPORT.md` §6.
- No paired difference is significant after Holm correction.
- Always-HIGH and climatology appear only as labelled diagnostics.

**Dependence:** uncertainty uses a date-cluster bootstrap and paired tests are per date. The five provinces of a date share one H.

**Reliability:** the evidence does not support a reliability claim.
- Even the best of 24 configurations chosen in hindsight reaches 0.727 at the next-quarter horizon (E38).
- What is needed: prospective outcomes (2026-Q4 lead 1, 2027-Q1 lead 2; frozen), more LOW quarters, and an adviser decision on the relative target (base-rate drift).

**Frozen records preserved and verified:**
- E25 seal and E31 Q3 (E31 tests);
- E32 `37e0d66b`, E35 `73a7ab1c`;
- E36 `9a9b1ebf` / `f64492ac`;
- E37 `7fa46aa9` / `881070f1`;
- E38 `9549071c` / `8169ecb1`.

## D. Tests and remaining defects

**Tests (final runs on this branch)**
- Backend 300 passed / 18 skipped. The 18 are the superseded tests listed with reasons in `backend/tests/conftest.py`, unchanged since E34.
- E31 138 + 138 (16 live skipped each).
- E32 16; E36 14; E37 8; E38 7.
- E35 25 passed + 4 strict xfail.
- Approved frontend vitest 30/30; build OK.
- **Live E2E 13/13** (`runner/e2e_live.py`, `runs/e2e_live_*.json`).

| Open item | Why it is open |
|---|---|
| E35-D1 ("High risk" band wording), D5 (panel note claims same-quarter PSA data), D6 (Landing FAQ claims) | The fixes exist on `e36-lgbm-one-quarter-ahead`, but the approved frontend keeps the original text. Changing wording needs your approval. |
| Five-trigger copy at 0% | The approved copy states a direction for every group (for example "Weather is hurting food supply" at 0%). Climate, Fish Kill, Employment and OFW have no input in the served model and almost no news data (E38: 192 of 2,820 titles; employment 1, OFW 0). **Decision needed:** keep it, or allow a functional "not used by the model" state. |
| Next target's forecast generation (2027-Q2 onward) not automated | Needs authorized inputs and a run of the E38 procedure at each new origin; the quarterly scheduler still runs PCF21 |
| `frontend/public/basemap.pmtiles` missing locally | Gitignored and not present; a re-download needs your approval. Province and LGU polygons render without it. |
| E35-D2 (SWS per-round n for PCF21) | PCF21 is not served |
| Lucena City poverty substitute of unverified source | A PSA HUC 2021 table is needed |
| Model files frozen with mixed line endings | Identity is kept by LF hash and prediction reproduction (`ARTIFACT_HASHES.json`); `.gitattributes` now stores all experiment and data artifacts byte-for-byte |
| Public deployment; DA ISO 25010 evaluation | Need your approval / external people |

## E. Chapter I objectives

| Objective | Implementation (technical) | Scientific / external |
|---|---|---|
| 1. Two-tier NLP → FSSI and patterns | Implemented (E31 store, R1.1, FSSI-v2, BERTopic descriptive); five triggers computed with the existing classifier | INCONCLUSIVE: title-only, sparse (7/120 sufficient); no measurable predictive value |
| 2. LightGBM metrics I–V, reliable horizon | TECHNICALLY COMPLETE: all metrics at leads 1 and 2, walk-forward, leakage-tested | NOT DEMONSTRATED: no horizon shown reliable |
| 3. LGU rankings from province forecasts, PSA poverty and density | TECHNICALLY COMPLETE: 141/142 PSA 2021 SAE, 142/142 POPCEN 2024, on the target quarter | Province forecasts not validated; rankings are relative positions |
| 4. Comparison with the baselines (six in SOP 3) | TECHNICALLY COMPLETE at both horizons | Negative result: no significant difference (H3 not rejected) |
| 5. Dashboard, alerts, ISO 25010, NNS face validity | Dashboard (approved UI) and alert confirmation workflow work locally (E2E) | PENDING EXTERNAL EVALUATION; not deployed |

## Files

**Key files changed or added on this branch (backend only):**
- `app/quarterly/target.py` (new);
- `app/ml/inference/e31_engine.py` (five triggers, labels);
- `app/services/dashboard.py` (target-aware default and timeline, `otherPct`);
- `app/api/v1/{dashboard,insights,admin,alerts,auth}.py`;
- `app/services/{review,security}.py`;
- `app/quarterly/alerts_e31.py`;
- `app/schemas/public.py`;
- `scripts/{build_record_e36,create_admin}.py`;
- `data/e36/*` (record, PDF, model copies);
- tests: `test_dynamic_target.py` (new), `test_e36_served_model.py`, `test_api_admin.py`, `test_api_dashboard.py`, `conftest.py`;
- `.gitattributes`.

**Audit artifacts:** `aipheed-backend-aligned/experiments/{E36…,E37…,E38…,FINAL_Integration_Audit}/`.

## How to run locally (no secrets in the repository)

1. Backend: `backend/venv/Scripts/python.exe -B aipheed-backend-aligned/experiments/E36_LightGBM_One_Quarter_Ahead/runner/serve_local.py`. It creates a scratch SQLite DB in the temp folder, runs the alembic migrations, sets a random `SECRET_KEY` and serves on port 8000.
2. Frontend: in `frontend/`, run `npm run dev` (port 8080). `VITE_API_BASE_URL=http://localhost:8000` comes from `frontend/.env`.
3. Admin account: run `scripts/create_admin.py --email <name>@calabarzon.da.gov.ph` with the same `DATABASE_URL` and a non-default `SECRET_KEY`. The password comes from a prompt or `AIPHEED_ADMIN_PASSWORD`.
4. Production needs: `SECRET_KEY`, `DATABASE_URL`, `CORS_ORIGINS`, `ADMIN_EMAIL_DOMAINS`, and optionally `DEMO_ADMIN_EMAIL` / `DEMO_ADMIN_PASSWORD`. **Never point a test at `backend/aipheed.db`.**
