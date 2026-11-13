# FINAL-ETMIX: backend, frontend and integration status (Parts 11–14)

## 1. Where FINAL-ETMIX is integrated, and where it is deliberately not

| Component | Status | Location |
|---|---|---|
| Model module | **Implemented, experimental** (`final-etmix-1.0-experimental`) | `C:\Users\admin\aipheed_hcw\backend\app\hcw\etmix.py` (branch `aiPHeed/setup-h-cw-dashboard`, uncommitted) |
| Live issue builder | **Implemented** | `app/hcw/etmix_serve.py` → `data/etmix/out/live.json`, `rows.csv`, `lgus.csv`, `contributor_registry.json`, `fits_*.pkl` |
| API | **Implemented, admin-only** (release gate `RESEARCH_ONLY`) | `app/api/v1/etmix.py`, mounted in `app/api/router.py` under `/api/v1/research/etmix/{status, outlook, contributors, alerts, lgus, contributor-registry}` |
| Tests | **Added: 6 tests** | `tests/unit/test_etmix.py` |
| Production model | **E196, unchanged** | `C:\Users\admin\aipheed_e196`: git status hash `8221a6c9…` and HEAD `6daf78e8` identical before and after this work |
| Public dashboard (aipheed.vercel.app) | **Unchanged.** Still serves E196 | — |
| Frontend code | **Unchanged** (approved design rule: no new UI elements) | — |

**Why ETMIX is not wired into production.**
- It has no independent validation (`FINAL_ETMIX_INDEPENDENT_VALIDATION_REPORT.md`).
- Replacing E196 needs your explicit approval (brief rules 13–14).
- It is therefore reachable only through the admin-only research API.

## 2. Backend verification

| Check | Result | Evidence |
|---|---|---|
| Correct model / artifact | `etmix.fit_predict` = FINAL fit (`app.hcw.final_engine`) predicted at g and s, averaged; 5 seeds | Reproduces the sealed-protocol research forecasts (p, p_g, p_s) to < 1e-9 (`test_etmix_reproduces_sealed_protocol_forecasts_and_explanations_are_exact`) |
| Preprocessing / feature schema | Rows built by the served pipeline (`app.hcw.serve._rows`: inputs published before the issue, anchors from released rounds) + MIND flags | Same code path as the H_cw live issue |
| Model version | `final-etmix-1.0-experimental`; per-seed FINAL configuration recorded | `live.json` → `configs` |
| Forecast lead / periods | Issue 2026-Q4; Lead 1 = 2027-Q1, Lead 2 = 2027-Q2 | `live.json` |
| Data cut-off | Data published before **2026-11-01**; news window 2026-08-01 … 2026-10-31 verified (178 national stories) | `cutoff_check` |
| Elapsed time | g = 22 (Batangas, Cavite), 30 (Quezon, Rizal), 34 (Laguna); s = 22 for all | `rows.csv` |
| HIGH/LOW | HIGH when p ≥ 0.50 | Tested |
| Probabilities | p = ½(p_g + p_s); both components reported | Tested (abs diff < 2e-4 after rounding) |
| Missing values | MIND flags; inputs missing at the issue listed per province (none at this issue) | `inputs_missing_at_issue` |
| Explanations | Exact TreeSHAP of the live fits; anchor + factors + time + trend + pooled context = forecast logit (check ≤ 1e-9) | `contrib_sum_check`; API additivity test |
| Contributor groups | Tiers read from the research registry, not hardcoded | `contributor_registry.json` (copied from the research folder) |
| Alerts | Candidate only when p ≥ 0.50 at Lead 1 (the model's own cut-off) | Tested; **none at this issue** |
| Municipal priorities | Approved formula (`rank_lgus`) on the served 142-LGU input (sha256 `82f21a9f…`) | 142 LGUs; max \|risk − p × vulnerability\| = 1e-16; 141 PSA SAE + 1 labelled substitute (Lucena) |
| Error handling | 503 when the artifact or registry is missing; 404 for a lead not in the issue; build **refuses** when the cut-off label does not match the panels | A first build was refused for exactly this reason (panels refreshed as of 2026-11-01); rebuilt with `AIPHEED_LIVE_ASOF=2026-11-01` |
| Access control | All six routes return **401 without an admin token** | `test_etmix_routes_require_admin_login` (real app) |
| Isolation | `etmix` is not referenced by the map engine, serving, main, dashboard services or the registry | `test_etmix_not_wired_into_public_serving_or_registry` |
| Future-data leakage | Same as-of rows as the served pipeline; existing as-of / leakage / reproduction suites pass | 26 tests (below) |

## 3. Live experimental forecast (issue 2026-Q4; not published)

| Province | 2027-Q1 p (class) | p under g / s | Anchor (latest survey level) | Own survey | Factor contributions (logit): food prices / agriculture | Average trend |
|---|---|---|---|---|---|---|
| Batangas | 0.001 (LOW) | 0.001 / 0.001 | 31.7 % | ENNS 2021 | −0.095 / −0.030 | −0.35 |
| Cavite | 0.003 (LOW) | 0.003 / 0.003 | 30.9 % | ENNS 2021 | +0.020 / +0.030 | −0.35 |
| Laguna | 0.002 (LOW) | 0.001 / 0.003 | 29.6 % | ENNS 2018 | +0.040 / −0.038 | −0.44 |
| Quezon | 0.008 (LOW) | 0.006 / 0.010 | 32.8 % | ENNS 2019 | +0.031 / −0.022 | −0.41 |
| Rizal | 0.005 (LOW) | 0.003 / 0.006 | 31.2 % | ENNS 2019 | +0.042 / −0.031 | −0.41 |

- **Lead 2 (2027-Q2):** all LOW, p 0.001–0.007.
- **Agreement:** E196 production also has all LOW (p 0.01–0.05).
- **Important finding for the dashboard.** The live fits (trained through ENNS 2021, like the 2021 Lead-1/2 fold fits) **did not select the regional-economy or poverty inputs**.
  - Their contributions to this issue are exactly zero, and the API says "not used by this issue's model".
  - The forecast is carried by the survey anchor, the average downward trend since the survey, food prices and agriculture, plus context inputs (climate, news, employment), which are pooled and shown without a direction.
  - Input importance is therefore **not stable across training periods**. The "core" label of the regional economy rests on the 2018/2019 folds.

## 4. Tests actually executed (2026-11-13)

| Suite | Result |
|---|---|
| `tests/unit/test_etmix.py` (new: elapsed-time rule; reproduction of sealed-protocol forecasts + exact explanations; research group map; isolation from production; API payloads vs artifact, alerts, LGU formula, additivity; admin-only access) | **6 passed** |
| `test_hcw_engine.py`, `test_hcw_final_engine.py`, `test_e151.py` (NLP pipeline), `test_e152.py` (as-of panel), `test_e175_target_scaling.py` | **26 passed** |
| Total in one run (aipheed_hcw backend, venv `aipheed\backend\venv`) | **32 passed, 0 failed** (4 min 06 s) |

**Not executed here:**
- the full aipheed_hcw backend suite (earlier sessions recorded known stale-expectation failures unrelated to ETMIX);
- the E196 frontend suite (101/101 recorded on 11-13 for the uncommitted E196 fixes).

The E196 worktree was not modified, so no E196 regression is possible from this work.

## 5. Frontend
- **Not changed, deliberately.**
  - The public dashboard serves E196.
  - The approved design forbids new UI elements.
  - ETMIX is not an approved replacement.
- **What switching would take (after approval):** the approved trigger card (`frontend/src/components/LeftPanel.tsx`, `RiskDriversCardBody`) renders whatever `triggers` the explainability endpoint returns, so the switch is a backend data change:
  1. register and promote ETMIX through the release gate;
  2. map the four factor groups to the `triggers` payload;
  3. put the regional label and the context notes into the existing text fields.
- **Icons:** the new keys would use the existing fallback icon. That is a visible change, so it needs your approval.

## 6. Deployment and DA validation (Part 14)

| Item | Status |
|---|---|
| Backend / frontend availability, API connectivity, environment | Production unchanged (E196 on Render + Vercel). ETMIX is not deployed |
| Model artifact availability | ETMIX artifacts exist locally only (`aipheed_hcw/backend/data/etmix/out`, uncommitted) |
| Data refresh | ETMIX uses the same monthly refreshed panels. Each issue must be built with `AIPHEED_LIVE_ASOF` set to the refresh date (enforced) |
| Security | ETMIX routes are admin-only (401 verified) |
| **ISO/IEC 25010 with DA Region IV-A** | 50 DA Region IV-A evaluators (owner-attested). The instrument (ISO/IEC 25010:2023, 9 characteristics) and tested scorer are in `aipheed_e196/docs/final/iso25010/` and `backend/app/iso25010/score.py`. **The response file `responses_template.csv` holds only its header row**, so per-characteristic results, overall findings and issues **cannot be reported from the repository**. Nothing is fabricated here. Entering the 50 responses and running the scorer is your action |
