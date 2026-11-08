# E108 Deliverable G: reproducibility and integration

## Files (from `aipheed-backend-aligned/experiments/E108_Best_Defensible_Forecasting/`)

| Kind | Path |
|---|---|
| Protocol (hash-frozen before scoring) | `PROTOCOL.md`; `runner/PROTOCOL_SHA256.txt` = `fc3e42f97d814b24916bcb5d36e10cb4c1da1abbbbe270ff820c0ae7d93f6e01`; `runner/PROTOCOL_FROZEN_AT.txt` = 2026-10-25T03:18:38Z |
| E107 diagnosis (no model scored) | `runner/diagnose_e107.py` → `out/diagnosis.json` |
| Library: factored forecast, candidates, baselines, rule | `runner/e108_lib.py`. It imports E107's `e107_lib.py` (data, issue-date cuts, 13 columns) and `e107_model.py` (metrics) **unchanged**. |
| Runner | `runner/run_e108.py` (phases `score`, `diag`, `prospective`, `export`) |
| Predictions (every arm per row) | `out/predictions_T43_lead{1..4}.csv`; regional `out/regional_lead{1..4}.csv` |
| Results and decisions | `out/results.json`; per-origin configurations, inner log loss and SHAP in `out/origin_records.json` |
| Post-hoc rule on every arm | `out/rule_all_arms_posthoc.json` |
| Diagnostics | `out/diagnostics.json` (ablations, permutation, SHAP stability, S1, S2) |
| Sealed prospective forecasts | `out/sealed_prospective.csv`; `.sha256` = `fbc8bf911b1342e7f839cd4c27d35b037bbcd92953281067cffe7747650c325f`; `out/prospective_record.json` |
| Tests | `backend/tests/unit/test_e108.py` |
| Read-only API | `backend/app/api/v1/e108.py` → `/api/v1/e108/{evaluation,forecast,indicators}`; files in `backend/data/e108/` |

## Commands

```bash
cd aipheed-backend-aligned/experiments/E108_Best_Defensible_Forecasting/runner
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe diagnose_e107.py
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e108.py score
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e108.py diag
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e108.py prospective
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e108.py export
```

**Environment.** Python 3.13, LightGBM 4.6.0, SHAP 0.51.0, pandas 2.3.3, scikit-learn 1.8.0. LightGBM runs deterministic, row-wise, single-threaded, seed 108.

## Commit trail (branch `aiPHeed/e108-best-defensible-forecasting`)

| Commit | Content |
|---|---|
| `6529621` | Root-cause diagnosis and protocol, frozen before any E108 model was scored |
| `0040da6` | Pipeline, runner and tests. **The scoring run and the seal used this commit with a clean runner** (`results.json` → `run`, `prospective_record.json` → `git`). |
| `dcebc9e` | Results, diagnostics, seal, reports, read-only API |

**Order of work.** The diagnostics phase and the post-hoc rule table ran after scoring and changed no prediction. No model change was made after scoring.

**Preserved.** E107 is untouched: its protocol, addenda and sealed forecasts (`246700a8…`) were re-hashed and checked by `test_e108_seal_hash_matches_and_e107_seal_untouched`. The E107 seal was never opened for tuning.

## Verification (2026-10-25)

- **`backend/tests/unit/test_e108.py`: 50 passed.** Coverage:
  - completeness;
  - per-family future perturbation at feature **and** prediction level (8 data families × 4 leads);
  - backend as-of items (C1, N1, H1) × 4 leads, plus a negative control;
  - label availability;
  - T43 = hunger × price;
  - reproduction of stored predictions;
  - frozen protocol and clean runner;
  - both seals;
  - API.
- **Full backend suite: 671 passed, 18 skipped, 0 failed** (pytest, 3 min 2 s, at `dcebc9e`).
- **Frontend:** untouched. `git diff 4ed6b27 -- frontend` is empty.

## Deployment status

- **Local only, plus the pushed branch.** Nothing is merged into `main`, the branch Render deploys from.
- The production dashboard and API serve FIRI v2 / E56, unchanged.
- `/api/v1/e108/*` was verified through FastAPI's TestClient, not on a deployed server.
- The production default model was not changed.
