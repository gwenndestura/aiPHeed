# AIPHEED v4: final report

**Tags:**
- VERIFIED: a command was run and its output is saved;
- INFERRED;
- NOT VERIFIED.

**Branch:** `impl/backend-completion`. Local only: nothing pushed, deployed, downloaded or requested.

**Documents** (cross-linked):
- `TARGET_OPTIONS.md` (A);
- `EVALUATION_DESIGN.md` (B);
- `PREREGISTRATION.md` (C, hashed before fitting);
- `METHODOLOGY.md`;
- `MODEL_REPORT_V4.md` (D–E);
- `API.md`;
- `TEST_REPORT.md`;
- `DEVIATIONS.md`;
- earlier context in `../v2/` and `../v3/`.

## Three verdicts

### A. Software: YES

| Item | Evidence |
|---|---|
| v4 integrated additively. `/api/v1/hunger-forecast/v4` serves the rule-selected model from a hashed artifact. Inference never refits (a test patches `fit` to raise). Every record carries issue date, target, lead, score, interval, model hash, vintage, feature cutoff, evidence status, the computed reliability status, claim statuses and a limitation. | `tests/unit/test_v4_core.py` (VERIFIED) |
| Explanations come from the model: the exact sum is checked, including a forced DELTA-X path; there is a five-group summary; the hash equals the forecast hash | test (VERIFIED) |
| Geography: 142 LGUs and 5 provinces with explicit status; provincial and LGU estimates `null` | test (VERIFIED) |
| P0H4 stays labelled a price-pressure index | `test_v2_defects.py` (VERIFIED) |
| Full suite | TEST_REPORT §1 (VERIFIED) |
| Coverage 89.4 % (1313 / 1469 lines) of `app/forecasting/**`, the router and `paths.py`; v4 package 91.5 % (368 / 402) | `v4/results/coverage.txt` (VERIFIED) |
| E2E twice: identical. Artifact, store, API and seal reproduced. | `v4/results/v4_e2e_run.json` (VERIFIED) |
| Validation rerun gives byte-identical results | `git status` clean after rerun (VERIFIED) |
| Hashes re-verified at the end: protocol lock, v2 and v4 pre-registrations, tiers, snapshots, seal | TEST_REPORT §3 (VERIFIED) |

### B. Research

| Claim | DEVELOPMENT data (seen; non-confirmatory) | SEALED / FUTURE data |
|---|---|---|
| ≥ 75 % within the **frozen** tolerance at Lead 2 | **No.** 16/40 = 40.0 % [block 95 % CI 22.5–62.5] | **Not yet testable** (0 scorable rows; needs 10 quarters / 40 rows, about 2029-05) |
| ≥ 75 % within the **amended** tolerance (published margin; PROPOSED_NOT_ADOPTED) | **No.** 50.0 % [32.5–67.5] | **Not yet testable**, and not adopted without adviser sign-off |
| Beats every other model | **No.** Holm-adjusted p ≥ 0.38 against 6 of 7 baselines; it beats only CLIM. HFM-X (50 %) and SEAS-LLM (45 %) score higher. | **Not yet testable.** RIDGE-ALL also has no prospective forecast. |
| Lead 2 reliable (frozen N1–N7) | No (N2, N4 and N5 fail) | Not yet testable |
| Maximum reliable lead | None | Not yet testable |

**Bottom line** (INFERRED from VERIFIED evidence):
- The strongest legitimate system built from the data held is persistence, served with an honest interval.
- No exogenous indicator improved it under a pre-declared rule.
- The pre-declared hypotheses will be decided by the sealed SWS quarters, and only from about mid-2029.

### C. Data: what is still needed, and by when

1. **Unseen SWS quarters:**
   - 10 Lead-2 target quarters (2026-Q4 … 2029-Q1): first verdict about **2029-05** (±15 pp CI);
   - 22 quarters for ±10 pp: about **2032-05**;
   - each later quarter needs its forecast sealed before publication: run `python -m app.forecasting.v4.serving run <issue> <artifact>` at each quarter start; stored forecasts are write-once.
2. **A RIDGE-ALL prospective forecast** at the sealed issues, for the beats-all test to be complete. It must be produced before the 2026-Q4 SWS release (about 2027-01).
3. **Adviser sign-off,** if the amended tolerance is to be reported as an adopted metric (v3 draft template).
4. **SWS round documentation** (n, margin, design effect): it replaces 8 assumed margins, which is needed to define the amended tolerance purely from measurement properties.
5. **Optional:**
   - **Regional quarterly LFS:** the only untested leading-signal predictor; needs a download authorisation.
   - **CBMS 2024 FIES:** for any provincial or LGU claim; needs a formal, adviser-signed request.

   Exact steps: TARGET_OPTIONS §3.

## Files

**Created:**
- **Package:** `backend/app/forecasting/v4/` (`features`, `models`, `select`, `verdict`, `serving`).
- **Scripts:** `backend/scripts/v4_features.py`, `v4_validate.py`, `v4_seal.py`, `v4_score_sealed.py`, `v4_e2e.py`.
- **Tests:** `backend/tests/unit/test_v4_core.py`, `test_v4_preregistration.py`.
- **Data:** `backend/data/forecasting/v4_feature_snapshots.csv`, `artifacts/v4_2026-10-01.json`, `forecasts_v4/…json`.
- **Docs:** `docs/aipheed/v4/*` (including `tiers/`, `sealed/`, `results/`).

**Modified:**
- `app/api/v1/hunger_forecast.py`: v4 routes.
- `backend/scripts/v2_coverage.py`: output folder argument; v4 tests added.
- `.gitattributes`: v4 folders stored byte-for-byte.
- `docs/aipheed/PROGRESS.md`.

**Removed:** none.

## Reproduction (repository root, backend venv)

```
python -I backend/scripts/v4_validate.py
python -I backend/scripts/v4_score_sealed.py
python -I backend/scripts/v4_e2e.py
cd backend
python -m pytest -q -p no:cacheprovider
python -I scripts/v2_coverage.py v4
```

**Write-once steps:** `v4_features.py`, `v4_seal.py` and `python -m app.forecasting.v4.serving build|run` refuse to overwrite.

## Git state

The commit hash and `git status` are recorded in `../PROGRESS.md` (final entry). The 15 untracked paths that predate this work remain untouched.
