# E110: SWS hunger forecasting, generalization across areas and quarters (2021+)

**Branch:** `aiPHeed/e110-hunger-generalization` (from E109 `00937d0`). **Status:** evaluated; not served; production unchanged.

| Deliverable | File |
|---|---|
| Root cause and improvement | `E110_ROOT_CAUSE_AND_IMPROVEMENT_REPORT.md` |
| Experiments and comparisons | `E110_MODEL_EXPERIMENTS_AND_COMPARISONS.md` |
| Quarterly generalization | `E110_QUARTERLY_GENERALIZATION_REPORT.md` |
| Maximum reliable lead time | `E110_MAXIMUM_RELIABLE_LEAD_TIME.md` |
| Final methodology | `E110_FINAL_METHODOLOGY.md` |
| Thesis objectives | `E110_THESIS_OBJECTIVE_ASSESSMENT.md` |
| Recommendation | `E110_FINAL_RECOMMENDATION.md` |
| Protocol | `PROTOCOL.md` (sha `97f7493d…`; frozen before scoring); `runner/PROTOCOL_SHA256.txt` |
| Data and sources | `data/sws_area_rounds.csv`, `data/sws_area_rounds_excluded.csv`, `sources/SOURCES_LOG.md` |
| Scripts | `runner/diagnose_e109.py`, `runner/e110_lib.py`, `runner/run_e110.py` (`score`, `prospective`, `export`) |
| Tests | `backend/tests/unit/test_e110.py` |
| Outputs | `out/results.json`, `out/panel_lead{1..6}.csv`, `out/bl_lead{1,2}.csv`, `out/diagnosis.json` |
| Seal | `out/sealed_prospective.csv` (sha `81f0b237…`), `out/prospective_record.json` |
| Read-only API | `/api/v1/e110/{evaluation,forecast}` |

## Reproduce

```bash
cd aipheed-backend-aligned/experiments/E110_Hunger_Generalization/runner
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe diagnose_e109.py
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e110.py score
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e110.py prospective
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e110.py export
```

## Order of work

| Commit | Content |
|---|---|
| `d8912c5` | diagnosis, data, protocol (frozen before scoring) |
| `c7b9c80` | code and tests |
| `ec3f29a` and the next commit | two crash fixes (bootstrap block length; JSON booleans), made before any result was written |
| — | scoring and seal, run with a clean runner |

## Verification (2026-10-25)

- `pytest tests/unit/test_e110.py`: **18 passed**.
- Full backend suite: **709 passed, 18 skipped, 0 failed**.
- The E107, E108 and E109 seals are unchanged (tested).
- The frontend is untouched.
- **Deployment:** the branch is pushed, not merged.
