# E112: final food-insecurity forecasting methodology with dated news indicators (2021+)

**Branch:** `aiPHeed/e112-food-insecurity-forecasting`, from E111 `509781e`.

**Status:** evaluated; not served. Production, the served FIRI v2 and the dashboard design are unchanged.

## Deliverables

| Deliverable | File |
|---|---|
| Root-cause audit and decision record (E107–E111) | `E112_ROOT_CAUSE_AUDIT_AND_DECISION_RECORD.md` |
| Target and data suitability (incl. LGU data gap) | `E112_TARGET_AND_DATA_SUITABILITY.md` |
| Final methodology and diagram | `E112_FINAL_METHODOLOGY.md` |
| News evaluation (pipeline, validity, advance warning, news-only / ablation / contribution) | `E112_NEWS_EVALUATION.md` |
| 12-indicator LightGBM, baselines and generalization | `E112_LIGHTGBM_BASELINES_GENERALIZATION.md` |
| Horizon assessment | `E112_HORIZON_ASSESSMENT.md` |
| Objective-by-objective assessment | `E112_OBJECTIVES_ASSESSMENT.md` |
| Thesis-ready methodology and results | `E112_THESIS_READY_METHODOLOGY_AND_RESULTS.md` |
| Answers to the 12 questions | `E112_FINAL_REPORT.md` |
| Protocol | `PROTOCOL.md` (sha `77c3d9e2…`, frozen 2026-10-25T09:50Z before scoring) + `ADDENDUM_1.md` (sha `7af47afe…`, Objective-4 baselines, hashed before they were scored) |
| Code | `runner/news_indicators.py`, `runner/e112_lib.py`, `runner/run_e112.py`, `runner/score_prospective.py` |
| Tests | `backend/tests/unit/test_e112.py` |
| Outputs | `out/news_quarterly_{corpus,gdelt}.csv`, `out/results.json`, `out/objective4_baselines.json`, `out/bl_lead{1..4}.csv`, `out/panel_lead{1..4}.csv`, `out/prospective_scores.json` |
| Seal | `out/sealed_prospective.csv` (sha `7f774c00…`), origin 2026-Q3, issue 2026-10-01. The E107–E111 seals are verified unchanged. |
| Read-only API | `/api/v1/e112/{evaluation,forecast,news-indicators}` (`backend/app/api/v1/e112.py`) |

## Reproduce

Run from `aipheed-backend-aligned/experiments/E112_Food_Insecurity_Forecasting/runner`:

```bash
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe news_indicators.py
```

```bash
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e112.py score
```

```bash
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e112.py obj4
```

```bash
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e112.py prospective
```

```bash
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e112.py export
```

```bash
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe score_prospective.py
```

**Notes on the run:**
- `score` and `obj4` refuse to run if `PROTOCOL.md` or `ADDENDUM_1.md` has changed.
- Re-running is deterministic: the seal hash was identical on re-run.
- Runtime is about 1 minute.

**Scoring sealed forecasts.** Enter each new SWS round, with its publication date, in:
- `E109_Hunger_Forecasting/data/outcome_rounds.csv` (Balance Luzon);
- `E110_Hunger_Generalization/data/sws_area_rounds.csv` (all areas).

Then run `score_prospective.py`. Sealed files are never modified, and a changed hash is refused.

## Verification (2026-10-25)

- `pytest tests/unit/test_e112.py`: **14 passed**. The tests cover:
  - news cutoff;
  - an injected post-issue headline is refused;
  - YoY definition;
  - dedup and lexicon;
  - LightGBM reproduces E109;
  - 12 families;
  - future rounds change nothing;
  - stored predictions reproduce;
  - the frozen protocol and decision rule;
  - all seals;
  - the API.
- **Full backend suite:** **737 passed, 18 skipped, 0 failed**.
- **Frontend:** untouched.
- **Deployment:** none.

## Unresolved evidence requirements

See `E112_FINAL_REPORT.md` §12:
- unseen SWS quarters, from 2026-Q4;
- CBMS 2024 LGU food-security aggregates;
- a provincial FIES or hunger series;
- prospective replication of the news association;
- handling of the 2025 SWS respondent-base change.

Under the no-new-data rule, none of these was requested or collected.
