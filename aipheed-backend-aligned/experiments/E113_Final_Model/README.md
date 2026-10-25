# E113: the final aiPHeed hunger forecast model (2021+)

**Branch:** `aiPHeed/e113-final-model`, from E112 `efe8a24`.

**Status:** evaluated; not served. Production, the served FIRI v2 and the dashboard design are unchanged.

**Result:** the adopted forecast is persistence (the latest SWS reading) with a conformal 80% band and its true horizon. No pre-registered candidate beat it, and no reliable lead was established.

## Deliverables

| # | Deliverable | File |
|---|---|---|
| 1 | Protocol (frozen before scoring) | `PROTOCOL_E113.md` (sha `bb255afe…`, 2026-10-25T10:16Z) + `ADDENDUM_1.md` (sha `24e5326b…`, before scoring) |
| 2 | Code, seed 113, one command | `runner/e113_lib.py`, `runner/run_e113.py`, `runner/score_prospective.py` |
| 3 | Final report (12 questions, change from E112) | `E113_FINAL_REPORT.md` |
| 4 | Root-cause audit, hypotheses, workstreams A–I, leakage audit | `E113_ROOT_CAUSE_AUDIT.md` |
| 5 | CPI validation | `E113_CPI_VALIDATION.md` |
| 6 | Objectives 1–5 | `E113_OBJECTIVES_ASSESSMENT.md` |
| 7 | Model card | `E113_FINAL_MODEL_CARD.md` |
| 8 | Sealed prospective forecasts + scorer | `out/sealed_prospective_A.csv` (`b53e8793…`, issue 2026-10-01); `out/sealed_prospective_B.csv` (`a86bcd49…`, issue 2026-10-25); `runner/score_prospective.py` (E109–E113) |
| 9 | Plain-language summary + diagram | `E113_PLAIN_LANGUAGE_SUMMARY.md` |
| — | Outputs | `out/results.json`, `out/analyses.json`, `out/leakage_audit.json`, `out/panel_lead{1..6}.csv`, `out/news_composites_{C,G}.csv`, `out/prospective_record.json`, `out/prospective_scores.json` |
| — | Read-only API | `/api/v1/e113/{evaluation,forecast}` (`backend/app/api/v1/e113.py`) |
| — | Tests | `backend/tests/unit/test_e113.py` |

## Reproduce

Run from `aipheed-backend-aligned/experiments/E113_Final_Model/runner`:

```bash
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe run_e113.py all
```

The run has six phases:
1. news composites;
2. leakage audit (must pass);
3. scoring;
4. analyses (CPI, regimes, spatial, 200-permutation placebos);
5. seals;
6. export.

It takes about 2.5 minutes and refuses to run if the protocol or addendum hash changed. Re-running reproduces the seal hashes.

**Scoring the seals.** Enter new SWS rounds (with publication dates) in `E110_Hunger_Generalization/data/sws_area_rounds.csv`, then run:

```bash
/c/Users/admin/aipheed/backend/venv/Scripts/python.exe score_prospective.py
```

## Verification (2026-10-25)

- `pytest tests/unit/test_e113.py`: **13 passed**. The tests cover:
  - the CPI release rule;
  - the regime anchor;
  - persistence at zero features;
  - news cut-off;
  - training targets published before issue;
  - the future-data test and its negative control;
  - the frozen protocol and audit;
  - reproduction;
  - the selection rule;
  - all seals;
  - the API.
- Full backend suite: **750 passed, 18 skipped, 0 failed**.
- `run_e113.py all` re-run reproduces both seal hashes exactly (2.5 min).

## Flags for the adviser

1. **Pre-2021 SWS history was not used.** The study-window rule is binding, although the E113 brief asked for longer history.
2. **The 2025 respondent-base change is handled by a regime-specific anchor.** This is an assumption that needs approval; no bridging round exists.
3. **The CPI comes from the repository, with a day-10 release rule.** National and rice CPI are not available (no-new-data rule).
