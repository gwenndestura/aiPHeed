# v6 progress (resumable)

**Start:** branch `impl/backend-completion` @ `9227010`. Protocol lock `8bae6962…dd0d3` verified at start (sha256sum, VERIFIED). Only the 15 pre-existing untracked paths.

**Standing constraint:** no SWS web searches or fetches (owner rule; sealed 2026-H2 protection). Literature citations are verified by web search and fetch; the log is `v6/results/citation_log.md`.

| Stage | Status | Commit |
|---|---|---|
| 0 Construct | DONE: Gate 0 PASSED with restricted claim (SWS area hunger; not provincial) | (this commit) |
| 1 Data audit | DONE: Gate 1 PASSED (SWS 88/88 = release tables; CPI, FIRI, FSSI, XLM-R reproduced; 3 limitations need external data) | (this commit) |
| 2 Feasibility | DONE: Gate 2 no route passes 0.85 at Lead 2 (best R3 0.59/0.78); closest overall R4 nowcast 0.81/0.93; v2 and v4 re-verified by re-execution | (this commit) |
| 3 Method sources | DONE: all methods sourced (verified); blocked k-fold CV and one unverified citation dropped | (this commit) |
| 5a Baseline seals | DONE: RIDGE-ALL (E132 setup) and HFM-X reproduced exactly vs E136 on 12 rows; sealed at 2026-07-01 / 2026-10-01, `V6_BASELINE_SEAL.csv` 495e6a93 | (this commit) |
| 5 Pre-registration | DONE: committed and hashed before any v6 fit | (this commit) |
| 4/6a LightGBM code | DONE (not yet evaluated): `app/forecasting/v6/{lgbm,select}.py` follow PREREGISTRATION §2 exactly. Smoke test at issue 2026-10-01: Lead 2, 56 training rows, best iteration 20, ONI admitted, predicted change about +4 pp. **No metric has been computed.** | (this commit) |
| 6 Validation | DONE (development): PERSIST selected at all 22 issues; LGBM-D Lead 2 30.0 %, MAE 7.50; V6 40.0 %; beats-all NO; shuffle control did not behave as stated (DEVIATIONS #3) | (this commit) |
| 6b Seal | DONE: V6_PROSPECTIVE_SEAL.csv 1309a556 (issues 2026-07-01, 2026-10-01); scorer ran once: 0 of 336 scorable; 8 baselines covered | (this commit) |
| 7a Serving | DONE: v6 artifact, inference, explanation (TreeSHAP path tested), store, /api/v1/hunger-forecast/v6 routes; E2E twice identical | (this commit) |
| 7b Tests and reports | DONE: 1350 passed / 0 failed / 18 skipped; coverage 90.1 %; mutation 6/6 in-process; E2E identical; lock and pre-registration hashes unchanged at the end; FINAL_REPORT written | (this commit) |
