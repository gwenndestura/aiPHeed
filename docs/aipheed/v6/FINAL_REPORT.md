# AIPHEED v6: final report

**Tags:** VERIFIED (command run, output saved) / INFERRED / NOT VERIFIED.

**Branch:** `impl/backend-completion`. Nothing was pushed, deployed, downloaded or requested. No SWS web page was opened (owner rule protecting sealed quarters). The frozen protocol and the served dashboard model are unchanged.

**Documents:** `CONSTRUCT.md`, `DATA_AUDIT.md`, `FEASIBILITY.md`, `METHOD_SOURCES.md` (citations: `results/citation_log.md`), `PREREGISTRATION.md`, `DEVIATIONS.md`, `MODEL_REPORT_V6.md`, `DATA_REQUESTS.md`, `API.md`, `TEST_REPORT.md`, `PROGRESS.md`.

## Verdicts

### A. Software: YES

| Item | Evidence (VERIFIED) |
|---|---|
| Additive routes `/api/v1/hunger-forecast/v6`; approved artifact only; never retrains; fails loudly; full provenance, computed status, limitation string | `test_v6_core.py` |
| Explanations sum to the output, with five groups shown; TreeSHAP path tested | `test_v6_core.py` |
| 142 LGUs with explicit status; provincial and LGU values `null` | `test_v6_core.py` |
| Full suite: **1350 passed, 0 failed, 18 skipped** (pre-existing) | `results/final_tests_v6.txt` |
| Coverage 90.1 %; v6 package 92.8 % | `results/coverage.txt` |
| Mutation check 6 of 6 killed, after fixing a weak test it exposed | `results/mutation_check.txt`, TEST_REPORT §4 |
| E2E twice, byte-identical; validation rerun byte-identical | `results/v6_e2e_run.json` |
| Data audit from source: Gate 1 passed | `DATA_AUDIT.md` |

**One process incident:** my first mutation check edited shared source files for about 3.5 minutes while another session was using this worktree. Files were restored, and that session reports its rerun was byte-identical (TEST_REPORT §4).

### B. Research

**Per objective, Lead 2, V6 (= persistence, selected by the pre-registered rule at all 22 issues):**

| Objective | DEVELOPMENT (seen; non-confirmatory) | CONFIRMATORY (sealed / future) |
|---|---|---|
| ≥ 75 % within the **frozen** tolerance | **No:** 40.0 % [block 95 % CI 22.5–62.5] | **Not yet testable** (0 of 336 rows; first possible about 2029-05) |
| ≥ 75 % within the **proposed** published-margin tolerance (not adopted) | **No:** 50.0 % [32.5–67.5] | **Not yet testable,** and needs adviser sign-off |
| Beats all 8 baselines | **No:** Holm p ≥ 0.44 against 7 of 8; beats only the long-run mean. HFM-X 50 % and SEAS-LLM 45 % are higher, not significantly. | **Not yet testable.** All 8 baselines are now sealed at the same cutoff. |
| Lead 2 reliable (frozen N1–N7) | **No** (N2, N4, N5 fail) | Not yet testable |
| Maximum reliable lead | **None** | Not yet testable |
| LightGBM improves on persistence | **No:** 30.0 % [15.0–42.5], MAE 7.50 vs 5.98; not selected at any issue; largest train-to-outer gap. It had a model on only 24 of 40 rows and never forecast the 2024 surge. | Sealed for scoring; not yet testable |
| Provincial / LGU food-insecurity forecast | **Not supported:** no measurement exists at that resolution and frequency (`CONSTRUCT.md`) | Not testable without CBMS or similar data |

**Per route, Lead-2 oracle** (all data / calm period), with the filter requiring ≥ 0.85 on both (`FEASIBILITY.md`):

| Route | Oracle | Decision |
|---|---|---|
| R1 frozen | 0.43 / 0.60 | ELIMINATED |
| R2 1.645 × published SE | 0.51 / 0.70 | ELIMINATED |
| R3 published margin | 0.59 / 0.78 | ELIMINATED; best Lead-2 route |
| R4 one-quarter nowcast, published margin | 0.81 / 0.93 (h = 1, not Lead 2) | ELIMINATED by 0.04 on all data; closest of all |
| R5 latent target | 0.38 / 0.51 | ELIMINATED |
| R6 semiannual mean | 0.32 / 0.48 | ELIMINATED |
| R7 national mean | 0.28 / 0.52 | ELIMINATED |
| R8 interval overlap | — | ELIMINATED on validity (gameable) |
| R9 bands, R10 direction | 0.83, 0.80 | ELIMINATED on validity (saturated labels, base rates) |

**Limits of this evidence** (INFERRED):
- The oracle assumes a random-walk true level, with q estimated on the data themselves.
- A pre-registered control did not behave as stated (`DEVIATIONS.md` #3). Exploratory checks found no sign of leakage, but this explanation was not pre-registered.
- Conclusions rest on 10 target quarters and one large level shift.

### C. Data and time still needed

| Need | When | Why |
|---|---|---|
| **10 unseen Lead-2 target quarters** | About **2029-05** if SWS fields every quarter (±15 pp CI); 22 quarters about **2032-05** (±10 pp) | Nothing can be confirmed before this |
| **A new sealed forecast each quarter** | Each quarter start, beginning **2027-01-01** | The current seals cover only 2026-Q4 … 2027-Q3 (see below) |
| A leading indicator explaining about 85 % of 3-quarter change variance | Unknown; regional LFS is the only untested candidate, with a small gain expected | The only route to 75 % at Lead 2 under the oracle analysis |
| SWS documentation (8 margins, design effects, 1 round) | Any time; `DATA_REQUESTS.md` letter A | Settles the tolerance question without using outcomes |
| CBMS 2024 FIES | Formal request; letter B | Any provincial or LGU claim |
| Adviser decisions | Yours | Whether to amend the tolerance or the objective; the draft is in `../v3/PROTOCOL_AMENDMENT_DRAFT.md` |

**Keeping the confirmation test alive (not automated):**
- `v6_seal.py`, `v6_seal_baselines.py` and `v4_seal.py` are write-once for their current files. Later issues need new seal files, and the scorer needs to read them.
- The predictor snapshots (`v4_feature_snapshots.csv`) stop at 2026-10-01, and `v6_seal.py` refuses to seal without them.
- **Without this work, the test stops at 2027-Q3 with only 2 Lead-2 quarters.** This is the most important remaining engineering task.

## Most likely route to a real, defensible 75 %

**R4: a one-quarter-ahead nowcast scored against SWS's published margin of error.**

**Why:**
- It is the only route whose ceiling clears 75 % in both regimes (0.81 / 0.93). v3 reported 0.83 for the same route on consecutive-quarter pairs; this report's 0.81 uses all quarter rows.
- Simple persistence reached 0.74 on development data (v3): close, but below 75 %, and already seen.
- Its tolerance comes from SWS's own published precision, not from results.

**What it costs and needs:**
- It answers a one-quarter objective, **not Lead 2**.
- It failed the 0.85 filter you set, by 0.04 on all data.
- It requires adviser sign-off and a change to the stated objective.
- It must still be confirmed on unseen quarters. It is a route to test, **not an achieved result**.

**For Lead 2 as written, no legitimate route exists with the data held.**

## Files

**Created:**
- **Package:** `backend/app/forecasting/v6/` (`lgbm`, `select`, `serving`).
- **Scripts:** `backend/scripts/v6_data_audit.py`, `v6_feasibility.py`, `v6_seal_baselines.py`, `v6_validate.py`, `v6_controls.py`, `v6_seal.py`, `v6_score_sealed.py`, `v6_e2e.py`, `v6_mutation_check.py`.
- **Tests:** `backend/tests/unit/test_v6_core.py`, `test_v6_preregistration.py`.
- **Data:** `backend/data/forecasting/artifacts/v6_2026-10-01.json`, `forecasts_v6/…json`.
- **Docs:** `docs/aipheed/v6/*`.

**Modified:**
- `backend/app/api/v1/hunger_forecast.py`: v6 routes.
- `backend/scripts/v2_coverage.py`: v6 tests; excludes `v9`.
- `.gitattributes`.

**Removed:** none.

## Reproduction (repository root, backend venv)

```
python -I backend/scripts/v6_data_audit.py
python -I backend/scripts/v6_feasibility.py
python -I backend/scripts/v6_validate.py
python -I backend/scripts/v6_controls.py
python -I backend/scripts/v6_score_sealed.py
python -I backend/scripts/v6_e2e.py
cd backend
python -m pytest -q -p no:cacheprovider
python -I scripts/v2_coverage.py v6
python -I scripts/v6_mutation_check.py
```

**Write-once steps:** `v6_seal.py`, `v6_seal_baselines.py` and `python -m app.forecasting.v6.serving build|run` refuse to overwrite.

## Git state

The final commit and `git status` are in `PROGRESS.md`. A separate v9/v10 session commits to this branch in the same worktree, so its files may appear in `git status`.
