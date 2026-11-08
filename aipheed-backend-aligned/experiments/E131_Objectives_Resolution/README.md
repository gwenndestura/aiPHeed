# E131 · Resolving E130 and testing every thesis objective

**Outcome.**
- **Achieved:**
  - a measured food-insecurity target framework;
  - a sealed, measurement-aware forecasting candidate (LLM);
  - a provincial price-versus-income decomposition that answers the owner's CPI questions;
  - an honest model comparison (LightGBM is not superior).
- **Not achieved:** ≥ 75 % numerical agreement, a reliable Lead 2 (maximum reliable lead: none), or a demonstrated trigger-group contribution.

Start with `E131_THESIS_OBJECTIVE_ASSESSMENT.md` and `E131_PROVINCIAL_CPI_QUESTIONS.md`.

**Context.**
- Branch `aiPHeed/corrected-data-pipeline`.
- Protocol frozen at `88b270c` (sha256 in `runner/PROTOCOL_SHA256.txt`).
- Offline only: nothing in production, the dashboard, FIRI v2, FIRI3, E128, E129 or E130 changed. Nothing pushed.

## Reproduce

Use the backend virtual environment and run from this folder:

```
python -I runner/e131_acquire.py                 # OpenSTAT regional CPI (2021+), official food thresholds 2021/2023, poverty from the owner workbook
python -I runner/e131_x1.py                      # X1: 4-area SWS walk-forward, Leads 1-4, P-DASH / P-REL, 10 models, N1-N7, ablation, seeds (~1.5 min)
python -I runner/e131_univariate.py              # X1: univariate models on their full evaluable set
python -I runner/e131_provincial.py <FIES_PUF_2023_Volume1.dat>   # X3: price-versus-income, pattern stability, relative deprivation
python -I runner/e131_summary.py                 # headline numbers (out/e131_summary.json)
python -I runner/e131_seal.py                    # prospective seal (write-once; already written)
```

Tests: `backend/tests/unit/test_e131_resolution.py`.

## Deliverables (the directive's 12, plus the CPI answers)

| # | File |
|---|---|
| 1 | `E131_DIAGNOSTIC_REPORT.md` |
| 2 | `E131_DATA_SOURCE_INVESTIGATION.md` |
| 3 | `E131_ALTERNATIVE_APPROACHES.md` |
| 4 | `E131_SELECTED_SOLUTION.md` |
| 5 | `E131_EXPERIMENTAL_RESULTS.md` |
| 6 | `E131_TARGET_VALIDATION_REPORT.md` |
| 7 | `E131_NUMERICAL_FORECASTING_REPORT.md` |
| 8 | `E131_LEAD_TIME_REPORT.md` |
| 9 | `E131_TRIGGER_CONTRIBUTION_REPORT.md` |
| 10 | `E131_RELIABILITY_REPORT.md` |
| 11 | `E131_PRODUCTION_READINESS_REPORT.md` |
| 12 | `E131_THESIS_OBJECTIVE_ASSESSMENT.md` |
| — | `E131_PROVINCIAL_CPI_QUESTIONS.md` (the owner's five questions) |

**Machine outputs** are in `out/`:

| Files | Contents |
|---|---|
| `x1_*.csv` / `x1_*.json` | Predictions, metrics, rules, ablation, seeds, univariate set |
| `x3*.csv` / `x3*.json` | Provincial layer |
| `e131_summary.json` | Headline numbers |

**Seals** are in `sealed/` (`E131_SEAL_SHA256.txt`). **Raw data** are in `data/raw/`, with `data/acquisition_log.json`.

## Scoring the seal (after SWS publishes 2026-Q4 and later)

**Primary criterion only.** Addendum 1 (`E131_ADDENDUM_1_DA_OPERATIONAL_TOLERANCE.md`, frozen 2026-11-01) found no independently justifiable DA Region IV-A operational tolerance, so no secondary tolerance is applied.

1. Put the new non-commissioned SWS rounds (quarters after 2026-Q3) in `data/sws_rounds_after_2026Q3.csv`, with the same columns as E110 `data/sws_area_rounds.csv`.
2. Run `python -I runner/score_e131.py`.
   - It verifies the seal hash and scores every sealed forecast with |forecast − SWS| ≤ 1.645 × SE.
   - It also reports surge capture and 80 % interval coverage.
   - Output goes to `out/seal_scores/` (append-only).
3. Never re-seal, and never describe any other band as meeting the 75 % objective.
