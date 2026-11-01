# AIPHEED backend completion: progress log

**Evidence tags used throughout:**
- **VERIFIED:** a command was run and its output saved (path given).
- **INFERRED:** read from code or documents, not executed.
- **NOT VERIFIED.**

## Session 1 · 2026-11-01

**Setup**
- Repository `gwenndestura/aiPHeed`, worktree `C:\Users\admin\aipheed_final`.
- Started on branch `aiPHeed/corrected-data-pipeline` @ `2d9a2d9`; working branch `impl/backend-completion`, created from it.
- `git status` at start: 15 untracked paths that predate this work (CREDIBILITY_AUDIT/, E114 GDELT raw files, FINAL_SYSTEM_SELECTION annotation workbooks, docs/aiPHeed_Complete_System_Guide.docx, node_modules/). They are **left untouched** (not added, not stashed, not deleted).
- Rules: never push, deploy, delete experiment packages or overwrite artifacts; one commit per phase.

**Baseline tests:** `docs/aipheed/baseline_tests.txt` (VERIFIED; result below).
- **Result:** 1258 passed, 0 failed, 18 skipped, exit 0, in 214 s (VERIFIED, `docs/aipheed/baseline_tests.txt`).

## Phase 0 · Protocol lock: DONE

**`docs/aipheed/PROTOCOL_LOCK.md`** (VERIFIED). It holds 15 verbatim excerpts, each with its path, frozen commit and line range:
- tolerance: T1–T4;
- leads, issue policy and eligible rows: E1–E2;
- N1–N7, the reliable lead and the maximum reliable lead: R1–R2;
- CPI cutoff and YoY base: C1–C4;
- windows: W1–W3.

**Integrity checks:**
- `backend/scripts/build_protocol_lock.py` reads each excerpt with `git show <commit>:<path>` and refuses to build if the working tree differs from the frozen commit.
- The lock's SHA-256 is in `PROTOCOL_LOCK.sha256` (`8bae6962…`); `protocol_lock_manifest.json` holds per-excerpt hashes.
- `backend/tests/unit/test_protocol_lock.py` has 4 tests. They check the lock hash, every source excerpt and the frozen numbers in code (1.645, N1 at 10 quarters / 40 rows, N2 at 0.75). One test shows that an edited excerpt (1.645 → 2.000) is detected.
- `docs/aipheed/.gitattributes` is `* -text`, so a CRLF conversion cannot change the hash.

**Nothing was missing**: every requested value was found in the repository.

## Phase 1 · Audit: DONE

**Output: `docs/aipheed/AUDIT.md`**, with a data-flow diagram and 9 defects.

**Served model.**
- Deployment serves `AIPHEED_LEAD2_MODEL=thesis` with `AIPHEED_STRICT_MODEL=1`; the map shows the P0H4 Chapter I risk probability (`data/ch1_engine/rows.csv`).
- Its Lead-1 metrics reproduce exactly from the export: 70 rows, 14 quarters, Brier 0.1322, accuracy 0.8429 (VERIFIED, `docs/aipheed/served_model_reproduction.txt`).
- Its Leads 2–4 metrics cannot be reproduced from served artifacts (NOT VERIFIED).

**Fixed.**
- **D2 (High):** the 6 `joblib.load` sites now go through `app/forecasting/safe_load.py`, which checks a SHA-256 manifest and refuses files outside `models/`.
- `models/MODEL_MANIFEST.json` records the 3 existing artifacts; no artifact was modified. `backend/models/` is gitignored, so only the manifest is force-added; the artifacts stay local.
- Tests: `tests/unit/test_safe_load.py` (3, VERIFIED).

**Logged, not fixed** (they need owner approval or carry risk to the served system):
- D1: the served target is a composite probability;
- D3: the scikit-learn version of the artifact differs from the pinned version;
- D4: cwd-relative paths;
- D5: no single as-of selector in legacy paths;
- D6: API surface;
- D9: missing legacy artifact.

**Full suite after phase 1 edits (VERIFIED, `docs/aipheed/phase1_tests.txt`):** 1263 passed, 2 failed, 18 skipped.
- The 2 failures are `test_e119r2_framework::test_all_validation_checks_pass` and `test_e120_firi_design::test_e120_checks_pass`.
- Both are experiment self-checks that require `git status` to show no uncommitted changes under `backend/app`.
- **Classification: intended change** (the edits were uncommitted at run time). Re-checked after commit (phase 2 entry).

## Phases 2–4 · Data, as-of control, target gate, FIRI: DONE

**Output: `docs/aipheed/DATA_INVENTORY.md`.**

**New package: `backend/app/forecasting/`.**

| Module | Purpose |
|---|---|
| `evidence.py` | EvidenceStatus, DataState and ReliabilityStatus enums |
| `as_of.py` | The one selector, strictly before 00:00 PHT on the issue day |
| `validation.py` | Checks on SWS rounds and LGUs |
| `sws.py` | Target with binomial SE and the frozen tolerance |
| `models.py` | PERSIST, TREND-D, SEAS-LLM |
| `artifact.py` | Hashed JSON artifacts, write-once |
| `inference.py` | Forecasts from an artifact; never refits; fails loudly |
| `explain.py` | Exact additive explanation; trigger groups as context |
| `geography.py` | 142 LGUs and 5 provinces with explicit status |
| `store.py` | Write-once store keyed by (artifact hash, data vintage, issue date) |

**Supporting files:**
- Data copy `backend/data/forecasting/sws_area_rounds.csv` (identical to the E110 source).
- Artifact `backend/data/forecasting/artifacts/seas_llm_2026-10-01.json`.
- Stored forecast `backend/data/forecasting/forecasts/09ee23b09a0207c8_2026-08-24_2026-10-01.json`.
- Read-only router `app/api/v1/hunger_forecast.py`, registered additively.

**Exactness (VERIFIED by tests):**
- The target equals the E131 implementation.
- SEAS-LLM equals the E132 seal (to 1e-9) and the walk-forward. An ad-hoc run over all 272 P-DASH rows gave a maximum difference of 7e-15.

**Target gate decision.**
- Balance Luzon / SWS-area claims only. Provincial and LGU estimates are `null` / `AWAITING_GROUND_TRUTH`.
- The evidence-status enum existed before any model work.

**Tests:** `tests/unit/test_forecasting_core.py` (13). Leak injection demonstrated in `docs/aipheed/leak_injection_demo.txt`.

**Open issues:**
- Legacy feature paths are not rerouted through `as_of` (AUDIT D5).
- The NLP pipeline was not re-executed (NOT VERIFIED).

## Phases 5–6 · Model selection and reliability: DONE

**Inputs and outputs:**
- Rule `SELECTION_RULE.md`, committed before the first run (`c07324e`).
- Report `MODEL_REPORT.md` and `results/*.csv` (VERIFIED, `python -I backend/scripts/model_report.py`; seed 2026; SHA-256s in `run_config.json`).

**Selected by the rule: PERSIST.** No candidate beats it with a paired 95 % CI above 0:

| Candidate | Δ within vs PERSIST | 95 % CI |
|---|---|---|
| SEAS-LLM | +0.05 | [−0.10, +0.20] |
| HFM-X | +0.10 | [−0.125, +0.325] |

**Reliability:**
- **Maximum reliable lead: none.** No model passes N1–N7 at any lead.
- **Lead-2 blockers:** signal absent (best 20/40 within, 30 needed; correlation ≤ 0.25), target lag (h = 3), N5 instability, N1 too few quarters at Leads 3–4.

**Conflict for the owner.** The pre-declared backend rule selects PERSIST, while E134 Addendum 2 (owner-approved) makes SEAS-LLM the prospective primary. The new endpoint serves SEAS-LLM under that approval and shows the latest SWS value (= persistence) in every record. Not changed without approval.

**Test:** the served `reliability_status` is pinned to the mechanical verdict (`test_served_reliability_status_matches_mechanical_verdict`).

## Phases 7–8 · Inference, geography, explanations and API: DONE

**Phase 7** (built in phases 2–4; VERIFIED by `tests/unit/test_forecasting_core.py`).
- **Inference** loads only the hashed JSON artifact and checks its schema, hash, feature config and preprocessing version. It never refits (a test fails if `fit_seas` is called), validates ranges and fails loudly.
- **Each record** stores the provenance fields listed in API.md.
- **Geography:** 142 LGUs and 5 provinces with explicit status. Province codes equal the served dashboard's.
- **Explanations** are exact and additive (level + design effect). The trigger groups are listed separately as context.
- **Uncertainty:** Kalman 80 % interval. Development coverage at Lead 2 is 0.725 on 40 rows (MODEL_REPORT).

**Phase 8.**
- `docs/aipheed/API.md` and `results/api_audit.csv`: 106 routes; 85 GETs smoke-tested.
- **Fixed D10 (High):** two unhandled 500s on the legacy assessments routes, caused by a missing artifact, now return 503 with a JSON message.
- No secrets in bodies. All admin routes are guarded; the only unguarded writes are the public auth and feedback routes.

## Phases 9–12 · Tests, security and performance, E2E, documentation: DONE

**Phase 9:** 1280 passed, 0 failed, 18 skipped (pre-existing skips; VERIFIED, `final_tests.txt`). 22 new tests. Coverage **not measured** (no coverage tool in the virtual environment).

**Phase 10:** D2 and D10 fixed; secrets, timeouts and caching reviewed (`ARCHITECTURE.md`).

**Phase 11:** two E2E runs are byte-identical (VERIFIED, `results/e2e_run.json`).

**Phase 12:** METHODOLOGY, ARCHITECTURE, DATA_INVENTORY, MODEL_REPORT, API, TEST_REPORT and FINAL_REPORT written.

**Verdicts:**
- **A software:** YES.
- **B research:** NO. 75 % not met (best 50 %); Lead 2 not reliable; maximum reliable lead none.
- **C data:** unseen SWS quarters, a leading indicator of hunger change, and a provincial measurement.

**Awaiting the owner:**
1. PERSIST (rule-selected) or SEAS-LLM (Addendum 2) on the new endpoint.
2. D1, the served dashboard target.
3. D3, rebuilding the thesis pickle under the pinned scikit-learn.

**Final commit:** `9171949` on `impl/backend-completion`. `git status` after it: only the 15 untracked paths that predate this work (verified below).
