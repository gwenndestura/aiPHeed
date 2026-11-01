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

## Resume here (next session)
1. **Write `backend/scripts/v6_validate.py`.** Pattern it on `v4_validate.py`. Steps:
   - walk-forward with `S6.walk_forward`;
   - selection with `S6.select`;
   - conformal intervals;
   - outer table with baselines `TREND-D`, `CLIM`, `RIDGE-ALL`, `HFM-X`, `SEAS-LLM` (E136), `V2` (v2 outer), `V4` (v4 devtest);
   - Holm over 8, plus secondary DM-HLN;
   - N1–N7;
   - leave-one-area-out (`exclude_area`);
   - window sensitivity (`start_issue`);
   - shuffle and future-shift controls;
   - train / inner / outer MAE;
   - write `v6/results/v6_verdict.json`.
2. **`v6_seal.py`:** V6 + candidates at 2026-07-01 / 2026-10-01 → `v6/sealed/V6_PROSPECTIVE_SEAL.csv` (hash in a test). Then `v6_score_sealed.py` (8 baselines, incl. `V6_BASELINE_SEAL.csv`).
3. **Stage 7:** v6 serving with the booster string in the artifact, TreeSHAP explanation summing to the score, `/api/v1/hunger-forecast/v6` routes, `tests/unit/test_v6_core.py`, coverage (`v2_coverage.py v6` + v6 tests), E2E twice, full suite.
4. **Docs:** `MODEL_REPORT_V6.md`, `DATA_REQUESTS.md` (draft letters: SWS documentation, regional LFS, CBMS FIES, FNRI), `API.md`, `TEST_REPORT.md`, `FINAL_REPORT.md`. Re-verify the lock and pre-registration hashes at the end.
