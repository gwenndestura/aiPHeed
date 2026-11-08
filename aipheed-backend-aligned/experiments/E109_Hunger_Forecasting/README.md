# E109: forecasting experienced hunger (SWS Balance Luzon), Leads 1–4

**Branch:** `aiPHeed/e109-hunger-forecasting` (from E108 `b56d90e`). **Status:** evaluated; not served; production unchanged.

**Result.** The target is the actual hunger outcome (SWS Total Hunger, Balance Luzon, regional). No model, including LightGBM on all 12 indicators, beats the latest published reading. **No reliable lead time is established.**

| Deliverable | File |
|---|---|
| 1. Sources and target | `E109_SOURCE_AND_TARGET_AUDIT.md` (sources in `sources/SOURCES_LOG.md`) |
| 2. Data quality and leakage | `E109_DATA_QUALITY_AND_LEAKAGE_AUDIT.md` |
| 3. Method and model comparison | `E109_METHOD_AND_MODEL_COMPARISON.md` |
| 4. Lead-time reliability | `E109_LEAD_TIME_RELIABILITY_REPORT.md` |
| 5. Thesis objectives | `E109_THESIS_OBJECTIVE_ASSESSMENT.md` |
| 9. Final recommendation | `E109_FINAL_RECOMMENDATION.md` |
| Protocol | `PROTOCOL.md` (sha `3d794793…`), `ADDENDUM_1.md` (real-time vintage), hashes in `runner/` |
| Scripts | `runner/e109_lib.py`, `runner/run_e109.py` (`score`, `prospective`, `export`), `runner/score_prospective.py` |
| Tests | `backend/tests/unit/test_e109.py` |
| Outputs | `out/predictions_lead{1..4}.csv`, `out/results.json`, `out/sealed_prospective.csv` (sha `61bcc353…`), `out/prospective_record.json`, `out/prospective_scores.json` |
| Read-only API | `/api/v1/e109/{evaluation,forecast,lgu-status}` (`backend/data/e109/`) |

## Reproduce

```bash
cd aipheed-backend-aligned/experiments/E109_Hunger_Forecasting/runner
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e109.py score
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e109.py prospective
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e109.py export
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe score_prospective.py
```

**Order of work.**
- Scoring and the seal ran at commit `d220ad7` with a clean runner (`results.json` → `run`).
- The NaN-to-null fix in the export phase came after scoring and changed no prediction.

## Verification (2026-10-25)

- `pytest tests/unit/test_e109.py`: **20 passed**.
- Full backend suite (`pytest -q` in `backend/`): **691 passed, 18 skipped, 0 failed** (3 min 22 s).
- The E107 and E108 seals were re-hashed, unchanged.
- `git diff b56d90e -- frontend` is empty.

**Deployment.** The branch is pushed, not merged; Render deploys `main`. Production and the dashboard are unchanged.
